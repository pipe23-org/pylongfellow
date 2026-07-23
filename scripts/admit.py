#!/usr/bin/env python3
"""Admit circuits and presentations into the differential-test corpus.

    python scripts/admit.py circuit-import <blob-path> --origin <string>
    python scripts/admit.py circuit-generate --version V --num-attributes N
    python scripts/admit.py presentation <fixture-json-path> --slug <slug>

circuit-import copies an externally produced circuit blob byte-identically.
circuit-generate produces a blob with the pinned google-cpp backend. Both write
the blob under tests/differential/circuits/ with a same-stem JSON sidecar.
presentation converts a committed fixture from tests/data/ into a directory under
tests/differential/presentations/, writing presentation.json and, when the
fixture carries a proof, a .proof file with its sidecar.
"""

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import cbor2

import pylongfellow.mdoc as mdoc
from pylongfellow import Pylongfellow

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "longfellow-zk"
CIRCUITS = ROOT / "tests" / "differential" / "circuits"
PRESENTATIONS = ROOT / "tests" / "differential" / "presentations"
SYSTEM = "longfellow-libzk-v1"
GIT = shutil.which("git") or "git"


def _pin() -> str:
    result = subprocess.run(
        [GIT, "-C", str(VENDOR), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n")


def _write_circuit(blob: bytes, spec: mdoc.ZkSpec, origin: str) -> Path:
    stem = f"v{spec.version}-{spec.num_attributes}attr"
    CIRCUITS.mkdir(parents=True, exist_ok=True)
    blob_path = CIRCUITS / f"{stem}.circuit"
    blob_path.write_bytes(blob)
    sidecar = {
        "system": SYSTEM,
        "circuit_id": spec.circuit_hash,
        "computed_by": f"google-cpp @ {_pin()}",
        "byte_sha256": _sha256(blob),
        "version": spec.version,
        "num_attributes": spec.num_attributes,
        "block_enc_hash": spec.block_enc_hash,
        "block_enc_sig": spec.block_enc_sig,
        "origin": origin,
    }
    _write_json(CIRCUITS / f"{stem}.json", sidecar)
    print(f"wrote circuits/{stem}.circuit + {stem}.json")
    return blob_path


def circuit_import(blob_path: str, origin: str) -> None:
    blob = Path(blob_path).read_bytes()
    circuit_id = mdoc.circuit_id(blob)
    spec = mdoc.find_zk_spec(SYSTEM, circuit_id)
    if spec is None:
        sys.exit(f"error: no ZkSpec for {SYSTEM} {circuit_id}")
    _write_circuit(blob, spec, origin)


def circuit_generate(version: int, num_attributes: int) -> None:
    spec = next(
        (s for s in mdoc.zk_specs() if s.version == version and s.num_attributes == num_attributes),
        None,
    )
    if spec is None:
        sys.exit(f"error: no ZkSpec for version {version}, {num_attributes} attributes")
    blob = Pylongfellow(backend="google-cpp").generate_circuit(spec)
    if mdoc.circuit_id(blob) != spec.circuit_hash:
        sys.exit("error: generated circuit_id does not match spec.circuit_hash")
    _write_circuit(blob, spec, f"generated: google-cpp @ {_pin()}")


def _transcript_hex(fixture: dict[str, Any]) -> str:
    if "transcript_hex" in fixture:
        return fixture["transcript_hex"]
    return base64.b64decode(fixture["transcript_b64"]).hex()


def _device_namespaces_hex(mdoc_hex: str) -> str:
    response = cbor2.loads(bytes.fromhex(mdoc_hex))
    name_spaces = response["documents"][0]["deviceSigned"]["nameSpaces"]
    return name_spaces.value.hex()


def _attrs_from_credential(fixture: dict, mdoc_hex: str) -> list[dict]:
    """Rebuild the fixture's attrs against the credential's own issuerSigned map.

    The namespace is resolved by locating the attribute id in the mdoc's
    issuerSigned nameSpaces; a fixture's own namespace record is not trusted.
    The claimed value must equal the credential's elementValue.
    """
    response = cbor2.loads(bytes.fromhex(mdoc_hex))
    elements: dict[str, tuple[str, bytes]] = {}
    for namespace, items in response["documents"][0]["issuerSigned"]["nameSpaces"].items():
        for item in items:
            inner = cbor2.loads(item.value)
            identifier = inner["elementIdentifier"]
            if identifier in elements:
                sys.exit(f"error: attribute id {identifier!r} appears in multiple namespaces")
            elements[identifier] = (namespace, cbor2.dumps(inner["elementValue"]))
    attrs = []
    for attr in fixture["attrs"]:
        if attr["id"] not in elements:
            sys.exit(f"error: attribute id {attr['id']!r} not in the credential's issuerSigned")
        namespace, element_value = elements[attr["id"]]
        if bytes.fromhex(attr["cbor_value_hex"]) != element_value:
            sys.exit(f"error: claimed value for {attr['id']!r} does not match the credential")
        attrs.append(
            {"namespace": namespace, "id": attr["id"], "cbor_value_hex": attr["cbor_value_hex"]}
        )
    return attrs


def _circuit_byte_sha256(circuit_id: str) -> str:
    for sidecar_path in CIRCUITS.glob("*.json"):
        sidecar = json.loads(sidecar_path.read_text())
        if sidecar["circuit_id"] == circuit_id:
            return sidecar["byte_sha256"]
    sys.exit(f"error: circuit {circuit_id} not admitted; import it first")


def presentation(fixture_path: str, slug: str) -> None:
    src = Path(fixture_path)
    fixture = json.loads(src.read_text())
    circuit_id = fixture["circuit_hash"]
    spec = mdoc.find_zk_spec(SYSTEM, circuit_id)
    if spec is None:
        sys.exit(f"error: no ZkSpec for {SYSTEM} {circuit_id}")

    origin = str(src.resolve().relative_to(ROOT))
    out = PRESENTATIONS / slug
    out.mkdir(parents=True, exist_ok=True)

    doc = {
        "doctype": fixture["doctype"],
        "system": fixture["system"],
        "circuit_id": circuit_id,
        "attrs": fixture["attrs"],
        "transcript_hex": _transcript_hex(fixture),
        "issuer_pk_x": fixture["issuer_pk_x"],
        "issuer_pk_y": fixture["issuer_pk_y"],
        "timestamp": fixture["timestamp"],
        "origin": origin,
    }
    if "mdoc_hex" in fixture:
        doc["attrs"] = _attrs_from_credential(fixture, fixture["mdoc_hex"])
        doc["mdoc_hex"] = fixture["mdoc_hex"]
        doc["device_namespaces_hex"] = _device_namespaces_hex(fixture["mdoc_hex"])
    _write_json(out / "presentation.json", doc)
    print(f"wrote presentations/{slug}/presentation.json")

    if "proof_b64" in fixture:
        proof = base64.b64decode(fixture["proof_b64"])
        stem = f"google-cpp-v{spec.version}"
        proof_path = out / f"{stem}.proof"
        proof_path.write_bytes(proof)
        sidecar = {
            "prover": "google-cpp",
            "prover_source": fixture["source"],
            "circuit_id": circuit_id,
            "circuit_byte_sha256": _circuit_byte_sha256(circuit_id),
            "byte_sha256": _sha256(proof),
            "origin": origin,
        }
        _write_json(out / f"{stem}.json", sidecar)
        print(f"wrote presentations/{slug}/{stem}.proof + {stem}.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("circuit-import")
    p_import.add_argument("blob_path")
    p_import.add_argument("--origin", required=True)

    p_generate = sub.add_parser("circuit-generate")
    p_generate.add_argument("--version", type=int, required=True)
    p_generate.add_argument("--num-attributes", type=int, required=True)

    p_present = sub.add_parser("presentation")
    p_present.add_argument("fixture_path")
    p_present.add_argument("--slug", required=True)

    args = parser.parse_args()
    if args.command == "circuit-import":
        circuit_import(args.blob_path, args.origin)
    elif args.command == "circuit-generate":
        circuit_generate(args.version, args.num_attributes)
    else:
        presentation(args.fixture_path, args.slug)


if __name__ == "__main__":
    main()

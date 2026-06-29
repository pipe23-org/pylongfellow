#!/usr/bin/env python3
"""Extract clean verify() inputs from a ZK mdoc device response.

    python scripts/extract_device_response.py <device_response.json> <fixture_name>

Reads a raw response (base64 Transcript + ZKDeviceResponseCBOR), pulls out the
verify() inputs, and writes tests/data/<fixture_name>.json plus the referenced
circuit blob into tests/data/circuits/. Run once; the output is committed and
conftest loads it.
"""

import base64
import json
import shutil
import sys
from pathlib import Path

import cbor2
from cryptography import x509

ROOT = Path(__file__).resolve().parent.parent
VENDOR_CIRCUITS = ROOT / "vendor/longfellow-zk/lib/circuits/mdoc/circuits"
DATA = ROOT / "tests/data"


def _issuer_pk(cert_der: bytes) -> tuple[str, str]:
    nums = x509.load_der_x509_certificate(cert_der).public_key().public_numbers()
    return f"{nums.x:064x}", f"{nums.y:064x}"


def main(src: str, name: str) -> None:
    raw = json.loads(Path(src).read_text())
    response = cbor2.loads(base64.b64decode(raw["ZKDeviceResponseCBOR"]))
    doc = response["zkDocuments"][0]
    data = cbor2.loads(doc["documentData"].value)  # tag-24 payload
    circuit_hash = data["zkSystemId"]
    x, y = _issuer_pk(data["msoX5chain"])

    fixture = {
        "source": str(Path(src).resolve().relative_to(ROOT)),
        "system": "longfellow-libzk-v1",
        "circuit_hash": circuit_hash,
        "doctype": data["docType"],
        "timestamp": data["timestamp"].isoformat(),
        "issuer_pk_x": x,
        "issuer_pk_y": y,
        "transcript_b64": raw["Transcript"],
        "proof_b64": base64.b64encode(doc["proof"]).decode(),
        "attrs": [
            {
                "namespace": namespace,
                "id": item["elementIdentifier"],
                "cbor_value_hex": cbor2.dumps(item["elementValue"]).hex(),
            }
            for namespace, items in data["issuerSigned"].items()
            for item in items
        ],
    }
    (DATA / f"{name}.json").write_text(json.dumps(fixture, indent=2) + "\n")
    (DATA / "circuits").mkdir(exist_ok=True)
    shutil.copyfile(VENDOR_CIRCUITS / circuit_hash, DATA / "circuits" / circuit_hash)
    print(f"wrote tests/data/{name}.json + circuits/{circuit_hash[:16]}…")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

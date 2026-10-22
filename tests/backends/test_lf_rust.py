import dataclasses
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError, lf_rust

_REPO = Path(__file__).parents[2]
_DATA = _REPO / "tests" / "api" / "data"
_RUST = _REPO / "vendor" / "longfellow-zk" / "rust" / "applications" / "mdoc_zk"
_ARCHIVES = _RUST / "artifacts" / "circuits"
_ERROR_RS = _RUST / "runtime" / "src" / "error.rs"

_V7_1ATTR = "8d079211715200ff06c5109639245502bfe94aa869908d31176aae4016182121"


def _lf_rust_available() -> bool:
    try:
        return (
            importlib.util.find_spec("pylongfellow.backends._lf_rust.longfellow_zk_uniffi")
            is not None
        )
    except ModuleNotFoundError:
        return False


# PYLONGFELLOW_BUILD_LF_RUST defaults OFF, so an ordinary build has no cdylib to call.
# Delete this skip when the switch defaults ON.
skip_without_lf_rust = pytest.mark.skipif(
    not _lf_rust_available(), reason="lf-rust backend not built"
)


@dataclasses.dataclass(frozen=True)
class _ProveInputs:
    circuit: bytes
    mdoc_bytes: bytes
    issuer_pk: mdoc.PublicKey
    transcript: bytes
    claims: list[mdoc.RequestedAttribute]
    timestamp: datetime
    doctype: str


def _mdoc_eu_av() -> _ProveInputs:
    fixture = json.loads((_DATA / "mdoc_eu_av.json").read_text())
    return _ProveInputs(
        # The committed blob is the C++ tree's own v7/1attr archive, byte for byte.
        circuit=(_DATA / "circuits" / fixture["circuit_hash"]).read_bytes(),
        mdoc_bytes=bytes.fromhex(fixture["mdoc_hex"]),
        issuer_pk=mdoc.PublicKey(int(fixture["issuer_pk_x"], 16), int(fixture["issuer_pk_y"], 16)),
        transcript=bytes.fromhex(fixture["transcript_hex"]),
        claims=[
            mdoc.RequestedAttribute(
                attr["namespace"], attr["id"], bytes.fromhex(attr["cbor_value_hex"])
            )
            for attr in fixture["attrs"]
        ],
        timestamp=datetime.fromisoformat(fixture["timestamp"]),
        doctype=fixture["doctype"],
    )


def _upstream_codes(enum: str) -> dict[str, int]:
    body = _ERROR_RS.read_text().split(f"pub enum {enum} {{")[1].split("}")[0]
    return {match[1]: int(match[2]) for match in re.finditer(r"(\w+) = (\d+),", body)}


def test_prover_error_codes_match_upstream():
    assert {code.name: code.value for code in lf_rust.ProverErrorCode} == _upstream_codes(
        "MdocProverErrorCode"
    )


def test_verifier_error_codes_match_upstream():
    assert {code.name: code.value for code in lf_rust.VerifierErrorCode} == _upstream_codes(
        "MdocVerifierErrorCode"
    )


def test_prove_reports_unavailable_backend(monkeypatch):
    inputs = _mdoc_eu_av()
    state = lf_rust.BACKEND.load_circuit(inputs.circuit, 7, 1)
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._lf_rust", None)
    with pytest.raises(BackendUnavailableError, match="lf-rust/build"):
        lf_rust.BACKEND.prove(
            state,
            inputs.mdoc_bytes,
            inputs.issuer_pk,
            inputs.transcript,
            inputs.claims,
            inputs.timestamp,
        )


def test_verify_reports_unavailable_backend(monkeypatch):
    inputs = _mdoc_eu_av()
    state = lf_rust.BACKEND.load_circuit(inputs.circuit, 7, 1)
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._lf_rust", None)
    with pytest.raises(BackendUnavailableError, match="lf-rust/build"):
        lf_rust.BACKEND.verify(
            state,
            inputs.issuer_pk,
            inputs.transcript,
            inputs.claims,
            inputs.timestamp,
            b"",
            inputs.doctype,
            None,
        )


def test_materialize_circuit_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._lf_rust", None)
    with pytest.raises(BackendUnavailableError, match="lf-rust/build"):
        lf_rust.materialize_circuit(7, 1)


def test_prove_rejects_claims_count_mismatch():
    inputs = _mdoc_eu_av()
    state = lf_rust.BACKEND.load_circuit(inputs.circuit, 7, 2)
    with pytest.raises(ValueError, match="does not match the loaded circuit"):
        lf_rust.BACKEND.prove(
            state,
            inputs.mdoc_bytes,
            inputs.issuer_pk,
            inputs.transcript,
            inputs.claims,
            inputs.timestamp,
        )


def test_verify_rejects_claims_count_mismatch():
    inputs = _mdoc_eu_av()
    state = lf_rust.BACKEND.load_circuit(inputs.circuit, 7, 2)
    with pytest.raises(ValueError, match="does not match the loaded circuit"):
        lf_rust.BACKEND.verify(
            state,
            inputs.issuer_pk,
            inputs.transcript,
            inputs.claims,
            inputs.timestamp,
            b"",
            inputs.doctype,
            None,
        )


@skip_without_lf_rust
def test_prove_rejects_unknown_version():
    inputs = _mdoc_eu_av()
    longfellow = Pylongfellow(backend="lf-rust")
    longfellow.load_circuit(inputs.circuit, 4, 1)
    with pytest.raises(ValueError, match="no circuit with version 4 and num_attributes 1"):
        longfellow.prove(
            inputs.mdoc_bytes, inputs.issuer_pk, inputs.transcript, inputs.claims, inputs.timestamp
        )


@skip_without_lf_rust
def test_verify_rejects_unknown_version():
    inputs = _mdoc_eu_av()
    longfellow = Pylongfellow(backend="lf-rust")
    longfellow.load_circuit(inputs.circuit, 4, 1)
    with pytest.raises(ValueError, match="no circuit with version 4 and num_attributes 1"):
        longfellow.verify(
            inputs.issuer_pk,
            inputs.transcript,
            inputs.claims,
            inputs.timestamp,
            b"",
            inputs.doctype,
        )


@skip_without_lf_rust
def test_prove_rejects_unknown_claim():
    inputs = _mdoc_eu_av()
    longfellow = Pylongfellow(backend="lf-rust")
    longfellow.load_circuit(inputs.circuit, 7, 1)
    claims = [dataclasses.replace(inputs.claims[0], id="definitely_not_present")]
    with pytest.raises(mdoc.ProverError) as excinfo:
        longfellow.prove(
            inputs.mdoc_bytes, inputs.issuer_pk, inputs.transcript, claims, inputs.timestamp
        )
    assert excinfo.value.code is lf_rust.ProverErrorCode.AttributeNotFound


@skip_without_lf_rust
def test_materialize_circuit_matches_committed_archive():
    assert lf_rust.materialize_circuit(7, 1) == (_ARCHIVES / f"{_V7_1ATTR}.lfa2").read_bytes()


@skip_without_lf_rust
def test_materialize_circuit_rejects_unknown_version():
    with pytest.raises(mdoc.CircuitError) as excinfo:
        lf_rust.materialize_circuit(4, 1)
    assert excinfo.value.code is lf_rust.ProverErrorCode.InvalidZkSpecVersion


@pytest.mark.slow
@skip_without_lf_rust
def test_materialize_circuit_compiles_current_version():
    assert lf_rust.materialize_circuit(8, 1)


@pytest.mark.slow
@skip_without_lf_rust
def test_round_trip_verifies_over_cpp_circuit():
    inputs = _mdoc_eu_av()
    longfellow = Pylongfellow(backend="lf-rust")
    longfellow.load_circuit(inputs.circuit, 7, 1)
    proof = longfellow.prove(
        inputs.mdoc_bytes, inputs.issuer_pk, inputs.transcript, inputs.claims, inputs.timestamp
    )
    longfellow.verify(
        inputs.issuer_pk,
        inputs.transcript,
        inputs.claims,
        inputs.timestamp,
        proof,
        inputs.doctype,
    )


@pytest.mark.slow
@skip_without_lf_rust
def test_round_trip_verifies_over_materialized_circuit():
    inputs = _mdoc_eu_av()
    longfellow = Pylongfellow(backend="lf-rust")
    longfellow.load_circuit(lf_rust.materialize_circuit(7, 1), 7, 1)
    proof = longfellow.prove(
        inputs.mdoc_bytes, inputs.issuer_pk, inputs.transcript, inputs.claims, inputs.timestamp
    )
    longfellow.verify(
        inputs.issuer_pk,
        inputs.transcript,
        inputs.claims,
        inputs.timestamp,
        proof,
        inputs.doctype,
    )


@pytest.mark.slow
@skip_without_lf_rust
def test_verify_rejects_tampered_proof():
    inputs = _mdoc_eu_av()
    longfellow = Pylongfellow(backend="lf-rust")
    longfellow.load_circuit(inputs.circuit, 7, 1)
    proof = bytearray(
        longfellow.prove(
            inputs.mdoc_bytes, inputs.issuer_pk, inputs.transcript, inputs.claims, inputs.timestamp
        )
    )
    proof[100] ^= 0xFF
    with pytest.raises(mdoc.VerifierError) as excinfo:
        longfellow.verify(
            inputs.issuer_pk,
            inputs.transcript,
            inputs.claims,
            inputs.timestamp,
            bytes(proof),
            inputs.doctype,
        )
    assert excinfo.value.code is lf_rust.VerifierErrorCode.GeneralFailure

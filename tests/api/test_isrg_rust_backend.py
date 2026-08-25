"""The isrg-rust backend: input-validation branches without the native module, then round trips."""

import dataclasses
import sys
from datetime import UTC, datetime

import pytest

from pylongfellow import mdoc
from pylongfellow.backends import BackendUnavailableError, isrg_rust

from .conftest import ISRG_RUST_AVAILABLE

_AWARE = datetime(2024, 10, 1, 9, 0, 0, tzinfo=UTC)

skip_without_isrg_rust = pytest.mark.skipif(
    not ISRG_RUST_AVAILABLE, reason="isrg-rust backend not built"
)


def _dummy_state() -> object:
    return isrg_rust._LoadedCircuit(b"", 6, 1)


def _one_attr() -> list[mdoc.RequestedAttribute]:
    return [mdoc.RequestedAttribute("org.iso.18013.5.1", "issue_date", b"\x01")]


def test_load_rejects_bad_version(vendored_vector):
    with pytest.raises(ValueError, match="unsupported circuit version"):
        isrg_rust.BACKEND.load_circuit(vendored_vector.circuit, 5, 1)


def test_prove_rejects_mixed_namespaces():
    attrs = [
        mdoc.RequestedAttribute("ns.a", "x", b"\x01"),
        mdoc.RequestedAttribute("ns.b", "y", b"\x02"),
    ]
    with pytest.raises(ValueError, match="one namespace"):
        isrg_rust.BACKEND.prove(_dummy_state(), b"", mdoc.PublicKey(1, 2), b"", attrs, _AWARE)


def test_verify_rejects_missing_device_namespaces():
    with pytest.raises(ValueError, match="device_namespaces is required"):
        isrg_rust.BACKEND.verify(
            _dummy_state(), mdoc.PublicKey(1, 2), b"", _one_attr(), _AWARE, b"", "doc", None
        )


def test_encode_public_key(vendored_vector):
    encoded = isrg_rust._encode_public_key(vendored_vector.issuer_pk)
    assert encoded == vendored_vector.issuer_pk_sec1
    assert len(encoded) == 65
    assert encoded[0] == 0x04


def test_circuit_version_maps_both():
    class _Versions:
        V6 = object()
        V7 = object()

    class _Zk:
        CircuitVersion = _Versions

    assert isrg_rust._circuit_version(_Zk, 6) is _Versions.V6
    assert isrg_rust._circuit_version(_Zk, 7) is _Versions.V7


def test_prove_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._zk_cred", None)
    with pytest.raises(BackendUnavailableError, match="isrg-rust/build"):
        isrg_rust.BACKEND.prove(_dummy_state(), b"", mdoc.PublicKey(1, 2), b"", _one_attr(), _AWARE)


def test_verify_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._zk_cred", None)
    with pytest.raises(BackendUnavailableError, match="isrg-rust/build"):
        isrg_rust.BACKEND.verify(
            _dummy_state(), mdoc.PublicKey(1, 2), b"", _one_attr(), _AWARE, b"", "doc", b"\xa0"
        )


@pytest.mark.slow
@skip_without_isrg_rust
def test_round_trip_verifies(isrg, isrg_proof, vendored_vector):
    v = vendored_vector
    assert isrg_proof
    isrg.verify(
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        isrg_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )


@pytest.mark.slow
@skip_without_isrg_rust
def test_verify_rejects_tampered_proof(isrg, isrg_proof, vendored_vector):
    v = vendored_vector
    tampered = bytearray(isrg_proof)
    tampered[100] ^= 0xFF
    with pytest.raises(mdoc.VerifierError) as excinfo:
        isrg.verify(
            v.issuer_pk,
            v.transcript,
            v.attrs,
            v.timestamp,
            bytes(tampered),
            v.doctype,
            device_namespaces=v.device_namespaces,
        )
    assert excinfo.value.code is None
    assert str(excinfo.value) == str(excinfo.value.__cause__)


@pytest.mark.slow
@skip_without_isrg_rust
def test_prove_rejects_unknown_claim(isrg, vendored_vector):
    v = vendored_vector
    attrs = [dataclasses.replace(v.attrs[0], id="definitely_not_present")]
    with pytest.raises(mdoc.ProverError) as excinfo:
        isrg.prove(v.mdoc_bytes, v.issuer_pk, v.transcript, attrs, v.timestamp)
    assert excinfo.value.code is None
    assert str(excinfo.value) == str(excinfo.value.__cause__)

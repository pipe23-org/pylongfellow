"""The rust backend: input-validation branches without the native module, then round trips."""

import dataclasses
import sys
from datetime import UTC, datetime

import pytest

from pylongfellow import mdoc
from pylongfellow.backends import (
    BackendUnavailableError,
    CircuitHandle,
    GenerationUnsupportedError,
    rust,
)

from .conftest import RUST_AVAILABLE

_AWARE = datetime(2024, 10, 1, 9, 0, 0, tzinfo=UTC)
_NAIVE = datetime(2024, 10, 1, 9, 0, 0)
_SPEC = mdoc.ZkSpec("", "0" * 64, 1, 6, 0, 0)

skip_without_rust = pytest.mark.skipif(not RUST_AVAILABLE, reason="rust backend not built")


def _dummy_handle() -> CircuitHandle:
    return CircuitHandle(spec=_SPEC, backend=rust.BACKEND, state=rust._Circuit(b"", 6, 1))


def _one_attr() -> list[mdoc.RequestedAttribute]:
    return [mdoc.RequestedAttribute("org.iso.18013.5.1", "issue_date", b"\x01")]


def test_generate_circuit_unsupported():
    with pytest.raises(GenerationUnsupportedError):
        rust.BACKEND.generate_circuit(_SPEC)


def test_load_rejects_bad_version(vendored_vector):
    spec = dataclasses.replace(vendored_vector.spec, version=5)
    with pytest.raises(ValueError, match="unsupported circuit version"):
        rust.BACKEND.load_circuit(spec, vendored_vector.compressed)


def test_load_rejects_hash_mismatch(vendored_vector):
    spec = dataclasses.replace(vendored_vector.spec, circuit_hash="a" * 64)
    with pytest.raises(ValueError, match="does not match the circuit"):
        rust.BACKEND.load_circuit(spec, vendored_vector.compressed)


def test_load_rejects_missing_zstandard(monkeypatch, vendored_vector):
    monkeypatch.setitem(sys.modules, "zstandard", None)
    with pytest.raises(BackendUnavailableError, match="zstandard"):
        rust.BACKEND.load_circuit(vendored_vector.spec, vendored_vector.compressed)


def test_prove_rejects_mixed_namespaces():
    attrs = [
        mdoc.RequestedAttribute("ns.a", "x", b"\x01"),
        mdoc.RequestedAttribute("ns.b", "y", b"\x02"),
    ]
    with pytest.raises(ValueError, match="one namespace"):
        rust.BACKEND.prove(_dummy_handle(), b"", (1, 2), b"", attrs, _AWARE)


def test_prove_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        rust.BACKEND.prove(_dummy_handle(), b"", (1, 2), b"", _one_attr(), _NAIVE)


def test_verify_rejects_missing_device_namespaces():
    with pytest.raises(ValueError, match="device_namespaces is required"):
        rust.BACKEND.verify(_dummy_handle(), (1, 2), b"", _one_attr(), _AWARE, b"", "doc", None)


def test_verify_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        rust.BACKEND.verify(_dummy_handle(), (1, 2), b"", _one_attr(), _NAIVE, b"", "doc", b"\xa0")


def test_sec1_encoding(vendored_vector):
    encoded = rust._sec1(vendored_vector.issuer_pk)
    assert encoded == vendored_vector.issuer_pk_sec1
    assert len(encoded) == 65
    assert encoded[0] == 0x04


def test_circuit_version_maps_both():
    class _Versions:
        V6 = object()
        V7 = object()

    class _Zk:
        CircuitVersion = _Versions

    assert rust._circuit_version(_Zk, 6) is _Versions.V6
    assert rust._circuit_version(_Zk, 7) is _Versions.V7


def test_prove_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._zk_cred", None)
    with pytest.raises(BackendUnavailableError, match="build_rust_backend"):
        rust.BACKEND.prove(_dummy_handle(), b"", (1, 2), b"", _one_attr(), _AWARE)


def test_verify_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._zk_cred", None)
    with pytest.raises(BackendUnavailableError, match="build_rust_backend"):
        rust.BACKEND.verify(_dummy_handle(), (1, 2), b"", _one_attr(), _AWARE, b"", "doc", b"\xa0")


@pytest.mark.slow
@skip_without_rust
def test_round_trip_verifies(rust_handle, rust_proof, vendored_vector):
    v = vendored_vector
    assert rust_proof
    mdoc.verify(
        rust_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        rust_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )


@pytest.mark.slow
@skip_without_rust
def test_verify_rejects_tampered_proof(rust_handle, rust_proof, vendored_vector):
    v = vendored_vector
    tampered = bytearray(rust_proof)
    tampered[100] ^= 0xFF
    with pytest.raises(mdoc.VerifierError) as excinfo:
        mdoc.verify(
            rust_handle,
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
@skip_without_rust
def test_prove_rejects_unknown_claim(rust_handle, vendored_vector):
    v = vendored_vector
    attrs = [dataclasses.replace(v.attrs[0], id="definitely_not_present")]
    with pytest.raises(mdoc.ProverError) as excinfo:
        mdoc.prove(rust_handle, v.mdoc_bytes, v.issuer_pk, v.transcript, attrs, v.timestamp)
    assert excinfo.value.code is None
    assert str(excinfo.value) == str(excinfo.value.__cause__)

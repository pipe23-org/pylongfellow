"""The isrg backend: input-validation branches without the native module, then round trips."""

import dataclasses
import sys
from datetime import UTC, datetime

import pytest

from pylongfellow import mdoc
from pylongfellow.backends import (
    BackendUnavailableError,
    CircuitHandle,
    GenerationUnsupportedError,
    isrg,
)

from .conftest import ISRG_AVAILABLE

_AWARE = datetime(2024, 10, 1, 9, 0, 0, tzinfo=UTC)
_NAIVE = datetime(2024, 10, 1, 9, 0, 0)
_SPEC = mdoc.ZkSpec("", "0" * 64, 1, 6, 0, 0)

skip_without_isrg = pytest.mark.skipif(not ISRG_AVAILABLE, reason="isrg backend not built")


def _dummy_handle() -> CircuitHandle:
    return CircuitHandle(spec=_SPEC, backend=isrg.BACKEND, state=isrg._Circuit(b"", 6, 1))


def _one_attr() -> list[mdoc.RequestedAttribute]:
    return [mdoc.RequestedAttribute("org.iso.18013.5.1", "issue_date", b"\x01")]


def test_generate_circuit_unsupported():
    with pytest.raises(GenerationUnsupportedError):
        isrg.BACKEND.generate_circuit(_SPEC)


def test_load_rejects_bad_version(vendored_vector):
    spec = dataclasses.replace(vendored_vector.spec, version=5)
    with pytest.raises(ValueError, match="unsupported circuit version"):
        isrg.BACKEND.load_circuit(spec, vendored_vector.compressed)


def test_load_rejects_missing_zstandard(monkeypatch, vendored_vector):
    monkeypatch.setitem(sys.modules, "zstandard", None)
    with pytest.raises(BackendUnavailableError, match="zstandard"):
        isrg.BACKEND.load_circuit(vendored_vector.spec, vendored_vector.compressed)


def test_prove_rejects_mixed_namespaces():
    attrs = [
        mdoc.RequestedAttribute("ns.a", "x", b"\x01"),
        mdoc.RequestedAttribute("ns.b", "y", b"\x02"),
    ]
    with pytest.raises(ValueError, match="one namespace"):
        isrg.BACKEND.prove(_dummy_handle(), b"", (1, 2), b"", attrs, _AWARE)


def test_prove_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        isrg.BACKEND.prove(_dummy_handle(), b"", (1, 2), b"", _one_attr(), _NAIVE)


def test_verify_rejects_missing_device_namespaces():
    with pytest.raises(ValueError, match="device_namespaces is required"):
        isrg.BACKEND.verify(_dummy_handle(), (1, 2), b"", _one_attr(), _AWARE, b"", "doc", None)


def test_verify_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        isrg.BACKEND.verify(_dummy_handle(), (1, 2), b"", _one_attr(), _NAIVE, b"", "doc", b"\xa0")


def test_sec1_encoding(vendored_vector):
    encoded = isrg._sec1(vendored_vector.issuer_pk)
    assert encoded == vendored_vector.issuer_pk_sec1
    assert len(encoded) == 65
    assert encoded[0] == 0x04


def test_circuit_version_maps_both():
    class _Versions:
        V6 = object()
        V7 = object()

    class _Zk:
        CircuitVersion = _Versions

    assert isrg._circuit_version(_Zk, 6) is _Versions.V6
    assert isrg._circuit_version(_Zk, 7) is _Versions.V7


def test_prove_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._zk_cred", None)
    with pytest.raises(BackendUnavailableError, match="build_isrg_backend"):
        isrg.BACKEND.prove(_dummy_handle(), b"", (1, 2), b"", _one_attr(), _AWARE)


def test_verify_reports_unavailable_backend(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow.backends._zk_cred", None)
    with pytest.raises(BackendUnavailableError, match="build_isrg_backend"):
        isrg.BACKEND.verify(_dummy_handle(), (1, 2), b"", _one_attr(), _AWARE, b"", "doc", b"\xa0")


@pytest.mark.slow
@skip_without_isrg
def test_round_trip_verifies(isrg_client, isrg_handle, isrg_proof, vendored_vector):
    v = vendored_vector
    assert isrg_proof
    isrg_client.verify(
        isrg_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        isrg_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )


@pytest.mark.slow
@skip_without_isrg
def test_verify_rejects_tampered_proof(isrg_client, isrg_handle, isrg_proof, vendored_vector):
    v = vendored_vector
    tampered = bytearray(isrg_proof)
    tampered[100] ^= 0xFF
    with pytest.raises(mdoc.VerifierError) as excinfo:
        isrg_client.verify(
            isrg_handle,
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
@skip_without_isrg
def test_prove_rejects_unknown_claim(isrg_client, isrg_handle, vendored_vector):
    v = vendored_vector
    attrs = [dataclasses.replace(v.attrs[0], id="definitely_not_present")]
    with pytest.raises(mdoc.ProverError) as excinfo:
        isrg_client.prove(isrg_handle, v.mdoc_bytes, v.issuer_pk, v.transcript, attrs, v.timestamp)
    assert excinfo.value.code is None
    assert str(excinfo.value) == str(excinfo.value.__cause__)

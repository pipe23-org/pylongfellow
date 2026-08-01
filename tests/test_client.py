"""The Pylongfellow longfellow: backend binding, registry resolution, and dispatch."""

import sys
from datetime import UTC, datetime

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError, CircuitHandle, google_cpp

_AWARE = datetime(2024, 10, 1, 9, 0, 0, tzinfo=UTC)
_NAIVE = datetime(2024, 10, 1, 9, 0, 0)
_SPEC = mdoc.CircuitSpec("", "0" * 64, 1, 6, 0, 0)


class _RecordingBackend:
    """A Backend stub that records which operations were dispatched to it."""

    name: str = "stub"
    can_generate: bool = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    def ensure_available(self) -> None:
        self.calls.append("ensure_available")

    def load_circuit(self, spec: mdoc.CircuitSpec, compressed: bytes) -> CircuitHandle:
        self.calls.append("load_circuit")
        return CircuitHandle(spec=spec, backend=self, state=compressed)

    def generate_circuit(self, spec: mdoc.CircuitSpec) -> bytes:
        self.calls.append("generate_circuit")
        return b""

    def prove(
        self,
        handle: CircuitHandle,
        mdoc: bytes,
        issuer_pk: tuple[int, int],
        transcript: bytes,
        attrs: list[mdoc.RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        self.calls.append("prove")
        return b"proof"

    def verify(
        self,
        handle: CircuitHandle,
        issuer_pk: tuple[int, int],
        transcript: bytes,
        attrs: list[mdoc.RequestedAttribute],
        timestamp: datetime,
        proof: bytes,
        doctype: str,
        device_namespaces: bytes | None,
    ) -> None:
        self.calls.append("verify")


def test_registry_name_resolves_to_singleton():
    longfellow = Pylongfellow(backend="google-cpp")
    assert longfellow.backend is google_cpp.BACKEND


def test_backend_instance_is_bound_and_probed():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    assert longfellow.backend is stub
    assert stub.calls == ["ensure_available"]


def test_unknown_backend_name_lists_registered():
    with pytest.raises(
        ValueError, match=r"unknown backend 'nope' \(registered: google-cpp, isrg-rust\)"
    ):
        Pylongfellow(backend="nope")


def test_construction_reports_unbuilt_google_extension(monkeypatch):
    monkeypatch.setitem(sys.modules, "pylongfellow._longfellow", None)
    with pytest.raises(BackendUnavailableError, match="google-cpp"):
        Pylongfellow(backend="google-cpp")


def test_generate_circuit_routes_to_bound_backend():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    assert longfellow.generate_circuit(_SPEC) == b""
    assert stub.calls == ["ensure_available", "generate_circuit"]


def test_prove_and_verify_dispatch_through_handle_backend():
    # A handle loaded on one backend keeps its dispatch even on another
    # longfellow: prove/verify route through handle.backend, not longfellow.backend.
    loader, other = _RecordingBackend(), _RecordingBackend()
    handle = loader.load_circuit(_SPEC, b"")
    longfellow = Pylongfellow(backend=other)
    longfellow.prove(handle, b"", (1, 2), b"", [], _AWARE)
    longfellow.verify(handle, (1, 2), b"", [], _AWARE, b"", "doc")
    assert loader.calls == ["load_circuit", "prove", "verify"]
    assert other.calls == ["ensure_available"]


def test_prove_rejects_naive_timestamp():
    # The tz-aware check sits above backend dispatch: prove is never reached.
    backend = _RecordingBackend()
    handle = backend.load_circuit(_SPEC, b"")
    longfellow = Pylongfellow(backend=backend)
    with pytest.raises(ValueError, match="timezone-aware"):
        longfellow.prove(handle, b"", (1, 2), b"", [], _NAIVE)
    assert "prove" not in backend.calls


def test_verify_rejects_naive_timestamp():
    backend = _RecordingBackend()
    handle = backend.load_circuit(_SPEC, b"")
    longfellow = Pylongfellow(backend=backend)
    with pytest.raises(ValueError, match="timezone-aware"):
        longfellow.verify(handle, (1, 2), b"", [], _NAIVE, b"", "doc")
    assert "verify" not in backend.calls


def test_handle_carries_spec(google, mdoc_eu_av):
    handle = google.load_circuit(mdoc_eu_av.spec, mdoc_eu_av.circuit)
    assert handle.spec is mdoc_eu_av.spec
    assert handle.state == mdoc_eu_av.circuit


def test_load_circuit_rejects_hash_spec_mismatch(google, mdoc_eu_av):
    # A spec naming a different circuit than the bytes is rejected at load
    # (google-native identity check).
    wrong = google_cpp.find_zk_spec(
        "longfellow-libzk-v1",
        "137e5a75ce72735a37c8a72da1a8a0a5df8d13365c2ae3d2c2bd6a0e7197c7c6",  # v6, not the v7 circuit
    )
    assert wrong is not None
    with pytest.raises(ValueError, match="does not match the circuit"):
        google.load_circuit(wrong, mdoc_eu_av.circuit)


def test_google_error_populates_code(google, proof_age_over_18):
    inputs = proof_age_over_18
    handle = google.load_circuit(inputs.spec, inputs.circuit)
    bad_proof = bytearray(inputs.proof)
    bad_proof[len(bad_proof) // 2] ^= 0x01
    with pytest.raises(mdoc.VerifierError) as excinfo:
        google.verify(
            handle,
            inputs.issuer_pk,
            inputs.transcript,
            inputs.attrs,
            inputs.timestamp,
            bytes(bad_proof),
            inputs.doctype,
        )
    assert isinstance(excinfo.value.code, mdoc.VerifierErrorCode)


def test_device_namespaces_ignored_on_google_verify(google, proof_age_over_18):
    inputs = proof_age_over_18
    handle = google.load_circuit(inputs.spec, inputs.circuit)
    google.verify(
        handle,
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.proof,
        inputs.doctype,
        device_namespaces=b"\xa0",
    )

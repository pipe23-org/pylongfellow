"""Pylongfellow: backend selection, circuit loading, and what the loaded circuit gates."""

import sys
from datetime import UTC, datetime

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError, google_cpp

_AWARE = datetime(2024, 10, 1, 9, 0, 0, tzinfo=UTC)
_NAIVE = datetime(2024, 10, 1, 9, 0, 0)
_SPEC = mdoc.CircuitSpec("", "0" * 64, 1, 6, 0, 0)


class _RecordingBackend:
    """A Backend stub that records the operations called on it and the state it was given."""

    name: str = "stub"
    can_generate: bool = True

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.states: list[object] = []

    def ensure_available(self) -> None:
        self.calls.append("ensure_available")

    def load_circuit(self, spec: mdoc.CircuitSpec, circuit: bytes) -> object:
        self.calls.append("load_circuit")
        return circuit

    def generate_circuit(self, spec: mdoc.CircuitSpec) -> bytes:
        self.calls.append("generate_circuit")
        return b""

    def prove(
        self,
        state: object,
        mdoc: bytes,
        issuer_public_key: mdoc.PublicKey,
        transcript: bytes,
        claims: list[mdoc.RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        self.calls.append("prove")
        self.states.append(state)
        return b"proof"

    def verify(
        self,
        state: object,
        issuer_public_key: mdoc.PublicKey,
        transcript: bytes,
        claims: list[mdoc.RequestedAttribute],
        timestamp: datetime,
        proof: bytes,
        doctype: str,
        device_namespaces: bytes | None,
    ) -> None:
        self.calls.append("verify")
        self.states.append(state)


def test_registry_name_resolves_to_singleton():
    longfellow = Pylongfellow(backend="google-cpp")
    assert longfellow.backend is google_cpp.BACKEND


def test_backend_instance_is_bound_and_checked():
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


def test_prove_and_verify_run_on_the_loaded_circuit():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(_SPEC, b"circuit")
    longfellow.prove(b"", mdoc.PublicKey(1, 2), b"", [], _AWARE)
    longfellow.verify(mdoc.PublicKey(1, 2), b"", [], _AWARE, b"", "doc")
    assert stub.calls == ["ensure_available", "load_circuit", "prove", "verify"]
    assert stub.states == [b"circuit", b"circuit"]


def test_second_load_circuit_replaces_the_first():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(_SPEC, b"first")
    longfellow.load_circuit(_SPEC, b"second")
    longfellow.prove(b"", mdoc.PublicKey(1, 2), b"", [], _AWARE)
    assert stub.states == [b"second"]


def test_prove_without_a_loaded_circuit():
    longfellow = Pylongfellow(backend=_RecordingBackend())
    with pytest.raises(RuntimeError, match="no circuit is loaded"):
        longfellow.prove(b"", mdoc.PublicKey(1, 2), b"", [], _AWARE)


def test_verify_without_a_loaded_circuit():
    longfellow = Pylongfellow(backend=_RecordingBackend())
    with pytest.raises(RuntimeError, match="no circuit is loaded"):
        longfellow.verify(mdoc.PublicKey(1, 2), b"", [], _AWARE, b"", "doc")


def test_prove_rejects_naive_timestamp():
    # The tz-aware check sits above the backend call: prove is never reached.
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(_SPEC, b"")
    with pytest.raises(ValueError, match="timezone-aware"):
        longfellow.prove(b"", mdoc.PublicKey(1, 2), b"", [], _NAIVE)
    assert "prove" not in stub.calls


def test_verify_rejects_naive_timestamp():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(_SPEC, b"")
    with pytest.raises(ValueError, match="timezone-aware"):
        longfellow.verify(mdoc.PublicKey(1, 2), b"", [], _NAIVE, b"", "doc")
    assert "verify" not in stub.calls


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
    google.load_circuit(inputs.spec, inputs.circuit)
    bad_proof = bytearray(inputs.proof)
    bad_proof[len(bad_proof) // 2] ^= 0x01
    with pytest.raises(mdoc.VerifierError) as excinfo:
        google.verify(
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
    google.load_circuit(inputs.spec, inputs.circuit)
    google.verify(
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.proof,
        inputs.doctype,
        device_namespaces=b"\xa0",
    )

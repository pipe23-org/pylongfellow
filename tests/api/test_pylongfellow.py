import sys
from datetime import UTC, datetime

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError, google_cpp

_AWARE = datetime(2024, 10, 1, 9, 0, 0, tzinfo=UTC)
_NAIVE = datetime(2024, 10, 1, 9, 0, 0)


class _RecordingBackend:
    """A Backend stub that records the operations called on it and the state it was given."""

    name: str = "stub"

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.states: list[object] = []

    def ensure_available(self) -> None:
        self.calls.append("ensure_available")

    def load_circuit(self, circuit: bytes, version: int, num_attributes: int) -> object:
        self.calls.append("load_circuit")
        return circuit

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


def test_prove_and_verify_run_on_the_loaded_circuit():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(b"circuit", 0, 0)
    longfellow.prove(b"", mdoc.PublicKey(1, 2), b"", [], _AWARE)
    longfellow.verify(mdoc.PublicKey(1, 2), b"", [], _AWARE, b"", "doc")
    assert stub.calls == ["ensure_available", "load_circuit", "prove", "verify"]
    assert stub.states == [b"circuit", b"circuit"]


def test_second_load_circuit_replaces_the_first():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(b"first", 0, 0)
    longfellow.load_circuit(b"second", 0, 0)
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
    longfellow.load_circuit(b"", 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        longfellow.prove(b"", mdoc.PublicKey(1, 2), b"", [], _NAIVE)
    assert "prove" not in stub.calls


def test_verify_rejects_naive_timestamp():
    stub = _RecordingBackend()
    longfellow = Pylongfellow(backend=stub)
    longfellow.load_circuit(b"", 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        longfellow.verify(mdoc.PublicKey(1, 2), b"", [], _NAIVE, b"", "doc")
    assert "verify" not in stub.calls


def test_load_circuit_rejects_unknown_pair(google, mdoc_eu_av):
    # The table's counts run 1 to 4, so no row carries 9 attributes.
    with pytest.raises(ValueError, match="no compiled-in circuit"):
        google.load_circuit(mdoc_eu_av.circuit, 7, 9)


def test_google_error_populates_code(google, proof_age_over_18):
    inputs = proof_age_over_18
    google.load_circuit(inputs.circuit, inputs.version, inputs.num_attributes)
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
    google.load_circuit(inputs.circuit, inputs.version, inputs.num_attributes)
    google.verify(
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.proof,
        inputs.doctype,
        device_namespaces=b"\xa0",
    )

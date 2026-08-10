"""Embedded-id enforcement: what circuit_id, load, and a full prove/verify round trip
do with a circuit whose embedded id does not match its structure. The committed reject
vector is read as-is; the tamper is never constructed at test time. The entry in
README.md Recorded divergences carries the source citations."""

import json

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError, google_cpp, isrg_rust

from .conftest import CIRCUITS, PRESENTATIONS, REJECT_VECTORS_DIR, spec_of

_VECTOR_STEM = "v6-1attr-embedded-id-zeroed"
_VECTOR = (REJECT_VECTORS_DIR / f"{_VECTOR_STEM}.circuit").read_bytes()
_SIDECAR = json.loads((REJECT_VECTORS_DIR / f"{_VECTOR_STEM}.json").read_text())
_SPEC = spec_of(next(c for c in CIRCUITS if c.stem == _SIDECAR["derived_from"]))
_PRESENTATION = next(
    p
    for p in PRESENTATIONS
    if len(p.attrs) == 1 and p.mdoc_bytes is not None and p.device_namespaces is not None
)

_ISRG_UNCHECKED = pytest.mark.xfail(
    strict=True,
    reason="isrg-rust's decode reads the embedded id without checking it "
    "(src/circuit.rs:71 @ b22d84e); the check exists only in the test-only "
    "check_invariants (circuit.rs:459-465)",
)


def _round_trip(backend: str, mdoc_bytes: bytes) -> None:
    p = _PRESENTATION
    longfellow = Pylongfellow(backend=backend)
    longfellow.load_circuit(_SPEC, _VECTOR)
    proof = longfellow.prove(mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
    longfellow.verify(
        p.issuer_pk,
        p.transcript,
        p.attrs,
        p.timestamp,
        proof,
        p.doctype,
        device_namespaces=p.device_namespaces,
    )


def test_google_cpp_circuit_id_rejects_bad_circuit_id():
    with pytest.raises(mdoc.Error):
        google_cpp.circuit_id(_VECTOR)


@pytest.mark.slow
@_ISRG_UNCHECKED
def test_isrg_rust_circuit_id_rejects_bad_circuit_id():
    try:
        with pytest.raises(mdoc.Error):
            isrg_rust.circuit_id(_VECTOR)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")


def test_google_cpp_load_rejects_bad_circuit_id():
    with pytest.raises(mdoc.Error):
        Pylongfellow(backend="google-cpp").load_circuit(_SPEC, _VECTOR)


@pytest.mark.slow
@_ISRG_UNCHECKED
def test_isrg_rust_load_rejects_bad_circuit_id():
    try:
        with pytest.raises(mdoc.Error):
            Pylongfellow(backend="isrg-rust").load_circuit(_SPEC, _VECTOR)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")


def test_google_cpp_round_trip_rejects_bad_circuit_id():
    mdoc_bytes = _PRESENTATION.mdoc_bytes
    assert mdoc_bytes is not None
    with pytest.raises(mdoc.Error):
        _round_trip("google-cpp", mdoc_bytes)


@pytest.mark.slow
@_ISRG_UNCHECKED
def test_isrg_rust_round_trip_rejects_bad_circuit_id():
    mdoc_bytes = _PRESENTATION.mdoc_bytes
    assert mdoc_bytes is not None
    try:
        with pytest.raises(mdoc.Error):
            _round_trip("isrg-rust", mdoc_bytes)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")

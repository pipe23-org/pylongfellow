"""Corpus integrity: sidecar presence, byte hashes, and cross-references, every run.

circuit_id claims are verified at admission by scripts/admit.py, not here; the
byte_sha256 checks pin the artifacts instead.
"""

import hashlib

from .conftest import CIRCUITS, CIRCUITS_DIR, PRESENTATIONS, PRESENTATIONS_DIR

_CIRCUITS_BY_ID = {c.circuit_id: c for c in CIRCUITS}


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_corpus_is_not_empty():
    assert CIRCUITS
    assert PRESENTATIONS


def test_every_circuit_has_a_sidecar():
    for path in CIRCUITS_DIR.glob("*.circuit"):
        assert path.with_suffix(".json").is_file(), f"{path.name} has no sidecar"


def test_every_proof_has_a_sidecar():
    for path in PRESENTATIONS_DIR.glob("*/*.proof"):
        assert path.with_suffix(".json").is_file(), f"{path.name} has no sidecar"


def test_circuit_byte_hashes_match():
    for circuit in CIRCUITS:
        assert _sha256(circuit.path) == circuit.byte_sha256, circuit.stem


def test_proof_byte_hashes_match():
    for presentation in PRESENTATIONS:
        for proof in presentation.proofs:
            assert _sha256(proof.path) == proof.sidecar["byte_sha256"], proof.path.name


def test_every_proof_references_an_admitted_circuit():
    for presentation in PRESENTATIONS:
        for proof in presentation.proofs:
            circuit = _CIRCUITS_BY_ID.get(proof.circuit_id)
            assert circuit is not None, f"{proof.path.name} references an unadmitted circuit"
            assert proof.sidecar["circuit_byte_sha256"] == circuit.byte_sha256, proof.path.name


def test_every_presentation_pairs_with_an_admitted_circuit():
    counts = {c.num_attributes for c in CIRCUITS}
    for presentation in PRESENTATIONS:
        assert len(presentation.attrs) in counts, f"{presentation.slug} pairs with no circuit"


def test_presentations_with_mdoc_carry_device_namespaces():
    for presentation in PRESENTATIONS:
        if presentation.mdoc_bytes is not None:
            assert presentation.device_namespaces is not None, presentation.slug

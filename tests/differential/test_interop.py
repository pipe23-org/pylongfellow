"""Interop relationship tests over the corpus join.

Every case asserts both directions of the pass criteria: the valid proof is
accepted and a corrupted copy of it is rejected. The parametrizations come
from the conftest join, computed over the backend set.
"""

import pytest

from pylongfellow import mdoc

from .conftest import ROUND_TRIP_PARAMS, VERIFY_PARAMS, RoundTripCase, VerifyCase


def _corrupted(proof: bytes) -> bytes:
    flipped = bytearray(proof)
    flipped[len(flipped) // 2] ^= 0x01
    return bytes(flipped)


def _verify(longfellow, handle, case, proof: bytes) -> None:
    p = case.presentation
    longfellow.verify(
        handle,
        p.issuer_pk,
        p.transcript,
        p.attrs,
        p.timestamp,
        proof,
        p.doctype,
        device_namespaces=p.device_namespaces,
    )


@pytest.mark.parametrize("case", VERIFY_PARAMS)
def test_committed_proof(case: VerifyCase, longfellow_for, handle_for):
    verifier = longfellow_for(case.verifier)
    handle = handle_for(case.verifier, case.circuit)
    proof = case.proof.path.read_bytes()
    _verify(verifier, handle, case, proof)
    with pytest.raises(mdoc.VerifierError):
        _verify(verifier, handle, case, _corrupted(proof))


@pytest.mark.parametrize("case", ROUND_TRIP_PARAMS)
def test_round_trip(case: RoundTripCase, longfellow_for, handle_for):
    p = case.presentation
    mdoc_bytes = p.mdoc_bytes
    assert mdoc_bytes is not None  # a presentation without mdoc bytes is skipped as untestable
    prover = longfellow_for(case.prover)
    prove_handle = handle_for(case.prover, case.circuit)
    proof = prover.prove(prove_handle, mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
    assert proof
    verifier = longfellow_for(case.verifier)
    verify_handle = handle_for(case.verifier, case.circuit)
    _verify(verifier, verify_handle, case, proof)
    with pytest.raises(mdoc.VerifierError):
        _verify(verifier, verify_handle, case, _corrupted(proof))

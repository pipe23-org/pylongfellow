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


def _verify(client, handle, case, proof: bytes) -> None:
    p = case.presentation
    client.verify(
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
def test_committed_proof(case: VerifyCase, client_for, handle_for):
    client = client_for(case.verifier)
    handle = handle_for(case.verifier, case.circuit)
    proof = case.proof.path.read_bytes()
    _verify(client, handle, case, proof)
    with pytest.raises(mdoc.VerifierError):
        _verify(client, handle, case, _corrupted(proof))


@pytest.mark.parametrize("case", ROUND_TRIP_PARAMS)
def test_round_trip(case: RoundTripCase, client_for, handle_for):
    p = case.presentation
    mdoc_bytes = p.mdoc_bytes
    assert mdoc_bytes is not None  # the join only emits round trips for presentations with an mdoc
    prover_client = client_for(case.prover)
    prove_handle = handle_for(case.prover, case.circuit)
    proof = prover_client.prove(
        prove_handle, mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp
    )
    assert proof
    verifier_client = client_for(case.verifier)
    verify_handle = handle_for(case.verifier, case.circuit)
    _verify(verifier_client, verify_handle, case, proof)
    with pytest.raises(mdoc.VerifierError):
        _verify(verifier_client, verify_handle, case, _corrupted(proof))

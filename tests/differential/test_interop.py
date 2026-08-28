"""Interop relationship tests over the collection join.

A valid case asserts both directions of the pass criteria: the proof is
accepted and a corrupted copy of it is rejected. The parametrizations come
from the conftest join, computed over the backend set.
"""

import pytest

from pylongfellow import mdoc

from .conftest import (
    BIT_FLIPPED_PARAMS,
    DISCLOSED_CLAIMS,
    ROUND_TRIP_PARAMS,
    VECTORS,
    VERIFICATION_TIMES,
    VERIFY_PARAMS,
    RoundTripCase,
    VerifyCase,
)


def _corrupted(proof: bytes) -> bytes:
    flipped = bytearray(proof)
    flipped[len(flipped) // 2] ^= 0x01
    return bytes(flipped)


def _verify(longfellow, public_inputs, claims, timestamp, proof: bytes) -> None:
    longfellow.verify(
        mdoc.PublicKey(public_inputs.issuer_public_key.x, public_inputs.issuer_public_key.y),
        public_inputs.transcript,
        claims,
        timestamp,
        proof,
        public_inputs.doctype,
        device_namespaces=public_inputs.device_namespaces,
    )


@pytest.mark.parametrize("case", VERIFY_PARAMS)
def test_committed_proof(case: VerifyCase, longfellow_for):
    proof = VECTORS.proof(case.proof)
    assert proof.circuit is not None, f"proof {case.proof} references no circuit"
    statement = proof.statement()
    claims = [mdoc.RequestedAttribute(c.namespace, c.id, c.cbor_value) for c in statement.claims]
    verifier = longfellow_for(case.verifier, proof.circuit)
    _verify(verifier, statement, claims, statement.timestamp, proof.bytes)
    with pytest.raises(mdoc.VerifierError):
        _verify(verifier, statement, claims, statement.timestamp, _corrupted(proof.bytes))


@pytest.mark.parametrize("case", BIT_FLIPPED_PARAMS)
def test_bit_flipped_proof(case: VerifyCase, longfellow_for):
    proof = VECTORS.proof(case.proof)
    assert proof.circuit is not None, f"proof {case.proof} references no circuit"
    statement = proof.statement()
    claims = [mdoc.RequestedAttribute(c.namespace, c.id, c.cbor_value) for c in statement.claims]
    verifier = longfellow_for(case.verifier, proof.circuit)
    with pytest.raises(mdoc.VerifierError):
        _verify(verifier, statement, claims, statement.timestamp, proof.bytes)


@pytest.mark.parametrize("case", ROUND_TRIP_PARAMS)
def test_round_trip(case: RoundTripCase, longfellow_for):
    circuit = VECTORS.circuit(case.circuit)
    presentation = VECTORS.presentation(case.presentation)
    assert presentation.issuer_public_key is not None, (
        f"presentation {case.presentation} records no issuer public key"
    )
    assert presentation.transcript is not None, (
        f"presentation {case.presentation} records no transcript"
    )
    disclosed = {claim.id: claim for claim in presentation.claims()}
    claims = [
        mdoc.RequestedAttribute(disclosed[name].namespace, name, disclosed[name].cbor_value)
        for name in DISCLOSED_CLAIMS[case.presentation][circuit.num_attributes]
    ]
    issuer_pk = mdoc.PublicKey(presentation.issuer_public_key.x, presentation.issuer_public_key.y)
    timestamp = VERIFICATION_TIMES[case.presentation]
    prover = longfellow_for(case.prover, circuit)
    proof = prover.prove(presentation.mdoc, issuer_pk, presentation.transcript, claims, timestamp)
    assert proof
    verifier = longfellow_for(case.verifier, circuit)
    _verify(verifier, presentation, claims, timestamp, proof)
    with pytest.raises(mdoc.VerifierError):
        _verify(verifier, presentation, claims, timestamp, _corrupted(proof))

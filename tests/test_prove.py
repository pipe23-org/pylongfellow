"""Prove from a real upstream mdoc: the round trip, and the rejections."""

import dataclasses

import cbor2
import pytest

import pylongfellow as lf


def _prove(inputs):
    return lf.prove(
        inputs.circuit,
        inputs.mdoc,
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.spec,
    )


def _attr(inputs, **changes):
    return dataclasses.replace(inputs, attrs=[dataclasses.replace(inputs.attrs[0], **changes)])


def test_prove_then_verify(mdoc_eu_av):
    inputs = mdoc_eu_av
    proof = _prove(inputs)
    assert proof
    # The proof we just made must verify against the same inputs.
    lf.verify(
        inputs.circuit,
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        proof,
        inputs.doctype,
        inputs.spec,
    )


# prove() must reject every input it validates. (The transcript it only binds,
# so a tampered transcript would still prove — that's a verify-side failure,
# not here.)
@pytest.mark.parametrize(
    "mutate",
    [
        lambda inputs: dataclasses.replace(
            inputs, mdoc=inputs.mdoc[: len(inputs.mdoc) // 2]
        ),  # truncated
        lambda inputs: dataclasses.replace(
            inputs, issuer_pk=(inputs.issuer_pk[1], inputs.issuer_pk[0])
        ),
        lambda inputs: dataclasses.replace(inputs, timestamp=inputs.timestamp.replace(year=2020)),
        lambda inputs: _attr(inputs, id="definitely_not_present"),
        lambda inputs: _attr(inputs, cbor_value=cbor2.dumps(False)),
    ],
    ids=["mdoc", "pubkey", "timestamp", "id", "value"],
)
def test_prove_rejects(mdoc_eu_av, mutate):
    with pytest.raises(lf.ProverError):
        _prove(mutate(mdoc_eu_av))


def test_prove_rejects_spec_for_wrong_circuit(mdoc_eu_av):
    # A spec naming a different circuit must be a clean ValueError, not the
    # upstream SIGABRT (the binding's spec<->circuit guard).
    wrong = lf.find_zk_spec(
        "longfellow-libzk-v1",
        "137e5a75ce72735a37c8a72da1a8a0a5df8d13365c2ae3d2c2bd6a0e7197c7c6",  # v6, not the v7 circuit
    )
    with pytest.raises(ValueError, match="does not match the circuit"):
        _prove(dataclasses.replace(mdoc_eu_av, spec=wrong))

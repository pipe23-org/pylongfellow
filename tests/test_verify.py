"""verify() against a real upstream proof — the positive case and the rejections."""

import dataclasses

import cbor2
import pytest

import pylongfellow as lf


def _verify(inputs):
    lf.verify(
        inputs.circuit,
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.proof,
        inputs.doctype,
        inputs.spec,
    )


def test_verify_proof_age_over_18(proof_age_over_18):
    _verify(proof_age_over_18)  # returns None on success, raises VerifierError on failure


def _flip(data: bytes) -> bytes:
    buf = bytearray(data)
    buf[len(buf) // 2] ^= 0x01
    return bytes(buf)


def _attr(inputs, **changes):
    return dataclasses.replace(inputs, attrs=[dataclasses.replace(inputs.attrs[0], **changes)])


# Each case breaks one input verify() must depend on, checking the binding
# surfaces the rejection rather than silently accepting.
@pytest.mark.parametrize(
    "mutate",
    [
        lambda inputs: dataclasses.replace(inputs, proof=_flip(inputs.proof)),
        lambda inputs: dataclasses.replace(
            inputs, issuer_pk=(inputs.issuer_pk[1], inputs.issuer_pk[0])
        ),
        lambda inputs: dataclasses.replace(inputs, transcript=_flip(inputs.transcript)),
        lambda inputs: dataclasses.replace(inputs, timestamp=inputs.timestamp.replace(year=2024)),
        lambda inputs: _attr(inputs, cbor_value=cbor2.dumps(False)),
        lambda inputs: _attr(inputs, id="age_over_21"),
        lambda inputs: dataclasses.replace(
            inputs, spec=dataclasses.replace(inputs.spec, version=7)
        ),
    ],
    ids=["proof", "pubkey", "transcript", "timestamp", "value", "id", "spec"],
)
def test_verify_rejects(proof_age_over_18, mutate):
    with pytest.raises(lf.VerifierError):
        _verify(mutate(proof_age_over_18))


def test_verify_rejects_spec_for_wrong_circuit(proof_age_over_18):
    # A spec naming a different circuit must be a clean ValueError (spec<->circuit guard).
    wrong = lf.find_zk_spec(
        "longfellow-libzk-v1",
        "8d079211715200ff06c5109639245502bfe94aa869908d31176aae4016182121",  # v7, not the v6 circuit
    )
    with pytest.raises(ValueError, match="does not match the circuit"):
        _verify(dataclasses.replace(proof_age_over_18, spec=wrong))

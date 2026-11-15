import dataclasses

import cbor2
import pytest

from pylongfellow import mdoc


def _verify(longfellow, inputs, device_namespaces=b"\xa0"):
    longfellow.load_circuit(inputs.circuit, inputs.version, inputs.num_attributes)
    longfellow.verify(
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.proof,
        inputs.doctype,
        device_namespaces=device_namespaces,
    )


def test_verify_proof_age_over_18(google, proof_age_over_18):
    _verify(google, proof_age_over_18)  # returns None on success, raises VerifierError on failure


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
            inputs, issuer_pk=mdoc.PublicKey(inputs.issuer_pk.y, inputs.issuer_pk.x)
        ),
        lambda inputs: dataclasses.replace(inputs, transcript=_flip(inputs.transcript)),
        lambda inputs: dataclasses.replace(inputs, timestamp=inputs.timestamp.replace(year=2024)),
        lambda inputs: _attr(inputs, cbor_value=cbor2.dumps(False)),
        lambda inputs: _attr(inputs, id="age_over_21"),
    ],
    ids=["proof", "pubkey", "transcript", "timestamp", "value", "id"],
)
def test_verify_rejects(google, proof_age_over_18, mutate):
    # A tampered Zk statement the C verifier rejects with VerifierError.
    with pytest.raises(mdoc.VerifierError):
        _verify(google, mutate(proof_age_over_18))


def test_verify_rejects_long_doctype(google, proof_age_over_18):
    # C silently substitutes a default doctype at >= 256 bytes; refuse instead.
    with pytest.raises(ValueError, match="doctype too long"):
        _verify(google, dataclasses.replace(proof_age_over_18, doctype="x" * 256))


@pytest.mark.parametrize("resize", [lambda a: a + a, lambda a: []], ids=["over", "under"])
def test_verify_rejects_attr_count_mismatch(google, proof_age_over_18, resize):
    inputs = proof_age_over_18
    with pytest.raises(ValueError, match="num_attributes"):
        _verify(google, dataclasses.replace(inputs, attrs=resize(inputs.attrs)))


def test_verify_rejects_non_empty_device_namespaces(google, proof_age_over_18):
    device_namespaces = cbor2.dumps({"org.iso.18013.5.1": {"age_over_18": True}})
    with pytest.raises(ValueError, match="device_namespaces must be the encoded empty map"):
        _verify(google, proof_age_over_18, device_namespaces)


def test_verify_rejects_device_namespaces_that_are_not_cbor(google, proof_age_over_18):
    with pytest.raises(ValueError, match="device_namespaces must be the encoded empty map"):
        _verify(google, proof_age_over_18, b"not cbor")

"""The mdoc facade: handles, backend resolution, and cpp error surfacing."""

import pytest

from pylongfellow import mdoc
from pylongfellow.backends import cpp


def test_handle_carries_spec(mdoc_eu_av):
    handle = mdoc.load_circuit(mdoc_eu_av.spec, mdoc_eu_av.circuit)
    assert handle.spec is mdoc_eu_av.spec
    assert handle.state == mdoc_eu_av.circuit


def test_default_backend_is_cpp(mdoc_eu_av):
    default = mdoc.load_circuit(mdoc_eu_av.spec, mdoc_eu_av.circuit)
    explicit = mdoc.load_circuit(mdoc_eu_av.spec, mdoc_eu_av.circuit, backend=cpp.BACKEND)
    assert default.backend is cpp.BACKEND
    assert explicit.backend is cpp.BACKEND


def test_load_circuit_rejects_hash_spec_mismatch(mdoc_eu_av):
    # A spec naming a different circuit than the bytes is rejected at load.
    wrong = mdoc.find_zk_spec(
        "longfellow-libzk-v1",
        "137e5a75ce72735a37c8a72da1a8a0a5df8d13365c2ae3d2c2bd6a0e7197c7c6",  # v6, not the v7 circuit
    )
    assert wrong is not None
    with pytest.raises(ValueError, match="does not match the circuit"):
        mdoc.load_circuit(wrong, mdoc_eu_av.circuit)


def test_cpp_error_populates_code(proof_age_over_18):
    inputs = proof_age_over_18
    handle = mdoc.load_circuit(inputs.spec, inputs.circuit)
    bad_proof = bytearray(inputs.proof)
    bad_proof[len(bad_proof) // 2] ^= 0x01
    with pytest.raises(mdoc.VerifierError) as excinfo:
        mdoc.verify(
            handle,
            inputs.issuer_pk,
            inputs.transcript,
            inputs.attrs,
            inputs.timestamp,
            bytes(bad_proof),
            inputs.doctype,
        )
    assert isinstance(excinfo.value.code, mdoc.VerifierErrorCode)


def test_device_namespaces_ignored_on_cpp_verify(proof_age_over_18):
    inputs = proof_age_over_18
    handle = mdoc.load_circuit(inputs.spec, inputs.circuit)
    mdoc.verify(
        handle,
        inputs.issuer_pk,
        inputs.transcript,
        inputs.attrs,
        inputs.timestamp,
        inputs.proof,
        inputs.doctype,
        device_namespaces=b"\xa0",
    )

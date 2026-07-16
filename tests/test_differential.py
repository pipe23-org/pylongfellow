"""Cross-backend agreement on the shared v6/1-attribute interop vector.

The cpp spec table registers the v6/1-attribute circuit (system longfellow-libzk-v1, hash
137e...), so the differential runs against the vendored `6_1_137e...` circuit.
"""

import pytest

from pylongfellow import mdoc

from .conftest import RUST_AVAILABLE

skip_without_rust = pytest.mark.skipif(not RUST_AVAILABLE, reason="rust backend not built")


def test_cpp_loads_vendored_circuit(cpp_handle, vendored_vector):
    assert cpp_handle.spec == vendored_vector.spec
    assert cpp_handle.state == vendored_vector.compressed


@pytest.mark.slow
@skip_without_rust
def test_cpp_prove_rust_verify(rust_handle, cpp_proof, vendored_vector):
    v = vendored_vector
    mdoc.verify(
        rust_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        cpp_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )


@pytest.mark.slow
@skip_without_rust
def test_rust_prove_cpp_verify(cpp_handle, rust_proof, vendored_vector):
    v = vendored_vector
    mdoc.verify(cpp_handle, v.issuer_pk, v.transcript, v.attrs, v.timestamp, rust_proof, v.doctype)


@pytest.mark.slow
@skip_without_rust
def test_both_backends_verify_cpp_interop_proof(cpp_handle, rust_handle, vendored_vector):
    v = vendored_vector
    mdoc.verify(
        cpp_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        v.cpp_interop_proof,
        v.doctype,
    )
    mdoc.verify(
        rust_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        v.cpp_interop_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )

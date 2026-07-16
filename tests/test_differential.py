"""Cross-backend agreement on the shared v6/1-attribute interop vector.

The google/longfellow-zk spec table registers the v6/1-attribute circuit (system
longfellow-libzk-v1, hash 137e...), so the differential runs against the vendored `6_1_137e...`
circuit.
"""

import pytest

from pylongfellow import mdoc

from .conftest import ISRG_AVAILABLE

skip_without_isrg = pytest.mark.skipif(not ISRG_AVAILABLE, reason="isrg backend not built")


def test_google_loads_vendored_circuit(google_handle, vendored_vector):
    assert google_handle.spec == vendored_vector.spec
    assert google_handle.state == vendored_vector.compressed


@pytest.mark.slow
@skip_without_isrg
def test_google_prove_isrg_verify(isrg_handle, google_proof, vendored_vector):
    v = vendored_vector
    mdoc.verify(
        isrg_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        google_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )


@pytest.mark.slow
@skip_without_isrg
def test_isrg_prove_google_verify(google_handle, isrg_proof, vendored_vector):
    v = vendored_vector
    mdoc.verify(
        google_handle, v.issuer_pk, v.transcript, v.attrs, v.timestamp, isrg_proof, v.doctype
    )


@pytest.mark.slow
@skip_without_isrg
def test_both_backends_verify_google_interop_proof(google_handle, isrg_handle, vendored_vector):
    v = vendored_vector
    mdoc.verify(
        google_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        v.google_interop_proof,
        v.doctype,
    )
    mdoc.verify(
        isrg_handle,
        v.issuer_pk,
        v.transcript,
        v.attrs,
        v.timestamp,
        v.google_interop_proof,
        v.doctype,
        device_namespaces=v.device_namespaces,
    )

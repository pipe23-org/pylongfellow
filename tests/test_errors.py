"""Each call's failure is a distinct exception carrying its own code enum."""

import pylongfellow as lf


def test_subclasses_share_base():
    for exc in (lf.ProverError, lf.VerifierError, lf.CircuitError):
        assert issubclass(exc, lf.LongfellowError)


def test_error_carries_its_code():
    err = lf.VerifierError(lf.MdocVerifierErrorCode.MDOC_VERIFIER_INVALID_CBOR)
    assert err.code is lf.MdocVerifierErrorCode.MDOC_VERIFIER_INVALID_CBOR
    assert "MDOC_VERIFIER_INVALID_CBOR" in str(err)

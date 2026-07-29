"""Each call's failure is a distinct exception carrying its own code enum."""

import pytest

import pylongfellow
from pylongfellow import mdoc

# (concrete exception, its .code enum)
_CONCRETES = [
    (mdoc.ProverError, mdoc.ProverErrorCode),
    (mdoc.VerifierError, mdoc.VerifierErrorCode),
    (mdoc.CircuitError, mdoc.CircuitGenerationErrorCode),
]


def test_error_carries_its_code():
    err = mdoc.VerifierError(mdoc.VerifierErrorCode.MDOC_VERIFIER_INVALID_CBOR)
    assert err.code is mdoc.VerifierErrorCode.MDOC_VERIFIER_INVALID_CBOR
    assert "MDOC_VERIFIER_INVALID_CBOR" in str(err)


def test_error_default_message_without_code():
    assert str(mdoc.ProverError()) == "prover call failed"
    assert str(mdoc.VerifierError()) == "verifier call failed"
    assert mdoc.ProverError().code is None


@pytest.mark.parametrize("exc", [mdoc.ProverError, mdoc.VerifierError], ids=["prover", "verifier"])
def test_error_preserves_backend_message(exc):
    err = exc(message="upstream detail")
    assert str(err) == "upstream detail"
    assert err.code is None


@pytest.mark.parametrize(("exc", "code_enum"), _CONCRETES, ids=["prover", "verifier", "circuit"])
def test_catch_contract(exc, code_enum):
    # The public catch contract: each concrete is reachable through both bases,
    # and .code is the matching enum. A silent re-parenting breaks downstream
    # `except` sites that neither mypy nor the behavioral tests would catch.
    err = exc(next(iter(code_enum)))
    assert isinstance(err, mdoc.Error)
    assert isinstance(err, pylongfellow.LongfellowError)
    assert isinstance(err, (mdoc.ProverError, mdoc.VerifierError, mdoc.CircuitError))
    assert isinstance(err.code, code_enum)

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


def test_top_level_drops_moved_names():
    # The break, locked in: nothing that moved to .mdoc is reachable from the top.
    for name in (
        "prove",
        "verify",
        "generate_circuit",
        "circuit_id",
        "find_zk_spec",
        "RequestedAttribute",
        "ZkSpec",
        "ProverError",
        "VerifierError",
        "CircuitError",
        "MdocProverErrorCode",
        "MdocVerifierErrorCode",
        "CircuitGenerationErrorCode",
    ):
        assert not hasattr(pylongfellow, name)

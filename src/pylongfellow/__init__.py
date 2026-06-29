"""Python bindings for the [longfellow-zk](https://github.com/google/longfellow-zk) mdoc prover and verifier."""

from importlib.metadata import version

from ._errors import (
    CircuitError,
    CircuitGenerationErrorCode,
    LongfellowError,
    MdocProverErrorCode,
    MdocVerifierErrorCode,
    ProverError,
    VerifierError,
)
from ._native import circuit_id, find_zk_spec, generate_circuit, prove, verify
from ._types import RequestedAttribute, ZkSpec

__version__ = version("pylongfellow")

__all__ = [
    "CircuitError",
    "CircuitGenerationErrorCode",
    "LongfellowError",
    "MdocProverErrorCode",
    "MdocVerifierErrorCode",
    "ProverError",
    "RequestedAttribute",
    "VerifierError",
    "ZkSpec",
    "__version__",
    "circuit_id",
    "find_zk_spec",
    "generate_circuit",
    "prove",
    "verify",
]

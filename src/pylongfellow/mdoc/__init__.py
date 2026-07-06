"""The mdoc-specific functions, data types, and errors from longfellow-zk."""

from ._errors import (
    CircuitError,
    CircuitGenerationErrorCode,
    Error,
    ProverError,
    ProverErrorCode,
    VerifierError,
    VerifierErrorCode,
)
from ._native import circuit_id, find_zk_spec, generate_circuit, prove, verify
from ._types import RequestedAttribute, ZkSpec

__all__ = [
    "CircuitError",
    "CircuitGenerationErrorCode",
    "Error",
    "ProverError",
    "ProverErrorCode",
    "RequestedAttribute",
    "VerifierError",
    "VerifierErrorCode",
    "ZkSpec",
    "circuit_id",
    "find_zk_spec",
    "generate_circuit",
    "prove",
    "verify",
]

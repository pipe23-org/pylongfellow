"""The mdoc-specific functions from longfellow-zk — proving, verifying, circuit generation.

Also the data types they take and the errors they raise.
"""

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

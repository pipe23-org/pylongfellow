"""Data types and errors for proving and verifying mdoc credentials."""

from ..backends import CircuitHandle
from ._errors import (
    CircuitError,
    CircuitGenerationErrorCode,
    Error,
    ProverError,
    ProverErrorCode,
    VerifierError,
    VerifierErrorCode,
)
from ._types import CircuitSpec, RequestedAttribute

__all__ = [
    "CircuitError",
    "CircuitGenerationErrorCode",
    "CircuitHandle",
    "CircuitSpec",
    "Error",
    "ProverError",
    "ProverErrorCode",
    "RequestedAttribute",
    "VerifierError",
    "VerifierErrorCode",
]

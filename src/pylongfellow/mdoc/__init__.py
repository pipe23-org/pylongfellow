"""The mdoc-specific data types and errors from longfellow-zk.

`create_credential` and its companion functions construct test credentials
without touching longfellow-zk; they run on `cryptography` and `cbor2` alone.
"""

from ..backends import CircuitHandle
from ._credential import (
    CreatedCredential,
    create_certificate,
    create_credential,
    sign_device_authentication,
    verify_device_authentication,
)
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
    "CreatedCredential",
    "Error",
    "ProverError",
    "ProverErrorCode",
    "RequestedAttribute",
    "VerifierError",
    "VerifierErrorCode",
    "create_certificate",
    "create_credential",
    "sign_device_authentication",
    "verify_device_authentication",
]

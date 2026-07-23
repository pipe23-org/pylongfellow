"""The mdoc-specific data types, errors, and spec-table functions from longfellow-zk.

`create_credential` and its companion functions construct test credentials
without touching longfellow-zk; they run on `cryptography` and `cbor2` alone.
"""

from ..backends import CircuitHandle
from ..backends.google import circuit_id, find_zk_spec, zk_specs
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
from ._types import RequestedAttribute, ZkSpec

__all__ = [
    "CircuitError",
    "CircuitGenerationErrorCode",
    "CircuitHandle",
    "CreatedCredential",
    "Error",
    "ProverError",
    "ProverErrorCode",
    "RequestedAttribute",
    "VerifierError",
    "VerifierErrorCode",
    "ZkSpec",
    "circuit_id",
    "create_certificate",
    "create_credential",
    "find_zk_spec",
    "sign_device_authentication",
    "verify_device_authentication",
    "zk_specs",
]

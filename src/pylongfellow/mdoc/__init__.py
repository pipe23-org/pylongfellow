"""The mdoc-specific functions, data types, and errors from longfellow-zk.

`create_credential` and its companion functions construct test credentials
without touching longfellow-zk; they run on `cryptography` and `cbor2` alone.
"""

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
from ._native import circuit_id, find_zk_spec, generate_circuit, prove, verify, zk_specs
from ._types import RequestedAttribute, ZkSpec

__all__ = [
    "CircuitError",
    "CircuitGenerationErrorCode",
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
    "generate_circuit",
    "prove",
    "sign_device_authentication",
    "verify",
    "verify_device_authentication",
    "zk_specs",
]

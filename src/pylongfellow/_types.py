"""Plain-dataclass mirrors of the two C structs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestedAttribute:
    r"""A claim to prove or verify: attribute (namespace, id) holds cbor_value.

    Attributes:
        namespace: mdoc namespace the attribute lives in.
        id: Attribute identifier within the namespace.
        cbor_value: Raw CBOR encoding of the value (e.g. `b"\xf5"` for true).
    """

    namespace: str
    id: str
    cbor_value: bytes


@dataclass(frozen=True)
class ZkSpec:
    """A circuit's identity, agreed between prover and verifier.

    Attributes:
        system: ZK system name and version (e.g. `longfellow-libzk-v*`).
        circuit_hash: SHA-256 (hex) pinning which circuit this is.
        num_attributes: Number of attributes the circuit proves over.
        version: Version of the ZK specification.
        block_enc_hash: `block_enc` parameter for the proof (upstream field).
        block_enc_sig: `block_enc` parameter for the proof (upstream field).
    """

    system: str
    circuit_hash: str
    num_attributes: int
    version: int
    block_enc_hash: int
    block_enc_sig: int

"""Plain-dataclass request and key records.

`RequestedAttribute` mirrors the upstream C struct of the same name.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestedAttribute:
    r"""A claim to prove or verify: attribute (namespace, id) holds cbor_value.

    Attributes:
        namespace: The mdoc namespace of the attribute.
        id: Attribute identifier within the namespace.
        cbor_value: Raw CBOR encoding of the value (e.g. `b"\xf5"` for true).
    """

    namespace: str
    id: str
    cbor_value: bytes


@dataclass(frozen=True)
class PublicKey:
    """A public key, as coordinates `x` and `y`."""

    x: int
    y: int

"""Backend-agnostic core: the Backend protocol and the circuit handle it hands out."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .._errors import LongfellowError

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import RequestedAttribute, ZkSpec


class GenerationUnsupportedError(LongfellowError):
    """A backend whose `can_generate` is False was asked to generate a circuit."""


@dataclass(frozen=True)
class CircuitHandle:
    """A circuit loaded by a backend, ready for prove and verify.

    Attributes:
        spec: The ZkSpec the circuit was loaded against.
        backend: The backend that loaded the circuit and runs its operations.
        state: Backend-private circuit state, opaque to callers; a backend may
            hold expensive parsed state here, so cache the handle rather than
            reloading the circuit per call.
    """

    spec: ZkSpec
    backend: Backend
    state: object


class Backend(Protocol):
    """A proving and verifying implementation for longfellow mdoc circuits."""

    name: str
    can_generate: bool

    def load_circuit(self, spec: ZkSpec, compressed: bytes) -> CircuitHandle:
        """Bind a compressed circuit to this backend as a CircuitHandle."""

    def generate_circuit(self, spec: ZkSpec) -> bytes:
        """Generate the compressed circuit named by spec."""

    def prove(
        self,
        handle: CircuitHandle,
        mdoc: bytes,
        issuer_pk: tuple[int, int],
        transcript: bytes,
        attrs: list[RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        """Prove the requested attributes over the mdoc, bound to the transcript."""

    def verify(
        self,
        handle: CircuitHandle,
        issuer_pk: tuple[int, int],
        transcript: bytes,
        attrs: list[RequestedAttribute],
        timestamp: datetime,
        proof: bytes,
        doctype: str,
        device_namespaces: bytes | None,
    ) -> None:
        """Verify a proof of the requested attributes against the transcript."""


__all__ = [
    "Backend",
    "CircuitHandle",
    "GenerationUnsupportedError",
]

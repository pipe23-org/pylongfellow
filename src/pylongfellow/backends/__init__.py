"""Backend-agnostic core: the Backend protocol and the CircuitHandle it returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .._errors import LongfellowError

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import CircuitSpec, RequestedAttribute


class GenerationUnsupportedError(LongfellowError):
    """A backend whose `can_generate` is False was asked to generate a circuit."""


class BackendUnavailableError(LongfellowError):
    """A backend's native dependency is not installed or built."""


@dataclass(frozen=True)
class CircuitHandle:
    """A circuit loaded by a backend, ready for prove and verify.

    Attributes:
        spec: The CircuitSpec the circuit was loaded against.
        backend: The backend that loaded the circuit and runs its operations.
        state: Backend-private circuit state, opaque to callers; a backend may
            hold expensive parsed state here, so cache the handle rather than
            reloading the circuit per call.
    """

    spec: CircuitSpec
    backend: Backend
    state: object


class Backend(Protocol):
    """A proving and verifying implementation for longfellow mdoc circuits."""

    name: str
    can_generate: bool

    def ensure_available(self) -> None:
        """Raise BackendUnavailableError unless the backend's native dependency is built."""

    def load_circuit(self, spec: CircuitSpec, compressed: bytes) -> CircuitHandle:
        """Load a compressed circuit and return a CircuitHandle."""

    def generate_circuit(self, spec: CircuitSpec) -> bytes:
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
        """Prove the requested attributes over the mdoc, bound to the transcript.

        `timestamp` is timezone-aware. `Pylongfellow` rejects naive datetimes before the
        backend is called.
        """

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
        """Verify a proof of the requested attributes against the transcript.

        `timestamp` is timezone-aware. `Pylongfellow` rejects naive datetimes before the
        backend is called.
        """


def _google_backend() -> Backend:
    from . import google_cpp

    return google_cpp.BACKEND


def _isrg_rust_backend() -> Backend:
    from . import isrg_rust

    return isrg_rust.BACKEND


# Registry names distinguish implementation, not just institution: google ships
# a second (Rust) implementation upstream, so "google-rust" is reserved.
_REGISTRY = {
    "google-cpp": _google_backend,
    "isrg-rust": _isrg_rust_backend,
}


def get_backend(name: str) -> Backend:
    """Return the registered backend singleton for a registry name.

    Args:
        name: Registry name, one of `google-cpp` or `isrg-rust`.

    Returns:
        The backend singleton. [`Pylongfellow`][pylongfellow.Pylongfellow]
            checks availability at construction.

    Raises:
        ValueError: `name` is not a registered backend name.
    """
    try:
        loader = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown backend {name!r} (registered: {', '.join(sorted(_REGISTRY))})"
        ) from None
    return loader()


__all__ = [
    "Backend",
    "BackendUnavailableError",
    "CircuitHandle",
    "GenerationUnsupportedError",
    "get_backend",
]

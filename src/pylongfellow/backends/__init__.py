"""Backend-agnostic core: the Backend protocol, its errors, and the registry of backend names."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .._errors import LongfellowError

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import CircuitSpec, PublicKey, RequestedAttribute


class GenerationUnsupportedError(LongfellowError):
    """A backend whose `can_generate` is False was asked to generate a circuit."""


class BackendUnavailableError(LongfellowError):
    """A backend's native dependency is not installed or built."""


class Backend(Protocol):
    """The operations a backend provides."""

    name: str
    can_generate: bool

    def ensure_available(self) -> None:
        """Raise BackendUnavailableError unless the backend's native dependency is built."""

    def load_circuit(self, spec: CircuitSpec, circuit: bytes) -> object:
        """Load a circuit and return the state prove and verify take.

        The state's type is the backend's own. `Pylongfellow` holds it between calls, so
        a backend may put expensive parsed state in it.
        """

    def generate_circuit(self, spec: CircuitSpec) -> bytes:
        """Generate the circuit named by spec."""

    def prove(
        self,
        state: object,
        mdoc: bytes,
        issuer_public_key: PublicKey,
        transcript: bytes,
        claims: list[RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        """Prove the claims over the mdoc, bound to the transcript.

        `state` comes from this backend's `load_circuit`. `timestamp` is timezone-aware:
        `Pylongfellow` rejects naive datetimes before the backend is called.
        """

    def verify(
        self,
        state: object,
        issuer_public_key: PublicKey,
        transcript: bytes,
        claims: list[RequestedAttribute],
        timestamp: datetime,
        proof: bytes,
        doctype: str,
        device_namespaces: bytes | None,
    ) -> None:
        """Verify a proof of the claims against the transcript.

        `state` comes from this backend's `load_circuit`. `timestamp` is timezone-aware:
        `Pylongfellow` rejects naive datetimes before the backend is called.
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
    """Return the named backend.

    Args:
        name: Registry name, one of `google-cpp` or `isrg-rust`.

    Returns:
        The named backend.

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
    "GenerationUnsupportedError",
    "get_backend",
]

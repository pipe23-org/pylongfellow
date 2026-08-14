"""Backend-agnostic core: the Backend protocol, its errors, and the registry of backend names."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Protocol, cast

from .._errors import LongfellowError

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import CircuitSpec, PublicKey, RequestedAttribute


class GenerationUnsupportedError(LongfellowError):
    """A backend whose `can_generate` is False was asked to generate a circuit."""


class CircuitIdUnsupportedError(LongfellowError):
    """A backend that does not implement circuit id recomputation was asked for one."""


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

        The state's type is the backend's own; `prove` and `verify` take it back as
        `state`, so a backend may put expensive parsed state in it.
        """

    def generate_circuit(self, spec: CircuitSpec) -> bytes:
        """Generate the circuit identified by `spec`."""

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


# Registry names distinguish implementation, not just institution: google ships
# a second (Rust) implementation upstream, so "google-rust" is reserved.
_REGISTRY = {
    "google-cpp": "pylongfellow.backends.google_cpp",
    "isrg-rust": "pylongfellow.backends.isrg_rust",
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
        module = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown backend {name!r} (registered: {', '.join(sorted(_REGISTRY))})"
        ) from None
    return cast("Backend", importlib.import_module(module).BACKEND)


__all__ = [
    "Backend",
    "BackendUnavailableError",
    "CircuitIdUnsupportedError",
    "GenerationUnsupportedError",
    "get_backend",
]

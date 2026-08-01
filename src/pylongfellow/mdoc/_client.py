"""The Pylongfellow client: circuit operations on a backend bound at construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..backends import Backend, CircuitHandle, get_backend

if TYPE_CHECKING:
    from datetime import datetime

    from ._types import CircuitSpec, RequestedAttribute


class Pylongfellow:
    """Circuit operations over one implementation, selected at construction.

    Attributes:
        backend: The selected [`Backend`][pylongfellow.backends.Backend].
    """

    backend: Backend

    def __init__(self, *, backend: str | Backend) -> None:
        """Select a backend and probe its availability.

        Args:
            backend: Registry name (`google-cpp` or `isrg-rust`) or a Backend
                instance.

        Raises:
            ValueError: `backend` is not a registered backend name.
            BackendUnavailableError: the backend's native dependency is not
                installed or built.
        """
        self.backend = get_backend(backend) if isinstance(backend, str) else backend
        self.backend.ensure_available()

    def load_circuit(self, spec: CircuitSpec, compressed: bytes) -> CircuitHandle:
        """Load a compressed circuit into the bound backend and return a handle over it.

        Args:
            spec: CircuitSpec naming the circuit.
            compressed: Compressed circuit bytes, as from
                [`generate_circuit`][pylongfellow.Pylongfellow.generate_circuit].

        Returns:
            A CircuitHandle to pass to [`prove`][pylongfellow.Pylongfellow.prove]
            and [`verify`][pylongfellow.Pylongfellow.verify].

        Raises:
            ValueError: `spec` is rejected by the backend, e.g. it is not
                registered or names a different circuit than `compressed`
                (google-cpp), or its version is unsupported (isrg-rust).
        """
        return self.backend.load_circuit(spec, compressed)

    def generate_circuit(self, spec: CircuitSpec) -> bytes:
        """Generate a compressed circuit blob on the bound backend.

        Args:
            spec: CircuitSpec naming the circuit to generate.

        Returns:
            Compressed circuit bytes.

        Raises:
            ValueError: `spec` is not registered on the backend (google-cpp).
            CircuitError: Generation failed, e.g. an unsupported spec version (google-cpp).
            GenerationUnsupportedError: The backend cannot generate circuits (isrg-rust).
        """
        return self.backend.generate_circuit(spec)

    def prove(
        self,
        handle: CircuitHandle,
        mdoc: bytes,
        issuer_pk: tuple[int, int],
        transcript: bytes,
        attrs: list[RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        """Prove the requested attributes hold over the mdoc, bound to the transcript.

        Runs on the handle's backend, which may differ from this instance's
        when the handle was loaded elsewhere.

        Args:
            handle: A CircuitHandle from
                [`load_circuit`][pylongfellow.Pylongfellow.load_circuit].
            mdoc: CBOR-encoded mdoc credential.
            issuer_pk: Issuer public key, as `(x, y)`.
            transcript: Session transcript the proof is bound to.
            attrs: Attributes to prove; `len(attrs)` must equal
                `handle.spec.num_attributes`.
            timestamp: Timezone-aware verification time.

        Returns:
            Proof bytes.

        Raises:
            ValueError: `timestamp` is naive; `len(attrs)` does not match
                `handle.spec.num_attributes` (google-cpp); or `attrs` do not
                share one namespace (isrg-rust).
            ProverError: The prover rejected the inputs.
        """
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return handle.backend.prove(handle, mdoc, issuer_pk, transcript, attrs, timestamp)

    def verify(
        self,
        handle: CircuitHandle,
        issuer_pk: tuple[int, int],
        transcript: bytes,
        attrs: list[RequestedAttribute],
        timestamp: datetime,
        proof: bytes,
        doctype: str,
        *,
        device_namespaces: bytes | None = None,
    ) -> None:
        """Verify a proof that the requested attributes hold, against the transcript.

        Runs on the handle's backend, which may differ from this instance's
        when the handle was loaded elsewhere.

        Args:
            handle: A CircuitHandle from
                [`load_circuit`][pylongfellow.Pylongfellow.load_circuit].
            issuer_pk: Issuer public key, as `(x, y)`.
            transcript: Session transcript the proof is bound to.
            attrs: Attributes the proof claims; `len(attrs)` must equal
                `handle.spec.num_attributes`.
            timestamp: Timezone-aware verification time.
            proof: Proof bytes from [`prove`][pylongfellow.Pylongfellow.prove].
            doctype: mdoc doctype the proof is scoped to.
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes;
                required by the isrg-rust backend.

        Raises:
            ValueError: `timestamp` is naive; `len(attrs)` does not match
                `handle.spec.num_attributes` or `doctype` is 256 bytes or longer
                (google-cpp); or `device_namespaces` is None (isrg-rust).
            VerifierError: The proof does not hold.
        """
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        handle.backend.verify(
            handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, device_namespaces
        )

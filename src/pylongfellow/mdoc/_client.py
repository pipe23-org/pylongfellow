"""The Pylongfellow client: a backend bound at construction, then load, prove, and verify."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..backends import Backend, CircuitHandle, get_backend

if TYPE_CHECKING:
    from datetime import datetime

    from ._types import RequestedAttribute, ZkSpec


class Pylongfellow:
    """A client bound to one backend; every circuit operation routes through it.

    Attributes:
        backend: The bound [`Backend`][pylongfellow.backends.Backend].
    """

    backend: Backend

    def __init__(self, *, backend: str | Backend) -> None:
        """Bind a backend and probe its availability.

        Args:
            backend: Registry name (`google-cpp` or `isrg`) or a Backend
                instance.

        Raises:
            ValueError: `backend` is not a registered backend name.
            BackendUnavailableError: the backend's native dependency is not
                installed or built.
        """
        self.backend = get_backend(backend) if isinstance(backend, str) else backend
        self.backend.ensure_available()

    def load_circuit(self, spec: ZkSpec, compressed: bytes) -> CircuitHandle:
        """Load a compressed circuit into the bound backend and return a handle over it.

        Args:
            spec: ZkSpec naming the circuit.
            compressed: Compressed circuit bytes, as from
                [`generate_circuit`][pylongfellow.Pylongfellow.generate_circuit].

        Returns:
            A CircuitHandle to pass to [`prove`][pylongfellow.Pylongfellow.prove]
            and [`verify`][pylongfellow.Pylongfellow.verify].

        Raises:
            ValueError: `spec` is rejected by the backend, e.g. it is not
                registered or names a different circuit than `compressed`
                (google-cpp), or its version is unsupported (isrg).
        """
        return self.backend.load_circuit(spec, compressed)

    def generate_circuit(self, spec: ZkSpec) -> bytes:
        """Generate a compressed circuit blob on the bound backend.

        Args:
            spec: ZkSpec naming the circuit to generate.

        Returns:
            Compressed circuit bytes.

        Raises:
            ValueError: `spec` is not registered on the backend.
            CircuitError: Generation failed, e.g. an unsupported spec version.
            GenerationUnsupportedError: The backend cannot generate circuits.
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

        Dispatches through the handle's backend, which may differ from the
        client's when the handle was loaded elsewhere.

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
            ValueError: `len(attrs)` does not match `handle.spec.num_attributes`.
            ProverError: The prover rejected the inputs.
        """
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

        Dispatches through the handle's backend, which may differ from the
        client's when the handle was loaded elsewhere.

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
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes,
                required by the isrg backend; ignored by the google-cpp backend.

        Raises:
            ValueError: `len(attrs)` does not match `handle.spec.num_attributes`,
                `doctype` is 256 bytes or longer (google-cpp), or
                `device_namespaces` is None (isrg).
            VerifierError: The proof does not hold.
        """
        handle.backend.verify(
            handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, device_namespaces
        )

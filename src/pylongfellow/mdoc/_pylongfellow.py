"""The Pylongfellow prover and verifier."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..backends import Backend, get_backend

if TYPE_CHECKING:
    from datetime import datetime

    # Docstring cross-references resolve through this module's imports.
    from ..backends import BackendUnavailableError, GenerationUnsupportedError  # noqa: F401
    from ._errors import CircuitError, ProverError, VerifierError  # noqa: F401
    from ._types import CircuitSpec, PublicKey, RequestedAttribute


class Pylongfellow:
    """A Longfellow prover and verifier for one circuit on one backend.

    Example:
        ```python
        longfellow = Pylongfellow(backend="google-cpp")
        longfellow.load_circuit(spec, circuit)
        proof = longfellow.prove(mdoc, issuer_public_key, transcript, claims, timestamp)
        longfellow.verify(issuer_public_key, transcript, claims, timestamp, proof, doctype)
        ```

    Attributes:
        backend: The selected [`Backend`][pylongfellow.backends.Backend].
    """

    backend: Backend

    def __init__(self, *, backend: str | Backend) -> None:
        """Initialize with the selected backend.

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
        self._circuit: object | None = None

    def _loaded_circuit(self) -> object:
        if self._circuit is None:
            raise RuntimeError("no circuit is loaded; call load_circuit first")
        return self._circuit

    def load_circuit(self, spec: CircuitSpec, circuit: bytes) -> None:
        """Load the circuit this instance proves and verifies with.

        A second call replaces the loaded circuit.

        Args:
            spec: CircuitSpec naming the circuit.
            circuit: Circuit bytes, as from
                [`generate_circuit`][pylongfellow.Pylongfellow.generate_circuit].

        Raises:
            ValueError: `spec` is rejected by the backend, e.g. it is not
                registered or does not match `circuit` (google-cpp), or its
                version is unsupported (isrg-rust).
        """
        self._circuit = self.backend.load_circuit(spec, circuit)

    def generate_circuit(self, spec: CircuitSpec) -> bytes:
        """Generate the circuit named by spec.

        Args:
            spec: CircuitSpec naming the circuit to generate.

        Returns:
            Circuit bytes.

        Raises:
            ValueError: `spec` is not registered on the backend (google-cpp).
            CircuitError: Generation failed, e.g. an unsupported spec version (google-cpp).
            GenerationUnsupportedError: The backend cannot generate circuits (isrg-rust).
        """
        return self.backend.generate_circuit(spec)

    def prove(
        self,
        mdoc: bytes,
        issuer_public_key: PublicKey,
        transcript: bytes,
        claims: list[RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        """Prove the claims hold over the mdoc, bound to the transcript.

        Args:
            mdoc: CBOR-encoded mdoc credential.
            issuer_public_key: The issuer's public key.
            transcript: Session transcript the proof is bound to.
            claims: Claims to prove; `len(claims)` must equal the loaded spec's
                `num_attributes`.
            timestamp: Timezone-aware verification time.

        Returns:
            Proof bytes.

        Raises:
            RuntimeError: No circuit is loaded.
            ValueError: `timestamp` is naive; `len(claims)` does not match the
                loaded spec's `num_attributes` (google-cpp); or `claims` do not
                share one namespace (isrg-rust).
            ProverError: The prover rejected the inputs.
        """
        state = self._loaded_circuit()
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return self.backend.prove(state, mdoc, issuer_public_key, transcript, claims, timestamp)

    def verify(
        self,
        issuer_public_key: PublicKey,
        transcript: bytes,
        claims: list[RequestedAttribute],
        timestamp: datetime,
        proof: bytes,
        doctype: str,
        *,
        device_namespaces: bytes | None = None,
    ) -> None:
        """Verify a proof that the claims hold, against the transcript.

        Args:
            issuer_public_key: The issuer's public key.
            transcript: Session transcript the proof is bound to.
            claims: Claims to verify; `len(claims)` must equal the loaded spec's
                `num_attributes`.
            timestamp: Timezone-aware verification time.
            proof: Proof bytes from [`prove`][pylongfellow.Pylongfellow.prove].
            doctype: mdoc doctype the proof is scoped to.
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes;
                required by the isrg-rust backend.

        Raises:
            RuntimeError: No circuit is loaded.
            ValueError: `timestamp` is naive; `len(claims)` does not match the
                loaded spec's `num_attributes` or `doctype` is 256 bytes or longer
                (google-cpp); or `device_namespaces` is None (isrg-rust).
            VerifierError: The proof does not hold.
        """
        state = self._loaded_circuit()
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        self.backend.verify(
            state,
            issuer_public_key,
            transcript,
            claims,
            timestamp,
            proof,
            doctype,
            device_namespaces,
        )

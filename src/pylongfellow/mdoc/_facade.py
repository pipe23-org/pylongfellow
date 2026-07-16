"""The backend-dispatched mdoc facade: load a circuit, then prove and verify."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..backends import CircuitHandle, cpp

if TYPE_CHECKING:
    from datetime import datetime

    from ..backends import Backend
    from ._types import RequestedAttribute, ZkSpec


def load_circuit(
    spec: ZkSpec, compressed: bytes, *, backend: Backend | None = None
) -> CircuitHandle:
    """Load a compressed circuit into a backend and return a handle over it.

    Args:
        spec: ZkSpec naming the circuit.
        compressed: Compressed circuit bytes, as from
            [`generate_circuit`][pylongfellow.mdoc.generate_circuit].
        backend: Backend to load into; the cpp backend by default.

    Returns:
        A CircuitHandle to pass to [`prove`][pylongfellow.mdoc.prove] and
        [`verify`][pylongfellow.mdoc.verify].

    Raises:
        ValueError: `spec` is not registered on the backend, or names a
            different circuit than `compressed` (cpp backend).
    """
    resolved = cpp.BACKEND if backend is None else backend
    return resolved.load_circuit(spec, compressed)


def prove(
    handle: CircuitHandle,
    mdoc: bytes,
    issuer_pk: tuple[int, int],
    transcript: bytes,
    attrs: list[RequestedAttribute],
    timestamp: datetime,
) -> bytes:
    """Prove the requested attributes hold over the mdoc, bound to the transcript.

    Args:
        handle: A CircuitHandle from
            [`load_circuit`][pylongfellow.mdoc.load_circuit].
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

    Args:
        handle: A CircuitHandle from
            [`load_circuit`][pylongfellow.mdoc.load_circuit].
        issuer_pk: Issuer public key, as `(x, y)`.
        transcript: Session transcript the proof is bound to.
        attrs: Attributes the proof claims; `len(attrs)` must equal
            `handle.spec.num_attributes`.
        timestamp: Timezone-aware verification time.
        proof: Proof bytes from [`prove`][pylongfellow.mdoc.prove].
        doctype: mdoc doctype the proof is scoped to.
        device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes,
            required by some backends; ignored by the cpp backend.

    Raises:
        ValueError: `len(attrs)` does not match `handle.spec.num_attributes`,
            or `doctype` is 256 bytes or longer (cpp backend).
        VerifierError: The proof does not hold.
    """
    handle.backend.verify(
        handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, device_namespaces
    )


def generate_circuit(spec: ZkSpec, *, backend: Backend | None = None) -> bytes:
    """Generate a compressed circuit blob.

    Args:
        spec: ZkSpec naming the circuit to generate.
        backend: Backend to generate with; the cpp backend by default.

    Returns:
        Compressed circuit bytes.

    Raises:
        ValueError: `spec` is not registered on the backend.
        CircuitError: Generation failed, e.g. an unsupported spec version.
        GenerationUnsupportedError: The backend cannot generate circuits.
    """
    resolved = cpp.BACKEND if backend is None else backend
    return resolved.generate_circuit(spec)

"""UniFFI bindings to abetterinternet/zk-cred-longfellow (ISRG) behind the Backend protocol."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Any, cast

from ..mdoc._errors import ProverError, VerifierError
from . import BackendUnavailableError, CircuitHandle, GenerationUnsupportedError

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import RequestedAttribute, ZkSpec

_VERSIONS = frozenset({6, 7})


def _zk() -> Any:
    try:
        from ._zk_cred import zk_cred_longfellow
    except ImportError as e:
        raise BackendUnavailableError(
            "the isrg backend is not built; run scripts/build_isrg_backend.py"
        ) from e
    return zk_cred_longfellow


def _decompress(compressed: bytes) -> bytes:
    try:
        import zstandard
    except ImportError as e:
        raise BackendUnavailableError(
            "the zstandard package is required by the isrg backend; install pylongfellow[isrg]"
        ) from e
    return zstandard.ZstdDecompressor().stream_reader(io.BytesIO(compressed)).read()


def _circuit_version(zk: Any, version: int) -> Any:
    return zk.CircuitVersion.V6 if version == 6 else zk.CircuitVersion.V7


def _fmt_timestamp(timestamp: datetime) -> str:
    """Render timestamp to the exact 20-byte RFC 3339 UTC form the circuit compares against.

    Args:
        timestamp: Timezone-aware verification time.

    Returns:
        The `YYYY-MM-DDTHH:MM:SSZ` string.

    Raises:
        ValueError: `timestamp` is naive.
    """
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sec1(issuer_pk: tuple[int, int]) -> bytes:
    """Encode a public key `(x, y)` as a 65-byte SEC1 uncompressed point.

    Args:
        issuer_pk: Public key coordinates.

    Returns:
        The 65-byte uncompressed point: the 0x04 prefix followed by x and y.
    """
    x, y = issuer_pk
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def _single_namespace(attrs: list[RequestedAttribute]) -> str:
    namespaces = {attr.namespace for attr in attrs}
    if len(namespaces) != 1:
        raise ValueError("all attributes must share one namespace")
    return namespaces.pop()


@dataclass
class _Circuit:
    """Per-handle circuit state: the decompressed bytes and cached prover/verifier."""

    decompressed: bytes
    version: int
    num_attributes: int
    prover: Any = field(default=None)
    verifier: Any = field(default=None)


def _ensure_prover(holder: _Circuit) -> tuple[Any, Any]:
    zk = _zk()
    if holder.prover is None:
        holder.prover = zk.initialize_prover(
            holder.decompressed, _circuit_version(zk, holder.version), holder.num_attributes
        )
    return zk, holder.prover


def _ensure_verifier(holder: _Circuit) -> tuple[Any, Any]:
    zk = _zk()
    if holder.verifier is None:
        holder.verifier = zk.initialize_verifier(
            holder.decompressed, _circuit_version(zk, holder.version), holder.num_attributes
        )
    return zk, holder.verifier


class _IsrgBackend:
    """abetterinternet/zk-cred-longfellow (ISRG) via UniFFI; it cannot generate circuits."""

    name: str = "isrg"
    can_generate: bool = False

    def ensure_available(self) -> None:
        """Raise BackendUnavailableError unless the UniFFI extension is built."""
        _zk()

    def load_circuit(self, spec: ZkSpec, compressed: bytes) -> CircuitHandle:
        """Decompress and bind a circuit to this backend as a CircuitHandle.

        Circuit identity is backend-native behaviour: this backend does not
        check that `spec.circuit_hash` matches `compressed`. A wrong circuit of
        the same version and attribute count is not detected at load;
        version/count mismatches surface as errors at prove/verify.

        Args:
            spec: ZkSpec naming the circuit; its version must be 6 or 7.
            compressed: zstd-compressed circuit bytes.

        Returns:
            A CircuitHandle carrying the decompressed circuit as backend state.

        Raises:
            ValueError: `spec.version` is not 6 or 7.
            BackendUnavailableError: the `zstandard` package is not installed.
        """
        if spec.version not in _VERSIONS:
            raise ValueError(f"unsupported circuit version {spec.version} (expected 6 or 7)")
        decompressed = _decompress(compressed)
        holder = _Circuit(decompressed, spec.version, spec.num_attributes)
        return CircuitHandle(spec=spec, backend=self, state=holder)

    def generate_circuit(self, spec: ZkSpec) -> bytes:
        """Reject circuit generation; this backend cannot generate circuits.

        Args:
            spec: ZkSpec naming the circuit to generate.

        Raises:
            GenerationUnsupportedError: always.
        """
        raise GenerationUnsupportedError("the isrg backend cannot generate circuits")

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

        Args:
            handle: A CircuitHandle from `load_circuit`.
            mdoc: CBOR-encoded mdoc credential, passed through as the device response.
            issuer_pk: Issuer public key, as `(x, y)`; unused on the prover side.
            transcript: Session transcript the proof is bound to.
            attrs: Attributes to prove; all must share one namespace.
            timestamp: Timezone-aware verification time.

        Returns:
            Proof bytes.

        Raises:
            ValueError: `attrs` do not share one namespace, or `timestamp` is naive.
            BackendUnavailableError: the isrg backend is not built.
            ProverError: the prover rejected the inputs.
        """
        holder = cast("_Circuit", handle.state)
        namespace = _single_namespace(attrs)
        claims = [attr.id for attr in attrs]
        time = _fmt_timestamp(timestamp)
        zk, prover = _ensure_prover(holder)
        try:
            return cast(bytes, zk.prove(prover, mdoc, namespace, claims, transcript, time))
        except zk.MdocZkError as e:
            raise ProverError(message=str(e)) from e

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
        """Verify a proof that the requested attributes hold, against the transcript.

        Args:
            handle: A CircuitHandle from `load_circuit`.
            issuer_pk: Issuer public key, as `(x, y)`.
            transcript: Session transcript the proof is bound to.
            attrs: Attributes the proof claims.
            timestamp: Timezone-aware verification time.
            proof: Proof bytes from `prove`.
            doctype: mdoc doctype the proof is scoped to.
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes; required.

        Raises:
            ValueError: `device_namespaces` is None, or `timestamp` is naive.
            BackendUnavailableError: the isrg backend is not built.
            VerifierError: the proof does not hold.
        """
        if device_namespaces is None:
            raise ValueError(
                "device_namespaces is required (inner bytes of the tag-24 DeviceNameSpacesBytes)"
            )
        time = _fmt_timestamp(timestamp)
        issuer_public_key = _sec1(issuer_pk)
        zk, verifier = _ensure_verifier(cast("_Circuit", handle.state))
        attributes = [
            zk.Attribute(identifier=attr.id, value_cbor=attr.cbor_value) for attr in attrs
        ]
        try:
            zk.verify(
                verifier,
                issuer_public_key,
                attributes,
                doctype,
                device_namespaces,
                transcript,
                time,
                proof,
            )
        except zk.MdocZkError as e:
            raise VerifierError(message=str(e)) from e


BACKEND = _IsrgBackend()

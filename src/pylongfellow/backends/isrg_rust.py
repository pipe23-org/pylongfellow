"""UniFFI bindings to abetterinternet/zk-cred-longfellow (ISRG) behind the Backend protocol."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Any, cast

from ..mdoc._errors import ProverError, VerifierError
from . import BackendUnavailableError, CircuitIdUnsupportedError, GenerationUnsupportedError

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import CircuitSpec, PublicKey, RequestedAttribute

_VERSIONS = frozenset({6, 7})


def _zk() -> Any:
    try:
        from ._zk_cred import zk_cred_longfellow
    except ImportError as e:
        raise BackendUnavailableError(
            "the isrg-rust backend is not built; source builds omit it when configured "
            "with PYLONGFELLOW_BUILD_ISRG=OFF, and a dev checkout builds it with "
            "native/isrg-rust/build.py"
        ) from e
    return zk_cred_longfellow


def _decompress(compressed: bytes) -> bytes:
    import zstandard

    return zstandard.ZstdDecompressor().stream_reader(io.BytesIO(compressed)).read()


def _circuit_version(zk: Any, version: int) -> Any:
    return zk.CircuitVersion.V6 if version == 6 else zk.CircuitVersion.V7


def _fmt_timestamp(timestamp: datetime) -> str:
    """Render timestamp as `YYYY-MM-DDTHH:MM:SSZ`."""
    return timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _encode_public_key(public_key: PublicKey) -> bytes:
    """Encode a public key as a 65-byte uncompressed point.

    Args:
        public_key: The key to encode.

    Returns:
        The 65-byte uncompressed point: the 0x04 prefix followed by x and y.
    """
    return b"\x04" + public_key.x.to_bytes(32, "big") + public_key.y.to_bytes(32, "big")


def _single_namespace(claims: list[RequestedAttribute]) -> str:
    namespaces = {claim.namespace for claim in claims}
    if len(namespaces) != 1:
        raise ValueError("all claims must share one namespace")
    return namespaces.pop()


def circuit_id(circuit: bytes) -> str:
    """Reject circuit id recomputation; this backend cannot recompute circuit ids.

    Args:
        circuit: zstd-compressed circuit bytes.

    Raises:
        CircuitIdUnsupportedError: always.
    """
    raise CircuitIdUnsupportedError("the isrg-rust backend cannot recompute circuit ids")


@dataclass
class _LoadedCircuit:
    """The decompressed circuit, and the prover and verifier initialised from it on first use."""

    decompressed: bytes
    version: int
    num_attributes: int
    prover: Any = field(default=None)
    verifier: Any = field(default=None)


def _ensure_prover(loaded: _LoadedCircuit) -> tuple[Any, Any]:
    zk = _zk()
    if loaded.prover is None:
        loaded.prover = zk.initialize_prover(
            loaded.decompressed, _circuit_version(zk, loaded.version), loaded.num_attributes
        )
    return zk, loaded.prover


def _ensure_verifier(loaded: _LoadedCircuit) -> tuple[Any, Any]:
    zk = _zk()
    if loaded.verifier is None:
        loaded.verifier = zk.initialize_verifier(
            loaded.decompressed, _circuit_version(zk, loaded.version), loaded.num_attributes
        )
    return zk, loaded.verifier


class _IsrgRustBackend:
    """abetterinternet/zk-cred-longfellow (ISRG) via UniFFI; it cannot generate circuits."""

    name: str = "isrg-rust"
    can_generate: bool = False

    def ensure_available(self) -> None:
        """Raise BackendUnavailableError unless the UniFFI extension is built."""
        _zk()

    def load_circuit(self, spec: CircuitSpec, circuit: bytes) -> object:
        """Decompress a circuit and return it as circuit state.

        Circuit identity is backend-native behaviour: this backend does not
        check that `spec.circuit_hash` matches `circuit`. A wrong circuit of
        the same version and attribute count is not detected at load;
        version/count mismatches surface as errors at prove/verify.

        Args:
            spec: CircuitSpec identifying the circuit; its version must be 6 or 7.
            circuit: zstd-compressed circuit bytes.

        Returns:
            The circuit state prove and verify take.

        Raises:
            ValueError: `spec.version` is not 6 or 7.
        """
        if spec.version not in _VERSIONS:
            raise ValueError(f"unsupported circuit version {spec.version} (expected 6 or 7)")
        decompressed = _decompress(circuit)
        return _LoadedCircuit(decompressed, spec.version, spec.num_attributes)

    def generate_circuit(self, spec: CircuitSpec) -> bytes:
        """Reject circuit generation; this backend cannot generate circuits.

        Args:
            spec: CircuitSpec identifying the circuit to generate.

        Raises:
            GenerationUnsupportedError: always.
        """
        raise GenerationUnsupportedError("the isrg-rust backend cannot generate circuits")

    def prove(
        self,
        state: object,
        mdoc: bytes,
        issuer_public_key: PublicKey,
        transcript: bytes,
        claims: list[RequestedAttribute],
        timestamp: datetime,
    ) -> bytes:
        """Prove the claims hold over the mdoc, bound to the transcript.

        Args:
            state: Circuit state from `load_circuit`.
            mdoc: CBOR-encoded mdoc credential, passed through as the device response.
            issuer_public_key: The issuer's public key.
            transcript: Session transcript to bind the proof to.
            claims: Claims to prove; all must share one namespace.
            timestamp: Timezone-aware verification time.

        Returns:
            Proof bytes.

        Raises:
            ValueError: `claims` do not share one namespace.
            BackendUnavailableError: the isrg-rust backend is not built.
            ProverError: the prover rejected the inputs.
        """
        loaded = cast("_LoadedCircuit", state)
        namespace = _single_namespace(claims)
        claim_ids = [claim.id for claim in claims]
        time = _fmt_timestamp(timestamp)
        zk, prover = _ensure_prover(loaded)
        try:
            return cast(bytes, zk.prove(prover, mdoc, namespace, claim_ids, transcript, time))
        except zk.MdocZkError as e:
            raise ProverError(message=str(e)) from e

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
        """Verify a proof that the claims hold, against the transcript.

        Args:
            state: Circuit state from `load_circuit`.
            issuer_public_key: The issuer's public key.
            transcript: Session transcript the proof is bound to.
            claims: Claims to verify.
            timestamp: Timezone-aware verification time.
            proof: Proof bytes from `prove`.
            doctype: mdoc doctype the proof is scoped to.
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes; required.

        Raises:
            ValueError: `device_namespaces` is None.
            BackendUnavailableError: the isrg-rust backend is not built.
            VerifierError: the proof does not hold.
        """
        if device_namespaces is None:
            raise ValueError(
                "device_namespaces is required (inner bytes of the tag-24 DeviceNameSpacesBytes)"
            )
        time = _fmt_timestamp(timestamp)
        encoded_public_key = _encode_public_key(issuer_public_key)
        zk, verifier = _ensure_verifier(cast("_LoadedCircuit", state))
        attributes = [
            zk.Attribute(identifier=claim.id, value_cbor=claim.cbor_value) for claim in claims
        ]
        try:
            zk.verify(
                verifier,
                encoded_public_key,
                attributes,
                doctype,
                device_namespaces,
                transcript,
                time,
                proof,
            )
        except zk.MdocZkError as e:
            raise VerifierError(message=str(e)) from e


BACKEND = _IsrgRustBackend()

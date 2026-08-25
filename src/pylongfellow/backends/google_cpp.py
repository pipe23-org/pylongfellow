"""The google/longfellow-zk backend: the vendored C++ library's C ABI behind the Backend protocol."""

import functools
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from ..mdoc._errors import (
    CircuitError,
    CircuitGenerationErrorCode,
    Error,
    ProverError,
    ProverErrorCode,
    VerifierError,
    VerifierErrorCode,
)
from ..mdoc._types import PublicKey, RequestedAttribute
from . import BackendUnavailableError

_SYSTEM = "longfellow-libzk-v1"

# C fixed-buffer sizes (from the upstream RequestedAttribute struct).
_NAMESPACE_MAX, _ID_MAX, _VALUE_MAX = 64, 32, 64


@dataclass(frozen=True)
class ZkSpec:
    """A row of the compiled-in circuit table; what `find_zk_spec` and `zk_specs` return.

    Attributes:
        system: ZK system name and version (e.g. `longfellow-libzk-v*`).
        circuit_hash: SHA-256 (hex) pinning which circuit the row describes.
        num_attributes: Number of attributes the circuit proves over.
        version: Version of the ZK specification.
        block_enc_hash: `block_enc` parameter for the proof (upstream field).
        block_enc_sig: `block_enc` parameter for the proof (upstream field).
    """

    system: str
    circuit_hash: str
    num_attributes: int
    version: int
    block_enc_hash: int
    block_enc_sig: int


def _load() -> tuple[Any, Any]:
    try:
        from .._longfellow import ffi, lib
    except ImportError as e:
        raise BackendUnavailableError(
            "the google-cpp backend's native extension is not built; source builds omit "
            "it when configured with PYLONGFELLOW_BUILD_GOOGLE=OFF"
        ) from e
    return ffi, lib


def _fmt_timestamp(timestamp: datetime) -> bytes:
    """Render timestamp as `YYYY-MM-DDTHH:MM:SSZ`."""
    return timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ").encode("ascii")


def _fill_attrs(ffi: Any, attrs: list[RequestedAttribute]) -> Any:
    c_attrs = ffi.new("RequestedAttribute[]", len(attrs))
    for i, attr in enumerate(attrs):
        namespace, attr_id, value = attr.namespace.encode(), attr.id.encode(), attr.cbor_value
        if len(namespace) > _NAMESPACE_MAX:
            raise ValueError(f"namespace too long ({len(namespace)} > {_NAMESPACE_MAX} bytes)")
        if len(attr_id) > _ID_MAX:
            raise ValueError(f"id too long ({len(attr_id)} > {_ID_MAX} bytes)")
        if len(value) > _VALUE_MAX:
            raise ValueError(f"cbor_value too long ({len(value)} > {_VALUE_MAX} bytes)")
        ffi.memmove(c_attrs[i].namespace_id, namespace, len(namespace))
        ffi.memmove(c_attrs[i].id, attr_id, len(attr_id))
        ffi.memmove(c_attrs[i].cbor_value, value, len(value))
        c_attrs[i].namespace_len = len(namespace)
        c_attrs[i].id_len = len(attr_id)
        c_attrs[i].cbor_value_len = len(value)
    return c_attrs


def _build_spec(ffi: Any, spec: ZkSpec) -> tuple[Any, Any]:
    """Build the C ZkSpecStruct from the dataclass.

    Returns (struct, system_buf). The struct's `system` field is a raw char*
    into system_buf; the caller must keep system_buf alive until the C call
    returns, or that pointer dangles into freed memory.
    """
    c_spec = ffi.new("ZkSpecStruct*")
    system_buf = ffi.new("char[]", spec.system.encode())
    c_spec.system = system_buf
    hash_bytes = spec.circuit_hash.encode()
    ffi.memmove(c_spec.circuit_hash, hash_bytes, len(hash_bytes))
    c_spec.num_attributes = spec.num_attributes
    c_spec.version = spec.version
    c_spec.block_enc_hash = spec.block_enc_hash
    c_spec.block_enc_sig = spec.block_enc_sig
    return c_spec, system_buf


def _require_claims_match_spec(claims: list[RequestedAttribute], spec: ZkSpec) -> None:
    # The C entry points never read num_attributes; the invariant is attrs_len ==
    # the circuit's attribute count, for which the loaded row's field is the proxy
    # (tied to the circuit by the id check at load). A mismatch hard-aborts in C
    # (DenseFiller overfill on too many; the Ligero subfield check on too few,
    # prover side) — only verify-with-too-few returns a clean status.
    if len(claims) != spec.num_attributes:
        raise ValueError(
            f"len(claims) ({len(claims)}) does not match the loaded circuit's "
            f"num_attributes ({spec.num_attributes})"
        )


def _find_row(version: int, num_attributes: int) -> ZkSpec | None:
    """Return the compiled-in row with this version and attribute count, or None."""
    for row in zk_specs():
        if (row.system, row.version, row.num_attributes) == (_SYSTEM, version, num_attributes):
            return row
    return None


def _spec_from_struct(ffi: Any, c_spec: Any) -> ZkSpec:
    """Convert a ZkSpecStruct (pointer or array element) to a ZkSpec."""
    return ZkSpec(
        system=ffi.string(c_spec.system).decode(),
        circuit_hash=ffi.string(c_spec.circuit_hash).decode(),
        num_attributes=c_spec.num_attributes,
        version=c_spec.version,
        block_enc_hash=c_spec.block_enc_hash,
        block_enc_sig=c_spec.block_enc_sig,
    )


@functools.cache
def circuit_id(circuit: bytes) -> str:
    """Recompute a circuit's canonical id from its bytes.

    Binds `circuit_id`. The id is 64 hex chars and equals
    [`ZkSpec.circuit_hash`][pylongfellow.backends.google_cpp.ZkSpec].

    Args:
        circuit: Circuit bytes.

    Returns:
        The canonical id, as 64-char hex.

    Raises:
        Error: The bytes could not be parsed.
    """
    ffi, lib = _load()
    # v0.9 circuit_id only null-checks the spec; the id is a pure function of the circuit.
    dummy_spec = ZkSpec("", "0" * 64, 0, 0, 0, 0)
    c_spec, _keepalive = _build_spec(ffi, dummy_spec)
    out = ffi.new("uint8_t[32]")
    if lib.circuit_id(out, circuit, len(circuit), c_spec) != 1:
        raise Error("circuit_id failed (unparseable circuit bytes)")
    return bytes(ffi.buffer(out, 32)).hex()


def find_zk_spec(system: str, circuit_hash: str) -> ZkSpec | None:
    """Look up the built-in ZkSpec for a (system, circuit_hash) pair.

    Binds `find_zk_spec`.

    Args:
        system: Proof-system identifier the spec is registered under.
        circuit_hash: Canonical circuit id, as from
            [`circuit_id`][pylongfellow.backends.google_cpp.circuit_id].

    Returns:
        The matching ZkSpec, or None if the build has no spec for that pair.
    """
    ffi, lib = _load()
    spec_ptr = lib.find_zk_spec(system.encode(), circuit_hash.encode())
    if spec_ptr == ffi.NULL:
        return None
    return _spec_from_struct(ffi, spec_ptr)


@functools.cache
def zk_specs() -> tuple[ZkSpec, ...]:
    """Return every ZkSpec compiled into the linked library, in table order.

    Binds the `kZkSpecs` table. Entries include superseded circuit versions:
    for a given `num_attributes`, several `(version, circuit_hash)` rows may be
    present. `generate_circuit` accepts only the highest version for a given
    `num_attributes`.

    Returns:
        The table's ZkSpec entries, in table order.
    """
    ffi, lib = _load()
    return tuple(_spec_from_struct(ffi, c_spec) for c_spec in lib.kZkSpecs)


def generate_circuit(version: int, num_attributes: int) -> bytes:
    """Generate the compiled-in circuit with this version and attribute count.

    Binds `generate_circuit`. C generates only the highest version the table holds
    for an attribute count, so an older version of a known count raises
    `CircuitError`.

    Args:
        version: Version of the ZK specification.
        num_attributes: Number of attributes the circuit proves over.

    Returns:
        Circuit bytes.

    Raises:
        ValueError: The compiled-in table has no circuit with that version and
            attribute count.
        CircuitError: Generation failed.
    """
    ffi, lib = _load()
    spec = _find_row(version, num_attributes)
    if spec is None:
        raise ValueError(
            f"no compiled-in circuit with version {version} and num_attributes {num_attributes}"
        )
    c_spec, _keepalive = _build_spec(ffi, spec)
    circuit_ptr = ffi.new("uint8_t**")
    circuit_len = ffi.new("size_t*")
    status = lib.generate_circuit(c_spec, circuit_ptr, circuit_len)
    if status != lib.CIRCUIT_GENERATION_SUCCESS:
        raise CircuitError(CircuitGenerationErrorCode(status))
    try:
        return bytes(ffi.buffer(circuit_ptr[0], circuit_len[0]))
    finally:
        if circuit_ptr[0] != ffi.NULL:
            lib.free(circuit_ptr[0])


@dataclass(frozen=True)
class _LoadedCircuit:
    """A circuit and the table row it was matched to; every C call takes both."""

    spec: ZkSpec
    circuit: bytes


class _GoogleBackend:
    """google/longfellow-zk's C++ library via its C ABI."""

    name: str = "google-cpp"

    def ensure_available(self) -> None:
        """Raise BackendUnavailableError unless the native extension is built."""
        _load()

    def load_circuit(self, circuit: bytes, version: int, num_attributes: int) -> object:
        """Return circuit state for bytes that are the declared compiled-in circuit.

        The circuit id is recomputed from the bytes; the table row it resolves to
        must carry the declared version and attribute count.

        Args:
            circuit: Circuit bytes.
            version: Version of the ZK specification the bytes are declared to be.
            num_attributes: Number of attributes the circuit is declared to prove over.

        Returns:
            The circuit state prove and verify take.

        Raises:
            Error: The bytes could not be parsed.
            ValueError: The bytes are not a compiled-in circuit with the declared
                version and attribute count.
        """
        spec = find_zk_spec(_SYSTEM, circuit_id(circuit))
        if spec is None or (spec.version, spec.num_attributes) != (version, num_attributes):
            raise ValueError(
                f"circuit bytes do not match a compiled-in circuit with version {version} "
                f"and num_attributes {num_attributes}"
            )
        return _LoadedCircuit(spec=spec, circuit=circuit)

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

        Binds `run_mdoc_prover`.

        Args:
            state: Circuit state from `load_circuit`.
            mdoc: CBOR-encoded mdoc credential.
            issuer_public_key: The issuer's public key.
            transcript: Session transcript to bind the proof to.
            claims: Claims to prove; `len(claims)` must equal the loaded circuit's
                `num_attributes`.
            timestamp: Timezone-aware verification time.

        Returns:
            Proof bytes.

        Raises:
            ValueError: `len(claims)` does not match the loaded circuit's `num_attributes`.
            ProverError: The prover rejected the inputs.
        """
        ffi, lib = _load()
        loaded = cast(_LoadedCircuit, state)
        spec, circuit = loaded.spec, loaded.circuit
        _require_claims_match_spec(claims, spec)
        pk_x, pk_y = issuer_public_key.x, issuer_public_key.y
        c_attrs = _fill_attrs(ffi, claims)
        c_spec, _keepalive = _build_spec(ffi, spec)
        proof_ptr = ffi.new("uint8_t**")
        proof_len = ffi.new("size_t*")
        status = lib.run_mdoc_prover(
            circuit,
            len(circuit),
            mdoc,
            len(mdoc),
            str(pk_x).encode(),
            str(pk_y).encode(),
            transcript,
            len(transcript),
            c_attrs,
            len(claims),
            _fmt_timestamp(timestamp),
            proof_ptr,
            proof_len,
            c_spec,
        )
        if status != lib.MDOC_PROVER_SUCCESS:
            raise ProverError(ProverErrorCode(status))
        try:
            return bytes(ffi.buffer(proof_ptr[0], proof_len[0]))
        finally:
            if proof_ptr[0] != ffi.NULL:
                lib.free(proof_ptr[0])

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

        Binds `run_mdoc_verifier`.

        Args:
            state: Circuit state from `load_circuit`.
            issuer_public_key: The issuer's public key.
            transcript: Session transcript the proof is bound to.
            claims: Claims to verify; `len(claims)` must equal the loaded circuit's
                `num_attributes`.
            timestamp: Timezone-aware verification time.
            proof: Proof bytes from [`prove`][pylongfellow.Pylongfellow.prove].
            doctype: mdoc doctype the proof is scoped to.
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes.

        Raises:
            ValueError: `len(claims)` does not match the loaded circuit's `num_attributes`,
                or `doctype` is 256 bytes or longer.
            VerifierError: The proof does not hold.
        """
        ffi, lib = _load()
        loaded = cast(_LoadedCircuit, state)
        spec, circuit = loaded.spec, loaded.circuit
        _require_claims_match_spec(claims, spec)
        # C silently substitutes a default doctype at >= 256 bytes, verifying the
        # proof against the wrong scope with no error. Refuse rather than mislead.
        if len(doctype.encode()) >= 256:
            raise ValueError(f"doctype too long ({len(doctype.encode())} >= 256 bytes)")
        pk_x, pk_y = issuer_public_key.x, issuer_public_key.y
        c_attrs = _fill_attrs(ffi, claims)
        c_spec, _keepalive = _build_spec(ffi, spec)
        status = lib.run_mdoc_verifier(
            circuit,
            len(circuit),
            str(pk_x).encode(),
            str(pk_y).encode(),
            transcript,
            len(transcript),
            c_attrs,
            len(claims),
            _fmt_timestamp(timestamp),
            proof,
            len(proof),
            doctype.encode(),
            c_spec,
        )
        if status != lib.MDOC_VERIFIER_SUCCESS:
            raise VerifierError(VerifierErrorCode(status))


BACKEND = _GoogleBackend()

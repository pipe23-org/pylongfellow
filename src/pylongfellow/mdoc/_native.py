"""Wrappers over the C ABI: marshal inputs, copy results out, raise typed errors."""

import functools
from datetime import UTC, datetime
from typing import Any

from ._errors import (
    CircuitError,
    CircuitGenerationErrorCode,
    Error,
    ProverError,
    ProverErrorCode,
    VerifierError,
    VerifierErrorCode,
)
from ._types import RequestedAttribute, ZkSpec

# C fixed-buffer sizes (from the upstream RequestedAttribute struct).
_NAMESPACE_MAX, _ID_MAX, _VALUE_MAX = 64, 32, 64


def _load() -> tuple[Any, Any]:
    try:
        from .._longfellow import ffi, lib
    except ImportError as e:  # pragma: no cover - depends on the build
        raise ImportError(
            "pylongfellow native extension is not built; build the package first"
        ) from e
    return ffi, lib


def _fmt_timestamp(timestamp: datetime) -> bytes:
    """Render timestamp to the exact 20-byte RFC 3339 UTC form the circuit compares against."""
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
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
    # The C field is char[65]; memmove of anything longer is an out-of-bounds
    # heap write (silent at 66-80 bytes, allocator abort beyond). Refuse here.
    if len(hash_bytes) > 64:
        raise ValueError(f"circuit_hash too long ({len(hash_bytes)} > 64 bytes)")
    ffi.memmove(c_spec.circuit_hash, hash_bytes, len(hash_bytes))
    c_spec.num_attributes = spec.num_attributes
    c_spec.version = spec.version
    c_spec.block_enc_hash = spec.block_enc_hash
    c_spec.block_enc_sig = spec.block_enc_sig
    return c_spec, system_buf


def _require_attrs_match_spec(attrs: list[RequestedAttribute], spec: ZkSpec) -> None:
    # The C entry points never read spec.num_attributes; the invariant is
    # attrs_len == the circuit's attribute count, for which the spec field is the
    # proxy (tied to the circuit by the hash check below). A mismatch hard-aborts
    # in C (DenseFiller overfill on too many; the Ligero subfield check on too
    # few, prover side) — only verify-with-too-few returns a clean status.
    if len(attrs) != spec.num_attributes:
        raise ValueError(
            f"len(attrs) ({len(attrs)}) does not match spec.num_attributes ({spec.num_attributes})"
        )


def _require_canonical_spec(spec: ZkSpec) -> None:
    # The C entry points read version and block_enc_* straight from the struct
    # and SIGABRT on non-canonical values even when the hash matches (Ligero
    # subfield / block_enc checks). num_attributes/system/circuit_hash are the
    # only fields C does *not* read, so the spec's self-report is otherwise
    # unchecked. Pin the whole tuple to the library's own table: a registered
    # (system, circuit_hash) has one canonical spec, and any deviation is a lie.
    if spec != find_zk_spec(spec.system, spec.circuit_hash):
        raise ValueError("spec is not a registered ZkSpec")


def _require_spec_matches_circuit(circuit: bytes, spec: ZkSpec) -> None:
    # The C prover hard-aborts (SIGABRT — a paranoid subfield check in the Ligero
    # prover) on a spec/circuit mismatch, with no error return; refuse it here as
    # a clean error. circuit_id is cached, so a reused circuit pays the parse once.
    if circuit_id(circuit) != spec.circuit_hash:
        raise ValueError("spec.circuit_hash does not match the circuit")


def prove(
    circuit: bytes,
    mdoc: bytes,
    issuer_pk: tuple[int, int],
    transcript: bytes,
    attrs: list[RequestedAttribute],
    timestamp: datetime,
    spec: ZkSpec,
) -> bytes:
    """Prove the requested attributes hold over the mdoc, bound to the transcript.

    Binds `run_mdoc_prover`.

    Args:
        circuit: Compressed circuit bytes, as from
            [`generate_circuit`][pylongfellow.mdoc.generate_circuit].
        mdoc: CBOR-encoded mdoc credential.
        issuer_pk: Issuer public key, as `(x, y)`.
        transcript: Session transcript the proof is bound to.
        attrs: Attributes to prove; `len(attrs)` must equal `spec.num_attributes`.
        timestamp: Timezone-aware verification time.
        spec: ZkSpec naming the circuit.

    Returns:
        Proof bytes.

    Raises:
        ValueError: `spec` is not a registered ZkSpec, names a different
            circuit than `circuit`, or `len(attrs)` does not match
            `spec.num_attributes`.
        ProverError: The prover rejected the inputs.
    """
    ffi, lib = _load()
    _require_canonical_spec(spec)
    _require_spec_matches_circuit(circuit, spec)
    _require_attrs_match_spec(attrs, spec)
    pk_x, pk_y = issuer_pk
    c_attrs = _fill_attrs(ffi, attrs)
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
        len(attrs),
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
    circuit: bytes,
    issuer_pk: tuple[int, int],
    transcript: bytes,
    attrs: list[RequestedAttribute],
    timestamp: datetime,
    proof: bytes,
    doctype: str,
    spec: ZkSpec,
) -> None:
    """Verify a proof that the requested attributes hold, against the transcript.

    Binds `run_mdoc_verifier`.

    Args:
        circuit: Compressed circuit bytes the proof was produced against.
        issuer_pk: Issuer public key, as `(x, y)`.
        transcript: Session transcript the proof is bound to.
        attrs: Attributes the proof claims; `len(attrs)` must equal
            `spec.num_attributes`.
        timestamp: Timezone-aware verification time.
        proof: Proof bytes from [`prove`][pylongfellow.mdoc.prove].
        doctype: mdoc doctype the proof is scoped to.
        spec: ZkSpec naming the circuit.

    Raises:
        ValueError: `spec` is not a registered ZkSpec, names a different
            circuit than `circuit`, `len(attrs)` does not match
            `spec.num_attributes`, or `doctype` is 256 bytes or longer.
        VerifierError: The proof does not hold.
    """
    ffi, lib = _load()
    _require_canonical_spec(spec)
    _require_spec_matches_circuit(circuit, spec)
    _require_attrs_match_spec(attrs, spec)
    # C silently substitutes a default doctype at >= 256 bytes, verifying the
    # proof against the wrong scope with no error. Refuse rather than mislead.
    if len(doctype.encode()) >= 256:
        raise ValueError(f"doctype too long ({len(doctype.encode())} >= 256 bytes)")
    pk_x, pk_y = issuer_pk
    c_attrs = _fill_attrs(ffi, attrs)
    c_spec, _keepalive = _build_spec(ffi, spec)
    status = lib.run_mdoc_verifier(
        circuit,
        len(circuit),
        str(pk_x).encode(),
        str(pk_y).encode(),
        transcript,
        len(transcript),
        c_attrs,
        len(attrs),
        _fmt_timestamp(timestamp),
        proof,
        len(proof),
        doctype.encode(),
        c_spec,
    )
    if status != lib.MDOC_VERIFIER_SUCCESS:
        raise VerifierError(VerifierErrorCode(status))


def generate_circuit(spec: ZkSpec) -> bytes:
    """Generate a circuit blob.

    Binds `generate_circuit`. Only the latest circuit version is generated.

    Args:
        spec: ZkSpec naming the circuit to generate.

    Returns:
        Compressed circuit bytes.

    Raises:
        ValueError: `spec` is not a registered ZkSpec.
        CircuitError: Generation failed, e.g. an unsupported spec version.
    """
    ffi, lib = _load()
    _require_canonical_spec(spec)
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


@functools.cache
def circuit_id(circuit: bytes) -> str:
    """Recompute a circuit's canonical id from its compressed bytes.

    Binds `circuit_id`. The id is 64 hex chars and equals
    [`ZkSpec.circuit_hash`][pylongfellow.mdoc.ZkSpec].

    Args:
        circuit: Compressed circuit bytes.

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


def find_zk_spec(system: str, circuit_hash: str) -> ZkSpec | None:
    """Look up the built-in ZkSpec for a (system, circuit_hash) pair.

    Binds `find_zk_spec`.

    Args:
        system: Proof-system identifier the spec is registered under.
        circuit_hash: Canonical circuit id, as from
            [`circuit_id`][pylongfellow.mdoc.circuit_id].

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

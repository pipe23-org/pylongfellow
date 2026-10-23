"""UniFFI bindings to the longfellow-zk Rust implementation behind the Backend protocol.

`materialize_circuit` reads the archives in the `vendor/longfellow-zk` checkout through a
path the crate resolves at compile time, so that checkout must be on disk when it is called.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Any, cast

import cbor2

from ..mdoc._errors import CircuitError, ProverError, VerifierError
from . import BackendUnavailableError
from .google_cpp import _fmt_timestamp

if TYPE_CHECKING:
    from datetime import datetime

    from ..mdoc._types import PublicKey, RequestedAttribute


class ProverErrorCode(IntEnum):
    """Return codes from the Rust `run_mdoc_prover` and `provider::materialize`."""

    Success = 0
    NullInput = 1
    InvalidInput = 2
    CircuitParsingFailure = 3
    HashParsingFailure = 4
    WitnessCreationFailure = 5
    GeneralFailure = 6
    MemoryAllocationFailure = 7
    InvalidZkSpecVersion = 8
    RootDecodingFailure = 9
    DocumentsMissing = 10
    Document0Missing = 11
    DocTypeMissing = 12
    IssuerSignedMissing = 13
    IssuerAuthMissing = 14
    MsoMissing = 15
    NsigMissing = 16
    NamespacesMissing = 17
    DeviceSignedMissing = 18
    DeviceAuthMissing = 19
    DeviceSignatureMissing = 20
    DeviceKeyMissing = 21
    MsoDecodingFailure = 22
    ValidityInfoMissing = 23
    DeviceKeyInfoMissing = 24
    AttributeDecodeFailure = 25
    AttributeEiMissing = 26
    AttributeEvMissing = 27
    AttributeDidMissing = 28
    SignatureFailure = 29
    DeviceSignatureFailure = 30
    AttributeNotFound = 31
    AttributeTooLong = 32
    TaggedMsoTooBig = 33
    VersionNotSupported = 34
    AttributeRandomMissing = 35
    UnsupportedAttribute = 36


class VerifierErrorCode(IntEnum):
    """Return codes from the Rust `run_mdoc_verifier`."""

    Success = 0
    CircuitParsingFailure = 1
    ProofTooSmall = 2
    HashParsingFailure = 3
    SignatureParsingFailure = 4
    GeneralFailure = 5
    NullInput = 6
    InvalidInput = 7
    ArgumentsTooSmall = 8
    AttributeNumberMismatch = 9
    InvalidZkSpecVersion = 10
    UnsupportedAttribute = 11


def _lf() -> Any:
    try:
        from ._lf_rust import longfellow_zk_uniffi
    except ImportError as e:
        raise BackendUnavailableError(
            "the lf-rust backend is not built; source builds omit it unless configured "
            "with PYLONGFELLOW_BUILD_LF_RUST=ON, and a dev checkout builds it with "
            "native/lf-rust/build.py"
        ) from e
    return longfellow_zk_uniffi


def _fmt_coordinate(coordinate: int) -> str:
    """Render a public-key coordinate as 64 hex characters."""
    return f"{coordinate:064x}"


def _mso_doctype(mdoc: bytes) -> str:
    """Return the MSO docType of the first document of a DeviceResponse."""
    issuer_signed = cbor2.loads(mdoc)["documents"][0]["issuerSigned"]
    mso = cbor2.loads(cbor2.loads(issuer_signed["issuerAuth"][2]).value)
    return cast(str, mso["docType"])


def _records(lf: Any, claims: list[RequestedAttribute]) -> list[Any]:
    """Convert claims to the crate's RequestedAttribute records."""
    return [
        lf.RequestedAttribute(
            namespace_id=claim.namespace.encode(),
            id=claim.id.encode(),
            cbor_value=claim.cbor_value,
        )
        for claim in claims
    ]


def materialize_circuit(version: int, num_attributes: int) -> bytes:
    """Return the compressed circuit for this version and attribute count.

    Binds `provider::materialize`. Versions below the current one come from the archives
    committed in the `vendor/longfellow-zk` checkout; the current version is compiled.

    Args:
        version: Version of the ZK specification.
        num_attributes: Number of attributes the circuit proves over.

    Returns:
        Compressed circuit bytes, in the archive format the Rust tree writes.

    Raises:
        BackendUnavailableError: the lf-rust backend is not built.
        CircuitError: upstream has no circuit for the pair, or materialization failed.
    """
    lf = _lf()
    try:
        return cast(bytes, lf.materialize_circuit(version, num_attributes))
    except lf.Error.Prover as e:
        raise CircuitError(ProverErrorCode(e.code)) from e


@dataclass(frozen=True)
class _LoadedCircuit:
    """The circuit bytes and the version and attribute count declared for them."""

    circuit: bytes
    version: int
    num_attributes: int


def _require_claims_match(claims: list[RequestedAttribute], num_attributes: int) -> None:
    if len(claims) != num_attributes:
        raise ValueError(
            f"len(claims) ({len(claims)}) does not match the loaded circuit's "
            f"num_attributes ({num_attributes})"
        )


def _unknown_circuit(loaded: _LoadedCircuit) -> ValueError:
    return ValueError(
        f"no circuit with version {loaded.version} and num_attributes {loaded.num_attributes}"
    )


class _LfRustBackend:
    """longfellow-zk/longfellow-zk's Rust implementation via UniFFI."""

    name: str = "lf-rust"

    def ensure_available(self) -> None:
        """Raise BackendUnavailableError unless the UniFFI extension is built."""
        _lf()

    def load_circuit(self, circuit: bytes, version: int, num_attributes: int) -> object:
        """Return circuit state for the declared version and attribute count.

        The declared pair is resolved against upstream's circuit table on the first
        `prove` or `verify` call, which is where an unknown pair is reported.

        Args:
            circuit: Compressed circuit bytes.
            version: Version of the ZK specification the bytes are declared to be.
            num_attributes: Number of attributes the circuit is declared to prove over.

        Returns:
            The circuit state prove and verify take.
        """
        return _LoadedCircuit(circuit=circuit, version=version, num_attributes=num_attributes)

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

        Binds `run_mdoc_prover`. The doctype the proof is scoped to is the `docType` of
        the mdoc's mobile security object.

        Args:
            state: Circuit state from `load_circuit`.
            mdoc: CBOR-encoded DeviceResponse.
            issuer_public_key: The issuer's public key.
            transcript: Session transcript to bind the proof to.
            claims: Claims to prove; `len(claims)` must equal the loaded circuit's
                `num_attributes`.
            timestamp: Timezone-aware verification time.

        Returns:
            Proof bytes.

        Raises:
            ValueError: `len(claims)` does not match the loaded circuit's
                `num_attributes`, or upstream has no circuit for the declared version
                and attribute count.
            BackendUnavailableError: the lf-rust backend is not built.
            ProverError: The prover rejected the inputs.
        """
        loaded = cast("_LoadedCircuit", state)
        _require_claims_match(claims, loaded.num_attributes)
        lf = _lf()
        try:
            return cast(
                bytes,
                lf.prove(
                    loaded.version,
                    loaded.num_attributes,
                    loaded.circuit,
                    mdoc,
                    _fmt_coordinate(issuer_public_key.x),
                    _fmt_coordinate(issuer_public_key.y),
                    transcript,
                    _records(lf, claims),
                    _fmt_timestamp(timestamp).decode("ascii"),
                    _mso_doctype(mdoc),
                ),
            )
        except lf.Error.Prover as e:
            raise ProverError(ProverErrorCode(e.code)) from e
        except lf.Error.UnknownCircuit as e:
            raise _unknown_circuit(loaded) from e

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
            proof: Proof bytes from `prove`.
            doctype: mdoc doctype the proof is scoped to.
            device_namespaces: Inner bytes of the tag-24 DeviceNameSpacesBytes; not read.

        Raises:
            ValueError: `len(claims)` does not match the loaded circuit's
                `num_attributes`, or upstream has no circuit for the declared version
                and attribute count.
            BackendUnavailableError: the lf-rust backend is not built.
            VerifierError: The proof does not hold.
        """
        loaded = cast("_LoadedCircuit", state)
        _require_claims_match(claims, loaded.num_attributes)
        lf = _lf()
        try:
            lf.verify(
                loaded.version,
                loaded.num_attributes,
                loaded.circuit,
                _fmt_coordinate(issuer_public_key.x),
                _fmt_coordinate(issuer_public_key.y),
                transcript,
                _records(lf, claims),
                _fmt_timestamp(timestamp).decode("ascii"),
                doctype,
                proof,
            )
        except lf.Error.Verifier as e:
            raise VerifierError(VerifierErrorCode(e.code)) from e
        except lf.Error.UnknownCircuit as e:
            raise _unknown_circuit(loaded) from e


BACKEND = _LfRustBackend()

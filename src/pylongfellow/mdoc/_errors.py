"""The mdoc surface's errors: the namespace base, the concrete exceptions, and their code enums."""

from enum import IntEnum

from .._errors import LongfellowError


class ProverErrorCode(IntEnum):
    """Return codes from `run_mdoc_prover`."""

    MDOC_PROVER_SUCCESS = 0
    MDOC_PROVER_NULL_INPUT = 1
    MDOC_PROVER_INVALID_INPUT = 2
    MDOC_PROVER_CIRCUIT_PARSING_FAILURE = 3
    MDOC_PROVER_HASH_PARSING_FAILURE = 4
    MDOC_PROVER_WITNESS_CREATION_FAILURE = 5
    MDOC_PROVER_GENERAL_FAILURE = 6
    MDOC_PROVER_MEMORY_ALLOCATION_FAILURE = 7
    MDOC_PROVER_INVALID_ZK_SPEC_VERSION = 8
    MDOC_PROVER_ROOT_DECODING_FAILURE = 9
    MDOC_PROVER_DOCUMENTS_MISSING = 10
    MDOC_PROVER_DOCUMENT_0_MISSING = 11
    MDOC_PROVER_DOCTYPE_MISSING = 12
    MDOC_PROVER_ISSUER_SIGNED_MISSING = 13
    MDOC_PROVER_ISSUER_AUTH_MISSING = 14
    MDOC_PROVER_MSO_MISSING = 15
    MDOC_PROVER_NSIG_MISSING = 16
    MDOC_PROVER_NAMESPACES_MISSING = 17
    MDOC_PROVER_DEVICE_SIGNED_MISSING = 18
    MDOC_PROVER_DEVICE_AUTH_MISSING = 19
    MDOC_PROVER_DEVICE_SIGNATURE_MISSING = 20
    MDOC_PROVER_DEVICE_KEY_MISSING = 21
    MDOC_PROVER_MSO_DECODING_FAILURE = 22
    MDOC_PROVER_VALIDITY_INFO_MISSING = 23
    MDOC_PROVER_DEVICE_KEY_INFO_MISSING = 24
    MDOC_PROVER_ATTRIBUTE_DECODE_FAILURE = 25
    MDOC_PROVER_ATTRIBUTE_EI_MISSING = 26
    MDOC_PROVER_ATTRIBUTE_EV_MISSING = 27
    MDOC_PROVER_ATTRIBUTE_DID_MISSING = 28
    MDOC_PROVER_SIGNATURE_FAILURE = 29
    MDOC_PROVER_DEVICE_SIGNATURE_FAILURE = 30
    MDOC_PROVER_ATTRIBUTE_NOT_FOUND = 31
    MDOC_PROVER_ATTRIBUTE_TOO_LONG = 32
    MDOC_PROVER_TAGGED_MSO_TOO_BIG = 33
    MDOC_PROVER_VERSION_NOT_SUPPORTED = 34
    MDOC_PROVER_ATTRIBUTE_RANDOM_MISSING = 35


class VerifierErrorCode(IntEnum):
    """Return codes from `run_mdoc_verifier`."""

    MDOC_VERIFIER_SUCCESS = 0
    MDOC_VERIFIER_CIRCUIT_PARSING_FAILURE = 1
    MDOC_VERIFIER_PROOF_TOO_SMALL = 2
    MDOC_VERIFIER_HASH_PARSING_FAILURE = 3
    MDOC_VERIFIER_SIGNATURE_PARSING_FAILURE = 4
    MDOC_VERIFIER_GENERAL_FAILURE = 5
    MDOC_VERIFIER_NULL_INPUT = 6
    MDOC_VERIFIER_INVALID_INPUT = 7
    MDOC_VERIFIER_ARGUMENTS_TOO_SMALL = 8
    MDOC_VERIFIER_ATTRIBUTE_NUMBER_MISMATCH = 9
    MDOC_VERIFIER_INVALID_ZK_SPEC_VERSION = 10
    MDOC_VERIFIER_INVALID_CBOR = 11


class CircuitGenerationErrorCode(IntEnum):
    """Return codes from `generate_circuit`."""

    CIRCUIT_GENERATION_SUCCESS = 0
    CIRCUIT_GENERATION_NULL_INPUT = 1
    CIRCUIT_GENERATION_ZLIB_FAILURE = 2
    CIRCUIT_GENERATION_GENERAL_FAILURE = 3
    CIRCUIT_GENERATION_INVALID_ZK_SPEC_VERSION = 4


class Error(LongfellowError):
    """Base class for errors raised by the mdoc surface."""


class ProverError(Error):
    """A prover call failed; `code` is a `ProverErrorCode`."""

    def __init__(self, code: ProverErrorCode) -> None:
        self.code = code
        super().__init__(f"{code.name} ({code.value})")


class VerifierError(Error):
    """A verifier call failed; `code` is a `VerifierErrorCode`."""

    def __init__(self, code: VerifierErrorCode) -> None:
        self.code = code
        super().__init__(f"{code.name} ({code.value})")


class CircuitError(Error):
    """Circuit generation failed; `code` is a `CircuitGenerationErrorCode`."""

    def __init__(self, code: CircuitGenerationErrorCode) -> None:
        self.code = code
        super().__init__(f"{code.name} ({code.value})")

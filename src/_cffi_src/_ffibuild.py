"""cffi build script — emits the extension C source for CMake to compile.

Run by the CMake build (`add_custom_command`) with the output path as argv[1].
It does not compile anything itself; CMake compiles the emitted source and links
it against the static upstream library.

The cdef below mirrors the C ABI of the pinned upstream header
(vendor/longfellow-zk/lib/circuits/mdoc/mdoc_zk.h at tag v0.9). It is transcribed
by hand; if the submodule is bumped, re-check it against the header.
"""

import sys

from cffi import FFI

ffibuilder = FFI()

ffibuilder.cdef(
    r"""
typedef struct {
    uint8_t namespace_id[64];
    uint8_t id[32];
    uint8_t cbor_value[64];
    size_t namespace_len, id_len, cbor_value_len;
} RequestedAttribute;

typedef struct {
    const char* system;
    char circuit_hash[65];
    size_t num_attributes;
    size_t version;
    size_t block_enc_hash, block_enc_sig;
} ZkSpecStruct;

typedef enum {
    MDOC_PROVER_SUCCESS = 0,
    MDOC_PROVER_NULL_INPUT,
    MDOC_PROVER_INVALID_INPUT,
    MDOC_PROVER_CIRCUIT_PARSING_FAILURE,
    MDOC_PROVER_HASH_PARSING_FAILURE,
    MDOC_PROVER_WITNESS_CREATION_FAILURE,
    MDOC_PROVER_GENERAL_FAILURE,
    MDOC_PROVER_MEMORY_ALLOCATION_FAILURE,
    MDOC_PROVER_INVALID_ZK_SPEC_VERSION,
    MDOC_PROVER_ROOT_DECODING_FAILURE,
    MDOC_PROVER_DOCUMENTS_MISSING,
    MDOC_PROVER_DOCUMENT_0_MISSING,
    MDOC_PROVER_DOCTYPE_MISSING,
    MDOC_PROVER_ISSUER_SIGNED_MISSING,
    MDOC_PROVER_ISSUER_AUTH_MISSING,
    MDOC_PROVER_MSO_MISSING,
    MDOC_PROVER_NSIG_MISSING,
    MDOC_PROVER_NAMESPACES_MISSING,
    MDOC_PROVER_DEVICE_SIGNED_MISSING,
    MDOC_PROVER_DEVICE_AUTH_MISSING,
    MDOC_PROVER_DEVICE_SIGNATURE_MISSING,
    MDOC_PROVER_DEVICE_KEY_MISSING,
    MDOC_PROVER_MSO_DECODING_FAILURE,
    MDOC_PROVER_VALIDITY_INFO_MISSING,
    MDOC_PROVER_DEVICE_KEY_INFO_MISSING,
    MDOC_PROVER_ATTRIBUTE_DECODE_FAILURE,
    MDOC_PROVER_ATTRIBUTE_EI_MISSING,
    MDOC_PROVER_ATTRIBUTE_EV_MISSING,
    MDOC_PROVER_ATTRIBUTE_DID_MISSING,
    MDOC_PROVER_SIGNATURE_FAILURE,
    MDOC_PROVER_DEVICE_SIGNATURE_FAILURE,
    MDOC_PROVER_ATTRIBUTE_NOT_FOUND,
    MDOC_PROVER_ATTRIBUTE_TOO_LONG,
    MDOC_PROVER_TAGGED_MSO_TOO_BIG,
    MDOC_PROVER_VERSION_NOT_SUPPORTED,
    MDOC_PROVER_ATTRIBUTE_RANDOM_MISSING,
} MdocProverErrorCode;

typedef enum {
    MDOC_VERIFIER_SUCCESS = 0,
    MDOC_VERIFIER_CIRCUIT_PARSING_FAILURE,
    MDOC_VERIFIER_PROOF_TOO_SMALL,
    MDOC_VERIFIER_HASH_PARSING_FAILURE,
    MDOC_VERIFIER_SIGNATURE_PARSING_FAILURE,
    MDOC_VERIFIER_GENERAL_FAILURE,
    MDOC_VERIFIER_NULL_INPUT,
    MDOC_VERIFIER_INVALID_INPUT,
    MDOC_VERIFIER_ARGUMENTS_TOO_SMALL,
    MDOC_VERIFIER_ATTRIBUTE_NUMBER_MISMATCH,
    MDOC_VERIFIER_INVALID_ZK_SPEC_VERSION,
    MDOC_VERIFIER_INVALID_CBOR,
} MdocVerifierErrorCode;

typedef enum {
    CIRCUIT_GENERATION_SUCCESS = 0,
    CIRCUIT_GENERATION_NULL_INPUT,
    CIRCUIT_GENERATION_ZLIB_FAILURE,
    CIRCUIT_GENERATION_GENERAL_FAILURE,
    CIRCUIT_GENERATION_INVALID_ZK_SPEC_VERSION,
} CircuitGenerationErrorCode;

MdocProverErrorCode run_mdoc_prover(
    const uint8_t* bcp, size_t bcsz,
    const uint8_t* mdoc, size_t mdoc_len,
    const char* pkx, const char* pky,
    const uint8_t* transcript, size_t tr_len,
    const RequestedAttribute* attrs, size_t attrs_len,
    const char* now,
    uint8_t** prf, size_t* proof_len, const ZkSpecStruct* zk_spec_version);

MdocVerifierErrorCode run_mdoc_verifier(
    const uint8_t* bcp, size_t bcsz,
    const char* pkx, const char* pky,
    const uint8_t* transcript, size_t tr_len,
    const RequestedAttribute* attrs, size_t attrs_len,
    const char* now,
    const uint8_t* zkproof, size_t proof_len, const char* docType,
    const ZkSpecStruct* zk_spec_version);

CircuitGenerationErrorCode generate_circuit(
    const ZkSpecStruct* zk_spec_version, uint8_t** cb, size_t* clen);

int circuit_id(uint8_t id[], const uint8_t* bcp, size_t bcsz,
               const ZkSpecStruct* zk_spec);

const ZkSpecStruct* find_zk_spec(const char* system_name,
                                 const char* circuit_hash);

extern const ZkSpecStruct kZkSpecs[12];

// cffi owns the malloc'd outputs of run_mdoc_prover (prf) and generate_circuit
// (cb); declare free so the wrapper can release them.
void free(void* ptr);
"""
)

ffibuilder.set_source("pylongfellow._longfellow", r'#include "mdoc_zk.h"')


if __name__ == "__main__":
    ffibuilder.emit_c_code(sys.argv[1])

// Extract one entry from the vendored mdoc test corpus into a clean prove
// fixture (tests/data/mdoc_<name>.json) — the C++ analogue of
// extract_device_response.py. Run once; re-run on a submodule bump.
//
//   g++ -std=c++17 -I vendor/longfellow-zk/lib scripts/extract_mdoc.cc -o /tmp/extract_mdoc
//   /tmp/extract_mdoc 15 > tests/data/mdoc_eu_av.json
//   cp vendor/longfellow-zk/lib/circuits/mdoc/circuits/8d079211* tests/data/circuits/

#include <cstdio>
#include <cstdlib>

#include "circuits/mdoc/mdoc_examples.h"
#include "circuits/mdoc/mdoc_test_attributes.h"

using namespace proofs;

// v7 / 1-attribute circuit (the latest) — what we prove and verify against.
static const char* kCircuitHash =
    "8d079211715200ff06c5109639245502bfe94aa869908d31176aae4016182121";

static void hex(const uint8_t* p, size_t n) {
  for (size_t i = 0; i < n; i++) printf("%02x", p[i]);
}

int main(int argc, char** argv) {
  int i = argc > 1 ? atoi(argv[1]) : 15;
  const MdocTests& t = mdoc_tests[i];
  const RequestedAttribute& a = test::age_over_18;  // claim paired with EUAV in mdoc_zk_test.cc

  printf("{\n");
  printf("  \"source\": \"vendor/longfellow-zk/lib/circuits/mdoc/mdoc_examples.h (mdoc_tests[%d])\",\n", i);
  printf("  \"system\": \"longfellow-libzk-v1\",\n");
  printf("  \"circuit_hash\": \"%s\",\n", kCircuitHash);
  printf("  \"doctype\": \"%s\",\n", t.doc_type);
  printf("  \"timestamp\": \"%s\",\n", (const char*)t.now);
  printf("  \"issuer_pk_x\": \"%s\",\n", t.pkx.as_pointer + 2);  // strip the 0x prefix
  printf("  \"issuer_pk_y\": \"%s\",\n", t.pky.as_pointer + 2);
  printf("  \"transcript_hex\": \"");
  hex(t.transcript, t.transcript_size);
  printf("\",\n");
  printf("  \"mdoc_hex\": \"");
  hex(t.mdoc, t.mdoc_size);
  printf("\",\n");
  printf("  \"attrs\": [{\"namespace\": \"%.*s\", \"id\": \"%.*s\", \"cbor_value_hex\": \"",
         (int)a.namespace_len, (const char*)a.namespace_id,
         (int)a.id_len, (const char*)a.id);
  hex(a.cbor_value, a.cbor_value_len);
  printf("\"}]\n");
  printf("}\n");
  return 0;
}

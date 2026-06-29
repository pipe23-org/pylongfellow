# Test data

The files in this directory back the test fixtures in `tests/conftest.py`, generated
from test data in the `vendor/longfellow-zk` submodule (see the table below). Circuits
used for testing reside in `tests/data/circuits/`.

| File | Type | Claim | Source (in `vendor/longfellow-zk/`) | Generator |
|---|---|---|---|---|
| `proof_age_over_18.json` | proof | `age_over_18` = true | `reference/verifier-service/server/examples/post1.json` | `extract_device_response.py` |
| `mdoc_eu_av.json` | mdoc | `age_over_18` = true | `lib/circuits/mdoc/mdoc_examples.h` (`mdoc_tests[15]`) | `extract_mdoc.cc` |

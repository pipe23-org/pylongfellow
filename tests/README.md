# tests/

The suite tests the backends (`google-cpp`, `isrg-rust`) pairwise against a set of test
fixtures.

## api/

`api/` tests pylongfellow's own API: circuit loading, presentation creation, proving,
verification, marshalling, logging, and error handling. Its fixtures are in `data/`,
documented in `data/README.md`. A failure here means pylongfellow's own API broke.

## differential/

`differential/` runs a corpus of circuits (`circuits/`), presentations (`presentations/`),
and reject vectors (`reject-vectors/`) through both backends and compares the results.
`conftest.py` joins the corpus into the (circuit, presentation, prover, verifier) tuples
the tests parametrize over. A tuple the corpus cannot supply is parametrized as a skip.
`untestable-cases.json` is the committed list of those skips. A failure here means the
two implementations stopped agreeing.

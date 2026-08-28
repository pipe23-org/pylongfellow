# tests/

## api/

`api/` tests pylongfellow's own API: circuit loading, presentation creation, proving,
verification, marshalling, logging, and error handling. Its fixtures are in `data/`,
documented in `data/README.md`. A failure here means pylongfellow's own API broke.

## differential/

`differential/` runs the circuits, presentations, and proofs of the `longfellow-vectors`
package through both backends and compares the results. `conftest.py` declares the attribute
selection, the verification times, and the proof names expected to verify, then joins them
into the (circuit, presentation, prover, verifier) tuples the tests parametrize over. A
failure here means the two implementations stopped agreeing.

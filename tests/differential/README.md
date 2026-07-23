# Differential tests

Cross-implementation agreement tests over the backends in `pylongfellow.backends`. A test
proves with one backend and verifies with another over a shared corpus of circuits and
presentations. The failure these tests detect is disagreement between independent
implementations of the same proof scheme (draft-google-cfrg-libzk). The corpus doubles as an
observation record: which implementation accepts which circuit, kept under version control as
backends and circuit versions change.

## Test categories

- **interop tests** — the circuit is a committed corpus artifact loaded byte-identically into
  both backends; only the proof crosses implementations. A failure is in prove or verify.
- **generation tests** — the circuit is produced at test time by `generate_circuit` on a
  backend whose `can_generate` is `True`. A failure decomposes in order: a changed
  `circuit_id` is generation drift; a changed byte hash with a stable `circuit_id` is a
  serialization change, reported without failing the test; a cross prove/verify failure is
  scored as in the interop category.

## Backend set

Backends are a set. Cross-tests are computed over every compatible (prover backend, verifier
backend) pair at collection time. No test names a specific pair. An added backend adds matrix
rows.

## Pass criteria

A passing run means every valid proof was accepted and every corrupted control was rejected.
Every verify input (transcript, mdoc bytes, issuer key, `device_namespaces`) is extracted from
the presentation it belongs to and travels with it. No test borrows an input from another
presentation.

## Corpus layout

```
tests/differential/
  circuits/
    v7-1attr.circuit + v7-1attr.json
    v6-1attr.circuit + v6-1attr.json
  presentations/
    age-over-18/
      presentation.json
      google-cpp-v7.proof + google-cpp-v7.json
      isrg-v6.proof + isrg-v6.json
```

- The corpus is data. Behaviour lives in `pylongfellow`; the corpus never grows methods.
- Circuits: one reference serialization per (version, attribute count), named
  `v{version}-{count}attr.circuit`. A byte-hash segment is appended to the stem only when two
  serializations of one (version, count) are held.
- Proofs: `{prover}-v{version}.proof`, where `{prover}` is the backend registry name.
- Presentations: one directory per disclosure, containing a self-describing
  `presentation.json`.
- Names are lowercase and hyphenated. A sidecar shares the full stem of its artifact.
- A committed circuit's origin cites an immutable ref (commit or tag). Circuits generated from
  a current checkout are not committed; they are generated at test time and compared against
  the committed reference.

## Sidecars

Every `.circuit` and `.proof` has a same-stem `.json` sidecar. Sidecars are JSON. No pickle,
no format bound to a language or a class.

- Circuit sidecar: `system`, `circuit_id` (with `computed_by` provenance), `byte_sha256`,
  `version`, `num_attributes`, `block_enc_hash`, `block_enc_sig`, `origin`.
- Proof sidecar: `prover`, `prover_source`, `circuit_id`, `circuit_byte_sha256`,
  `byte_sha256`, `origin`.
- `presentation.json` carries `doctype`, the attributes, the transcript, the issuer key, the
  timestamp, and `origin`. A presentation captured with its mdoc carries the mdoc bytes and
  the `device_namespaces` extracted from them; a verify-only capture without device namespaces
  omits both fields.

A circuit's identity is its spec fields plus `byte_sha256`. `circuit_id` is a sourced claim,
verified once at admission and recorded with the backend and pin that computed it.
`byte_sha256` is verified on every run.

## Admission

Artifacts enter the corpus through `scripts/admit.py`.

- `generate` runs a pinned generator and writes the blob, its hashes, and the sidecar. The
  result is reproducible by re-running against the pin.
- `import` copies an externally produced artifact and writes a sidecar whose `origin` records
  the source repository, ref, and capture date.

Both modes write the same sidecar schema.

## Pairing

Pairing is computed in `conftest.py` at collection time. Sidecars are read into plain records,
and compatible (circuit, presentation, prover backend, verifier backend) tuples are generated
over the backend set. Directory nesting carries no pairing semantics.

## Integrity

An integrity test checks on every run: every `.circuit` and `.proof` has a same-stem `.json`;
every sidecar's `byte_sha256` matches its file; every proof's `circuit_id` names a circuit in
`circuits/` and its `circuit_byte_sha256` matches that circuit's sidecar; every presentation's
`circuit_id` names a circuit in `circuits/` and its attribute count matches the circuit;
every presentation with mdoc bytes carries `device_namespaces`. `circuit_id` claims are
checked at admission, not per run.

## Pinned and floating runs

Pinned and floating describe the environment (the submodule checkout), not the test. The same
tests run in both. On `main` the submodules are pinned. Test names never carry `pinned` or
`head`.

## Running

The cross-verification tests are marked `slow`; the full suite is
`uv run pytest -m "slow or not slow"`. The isrg backend must be built first
(`uv run python scripts/build_isrg_backend.py`) or the cross-tests skip.

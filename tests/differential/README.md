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
- **generation tests** — the latest circuit per attribute count is regenerated at test time by
  `generate_circuit` on a backend whose `can_generate` is `True`. The recomputed `circuit_id`
  must equal the committed sidecar's; a mismatch fails the case as generation drift. A changed
  decompressed byte hash at a stable `circuit_id` is a serialization change, emitted as an
  `ObservationWarning` that appears in the warnings summary without failing the case. The
  comparison is over decompressed bytes: the zstd envelope differs between upstream's export
  pipeline and the runtime generate path while wrapping an identical serialization, and it
  varies with zstd versions.

## Observations

An `ObservationWarning` records an event that breaks no contract. It is carried as a warning in
a passing run, never through the exit code. The generation tests hold the one warn site: a
decompressed serialization that changed while the `circuit_id` held. Warnings are events measured against the
corpus census, not standing states. Pin-tree runs are warning-free; a warning at the pin is a
reproducibility break.

## Untestable cells

A cell whose inputs the corpus cannot supply is emitted as a skip carrying the reason. Two
classes occur:

- a verify-only capture carries no mdoc bytes, which the prover requires as input;
- a capture whose wire data carries no device namespaces cannot feed a verifier backend whose
  FFI takes `device_namespaces` as a required parameter (`isrg-rust`).

The cells are skips. An xfail executes the call and requires it to fail; these cells have no
call to execute without fabricating an input the wire format does not carry. Nothing in
`pylongfellow` defaults or supplies the missing input.

Untestable cells carry no `slow` mark, so they appear in the summary of every run, fast or
full. The cell id is repeated inside the skip reason because pytest groups summary lines by
(location, reason).

The full set of (cell id, reason) is committed in `untestable-cells.json` and asserted by the
integrity test, so the set cannot grow or shrink without a diff. Rewrite it after a corpus or
backend-set change:

```
uv run python -c "import json;from tests.differential.conftest import UNTESTABLE_CELLS as c;print(json.dumps(list(c),indent=2))" > tests/differential/untestable-cells.json
```

## Backend set

Backends are a set. Cross-tests are computed over every (prover backend, verifier
backend) pair at collection time. No test names a specific pair. An added backend adds matrix
rows.

## Pass criteria

A passing run means every valid proof was accepted and every corrupted control was rejected.
Every verify input (transcript, mdoc bytes, issuer key, `device_namespaces`) is extracted from
the presentation it belongs to and travels with it. No test borrows an input from another
presentation.

## Corpus layout

The corpus lives in this directory: circuits in `circuits/`, presentations and their committed
proofs in `presentations/`, and the untestable-cell set in `untestable-cells.json`. Circuits and
proofs are opaque blobs, each with a JSON sidecar. The sidecar is the metadata of record for its
blob. The join reads the directory at collection time.

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
- `presentation.json` carries `system`, `doctype`, the attributes, the transcript, the issuer
  key, the timestamp, and `origin`. A presentation captured with its mdoc carries the mdoc bytes and
  the `device_namespaces` extracted from them; a verify-only capture without device namespaces
  omits both fields.

A circuit's identity is its spec fields plus `byte_sha256`. `circuit_id` is a sourced claim,
verified once when the artifact is written and recorded with the backend and pin that computed it.
`byte_sha256` is verified on every run.

## Adding artifacts

Artifacts enter the corpus through `scripts/add_test_data.py`.

- `generate` runs a pinned generator and writes the blob, its hashes, and the sidecar. The
  result is reproducible by re-running against the pin.
- `import` copies an externally produced artifact and writes a sidecar whose `origin` records
  the source repository, ref, and capture date.
- `create-presentation` builds a credential with `mdoc.testing.create_credential` (fresh keys per
  run) and writes its presentation through the same extraction path as captures. This is the
  origin for inputs no deployed wallet produces, e.g. non-empty device namespaces.

All modes write the same schemas.

## Pairing

Pairing is computed in `conftest.py` at collection time. Sidecars are read into plain records,
and (circuit, presentation, prover backend, verifier backend) tuples are generated over the
backend set. A presentation pairs with every circuit whose attribute count matches; a committed
proof pairs with the circuit its sidecar's `circuit_id` names. Directory nesting carries no
pairing semantics. A tuple the corpus cannot supply inputs for is emitted as an untestable
cell, never dropped.

## Integrity

An integrity test checks on every run: every `.circuit` and `.proof` has a same-stem `.json`;
every sidecar's `byte_sha256` matches its file; every proof's `circuit_id` names a circuit in
`circuits/` and its `circuit_byte_sha256` matches that circuit's sidecar; every presentation's
`circuit_id` names a circuit in `circuits/` and its attribute count matches the circuit;
every presentation with mdoc bytes carries `device_namespaces`; the untestable cells the join
emits match `untestable-cells.json` exactly. `circuit_id` claims are checked when the artifact
is written, not per run.

## Recorded divergences

Divergences observed by this suite between backends. An entry states the observed behaviour,
the corpus entry that exhibits it, and the source locations of the differing code.

### device namespaces

- Observed: over `presentations/device-namespaces-nonempty/` (a credential whose device
  signed a non-empty `DeviceNameSpaces` map), isrg-rust proves and verifies on both
  1-attribute circuits; google-cpp fails as prover with
  `MDOC_PROVER_DEVICE_SIGNATURE_FAILURE` (30) and rejects the valid isrg-rust proof as
  verifier with `MDOC_VERIFIER_GENERAL_FAILURE` (5). The codes are defined in
  `lib/circuits/mdoc/mdoc_zk.h`; they are run-time observations, not suite assertions. The
  circuit blobs loaded into both backends are byte-identical.
- Mechanism: `DeviceNameSpacesBytes` is not a circuit input. Both implementations hash the
  four-element `DeviceAuthentication` structure outside the circuit and bind the digest as a
  public input. google/longfellow-zk assembles it over the constant `D8 18 41 A0` (tag 24
  wrapping an empty map) in `compute_transcript_hash` — pin `fe83ec6`:
  `lib/circuits/mdoc/mdoc_witness.h:413`, prover call `:597`, caller
  `lib/circuits/mdoc/mdoc_zk.cc:200` (`fill_public_inputs`); unchanged at upstream HEAD
  `3dfaac7` (`mdoc_witness.h:466`); the next-generation Rust implementation at `598816b`
  carries the same constant (`rust/applications/mdoc_zk/circuits/src/cbor/mdoc.rs:354`).
  abetterinternet/zk-cred-longfellow (`4f3d1b3`) takes the value as a prove and verify
  parameter (`src/mdoc_zk/mod.rs:676`; prover side `src/mdoc_zk/mdoc/mod.rs:193`).
- Scope: deployed wallets emit the empty map, over which the backends agree; the constant is
  consistent with a restriction to that deployed profile. The google-cpp cells are strict
  xfails in the pairing join, with the source citation in the reason string; an upstream
  change that stops the failure surfaces as an unexpected pass and fails the run.

## Pinned and floating runs

Pinned and floating describe the environment (the submodule checkout), not the test. The same
tests run in both. On `main` the submodules are pinned. Test names never carry `pinned` or
`head`.

## Running

A case involving the isrg-rust backend is marked `slow`; the full suite is
`uv run pytest -m "slow or not slow"`. `uv sync` builds both backends; a case whose backend is
not built skips.

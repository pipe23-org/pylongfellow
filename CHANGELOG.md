# Changelog

## Unreleased

- **BACKWARDS INCOMPATIBLE:** `Pylongfellow.load_circuit` now takes
  `(circuit, version, num_attributes)` in place of a `CircuitSpec` and the circuit bytes.
- **BACKWARDS INCOMPATIBLE:** Removed `pylongfellow.mdoc.CircuitSpec`, replaced by
  `pylongfellow.backends.google_cpp.ZkSpec`, the type `find_zk_spec` and `zk_specs` return.
- **BACKWARDS INCOMPATIBLE:** Removed `Pylongfellow.generate_circuit`, replaced by
  `pylongfellow.backends.google_cpp.generate_circuit(version, num_attributes)`.
- **BACKWARDS INCOMPATIBLE:** The `Backend` protocol's `load_circuit` now takes
  `(circuit, version, num_attributes)`, and its `can_generate` and `generate_circuit` members
  are removed, along with `GenerationUnsupportedError` and `CircuitIdUnsupportedError` from
  `pylongfellow.backends`.
- Removed `circuit_id` from the isrg-rust backend and the build-time patch to the vendored
  crate that added a `circuit_id` export (#50).
- Moved the native build inputs to `native/`, one directory per backend;
  `scripts/build_isrg_rust_backend.py` is now `native/isrg-rust/build.py` (#49).
- Added a pinned-hash test over the vendored `mdoc_zk.h` header that the cffi cdef
  transcribes (#49).

## 0.5.2 - 2026-08-07

- Bumped the zk-cred-longfellow pin to b22d84e and removed the uniffi patch (#47).

## 0.5.1 - 2026-08-07

- Added a uniffi patch to (temporarily) resolve #43 (#44).
- Bumped the zk-cred-longfellow pin to 3485a3c (#45).

## 0.5.0

Breaking API changes and a documentation overhaul. The release carries the rewritten README
and docs to the PyPI project page.

- **Breaking: `prove` and `verify` no longer take a circuit handle** — they use the
  circuit from `load_circuit`, which stores it on the instance and returns `None`.
  `mdoc.CircuitHandle` is removed. `Backend` implementations pass the loaded circuit as
  an opaque `state` object.
- **Breaking: `load_circuit(spec, circuit)`** — the second parameter was `compressed`.
  Same rename in the `Backend` protocol.
- **Breaking: `prove` and `verify` take `issuer_public_key`, a `mdoc.PublicKey`** — was
  `issuer_pk`, an `(x, y)` tuple. Also in the `Backend` protocol.
- **Breaking: `prove` and `verify` take `claims`** — was `attrs`. Also in the `Backend`
  protocol.
- **Breaking: `pylongfellow.mdoc.testing`** — `create_credential`, `create_certificate`,
  `sign_device_authentication`, `verify_device_authentication`, and `CreatedCredential`
  move there from `pylongfellow.mdoc`. `create_credential` is renamed
  `create_presentation`, `CreatedCredential` is renamed `PresentationSpecimen`, and the
  specimen's `issuer_key` field and `issuer_pk` property are replaced by
  `issuer_public_key`.
- **Breaking: `PYLONGFELLOW_GOOGLE_CPP_LOG_LEVEL`** — replaces `PYLONGFELLOW_LOG_LEVEL`;
  it configures the google-cpp backend only.
- The distribution `description`, package docstring, docs landing page, and mkdocs
  `site_description` read "Python interface to implementations of Longfellow
  zero-knowledge proofs over ISO 18013-5 mdoc credentials".
- The README is cut to Installation, Usage, Documentation, and Licensing; the removed
  sections move to the docs site, the code, or the tracker.
- The API reference renders per-backend behaviour from the docstrings; the development
  page opens with the dev-loop commands.
- Examples and tests name instances `longfellow`, `prover`, and `verifier`; `client` is
  gone from the documentation vocabulary.
- The `Documentation` project URL points at
  `https://pylongfellow.readthedocs.io/en/stable/`
  ([#34](https://github.com/pipe23-org/pylongfellow/pull/34)).

## 0.4.0

Every wheel now ships both backends. The isrg-rust cdylib (abetterinternet/zk-cred-longfellow,
pinned at `4f3d1b3`) is built into the cp311–cp314 wheels alongside the google-cpp extension;
`Pylongfellow(backend="isrg-rust")` works from a plain `pip install pylongfellow`.

- **`[isrg-rust]` extra removed** — `zstandard` is a runtime dependency; the extra pulled
  nothing else. `pip install pylongfellow[isrg-rust]` now warns about an unknown extra and
  installs the same package.
- **Licence expression `Apache-2.0 AND MPL-2.0`** — the wheel carries the compiled MPL-2.0
  cdylib, so the distribution metadata names both licences and ships all three licence texts.
  See the README's Licensing section. `pylongfellow`'s own code stays Apache-2.0.
- **Per-backend build switches** — source builds take
  `-C cmake.define.PYLONGFELLOW_BUILD_ISRG=OFF` or
  `-C cmake.define.PYLONGFELLOW_BUILD_GOOGLE=OFF` to omit one backend; the omitted backend
  raises `BackendUnavailableError` at first use. Default source builds require both toolchains
  (C++ and cargo).
- **`scripts/build_isrg_rust_backend.py` runs inside the CMake build** — `uv sync` and wheel
  builds produce the backend without a separate step; the script still works standalone for
  incremental dev builds.
- **musllinux builds set `RUSTFLAGS="-C target-feature=-crt-static"`** — the musl target's
  default static CRT drops the `cdylib` crate type, so cargo builds no `.so` without it. The
  build script fails with a named error when cargo produces no cdylib.

## 0.3.0

Breaking. The module-level `mdoc` functions are replaced by an instantiated client:
`Pylongfellow(backend=...)` binds one backend at construction, and circuit operations are
methods on it. Adds the `pylongfellow.backends` submodule and a second backend over
abetterinternet/zk-cred-longfellow (ISRG). Wheels ship the `google-cpp` backend only.

### Breaking

- **`Pylongfellow(*, backend)`** — new entry point, exported from the package root. `backend`
  is required: a registry name (`"google-cpp"`, `"isrg-rust"`) or a `Backend` instance. Construction
  raises `ValueError` for an unknown name and `BackendUnavailableError` when the backend's
  native dependency is not built. There is no default backend.
- **`mdoc.load_circuit`, `mdoc.prove`, `mdoc.verify`, `mdoc.generate_circuit`** — removed; use
  the client methods. `mdoc` keeps the data types and errors.
- **`mdoc.ZkSpec` → `mdoc.CircuitSpec`** — the circuit-spec dataclass is renamed. Field names
  are unchanged.
- **`mdoc.circuit_id`, `mdoc.find_zk_spec`, `mdoc.zk_specs`** — moved to
  `pylongfellow.backends.google_cpp`; they read that backend's compiled-in spec table. `mdoc`
  no longer binds any backend.
- **`.prove(handle, mdoc, issuer_pk, transcript, attrs, timestamp)`** — was
  `prove(circuit, mdoc, issuer_pk, transcript, attrs, timestamp, spec)` in 0.2.x. The leading
  `circuit` bytes and trailing `spec` are replaced by `handle`, from `.load_circuit`.
- **`.verify(handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, *, device_namespaces=None)`**
  — was `verify(circuit, issuer_pk, transcript, attrs, timestamp, proof, doctype, spec)` in
  0.2.x. The leading `circuit` bytes and trailing `spec` are replaced by `handle`.
  `device_namespaces` (`bytes | None`) is new and keyword-only: the inner bytes of the tag-24
  `DeviceNameSpacesBytes`, required by the `isrg-rust` backend and ignored by `google-cpp`.
- **`ProverError.code`, `VerifierError.code`** — now `Optional`. The `google-cpp` backend
  populates the code; the `isrg-rust` backend leaves it `None`. Catch by class. Both exceptions
  accept a keyword-only `message`.

### Added

- **`pylongfellow.backends`** — the `Backend` protocol (the SPI), `CircuitHandle`,
  `get_backend`, `GenerationUnsupportedError`, and `BackendUnavailableError`. Registry names
  distinguish implementation, not just institution: `google-cpp` and `isrg-rust` are registered,
  `google-rust` is reserved for upstream's next-generation Rust implementation.
- **`google-cpp`** (`backends.google_cpp.BACKEND`) — the backend over the vendored
  google/longfellow-zk C++ library. `can_generate` is `True`. Checks at load that
  `spec.circuit_hash` matches the circuit bytes.
- **`isrg-rust`** (`backends.isrg_rust.BACKEND`) — a backend over
  [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
  (ISRG; vendored submodule, MPL-2.0). `can_generate` is `False`: circuits come from a
  `google-cpp` client or from disk. Circuit identity checking is backend-native behaviour:
  this backend does not check `spec.circuit_hash` at load. Source-build only; run
  `uv run python scripts/build_isrg_rust_backend.py` (needs cargo 1.85 or newer for edition 2024). The
  `isrg-rust` extra (`pip install pylongfellow[isrg-rust]`) adds `zstandard`. Not shipped in wheels.

### Recorded divergence

- **Device namespaces in ZK verification** — the differential suite records a divergence
  between the backends over the mdoc `DeviceNameSpacesBytes` value. `DeviceNameSpacesBytes`
  is not a circuit input: both implementations hash the `DeviceAuthentication` structure
  outside the circuit and bind the digest as a public input. google/longfellow-zk assembles
  it over the constant `D8 18 41 A0` (tag 24 wrapping an empty map) in
  `compute_transcript_hash`: at the vendored pin `fe83ec6`,
  `lib/circuits/mdoc/mdoc_witness.h:413`; unchanged at upstream HEAD `3dfaac7`
  (`mdoc_witness.h:466`); present in the next-generation Rust implementation at `598816b`,
  `rust/applications/mdoc_zk/circuits/src/cbor/mdoc.rs:354`.
  abetterinternet/zk-cred-longfellow at `4f3d1b3` takes the value as a prove and verify
  parameter (`src/mdoc_zk/mod.rs`). On a credential whose device signed a non-empty
  namespace map (`tests/differential/presentations/device-namespaces-nonempty/`), the
  isrg-rust backend proves and verifies on both 1-attribute circuits; the google-cpp
  backend fails as prover with `MDOC_PROVER_DEVICE_SIGNATURE_FAILURE` (30) and rejects the
  valid isrg-rust proof as verifier with `MDOC_VERIFIER_GENERAL_FAILURE` (5), codes as
  defined in `lib/circuits/mdoc/mdoc_zk.h` and observed at run time. The circuit blobs
  loaded into both backends are byte-identical. Deployed wallets emit an empty
  device-namespace map, over which the implementations agree. The full record is in
  `tests/differential/README.md`, Recorded divergences.

### Unchanged

- The vendored longfellow revision (v0.9, `fe83ec6`) is unchanged.

## 0.2.3

Backend-free test-credential construction in `pylongfellow.mdoc`. None of the new
functions load or call longfellow-zk; they run on `cryptography` and `cbor2`, which move
from the dev/test groups to runtime dependencies.

- **`mdoc.create_credential()`** — assembles an ISO 18013-5 `DeviceResponse` under locally
  held keys, with caller-controlled issuer-signed claims and device namespaces. Deployed
  wallets emit an empty device-namespace map; a created credential can carry a non-empty,
  device-signed one. The keys and the leaf certificate can be supplied or generated;
  the encoded output is checked against its own signatures before it is returned.
- **`mdoc.create_certificate()`** — builds one X.509 certificate of a test trust chain
  (CA or leaf), ECDSA over SHA-256.
- **`mdoc.sign_device_authentication()`** / **`mdoc.verify_device_authentication()`** —
  the `DeviceAuthentication` COSE signature over a session transcript, as a
  sign/check pair. Signing serves presenters that re-bind a credential to a fresh
  session transcript; checking validates any mdoc's device signature without a ZK
  backend.

## 0.2.2

- **`mdoc.zk_specs()`** — returns every ZkSpec compiled into the linked library, in table
  order, binding the `kZkSpecs` table. Consumers that select a spec by policy (system,
  version, num_attributes) can now enumerate what the build holds instead of resolving a
  known `circuit_hash` through `find_zk_spec`. The table includes superseded circuit
  versions; `generate_circuit` accepts only the highest version for a given
  `num_attributes`.

## 0.2.1

Input-contract hardening: several caller-input violations that the C library handled by
aborting the process (`SIGABRT`), silently misbehaving, or writing out of bounds are now
rejected with `ValueError` before any C call. Found by a systematic sweep of every input
crossing into C; guards added only where C did not already return a clean error.

- **`len(attrs) == spec.num_attributes`** — three of the four mismatch cases killed the
  process (array overfill on too many; Ligero subfield check on too few, prover side); only
  verify-with-too-few returned a clean error. The C entry points never read
  `spec.num_attributes`; the invariant is the circuit's attribute count, hash-pinned via the
  spec. Behaviour change: an empty `attrs` on `verify` now raises `ValueError` instead of
  `VerifierError(MDOC_VERIFIER_ARGUMENTS_TOO_SMALL)`.
- **Canonical spec** — `prove`, `verify`, and `generate_circuit` now reject a `ZkSpec` that is
  not the registered spec for its `(system, circuit_hash)`. The C code reads `version` and
  `block_enc_*` straight from the struct and aborted on non-canonical values even when the
  hash matched; a lying spec is now checked against the library's own table.
- **`circuit_hash` length** — a `circuit_hash` longer than the 65-byte C field was an
  out-of-bounds heap write (silent at 66–80 bytes, allocator abort beyond); now rejected in
  spec marshalling.
- **`doctype` length (`verify`)** — a doctype of 256 bytes or more was silently discarded and
  replaced by a default, verifying the proof against the wrong scope with no error; now
  rejected.

## 0.2.0

Breaking. The mdoc functions, types, and errors moved into the `pylongfellow.mdoc`
submodule. This
is a clean break: no deprecation shims, no top-level re-exports of the moved names. The old
`import pylongfellow as lf; lf.verify(...)` becomes `from pylongfellow import mdoc;
mdoc.verify(...)`.

### Moved (new address, same object)

- `pylongfellow.prove` → `pylongfellow.mdoc.prove`
- `pylongfellow.verify` → `pylongfellow.mdoc.verify`
- `pylongfellow.generate_circuit` → `pylongfellow.mdoc.generate_circuit`
- `pylongfellow.circuit_id` → `pylongfellow.mdoc.circuit_id`
- `pylongfellow.find_zk_spec` → `pylongfellow.mdoc.find_zk_spec`
- `pylongfellow.RequestedAttribute` → `pylongfellow.mdoc.RequestedAttribute`
- `pylongfellow.ZkSpec` → `pylongfellow.mdoc.ZkSpec`
- `pylongfellow.ProverError` → `pylongfellow.mdoc.ProverError`
- `pylongfellow.VerifierError` → `pylongfellow.mdoc.VerifierError`
- `pylongfellow.CircuitError` → `pylongfellow.mdoc.CircuitError`

### Renamed (`Mdoc` prefix removed)

- `pylongfellow.MdocProverErrorCode` → `pylongfellow.mdoc.ProverErrorCode`
- `pylongfellow.MdocVerifierErrorCode` → `pylongfellow.mdoc.VerifierErrorCode`
- `pylongfellow.CircuitGenerationErrorCode` → `pylongfellow.mdoc.CircuitGenerationErrorCode`
  (moved, name unchanged)

### Added

- `pylongfellow.mdoc.Error` — base class for exceptions raised by `pylongfellow.mdoc`; a
  subclass of `LongfellowError`. The hierarchy is
  `LongfellowError` → `mdoc.Error` → {`ProverError`, `VerifierError`, `CircuitError`}. Catch
  `LongfellowError` for anything from the package, `mdoc.Error` for anything from
  `pylongfellow.mdoc`, or a concrete class for one call. `.code` exists only on the concrete
  classes, typed as the matching enum.

### Changed

- `circuit_id` on unparseable bytes now raises `mdoc.Error` (previously the bare
  `LongfellowError`), so `except mdoc.Error` catches every failure an mdoc function raises.
  Code catching `LongfellowError` is unaffected.

### Unchanged

- `pylongfellow.LongfellowError` and `pylongfellow.__version__` stay at the top level.
- No function signatures, error behaviour, or native code changed: byte-for-byte the same
  functions at a new address. The vendored upstream longfellow revision is unchanged.

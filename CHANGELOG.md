# Changelog

## 0.3.0

Breaking. The module-level `mdoc` functions are replaced by an instantiated client:
`Pylongfellow(backend=...)` binds one backend at construction, and circuit operations are
methods on it. Adds the `pylongfellow.backends` submodule and a second backend over
abetterinternet/zk-cred-longfellow (ISRG). Wheels ship the `google-cpp` backend only.

### Breaking

- **`Pylongfellow(*, backend)`** — new entry point, exported from the package root. `backend`
  is required: a registry name (`"google-cpp"`, `"isrg"`) or a `Backend` instance. Construction
  raises `ValueError` for an unknown name and `BackendUnavailableError` when the backend's
  native dependency is not built. There is no default backend.
- **`mdoc.load_circuit`, `mdoc.prove`, `mdoc.verify`, `mdoc.generate_circuit`** — removed; use
  the client methods. `mdoc` keeps the data types, errors, and the spec-table functions
  (`circuit_id`, `find_zk_spec`, `zk_specs`).
- **`.prove(handle, mdoc, issuer_pk, transcript, attrs, timestamp)`** — was
  `prove(circuit, mdoc, issuer_pk, transcript, attrs, timestamp, spec)` in 0.2.x. The leading
  `circuit` bytes and trailing `spec` are replaced by `handle`, from `.load_circuit`.
- **`.verify(handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, *, device_namespaces=None)`**
  — was `verify(circuit, issuer_pk, transcript, attrs, timestamp, proof, doctype, spec)` in
  0.2.x. The leading `circuit` bytes and trailing `spec` are replaced by `handle`.
  `device_namespaces` (`bytes | None`) is new and keyword-only: the inner bytes of the tag-24
  `DeviceNameSpacesBytes`, required by the `isrg` backend and ignored by `google-cpp`.
- **`ProverError.code`, `VerifierError.code`** — now `Optional`. The `google-cpp` backend
  populates the code; the `isrg` backend leaves it `None`. Catch by class. Both exceptions
  accept a keyword-only `message`.

### Added

- **`pylongfellow.backends`** — the `Backend` protocol (the SPI), `CircuitHandle`,
  `get_backend`, `GenerationUnsupportedError`, and `BackendUnavailableError`. Registry names
  distinguish implementation, not just institution: `google-cpp` and `isrg` are registered,
  `google-rust` is reserved for upstream's next-generation Rust implementation.
- **`google-cpp`** (`backends.google.BACKEND`) — the backend over the vendored
  google/longfellow-zk C++ library. `can_generate` is `True`. Checks at load that
  `spec.circuit_hash` matches the circuit bytes.
- **`isrg`** (`backends.isrg.BACKEND`) — a backend over
  [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
  (ISRG; vendored submodule, MPL-2.0). `can_generate` is `False`: circuits come from a
  `google-cpp` client or from disk. Circuit identity checking is backend-native behaviour:
  this backend does not check `spec.circuit_hash` at load. Source-build only; run
  `uv run python scripts/build_isrg_backend.py` (needs cargo 1.85 or newer for edition 2024). The
  `isrg` extra (`pip install pylongfellow[isrg]`) adds `zstandard`. Not shipped in wheels.

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

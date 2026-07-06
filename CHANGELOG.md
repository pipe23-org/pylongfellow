# Changelog

## 0.2.1

- `prove` and `verify` now raise `ValueError` when `len(attrs) != spec.num_attributes`,
  before any C call. Previously three of the four mismatch cases killed the process with
  SIGABRT inside the C library (array overfill on too many attributes; the Ligero subfield
  check on too few, prover side); only verify-with-too-few returned a clean error. The C
  entry points never read `spec.num_attributes` — the invariant is the circuit's attribute
  count, for which the spec field is the hash-pinned proxy. Behaviour change: an empty
  `attrs` list on `verify` now raises `ValueError` instead of
  `VerifierError(MDOC_VERIFIER_ARGUMENTS_TOO_SMALL)`.

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

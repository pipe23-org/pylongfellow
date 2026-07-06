# Changelog

## 0.2.0

Breaking. The mdoc prover and verifier surface moved into a `pylongfellow.mdoc` namespace. This
is a clean break — no deprecation shims, no top-level re-exports of the moved names. The old
`import pylongfellow as lf; lf.verify(...)` becomes `from pylongfellow import mdoc;
mdoc.verify(...)`.

### Moved (mechanical rename — new address, same object)

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

### Renamed (the `Mdoc` prefix dies — the namespace carries it now)

- `pylongfellow.MdocProverErrorCode` → `pylongfellow.mdoc.ProverErrorCode`
- `pylongfellow.MdocVerifierErrorCode` → `pylongfellow.mdoc.VerifierErrorCode`
- `pylongfellow.CircuitGenerationErrorCode` → `pylongfellow.mdoc.CircuitGenerationErrorCode`
  (moved, name unchanged)

### Added

- `pylongfellow.mdoc.Error` — a contract-free namespace base subclassing `LongfellowError`, one
  per namespace. The error hierarchy is now
  `LongfellowError` → `mdoc.Error` → {`ProverError`, `VerifierError`, `CircuitError`}. Catch
  `LongfellowError` across every namespace, `mdoc.Error` for the mdoc surface, or a concrete for
  one call. `.code` exists only on the concretes, typed as the matching enum.

### Unchanged

- `pylongfellow.LongfellowError` and `pylongfellow.__version__` stay at the top level.
- No function signatures, error behaviour, or native code changed — byte-for-byte the same
  functions at a new address. The vendored upstream longfellow revision is unchanged.

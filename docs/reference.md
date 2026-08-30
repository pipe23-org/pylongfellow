# API Reference

## `pylongfellow`

::: pylongfellow.Pylongfellow
::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

### Data types

::: pylongfellow.mdoc.RequestedAttribute
::: pylongfellow.mdoc.PublicKey

### Errors

```
LongfellowError
└── mdoc.Error
    ├── ProverError      # .code: mdoc.ProverErrorCode or None
    ├── VerifierError    # .code: mdoc.VerifierErrorCode or None
    └── CircuitError     # .code: mdoc.CircuitGenerationErrorCode or None
```

::: pylongfellow.mdoc.Error
::: pylongfellow.mdoc.ProverError
::: pylongfellow.mdoc.VerifierError
::: pylongfellow.mdoc.CircuitError
::: pylongfellow.mdoc.ProverErrorCode
::: pylongfellow.mdoc.VerifierErrorCode
::: pylongfellow.mdoc.CircuitGenerationErrorCode

## `pylongfellow.backends`

A `Backend` implements one longfellow implementation. `Pylongfellow` takes a registry name
(`"google-cpp"`, `"isrg-rust"`) or a `Backend` instance.

::: pylongfellow.backends.Backend
    options:
      members: false
::: pylongfellow.backends.get_backend
::: pylongfellow.backends.BackendUnavailableError

### Backend scope

google-cpp and isrg-rust differ in the following behaviour.

- **Circuit identity at load.** Neither backend checks the circuit bytes against the declared
  version and attribute count, so a wrong circuit of the declared version and attribute count
  fails at prove or verify, not at load. google-cpp requires a compiled-in row with the
  declared version and attribute count. isrg-rust accepts version 6 or 7 and takes the
  attribute count as declared.
- **Circuit versions.** google-cpp accepts the versions in the compiled-in table: 5, 6, and 7
  at the v0.9 pin, each with attribute counts 1 to 4. isrg-rust accepts versions 6 and 7.
- **Circuit generation.** `google_cpp.generate_circuit` generates the highest table version
  for an attribute count. isrg-rust generates no circuits.
- **Claims count.** google-cpp requires `len(claims)` to equal the loaded circuit's attribute
  count on prove and verify. isrg-rust passes the claims through.
- **Namespace.** isrg-rust takes one namespace for all claims and raises `ValueError` on a
  mixed set. google-cpp takes a namespace per claim.
- **`device_namespaces`.** isrg-rust's verifier requires `device_namespaces`. google-cpp does
  not read it.
- **`doctype`.** google-cpp rejects a `doctype` of 256 bytes or longer.
- **Error codes.** `ProverError.code` and `VerifierError.code` carry a code on google-cpp and
  are None on isrg-rust.

## `pylongfellow.backends.google_cpp`

Binds the vendored google/longfellow-zk C++ library through cffi.

::: pylongfellow.backends.google_cpp.ZkSpec
::: pylongfellow.backends.google_cpp.circuit_id
::: pylongfellow.backends.google_cpp.find_zk_spec
::: pylongfellow.backends.google_cpp.zk_specs
::: pylongfellow.backends.google_cpp.generate_circuit

### Logging

**`PYLONGFELLOW_GOOGLE_CPP_LOG_LEVEL`** sets the stderr log level of google/longfellow-zk, read
once when the backend first loads in the process. Values (case-insensitive): `error`, `warning`,
`info`, `silent`. The default is `warning`, which hides upstream's per-call info output but
keeps genuine errors and warnings.

google/longfellow-zk logs to stderr, not through Python `logging`, and exposes no callback to
bridge. There is no Python API and no runtime reconfiguration. The isrg-rust backend emits no
log output.

## `pylongfellow.backends.isrg_rust`

Binds the vendored abetterinternet/zk-cred-longfellow Rust library through generated UniFFI
bindings.

## `pylongfellow.mdoc.testing`

### Functions

::: pylongfellow.mdoc.testing.create_presentation
::: pylongfellow.mdoc.testing.create_certificate
::: pylongfellow.mdoc.testing.sign_device_authentication
::: pylongfellow.mdoc.testing.verify_device_authentication

### Data types

::: pylongfellow.mdoc.testing.PresentationSpecimen

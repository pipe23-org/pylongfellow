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
(`"google-cpp"`, `"isrg-rust"`, `"lf-rust"`) or a `Backend` instance.

::: pylongfellow.backends.Backend
    options:
      members: false
::: pylongfellow.backends.get_backend
::: pylongfellow.backends.BackendUnavailableError

### Backend scope

The backends differ in the following behaviour.

- **Circuit versions.** google-cpp accepts versions 5, 6, and 7 at the de5f949 pin, each with
  attribute counts 1 to 4. lf-rust accepts versions 5 to 8 at the same pin, each with attribute
  counts 1 to 4. isrg-rust accepts versions 6 and 7.
- **Circuit generation.** `google_cpp.generate_circuit` generates the highest table version
  for an attribute count. `lf_rust.materialize_circuit` returns the archived circuit for
  versions 5 to 7 and compiles version 8. isrg-rust generates no circuits.
- **Claims count.** google-cpp and lf-rust require `len(claims)` to equal the loaded circuit's
  attribute count on prove and verify. isrg-rust passes the claims through.
- **`device_namespaces`.** isrg-rust's verifier requires `device_namespaces`. google-cpp and
  lf-rust fix DeviceNameSpacesBytes to the empty map, whatever the argument holds.
- **`doctype`.** google-cpp rejects a `doctype` of 256 bytes or longer.
- **Error codes.** `ProverError.code` and `VerifierError.code` carry a code from the backend's
  own table on google-cpp and lf-rust and are None on isrg-rust.

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

## `pylongfellow.backends.lf_rust`

Binds the Rust implementation in the vendored longfellow-zk/longfellow-zk repository through
generated UniFFI bindings. The backend is built only when `PYLONGFELLOW_BUILD_LF_RUST=ON`
(see [Development](development.md)).

::: pylongfellow.backends.lf_rust.materialize_circuit
::: pylongfellow.backends.lf_rust.ProverErrorCode
::: pylongfellow.backends.lf_rust.VerifierErrorCode

## `pylongfellow.mdoc.testing`

### Functions

::: pylongfellow.mdoc.testing.create_presentation
::: pylongfellow.mdoc.testing.create_certificate
::: pylongfellow.mdoc.testing.sign_device_authentication
::: pylongfellow.mdoc.testing.verify_device_authentication

### Data types

::: pylongfellow.mdoc.testing.PresentationSpecimen

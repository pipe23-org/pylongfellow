# API Reference

## `pylongfellow`

::: pylongfellow.Pylongfellow
::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

### Data types

::: pylongfellow.mdoc.RequestedAttribute
::: pylongfellow.mdoc.PublicKey
::: pylongfellow.mdoc.CircuitSpec

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
::: pylongfellow.backends.GenerationUnsupportedError
::: pylongfellow.backends.BackendUnavailableError

## `pylongfellow.backends.google_cpp`

Binds the vendored google/longfellow-zk C++ library through cffi.

::: pylongfellow.backends.google_cpp.circuit_id
::: pylongfellow.backends.google_cpp.find_zk_spec
::: pylongfellow.backends.google_cpp.zk_specs

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

::: pylongfellow.backends.isrg_rust.circuit_id

## `pylongfellow.mdoc.testing`

### Functions

::: pylongfellow.mdoc.testing.create_presentation
::: pylongfellow.mdoc.testing.create_certificate
::: pylongfellow.mdoc.testing.sign_device_authentication
::: pylongfellow.mdoc.testing.verify_device_authentication

### Data types

::: pylongfellow.mdoc.testing.PresentationSpecimen

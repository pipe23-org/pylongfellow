# API Reference

## `pylongfellow`

::: pylongfellow.Pylongfellow
::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The mdoc-specific data types and errors, and the test-credential functions, which run on
`cryptography` and `cbor2` without a backend.

### Functions

::: pylongfellow.mdoc.create_credential
::: pylongfellow.mdoc.create_certificate
::: pylongfellow.mdoc.sign_device_authentication
::: pylongfellow.mdoc.verify_device_authentication

### Data types

::: pylongfellow.mdoc.CircuitHandle
::: pylongfellow.mdoc.RequestedAttribute
::: pylongfellow.mdoc.CircuitSpec
::: pylongfellow.mdoc.CreatedCredential

### Errors

Each function raises its own exception on a failed call. When the backend supplies a return
code it is in the exception's `.code`, typed as the corresponding enum or None: the google-cpp
backend always supplies it, the isrg-rust backend leaves it None. Catch by class; do not
branch on the code. The
exceptions are subclasses of [`mdoc.Error`][pylongfellow.mdoc.Error], which is a subclass of
[`LongfellowError`][pylongfellow.LongfellowError]:

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

The backend SPI. A `Backend` implements load, generate, prove, and verify for one longfellow
implementation; `Pylongfellow` binds one at construction, by registry name (`google-cpp`,
`isrg-rust`) or instance. `prove` and `verify` dispatch through the backend a circuit was
loaded into: the `CircuitHandle` carries it, so a handle works on any client. A backend whose
native piece is not installed raises `BackendUnavailableError`.

::: pylongfellow.backends.Backend
::: pylongfellow.backends.get_backend
::: pylongfellow.backends.GenerationUnsupportedError
::: pylongfellow.backends.BackendUnavailableError

## google-cpp backend

Binds the vendored google/longfellow-zk C++ library through cffi. It proves, verifies, and
generates circuits. It supplies `.code` on the exceptions it raises and ignores
`device_namespaces` on `verify`. At load it checks that `spec.circuit_hash` matches the
circuit bytes and requires the whole spec record to match its compiled-in table.

`circuit_id` recomputes a circuit's canonical id from its bytes. `find_zk_spec` and `zk_specs`
read the backend's compiled-in spec table. All three are `google-cpp`-specific and require the
built native extension.

::: pylongfellow.backends.google_cpp.circuit_id
::: pylongfellow.backends.google_cpp.find_zk_spec
::: pylongfellow.backends.google_cpp.zk_specs

### Logging

**`PYLONGFELLOW_LOG_LEVEL`** sets the stderr log level of google/longfellow-zk, read once when
the `_longfellow` extension loads, following the `TF_CPP_MIN_LOG_LEVEL` / `GRPC_VERBOSITY`
convention. Values (case-insensitive): `error`, `warning`, `info`, `silent`. The default is
`warning`, which hides upstream's per-call info output but keeps genuine errors and warnings.

google/longfellow-zk logs to stderr, not through Python `logging`, and exposes no callback to
bridge. There is no Python API and no runtime reconfiguration. It affects the google-cpp
backend only.

## isrg-rust backend

Binds [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
(ISRG) through UniFFI. It proves and verifies; it cannot generate circuits, so `generate_circuit`
raises `GenerationUnsupportedError` and circuits come from a `google-cpp` client or from disk.
It leaves `.code` as `None` on the exceptions it raises. `verify` requires the
`device_namespaces` argument and raises `ValueError` without it. It does not check
`spec.circuit_hash` against the circuit bytes at load; identity checking is backend-native
behaviour. A wrong circuit of the same version and attribute count is therefore not detected
at load; a mismatched version or attribute count surfaces as an error at `prove`/`verify`.

Engine init takes about 18 seconds per role and about 740 MB resident for a v6 1-attribute
circuit. Init is lazy and cached on the handle. `prove` then takes about 1.3 seconds and
`verify` about 0.8 seconds on the reference machine.

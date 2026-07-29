# API Reference

## `pylongfellow`

::: pylongfellow.Pylongfellow
::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The mdoc-specific data types and errors from longfellow-zk.

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
code it is in the exception's `.code`, typed as the corresponding enum or None; the
google/longfellow-zk backend always supplies it, other backends may not. Catch by class; do not
branch on the code. The
exceptions are subclasses of [`mdoc.Error`][pylongfellow.mdoc.Error], which is a subclass of
[`LongfellowError`][pylongfellow.LongfellowError]:

```
LongfellowError
└── mdoc.Error
    ├── ProverError      # .code: mdoc.ProverErrorCode
    ├── VerifierError    # .code: mdoc.VerifierErrorCode
    └── CircuitError     # .code: mdoc.CircuitGenerationErrorCode
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
`isrg-rust`) or instance.

::: pylongfellow.backends.Backend
::: pylongfellow.backends.get_backend
::: pylongfellow.backends.GenerationUnsupportedError
::: pylongfellow.backends.BackendUnavailableError

## The google-cpp backend

The default backend, binding the vendored google/longfellow-zk C++ library. These functions read
its compiled-in spec table; they are `google-cpp`-specific and depend on the built native
extension.

::: pylongfellow.backends.google_cpp.circuit_id
::: pylongfellow.backends.google_cpp.find_zk_spec
::: pylongfellow.backends.google_cpp.zk_specs

## The isrg-rust backend

An alternative backend that binds [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
(ISRG) through UniFFI. It proves and verifies; it cannot generate circuits, so `generate_circuit`
raises `GenerationUnsupportedError`. `verify` requires the `device_namespaces` argument.

Every wheel ships it. In a dev checkout, build it with
`uv run python scripts/build_isrg_rust_backend.py`; this needs the vendored
`vendor/zk-cred-longfellow` submodule (`git submodule update --init`) and a Rust toolchain.
When the native module is absent — a dev checkout before that build, or a source install
configured with `PYLONGFELLOW_BUILD_ISRG=OFF` — the backend raises `BackendUnavailableError`.

Select it by name — `Pylongfellow(backend="isrg-rust")`; `prove` and `verify` then dispatch through
the handles it loads. It does not check `spec.circuit_hash` against the circuit bytes at load;
identity checking is backend-native behaviour.

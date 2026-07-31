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
`isrg-rust`) or instance.

::: pylongfellow.backends.Backend
::: pylongfellow.backends.get_backend
::: pylongfellow.backends.GenerationUnsupportedError
::: pylongfellow.backends.BackendUnavailableError

## google-cpp backend

Binds the vendored google/longfellow-zk C++ library. `circuit_id` recomputes a circuit's
canonical id from its bytes. `find_zk_spec` and `zk_specs` read the backend's compiled-in spec
table. All three are `google-cpp`-specific and require the built native extension.

::: pylongfellow.backends.google_cpp.circuit_id
::: pylongfellow.backends.google_cpp.find_zk_spec
::: pylongfellow.backends.google_cpp.zk_specs

## isrg-rust backend

Binds [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
(ISRG) through UniFFI. It proves and verifies; it cannot generate circuits, so `generate_circuit`
raises `GenerationUnsupportedError`. `verify` requires the `device_namespaces` argument and
raises `ValueError` without it.

Every wheel ships it. In a dev checkout `uv sync` builds it from the `vendor/zk-cred-longfellow`
submodule, which needs cargo; `scripts/build_isrg_rust_backend.py` rebuilds it on its own, as
described on the [development page](development.md). When the native module is absent — a source
install configured with `PYLONGFELLOW_BUILD_ISRG=OFF`, or a checkout whose submodule was never
built — the backend raises `BackendUnavailableError`.

Select it by name — `Pylongfellow(backend="isrg-rust")`; `prove` and `verify` then dispatch through
the handles it loads. It does not check `spec.circuit_hash` against the circuit bytes at load;
identity checking is backend-native behaviour.

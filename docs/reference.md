# API Reference

## `pylongfellow`

::: pylongfellow.Pylongfellow
::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The mdoc-specific data types, errors, and spec-table functions from longfellow-zk.

### Functions

::: pylongfellow.mdoc.circuit_id
::: pylongfellow.mdoc.find_zk_spec
::: pylongfellow.mdoc.zk_specs
::: pylongfellow.mdoc.create_credential
::: pylongfellow.mdoc.create_certificate
::: pylongfellow.mdoc.sign_device_authentication
::: pylongfellow.mdoc.verify_device_authentication

### Data types

::: pylongfellow.mdoc.CircuitHandle
::: pylongfellow.mdoc.RequestedAttribute
::: pylongfellow.mdoc.ZkSpec
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
`isrg`) or instance.

::: pylongfellow.backends.Backend
::: pylongfellow.backends.get_backend
::: pylongfellow.backends.GenerationUnsupportedError
::: pylongfellow.backends.BackendUnavailableError

## The isrg backend

An alternative backend that binds [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
(ISRG) through UniFFI. It proves and verifies; it cannot generate circuits, so `generate_circuit`
raises `GenerationUnsupportedError`. `verify` requires the `device_namespaces` argument.

Build it before use: `uv run python scripts/build_isrg_backend.py`. This needs the vendored
`vendor/zk-cred-longfellow` submodule (`git submodule update --init`) and a Rust toolchain. Install
the `zstandard` runtime dependency with `pip install pylongfellow[isrg]`. If either is missing, the
backend raises `BackendUnavailableError`.

Select it by name — `Pylongfellow(backend="isrg")`; `prove` and `verify` then dispatch through
the handles it loads. It does not check `spec.circuit_hash` against the circuit bytes at load;
identity checking is backend-native behaviour.

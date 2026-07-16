# API Reference

## `pylongfellow`

::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The mdoc-specific functions, data types, and errors from longfellow-zk.

### Functions

::: pylongfellow.mdoc.load_circuit
::: pylongfellow.mdoc.prove
::: pylongfellow.mdoc.verify
::: pylongfellow.mdoc.generate_circuit
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
code it is in the exception's `.code`, typed as the corresponding enum or None; the cpp backend
always supplies it, other backends may not. Catch by class; do not branch on the code. The
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

## Rust backend

An alternative backend over [abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow),
generated with UniFFI. It proves and verifies; it cannot generate circuits, so `generate_circuit`
raises `GenerationUnsupportedError`. `verify` requires the `device_namespaces` argument.

Build it before use: `uv run python scripts/build_rust_backend.py`. This needs the vendored
`vendor/zk-cred-longfellow` submodule (`git submodule update --init`) and a Rust toolchain. Install
the `zstandard` runtime dependency with `pip install pylongfellow[rust]`. If either is missing, the
backend raises `BackendUnavailableError`.

Select it by passing `backend=pylongfellow.backends.rust.BACKEND` to
[`load_circuit`][pylongfellow.mdoc.load_circuit]; `prove` and `verify` then dispatch through the
returned handle.

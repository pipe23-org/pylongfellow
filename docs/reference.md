# API Reference

## `pylongfellow`

::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The mdoc-specific functions, data types, and errors from longfellow-zk.

### Functions

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

::: pylongfellow.mdoc.RequestedAttribute
::: pylongfellow.mdoc.ZkSpec
::: pylongfellow.mdoc.CreatedCredential

### Errors

Each function raises its own exception on a non-success C return code. The return code is in
the exception's `.code`, typed as the corresponding enum. The exceptions are subclasses of
[`mdoc.Error`][pylongfellow.mdoc.Error], which is a subclass of
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

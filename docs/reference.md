# API Reference

## `pylongfellow`

::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The mdoc-specific functions from longfellow-zk — `prove`, `verify`, and circuit generation —
with the data types they take and the errors they raise.

```python
from pylongfellow import mdoc

mdoc.verify(...)
```

### Functions

::: pylongfellow.mdoc.prove
::: pylongfellow.mdoc.verify
::: pylongfellow.mdoc.generate_circuit
::: pylongfellow.mdoc.circuit_id
::: pylongfellow.mdoc.find_zk_spec

### Data types

::: pylongfellow.mdoc.RequestedAttribute
::: pylongfellow.mdoc.ZkSpec

### Errors

Each function raises its own exception on a non-success C return code — `ProverError`,
`VerifierError`, or `CircuitError`. The return code is in the exception's `.code`, typed as
the corresponding enum. All three are subclasses of `mdoc.Error`, which is a subclass of
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

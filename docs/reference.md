# API Reference

## `pylongfellow`

The top level holds only the root exception and the version. Everything bound lives in a
namespace under it.

::: pylongfellow.LongfellowError

## `pylongfellow.mdoc`

The prover and verifier surface. Import it and call through it:

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

Non-success C return codes raise a concrete exception whose `.code` is the matching enum. The
hierarchy hangs off the root [`LongfellowError`][pylongfellow.LongfellowError] via the
namespace base `mdoc.Error`, so a caller can catch broadly or narrowly:

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

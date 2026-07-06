"""Python bindings for the [longfellow-zk](https://github.com/google/longfellow-zk) library.

The bound surface lives in namespaces, one per area of the upstream library. Today there is a
single namespace, `mdoc` (the prover and verifier); more will follow as further upstream
surface is bound. Import it and call through it:

    from pylongfellow import mdoc

    mdoc.verify(...)

Errors follow that layout. [`LongfellowError`][pylongfellow.LongfellowError] is the root — the
one cross-namespace catch-all — and is all that lives here. Every concrete exception lives with
the surface it comes from (`mdoc.Error` and its subclasses), so `.code` and its enum are one
contract in one place.
"""

from importlib.metadata import version

from ._errors import LongfellowError

__version__ = version("pylongfellow")

__all__ = [
    "LongfellowError",
    "__version__",
]

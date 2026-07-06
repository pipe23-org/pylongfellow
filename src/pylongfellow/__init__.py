"""Python bindings for the [longfellow-zk](https://github.com/google/longfellow-zk) library.

The package is organised into submodules, one per part of the upstream library. Currently the
mdoc-specific functions — proving, verifying, and circuit generation — are implemented, in
`pylongfellow.mdoc`:

    from pylongfellow import mdoc

    mdoc.verify(...)
"""

from importlib.metadata import version

from ._errors import LongfellowError

__version__ = version("pylongfellow")

__all__ = [
    "LongfellowError",
    "__version__",
]

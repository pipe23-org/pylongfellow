"""Python bindings for the [longfellow-zk](https://github.com/google/longfellow-zk) library.

Currently `pylongfellow.mdoc` implements the mdoc-specific functions: proving, verifying,
and circuit generation.
"""

from importlib.metadata import version

from ._errors import LongfellowError

__version__ = version("pylongfellow")

__all__ = [
    "LongfellowError",
    "__version__",
]

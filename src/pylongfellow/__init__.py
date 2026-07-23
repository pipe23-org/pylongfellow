"""Python bindings for the [longfellow-zk](https://github.com/google/longfellow-zk) library.

[`Pylongfellow`][pylongfellow.Pylongfellow] is the entry point: a client bound to one
backend. `pylongfellow.mdoc` holds the mdoc-specific data types and errors, and the
backend-free test-credential construction functions.
"""

from importlib.metadata import version

from ._errors import LongfellowError
from .mdoc._client import Pylongfellow

__version__ = version("pylongfellow")

__all__ = [
    "LongfellowError",
    "Pylongfellow",
    "__version__",
]

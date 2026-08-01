"""A Python interface to implementations of Longfellow zero-knowledge mdoc proofs.

[`Pylongfellow`][pylongfellow.Pylongfellow] is constructed with a choice of backend
(`google-cpp` or `isrg-rust`). It provides functions for proving, verifying, and circuit
generation.
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

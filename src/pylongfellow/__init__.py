"""A Python interface to implementations of Longfellow zero-knowledge mdoc proofs.

A [`Pylongfellow`][pylongfellow.Pylongfellow] selects an implementation (`google-cpp` or
`isrg-rust`) at construction. `pylongfellow.mdoc` holds the data types, errors, and
credential helpers.
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

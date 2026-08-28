"""A Python interface to implementations of Longfellow zero-knowledge mdoc proofs.

[`Pylongfellow`][pylongfellow.Pylongfellow] is constructed with a choice of backend
(`google-cpp` or `isrg-rust`). It proves and verifies.
[`generate_circuit`][pylongfellow.backends.google_cpp.generate_circuit] generates circuits.
"""

from importlib.metadata import version

from ._errors import LongfellowError
from .mdoc._pylongfellow import Pylongfellow

__version__ = version("pylongfellow")

__all__ = [
    "LongfellowError",
    "Pylongfellow",
    "__version__",
]

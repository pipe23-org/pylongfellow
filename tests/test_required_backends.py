"""Artifact gate: backends named in PYLONGFELLOW_REQUIRE_BACKENDS must be available.

Wheel and sdist CI set the variable, so a packaging regression that drops a
backend's native piece fails here instead of skipping through the suite. Unset
(the default in dev checkouts), the test skips.
"""

import os

import pytest

from pylongfellow.backends import get_backend


def test_required_backends_are_available():
    names = [n.strip() for n in os.environ.get("PYLONGFELLOW_REQUIRE_BACKENDS", "").split(",")]
    required = [n for n in names if n]
    if not required:
        pytest.skip("PYLONGFELLOW_REQUIRE_BACKENDS not set")
    for name in required:
        get_backend(name).ensure_available()

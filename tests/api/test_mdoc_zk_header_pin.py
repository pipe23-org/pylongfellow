import hashlib
from pathlib import Path

import pytest

# The cdef in native/google-cpp/ffibuild.py is a hand transcription of the C ABI in
# mdoc_zk.h. cffi trusts the cdef at build time, so a drift between the two is silent
# memory corruption at runtime rather than a build failure.
_HEADER = (
    Path(__file__).parents[2]
    / "vendor"
    / "longfellow-zk"
    / "lib"
    / "circuits"
    / "mdoc"
    / "mdoc_zk.h"
)
_PINNED_SHA256 = "96c6ce2876ce3e9a9db034ed971cf361ce03d66ba2e279eaeb4e7505d7755920"


def test_header_hash_matches_pin():
    if not _HEADER.is_file():
        pytest.skip(f"{_HEADER} not present (no vendor checkout)")
    actual = hashlib.sha256(_HEADER.read_bytes()).hexdigest()
    assert actual == _PINNED_SHA256, (
        "mdoc_zk.h changed, likely from a vendor/longfellow-zk submodule bump. Diff the header "
        "between the old and new pins, re-verify the cdef in native/google-cpp/ffibuild.py "
        "against it, then update _PINNED_SHA256 in this file."
    )

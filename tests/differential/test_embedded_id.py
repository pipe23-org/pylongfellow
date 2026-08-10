"""Embedded-id enforcement: what each backend's circuit_id does with a blob whose
embedded id is wrong. The entry in README.md Recorded divergences carries the
source citations."""

import io

import pytest
import zstandard

from pylongfellow import mdoc
from pylongfellow.backends import BackendUnavailableError, google_cpp, isrg_rust

from .conftest import CIRCUITS

# The divergence is parse-time, so one exhibit suffices; the smallest corpus
# circuit keeps the tamper-and-recompress cheap.
_CIRCUIT = min(CIRCUITS, key=lambda c: c.path.stat().st_size)


def _wrong_embedded_id() -> bytes:
    # The serialized circuit ends with its own 32-byte id, and the file is two
    # circuits back to back, so the last 32 decompressed bytes are the hash
    # circuit's embedded id. Zeros cannot collide with a real digest here.
    decompressed = (
        zstandard.ZstdDecompressor().stream_reader(io.BytesIO(_CIRCUIT.path.read_bytes())).read()
    )
    return zstandard.ZstdCompressor().compress(decompressed[:-32] + bytes(32))


def test_google_cpp_rejects_a_wrong_embedded_id():
    with pytest.raises(mdoc.Error):
        google_cpp.circuit_id(_wrong_embedded_id())


@pytest.mark.slow
def test_isrg_rust_recomputes_past_a_wrong_embedded_id():
    try:
        computed = isrg_rust.circuit_id(_wrong_embedded_id())
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")
    assert computed == _CIRCUIT.circuit_id

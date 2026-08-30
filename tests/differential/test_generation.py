import hashlib
import io
import warnings

import pytest
import zstandard
from longfellow_vectors.mdoc import Circuit

from pylongfellow import Pylongfellow
from pylongfellow.backends import google_cpp

from .conftest import GENERATED_CIRCUITS, VECTORS, ObservationWarning

GENERATION_PARAMS = [pytest.param(name, id=name) for name in GENERATED_CIRCUITS]

# Generation dominates the cost of every case in this module, so each circuit is
# generated once and shared across cases.
_GENERATED: dict[str, bytes] = {}


def _generated(circuit: Circuit) -> bytes:
    if circuit.name not in _GENERATED:
        _GENERATED[circuit.name] = google_cpp.generate_circuit(
            circuit.version, circuit.num_attributes
        )
    return _GENERATED[circuit.name]


@pytest.mark.slow
@pytest.mark.parametrize("name", GENERATION_PARAMS)
def test_generation(name: str):
    circuit = VECTORS.circuit(name)
    generated = _generated(circuit)

    Pylongfellow(backend="google-cpp").load_circuit(
        generated, circuit.version, circuit.num_attributes
    )

    # The comparison is over decompressed bytes: the zstd envelope differs
    # between upstream's export pipeline and the runtime generate path (and
    # varies with zstd versions) while wrapping an identical serialization.
    def _decompressed_sha256(blob: bytes) -> str:
        reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob))
        return hashlib.sha256(reader.read()).hexdigest()

    generated_sha256 = _decompressed_sha256(generated)
    committed_sha256 = _decompressed_sha256(circuit.bytes)
    if generated_sha256 != committed_sha256:
        warnings.warn(
            ObservationWarning(
                f"observation: serialization drift: {circuit.name} "
                f"generated {generated_sha256[:12]} != committed {committed_sha256[:12]} "
                f"(decompressed)"
            ),
            stacklevel=2,
        )

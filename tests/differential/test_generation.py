"""Generation drift check over the latest circuit per attribute count.

Each circuit is regenerated at test time on the google-cpp backend and scored
against its committed sidecar. A changed circuit_id fails the case (generation
drift); a changed byte hash at a stable circuit_id is emitted as an
ObservationWarning (serialization drift) without failing. README.md in this
directory is the taxonomy.
"""

import hashlib
import io
import warnings

import pytest

from pylongfellow.backends import google_cpp

from .conftest import CIRCUITS, Circuit, ObservationWarning, spec_of


def _latest_per_attr_count() -> list[Circuit]:
    # google's generate_circuit only makes the latest version for a given
    # num_attributes; an older spec is rejected, so an older sidecar is not a
    # generation case.
    latest: dict[int, Circuit] = {}
    for circuit in CIRCUITS:
        current = latest.get(circuit.num_attributes)
        if current is None or circuit.version > current.version:
            latest[circuit.num_attributes] = circuit
    return [latest[count] for count in sorted(latest)]


GENERATION_PARAMS = [pytest.param(circuit, id=circuit.stem) for circuit in _latest_per_attr_count()]


@pytest.mark.slow
@pytest.mark.parametrize("circuit", GENERATION_PARAMS)
def test_generation(circuit: Circuit, longfellow_for):
    longfellow = longfellow_for("google-cpp", circuit)
    generated = longfellow.generate_circuit(spec_of(circuit))
    assert google_cpp.circuit_id(generated) == circuit.circuit_id
    # The comparison is over decompressed bytes: the zstd envelope differs
    # between upstream's export pipeline and the runtime generate path (and
    # varies with zstd versions) while wrapping an identical serialization.
    import zstandard

    def _decompressed_sha256(blob: bytes) -> str:
        reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob))
        return hashlib.sha256(reader.read()).hexdigest()

    generated_sha256 = _decompressed_sha256(generated)
    committed_sha256 = _decompressed_sha256(circuit.path.read_bytes())
    if generated_sha256 != committed_sha256:
        warnings.warn(
            ObservationWarning(
                f"observation: serialization drift: {circuit.stem} "
                f"generated {generated_sha256[:12]} != committed {committed_sha256[:12]} "
                f"(decompressed)"
            ),
            stacklevel=2,
        )

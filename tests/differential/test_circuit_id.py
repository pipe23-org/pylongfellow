"""circuit_id agreement: every backend recomputes each corpus circuit's committed id."""

import pytest

from pylongfellow.backends import BackendUnavailableError

from .conftest import BACKENDS, CIRCUIT_ID_FUNCTIONS, CIRCUITS, Circuit

CIRCUIT_ID_PARAMS = [
    pytest.param(
        name,
        circuit,
        id=f"{circuit.stem}-circuit-id-{name}",
        marks=[pytest.mark.slow] if name == "isrg-rust" else [],
    )
    for circuit in CIRCUITS
    for name in BACKENDS
]


@pytest.mark.parametrize(("backend", "circuit"), CIRCUIT_ID_PARAMS)
def test_circuit_id_recomputes_the_committed_id(backend: str, circuit: Circuit):
    try:
        computed = CIRCUIT_ID_FUNCTIONS[backend](circuit.path.read_bytes())
    except BackendUnavailableError:
        pytest.skip(f"{backend} backend not built")
    assert computed == circuit.circuit_id

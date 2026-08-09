"""circuit_id agreement: every backend recomputes each corpus circuit's committed id."""

import importlib
from collections.abc import Callable

import pytest

from pylongfellow.backends import _REGISTRY, BackendUnavailableError

from .conftest import BACKENDS, CIRCUITS, Circuit

CIRCUIT_ID_FUNCTIONS: dict[str, Callable[[bytes], str]] = {
    name: importlib.import_module(_REGISTRY[name]).circuit_id for name in BACKENDS
}
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

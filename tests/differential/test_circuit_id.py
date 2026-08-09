"""circuit_id agreement: every backend recomputes each corpus circuit's committed id."""

import pytest

from pylongfellow.backends import BackendUnavailableError

from .conftest import CIRCUIT_ID_FUNCTIONS, CIRCUIT_ID_PARAMS, Circuit


@pytest.mark.parametrize(("backend", "circuit"), CIRCUIT_ID_PARAMS)
def test_circuit_id_recomputes_the_committed_id(backend: str, circuit: Circuit):
    try:
        computed = CIRCUIT_ID_FUNCTIONS[backend](circuit.path.read_bytes())
    except BackendUnavailableError:
        pytest.skip(f"{backend} backend not built")
    assert computed == circuit.circuit_id

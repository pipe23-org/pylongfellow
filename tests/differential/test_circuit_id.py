"""circuit_id agreement: circuit_id recomputes each corpus circuit's committed id."""

import pytest

from pylongfellow.backends import BackendUnavailableError

from .conftest import CIRCUIT_ID_FUNCTIONS, CIRCUITS, Circuit

CIRCUIT_ID_PARAMS = [pytest.param(circuit, id=circuit.stem) for circuit in CIRCUITS]


@pytest.mark.parametrize("circuit", CIRCUIT_ID_PARAMS)
def test_circuit_id_recomputes_the_committed_id(circuit: Circuit):
    try:
        computed = CIRCUIT_ID_FUNCTIONS(circuit.path.read_bytes())
    except BackendUnavailableError:
        pytest.skip("google-cpp backend not built")
    assert computed == circuit.circuit_id

"""circuit_id agreement: every backend recomputes each corpus circuit's committed id.

circuit_id is a module-level function per backend rather than a Backend
protocol method, so the backends are named here instead of joined over the
registry.
"""

from collections.abc import Callable

import pytest

from pylongfellow.backends import BackendUnavailableError, google_cpp, isrg_rust

from .conftest import CIRCUITS, Circuit

# Annotated because google-cpp's binding is cache-wrapped and isrg-rust's is not,
# so the inferred value type of the two together is object.
_CIRCUIT_ID: dict[str, Callable[[bytes], str]] = {
    "google-cpp": google_cpp.circuit_id,
    "isrg-rust": isrg_rust.circuit_id,
}

CIRCUIT_ID_PARAMS = [pytest.param(circuit, id=circuit.stem) for circuit in CIRCUITS]


@pytest.mark.slow
@pytest.mark.parametrize("circuit", CIRCUIT_ID_PARAMS)
def test_circuit_id_agrees(circuit: Circuit):
    blob = circuit.path.read_bytes()
    computed = {}
    for name, compute in _CIRCUIT_ID.items():
        try:
            computed[name] = compute(blob)
        except BackendUnavailableError:
            pytest.skip(f"{name} backend not built")
    assert computed == dict.fromkeys(_CIRCUIT_ID, circuit.circuit_id)

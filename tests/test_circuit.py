"""circuit_id and find_zk_spec — circuit/spec identity."""

from pathlib import Path

import pytest

from pylongfellow import mdoc

_SYSTEM = "longfellow-libzk-v1"
_CIRCUITS = Path(__file__).parent / "data" / "circuits"

# committed circuit blobs: (circuit_id/hash, version, num_attributes)
_KNOWN = [
    ("137e5a75ce72735a37c8a72da1a8a0a5df8d13365c2ae3d2c2bd6a0e7197c7c6", 6, 1),
    ("8d079211715200ff06c5109639245502bfe94aa869908d31176aae4016182121", 7, 1),
]


@pytest.mark.parametrize("circuit_hash", [h for h, _, _ in _KNOWN], ids=["v6", "v7"])
def test_circuit_id_matches_hash(circuit_hash):
    circuit = (_CIRCUITS / circuit_hash).read_bytes()
    assert mdoc.circuit_id(circuit) == circuit_hash


def test_circuit_id_rejects_garbage():
    with pytest.raises(mdoc.Error):
        mdoc.circuit_id(b"not a circuit" * 20)


def test_find_zk_spec_resolves_known():
    circuit_hash, version, num_attributes = _KNOWN[1]
    spec = mdoc.find_zk_spec(_SYSTEM, circuit_hash)
    assert spec is not None
    assert spec.circuit_hash == circuit_hash
    assert spec.version == version
    assert spec.num_attributes == num_attributes


def test_find_zk_spec_miss_returns_none():
    assert mdoc.find_zk_spec(_SYSTEM, "00" * 32) is None
    assert mdoc.find_zk_spec("nope", _KNOWN[0][0]) is None


def test_generate_circuit_rejects_old_version():
    # generate_circuit only makes the latest version; an older spec is rejected.
    spec = mdoc.find_zk_spec(_SYSTEM, _KNOWN[0][0])  # v6, not the latest
    assert spec is not None
    with pytest.raises(mdoc.CircuitError):
        mdoc.generate_circuit(spec)


@pytest.mark.slow
def test_generate_circuit_self_validates():
    # Generation must reproduce the canonical id — the interoperable circuit,
    # not merely a valid one.
    circuit_hash = _KNOWN[1][0]  # v7/n1
    spec = mdoc.find_zk_spec(_SYSTEM, circuit_hash)
    assert spec is not None
    assert mdoc.circuit_id(mdoc.generate_circuit(spec)) == circuit_hash

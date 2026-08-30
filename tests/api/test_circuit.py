from pathlib import Path

import pytest

from pylongfellow import mdoc
from pylongfellow.backends import google_cpp

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
    assert google_cpp.circuit_id(circuit) == circuit_hash


def test_circuit_id_rejects_garbage():
    with pytest.raises(mdoc.Error):
        google_cpp.circuit_id(b"not a circuit" * 20)


def test_find_zk_spec_resolves_known():
    circuit_hash, version, num_attributes = _KNOWN[1]
    spec = google_cpp.find_zk_spec(_SYSTEM, circuit_hash)
    assert spec is not None
    assert spec.circuit_hash == circuit_hash
    assert spec.version == version
    assert spec.num_attributes == num_attributes


def test_find_zk_spec_miss_returns_none():
    assert google_cpp.find_zk_spec(_SYSTEM, "00" * 32) is None
    assert google_cpp.find_zk_spec("nope", _KNOWN[0][0]) is None


def test_generate_circuit_rejects_old_version():
    # generate_circuit only makes the latest version for a count; v6/1 is superseded.
    with pytest.raises(mdoc.CircuitError):
        google_cpp.generate_circuit(6, 1)


def test_generate_circuit_rejects_unknown_pair():
    with pytest.raises(ValueError, match="no circuit with"):
        google_cpp.generate_circuit(7, 9)


def test_generate_circuit_self_validates():
    # Generation must reproduce the canonical id — the interoperable circuit,
    # not merely a valid one.
    circuit_hash = _KNOWN[1][0]  # v7/n1
    assert google_cpp.circuit_id(google_cpp.generate_circuit(7, 1)) == circuit_hash


def test_zk_specs_length():
    assert len(google_cpp.zk_specs()) == 12


def test_zk_specs_round_trip():
    # Every table entry resolves back to itself through find_zk_spec.
    for spec in google_cpp.zk_specs():
        assert google_cpp.find_zk_spec(spec.system, spec.circuit_hash) == spec


def test_zk_specs_versions_unique_per_group():
    # generate_circuit's latest-only rule keys on the max version within a
    # (system, num_attributes) group, so the versions in each group must be unique.
    groups: dict[tuple[str, int], list[int]] = {}
    for spec in google_cpp.zk_specs():
        groups.setdefault((spec.system, spec.num_attributes), []).append(spec.version)
    for versions in groups.values():
        assert len(versions) == len(set(versions))


@pytest.mark.parametrize(("circuit_hash", "version", "num_attributes"), _KNOWN, ids=["v6", "v7"])
def test_known_blobs_present_in_table(circuit_hash, version, num_attributes):
    # Ties the hand-maintained _KNOWN list (committed circuit blobs by filename)
    # to the library's circuit table.
    matches = [s for s in google_cpp.zk_specs() if s.circuit_hash == circuit_hash]
    assert len(matches) == 1
    assert matches[0].version == version
    assert matches[0].num_attributes == num_attributes

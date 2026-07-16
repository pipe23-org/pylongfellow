"""circuit_id and find_zk_spec — circuit/spec identity."""

import dataclasses
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
def test_generate_circuit_rejects_noncanonical_spec():
    # A hand-built spec that isn't in the library's table must be refused before
    # reaching C (block_enc/version SIGABRT; oversize hash is a heap overflow).
    spec = mdoc.find_zk_spec(_SYSTEM, _KNOWN[1][0])
    assert spec is not None
    with pytest.raises(ValueError, match="registered ZkSpec"):
        mdoc.generate_circuit(dataclasses.replace(spec, block_enc_hash=spec.block_enc_hash + 1))


def test_build_spec_rejects_oversize_hash():
    # Direct protection on the marshalling primitive: a circuit_hash longer than
    # the 65-byte C field is an out-of-bounds write. Callers via prove/verify/
    # generate_circuit are shielded earlier by the canonical guard; this covers
    # the primitive itself.
    from pylongfellow._longfellow import ffi
    from pylongfellow.backends.google import _build_spec

    spec = mdoc.find_zk_spec(_SYSTEM, _KNOWN[1][0])
    assert spec is not None
    with pytest.raises(ValueError, match="circuit_hash too long"):
        _build_spec(ffi, dataclasses.replace(spec, circuit_hash="a" * 200))


def test_generate_circuit_self_validates():
    # Generation must reproduce the canonical id — the interoperable circuit,
    # not merely a valid one.
    circuit_hash = _KNOWN[1][0]  # v7/n1
    spec = mdoc.find_zk_spec(_SYSTEM, circuit_hash)
    assert spec is not None
    assert mdoc.circuit_id(mdoc.generate_circuit(spec)) == circuit_hash


def test_zk_specs_length():
    assert len(mdoc.zk_specs()) == 12


def test_zk_specs_round_trip():
    # Every table entry resolves back to itself through find_zk_spec.
    for spec in mdoc.zk_specs():
        assert mdoc.find_zk_spec(spec.system, spec.circuit_hash) == spec


def test_zk_specs_versions_unique_per_group():
    # generate_circuit's latest-only rule keys on the max version within a
    # (system, num_attributes) group, so the versions in each group must be unique.
    groups: dict[tuple[str, int], list[int]] = {}
    for spec in mdoc.zk_specs():
        groups.setdefault((spec.system, spec.num_attributes), []).append(spec.version)
    for versions in groups.values():
        assert len(versions) == len(set(versions))


@pytest.mark.parametrize(("circuit_hash", "version", "num_attributes"), _KNOWN, ids=["v6", "v7"])
def test_known_blobs_present_in_table(circuit_hash, version, num_attributes):
    # Ties the hand-maintained _KNOWN list (committed circuit blobs by filename)
    # to the compiled-in table.
    matches = [s for s in mdoc.zk_specs() if s.circuit_hash == circuit_hash]
    assert len(matches) == 1
    assert matches[0].version == version
    assert matches[0].num_attributes == num_attributes

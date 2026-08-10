"""CircuitSpec enforcement: what load and a full prove/verify round trip do with a
spec whose fields lie about the circuit it names. Two probes over the committed
v6-1attr circuit, both built in-test from conftest's spec_of — no reject-vector
artifact, since the lie lives in the spec, not the circuit bytes. The README.md
Recorded divergences entry carries the source citations."""

from __future__ import annotations

import dataclasses
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError

from .conftest import CIRCUITS, PRESENTATIONS, spec_of

_REPO_ROOT = Path(__file__).parents[2]

_CIRCUIT = next(c for c in CIRCUITS if c.stem == "v6-1attr")
_BYTES = _CIRCUIT.path.read_bytes()
_SPEC = spec_of(_CIRCUIT)
_PRESENTATION = next(
    p
    for p in PRESENTATIONS
    if len(p.attrs) == 1 and p.mdoc_bytes is not None and p.device_namespaces is not None
)
assert _PRESENTATION.mdoc_bytes is not None
_MDOC_BYTES = _PRESENTATION.mdoc_bytes

# The Ligero layout's hard-coded bound is 2**28 (lib/ligero/ligero_param.h,
# max_lg_size); a +1 perturbation stays inside a valid, merely non-canonical
# layout and never reaches the C-level check this probe is exercising.
_BLOCK_ENC_DELTA = 1 << 30

_WRONG_CIRCUIT_HASH = dataclasses.replace(_SPEC, circuit_hash="f" * 64)
_NONCANONICAL_SPEC = dataclasses.replace(
    _SPEC,
    block_enc_hash=_SPEC.block_enc_hash + _BLOCK_ENC_DELTA,
    block_enc_sig=_SPEC.block_enc_sig + _BLOCK_ENC_DELTA,
)

_NOT_REGISTERED = "not registered in the compiled-in spec table"

_ISRG_DISCARDS = pytest.mark.xfail(
    strict=True,
    reason="isrg-rust's load_circuit consumes spec.version and spec.num_attributes "
    "only and discards the rest (src/pylongfellow/backends/isrg_rust.py load_circuit); "
    "upstream's initialize_prover/initialize_verifier take no spec parameter at all "
    "(vendor/zk-cred-longfellow/src/ffi_api.rs @ b22d84e)",
)


def _round_trip(spec: mdoc.CircuitSpec) -> None:
    p = _PRESENTATION
    longfellow = Pylongfellow(backend="isrg-rust")
    longfellow.load_circuit(spec, _BYTES)
    proof = longfellow.prove(_MDOC_BYTES, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
    longfellow.verify(
        p.issuer_pk,
        p.transcript,
        p.attrs,
        p.timestamp,
        proof,
        p.doctype,
        device_namespaces=p.device_namespaces,
    )


def test_google_cpp_load_rejects_wrong_circuit_hash():
    with pytest.raises(ValueError, match=_NOT_REGISTERED):
        Pylongfellow(backend="google-cpp").load_circuit(_WRONG_CIRCUIT_HASH, _BYTES)


@pytest.mark.slow
@_ISRG_DISCARDS
def test_isrg_rust_load_rejects_wrong_circuit_hash():
    try:
        with pytest.raises(ValueError, match=_NOT_REGISTERED):
            Pylongfellow(backend="isrg-rust").load_circuit(_WRONG_CIRCUIT_HASH, _BYTES)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")


def test_google_cpp_load_rejects_noncanonical_spec():
    with pytest.raises(ValueError, match=_NOT_REGISTERED):
        Pylongfellow(backend="google-cpp").load_circuit(_NONCANONICAL_SPEC, _BYTES)


@pytest.mark.slow
@_ISRG_DISCARDS
def test_isrg_rust_load_rejects_noncanonical_spec():
    try:
        with pytest.raises(ValueError, match=_NOT_REGISTERED):
            Pylongfellow(backend="isrg-rust").load_circuit(_NONCANONICAL_SPEC, _BYTES)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")


# The child bypasses pylongfellow's own guards by constructing google_cpp's loaded
# state directly, then calls the backend's prove with real presentation inputs. A
# spec/circuit mismatch the C layer itself checks (see the noncanonical-spec probe)
# aborts the whole process; run it out of process so the abort doesn't take pytest
# down with it.
_CHILD_PROVE = """
import dataclasses

from pylongfellow.backends import google_cpp
from tests.differential.conftest import CIRCUITS, PRESENTATIONS, spec_of

circuit = next(c for c in CIRCUITS if c.stem == "v6-1attr")
spec = spec_of(circuit)
p = next(
    pp
    for pp in PRESENTATIONS
    if len(pp.attrs) == 1 and pp.mdoc_bytes is not None and pp.device_namespaces is not None
)
lying_spec = dataclasses.replace(spec, {kwargs})
state = google_cpp._LoadedCircuit(spec=lying_spec, circuit=circuit.path.read_bytes())
google_cpp.BACKEND.prove(state, p.mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
"""

_WRONG_CIRCUIT_HASH_KWARGS = 'circuit_hash="f" * 64'
_NONCANONICAL_SPEC_KWARGS = (
    f"block_enc_hash=spec.block_enc_hash + {_BLOCK_ENC_DELTA}, "
    f"block_enc_sig=spec.block_enc_sig + {_BLOCK_ENC_DELTA}"
)


def _run_child_prove(kwargs: str) -> subprocess.CompletedProcess[str]:
    code = _CHILD_PROVE.format(kwargs=kwargs)
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT)}
    try:
        return subprocess.run(  # noqa: S603 - our own interpreter, a fixed code string
            [sys.executable, "-c", code],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"child process hung past the 120s timeout: {e}")


def _assert_dies_by_sigabrt(result: subprocess.CompletedProcess[str]) -> None:
    tail = (result.stdout + result.stderr)[-2000:]
    assert result.returncode == -signal.SIGABRT, (
        f"expected SIGABRT (returncode -{signal.SIGABRT}), got {result.returncode}; "
        f"output tail: {tail!r}"
    )


@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="run_mdoc_prover never dereferences spec.circuit_hash (vendor/longfellow-zk "
    "lib/circuits/mdoc/mdoc_zk.cc:111, enforce_circuit_id_in_prover=false, and the field "
    "is absent from every zk_spec-> read in the function); with pylongfellow's own guard "
    "bypassed there is no C-level backstop left and the child exits without aborting",
)
def test_google_cpp_round_trip_rejects_wrong_circuit_hash():
    _assert_dies_by_sigabrt(_run_child_prove(_WRONG_CIRCUIT_HASH_KWARGS))


@pytest.mark.slow
def test_google_cpp_round_trip_rejects_noncanonical_spec():
    _assert_dies_by_sigabrt(_run_child_prove(_NONCANONICAL_SPEC_KWARGS))


@pytest.mark.slow
@_ISRG_DISCARDS
def test_isrg_rust_round_trip_rejects_wrong_circuit_hash():
    try:
        with pytest.raises(ValueError, match=_NOT_REGISTERED):
            _round_trip(_WRONG_CIRCUIT_HASH)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")


@pytest.mark.slow
@_ISRG_DISCARDS
def test_isrg_rust_round_trip_rejects_noncanonical_spec():
    try:
        with pytest.raises(ValueError, match=_NOT_REGISTERED):
            _round_trip(_NONCANONICAL_SPEC)
    except BackendUnavailableError:
        pytest.skip("isrg-rust backend not built")

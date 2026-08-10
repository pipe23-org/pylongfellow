"""Circuit spec handling: what google's C layer does with spec fields when
pylongfellow's own front-door guards are bypassed. The child constructs the
backend's loaded state directly — with the guards up, garbage specs never
reach C through the public API, and the point here is characterizing C. Four
probes over the committed v6-1attr circuit; the README.md Recorded
divergences entry carries the source citations."""

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parents[2]

# lib/ligero/ligero_param.h:176 aborts the process once layout(block_enc) reaches
# SIZE_MAX; the bound is 2**28, so a +2**30 perturbation lands well past it.
# block_enc_hash and block_enc_sig each build their own LigeroParam
# (lib/circuits/mdoc/mdoc_zk.cc:480 and :481), so the check applies per field.
_BLOCK_ENC_DELTA = 1 << 30

# isrg-rust's API has no block_enc parameter anywhere: initialize_prover
# (vendor/zk-cred-longfellow/src/ffi_api.rs:20-28) and initialize_verifier (:52-59,
# pin b22d84e) take only (circuit, circuit_version, num_attributes). These probes
# characterize google_cpp only.

# The child bypasses pylongfellow's own guards by constructing google_cpp's loaded
# state directly, then calls the backend's prove with real presentation inputs.
_CHILD_PROVE = """
import dataclasses

from pylongfellow.backends import google_cpp
from tests.differential.conftest import CIRCUITS, PRESENTATIONS, spec_of

circuit = next(c for c in CIRCUITS if c.stem == "v6-1attr")
spec = spec_of(circuit)
spec = dataclasses.replace(spec, {kwargs})
p = next(
    pp
    for pp in PRESENTATIONS
    if len(pp.attrs) == 1 and pp.mdoc_bytes is not None and pp.device_namespaces is not None
)
state = google_cpp._LoadedCircuit(spec=spec, circuit=circuit.path.read_bytes())
google_cpp.BACKEND.prove(state, p.mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
"""

_DEAD_FIELDS_KWARGS = 'circuit_hash="f" * 64, system="garbage-system"'
_OUT_OF_RANGE_BLOCK_ENC_HASH_KWARGS = f"block_enc_hash=spec.block_enc_hash + {_BLOCK_ENC_DELTA}"
_OUT_OF_RANGE_BLOCK_ENC_SIG_KWARGS = f"block_enc_sig=spec.block_enc_sig + {_BLOCK_ENC_DELTA}"
_IN_BOUNDS_BLOCK_ENC_KWARGS = (
    "block_enc_hash=spec.block_enc_hash + 1, block_enc_sig=spec.block_enc_sig + 1"
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


@pytest.mark.slow
def test_google_cpp_prove_ignores_dead_fields():
    result = _run_child_prove(_DEAD_FIELDS_KWARGS)
    tail = (result.stdout + result.stderr)[-2000:]
    assert result.returncode == 0, (
        f"expected a clean exit, got {result.returncode}; output tail: {tail!r}"
    )


@pytest.mark.slow
def test_google_cpp_prove_aborts_on_out_of_range_block_enc_hash():
    result = _run_child_prove(_OUT_OF_RANGE_BLOCK_ENC_HASH_KWARGS)
    tail = (result.stdout + result.stderr)[-2000:]
    assert result.returncode == -signal.SIGABRT, (
        f"expected SIGABRT (returncode -{signal.SIGABRT}), got {result.returncode}; "
        f"output tail: {tail!r}"
    )


@pytest.mark.slow
def test_google_cpp_prove_aborts_on_out_of_range_block_enc_sig():
    result = _run_child_prove(_OUT_OF_RANGE_BLOCK_ENC_SIG_KWARGS)
    tail = (result.stdout + result.stderr)[-2000:]
    assert result.returncode == -signal.SIGABRT, (
        f"expected SIGABRT (returncode -{signal.SIGABRT}), got {result.returncode}; "
        f"output tail: {tail!r}"
    )


@pytest.mark.slow
def test_google_cpp_prove_accepts_in_bounds_noncanonical_block_enc():
    result = _run_child_prove(_IN_BOUNDS_BLOCK_ENC_KWARGS)
    tail = (result.stdout + result.stderr)[-2000:]
    assert result.returncode == 0, (
        f"expected a clean exit, got {result.returncode}; output tail: {tail!r}"
    )

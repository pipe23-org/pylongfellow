"""PYLONGFELLOW_LOG_LEVEL sets upstream's stderr level at load (default WARNING).

Read once in a load-time constructor, so each value needs its own process: every
test re-runs this file as a subprocess with the env controlled. "ms]" is upstream's
log-line timestamp — on stderr iff the per-call firehose is on.
"""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pylongfellow import Pylongfellow, mdoc


def _stderr(level: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYLONGFELLOW_LOG_LEVEL"}
    if level is not None:
        env["PYLONGFELLOW_LOG_LEVEL"] = level
    result = subprocess.run(  # noqa: S603 - our own interpreter re-running this file
        [sys.executable, __file__], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stderr


def test_default_is_quiet():
    assert "ms]" not in _stderr(None)


def test_info_enables_the_firehose():
    assert "ms]" in _stderr("info")


if __name__ == "__main__":
    # Subprocess worker: load the proof fixture (as conftest does) and run one
    # verify, which logs at INFO.
    data = Path(__file__).parent / "data"
    fx = json.loads((data / "proof_age_over_18.json").read_text())
    spec = mdoc.find_zk_spec(fx["system"], fx["circuit_hash"])
    assert spec is not None
    attrs = [
        mdoc.RequestedAttribute(a["namespace"], a["id"], bytes.fromhex(a["cbor_value_hex"]))
        for a in fx["attrs"]
    ]
    client = Pylongfellow(backend="google-cpp")
    handle = client.load_circuit(spec, (data / "circuits" / fx["circuit_hash"]).read_bytes())
    client.verify(
        handle,
        (int(fx["issuer_pk_x"], 16), int(fx["issuer_pk_y"], 16)),
        base64.b64decode(fx["transcript_b64"]),
        attrs,
        datetime.fromisoformat(fx["timestamp"]),
        base64.b64decode(fx["proof_b64"]),
        fx["doctype"],
    )

"""Prove and verify age_over_18 over a committed sample mdoc, end to end.

Runs entirely on the bundled mdoc_eu_av.json (an ISO 18013-5 mdoc lifted from
upstream's test data). Circuit generation dominates the runtime (~15s).

    python examples/prove_and_verify.py
"""

import json
from datetime import datetime
from pathlib import Path

from pylongfellow import mdoc

credential = json.loads((Path(__file__).parent / "mdoc_eu_av.json").read_text())

spec = mdoc.find_zk_spec(credential["system"], credential["circuit_hash"])
if spec is None:
    raise SystemExit(f"no built-in spec for {credential['circuit_hash']}")

print(f"generating circuit for {spec.system} (v{spec.version}, {spec.num_attributes} attr)...")
circuit = mdoc.generate_circuit(spec)
if mdoc.circuit_id(circuit) != spec.circuit_hash:
    raise SystemExit("generated circuit id does not match the spec")

attrs = [
    mdoc.RequestedAttribute(a["namespace"], a["id"], bytes.fromhex(a["cbor_value_hex"]))
    for a in credential["attrs"]
]
issuer_pk = (int(credential["issuer_pk_x"], 16), int(credential["issuer_pk_y"], 16))
transcript = bytes.fromhex(credential["transcript_hex"])
credential_mdoc = bytes.fromhex(credential["mdoc_hex"])
timestamp = datetime.fromisoformat(credential["timestamp"])

proof = mdoc.prove(circuit, credential_mdoc, issuer_pk, transcript, attrs, timestamp, spec)
print(f"proved: {len(proof)} bytes")

# verify() returns None on success and raises VerifierError otherwise.
mdoc.verify(circuit, issuer_pk, transcript, attrs, timestamp, proof, credential["doctype"], spec)
print("verified")

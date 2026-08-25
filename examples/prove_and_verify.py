"""Prove and verify age_over_18 over a committed sample mdoc, end to end.

Runs entirely on the bundled mdoc_eu_av.json (an ISO 18013-5 mdoc lifted from
upstream's test data). Circuit generation dominates the runtime (~15s).

    python examples/prove_and_verify.py
"""

import json
from datetime import datetime
from pathlib import Path

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends.google_cpp import circuit_id, generate_circuit

longfellow = Pylongfellow(backend="google-cpp")

credential = json.loads((Path(__file__).parent / "mdoc_eu_av.json").read_text())

print("generating the v7 1-attribute circuit...")
circuit = generate_circuit(7, 1)
if circuit_id(circuit) != credential["circuit_hash"]:
    raise SystemExit("generated circuit id does not match the credential's circuit")

longfellow.load_circuit(circuit, 7, 1)

claims = [
    mdoc.RequestedAttribute(a["namespace"], a["id"], bytes.fromhex(a["cbor_value_hex"]))
    for a in credential["attrs"]
]
issuer_public_key = mdoc.PublicKey(
    int(credential["issuer_pk_x"], 16), int(credential["issuer_pk_y"], 16)
)
transcript = bytes.fromhex(credential["transcript_hex"])
credential_mdoc = bytes.fromhex(credential["mdoc_hex"])
timestamp = datetime.fromisoformat(credential["timestamp"])

proof = longfellow.prove(credential_mdoc, issuer_public_key, transcript, claims, timestamp)
print(f"proved: {len(proof)} bytes")

# verify() returns None on success and raises VerifierError otherwise.
longfellow.verify(issuer_public_key, transcript, claims, timestamp, proof, credential["doctype"])
print("verified")

#!/usr/bin/env python3
"""Decode and summarize an X.509 certificate (DER or PEM).

    python scripts/dump_x509.py <cert.der|cert.pem>

Handy for the issuer cert pulled from an mdoc's msoX5chain — the EC point it
prints is the pkx/pky the verifier needs.
"""

import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec


def load(path: str) -> x509.Certificate:
    raw = Path(path).read_bytes()
    try:
        return x509.load_pem_x509_certificate(raw)
    except ValueError:
        return x509.load_der_x509_certificate(raw)


def main(path: str) -> None:
    cert = load(path)
    print("subject  :", cert.subject.rfc4514_string())
    print("issuer   :", cert.issuer.rfc4514_string())
    print("serial   :", hex(cert.serial_number))
    print("validity :", cert.not_valid_before_utc, "->", cert.not_valid_after_utc)
    print("sig alg  :", cert.signature_algorithm_oid._name)

    pub = cert.public_key()
    if isinstance(pub, ec.EllipticCurvePublicKey):
        nums = pub.public_numbers()
        print(f"pubkey   : EC {nums.curve.name}")
        print("  x (pkx):", format(nums.x, "064x"))
        print("  y (pky):", format(nums.y, "064x"))
    else:
        print("pubkey   :", type(pub).__name__)

    print("extensions:")
    for ext in cert.extensions:
        print(f"  {ext.oid._name} (critical={ext.critical})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

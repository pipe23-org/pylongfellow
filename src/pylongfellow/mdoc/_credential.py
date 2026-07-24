"""Test-credential construction: an mdoc DeviceResponse issued under locally held keys.

Everything in this module runs on `cryptography` and `cbor2` alone; no ZK backend is
loaded or called. Whether a backend can prove or verify over a created credential is a
property of that backend.
"""

import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import cbor2
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.x509.oid import NameOID

from ._errors import Error

# COSE protected header {1: -7}: ES256, the only algorithm on this path.
_COSE_ES256_PROTECTED = b"\xa1\x01\x26"


def _require_utc(value: datetime, name: str) -> datetime:
    """Reject a naive datetime and normalize an aware one to UTC."""
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _tdate(value: datetime) -> cbor2.CBORTag:
    """Encode a UTC datetime the way deployed MSOs do: tag 0, whole seconds, Zulu."""
    return cbor2.CBORTag(0, value.strftime("%Y-%m-%dT%H:%M:%SZ"))


def _device_authentication_bytes(transcript: bytes, doc_type: str, namespaces: object) -> bytes:
    """Build ``DeviceAuthenticationBytes``, the device signature's detached payload."""
    authentication = ["DeviceAuthentication", cbor2.loads(transcript), doc_type, namespaces]
    return cbor2.dumps(cbor2.CBORTag(24, cbor2.dumps(authentication)))


def _cose_sign(key: ec.EllipticCurvePrivateKey, payload: bytes) -> bytes:
    """Sign a COSE ``Signature1`` structure over the payload, returning raw ``r || s``."""
    structure = cbor2.dumps(["Signature1", _COSE_ES256_PROTECTED, b"", payload])
    r, s = decode_dss_signature(key.sign(structure, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _cose_verify(key: ec.EllipticCurvePublicKey, payload: bytes, signature: bytes) -> None:
    """Check a COSE ``Signature1`` signature; raises ``InvalidSignature`` on mismatch."""
    structure = cbor2.dumps(["Signature1", _COSE_ES256_PROTECTED, b"", payload])
    der = encode_dss_signature(
        int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    )
    key.verify(der, structure, ec.ECDSA(hashes.SHA256()))


def _key_usage(*, ca: bool) -> x509.KeyUsage:
    """Build the keyUsage extension: keyCertSign for a CA, digitalSignature for a leaf."""
    return x509.KeyUsage(
        digital_signature=not ca,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=ca,
        crl_sign=ca,
        encipher_only=False,
        decipher_only=False,
    )


def create_certificate(
    subject: str,
    public_key: ec.EllipticCurvePublicKey,
    issuer: str,
    signing_key: ec.EllipticCurvePrivateKey,
    valid_from: datetime,
    valid_until: datetime,
    *,
    ca: bool = False,
) -> x509.Certificate:
    """Build one X.509 certificate of a test trust chain.

    The subject and issuer names carry a single common-name attribute. The
    certificate is signed with ECDSA over SHA-256.

    Args:
        subject: Subject common name.
        public_key: Public key the certificate certifies.
        issuer: Issuer common name; equals `subject` on a self-signed
            certificate.
        signing_key: Private key that signs the certificate.
        valid_from: Start of the validity window; timezone-aware.
        valid_until: End of the validity window; timezone-aware.
        ca: True builds a CA certificate (`basicConstraints` CA, keyUsage
            `keyCertSign`); False builds a leaf (keyUsage `digitalSignature`).

    Returns:
        The signed certificate.

    Raises:
        ValueError: `valid_from` or `valid_until` is naive.
    """
    valid_from = _require_utc(valid_from, "valid_from")
    valid_until = _require_utc(valid_until, "valid_until")

    def _name(cn: str) -> x509.Name:
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    builder = (
        x509.CertificateBuilder()
        .subject_name(_name(subject))
        .issuer_name(_name(issuer))
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_until)
        .add_extension(_key_usage(ca=ca), critical=True)
    )
    if ca:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
    return builder.sign(signing_key, hashes.SHA256())


def sign_device_authentication(
    device_key: ec.EllipticCurvePrivateKey,
    transcript: bytes,
    doc_type: str,
    device_namespaces: object,
) -> bytes:
    """Sign ``DeviceAuthentication`` over a session transcript.

    Builds the detached ``DeviceAuthenticationBytes`` payload from the
    transcript, the doctype, and the device namespaces, and signs it as a COSE
    ``Signature1`` structure with ES256.

    Args:
        device_key: The credential's device private key.
        transcript: CBOR-encoded session transcript.
        doc_type: The credential's doctype.
        device_namespaces: The data item held in the credential's
            ``deviceSigned.nameSpaces``: tag 24 over the encoded namespace map.

    Returns:
        The raw 64-byte ``r || s`` signature, the fourth element of
        ``deviceAuth.deviceSignature``.
    """
    payload = _device_authentication_bytes(transcript, doc_type, device_namespaces)
    return _cose_sign(device_key, payload)


def verify_device_authentication(mdoc: bytes, transcript: bytes) -> None:
    """Verify an mdoc's device signature over a session transcript.

    Takes the device public key from the first document's MSO ``deviceKeyInfo``,
    rebuilds the detached ``DeviceAuthenticationBytes`` payload from the
    document's own doctype and device namespaces, and checks the document's
    ``deviceSignature`` against it. The check runs on `cryptography` alone.

    Args:
        mdoc: CBOR-encoded mdoc credential.
        transcript: CBOR-encoded session transcript the signature is bound to.

    Raises:
        Error: The device signature does not verify over the transcript.
    """
    document = cbor2.loads(mdoc)["documents"][0]
    mso = cbor2.loads(cbor2.loads(document["issuerSigned"]["issuerAuth"][2]).value)
    cose_key = mso["deviceKeyInfo"]["deviceKey"]
    device_public = ec.EllipticCurvePublicNumbers(
        int.from_bytes(cose_key[-2], "big"), int.from_bytes(cose_key[-3], "big"), ec.SECP256R1()
    ).public_key()
    payload = _device_authentication_bytes(
        transcript, document["docType"], document["deviceSigned"]["nameSpaces"]
    )
    signature = document["deviceSigned"]["deviceAuth"]["deviceSignature"][3]
    try:
        _cose_verify(device_public, payload, signature)
    except InvalidSignature as e:
        raise Error("device signature does not verify over the transcript") from e


def _check_issuer_auth(credential: bytes) -> None:
    """Verify the issuer signature against the embedded certificate.

    Decodes the credential back the way a consumer would, so a certificate that
    does not certify the signing key, or drift between encode and decode,
    fails here.
    """
    issuer_auth = cbor2.loads(credential)["documents"][0]["issuerSigned"]["issuerAuth"]
    certificate = x509.load_der_x509_certificate(issuer_auth[1][33])
    public = certificate.public_key()
    if not isinstance(public, ec.EllipticCurvePublicKey):
        raise Error("embedded certificate does not carry an EC public key")
    try:
        _cose_verify(public, issuer_auth[2], issuer_auth[3])
    except InvalidSignature as e:
        raise Error("issuer signature does not verify against the embedded certificate") from e


@dataclass(frozen=True)
class CreatedCredential:
    """A credential from [`create_credential`][pylongfellow.mdoc.create_credential].

    Attributes:
        mdoc: CBOR-encoded ``DeviceResponse`` bytes.
        issuer_key: Private key whose signature the MSO carries.
        issuer_certificate: Leaf certificate embedded in ``issuerAuth``'s
            x5chain header.
        device_key: Private key matching the MSO's ``deviceKeyInfo``.
    """

    mdoc: bytes
    issuer_key: ec.EllipticCurvePrivateKey
    issuer_certificate: x509.Certificate
    device_key: ec.EllipticCurvePrivateKey

    @property
    def issuer_pk(self) -> tuple[int, int]:
        """The issuer public key as ``(x, y)``, the form the prover and verifier take."""
        numbers = self.issuer_key.public_key().public_numbers()
        return (numbers.x, numbers.y)


def create_credential(
    doc_type: str,
    claims: Mapping[str, Mapping[str, object]],
    transcript: bytes,
    valid_from: datetime,
    valid_until: datetime,
    *,
    device_namespaces: Mapping[str, Mapping[str, object]] | None = None,
    issuer_key: ec.EllipticCurvePrivateKey | None = None,
    device_key: ec.EllipticCurvePrivateKey | None = None,
    issuer_certificate: x509.Certificate | None = None,
) -> CreatedCredential:
    """Create a test mdoc credential under locally held keys.

    Assembles an ISO 18013-5 ``DeviceResponse`` holding one document. Each
    claim becomes an ``IssuerSignedItem`` with a fresh 16-byte ``random`` and a
    per-namespace sequential ``digestID``, digested into an MSO signed by the
    issuer key. The device signature covers ``DeviceAuthentication`` over the
    transcript, the doctype, and the device namespaces. Before returning, both
    signatures are verified back off the encoded bytes with `cryptography`.

    Deployed wallets emit an empty device-namespace map; `device_namespaces`
    yields a credential whose device signature covers a non-empty one.

    Args:
        doc_type: Doctype of the single document.
        claims: Issuer-signed claims, as namespace to element identifier to
            element value. Values are encoded with `cbor2`; map order is
            preserved.
        transcript: CBOR-encoded session transcript the device signature is
            bound to. Presenting under another transcript requires re-signing,
            see
            [`sign_device_authentication`][pylongfellow.mdoc.sign_device_authentication].
        valid_from: MSO ``signed``/``validFrom`` timestamp, and the generated
            certificate's window start; timezone-aware.
        valid_until: MSO ``validUntil`` timestamp, and the generated
            certificate's window end; timezone-aware.
        device_namespaces: Device-signed items, as namespace to element
            identifier to element value. None issues the empty map.
        issuer_key: Issuer private key; a fresh P-256 key is generated when
            None.
        device_key: Device private key; a fresh P-256 key is generated when
            None.
        issuer_certificate: Leaf certificate to embed in the x5chain header;
            must certify `issuer_key`. A self-signed leaf over `issuer_key` is
            generated when None.

    Returns:
        The credential bytes together with the keys and certificate that
        signed them.

    Raises:
        ValueError: `valid_from` or `valid_until` is naive.
        Error: The encoded credential failed its signature self-check; with a
            caller-supplied `issuer_certificate` this means the certificate
            does not certify `issuer_key` or does not carry an EC key.
    """
    valid_from = _require_utc(valid_from, "valid_from")
    valid_until = _require_utc(valid_until, "valid_until")
    if issuer_key is None:
        issuer_key = ec.generate_private_key(ec.SECP256R1())
    if device_key is None:
        device_key = ec.generate_private_key(ec.SECP256R1())
    if issuer_certificate is None:
        issuer_certificate = create_certificate(
            "pylongfellow test issuer",
            issuer_key.public_key(),
            "pylongfellow test issuer",
            issuer_key,
            valid_from,
            valid_until,
        )

    namespaces: dict[str, list[cbor2.CBORTag]] = {}
    digests: dict[str, dict[int, bytes]] = {}
    for space, elements in claims.items():
        for digest_id, (identifier, value) in enumerate(elements.items()):
            item = cbor2.CBORTag(
                24,
                cbor2.dumps(
                    {
                        "random": os.urandom(16),
                        "digestID": digest_id,
                        "elementIdentifier": identifier,
                        "elementValue": value,
                    }
                ),
            )
            namespaces.setdefault(space, []).append(item)
            digests.setdefault(space, {})[digest_id] = hashlib.sha256(cbor2.dumps(item)).digest()

    device_numbers = device_key.public_key().public_numbers()
    mso = {
        "docType": doc_type,
        "version": "1.0",
        "digestAlgorithm": "SHA-256",
        "valueDigests": digests,
        "deviceKeyInfo": {
            "deviceKey": {
                1: 2,
                -1: 1,
                -2: device_numbers.x.to_bytes(32, "big"),
                -3: device_numbers.y.to_bytes(32, "big"),
            }
        },
        "validityInfo": {
            "signed": _tdate(valid_from),
            "validFrom": _tdate(valid_from),
            "validUntil": _tdate(valid_until),
        },
    }
    mso_payload = cbor2.dumps(cbor2.CBORTag(24, cbor2.dumps(mso)))

    device_items = {space: dict(elements) for space, elements in (device_namespaces or {}).items()}
    device_namespaces_item = cbor2.CBORTag(24, cbor2.dumps(device_items))
    device_signature = sign_device_authentication(
        device_key, transcript, doc_type, device_namespaces_item
    )

    credential = cbor2.dumps(
        {
            "version": "1.0",
            "documents": [
                {
                    "docType": doc_type,
                    "issuerSigned": {
                        "nameSpaces": namespaces,
                        "issuerAuth": [
                            _COSE_ES256_PROTECTED,
                            {33: issuer_certificate.public_bytes(serialization.Encoding.DER)},
                            mso_payload,
                            _cose_sign(issuer_key, mso_payload),
                        ],
                    },
                    "deviceSigned": {
                        "nameSpaces": device_namespaces_item,
                        "deviceAuth": {
                            "deviceSignature": [
                                _COSE_ES256_PROTECTED,
                                {},
                                None,
                                device_signature,
                            ]
                        },
                    },
                }
            ],
            "status": 0,
        }
    )
    _check_issuer_auth(credential)
    verify_device_authentication(credential, transcript)
    return CreatedCredential(credential, issuer_key, issuer_certificate, device_key)

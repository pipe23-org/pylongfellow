"""create_credential and its companions — assembly, signatures, and the self-check.

Every assertion re-derives COSE structures and digests with cryptography/cbor2
directly; no ZK backend is involved anywhere in this file.
"""

import hashlib
from datetime import UTC, datetime, timedelta, timezone

import cbor2
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.x509.oid import NameOID

from pylongfellow import mdoc

VALID_FROM = datetime(2026, 7, 1, tzinfo=UTC)
VALID_UNTIL = datetime(2036, 7, 1, tzinfo=UTC)
DOC_TYPE = "eu.europa.ec.av.1"
CLAIMS = {"eu.europa.ec.av.1": {"age_over_18": True}}
TRANSCRIPT = cbor2.dumps([None, None, ["dcapi", hashlib.sha256(b"test handover").digest()]])
COSE_ES256_PROTECTED = b"\xa1\x01\x26"


def _verify_cose(public_key, payload, signature):
    structure = cbor2.dumps(["Signature1", COSE_ES256_PROTECTED, b"", payload])
    der = encode_dss_signature(
        int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    )
    public_key.verify(der, structure, ec.ECDSA(hashes.SHA256()))


def _document(created):
    return cbor2.loads(created.mdoc)["documents"][0]


def _mso(document):
    return cbor2.loads(cbor2.loads(document["issuerSigned"]["issuerAuth"][2]).value)


def _device_auth_payload(transcript, doc_type, namespaces):
    authentication = ["DeviceAuthentication", cbor2.loads(transcript), doc_type, namespaces]
    return cbor2.dumps(cbor2.CBORTag(24, cbor2.dumps(authentication)))


def _point(public_key):
    return public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def test_device_response_shape():
    created = mdoc.create_credential(DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, VALID_UNTIL)
    response = cbor2.loads(created.mdoc)
    assert response["version"] == "1.0"
    assert response["status"] == 0
    document = response["documents"][0]
    assert document["docType"] == DOC_TYPE
    assert document["deviceSigned"]["nameSpaces"] == cbor2.CBORTag(24, b"\xa0")
    assert document["deviceSigned"]["deviceAuth"]["deviceSignature"][:3] == [
        COSE_ES256_PROTECTED,
        {},
        None,
    ]


def test_issuer_signature_digests_and_claims():
    claims: dict[str, dict[str, object]] = {
        "eu.europa.ec.av.1": {"age_over_18": True, "issuance_date": "2026-07-01"},
        "org.iso.18013.5.1": {"age_over_18": True},
    }
    created = mdoc.create_credential(DOC_TYPE, claims, TRANSCRIPT, VALID_FROM, VALID_UNTIL)
    document = _document(created)
    issuer_auth = document["issuerSigned"]["issuerAuth"]
    _verify_cose(created.issuer_key.public_key(), issuer_auth[2], issuer_auth[3])
    mso = _mso(document)
    assert mso["docType"] == DOC_TYPE
    assert mso["digestAlgorithm"] == "SHA-256"
    decoded: dict[str, dict[str, object]] = {}
    for space, items in document["issuerSigned"]["nameSpaces"].items():
        for wrapped in items:
            item = cbor2.loads(wrapped.value)
            assert len(item["random"]) == 16
            digest = mso["valueDigests"][space][item["digestID"]]
            assert digest == hashlib.sha256(cbor2.dumps(wrapped)).digest()
            decoded.setdefault(space, {})[item["elementIdentifier"]] = item["elementValue"]
    assert decoded == claims


def test_mso_validity_window_is_zulu_whole_seconds():
    plus_two = timezone(timedelta(hours=2))
    created = mdoc.create_credential(
        DOC_TYPE,
        CLAIMS,
        TRANSCRIPT,
        datetime(2026, 7, 1, 2, 0, tzinfo=plus_two),
        VALID_UNTIL,
    )
    document = _document(created)
    validity = _mso(document)["validityInfo"]
    assert validity["signed"] == datetime(2026, 7, 1, tzinfo=UTC)
    assert validity["validFrom"] == datetime(2026, 7, 1, tzinfo=UTC)
    assert validity["validUntil"] == datetime(2036, 7, 1, tzinfo=UTC)
    # cbor2 decodes tag 0 back to datetime; the wire form is asserted on the raw MSO bytes.
    mso_bytes = cbor2.loads(document["issuerSigned"]["issuerAuth"][2]).value
    assert mso_bytes.count(b"2026-07-01T00:00:00Z") == 2
    assert mso_bytes.count(b"2036-07-01T00:00:00Z") == 1


def test_device_namespaces_are_signed():
    device = {"eu.europa.ec.av.1": {"operational_status": "test"}}
    created = mdoc.create_credential(
        DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, VALID_UNTIL, device_namespaces=device
    )
    document = _document(created)
    namespaces = document["deviceSigned"]["nameSpaces"]
    assert cbor2.loads(namespaces.value) == device
    cose_key = _mso(document)["deviceKeyInfo"]["deviceKey"]
    device_public = ec.EllipticCurvePublicNumbers(
        int.from_bytes(cose_key[-2], "big"), int.from_bytes(cose_key[-3], "big"), ec.SECP256R1()
    ).public_key()
    payload = _device_auth_payload(TRANSCRIPT, DOC_TYPE, namespaces)
    signature = document["deviceSigned"]["deviceAuth"]["deviceSignature"][3]
    _verify_cose(device_public, payload, signature)


def test_supplied_keys_and_certificate_are_used():
    issuer_key = ec.generate_private_key(ec.SECP256R1())
    device_key = ec.generate_private_key(ec.SECP256R1())
    ca_key = ec.generate_private_key(ec.SECP256R1())
    leaf = mdoc.create_certificate(
        "leaf", issuer_key.public_key(), "test CA", ca_key, VALID_FROM, VALID_UNTIL
    )
    created = mdoc.create_credential(
        DOC_TYPE,
        CLAIMS,
        TRANSCRIPT,
        VALID_FROM,
        VALID_UNTIL,
        issuer_key=issuer_key,
        device_key=device_key,
        issuer_certificate=leaf,
    )
    assert created.issuer_key is issuer_key
    assert created.device_key is device_key
    assert created.issuer_certificate is leaf
    document = _document(created)
    assert document["issuerSigned"]["issuerAuth"][1][33] == leaf.public_bytes(
        serialization.Encoding.DER
    )
    device_numbers = device_key.public_key().public_numbers()
    cose_key = _mso(document)["deviceKeyInfo"]["deviceKey"]
    assert cose_key[-2] == device_numbers.x.to_bytes(32, "big")
    assert cose_key[-3] == device_numbers.y.to_bytes(32, "big")
    issuer_numbers = issuer_key.public_key().public_numbers()
    assert created.issuer_pk == (issuer_numbers.x, issuer_numbers.y)


def test_generated_leaf_is_self_signed_over_issuer_key():
    created = mdoc.create_credential(DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, VALID_UNTIL)
    certificate = created.issuer_certificate
    assert certificate.subject == certificate.issuer
    certificate.verify_directly_issued_by(certificate)
    assert _point(certificate.public_key()) == _point(created.issuer_key.public_key())


def test_mismatched_certificate_fails_self_check():
    other_key = ec.generate_private_key(ec.SECP256R1())
    certificate = mdoc.create_certificate(
        "other", other_key.public_key(), "other", other_key, VALID_FROM, VALID_UNTIL
    )
    with pytest.raises(mdoc.Error, match="does not verify against the embedded certificate"):
        mdoc.create_credential(
            DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, VALID_UNTIL, issuer_certificate=certificate
        )


def test_non_ec_certificate_fails_self_check():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "rsa")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(VALID_FROM)
        .not_valid_after(VALID_UNTIL)
        .sign(key, hashes.SHA256())
    )
    with pytest.raises(mdoc.Error, match="EC public key"):
        mdoc.create_credential(
            DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, VALID_UNTIL, issuer_certificate=certificate
        )


def test_naive_validity_rejected():
    with pytest.raises(ValueError, match="valid_from must be timezone-aware"):
        mdoc.create_credential(DOC_TYPE, CLAIMS, TRANSCRIPT, datetime(2026, 7, 1), VALID_UNTIL)
    with pytest.raises(ValueError, match="valid_until must be timezone-aware"):
        mdoc.create_credential(DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, datetime(2036, 7, 1))


def test_certificate_ca_and_leaf_extensions():
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = mdoc.create_certificate(
        "test CA", ca_key.public_key(), "test CA", ca_key, VALID_FROM, VALID_UNTIL, ca=True
    )
    basic = ca.extensions.get_extension_for_class(x509.BasicConstraints)
    assert basic.critical
    assert basic.value.ca is True
    ca_usage = ca.extensions.get_extension_for_class(x509.KeyUsage).value
    assert ca_usage.key_cert_sign
    assert ca_usage.crl_sign
    assert not ca_usage.digital_signature

    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf = mdoc.create_certificate(
        "leaf", leaf_key.public_key(), "test CA", ca_key, VALID_FROM, VALID_UNTIL
    )
    with pytest.raises(x509.ExtensionNotFound):
        leaf.extensions.get_extension_for_class(x509.BasicConstraints)
    leaf_usage = leaf.extensions.get_extension_for_class(x509.KeyUsage).value
    assert leaf_usage.digital_signature
    assert not leaf_usage.key_cert_sign
    leaf.verify_directly_issued_by(ca)
    assert leaf.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "leaf"
    assert leaf.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "test CA"
    assert leaf.not_valid_before_utc == VALID_FROM
    assert leaf.not_valid_after_utc == VALID_UNTIL


def test_certificate_naive_validity_rejected():
    key = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(ValueError, match="valid_from must be timezone-aware"):
        mdoc.create_certificate("x", key.public_key(), "x", key, datetime(2026, 7, 1), VALID_UNTIL)


def test_sign_device_authentication_round_trip():
    device_key = ec.generate_private_key(ec.SECP256R1())
    namespaces = cbor2.CBORTag(24, cbor2.dumps({"ns": {"id": 1}}))
    signature = mdoc.sign_device_authentication(device_key, TRANSCRIPT, DOC_TYPE, namespaces)
    assert len(signature) == 64
    payload = _device_auth_payload(TRANSCRIPT, DOC_TYPE, namespaces)
    _verify_cose(device_key.public_key(), payload, signature)


def test_verify_device_authentication_accepts_and_rejects():
    created = mdoc.create_credential(DOC_TYPE, CLAIMS, TRANSCRIPT, VALID_FROM, VALID_UNTIL)
    mdoc.verify_device_authentication(created.mdoc, TRANSCRIPT)
    other_transcript = cbor2.dumps([None, None, ["dcapi", hashlib.sha256(b"other").digest()]])
    with pytest.raises(mdoc.Error, match="does not verify over the transcript"):
        mdoc.verify_device_authentication(created.mdoc, other_transcript)

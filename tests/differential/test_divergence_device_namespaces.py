"""Non-empty device namespaces: what a full prove and a full verify do with a
credential whose device signed a non-empty DeviceNameSpaces map. The pairing join
in test_interop.py already carries this case for every matching circuit; these
tests are the record's dedicated probe. The entry in README.md Recorded
divergences carries the source citations.
"""

from collections.abc import Callable

import pytest

from pylongfellow import Pylongfellow

from .conftest import _GOOGLE_DEVICE_NAMESPACES_XFAIL, CIRCUITS, PRESENTATIONS, Circuit

_PRESENTATION = next(p for p in PRESENTATIONS if p.device_namespaces not in (None, b"\xa0"))
_CIRCUIT = next(c for c in CIRCUITS if c.num_attributes == len(_PRESENTATION.attrs))


@_GOOGLE_DEVICE_NAMESPACES_XFAIL
def test_google_cpp_prove_accepts_nonempty_device_namespaces(longfellow_for) -> None:
    p = _PRESENTATION
    mdoc_bytes = p.mdoc_bytes
    assert mdoc_bytes is not None
    prover = longfellow_for("google-cpp", _CIRCUIT)
    proof = prover.prove(mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
    assert proof


@pytest.mark.slow
def test_isrg_rust_prove_accepts_nonempty_device_namespaces(longfellow_for) -> None:
    p = _PRESENTATION
    mdoc_bytes = p.mdoc_bytes
    assert mdoc_bytes is not None
    prover = longfellow_for("isrg-rust", _CIRCUIT)
    proof = prover.prove(mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)
    assert proof


@pytest.fixture(scope="module")
def device_namespaces_proof(
    longfellow_for: Callable[[str, Circuit], Pylongfellow],
) -> bytes:
    """The presentation's proof, produced by isrg-rust.

    No proof is committed under presentations/device-namespaces-nonempty/, so the
    verify pair proves it here instead of reading a corpus proof file.
    """
    p = _PRESENTATION
    mdoc_bytes = p.mdoc_bytes
    assert mdoc_bytes is not None
    prover = longfellow_for("isrg-rust", _CIRCUIT)
    return prover.prove(mdoc_bytes, p.issuer_pk, p.transcript, p.attrs, p.timestamp)


@pytest.mark.slow
@_GOOGLE_DEVICE_NAMESPACES_XFAIL
def test_google_cpp_verify_accepts_nonempty_device_namespaces(
    longfellow_for, device_namespaces_proof: bytes
) -> None:
    p = _PRESENTATION
    verifier = longfellow_for("google-cpp", _CIRCUIT)
    verifier.verify(
        p.issuer_pk,
        p.transcript,
        p.attrs,
        p.timestamp,
        device_namespaces_proof,
        p.doctype,
        device_namespaces=p.device_namespaces,
    )


@pytest.mark.slow
def test_isrg_rust_verify_accepts_nonempty_device_namespaces(
    longfellow_for, device_namespaces_proof: bytes
) -> None:
    p = _PRESENTATION
    verifier = longfellow_for("isrg-rust", _CIRCUIT)
    verifier.verify(
        p.issuer_pk,
        p.transcript,
        p.attrs,
        p.timestamp,
        device_namespaces_proof,
        p.doctype,
        device_namespaces=p.device_namespaces,
    )

"""Corpus loading and the case join.

Sidecars and presentation.json files are read into plain records at collection
time; the join computes the (circuit, presentation, prover, verifier) tuples
the relationship tests parametrize over. A tuple whose inputs the corpus cannot
supply is parametrized as a skip carrying the reason, and its id and reason are
collected in UNTESTABLE_CELLS. The corpus contract is README.md in this
directory.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import _REGISTRY, BackendUnavailableError

CORPUS = Path(__file__).parent
CIRCUITS_DIR = CORPUS / "circuits"
PRESENTATIONS_DIR = CORPUS / "presentations"

# Verifier backends whose FFI takes device_namespaces as a required parameter.
_NEEDS_DEVICE_NAMESPACES = frozenset({"isrg-rust"})

_NO_MDOC_CLAUSE = "the capture carries no mdoc bytes, which the prover requires as input"


class ObservationWarning(Warning):
    """An observed event that breaks no contract (see README taxonomy)."""


@dataclass(frozen=True)
class Circuit:
    stem: str
    path: Path
    sidecar: dict[str, Any]

    @property
    def circuit_id(self) -> str:
        return str(self.sidecar["circuit_id"])

    @property
    def version(self) -> int:
        return int(self.sidecar["version"])

    @property
    def num_attributes(self) -> int:
        return int(self.sidecar["num_attributes"])

    @property
    def byte_sha256(self) -> str:
        return str(self.sidecar["byte_sha256"])


@dataclass(frozen=True)
class Proof:
    path: Path
    sidecar: dict[str, Any]

    @property
    def prover(self) -> str:
        return str(self.sidecar["prover"])

    @property
    def circuit_id(self) -> str:
        return str(self.sidecar["circuit_id"])


@dataclass(frozen=True)
class Presentation:
    name: str
    path: Path
    doc: dict[str, Any]
    proofs: tuple[Proof, ...]

    @property
    def doctype(self) -> str:
        return str(self.doc["doctype"])

    @property
    def attrs(self) -> list[mdoc.RequestedAttribute]:
        return [
            mdoc.RequestedAttribute(a["namespace"], a["id"], bytes.fromhex(a["cbor_value_hex"]))
            for a in self.doc["attrs"]
        ]

    @property
    def transcript(self) -> bytes:
        return bytes.fromhex(self.doc["transcript_hex"])

    @property
    def issuer_pk(self) -> mdoc.PublicKey:
        return mdoc.PublicKey(int(self.doc["issuer_pk_x"], 16), int(self.doc["issuer_pk_y"], 16))

    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(self.doc["timestamp"])

    @property
    def mdoc_bytes(self) -> bytes | None:
        if "mdoc_hex" not in self.doc:
            return None
        return bytes.fromhex(self.doc["mdoc_hex"])

    @property
    def device_namespaces(self) -> bytes | None:
        if "device_namespaces_hex" not in self.doc:
            return None
        return bytes.fromhex(self.doc["device_namespaces_hex"])


def load_circuits() -> tuple[Circuit, ...]:
    return tuple(
        Circuit(
            stem=path.stem, path=path, sidecar=json.loads(path.with_suffix(".json").read_text())
        )
        for path in sorted(CIRCUITS_DIR.glob("*.circuit"))
    )


def load_presentations() -> tuple[Presentation, ...]:
    presentations = []
    for directory in sorted(p for p in PRESENTATIONS_DIR.iterdir() if p.is_dir()):
        proofs = tuple(
            Proof(path=path, sidecar=json.loads(path.with_suffix(".json").read_text()))
            for path in sorted(directory.glob("*.proof"))
        )
        presentations.append(
            Presentation(
                name=directory.name,
                path=directory,
                doc=json.loads((directory / "presentation.json").read_text()),
                proofs=proofs,
            )
        )
    return tuple(presentations)


CIRCUITS = load_circuits()
PRESENTATIONS = load_presentations()
BACKENDS = tuple(sorted(_REGISTRY))
CIRCUIT_ID_FUNCTIONS: dict[str, Callable[[bytes], str]] = {
    name: importlib.import_module(_REGISTRY[name]).circuit_id for name in BACKENDS
}

_CIRCUITS_BY_ID = {c.circuit_id: c for c in CIRCUITS}


def _verifier_input_clauses(presentation: Presentation, verifier: str) -> tuple[str, ...]:
    if presentation.device_namespaces is None and verifier in _NEEDS_DEVICE_NAMESPACES:
        return (
            "the ZK response format carries no device namespaces, "
            f"which the {verifier} verifier requires as input "
            "(https://github.com/pipe23-org/pylongfellow/issues/29)",
        )
    return ()


@dataclass(frozen=True)
class VerifyCase:
    """A committed proof verified by one backend."""

    presentation: Presentation
    circuit: Circuit
    proof: Proof
    verifier: str

    @property
    def id(self) -> str:
        return f"{self.presentation.name}-{self.circuit.stem}-{self.proof.path.stem}-verify-{self.verifier}"

    @property
    def untestable(self) -> tuple[str, ...]:
        return _verifier_input_clauses(self.presentation, self.verifier)


@dataclass(frozen=True)
class RoundTripCase:
    """One prover and one verifier over a presentation's own circuit."""

    presentation: Presentation
    circuit: Circuit
    prover: str
    verifier: str

    @property
    def id(self) -> str:
        return f"{self.presentation.name}-{self.circuit.stem}-prove-{self.prover}-verify-{self.verifier}"

    @property
    def untestable(self) -> tuple[str, ...]:
        prove: tuple[str, ...] = (
            () if self.presentation.mdoc_bytes is not None else (_NO_MDOC_CLAUSE,)
        )
        return prove + _verifier_input_clauses(self.presentation, self.verifier)


def _verify_cases() -> list[VerifyCase]:
    cases: list[VerifyCase] = []
    for presentation in PRESENTATIONS:
        for proof in presentation.proofs:
            circuit = _CIRCUITS_BY_ID.get(proof.circuit_id)
            if circuit is None:
                continue  # test_integrity reports the dangling reference
            cases.extend(
                VerifyCase(presentation, circuit, proof, verifier) for verifier in BACKENDS
            )
    return cases


def _round_trip_cases() -> list[RoundTripCase]:
    return [
        RoundTripCase(presentation, circuit, prover, verifier)
        for presentation in PRESENTATIONS
        for circuit in CIRCUITS
        if circuit.num_attributes == len(presentation.attrs)
        for prover in BACKENDS
        for verifier in BACKENDS
    ]


# The google harness fixes DeviceNameSpacesBytes to the empty map (constant
# {0xD8, 0x18, 0x41, 0xA0}, lib/circuits/mdoc/mdoc_witness.h:413 @ fe83ec6), so a
# presentation whose device signed a non-empty map cannot prove or verify there.
# strict: if a google backend ever accepts one, the run fails with XPASS and the
# characterization here is wrong or upstream changed.
_GOOGLE_DEVICE_NAMESPACES_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="google fixes DeviceNameSpacesBytes to the empty map; "
    "lib/circuits/mdoc/mdoc_witness.h:413 @ fe83ec6",
)


def _untestable_reason(case: VerifyCase | RoundTripCase) -> str:
    return "untestable: " + "; ".join(case.untestable)


def _param(case: VerifyCase | RoundTripCase, backends: tuple[str, ...]) -> Any:
    if case.untestable:
        # An untestable cell runs no backend code, so it carries no slow mark and
        # appears in the summary of every run. The cell id goes in the reason
        # because pytest groups the skip summary by (location, reason).
        skip = pytest.mark.skip(reason=f"{case.id}: {_untestable_reason(case)}")
        return pytest.param(case, id=case.id, marks=[skip])
    marks = [pytest.mark.slow] if "isrg-rust" in backends else []
    if case.presentation.device_namespaces not in (None, b"\xa0") and "google-cpp" in backends:
        marks.append(_GOOGLE_DEVICE_NAMESPACES_XFAIL)
    return pytest.param(case, id=case.id, marks=marks)


VERIFY_CASES = _verify_cases()
ROUND_TRIP_CASES = _round_trip_cases()
VERIFY_PARAMS = [_param(c, (c.verifier,)) for c in VERIFY_CASES]
ROUND_TRIP_PARAMS = [_param(c, (c.prover, c.verifier)) for c in ROUND_TRIP_CASES]

_ALL_CASES: tuple[VerifyCase | RoundTripCase, ...] = (*VERIFY_CASES, *ROUND_TRIP_CASES)

UNTESTABLE_CELLS = tuple(
    {"id": case.id, "reason": _untestable_reason(case)} for case in _ALL_CASES if case.untestable
)


def spec_of(circuit: Circuit) -> mdoc.CircuitSpec:
    """Build the CircuitSpec a corpus circuit's sidecar describes."""
    return mdoc.CircuitSpec(
        system=str(circuit.sidecar["system"]),
        circuit_hash=circuit.circuit_id,
        num_attributes=circuit.num_attributes,
        version=circuit.version,
        block_enc_hash=int(circuit.sidecar["block_enc_hash"]),
        block_enc_sig=int(circuit.sidecar["block_enc_sig"]),
    )


@pytest.fixture(scope="session")
def longfellow_for() -> Callable[[str, Circuit], Pylongfellow]:
    """Return a session-cached Pylongfellow per (registry name, corpus circuit), skipping if unbuilt.

    A Pylongfellow proves and verifies over one circuit, so the cases key on the
    pair. The isrg-rust backend initialises its prover and verifier engines
    lazily per instance, and sharing the instance across cases initialises them
    once.
    """
    cache: dict[tuple[str, str], Pylongfellow | None] = {}

    def get(name: str, circuit: Circuit) -> Pylongfellow:
        key = (name, circuit.stem)
        if key not in cache:
            try:
                longfellow = Pylongfellow(backend=name)
            except BackendUnavailableError:
                cache[key] = None
            else:
                longfellow.load_circuit(spec_of(circuit), circuit.path.read_bytes())
                cache[key] = longfellow
        loaded = cache[key]
        if loaded is None:
            pytest.skip(f"{name} backend not built")
        return loaded

    return get

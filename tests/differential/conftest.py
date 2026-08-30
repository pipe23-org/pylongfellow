from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from longfellow_vectors import LongfellowVectors
from longfellow_vectors.mdoc import Circuit

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends import BackendUnavailableError

VECTORS = LongfellowVectors().mdoc

CIRCUITS = (
    "google-v6-1attr",
    "google-v6-2attr",
    "google-v6-3attr",
    "google-v6-4attr",
    "google-v7-1attr",
    "google-v7-2attr",
    "google-v7-3attr",
    "google-v7-4attr",
)

BACKENDS = ("google-cpp", "isrg-rust")

# The claims a presentation discloses at each attribute count.
DISCLOSED_CLAIMS: dict[str, dict[int, tuple[str, ...]]] = {
    "av-over-18-device-namespaces-empty": {1: ("age_over_18",)},
    "av-over-18-device-namespaces-nonempty": {1: ("age_over_18",)},
    "mdl-mustermann": {
        1: ("issue_date",),
        2: ("issue_date", "age_over_18"),
        3: ("issue_date", "age_over_18", "birth_date"),
        4: ("issue_date", "age_over_18", "birth_date", "family_name"),
    },
}

# Verification times inside each presentation's MSO validity window.
# mdl-mustermann is valid 2024-09-30..2024-10-30; the av-over-18 credential 2026-01-01..2028-01-01.
VERIFICATION_TIMES = {
    "av-over-18-device-namespaces-empty": datetime(2026, 7, 2, tzinfo=UTC),
    "av-over-18-device-namespaces-nonempty": datetime(2026, 7, 2, tzinfo=UTC),
    "mdl-mustermann": datetime(2024, 10, 1, 9, 0, tzinfo=UTC),
}

VALID_PROOFS = (
    "google-cpp-mdl-mustermann-v6-1attr",
    "google-cpp-mdl-mustermann-v7-1attr",
    "isrg-rust-av-over-18-device-namespaces-nonempty-v6-1attr",
)

BIT_FLIPPED_PROOFS = (
    "google-cpp-mdl-mustermann-v6-1attr-bit-flipped",
    "google-cpp-mdl-mustermann-v7-1attr-bit-flipped",
)

# Circuit generation makes only the highest version the library holds for an
# attribute count; an older version of a known count raises CircuitError.
GENERATED_CIRCUITS = (
    "google-v7-1attr",
    "google-v7-2attr",
    "google-v7-3attr",
    "google-v7-4attr",
)


class ObservationWarning(Warning):
    """An observed event that breaks no contract."""


@dataclass(frozen=True)
class VerifyCase:
    """A committed proof verified by one backend."""

    proof: str
    verifier: str

    @property
    def id(self) -> str:
        return f"{self.proof}-verify-{self.verifier}"


@dataclass(frozen=True)
class RoundTripCase:
    """One prover and one verifier over a presentation and a circuit."""

    presentation: str
    circuit: str
    prover: str
    verifier: str

    @property
    def id(self) -> str:
        return f"{self.presentation}-{self.circuit}-prove-{self.prover}-verify-{self.verifier}"


def _round_trip_cases() -> list[RoundTripCase]:
    return [
        RoundTripCase(presentation, circuit, prover, verifier)
        for presentation, counts in DISCLOSED_CLAIMS.items()
        for circuit in CIRCUITS
        if VECTORS.circuit(circuit).num_attributes in counts
        for prover in BACKENDS
        for verifier in BACKENDS
    ]


def _verify_cases(proofs: tuple[str, ...]) -> list[VerifyCase]:
    return [VerifyCase(proof, verifier) for proof in proofs for verifier in BACKENDS]


# The google harness fixes DeviceNameSpacesBytes to the empty map (constant
# {0xD8, 0x18, 0x41, 0xA0}, lib/circuits/mdoc/mdoc_witness.h:413 @ fe83ec6), so a
# presentation whose device signed a non-empty map cannot prove or verify there.
# strict: if a google backend ever accepts one, the run fails with XPASS and the
# characterization here is wrong or upstream changed.
_GOOGLE_DEVICE_NAMESPACES_XFAIL = pytest.mark.xfail(
    strict=True,
    raises=mdoc.Error,
    reason="google fixes DeviceNameSpacesBytes to the empty map; "
    "lib/circuits/mdoc/mdoc_witness.h:413 @ fe83ec6",
)


def _param(
    case: VerifyCase | RoundTripCase, backends: tuple[str, ...], device_namespaces: bytes | None
) -> Any:
    marks = [pytest.mark.slow] if "isrg-rust" in backends else []
    if device_namespaces != b"\xa0" and "google-cpp" in backends:
        marks.append(_GOOGLE_DEVICE_NAMESPACES_XFAIL)
    return pytest.param(case, id=case.id, marks=marks)


ROUND_TRIP_PARAMS = [
    _param(
        case,
        (case.prover, case.verifier),
        VECTORS.presentation(case.presentation).device_namespaces,
    )
    for case in _round_trip_cases()
]

VERIFY_PARAMS = [
    _param(case, (case.verifier,), VECTORS.proof(case.proof).device_namespaces)
    for case in _verify_cases(VALID_PROOFS)
]

# The xfail marks cases that expect acceptance. These cases expect rejection,
# so they take only the slow mark.
BIT_FLIPPED_PARAMS = [
    pytest.param(case, id=case.id, marks=[pytest.mark.slow] if case.verifier == "isrg-rust" else [])
    for case in _verify_cases(BIT_FLIPPED_PROOFS)
]


@pytest.fixture(scope="session")
def longfellow_for() -> Callable[[str, Circuit], Pylongfellow]:
    cache: dict[tuple[str, str], Pylongfellow | None] = {}

    def get(name: str, circuit: Circuit) -> Pylongfellow:
        key = (name, circuit.name)
        if key not in cache:
            try:
                longfellow = Pylongfellow(backend=name)
            except BackendUnavailableError:
                cache[key] = None
            else:
                longfellow.load_circuit(circuit.bytes, circuit.version, circuit.num_attributes)
                cache[key] = longfellow
        loaded = cache[key]
        if loaded is None:
            pytest.skip(f"{name} backend not built")
        return loaded

    return get

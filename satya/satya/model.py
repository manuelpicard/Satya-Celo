"""Data model: evidence (Befund) and result (Ergebnis).

Core rule of Satya: only evidence of tier PROOF may ever lead to a definitive verdict.
PROOF = a cryptographically verifiable statement of an identifiable, accountable party
        (trusted C2PA signer, verified HMN human, registered AI provider) that any third
        party can re-check independently.
HINT  = everything else (unsigned metadata, open watermarks, statistics, similarity).
INFO  = neutral technical notes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Tier(str, Enum):
    PROOF = "beweis"
    HINT = "indiz"
    INFO = "info"


class Direction(str, Enum):
    AI = "ki"  # AI involvement
    HUMAN = "mensch"  # verified human declares: no AI
    CAPTURE = "kamera"  # signed camera/device capture, no AI declared
    BROKEN = "bruch"  # signed provenance exists but content changed afterwards
    NEUTRAL = "neutral"


class Verdict(str, Enum):
    AI_PROVEN = "KI_NACHGEWIESEN"
    HUMAN_ATTESTED = "MENSCH_BEZEUGT"
    CAPTURE_PROVEN = "KAMERA_NACHGEWIESEN"
    CONTRADICTION = "WIDERSPRUCH"
    PROVENANCE_BROKEN = "HERKUNFT_GEBROCHEN"
    UNDETERMINED = "UNBESTIMMT"


CERTAIN_VERDICTS = {Verdict.AI_PROVEN, Verdict.HUMAN_ATTESTED, Verdict.CAPTURE_PROVEN}


@dataclass
class Evidence:
    source: str  # c2pa | siegel | register | metadaten | wasserzeichen | aehnlichkeit | text
    tier: Tier
    direction: Direction
    title: str
    detail: str
    issuer: str | None = None  # who vouches (signer / person / provider)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tier"] = self.tier.value
        d["direction"] = self.direction.value
        return d


@dataclass
class Result:
    verdict: Verdict
    certain: bool
    headline: str
    explanation: str
    content: dict
    proofs: list[Evidence]
    hints: list[Evidence]
    notes: list[Evidence]
    limits: str

    def to_dict(self) -> dict:
        return {
            "urteil": self.verdict.value,
            "sicher": self.certain,
            "ueberschrift": self.headline,
            "erklaerung": self.explanation,
            "inhalt": self.content,
            "beweise": [e.to_dict() for e in self.proofs],
            "indizien": [e.to_dict() for e in self.hints],
            "hinweise": [e.to_dict() for e in self.notes],
            "grenzen": self.limits,
        }

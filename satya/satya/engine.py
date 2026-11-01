"""Satya engine: runs all checks and turns evidence into a verdict."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .c2pa_check import C2paChecker, TrustConfig, sniff_mime
from .hashing import count_invisible, phash64, sha256_bytes, simhash64, text_hash
from .ledger import Ledger, seal_evidence
from .metadata_check import check_metadata
from .model import Direction, Evidence, Result, Tier
from .seal import Seal, extract_seal
from .verdict import LIMITS, decide
from .watermark_check import ProviderDetector, check_open_watermarks

__version__ = "0.1.0"


@dataclass
class Config:
    trust: TrustConfig = field(default_factory=TrustConfig.default)
    rpc_url: str | None = None
    registry: str | None = None
    open_watermarks: bool = True
    similarity: bool = True
    providers: list[ProviderDetector] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Config":
        demo_ca = os.environ.get("SATYA_DEMO_CA")
        trust = TrustConfig.default(demo_ca, "Satya DEMO") if demo_ca else TrustConfig.default()
        trust.allow_remote_manifests = os.environ.get("SATYA_REMOTE_MANIFESTS") == "1"
        return cls(trust=trust, rpc_url=os.environ.get("SATYA_RPC"), registry=os.environ.get("SATYA_REGISTRY"))


def _looks_like_text(data: bytes) -> bool:
    if not data or b"\x00" in data[:4096]:
        return False
    try:
        data[:65536].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


class Satya:
    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.c2pa = C2paChecker(self.config.trust)
        self.ledger: Ledger | None = None
        self.ledger_error: str | None = None
        if self.config.rpc_url and self.config.registry:
            try:
                self.ledger = Ledger(self.config.rpc_url, self.config.registry)
            except Exception as e:  # noqa: BLE001
                self.ledger_error = str(e)[:200]

    # --------------------------------------------------------------- public
    def check_file(self, data: bytes, filename: str | None = None, seal: Seal | None = None) -> Result:
        mime = sniff_mime(data, filename)
        if mime is None and _looks_like_text(data):
            return self.check_text(data.decode("utf-8"))
        h = sha256_bytes(data)
        soft = phash64(data) if mime and mime.startswith("image/") else None
        content = {"art": "datei", "dateiname": filename, "mime": mime or "unbekannt", "bytes": len(data),
                   "sha256": h, "fingerabdruck": soft}
        ev: list[Evidence] = []
        ev += self.c2pa.check(data, mime)
        ev += check_metadata(data, mime)
        if self.config.open_watermarks:
            ev += check_open_watermarks(data, mime)
        for p in self.config.providers:
            ev += p.check(data, mime)
        if seal is not None:
            ev += seal_evidence(seal, h, self.ledger)
        ev += self._ledger_checks(h, soft)
        return self._result(ev, content)

    def check_text(self, text: str) -> Result:
        clean, seal, seal_err = extract_seal(text)
        h = text_hash(clean)
        soft = simhash64(clean)
        content = {"art": "text", "zeichen": len(clean), "sha256": h, "normalisierung": "satya-text-v1",
                   "fingerabdruck": soft, "siegel": seal is not None}
        ev: list[Evidence] = []
        if seal_err:
            ev.append(Evidence("siegel", Tier.INFO, Direction.NEUTRAL, "Siegel nicht lesbar", seal_err))
        if seal is not None:
            ev += seal_evidence(seal, h, self.ledger)
        n_inv = count_invisible(text)
        if n_inv:
            ev.append(Evidence("text", Tier.INFO, Direction.NEUTRAL, f"{n_inv} unsichtbare Unicode-Zeichen gefunden",
                               "Solche Zeichen können versteckte Markierungen enthalten (z. B. Text-Herkunftsdaten) "
                               "oder vom Kopieren stammen. Sie werden für den Hash entfernt. Allein sind sie kein Indiz für KI."))
        ev.append(Evidence("text", Tier.INFO, Direction.NEUTRAL, "Keine statistische KI-Texterkennung",
                           "Satya bewertet Texte bewusst nicht nach Stil oder Wortstatistik: Solche Detektoren "
                           "lassen sich durch Umformulieren täuschen und beschuldigen nachweislich überdurchschnittlich "
                           "oft Nicht-Muttersprachler. Anbieter-Wasserzeichen (z. B. SynthID-Text) können per Plugin "
                           "angebunden werden, zählen aber ebenfalls nur als Indiz."))
        ev += self._ledger_checks(h, soft)
        return self._result(ev, content)

    def status(self) -> dict:
        import c2pa

        led = None
        if self.ledger:
            try:
                led = self.ledger.info()
            except Exception as e:  # noqa: BLE001
                led = {"fehler": str(e)[:200]}
        return {
            "version": __version__, "c2pa_sdk": c2pa.sdk_version(),
            "vertrauensliste": {"c2pa_anker": self.config.trust.official_anchors.count("BEGIN CERTIFICATE"),
                                "tsa_anker": self.config.trust.tsa_anchors.count("BEGIN CERTIFICATE"),
                                "demo_anker": self.config.trust.extra_anchors.count("BEGIN CERTIFICATE")},
            "register": led or {"verbunden": False, "fehler": self.ledger_error},
        }

    # -------------------------------------------------------------- private
    def _ledger_checks(self, h: str, soft: str | None) -> list[Evidence]:
        if self.ledger is None:
            return [Evidence("register", Tier.INFO, Direction.NEUTRAL, "Herkunftsregister nicht verbunden",
                             "Ohne Verbindung zum Satya-Register können Erklärungen verifizierter Menschen und "
                             "registrierter KI-Anbieter nicht geprüft werden.")]
        try:
            ev = self.ledger.lookup(h)
            if not ev:
                ev.append(Evidence("register", Tier.INFO, Direction.NEUTRAL, "Kein Eintrag im Herkunftsregister",
                                   "Für genau diesen Inhalt hat bisher weder ein verifizierter Mensch noch ein "
                                   "registrierter KI-Anbieter eine Erklärung abgegeben."))
            if self.config.similarity:
                ev += self.ledger.similar(soft, h)
            return ev
        except Exception as e:  # noqa: BLE001
            return [Evidence("register", Tier.INFO, Direction.NEUTRAL, "Registerabfrage fehlgeschlagen", str(e)[:200])]

    @staticmethod
    def _result(ev: list[Evidence], content: dict) -> Result:
        verdict, certain, headline, explanation = decide(ev)
        return Result(verdict=verdict, certain=certain, headline=headline, explanation=explanation, content=content,
                      proofs=[e for e in ev if e.tier == Tier.PROOF], hints=[e for e in ev if e.tier == Tier.HINT],
                      notes=[e for e in ev if e.tier == Tier.INFO], limits=LIMITS)

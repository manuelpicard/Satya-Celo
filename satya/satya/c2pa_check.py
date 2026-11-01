"""C2PA / Content Credentials check.

Tier mapping (conservative on purpose):
  * Trusted manifest (signer chains to a configured trust list) whose bytes match
      -> PROOF. Direction AI if any manifest in the provenance chain declares a
         trained-AI digitalSourceType; CAPTURE if the origin is a device capture;
         otherwise HINT/NEUTRAL (a software signature without AI declaration does not
         prove the absence of AI - imported material may come from anywhere).
  * Valid but untrusted signer -> HINT (anyone can create a self-signed certificate).
  * Hash mismatch -> PROOF of BROKEN provenance (bytes differ from what was signed);
         an AI declaration inside it is downgraded to a HINT.
  * No manifest -> INFO (absence is NOT evidence: most media has none, platforms strip it).
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

from .model import Direction, Evidence, Tier

IPTC = "http://cv.iptc.org/newscodes/digitalsourcetype/"
AI_SOURCE_TYPES = {"trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia"}
AMBIGUOUS_SOURCE_TYPES = {"compositeSynthetic", "algorithmicMedia", "dataDrivenMedia"}
CAPTURE_SOURCE_TYPES = {"digitalCapture", "computationalCapture", "compositeCapture"}

SOURCE_TYPE_DE = {
    "trainedAlgorithmicMedia": "von einem trainierten KI-Modell erzeugt",
    "compositeWithTrainedAlgorithmicMedia": "Komposition mit KI-erzeugten Anteilen",
    "compositeSynthetic": "Komposition mit synthetischen Anteilen",
    "algorithmicMedia": "rein algorithmisch erzeugt (ohne Trainingsdaten)",
    "digitalCapture": "digitale Aufnahme eines Geräts",
    "computationalCapture": "computergestützte Kamera-Aufnahme",
    "compositeCapture": "Komposition mehrerer Aufnahmen",
    "digitalCreation": "digital von Hand erstellt",
    "humanEdits": "von Menschen bearbeitet",
    "screenCapture": "Bildschirmaufnahme",
}

TRUST_DIR = Path(__file__).parent / "trust"

MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".gif": "image/gif", ".tif": "image/tiff", ".tiff": "image/tiff", ".heic": "image/heic",
    ".heif": "image/heif", ".avif": "image/avif", ".dng": "image/dng", ".svg": "image/svg+xml",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".m4v": "video/x-m4v", ".avi": "video/avi",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".flac": "audio/flac",
    ".pdf": "application/pdf",
}


def sniff_mime(data: bytes, filename: str | None = None) -> str | None:
    head = data[:64]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if head.startswith(b"%PDF"):
        return "application/pdf"
    if head.startswith(b"fLaC"):
        return "audio/flac"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heix", b"mif1", b"msf1"):
            return "image/heic"
        if brand in (b"avif", b"avis"):
            return "image/avif"
        if brand == b"qt  ":
            return "video/quicktime"
        if brand in (b"M4A ", b"M4B "):
            return "audio/mp4"
        return "video/mp4"
    if filename:
        return MIME_BY_EXT.get(Path(filename).suffix.lower())
    return None


@dataclass
class TrustConfig:
    official_anchors: str
    tsa_anchors: str
    extra_anchors: str = ""  # e.g. a DEMO CA - must be labelled as such in the UI
    extra_label: str = ""
    allow_remote_manifests: bool = False

    @classmethod
    def default(cls, extra_anchor_file: str | None = None, extra_label: str = "") -> "TrustConfig":
        extra = Path(extra_anchor_file).read_text() if extra_anchor_file else ""
        return cls(
            official_anchors=(TRUST_DIR / "C2PA-TRUST-LIST.pem").read_text(),
            tsa_anchors=(TRUST_DIR / "C2PA-TSA-TRUST-LIST.pem").read_text(),
            extra_anchors=extra,
            extra_label=extra_label,
        )

    def settings(self) -> dict:
        anchors = self.official_anchors + ("\n" + self.extra_anchors if self.extra_anchors else "")
        return {
            "trust": {
                "trust_anchors": anchors,
                "anchors": [{"trust_anchors": self.tsa_anchors, "trust_kind": "tsa"}],
            },
            "verify": {
                "verify_trust": True,
                "verify_timestamp_trust": True,
                "remote_manifest_fetch": self.allow_remote_manifests,
                "ocsp_fetch": False,
            },
        }


def _short(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if isinstance(uri, str) else str(uri)


def _walk_source_types(obj, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("digitalSourceType", "digital_source_type") and isinstance(v, str):
                found.append((_short(v), path))
            else:
                found.extend(_walk_source_types(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_walk_source_types(v, f"{path}[{i}]"))
    return found


def _collect_actions(store: dict) -> list[dict]:
    actions = []
    for label, man in (store.get("manifests") or {}).items():
        for a in man.get("assertions", []):
            if str(a.get("label", "")).startswith("c2pa.actions"):
                for act in (a.get("data") or {}).get("actions", []):
                    actions.append({"manifest": label, **act})
    return actions


class C2paChecker:
    def __init__(self, trust: TrustConfig):
        import c2pa  # imported lazily so the rest of Satya works without the native lib

        self._c2pa = c2pa
        self.trust = trust
        self._ctx = c2pa.Context.from_dict(trust.settings())

    def check(self, data: bytes, mime: str | None) -> list[Evidence]:
        c2pa = self._c2pa
        if not mime or mime not in set(c2pa.Reader.get_supported_mime_types()):
            return [Evidence("c2pa", Tier.INFO, Direction.NEUTRAL, "C2PA nicht anwendbar",
                             f"Für den Dateityp {mime or 'unbekannt'} wird kein C2PA-Manifest geprüft.")]
        try:
            reader = c2pa.Reader(mime, io.BytesIO(data), context=self._ctx)
        except Exception as e:  # noqa: BLE001 - native errors are heterogeneous
            msg = str(e)
            if "Remote" in msg and "http" in msg:
                url = msg[msg.find("http"):].strip()
                return [Evidence("c2pa", Tier.INFO, Direction.NEUTRAL, "Externes C2PA-Manifest nicht abgerufen",
                                 "Die Datei verweist auf ein extern gespeichertes Manifest. Aus Sicherheitsgründen "
                                 "lädt Satya standardmäßig keine URLs aus hochgeladenen Dateien "
                                 "(Option allow_remote_manifests).", data={"url": url})]
            if "ManifestNotFound" in msg or "JumbfNotFound" in msg or "no manifest" in msg.lower():
                return [self._no_manifest()]
            return [Evidence("c2pa", Tier.INFO, Direction.NEUTRAL, "C2PA-Daten nicht lesbar",
                             f"Fehler beim Lesen: {msg[:200]}")]

        with reader:
            store = json.loads(reader.json())
            state = reader.get_validation_state() or "Unknown"
            results = reader.get_validation_results() or {}
            active = reader.get_active_manifest() or {}
        return self._evaluate(store, state, results, active)

    @staticmethod
    def _no_manifest() -> Evidence:
        return Evidence("c2pa", Tier.INFO, Direction.NEUTRAL, "Kein C2PA-Herkunftsnachweis",
                        "Die Datei enthält keine Content Credentials. Das ist KEIN Hinweis auf KI oder Mensch: "
                        "Die meisten Medien haben keine, und viele Plattformen entfernen sie beim Hochladen.")

    def _evaluate(self, store: dict, state: str, results: dict, active: dict) -> list[Evidence]:
        am = results.get("activeManifest") or {}
        failures = [f.get("code", "") for f in am.get("failure", [])]
        infos = [f.get("code", "") for f in am.get("informational", [])]
        sig = active.get("signature_info") or {}
        issuer_org = sig.get("issuer") or "unbekannter Signierer"
        issuer = f"{issuer_org} ({sig.get('common_name')})" if sig.get("common_name") else issuer_org
        if self.trust.extra_label and self.trust.extra_label.lower() in issuer.lower():
            issuer += " [DEMO-Vertrauensanker]"
        gen = ", ".join(g.get("name", "") for g in active.get("claim_generator_info", []) if isinstance(g, dict))

        source_types = _walk_source_types(store.get("manifests") or {})
        types = {t for t, _ in source_types}
        ai_types = sorted(types & AI_SOURCE_TYPES)
        ambiguous = sorted(types & AMBIGUOUS_SOURCE_TYPES)
        capture = sorted(types & CAPTURE_SOURCE_TYPES)
        actions = _collect_actions(store)
        n_manifests = len(store.get("manifests") or {})
        data = {
            "validierung": state, "signierer": issuer, "generator": gen, "signiert_am": sig.get("time"),
            "quelltypen": sorted(types), "manifeste": n_manifests,
            "aktionen": [a.get("action") for a in actions], "fehler": failures, "info_codes": infos,
        }
        out: list[Evidence] = []

        hash_broken = any("mismatch" in f.lower() for f in failures)
        if hash_broken:
            out.append(Evidence("c2pa", Tier.PROOF, Direction.BROKEN, "Inhalt passt nicht zur C2PA-Signatur",
                                "Die Datei enthält ein C2PA-Manifest, aber die signierten Hashwerte stimmen nicht mit "
                                "den aktuellen Bytes überein: Der Inhalt wurde nach dem Signieren verändert.",
                                issuer=issuer, data=data))
            if ai_types:
                out.append(Evidence("c2pa", Tier.HINT, Direction.AI, "Ursprünglich als KI-Inhalt signiert",
                                    "Das (gebrochene) Manifest deklariert: " +
                                    "; ".join(SOURCE_TYPE_DE.get(t, t) for t in ai_types) +
                                    ". Weil der Inhalt verändert wurde, ist das nur noch ein Indiz.",
                                    issuer=issuer, data=data))
            return out

        if state == "Invalid":
            out.append(Evidence("c2pa", Tier.HINT, Direction.NEUTRAL, "C2PA-Signatur ungültig",
                                "Das Manifest ist vorhanden, aber Signatur oder Zertifikat sind ungültig "
                                f"({', '.join(failures) or 'ohne Detail'}). Es wird nicht als Nachweis gewertet.",
                                issuer=issuer, data=data))
            return out

        trusted = state == "Trusted"
        tier = Tier.PROOF if trusted else Tier.HINT
        trust_txt = ("Der Signierer ist über die konfigurierte C2PA-Vertrauensliste verifiziert."
                     if trusted else
                     "ACHTUNG: Der Signierer ist NICHT auf der Vertrauensliste. Jeder kann sich ein solches "
                     "Zertifikat selbst ausstellen, daher nur ein Indiz.")

        if ai_types:
            out.append(Evidence("c2pa", tier, Direction.AI, "C2PA: KI-Erzeugung deklariert",
                                f"Signiertes Manifest von {issuer} deklariert: " +
                                "; ".join(SOURCE_TYPE_DE.get(t, t) for t in ai_types) + f". {trust_txt}",
                                issuer=issuer, data=data))
        elif capture:
            if trusted:
                out.append(Evidence("c2pa", Tier.PROOF, Direction.CAPTURE, "C2PA: signierte Geräte-Aufnahme",
                                    f"Signiert von {issuer}: " + "; ".join(SOURCE_TYPE_DE.get(t, t) for t in capture) +
                                    ". In der gesamten Herkunftskette ist keine KI-Erzeugung deklariert. " + trust_txt,
                                    issuer=issuer, data=data))
            else:
                out.append(Evidence("c2pa", Tier.HINT, Direction.CAPTURE, "C2PA: Aufnahme deklariert (nicht vertrauenswürdig)",
                                    f"Manifest von {issuer} deklariert eine Aufnahme. {trust_txt}", issuer=issuer, data=data))
        else:
            desc = "; ".join(SOURCE_TYPE_DE.get(t, t) for t in sorted(types)) or "keine Quellenangabe"
            out.append(Evidence("c2pa", Tier.HINT, Direction.NEUTRAL, "C2PA: Herkunft ohne KI-Deklaration",
                                f"Manifest von {issuer} ({desc}). Eine Software-Signatur ohne KI-Angabe beweist nicht, "
                                f"dass keine KI beteiligt war. {trust_txt}", issuer=issuer, data=data))
        if ambiguous:
            out.append(Evidence("c2pa", Tier.HINT, Direction.AI, "C2PA: mehrdeutige Quellenangabe",
                                "Deklariert: " + "; ".join(SOURCE_TYPE_DE.get(t, t) for t in ambiguous) +
                                ". Das kann, muss aber keine KI bedeuten.", issuer=issuer, data=data))

        wm = [a for a in actions if "watermark" in str(a.get("action", "")).lower()
              or "synthid" in str(a.get("description", "")).lower()]
        if wm:
            out.append(Evidence("c2pa", Tier.INFO, Direction.NEUTRAL, "Anbieter erklärt zusätzliches Wasserzeichen",
                                "Laut Manifest wurde zusätzlich ein unsichtbares Wasserzeichen eingebettet "
                                "(z. B. SynthID). Es kann nur mit dem Prüfwerkzeug des Anbieters geprüft werden und "
                                "hilft, die Herkunft nach dem Abstreifen der Metadaten wiederzufinden.",
                                issuer=issuer))
        if "timeStamp.untrusted" in infos:
            out.append(Evidence("c2pa", Tier.INFO, Direction.NEUTRAL, "Zeitstempel nicht über TSA-Liste verifiziert",
                                "Die Signatur ist gültig; nur der Zeitstempel der Signatur stammt von einer "
                                "Zeitstempelstelle außerhalb der C2PA-TSA-Liste."))
        return out

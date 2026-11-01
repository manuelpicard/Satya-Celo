"""Verdict logic - a pure, fully deterministic function.

Guarantee (tested property-based in tests/test_verdict.py):
  * A certain verdict is returned ONLY if at least one PROOF supports it.
  * HINTs can never change the verdict; at most they are displayed.
  * Contradicting proofs never yield a certain verdict.
"""

from __future__ import annotations

from .model import CERTAIN_VERDICTS, Direction, Evidence, Tier, Verdict

LIMITS = (
    "Satya sagt nur dann „sicher“, wenn ein kryptografisch überprüfbarer Nachweis einer "
    "identifizierbaren, haftbaren Stelle vorliegt (vertrauenswürdige C2PA-Signatur, verifizierter "
    "Mensch mit HMN-Credential oder registrierter KI-Anbieter). Ohne solchen Nachweis lautet das "
    "Urteil „unbestimmt“, denn ob ein beliebiger Inhalt von irgendeiner KI stammt, lässt sich "
    "nachweislich nicht sicher feststellen: Gute KI-Ausgaben sind statistisch nicht von menschlichen "
    "unterscheidbar, Wasserzeichen lassen sich entfernen, Metadaten abstreifen und lokale "
    "Open-Source-Modelle markieren gar nichts. Ein Nachweis belegt, WER etwas erklärt, nicht, dass "
    "die Erklärung wahr ist. Falsche Erklärungen sind aber zurechenbar und werden sanktioniert."
)

HEADLINES = {
    Verdict.AI_PROVEN: "KI-Beteiligung nachgewiesen",
    Verdict.HUMAN_ATTESTED: "Von einem verifizierten Menschen als KI-frei bezeugt",
    Verdict.CAPTURE_PROVEN: "Signierte Kamera-Aufnahme, keine KI deklariert",
    Verdict.CONTRADICTION: "Widerspruch zwischen Nachweisen",
    Verdict.PROVENANCE_BROKEN: "Herkunftsnachweis gebrochen: Inhalt wurde nach der Signatur verändert",
    Verdict.UNDETERMINED: "Unbestimmt: kein überprüfbarer Herkunftsnachweis",
}


def _issuers(items: list[Evidence]) -> str:
    names = sorted({e.issuer for e in items if e.issuer})
    return ", ".join(names) if names else "unbekannt"


def decide(evidence: list[Evidence]) -> tuple[Verdict, bool, str, str]:
    proofs = [e for e in evidence if e.tier == Tier.PROOF]
    ai = [p for p in proofs if p.direction == Direction.AI]
    human = [p for p in proofs if p.direction == Direction.HUMAN]
    capture = [p for p in proofs if p.direction == Direction.CAPTURE]
    broken = [p for p in proofs if p.direction == Direction.BROKEN]

    if ai and (human or capture):
        v = Verdict.CONTRADICTION
        expl = (
            f"Es liegen sich widersprechende Nachweise vor: KI-Beteiligung laut {_issuers(ai)}, "
            f"aber „ohne KI“ laut {_issuers(human + capture)}. Mindestens eine Stelle hat eine falsche "
            "Erklärung abgegeben oder einen Schlüssel verloren. Der Fall ist öffentlich nachvollziehbar "
            "und kann als Betrug gemeldet werden."
        )
    elif ai:
        v = Verdict.AI_PROVEN
        expl = f"Eine haftbare Stelle erklärt kryptografisch überprüfbar eine KI-Beteiligung: {_issuers(ai)}."
    elif human:
        v = Verdict.HUMAN_ATTESTED
        expl = (
            f"Verifizierte Menschen haben haftbar erklärt, diesen Inhalt ohne KI erstellt zu haben: {_issuers(human)}. "
            "Das beweist die Erklärung und ihre Urheber, nicht deren Wahrheit; eine nachgewiesene Falscherklärung "
            "führt zur dauerhaften Sperre der Person."
        )
        if capture:
            expl += f" Zusätzlich liegt eine signierte Kamera-Aufnahme vor ({_issuers(capture)})."
    elif capture:
        v = Verdict.CAPTURE_PROVEN
        expl = (
            f"Ein vertrauenswürdiges Aufnahmegerät hat die Aufnahme signiert ({_issuers(capture)}) und keine "
            "KI-Bearbeitung deklariert. Das belegt eine Kamera-Aufnahme, nicht, was vor der Linse war "
            "(z. B. ein abfotografierter Bildschirm)."
        )
    elif broken:
        v = Verdict.PROVENANCE_BROKEN
        expl = (
            f"Der Inhalt trägt einen Herkunftsnachweis ({_issuers(broken)}), passt aber nicht mehr zu ihm: "
            "Er wurde nach der Signatur verändert. Über eine KI-Beteiligung kann deshalb nichts Sicheres "
            "gesagt werden."
        )
    else:
        v = Verdict.UNDETERMINED
        expl = (
            "Es wurde kein überprüfbarer Herkunftsnachweis gefunden. Ohne einen solchen Nachweis kann "
            "kein Verfahren sicher sagen, ob eine KI beteiligt war. Eventuelle Indizien unten sind "
            "ausdrücklich kein Beweis."
        )

    certain = v in CERTAIN_VERDICTS
    return v, certain, HEADLINES[v], expl

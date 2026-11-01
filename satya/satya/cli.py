"""Command line: python -m satya <pruefen|siegeln|verankern|status> ...

Environment:
  SATYA_RPC        JSON-RPC URL of the chain with the SatyaRegistry
  SATYA_REGISTRY   address of the SatyaRegistry
  SATYA_DEMO_CA    optional PEM file with DEMO trust anchors (never in production)
  SATYA_KEY        private key for siegeln/verankern (never pass keys on the command line)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .engine import Config, Satya
from .model import Result
from .seal import AI_USE_DE, extract_seal, seal_text

COLORS = {"KI_NACHGEWIESEN": "\033[91m", "MENSCH_BEZEUGT": "\033[92m", "KAMERA_NACHGEWIESEN": "\033[92m",
          "WIDERSPRUCH": "\033[95m", "HERKUNFT_GEBROCHEN": "\033[93m", "UNBESTIMMT": "\033[90m"}
RESET = "\033[0m"


def render(res: Result, color: bool = True) -> str:
    c = COLORS.get(res.verdict.value, "") if color else ""
    r = RESET if color else ""
    lines = [f"{c}■ {res.verdict.value}{r}  {res.headline}", f"  Sicher: {'ja' if res.certain else 'nein'}",
             f"  {res.explanation}", "",
             f"  Inhalt: {res.content.get('art')} · SHA-256 {res.content.get('sha256')}"]
    for label, items in (("BEWEISE", res.proofs), ("INDIZIEN (kein Beweis)", res.hints), ("HINWEISE", res.notes)):
        if items:
            lines.append(f"\n  {label}")
            for e in items:
                lines.append(f"   - [{e.source}] {e.title}" + (f"  · {e.issuer}" if e.issuer else ""))
                lines.append(f"       {e.detail}")
    lines.append(f"\n  Grenzen: {res.limits}")
    return "\n".join(lines)


def _engine() -> Satya:
    return Satya(Config.from_env())


def cmd_pruefen(a) -> int:
    eng = _engine()
    if a.text is not None:
        res = eng.check_text(a.text)
    else:
        p = Path(a.datei)
        res = eng.check_file(p.read_bytes(), p.name)
    print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2) if a.json else render(res, sys.stdout.isatty()))
    return 0


def _key() -> str:
    key = os.environ.get("SATYA_KEY")
    if not key:
        sys.exit("SATYA_KEY ist nicht gesetzt (privater Schlüssel der eigenen Wallet).")
    return key


def cmd_siegeln(a) -> int:
    eng = _engine()
    if eng.ledger is None:
        sys.exit("Register nicht verbunden: SATYA_RPC und SATYA_REGISTRY setzen.")
    src = Path(a.text_datei)
    sealed, seal = seal_text(src.read_text(encoding="utf-8"), _key(), a.ki, eng.ledger.chain_id, eng.ledger.address)
    out = Path(a.ausgabe) if a.ausgabe else src.with_suffix(".versiegelt" + src.suffix)
    out.write_text(sealed, encoding="utf-8")
    print(f"Versiegelt ({AI_USE_DE[a.ki]}) von {seal.signer} -> {out}")
    return 0


def cmd_verankern(a) -> int:
    from eth_account import Account

    eng = _engine()
    if eng.ledger is None:
        sys.exit("Register nicht verbunden.")
    _, seal, err = extract_seal(Path(a.text_datei).read_text(encoding="utf-8"))
    if seal is None:
        sys.exit(err or "Kein Siegel im Text gefunden.")
    from .hashing import simhash64, strip_seal

    soft = bytes.fromhex(simhash64(strip_seal(Path(a.text_datei).read_text(encoding="utf-8"))[0])[2:])
    acct = Account.from_key(_key())  # relayer: pays gas, need not be the signer
    w3, c = eng.ledger.w3, eng.ledger.c
    tx = c.functions.anchorSeal(seal.as_tuple(), bytes.fromhex(seal.sig[2:]), soft).build_transaction(
        {"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address), "chainId": eng.ledger.chain_id})
    signed = acct.sign_transaction(tx)
    rc = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction))
    print(f"Verankert in Block {rc['blockNumber']} (Status {rc['status']}), Tx {rc['transactionHash'].hex()}")
    return 0 if rc["status"] == 1 else 1


def cmd_status(a) -> int:
    print(json.dumps(_engine().status(), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="satya", description="Satya: überprüfbare Herkunft statt Raten.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pruefen", help="Datei oder Text prüfen")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("datei", nargs="?")
    g.add_argument("--text")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_pruefen)
    s = sub.add_parser("siegeln", help="Text als verifizierter Mensch versiegeln (offline, kostenlos)")
    s.add_argument("text_datei")
    s.add_argument("--ki", type=int, choices=[0, 1, 2], default=0, help="0=ohne KI, 1=KI-unterstützt, 2=KI-generiert")
    s.add_argument("--ausgabe")
    s.set_defaults(fn=cmd_siegeln)
    v = sub.add_parser("verankern", help="Siegel eines Textes on-chain verankern")
    v.add_argument("text_datei")
    v.set_defaults(fn=cmd_verankern)
    st = sub.add_parser("status", help="Konfiguration und Registerverbindung anzeigen")
    st.set_defaults(fn=cmd_status)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())

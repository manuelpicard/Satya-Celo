"""Evaluate Satya on the corpus with known ground truth.

Phase 1: state as built (incl. Mallory's undetected lie).
Phase 2: the lie is uncovered - governance flags Mallory's contradicting statement as fraud and
         HMN revokes her credential with fraud=true (person banned). Chain state is restored
         afterwards via evm_snapshot / evm_revert.

Also reports what a naive "hint detector" (treats every indication as an answer) would say.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from eth_account import Account
from web3 import Web3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from seed_chain import KEYS  # noqa: E402

from satya import Config, Satya  # noqa: E402
from satya.c2pa_check import TrustConfig  # noqa: E402
from satya.hashing import text_hash  # noqa: E402
from satya.model import Direction, Verdict  # noqa: E402

DEP = json.loads((HERE / "deployment.json").read_text())
CORPUS = HERE / "corpus"


def engine() -> Satya:
    trust = TrustConfig.default(str(HERE / "pki/demo-root.pem"), "Satya DEMO")
    return Satya(Config(trust=trust, rpc_url=DEP["rpc"], registry=DEP["registry"]))


def naive(res) -> str:
    ev = res.proofs + res.hints
    if any(e.direction == Direction.AI for e in ev):
        return "ki"
    if any(e.direction in (Direction.HUMAN, Direction.CAPTURE) for e in ev):
        return "mensch"
    return "keine Aussage"


def certain_claim(v: Verdict) -> str | None:
    return {Verdict.AI_PROVEN: "ki", Verdict.HUMAN_ATTESTED: "mensch", Verdict.CAPTURE_PROVEN: "mensch"}.get(v)


def run(eng: Satya) -> list[dict]:
    items = json.loads((CORPUS / "corpus.json").read_text(encoding="utf-8"))
    rows = []
    for it in items:
        p = CORPUS / it["datei"]
        res = eng.check_text(p.read_text(encoding="utf-8")) if p.suffix == ".txt" else eng.check_file(p.read_bytes(), p.name)
        claim = certain_claim(res.verdict)
        rows.append({**it, "urteil": res.verdict.value, "sicher": res.certain,
                     "korrekt": None if claim is None else claim == it["wahrheit"],
                     "naiv": naive(res), "beweise": [e.title for e in res.proofs], "indizien": [e.title for e in res.hints],
                     "aussteller": sorted({e.issuer for e in res.proofs if e.issuer})})
    return rows


def stats(rows: list[dict]) -> dict:
    n = len(rows)
    certain = [r for r in rows if r["sicher"]]
    wrong = [r for r in certain if r["korrekt"] is False]
    naive_answers = [r for r in rows if r["naiv"] != "keine Aussage"]
    naive_wrong = [r for r in naive_answers if r["naiv"] != r["wahrheit"]]
    return {"n": n, "sicher": len(certain), "sicher_korrekt": len(certain) - len(wrong), "sicher_falsch": len(wrong),
            "abdeckung": len(certain) / n, "urteile": dict(Counter(r["urteil"] for r in rows)),
            "naiv_antworten": len(naive_answers), "naiv_falsch": len(naive_wrong),
            "naiv_falsche_ki_beschuldigung": sum(1 for r in naive_wrong if r["naiv"] == "ki"),
            "falsch_sicher": [r["datei"] for r in wrong], "naiv_falsch_dateien": [r["datei"] for r in naive_wrong]}


def uncover_fraud(w3: Web3) -> None:
    gov = Account.from_key(KEYS["governance"])
    reg = w3.eth.contract(address=DEP["registry"], abi=json.loads((ROOT / "satya/abi/SatyaRegistry.json").read_text())["abi"])
    hmn = w3.eth.contract(address=DEP["hmn"], abi=json.loads((ROOT / "satya/abi/HumanCredential.json").read_text())["abi"])
    tempo = (CORPUS / "20_text_ki_tempolimit_widerspruch.txt").read_text(encoding="utf-8")
    h = Web3.to_bytes(hexstr=text_hash(tempo))
    idx = next(i for i, a in enumerate(reg.functions.attestations(h).call()) if a[0] == DEP["accounts"]["mallory"])
    token = hmn.functions.tokenOf(DEP["accounts"]["mallory"]).call()
    for fn in (reg.functions.flagFraud(h, idx), hmn.functions.revoke(token, True)):
        t = fn.build_transaction({"from": gov.address, "nonce": w3.eth.get_transaction_count(gov.address), "chainId": DEP["chainId"]})
        rc = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(gov.sign_transaction(t).raw_transaction))
        assert rc["status"] == 1


def main() -> None:
    w3 = Web3(Web3.HTTPProvider(DEP["rpc"]))
    phase1 = run(engine())
    snap = w3.provider.make_request("evm_snapshot", [])["result"]
    try:
        uncover_fraud(w3)
        phase2 = run(engine())
    finally:
        w3.provider.make_request("evm_revert", [snap])
    out = {"phase1": {"zeilen": phase1, "statistik": stats(phase1)}, "phase2": {"zeilen": phase2, "statistik": stats(phase2)}}
    (HERE / "auswertung.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for ph in ("phase1", "phase2"):
        print(ph, json.dumps(out[ph]["statistik"], ensure_ascii=False))
    for r1, r2 in zip(phase1, phase2):
        flag = "" if r1["korrekt"] is not False else "  <-- FALSCH SICHER"
        chg = f"  => nach Aufdeckung: {r2['urteil']}" if r2["urteil"] != r1["urteil"] else ""
        print(f"{r1['datei']:<42} wahr={r1['wahrheit']:<6} urteil={r1['urteil']:<20} naiv={r1['naiv']:<13}{flag}{chg}")


if __name__ == "__main__":
    main()

"""Satya web API + UI.

  GET  /                      web UI
  GET  /api/status            configuration, trust list, registry connection
  POST /api/pruefen           multipart: datei=<file>  or  text=<string>
  GET  /api/beispiele         demo corpus (if present)
  GET  /api/beispiele/{name}  check a corpus item, returns result + ground truth
  POST /api/demo/siegeln      DEMO only (SATYA_DEMO_KEYS=1): seal a text as Alice / Mallory / AI agent

Celo / agent economy:
  GET  /api/celo/status          deployment, chain head, upstream registries
  GET  /api/celo/herkunft/{hash} free read of the on-chain provenance register
  POST /api/x402/verify          paid provenance check, settled per request in USDC
  GET  /.well-known/agent.json   ERC-8004 registration file for this service

Start:  uvicorn satya.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .celo_ledger import CeloLedger, CeloLedgerConfig
from .devkeys import anvil_key
from .engine import Config, Satya
from .hashing import sha256_bytes, text_hash
from .seal import seal_text
from .x402 import PaymentError, X402Config, X402Gateway, agent_card

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
CORPUS = Path(os.environ.get("SATYA_CORPUS", ROOT / "demo/corpus"))
MAX_BYTES = 50 * 1024 * 1024
DEMO_KEYS = {  # public Anvil development accounts, derived at runtime - local demo chain only
    "alice": anvil_key(2),
    "mallory": anvil_key(3),
    "agent": anvil_key(4),
}

app = FastAPI(title="Satya", version="0.1.0")
engine = Satya(Config.from_env())

_celo_cfg = CeloLedgerConfig.from_env()
celo = CeloLedger(_celo_cfg) if _celo_cfg else None

_x402_cfg = X402Config.from_env()
x402 = X402Gateway(_x402_cfg) if _x402_cfg else None


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-store"})


@app.get("/api/status")
def status() -> dict:
    s = engine.status()
    s["demo_siegel"] = os.environ.get("SATYA_DEMO_KEYS") == "1"
    s["beispiele"] = (CORPUS / "corpus.json").exists()
    return s


@app.post("/api/pruefen")
async def pruefen(datei: UploadFile | None = File(None), text: str | None = Form(None)) -> JSONResponse:
    if datei is not None and datei.filename:
        data = await datei.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Datei größer als 50 MB")
        res = engine.check_file(data, datei.filename)
    elif text and text.strip():
        res = engine.check_text(text)
    else:
        raise HTTPException(400, "Bitte eine Datei oder einen Text übergeben.")
    return JSONResponse(res.to_dict())


def _corpus() -> list[dict]:
    p = CORPUS / "corpus.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@app.get("/api/beispiele")
def beispiele() -> list[dict]:
    return [{"datei": i["datei"], "beschreibung": i["beschreibung"], "art": "text" if i["datei"].endswith(".txt") else "bild"}
            for i in _corpus()]


@app.get("/api/beispiele/{name}")
def beispiel(name: str) -> JSONResponse:
    item = next((i for i in _corpus() if i["datei"] == name), None)
    if item is None:
        raise HTTPException(404, "Unbekanntes Beispiel")
    p = CORPUS / name
    res = engine.check_text(p.read_text(encoding="utf-8")) if p.suffix == ".txt" else engine.check_file(p.read_bytes(), p.name)
    out = res.to_dict()
    out["beispiel"] = item
    if p.suffix == ".txt":
        out["beispiel"]["text"] = p.read_text(encoding="utf-8")
    return JSONResponse(out)


@app.get("/beispiel-datei/{name}")
def beispiel_datei(name: str) -> FileResponse:
    if name not in {i["datei"] for i in _corpus()}:
        raise HTTPException(404)
    return FileResponse(CORPUS / name)


@app.post("/api/demo/siegeln")
def demo_siegeln(text: str = Form(...), wer: str = Form("alice"), ki: int = Form(0)) -> dict:
    if os.environ.get("SATYA_DEMO_KEYS") != "1" or engine.ledger is None:
        raise HTTPException(403, "Demo-Siegel sind deaktiviert.")
    if wer not in DEMO_KEYS or ki not in (0, 1, 2):
        raise HTTPException(400, "Ungültige Parameter")
    sealed, seal = seal_text(text, DEMO_KEYS[wer], ki, engine.ledger.chain_id, engine.ledger.address)
    return {"text": sealed, "signer": seal.signer}


# --------------------------------------------------------------- Celo layer


def _require_celo() -> CeloLedger:
    if celo is None:
        raise HTTPException(503, "Celo-Register nicht konfiguriert (SATYA_CELO_ADDRESS fehlt).")
    return celo


@app.get("/api/celo/status")
def celo_status() -> dict:
    out: dict = {"celo": celo.status() if celo else None, "x402": None}
    if x402 is not None:
        out["x402"] = {
            "enabled": True,
            "price": f"{_x402_cfg.price_usdc} {_x402_cfg.asset_symbol}",
            "network": _x402_cfg.network["caip2"],
            "asset": _x402_cfg.asset["asset"],
            "payTo": _x402_cfg.pay_to,
            "facilitator": _x402_cfg.network["facilitator"],
            "settlement": _x402_cfg.resolved_settlement_mode,
            "ready": _x402_cfg.can_accept_paid_requests,
            "requiresAttribution": _x402_cfg.chain_id == 42220 and _x402_cfg.resolved_settlement_mode == "tagged-relayer",
            "attributionEvidence": (
                "erc8021-tag" if _x402_cfg.resolved_settlement_mode == "tagged-relayer"
                else "payto-wallet" if _x402_cfg.chain_id == 42220 else None
            ),
        }
    return out


@app.get("/api/celo/herkunft/{content_hash}")
def celo_herkunft(content_hash: str) -> dict:
    """Free read of the register. Charging applies to the full check, not to a lookup."""
    ledger = _require_celo()
    raw = content_hash[2:] if content_hash.startswith("0x") else content_hash
    try:
        digest = bytes.fromhex(raw)
    except ValueError:
        raise HTTPException(400, "contentHash muss hexadezimal sein.")
    if len(digest) != 32:
        raise HTTPException(400, "contentHash muss 32 Byte lang sein.")
    return {"contentHash": "0x" + digest.hex(), **ledger.lookup(digest)}


@app.get("/.well-known/agent.json")
def agent_json() -> dict:
    """ERC-8004 registration file so other agents can discover and price this service."""
    if x402 is None or celo is None:
        raise HTTPException(503, "Agentenbetrieb nicht konfiguriert.")
    agent_id = os.environ.get("SATYA_AGENT_ID")
    return agent_card(_x402_cfg, celo.config.address, int(agent_id) if agent_id else None)


@app.post("/api/x402/verify")
async def x402_verify(request: Request,
                      datei: UploadFile | None = File(None),
                      text: str | None = Form(None)) -> JSONResponse:
    """Provenance check an autonomous agent can buy per request.

    Without payment this answers 402 and describes the price. With a signed
    EIP-3009 authorisation in `X-PAYMENT` it verifies through the Celo
    facilitator, runs the check, settles, and returns the receipt.
    """
    if x402 is None:
        raise HTTPException(503, "x402 ist nicht konfiguriert (X402_PAY_TO fehlt).")

    header = request.headers.get("x-payment")
    resource = str(request.url.path)
    if not header:
        quote = _x402_cfg.payment_required(resource)
        quote["settlementReady"] = _x402_cfg.can_accept_paid_requests
        if not _x402_cfg.can_accept_paid_requests:
            quote["settlementNote"] = "Nur eine unverbindliche Quote: sichere Settlement-Konfiguration fehlt; keine Autorisierung senden."
        return JSONResponse(quote, status_code=402)
    if not _x402_cfg.can_accept_paid_requests:
        raise HTTPException(503, "x402-Zahlungen sind deaktiviert: sichere Settlement-Konfiguration fehlt.")
    if not ((datei is not None and datei.filename) or (text and text.strip())):
        raise HTTPException(400, "Bitte eine Datei oder einen Text übergeben.")

    try:
        payment = X402Gateway.decode_header(header)
        await x402.verify(payment, resource)
    except PaymentError as exc:
        return JSONResponse({**_x402_cfg.payment_required(resource), "error": exc.reason},
                            status_code=exc.status)

    # Paid: do the work.
    if datei is not None and datei.filename:
        data = await datei.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Datei größer als 50 MB")
        result = engine.check_file(data, datei.filename)
        digest = bytes.fromhex(sha256_bytes(data).removeprefix("0x"))
    elif text and text.strip():
        result = engine.check_text(text)
        digest = bytes.fromhex(text_hash(text).removeprefix("0x"))
    else:
        raise HTTPException(400, "Bitte eine Datei oder einen Text übergeben.")

    body: dict = {"contentHash": "0x" + digest.hex(), "pruefung": result.to_dict()}
    if celo is not None:
        try:
            body["celo"] = celo.lookup(digest)
        except Exception as exc:  # pragma: no cover - network dependent
            body["celo"] = {"error": str(exc)[:200]}

    try:
        settlement = await x402.settle(payment, resource)
    except PaymentError as exc:
        return JSONResponse({"error": exc.reason}, status_code=exc.status)

    if not x402.settlement_is_safe(settlement):
        return JSONResponse(
            {"error": "Zahlung wurde nicht vollständig bestätigt; das Prüfergebnis wird nicht ausgeliefert.",
             "zahlung": settlement},
            status_code=502,
        )

    body["zahlung"] = settlement
    return JSONResponse(body, headers={"X-PAYMENT-RESPONSE": X402Gateway.receipt_header(settlement)})

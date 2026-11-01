#!/usr/bin/env python3
"""An autonomous agent buying a provenance check from Satya over x402.

No account, no API key, no invoice. The agent calls the endpoint, is told the
price in a `402`, signs an EIP-3009 transfer authorisation for exactly that
amount, and retries. The service verifies the authorisation with the Celo
facilitator, does the work, settles on-chain, and returns a receipt.

    python3 demo/x402_client.py [--url http://localhost:8000] [--file path]
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import secrets
import sys
import time

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPLORER = "https://celo-sepolia.blockscout.com"


def load_buyer() -> Account:
    raw = json.loads((ROOT / ".secrets" / "buyer.json").read_text())
    d = raw["data"][0] if "data" in raw else (raw[0] if isinstance(raw, list) else raw)
    return Account.from_key(d["private_key"])


def sign_authorization(acct, requirement: dict, chain_id: int, version: int) -> dict:
    """Sign EIP-3009 `TransferWithAuthorization` for exactly the quoted price."""
    now = int(time.time())
    # The facilitator parses every numeric field of the authorisation as a
    # decimal string; the EIP-712 message itself still uses integers.
    auth = {
        "from": acct.address,
        "to": Web3.to_checksum_address(requirement["payTo"]),
        "value": str(int(requirement["maxAmountRequired"])),
        "validAfter": str(now - 60),
        "validBefore": str(now + int(requirement.get("maxTimeoutSeconds", 120)) + 60),
        "nonce": "0x" + secrets.token_bytes(32).hex(),
    }
    extra = requirement.get("extra", {})
    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": extra.get("name", "USDC"),
            "version": extra.get("version", "2"),
            "chainId": chain_id,
            "verifyingContract": Web3.to_checksum_address(requirement["asset"]),
        },
        "message": {
            **auth,
            "value": int(auth["value"]),
            "validAfter": int(auth["validAfter"]),
            "validBefore": int(auth["validBefore"]),
            "nonce": bytes.fromhex(auth["nonce"][2:]),
        },
    }
    signed = acct.sign_message(encode_typed_data(full_message=typed))
    return {
        "x402Version": version,
        "scheme": requirement["scheme"],
        "network": requirement["network"],
        "payload": {"signature": "0x" + signed.signature.hex().removeprefix("0x"),
                    "authorization": auth},
    }


def usdc_balance(rpc: str, token: str, who: str) -> int:
    w3 = Web3(Web3.HTTPProvider(rpc))
    abi = [{"inputs": [{"type": "address"}], "name": "balanceOf",
            "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}]
    c = w3.eth.contract(address=Web3.to_checksum_address(token), abi=abi)
    return c.functions.balanceOf(Web3.to_checksum_address(who)).call()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--file", default=str(ROOT / "demo/samples/ki_gpt_image.png"))
    ap.add_argument("--text", default=None)
    ap.add_argument("--rpc", default="https://forno.celo-sepolia.celo-testnet.org")
    args = ap.parse_args()

    acct = load_buyer()
    endpoint = f"{args.url.rstrip('/')}/api/x402/verify"
    print(f"agent wallet  {acct.address}")
    print(f"service       {endpoint}\n")

    def payload():
        if args.text:
            return None, {"text": args.text}
        p = pathlib.Path(args.file)
        return {"datei": (p.name, p.read_bytes(), "application/octet-stream")}, None

    files, data = payload()

    with httpx.Client(timeout=120) as client:
        # 1 ------------------------------------------------ ask without paying
        print("1) Calling the service with no payment")
        r = client.post(endpoint, files=files, data=data)
        if r.status_code != 402:
            sys.exit(f"   expected 402, got {r.status_code}: {r.text[:300]}")
        quote = r.json()
        req = quote["accepts"][0]
        version = int(quote.get("x402Version", 1))
        # v1 states the network by slug, v2 by CAIP-2 id; the EIP-712 domain
        # always needs the numeric chain id.
        net = req["network"]
        chain_id = (int(net.split(":")[1]) if ":" in net
                    else int(req.get("extra", {}).get("chainId", 11142220)))
        price = int(req["maxAmountRequired"]) / 10 ** req.get("extra", {}).get("decimals", 6)
        print(f"   402 Payment Required — {price} USDC on {net} (x402 v{version}, chain {chain_id})")
        print(f"   pay to {req['payTo']}  asset {req['asset']}")

        before = usdc_balance(args.rpc, req["asset"], acct.address)
        print(f"   agent balance before: {before / 1e6:.6f} USDC\n")

        # 2 ---------------------------------------------- sign and retry
        print("2) Signing an EIP-3009 authorisation and retrying")
        payment = sign_authorization(acct, req, chain_id, version)
        header = base64.b64encode(json.dumps(payment, separators=(",", ":")).encode()).decode()
        files, data = payload()
        r = client.post(endpoint, files=files, data=data, headers={"X-PAYMENT": header})
        if r.status_code != 200:
            sys.exit(f"   service returned {r.status_code}: {r.text[:400]}")
        body = r.json()
        print("   200 OK — the service answered\n")

        # 3 ------------------------------------------------------- result
        pruef = body.get("pruefung", {})
        print("3) What Satya says about the content")
        print(f"   contentHash {body.get('contentHash')}")
        print(f"   verdict     {pruef.get('urteil')}  (certain={pruef.get('sicher')})")
        print(f"   headline    {pruef.get('ueberschrift')}")
        for p in pruef.get("beweise", [])[:4]:
            print(f"     proof: {p.get('title')} — {p.get('detail')}")
        for h in pruef.get("indizien", [])[:3]:
            print(f"     hint:  {h.get('title')} — {h.get('detail')}")

        celo = body.get("celo") or {}
        if celo.get("statements"):
            print("\n   on-chain register:")
            for s in celo["statements"]:
                print(f"     {s['origin']} via {s['via']} by {s['attester']}"
                      f"{'  [revoked]' if s['revoked'] else ''}"
                      f"{'  [disputed]' if s['disputed'] else ''}")
            sm = celo["summary"]
            print(f"     summary: humanOnly={sm['humanOnly']} humanWithAi={sm['humanWithAi']} "
                  f"aiGenerated={sm['aiGenerated']} contradiction={sm['contradiction']}")

        # 4 ------------------------------------------------------ payment
        pay = body.get("zahlung", {})
        print(f"\n4) Payment: settled={pay.get('settled')} via={pay.get('via')}")
        if pay.get("transaction"):
            tx = pay["transaction"]
            tx = tx if tx.startswith("0x") else "0x" + tx
            print(f"   {EXPLORER}/tx/{tx}")
        if pay.get("note"):
            print(f"   {pay['note']}")

        after = usdc_balance(args.rpc, req["asset"], acct.address)
        print(f"   agent balance after:  {after / 1e6:.6f} USDC  "
              f"(paid {(before - after) / 1e6:.6f})")


if __name__ == "__main__":
    main()

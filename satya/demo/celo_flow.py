#!/usr/bin/env python3
"""Run the full Satya flow against the live Celo Sepolia deployment.

Registers an ERC-8004 agent identity for the demo generator, then declares a
genuinely AI-generated image on-chain and reads the register back.

    python3 demo/celo_flow.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

from eth_account import Account
from web3 import Web3
from web3.logs import DISCARD

ROOT = pathlib.Path(__file__).resolve().parent.parent
RPC = os.environ.get("CELO_RPC", "https://forno.celo-sepolia.celo-testnet.org")
CHAIN_ID = 11142220
SATYA = Web3.to_checksum_address("0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001")
ID_8004 = Web3.to_checksum_address("0x8004A818BFB912233c491871b3d84c89A494BD9e")
SELF_AGENTS = Web3.to_checksum_address("0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379")
EXPLORER = "https://celo-sepolia.blockscout.com"

ABI_8004 = [
    {"inputs": [{"type": "string", "name": "agentURI"}], "name": "register",
     "outputs": [{"type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"type": "uint256"}], "name": "getAgentWallet",
     "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"anonymous": False, "inputs": [
        {"indexed": True, "type": "uint256", "name": "agentId"},
        {"indexed": False, "type": "string", "name": "agentURI"},
        {"indexed": True, "type": "address", "name": "owner"}],
     "name": "Registered", "type": "event"},
]

ABI_SAT = [
    {"inputs": [{"type": "uint256", "name": "agentId"}, {"type": "bytes32", "name": "contentHash"},
                {"type": "bytes8", "name": "softHash"}],
     "name": "declareAsAgent8004", "outputs": [{"type": "uint256"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"type": "bytes32"}], "name": "summary", "outputs": [{"components": [
        {"type": "uint32", "name": "humanOnly"}, {"type": "uint32", "name": "humanWithAi"},
        {"type": "uint32", "name": "aiGenerated"}, {"type": "uint32", "name": "inactive"},
        {"type": "bool", "name": "contradiction"}, {"type": "bool", "name": "provenFraud"}],
        "type": "tuple"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "bytes32"}, {"type": "uint256"}], "name": "attestation", "outputs": [{"components": [
        {"type": "address", "name": "attester"}, {"type": "uint64", "name": "at"},
        {"type": "uint8", "name": "origin"}, {"type": "uint8", "name": "via_"},
        {"type": "bool", "name": "revoked"}, {"type": "bool", "name": "disputed"},
        {"type": "uint256", "name": "agentId"}, {"type": "uint256", "name": "nullifier"}],
        "type": "tuple"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "bytes32"}], "name": "count",
     "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "address"}], "name": "humanBehind",
     "outputs": [{"type": "bool"}, {"type": "uint256"}, {"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
]

ORIGIN = ["HUMAN_ONLY", "HUMAN_WITH_AI", "AI_GENERATED"]
VIA = ["SELF_HUMAN", "SELF_AGENT", "AGENT_8004"]


def load_account() -> Account:
    raw = json.loads((ROOT / ".secrets" / "deployer.json").read_text())
    key = raw["data"][0]["private_key"] if "data" in raw else raw["private_key"]
    return Account.from_key(key)


def send(w3: Web3, acct, fn, note: str):
    tx = fn.build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": CHAIN_ID,
        "gas": 600_000,
        "maxFeePerGas": w3.to_wei(120, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    status = "ok" if rcpt.status == 1 else "FAILED"
    print(f"  {note}: {status}  gas={rcpt.gasUsed}")
    print(f"    {EXPLORER}/tx/0x{h.hex().removeprefix('0x')}")
    if rcpt.status != 1:
        sys.exit(f"transaction reverted: {note}")
    return rcpt


def main() -> None:
    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = load_account()
    print(f"network   Celo Sepolia ({w3.eth.chain_id})")
    print(f"account   {acct.address}")
    print(f"balance   {w3.from_wei(w3.eth.get_balance(acct.address), 'ether'):.4f} CELO\n")

    sat = w3.eth.contract(address=SATYA, abi=ABI_SAT)
    reg = w3.eth.contract(address=ID_8004, abi=ABI_8004)

    state_path = ROOT / "demo" / "celo_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    # 1 ----------------------------------------------- ERC-8004 agent identity
    agent_id = state.get("agentId")
    if agent_id and reg.functions.getAgentWallet(agent_id).call() == acct.address:
        print(f"1) ERC-8004 agent #{agent_id} already registered to this wallet\n")
    else:
        print("1) Registering an ERC-8004 agent identity for the demo generator")
        agent_uri = state.get("agentURI", "https://satya.example/.well-known/agent.json")
        rcpt = send(w3, acct, reg.functions.register(agent_uri), "register()")
        logs = reg.events.Registered().process_receipt(rcpt, errors=DISCARD)
        agent_id = logs[0]["args"]["agentId"] if logs else None
        if agent_id is None:
            sys.exit("could not read agentId from the Registered event")
        state["agentId"] = agent_id
        state["agentURI"] = agent_uri
        print(f"   agentId = {agent_id}")
        print(f"   wallet  = {reg.functions.getAgentWallet(agent_id).call()}\n")

    # 2 ------------------------------------------- declare a real AI output
    image = ROOT / "demo" / "samples" / "ki_gpt_image.png"
    digest = hashlib.sha256(image.read_bytes()).digest()
    print(f"2) Declaring a genuinely AI-generated image as AI_GENERATED")
    print(f"   file        {image.relative_to(ROOT)}")
    print(f"   contentHash 0x{digest.hex()}")

    if sat.functions.count(digest).call() == 0:
        send(w3, acct, sat.functions.declareAsAgent8004(agent_id, digest, b"\x00" * 8),
             "declareAsAgent8004()")
    else:
        print("   already on record, skipping the write")

    # 3 ------------------------------------------------------- read it back
    print("\n3) Reading the register back")
    n = sat.functions.count(digest).call()
    for i in range(n):
        a = sat.functions.attestation(digest, i).call()
        print(f"   [{i}] attester={a[0]} origin={ORIGIN[a[2]]} via={VIA[a[3]]} "
              f"agentId={a[6]} nullifier={a[7]}")
    s = sat.functions.summary(digest).call()
    print(f"   summary: humanOnly={s[0]} humanWithAi={s[1]} aiGenerated={s[2]} "
          f"inactive={s[3]} contradiction={s[4]} provenFraud={s[5]}")

    # 4 ---------------------------------- live Self Agent ID sybil evidence
    print("\n4) Sybil evidence read live from Self Agent ID on Celo Sepolia")
    # Wallets whose Self Agent ID nullifiers are compared: set SATYA_SYBIL_OWNERS="0xA,0xB"
    owners = [o.strip() for o in os.environ.get("SATYA_SYBIL_OWNERS", "").split(",") if o.strip()]
    seen: dict[int, list[str]] = {}
    for o in owners:
        is_human, aid, nullifier = sat.functions.humanBehind(Web3.to_checksum_address(o)).call()
        print(f"   {o}  human={is_human} agentId={aid} nullifier={nullifier}")
        if nullifier:
            seen.setdefault(nullifier, []).append(o)
    for nullifier, wallets in seen.items():
        if len(wallets) > 1:
            print(f"   -> {len(wallets)} distinct wallets resolve to ONE human "
                  f"({str(nullifier)[:12]}...): in Satya they share a single voice.")

    state["contentHash"] = "0x" + digest.hex()
    state["satya"] = SATYA
    state["selfAgents"] = SELF_AGENTS
    state["identityRegistry8004"] = ID_8004
    state["chainId"] = CHAIN_ID
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(f"\nstate written to {state_path.relative_to(ROOT)}")
    print(f"contract: {EXPLORER}/address/{SATYA}")


if __name__ == "__main__":
    main()

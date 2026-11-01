"""Read the Satya provenance register deployed on Celo.

Thin, dependency-light reader used by the verification service: given a content
hash it returns every statement on record, who stands behind it, and whether the
register itself has already proven a contradiction.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from web3 import Web3

ORIGIN = ("HUMAN_ONLY", "HUMAN_WITH_AI", "AI_GENERATED")
VIA = ("SELF_HUMAN", "SELF_AGENT", "AGENT_8004")

EXPLORERS = {
    42220: "https://celoscan.io",
    11142220: "https://celo-sepolia.blockscout.com",
}

ABI: list[dict[str, Any]] = [
    {"inputs": [{"type": "bytes32"}], "name": "count",
     "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "bytes32"}], "name": "attestations", "outputs": [{"components": [
        {"type": "address", "name": "attester"}, {"type": "uint64", "name": "at"},
        {"type": "uint8", "name": "origin"}, {"type": "uint8", "name": "via_"},
        {"type": "bool", "name": "revoked"}, {"type": "bool", "name": "disputed"},
        {"type": "uint256", "name": "agentId"}, {"type": "uint256", "name": "nullifier"}],
        "type": "tuple[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "bytes32"}], "name": "summary", "outputs": [{"components": [
        {"type": "uint32", "name": "humanOnly"}, {"type": "uint32", "name": "humanWithAi"},
        {"type": "uint32", "name": "aiGenerated"}, {"type": "uint32", "name": "inactive"},
        {"type": "bool", "name": "contradiction"}, {"type": "bool", "name": "provenFraud"}],
        "type": "tuple"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "address"}], "name": "humanBehind",
     "outputs": [{"type": "bool"}, {"type": "uint256"}, {"type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "selfAgents",
     "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "agents8004",
     "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
]


@dataclass(frozen=True)
class CeloLedgerConfig:
    rpc: str
    address: str
    chain_id: int

    @classmethod
    def from_env(cls) -> "CeloLedgerConfig | None":
        address = os.environ.get("SATYA_CELO_ADDRESS")
        if not address:
            return None
        chain_id = int(os.environ.get("CELO_CHAIN_ID", "11142220"))
        default_rpc = ("https://forno.celo.org" if chain_id == 42220
                       else "https://forno.celo-sepolia.celo-testnet.org")
        return cls(rpc=os.environ.get("CELO_RPC", default_rpc),
                   address=Web3.to_checksum_address(address), chain_id=chain_id)


class CeloLedger:
    """Read-only view of SatyaCelo."""

    def __init__(self, config: CeloLedgerConfig):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc, request_kwargs={"timeout": 20}))
        self.contract = self.w3.eth.contract(address=config.address, abi=ABI)

    # ------------------------------------------------------------- queries

    def lookup(self, content_hash: bytes) -> dict[str, Any]:
        """Every statement on record for this content, plus the aggregate."""
        rows = self.contract.functions.attestations(content_hash).call()
        s = self.contract.functions.summary(content_hash).call()
        statements = [{
            "attester": r[0],
            "at": r[1],
            "origin": ORIGIN[r[2]],
            "via": VIA[r[3]],
            "revoked": r[4],
            "disputed": r[5],
            "agentId": r[6],
            # The nullifier is a pseudonym, never an identity. Expose a short,
            # stable prefix so clients can group statements by person without
            # publishing the full value.
            "human": f"human:{r[7]:x}"[:20] if r[7] else None,
            "active": not (r[4] or r[5]),
        } for r in rows]
        return {
            "statements": statements,
            "summary": {
                "humanOnly": s[0], "humanWithAi": s[1], "aiGenerated": s[2],
                "inactive": s[3], "contradiction": s[4], "provenFraud": s[5],
            },
            "distinctHumans": len({r[7] for r in rows if r[7]}),
        }

    def human_behind(self, address: str) -> dict[str, Any]:
        is_human, agent_id, nullifier = self.contract.functions.humanBehind(
            Web3.to_checksum_address(address)).call()
        return {
            "address": address,
            "isHuman": is_human,
            "agentId": agent_id,
            "human": f"human:{nullifier:x}"[:20] if nullifier else None,
        }

    def status(self) -> dict[str, Any]:
        explorer = EXPLORERS.get(self.config.chain_id, "")
        out = {
            "chainId": self.config.chain_id,
            "address": self.config.address,
            "explorer": f"{explorer}/address/{self.config.address}" if explorer else None,
            "connected": False,
        }
        try:
            out["connected"] = self.w3.eth.chain_id == self.config.chain_id
            out["block"] = self.w3.eth.block_number
            out["selfAgentId"] = self.contract.functions.selfAgents().call()
            out["identityRegistry8004"] = self.contract.functions.agents8004().call()
        except Exception as exc:  # pragma: no cover - network dependent
            out["error"] = str(exc)[:200]
        return out

"""Satya seals: EIP-712 signed statements "I, holder of this wallet, made this content
<without AI | with AI assistance | AI-generated>".

A seal alone proves only that a key signed the statement. It becomes PROOF only once the
registry confirms that the signer holds a valid HMN human credential (Layer 1), or once the
seal is anchored on-chain (the registry checked the credential at anchoring time).

Text seals are embedded as a block at the end of the text and survive copy & paste:

    -----BEGIN SATYA-SIEGEL-----
    <base64url(JSON)>
    -----END SATYA-SIEGEL-----
"""

from __future__ import annotations

import base64
import json
import textwrap
import time
from dataclasses import asdict, dataclass

from eth_account import Account
from eth_account.messages import encode_typed_data

from .hashing import SEAL_BEGIN, SEAL_END, normalize_text, strip_seal, text_hash

AI_USE_DE = {0: "ohne KI erstellt", 1: "mit KI-Unterstützung erstellt", 2: "KI-generiert"}

SEAL_TYPES = {
    "Seal": [
        {"name": "contentHash", "type": "bytes32"},
        {"name": "aiUse", "type": "uint8"},
        {"name": "createdAt", "type": "uint64"},
        {"name": "signer", "type": "address"},
    ]
}


def eip712_domain(chain_id: int, registry: str) -> dict:
    return {"name": "Satya", "version": "1", "chainId": chain_id, "verifyingContract": registry}


@dataclass
class Seal:
    hash: str  # 0x-prefixed SHA-256 (bytes32)
    aiUse: int
    createdAt: int
    signer: str
    chainId: int
    registry: str
    sig: str
    v: int = 1

    def message(self) -> dict:
        return {"contentHash": bytes.fromhex(self.hash[2:]), "aiUse": self.aiUse,
                "createdAt": self.createdAt, "signer": self.signer}

    def encode(self) -> str:
        raw = json.dumps(asdict(self), separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @classmethod
    def decode(cls, body: str) -> "Seal":
        pad = "=" * (-len(body) % 4)
        d = json.loads(base64.urlsafe_b64decode(body + pad))
        return cls(**d)

    def as_tuple(self) -> tuple:
        return (bytes.fromhex(self.hash[2:]), self.aiUse, self.createdAt, self.signer)


def sign_seal(private_key: str, content_hash: str, ai_use: int, chain_id: int, registry: str,
              created_at: int | None = None) -> Seal:
    if ai_use not in AI_USE_DE:
        raise ValueError("aiUse muss 0, 1 oder 2 sein")
    acct = Account.from_key(private_key)
    seal = Seal(hash=content_hash, aiUse=ai_use, createdAt=created_at or int(time.time()) - 5,
                signer=acct.address, chainId=chain_id, registry=registry, sig="")
    signed = Account.sign_typed_data(private_key, eip712_domain(chain_id, registry), SEAL_TYPES, seal.message())
    seal.sig = "0x" + signed.signature.hex().removeprefix("0x")
    return seal


def recover_signer(seal: Seal) -> str | None:
    """Offline recovery for EOAs (smart accounts need the on-chain ERC-1271 check)."""
    try:
        msg = encode_typed_data(eip712_domain(seal.chainId, seal.registry), SEAL_TYPES, seal.message())
        return Account.recover_message(msg, signature=bytes.fromhex(seal.sig[2:]))
    except Exception:
        return None


def seal_block(seal: Seal) -> str:
    return SEAL_BEGIN + "\n" + "\n".join(textwrap.wrap(seal.encode(), 64)) + "\n" + SEAL_END


def seal_text(text: str, private_key: str, ai_use: int, chain_id: int, registry: str) -> tuple[str, Seal]:
    clean, _ = strip_seal(text)
    seal = sign_seal(private_key, text_hash(clean), ai_use, chain_id, registry)
    return normalize_text(clean) + "\n\n" + seal_block(seal) + "\n", seal


def extract_seal(text: str) -> tuple[str, Seal | None, str | None]:
    """Return (text_without_seal, seal, error)."""
    clean, body = strip_seal(text)
    if body is None:
        return text, None, None
    try:
        return clean, Seal.decode(body), None
    except Exception as e:  # noqa: BLE001
        return clean, None, f"Siegel nicht lesbar: {e}"

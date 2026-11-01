"""Public Anvil development keys, derived at runtime - for the LOCAL DEMO CHAIN ONLY.

These are the well-known accounts of the public test mnemonic that Anvil/Hardhat use by
default. Anyone can compute them, so they must NEVER hold real funds, never be used on Celo
mainnet and never identify a real person. The module derives them (BIP-39 / BIP-32, path
m/44'/60'/0'/0/i) instead of storing private-key literals in the source.
"""

from __future__ import annotations

import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric import ec

ANVIL_MNEMONIC = "test test test test test test test test test test test junk"

_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_HARD = 2**31


def _compressed_pub(k: int) -> bytes:
    p = ec.derive_private_key(k, ec.SECP256K1()).public_key().public_numbers()
    return (b"\x02" if p.y % 2 == 0 else b"\x03") + p.x.to_bytes(32, "big")


def _child(k: int, c: bytes, i: int) -> tuple[int, bytes]:
    data = (b"\x00" + k.to_bytes(32, "big") if i >= _HARD else _compressed_pub(k)) + i.to_bytes(4, "big")
    h = hmac.new(c, data, hashlib.sha512).digest()
    return (int.from_bytes(h[:32], "big") + k) % _N, h[32:]


def anvil_key(index: int) -> str:
    """Private key (0x-hex) of Anvil default account `index`. Demo chain only."""
    if not 0 <= index < 10:
        raise ValueError("Anvil default accounts are 0..9")
    seed = hashlib.pbkdf2_hmac("sha512", ANVIL_MNEMONIC.encode(), b"mnemonic", 2048)
    h = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    k, c = int.from_bytes(h[:32], "big"), h[32:]
    for i in (44 + _HARD, 60 + _HARD, _HARD, 0, index):
        k, c = _child(k, c, i)
    return "0x" + k.to_bytes(32, "big").hex()

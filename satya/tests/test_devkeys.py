"""The derived demo keys must match the public Anvil defaults (addresses are well known)."""

import hashlib

import pytest

from satya.devkeys import anvil_key


def _address(priv_hex: str) -> str:
    from cryptography.hazmat.primitives.asymmetric import ec

    p = ec.derive_private_key(int(priv_hex, 16), ec.SECP256K1()).public_key().public_numbers()
    pub = p.x.to_bytes(32, "big") + p.y.to_bytes(32, "big")
    try:
        from Crypto.Hash import keccak  # pycryptodome (installed with eth-account)

        return "0x" + keccak.new(digest_bits=256, data=pub).hexdigest()[-40:]
    except ImportError:  # pragma: no cover
        pytest.skip("keccak not available")


@pytest.mark.parametrize(
    "index,address",
    [
        (0, "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"),
        (1, "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"),
        (2, "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc"),
        (3, "0x90f79bf6eb2c4f870365e785982e1f101e93b906"),
    ],
)
def test_anvil_default_addresses(index, address):
    assert _address(anvil_key(index)) == address


def test_distinct_and_valid():
    keys = [anvil_key(i) for i in range(6)]
    assert len(set(keys)) == 6
    assert all(len(k) == 66 and k.startswith("0x") for k in keys)
    with pytest.raises(ValueError):
        anvil_key(10)

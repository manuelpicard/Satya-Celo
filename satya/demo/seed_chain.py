"""Deploy Layer 1 (HMN HumanCredential) and Layer 2 (SatyaRegistry) to a local anvil chain
and create the demo identities.

Identities (anvil default dev keys - public, demo only):
  governance  acct 0  owner of both contracts, also relayer that pays gas for seals
  issuer      acct 1  HMN issuer (e.g. eID-NFC + ZK in production)
  alice       acct 2  verified human, honest
  mallory     acct 3  verified human, will lie ("written without AI" for AI text)
  agent       acct 4  AI agent, NO human credential
  provider    acct 5  registered AI provider "Demo-KI-Anbieter"
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from satya.devkeys import anvil_key  # noqa: E402  public Anvil dev keys, local demo chain only
RPC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8545"
KEYS = {  # public Anvil default accounts 0..5, derived at runtime
    "governance": anvil_key(0),
    "issuer": anvil_key(1),
    "alice": anvil_key(2),
    "mallory": anvil_key(3),
    "agent": anvil_key(4),
    "provider": anvil_key(5),
}

w3 = Web3(Web3.HTTPProvider(RPC))
ACC = {k: Account.from_key(v) for k, v in KEYS.items()}


def artifact(path: Path) -> tuple[list, str]:
    d = json.loads(path.read_text())
    return d["abi"], d["bytecode"]["object"]


def send(acct, fn_or_tx, value: int = 0):
    tx = fn_or_tx.build_transaction({"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
                                     "chainId": w3.eth.chain_id, "value": value})
    rc = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction))
    if rc["status"] != 1:
        raise RuntimeError(f"Transaktion fehlgeschlagen: {fn_or_tx}")
    return rc


def deploy(acct, abi, bytecode, *args):
    c = w3.eth.contract(abi=abi, bytecode=bytecode)
    rc = send(acct, c.constructor(*args))
    return w3.eth.contract(address=rc["contractAddress"], abi=abi)


def verify_human(hmn, who: str, person_seed: str, level: int = 2) -> None:
    holder = ACC[who].address
    att = (holder, Web3.keccak(text=person_seed), level, int(time.time()) + 180 * 86400, False,
           hmn.functions.nonces(holder).call(), int(time.time()) + 3600)
    digest = hmn.functions.hashAttestation(att).call()
    sig = Account.unsafe_sign_hash(digest, KEYS["issuer"]).signature
    send(ACC[who], hmn.functions.claim(att, ACC["issuer"].address, sig))


def main() -> None:
    hmn_abi, hmn_bin = artifact(ROOT.parent / "human-token/out/HumanCredential.sol/HumanCredential.json")
    reg_abi, reg_bin = artifact(ROOT / "contracts/out/SatyaRegistry.sol/SatyaRegistry.json")
    gov = ACC["governance"]
    hmn = deploy(gov, hmn_abi, hmn_bin, gov.address)
    reg = deploy(gov, reg_abi, reg_bin, hmn.address, gov.address)
    send(gov, hmn.functions.setIssuer(ACC["issuer"].address, True, 2, "DEMO eID-NFC-ZK"))
    send(gov, reg.functions.setProvider(ACC["provider"].address, True, "Demo-KI-Anbieter"))
    verify_human(hmn, "alice", "demo-person-alice")
    verify_human(hmn, "mallory", "demo-person-mallory")
    dep = {"rpc": RPC, "chainId": w3.eth.chain_id, "hmn": hmn.address, "registry": reg.address,
           "accounts": {k: a.address for k, a in ACC.items()}}
    (ROOT / "demo/deployment.json").write_text(json.dumps(dep, indent=2))
    print(json.dumps(dep, indent=2))
    print("alice isHuman:", hmn.functions.isHuman(ACC["alice"].address).call(),
          "| agent isHuman:", hmn.functions.isHuman(ACC["agent"].address).call())


if __name__ == "__main__":
    main()

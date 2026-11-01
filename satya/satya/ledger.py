"""Connection to the SatyaRegistry contract (Layer 2) and, through it, to HMN (Layer 1)."""

from __future__ import annotations

import json
from pathlib import Path

from .hashing import hamming
from .model import Direction, Evidence, Tier
from .seal import AI_USE_DE, Seal, recover_signer

ABI_DIR = Path(__file__).parent / "abi"
KIND_HUMAN, KIND_AI = 0, 1


def _short(x: str, n: int = 10) -> str:
    return x[:n] + "…" if x and len(x) > n else x


class Ledger:
    def __init__(self, rpc_url: str, registry_address: str, abi_file: str | None = None):
        from web3 import Web3

        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        abi = json.loads(Path(abi_file or ABI_DIR / "SatyaRegistry.json").read_text())
        abi = abi["abi"] if isinstance(abi, dict) else abi
        self.address = Web3.to_checksum_address(registry_address)
        self.c = self.w3.eth.contract(address=self.address, abi=abi)
        self.chain_id = self.w3.eth.chain_id
        self._provider_names: dict[str, str] = {}

    # ------------------------------------------------------------- helpers
    def info(self) -> dict:
        return {"rpc_verbunden": self.w3.is_connected(), "chain_id": self.chain_id, "register": self.address,
                "hmn": self.c.functions.hmn().call(), "block": self.w3.eth.block_number}

    def provider_name(self, addr: str) -> str:
        if addr not in self._provider_names:
            active, name = self.c.functions.provider(addr).call()
            self._provider_names[addr] = name or addr
        return self._provider_names[addr]

    # ------------------------------------------------------------- lookups
    def lookup(self, content_hash: str) -> list[Evidence]:
        h = bytes.fromhex(content_hash[2:])
        items = self.c.functions.attestations(h).call()
        out: list[Evidence] = []
        for i, a in enumerate(items):
            attester, anchored_at, kind, ai_use, level, revoked, fraud, person_id = a
            pid = "0x" + person_id.hex()
            valid = self.c.functions.isValid(h, i).call()
            data = {"index": i, "wallet": attester, "verankert_unix": anchored_at, "art": "mensch" if kind == KIND_HUMAN else "ki-anbieter",
                    "aiUse": ai_use, "hmn_level": level, "personId": pid if kind == KIND_HUMAN else None}
            if kind == KIND_AI:
                who = f"KI-Anbieter „{self.provider_name(attester)}“"
            else:
                who = f"HMN-Person {_short(pid)} (Level {level}, Wallet {_short(attester)})"
            if not valid:
                reason = "widerrufen" if revoked else "als Betrug markiert" if fraud else \
                         "Person gesperrt" if kind == KIND_HUMAN else "Anbieter deaktiviert"
                out.append(Evidence("register", Tier.INFO, Direction.NEUTRAL, f"Ungültige Erklärung im Register ({reason})",
                                    f"{who} hatte eine Erklärung abgegeben, die nicht mehr zählt: {reason}.",
                                    issuer=who, data=data))
                continue
            if kind == KIND_AI:
                out.append(Evidence("register", Tier.PROOF, Direction.AI, "Register: KI-Anbieter hat diesen Inhalt registriert",
                                    f"{who} hat genau diesen Inhalt (identischer SHA-256) als eigene KI-Ausgabe registriert.",
                                    issuer=who, data=data))
            elif ai_use == 0:
                out.append(Evidence("register", Tier.PROOF, Direction.HUMAN, "Register: verifizierter Mensch bezeugt „ohne KI“",
                                    f"{who} hat haftbar erklärt, diesen Inhalt {AI_USE_DE[0]} zu haben. Das Credential "
                                    "war beim Verankern gültig.", issuer=who, data=data))
            else:
                out.append(Evidence("register", Tier.PROOF, Direction.AI, f"Register: verifizierter Mensch erklärt „{AI_USE_DE[ai_use]}“",
                                    f"{who} hat haftbar erklärt, dieser Inhalt sei {AI_USE_DE[ai_use]}.",
                                    issuer=who, data=data))
        return out

    def similar(self, soft_hash: str | None, exclude_hash: str, max_distance: int = 6) -> list[Evidence]:
        if not soft_hash:
            return []
        out: list[Evidence] = []
        logs = list(self.c.events.HumanAttested.get_logs(from_block=0)) + list(self.c.events.AiAttested.get_logs(from_block=0))
        seen = set()
        for lg in logs:
            args = lg["args"]
            ch = "0x" + args["contentHash"].hex()
            sh = "0x" + args["softHash"].hex()
            if ch == exclude_hash or int(sh, 16) == 0 or ch in seen:
                continue
            d = hamming(sh, soft_hash)
            if d <= max_distance:
                seen.add(ch)
                is_ai = lg["event"] == "AiAttested" or args.get("aiUse", 0) != 0
                out.append(Evidence("aehnlichkeit", Tier.HINT, Direction.AI if is_ai else Direction.HUMAN,
                                    "Ähnlicher Inhalt im Register",
                                    f"Ein Inhalt mit sehr ähnlichem Fingerabdruck (Abstand {d}/64 Bit) wurde als "
                                    f"{'KI-Inhalt' if is_ai else 'menschlich, ohne KI'} registriert. Ähnlichkeit ist kein "
                                    "Beweis: Es kann sich um eine Bearbeitung, einen Screenshot oder einen Zufall handeln.",
                                    data={"contentHash": ch, "abstand": d}))
        return out

    def verify_seal(self, seal: Seal) -> dict:
        valid_sig, human, level, person_id = self.c.functions.verifySeal(seal.as_tuple(), bytes.fromhex(seal.sig[2:])).call()
        return {"signatur_gueltig": valid_sig, "mensch": human, "level": level, "personId": "0x" + person_id.hex()}


def seal_evidence(seal: Seal, current_hash: str, ledger: Ledger | None) -> list[Evidence]:
    """Evaluate an embedded/sidecar seal against the current content."""
    signer = seal.signer
    if seal.hash.lower() != current_hash.lower():
        return [Evidence("siegel", Tier.PROOF, Direction.BROKEN, "Inhalt wurde nach dem Versiegeln verändert",
                         "Das Siegel bezieht sich auf einen anderen Inhalt (SHA-256 stimmt nicht). Die Erklärung gilt "
                         "für diesen Inhalt nicht.", issuer=f"Wallet {_short(signer)}",
                         data={"siegel_hash": seal.hash, "aktueller_hash": current_hash})]
    what = AI_USE_DE.get(seal.aiUse, "?")
    direction = Direction.HUMAN if seal.aiUse == 0 else Direction.AI
    data = {"signer": signer, "aiUse": seal.aiUse, "createdAt": seal.createdAt, "chainId": seal.chainId, "registry": seal.registry}

    if ledger is None or ledger.chain_id != seal.chainId or ledger.address.lower() != seal.registry.lower():
        rec = recover_signer(seal)
        ok = rec is not None and rec.lower() == signer.lower()
        return [Evidence("siegel", Tier.HINT, direction if ok else Direction.NEUTRAL,
                         "Siegel gefunden, Menschen-Status nicht prüfbar" if ok else "Siegel-Signatur ungültig",
                         (f"Die Signatur von Wallet {_short(signer)} ist gültig („{what}“), aber das zugehörige Register "
                          "ist nicht verbunden. Ob der Signierer ein verifizierter Mensch ist, kann nicht geprüft werden.")
                         if ok else "Die Signatur passt nicht zur angegebenen Wallet: Das Siegel ist gefälscht oder beschädigt.",
                         issuer=f"Wallet {_short(signer)}", data=data)]

    r = ledger.verify_seal(seal)
    data.update(r)
    if not r["signatur_gueltig"]:
        return [Evidence("siegel", Tier.HINT, Direction.NEUTRAL, "Siegel-Signatur ungültig",
                         "Die Signatur passt nicht zur angegebenen Wallet: Das Siegel ist gefälscht oder beschädigt.",
                         issuer=f"Wallet {_short(signer)}", data=data)]
    if not r["mensch"]:
        return [Evidence("siegel", Tier.HINT, direction, "Signiert, aber nicht von einem verifizierten Menschen",
                         f"Wallet {_short(signer)} hat „{what}“ signiert, besitzt aber kein gültiges HMN-Credential. "
                         "Das kann ein KI-Agent, ein Bot oder ein abgelaufenes Credential sein, daher nur ein Indiz.",
                         issuer=f"Wallet {_short(signer)}", data=data)]
    who = f"HMN-Person {_short(r['personId'])} (Level {r['level']}, Wallet {_short(signer)})"
    return [Evidence("siegel", Tier.PROOF, direction, f"Siegel eines verifizierten Menschen: „{what}“",
                     f"{who} hat mit gültigem HMN-Credential signiert, diesen Inhalt {what} zu haben.",
                     issuer=who, data=data)]

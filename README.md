# Satya

**Verifiable provenance for digital content on Celo — and an honest "undetermined" when nothing can be proven.**
*(Deutsch: siehe unten.)*

*satya* (सत्य) is Sanskrit for "truth". Satya does **not** claim to detect AI. It answers a narrower question: *what can be cryptographically proven about where this content came from?*

> **Status (1 Nov 2026):** hackathon prototype for [Agents on Open Rails](https://www.loops.house/agents-on-open-rails). The registry runs on **Celo Sepolia (testnet)**. There is **no Celo mainnet deployment yet**, and the x402 / ERC-8021 mainnet path is not production-ready. Tests have not yet been re-run on the latest commit (see "Verification status").

## How a verdict works

A verdict is **certain** only if a proof from an identifiable, accountable party was verified. Hints never change a verdict. If no proof exists, the answer is `UNBESTIMMT` (undetermined) — missing metadata or a missing registry entry never proves human authorship.

| Verdict | Certain | Basis |
|---|---|---|
| `KI_NACHGEWIESEN` | yes | C2PA signature from a trusted AI provider, a registered AI-provider entry, or an honest "made with AI" seal |
| `MENSCH_BEZEUGT` | yes | Seal/registry entry of a verified human (Self Agent ID / HMN credential) |
| `KAMERA_NACHGEWIESEN` | yes | C2PA signature from a trusted capture device |
| `WIDERSPRUCH` | no | Valid proofs contradict each other |
| `HERKUNFT_GEBROCHEN` | no | Content changed after it was signed |
| `UNBESTIMMT` | no | No verifiable proof |

The verdict function (`satya/satya/verdict.py`) is pure and deterministic.

## Known limits — please read

- **A proof shows who made a statement, not that it is true.** In our own 22-case demo corpus, the case "Mallory lies" (a verified human falsely declares AI text as human-made) produced one *certain but wrong* verdict in the first evaluation run (8 of 9 certain verdicts correct). That is the designed limit, not a bug: false statements are attributable and sanctionable, but not impossible. A later run reports 9/9, but in that run the lying signer is no longer treated as a verified human, so it does not demonstrate a fix. See `satya/demo/auswertung.json` (phases 1 and 2).
- The corpus is small and internal; it is **not** evidence of general accuracy.
- A proof-of-personhood alone does not prove that a person created a specific file.
- On-chain identifiers (Self nullifier, HMN person id) are publicly readable. There is no anonymity guarantee; review linkability before any mainnet use.
- Demo keys are the **public Anvil development accounts**, derived at runtime in `satya/satya/devkeys.py`. Never use them with real funds or on mainnet.

## What is in this repository

```
satya/          Python engine + FastAPI service (verdict logic, C2PA check, seals, x402 gateway, demo corpus, tests)
satya-agent/    Next.js dApp (hash in browser, read registry, wallet actions) + Solidity contracts (Foundry)
  contracts/      SatyaCelo.sol (ownerless provenance registry, Self + ERC-8004), SatyaRegistry.sol (legacy),
                  SatyaHumanSBT.sol (ERC-5192 soulbound human credential, not deployed)
```

- **Provenance on Celo:** statements by a Self-verified human, a Self agent, or an ERC-8004 agent are bound to a content hash. ERC-8004 agents can only declare `AI_GENERATED`.
- **x402:** a paid verification endpoint (`POST /api/x402/verify`); the buyer signs an EIP-3009 authorization after seeing amount, asset, network and recipient. Wallet actions always stay with the user.
- **Testnet deployment (Celo Sepolia):** `SatyaCelo` `0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001`; ERC-8004 agent id 453. Testnet tokens have no value.

## Run it locally (demo)

```bash
# Python service (needs a local demo chain for the demo register)
pip install -r satya/requirements.txt
cd satya && SATYA_DEMO_KEYS=1 ./demo/serve.sh 8000   # X402_PAY_TO must be set to your own address

# dApp
cd satya-agent && npm install && npm run build && npm run start
```

Contracts: `cd satya-agent/contracts && git submodule update --init --recursive && forge test` (dependencies are pinned in `.gitmodules`).

## Verification status

- Last known: TypeScript check and Next.js production build passed; earlier states reported 60/60 Foundry and 20/20 Python tests.
- **Not yet re-verified on the latest commit:** Python tests (a dependency install was blocked in the authoring environment) and Foundry tests. A pure-logic property check of the verdict function (20,000 random evidence sets) found no violation of the core guarantee; this does not replace the test suite.
- No mainnet payment, signature or deployment has been made from this repository.

---

## Deutsch

Satya ist ein Celo-System für **nachvollziehbare Herkunft** digitaler Inhalte — kein universeller KI-Detektor. Ein Urteil gilt nur dann als **sicher**, wenn ein kryptografischer Nachweis einer haftbaren Stelle geprüft wurde; sonst lautet es ehrlich **unbestimmt**. Ein Nachweis belegt, *wer* etwas erklärt, nicht, dass es wahr ist.

Stand: Prototyp auf **Celo Sepolia (Testnet)**, noch kein Mainnet-Deployment. Bekannte Grenzen (insbesondere der Fall „Mallory lügt“), die Teststatus-Einschränkungen und die Bedeutung der Demo-Schlüssel stehen oben. Das ausführliche Konzept: [`satya/docs/Satya-Konzept.md`](satya/docs/Satya-Konzept.md), Celo-Details: [`satya/docs/Satya-Celo.md`](satya/docs/Satya-Celo.md).

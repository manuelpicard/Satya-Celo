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

## Hackathon eligibility — please read

Satya was not started from zero during the event. The first prototype (Python engine, `SatyaRegistry` / `SatyaCelo` on Celo Sepolia, a Sepolia x402 flow and a 22-case test corpus) is documented in the project's own notes dated **5 October 2026**, one day before the kickoff on 6 October. The event rules say that code is written during the hackathon. Whether this project qualifies has **not been confirmed with the organizers**, and we do not claim that it does (see [`satya-agent/docs/HACKATHON_READINESS_2026-10-26.md`](satya-agent/docs/HACKATHON_READINESS_2026-10-26.md)).

Not mentioned in the three documents dated 5 October (`satya/docs/celo-stand.md`, `Satya-Konzept.md`, `Satya-Celo.md`) and added afterwards: the ERC-5192 soulbound credential (`SatyaHumanSBT`), the wallet and x402-quote flow of the Next.js dApp, the ERC-8021 attribution module and mainnet settlement guard (`satya/satya/attribution.py`, `x402.py`), and — added on 1–2 November 2026 and visible in this repository's commit history — the runtime derivation of demo keys, the removal of the untagged-mainnet override, and the spend policy / receipt ledger for "Build with buy" (`satya/satya/purchases.py`, `satya/docs/build-with-buy.md`).

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

## Run it (not re-tested on the latest commit)

Prerequisites: Python 3.11+, Node 20+, and optionally [Foundry](https://book.getfoundry.sh/).

```bash
# Python service: read-only against the live Celo Sepolia register
pip install -r satya/requirements.txt
cd satya && X402_PAY_TO=<your own payout address> ./demo/serve.sh 8000

# dApp
cd satya-agent && npm install && npm run build && npm run start

# Contracts (libraries are vendored in contracts/lib: OpenZeppelin v5.7.0, forge-std v1.17.0)
cd satya-agent/contracts && forge test
```

Notes:
- `demo/serve.sh` also wires the legacy local demo register if `demo/deployment.json` exists. That part needs a local Anvil chain and the separate `human-token` repository (not included here); the Celo Sepolia path does not.
- The private demo CA keys (`satya/demo/pki/*.key`) are not part of this repository. Regenerate them locally with `python3 demo/make_demo_ca.py`. `.secrets/` and `*.key` are git-ignored; never commit generated keys.

## Verification status

- Last known: TypeScript check and Next.js production build passed; earlier states reported 60/60 Foundry and 20/20 Python tests.
- **Not yet re-verified on the latest commit:** Python tests (a dependency install was blocked in the authoring environment) and Foundry tests. A pure-logic property check of the verdict function (20,000 random evidence sets) found no violation of the core guarantee; this does not replace the test suite.
- `tests/test_x402_policy.py` and `tests/test_purchases.py` (22 tests) were run locally with stubbed third-party imports; the rest of the suite still needs a normal environment.
- No mainnet payment, signature or deployment has been made from this repository.

---

## Deutsch

Satya ist ein Celo-System für **nachvollziehbare Herkunft** digitaler Inhalte — kein universeller KI-Detektor. Ein Urteil gilt nur dann als **sicher**, wenn ein kryptografischer Nachweis einer haftbaren Stelle geprüft wurde; sonst lautet es ehrlich **unbestimmt**. Ein Nachweis belegt, *wer* etwas erklärt, nicht, dass es wahr ist.

Stand: Prototyp auf **Celo Sepolia (Testnet)**, noch kein Mainnet-Deployment. Bekannte Grenzen (insbesondere der Fall „Mallory lügt“), die Teststatus-Einschränkungen und die Bedeutung der Demo-Schlüssel stehen oben. Das ausführliche Konzept: [`satya/docs/Satya-Konzept.md`](satya/docs/Satya-Konzept.md), Celo-Details: [`satya/docs/Satya-Celo.md`](satya/docs/Satya-Celo.md).

**Teilnahmeberechtigung:** Der erste Prototyp ist in den Projektnotizen auf den 5. Oktober 2026 datiert, einen Tag vor dem Kick-off. Ob das nach der Regel „Code wird während des Hackathons geschrieben“ zählt, ist mit den Veranstaltern **nicht geklärt**; wir behaupten es nicht. Was nachweislich später dazukam, steht im Abschnitt „Hackathon eligibility“.

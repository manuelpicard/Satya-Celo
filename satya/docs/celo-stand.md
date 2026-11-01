# Satya auf Celo – Arbeitsstand

Stand: 5. Okt 2026. Hackathon „Agents on Open Rails" (Celo), Kick-off 6. Okt 12:00 GMT.

Das Projekt hieß bis zum 5. Oktober *Satyagiri* und heißt jetzt **Satya**. Python-Paket,
Verträge, Umgebungsvariablen (`SATYA_*`) und EIP-712-Domänen tragen den neuen Namen.
Der Vertrag wurde als `SatyaCelo` neu deployt und verifiziert; der alte Vertrag
`0x10Eb7811B477304999933544d1eBC0592D5E3B17` ist obsolet. Weil sich die EIP-712-Domäne
von „Satyagiri" auf „Satya" geändert hat, wurden lokale Chain und Testkorpus neu gebaut.

## Live-Deployment (Celo Sepolia, Chain-ID 11142220)

| Was | Adresse / Wert |
|---|---|
| **SatyaCelo** (verifiziert) | `0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001` |
| Explorer | https://celo-sepolia.blockscout.com/address/0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001 |
| Self Agent ID (upstream) | `0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379` |
| ERC-8004 Identity (upstream) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| USDC (x402-Asset) | `0x01C5C0122039549AD1493B8220cABEdD739BC44E` |
| x402-Facilitator | https://api.x402.sepolia.celo.org |
| Facilitator-Signer | `0x0d74D5Cefd2e7F24E623330ebE3d8D4cB45fFB48` |
| RPC | https://forno.celo-sepolia.celo-testnet.org |

Mainnet-Gegenstücke: Self Agent ID `0xaC3DF9ABf80d0F5c020C06B04Cced27763355944`, ERC-8004 `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, USDC `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`, Facilitator https://api.x402.celo.org.

## Konten (Schlüssel in `.secrets/`, nicht im Repo)
- Deployer / Dienst-Empfänger: (Adresse nicht veröffentlicht) (1 CELO vom Celo-Faucet)
- Agent-Käufer (zahlt per x402): `0x13F4DC3a205102343949579Ec3c01b4F3416e663` (20 USDC vom Circle-Faucet)

## Transaktionen
| Aktion | Tx | Gas |
|---|---|---|
| ERC-8004 `register()` → agentId **453** | `0xd21fa7687f2ea52eae81e17960ce62144ce96d3cf91dc61b10c40dde97c6fd26` | 177 792 |
| Deployment `SatyaCelo` | `0xd64811c255849ad90fa323a72ea1ea3755f668a7dcbcc3210c3bc97f1d572655` | – |
| `declareAsAgent8004()` KI-Bild | `0x77cc7734337f34d7bb6d9739f6e09c6e5164e6fa4f887442d0d96030fedddfa8` | 129 331 |
| x402-Zahlung (0,01 USDC) | `0xc3f8a7eebc67969f51e6c8b43e329b8e91fa3e118413fc8b4ea76d8b65c8e16b` | – |

Gegen den alten Vertrag (noch unter dem Namen Satyagiri): `0x180d8abd…` (declare),
`0x708e915f…` und `0x869e843f…` (x402-Zahlungen). Dienen nur noch als Beleg, dass der
Ablauf mehrfach reproduzierbar war.

Deklarierter Inhalt: `demo/samples/ki_gpt_image.png`, contentHash `0xd7c2d77c62016c1038466eb73df60ae1a01ba8ba2755510bdcbedbeb1dab2364` (echtes gpt-image-2.5-Bild).
Byte-gleich mit `demo/corpus/01_bild_ki_openai_original.png`, daher zeigt Fall 01 im
Testkorpus sowohl den C2PA-Beweis als auch den Celo-Registereintrag.

## x402: das Format, das wirklich funktioniert

Der Celo-Facilitator listet unter `/supported` v1 **und** v2, verifiziert aber nur v1:

- `network` muss der Slug sein (`celo-sepolia`), **nicht** `eip155:11142220`
- `paymentPayload.x402Version` muss `1` sein
- **alle Zahlenfelder der Autorisierung müssen Strings sein** (`"value": "10000"`,
  `validAfter`, `validBefore`); mit Integern antwortet er `invalid_format`
- jede v2-Variante wird mit `unsupported_scheme` abgelehnt

Dokumentiert in `satya/x402.py`, über `X402_VERSION` umschaltbar.

**Abrechnung:** `/settle` verlangt einen Dashboard-API-Schlüssel, der eine Wallet-Signatur
im Browser braucht. Der Dienst nutzt deshalb den direkten EIP-3009-Pfad: er reicht die
signierte Autorisierung des Käufers selbst bei USDC ein und zahlt das Gas
(`X402_SETTLE_KEY`). Mit `X402_API_KEY` schaltet er automatisch auf den Facilitator um.

## Messergebnis auf dem 22-Fälle-Korpus

| | Satya | naiver Detektor |
|---|---|---|
| Aussagen | 9 (41 %) | 16 |
| davon falsch | 1 | 5 |
| falsche KI-Beschuldigung | 0 | 3 |

Der eine Fehler ist Fall 22 (Mallory, verifiziert, konsistente Lüge). Nach Aufdeckung
des Widerspruchs sinkt er auf 0 – das ist der Celo-Beitrag.

## Live-Sybil-Beweis (echte Daten auf Celo Sepolia)
Drei Self-Agent-IDs, zwei verschiedene Wallets, **ein einziger Mensch**:

| Self agentId | Besitzer-Wallet | Nullifier |
|---|---|---|
| 1 | (Wallet nicht veröffentlicht) | (Nullifier nicht veröffentlicht) |
| 2 | (Wallet nicht veröffentlicht) | derselbe |
| 3 | (Wallet nicht veröffentlicht) | derselbe |

`sameHuman(1,2) = true`. In einem naiven Register hätte diese Person drei Stimmen; bei Satya hat sie genau eine.

## Code (neu für den Hackathon)
- `contracts/src/SatyaCelo.sol` – ownerless, Self-Agent-ID-gebunden, permissionlose Betrugsaufdeckung
- `contracts/src/interfaces/ISelfAgentRegistry.sol`, `IIdentityRegistry8004.sol`
- `contracts/test/SatyaCelo.t.sol` + `test/mocks/Mocks.sol` – 29 Tests, alle grün (46 im Repo gesamt)
- `contracts/script/DeployCelo.s.sol`
- `satya/x402.py` – x402-Bezahlschicht (v1, siehe oben), Verify über Celo-Facilitator, Settlement über Facilitator **oder** direkt per EIP-3009
- `satya/celo_ledger.py` – Leser für das On-Chain-Register
- `satya/server.py` – neue Routen `/api/celo/status`, `/api/celo/herkunft/{hash}`, `/api/x402/verify`, `/.well-known/agent.json`
- `demo/celo_flow.py` – End-to-End-Ablauf gegen die Live-Chain

## Dienst-Start

Bevorzugt über das Startskript, das Celo **und** das lokale Demo-Register für den
Testkorpus verbindet (lokale Anvil-Chain muss laufen):

```bash
./demo/serve.sh 8000
```
Öffentlich: https://8000-ik0hj4pg1fxauwdkyapdp-ca9f6603.sg2.manus.computer

## Offen
- **Umbenennung abgeschlossen**: alle 47 Dateien, Vertrag neu deployt und verifiziert,
  66 Tests grün, x402-Ablauf gegen den neuen Vertrag bestätigt
- **Registrierung beim Hackathon** (Luma: https://lu.ma/uk27jw1q) – erfordert Nutzerfreigabe,
  da ein öffentlicher Tweet Teil der Einreichung ist
- Öffentliches Git-Repository als Link für die Jury
- Demo-Video / Pitch
- `proveSelfContradiction` live: nur mit zwei echten Self-Agenten desselben Menschen
  vorführbar (Self-App mit echtem Ausweis). In den Foundry-Tests mit Mocks abgedeckt.
- Mainnet-Deployment (bewusst nicht erfolgt; Testnetz genügt für die Einreichung)

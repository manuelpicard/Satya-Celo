# Satya auf Celo – Hackathon „Agents on Open Rails"

## Hackathon
- Veranstalter: Celo / CeloDevs. Name: **Agents on Open Rails**.
- Kick-off: 6. Okt 2026, 12:00 GMT (lu.ma/uk27jw1q, YouTube ik4_h2hhDME). Banner docs.celo.org.
- Preise: $5.000 über drei Tracks + Mentoring + 3 Monate Chainstack Growth für ausgewählte Projekte.
- Tracks (Celo-Tweet 2105674393632579808): Stable Agents: LatAm (mit Ripio) · Stable Agents: Open Corridors · Build with `buy` (Celo x402-Marktplatz).
- Kick-off deckt ab: Ripio-Lokalwährungs-Stablecoins, Textile FX, USA₮ über Celo x402-Facilitator, `buy` (Agent-Service-Marktplatz).
- Registrierung über „Loops House". Frühere Celo-Hackathons: `npx skills add https://celobuilders.xyz`.
- Regeln früherer Celo-Hackathons: öffentliches GitHub-Repo, Mainnet zählt (Testnet nicht), unabhängige Gegenparteien, Code während des Hackathons geschrieben (bestehende Projekte dürfen mit neuer Arbeit antreten, Commit-Historie wird geprüft).

## Celo-Netzwerke
| | Mainnet | Sepolia-Testnet |
|---|---|---|
| Chain ID | 42220 | 11142220 |
| RPC | https://forno.celo.org | https://forno.celo-sepolia.celo-testnet.org |
| Explorer | celoscan.io | celo-sepolia.blockscout.com |
| Faucet | – | https://faucet.celo.org/celo-sepolia |

Alfajores (44787) ist stillgelegt.

## Bausteine
### Self Agent ID (= Layer 1 auf Celo, ersetzt eigenen HMN-Issuer)
Soulbound ERC-721, bindet Agenten-Schlüssel an ZK-Pass-Nullifier eines Menschen. Implementiert alle drei ERC-8004-Rollen plus `registerWithHumanProof()`, `revokeHumanProof()`, Nullifier-Sybil-Erkennung. Provider-agnostisch über `IHumanProofProvider`.

| Contract | Mainnet 42220 | Sepolia 11142220 |
|---|---|---|
| SelfAgentRegistry (Identity + proof-of-human) | 0xaC3DF9ABf80d0F5c020C06B04Cced27763355944 | 0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379 |
| SelfReputationRegistry | 0x69Da18CF4Ac27121FD99cEB06e38c3DC78F363f4 | (Self-Doku) |
| SelfValidationRegistry | 0x71a025e0e338EAbcB45154F8b8CA50b41e7A0577 | (Self-Doku) |
| Celo Agent Visa | 0xCa97f7586CF9De62B8ca516d7Ee25f6AEae5e109 | 0xf049FD6260Fce964B82728A86CF1BbEB8AB3E875 |

Agent-Aufrufe tragen `x-self-agent-address`, `x-self-agent-signature`, `x-self-agent-timestamp`. Verifier-Defaults: Sybil-Limit 1, Replay-Schutz, 300 s Zeitfenster. SDKs: `@selfxyz/agent-sdk` (TS), `selfxyz-agent-sdk` (Python), `self-agent-sdk` (Rust). Auf Sepolia akzeptiert die Self-App Mock-Dokumente.

### Self Protocol für Menschen (Build with Self)
`@selfxyz/contracts`, Contract erbt `SelfVerificationRoot`, Hub V2: Mainnet 0xe57F4773bd9c9d8b6Cd70431117d353298B9f5BF, Testnet 0x68c931C9a534D37aa78094877F46fE46a49F1A51. Config-ID über tools.self.xyz.

### ERC-8004 (Referenz-Deployment, separat von Self)
| Contract | Mainnet | Sepolia |
|---|---|---|
| Identity Registry | 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 | 0x8004A818BFB912233c491871b3d84c89A494BD9e |
| Reputation Registry | 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63 | 0x8004B663056A597Dffe9eCcC1965A193B7388713 |

Identity = ERC-721, `register()` setzt `agentWallet = msg.sender`, `agentURI` zeigt auf Registrierungsdatei. Reputation: `giveFeedback`, `readAllFeedback`, `getSummary`; Eigentümer/Operatoren dürfen nicht selbst bewerten.

### Verifizierte On-Chain-Schnittstellen

**SelfAgentRegistry** (aus `@selfxyz/agent-sdk/dist/constants.js`, Proxy ERC-1967, Impl Sepolia `0x6802a22e396743dedbf30f9289e7ff4c65fdc68a`):
```
getAgentId(bytes32 agentPubKey) view returns (uint256)
isVerifiedAgent(bytes32 agentPubKey) view returns (bool)
hasHumanProof(uint256 agentId) view returns (bool)
getHumanNullifier(uint256 agentId) view returns (uint256)
isProofFresh(uint256 agentId) view returns (bool)
proofExpiresAt(uint256 agentId) view returns (uint256)
getAgentsForNullifier(uint256 nullifier) view returns (uint256[])
getAgentCountForHuman(uint256 nullifier) view returns (uint256)
sameHuman(uint256 a, uint256 b) view returns (bool)
getAgentCredentials(uint256 agentId) view returns ((string,string[],string,string,string,string,string,uint256,bool[3]))
ownerOf(uint256) view returns (address) · verificationStrength() view returns (uint8)
agentRegisteredAt(uint256) view returns (uint256) · agentNonces(address) view returns (uint256)
```
`agentPubKey` ist die Agentenadresse linksgepaddet auf 32 Byte: `zeroPadValue(address, 32)` = `bytes32(uint256(uint160(addr)))` (SelfAgentVerifier.js:352).

**ERC-8004 IdentityRegistry** (erc-8004/erc-8004-contracts):
```
register() / register(string agentURI) / register(string, MetadataEntry[]) returns (uint256 agentId)
getAgentWallet(uint256 agentId) view returns (address)   // aus Metadata-Key "agentWallet"
ownerOf(uint256 agentId) view returns (address)          // ERC-721
isAuthorizedOrOwner(address spender, uint256 agentId) view returns (bool)
getMetadata(uint256 agentId, string key) view returns (bytes)
setAgentURI / setAgentWallet / unsetAgentWallet
```
Es gibt **keine** On-Chain-Rückwärtszuordnung Wallet → agentId. Aufrufer muss die `agentId` mitgeben; der Contract prüft `getAgentWallet(agentId) == msg.sender`. Transfer des NFT löscht `agentWallet`.

### x402 auf Celo
- Facilitator-API: `https://api.x402.celo.org` (Mainnet), `https://api.x402.sepolia.celo.org` (Sepolia). Dashboard x402.celo.org ist NICHT die API.
- Endpunkte `/verify`, `/supported` frei; `/settle` braucht API-Key (`X402_API_KEY`), per Wallet-Signatur im Dashboard erstellt.
- USDC/USDT über EIP-3009 `transferWithAuthorization`, Facilitator zahlt Gas, verwahrt keine Mittel.
- Middleware `@x402/express`, `@x402/hono` (v2).
- Fee Abstraction: Gas in Stablecoins über `feeCurrency` (CIP-64), bei USDC/USDT Adapter-Adresse verwenden.
- Attribution Tags: ERC-8021, `@celo/attribution-tags`.

## Plan: was für den Hackathon neu gebaut wird
Satya (Prüfschicht für Inhaltsherkunft) wird zur **Herkunftsschicht der Agenten-Ökonomie auf Celo**:

1. `IHumanSource`-Abstraktion im Registry: Adapter für **Self Agent ID** (Nullifier als `personId`) neben dem bestehenden HMN-Adapter.
2. **ERC-8004-Agenten als KI-Deklaranten**: statt kuratierter Anbieterliste darf jede in der Identity Registry registrierte Agent-Wallet ihre eigenen Ausgaben als KI deklarieren – permissionless und mit Reputation.
3. **x402-bezahlter Prüfdienst**: `POST /verify` kostet eine Mikrozahlung in USDC über den Celo-Facilitator. Passt auf Track „Build with `buy`".
4. **Agent-Authentifizierung** über Self-Agent-ID-Header.
5. Deployment auf Celo Sepolia, später Mainnet.

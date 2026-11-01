# Satya Human Credential (Soulbound)

Dieser Foundry-Ordner enthält Satya's optionales **nicht übertragbares Menschen-Credential**. Der Contract `src/credentials/SatyaHumanSBT.sol` implementiert ERC-721 plus [ERC-5192](https://eips.ethereum.org/EIPS/eip-5192) und bindet genau ein Credential an den stabilen Self-Human-Nullifier.

> Das Credential besagt ausschließlich, dass die aktuelle Self-Prüfung für die gebundene Person gültig ist. Es beweist **nicht**, dass ein Inhalt von einem Menschen geschrieben, aufgenommen oder erstellt wurde, und ist kein KI-Detektor.

## Verhalten

- `claim(agentId)`: Der Aufrufer muss Eigentümer einer Self Agent ID sein; Self muss einen vorhandenen, frischen Menschenbeweis, einen nichtleeren Nullifier und ein gültiges Ablaufdatum melden.
- Pro Self-Nullifier kann nur ein Credential existieren. Weitere Self Agent IDs derselben Person aktualisieren das bestehende Credential statt ein zweites zu minten.
- Übertragungen und Freigaben (`transferFrom`, `safeTransferFrom`, `approve`, `setApprovalForAll`) sind gesperrt. `locked(tokenId)` ist immer `true`; der Contract meldet `IERC5192` über `supportsInterface`.
- `isHuman(wallet)` ist nur dann `true`, wenn das Self-Credential noch frisch und nicht abgelaufen ist und die Wallet weiterhin Eigentümerin der gebundenen Agent-ID ist.
- Wallet-Wiederherstellung ist ein eigener Schritt: Dieselbe Person muss mit frischem Self-Beweis eine Agent-ID unter der neuen Wallet kontrollieren und `recover(agentId)` ausführen. Dabei wird der alte Token verbrannt und ein neuer ausgegeben.
- Die holderseitige Funktion `renounce()` verbrennt den aktuellen Token. Ein späterer Claim erfordert wieder einen frischen Self-Beweis.
- Es gibt keinen Admin, zentralen Issuer oder Upgrade-Pfad.

## Ordnerstruktur

```text
contracts/
├── README.md
├── foundry.toml
├── script/DeploySatyaHumanSBT.s.sol
├── lib/ (versionierte Foundry/OpenZeppelin-Submodule aus dem Repo-Root)
├── src/
│   ├── credentials/SatyaHumanSBT.sol
│   └── interfaces/{IERC5192,ISelfAgentRegistry}.sol
└── test/
    ├── credentials/SatyaHumanSBT.t.sol
    └── mocks/Mocks.sol
```

## Lokal testen

Nach einem Clone ohne `--recurse-submodules` zunächst aus dem Repository-Root:

```bash
git submodule update --init --recursive
cd contracts
forge test
```

OpenZeppelin Contracts (`v5.7.0`) und `forge-std` (`v1.17.0`) sind als Submodule auf konkrete Commits gepinnt. Die Contract-Tests decken Claim, Aktualisierung, EIP-5192-Sperre, fehlgeschlagene Übertragung/Freigabe, Ablauf, Relink, einmalige Ausgabe, Recovery und Burn ab.

## Deployment-Status

Das Skript `script/DeploySatyaHumanSBT.s.sol` ist absichtlich **nur für Celo Sepolia** freigeschaltet (Chain ID `11142220`) und bricht auf Mainnet oder anderen Chains ab. Es wurde in dieser Umsetzung **nicht ausgeführt**; es gibt daher noch keine SBT-Contract-Adresse. Für einen späteren Testnet-Deploy sind ein separat bestätigter Wallet-Account und Test-CELO nötig. Mainnet-Deployment ist nicht vorbereitet.

## Datenschutz- und Vertrauenshinweise

- Die EVM-Adresse, Agent-ID und Transaktionen sind öffentlich.
- Self-Nullifier sind pseudonym und können innerhalb des Self-Systems wiedererkannt/verknüpft werden; dieses Credential bietet keine Anonymitätsgarantie. Keine Pass- oder Ausweisdaten werden im Token-Metadatum gespeichert.
- Satya vertraut für Einzigartigkeit, Frische und Ablauf des Identitätsbeweises dem fest verdrahteten Self-Agent-Registry-Contract auf der gewählten Chain.
- Der Code ist ein Hackathon-Prototyp und wurde nicht extern auditiert. Vor einem produktiven oder Mainnet-Einsatz sind unabhängiger Contract- und Datenschutz-Review erforderlich.

# Satya – Übergabe und verbleibende Schritte

## In diesem Durchlauf erledigt
- [x] EIP-1193-Wallet kann auf Celo Sepolia wechseln; Self Agent ID wird nach Eigentum, Self-Menschenbeweis und Aktualität geprüft.
- [x] Eine `declareAsHuman`-Erklärung ist nur nach erfüllten Self-Bedingungen verfügbar und wird ausschließlich durch eine ausdrückliche Wallet-Transaktion des Nutzers gesendet.
- [x] x402-UI fragt Preis/Asset/Netzwerk/Empfänger zunächst ohne Inhaltsübermittlung ab; eine getrennte Wallet-Autorisierung ist nötig, bevor der ausgewählte Inhalt an den Backenddienst geschickt wird.
- [x] Das Frontend verarbeitet und zeigt die x402-Antwort, Settlement-Information und — wenn geliefert — einen Blockscout-Tx-Link.
- [x] Echte Browseraufnahme des Interfaces mit Celo-Sepolia-Registerbefund und unverbindlicher Testnet-Quote aufgenommen; MP4, Untertitel, Poster und Rohaufnahme liegen unter `demo-video/`.
- [x] Reproduzierbares Renderer-Skript, README und Demo-Abhängigkeiten hinzugefügt.
- [x] TypeScript-Prüfung und Next.js-Produktionsbuild erfolgreich.
- [x] Foundry-Verträge in einen GitHub-fähigen `contracts/`-Ordner in dieser Git-Arbeitskopie aufgenommen; der frühere Pfad `/home/ubuntu/satya/contracts` bleibt als Symlink verwendbar.
- [x] Self-verifiziertes Soulbound-Credential (`SatyaHumanSBT`, ERC-5192) mit Claim, Ablaufprüfung, expliziter Recovery und Renounce implementiert; **60/60 Foundry-Tests** bestehen.
- [x] OpenZeppelin Contracts `v5.7.0` und `forge-std` `v1.17.0` als gepinnte Git-Submodule; der Solidity-Build benötigt kein lokales `human-token`-Nachbarrepo mehr.
- [x] Foundry nach `forge clean` vollständig frisch gebaut: **60/60 Tests** bestanden. Separates Python-Testpaket: **20/20 Tests** bestanden.
- [x] x402-Backendstatus geprüft: Port 8000 war zunächst frei. Ein temporärer lokaler Starttest funktionierte, aber `/api/celo/status` meldete `celo: null` und `x402: null` (keine Konfiguration); der Prozess wurde wieder beendet.
- [x] Offizielle Loops-House-Frist geprüft: Anmeldung und Einreichung bis **9. November 2026, 09:00 GMT**, Gewinnerbekanntgabe am 13. November.
- [x] Hackathon-Anforderungen und Satya-Lücken in [`docs/HACKATHON_READINESS.md`](docs/HACKATHON_READINESS.md) dokumentiert.
- [x] Lokaler Git-Commit erstellt; das quellcodebereinigte Übergabe-ZIP `satya-agent-celo.zip` wurde erstellt und geprüft.

## Offen / Freigabe erforderlich
- [ ] **x402 ist lokal nicht einsatzbereit:** Kein Dienst läuft dauerhaft und es fehlt die X402-/Celo-Konfiguration. Live-Preisabfrage im Browser braucht den Backenddienst; der gespeicherte Videoclip zeigt eine zuvor erfolgreiche 0,01-Test-USDC-Quote. Es wurde keine Zahlung signiert oder ausgelöst.
- [ ] Der neue `SatyaHumanSBT` ist noch nicht deployed und hat deshalb keine Frontend-Integration/Mint-Schaltfläche. Das Deployment-Skript ist ausschließlich für Celo Sepolia.
- [ ] Öffentliche GitHub-Veröffentlichung bzw. Push: kein Remote-Ziel konfiguriert; für die Hackathon-Anmeldung ist ein öffentlich erreichbares Repo erforderlich.
- [ ] Hackathon-Readiness: Mainnet-Aktivität, Attribution Tag in jeder Transaktion und Verknüpfung der Agent-Wallet/ERC-8004-Identität mit dem Event-Eintrag fehlen noch. Bestehende Satya-Codebasis und Track-Fit vor Anmeldung mit dem Veranstalter abstimmen.
- [ ] Öffentliches Video-Posting und Hackathon-Registrierung/Einreichung: nicht ausgeführt.
- [ ] Für reale Self-Wallet-Interaktion benötigt der Nutzer seine eigene Wallet und Self Agent ID; es wurden keine persönlichen Zugangsdaten verwendet.

## Grenzen / Sicherheitsregeln
- Kein privater Schlüssel in App, lokalem Git, ZIP oder Video.
- Keine Zahlung, Wallet-Signatur, On-chain-Transaktion, Hackathon-Registrierung oder öffentliche Veröffentlichung durch diesen Durchlauf ausgelöst.
- Der Prototyp kann Aussagen und Signaturen zu einem Content-Hash prüfen; er kann nicht todsicher bestimmen, ob beliebiger Inhalt von KI stammt.
- Test-USDC/CELO auf Celo Sepolia haben keinen Mainnet-Wert.


## Hackathon-Finish (26.10.2026) — neue Arbeitspakete

- [ ] **Attribution vor jeder Satya-kontrollierten Wallet-Transaktion:** Verwende den exakten Loops/ERC-8021-App-Code; wenn er fehlt oder ungültig ist, wird vor Signatur/Broadcast abgebrochen. x402-Settlement bekommt einen Schema-2-Rollen-Suffix nur über einen konfigurierten Relayer und nur nach validierter App-ID.
- [ ] **USA₮-x402 ohne versehentliche Echtgeldausgabe:** Quote zeigt Chain, Token, Betrag, Empfänger und Rückabwicklungshinweis; Support ist auf die erlaubten Chain-/Asset-Paare begrenzt; der Inhalt verlässt den Browser erst nach ausdrücklicher EIP-3009-Walletsignatur. Mainnet bleibt ohne vollständige sichere Konfiguration deaktiviert.
- [ ] **Paid result nur gegen bestätigte Zahlung:** Verifiziere Signatur/Anforderungen, Settlement-Receipt und erwarteten Transfer; bei unbestätigtem oder fehlgeschlagenem Settlement wird kein Prüfergebnis ausgeliefert. Ungetaggte Mainnet-Settlement-Pfade werden nicht stillschweigend benutzt.
- [ ] **Privacy-sichere V2 als separate Contract-Generation:** kein Self-Agent-ID-Link und kein globaler Self-Nullifier im V2-Storage oder -Event; Self-Hub-Proof erhält einen Satya-eigenen Scope, während Content-Bindung, Replay-Schutz, Accountability und sichere Verdict-Regeln erhalten bleiben. Bestehender v1 wird als unveränderlicher Legacy-Stand ausgewiesen.
- [ ] **ERC-8004-Agentenkarte korrekt und auffindbar:** Chain-spezifische Registry-Adresse, Agent-ID, Satya-V2-Contract, tatsächliches Asset/Preis und klare Trust-/Verdict-Grenzen müssen zusammenpassen.
- [ ] **Jury-taugliches Paket:** README, Submission-Text und Demo nennen exakt, was kryptografisch bewiesen wird, was unbestimmt bleibt, welche Transaktion prüfbar ist und welche Teile noch vom Veranstalter/Walletinhaber abhängen. Keine erfundenen Nutzer, Aktivität oder Settlements.

Details und Stop-Grenzen: [`plan.md`](plan.md) sowie [`docs/HACKATHON_READINESS_2026-10-26.md`](docs/HACKATHON_READINESS_2026-10-26.md).


Sicherheitsbasis ist aktualisiert: Next.js 15.5.28 und PostCSS 8.5.31; `npm audit` meldet null Advisories im Lockfile-Diagramm zum 26.10.2026. Die Build-/TypeScript-Prüfung und tatsächliche UI-Integration des Loops-App-Codes stehen noch aus. Einzelheiten: [`docs/SECURITY_BASELINE_2026-10-26.md`](docs/SECURITY_BASELINE_2026-10-26.md).
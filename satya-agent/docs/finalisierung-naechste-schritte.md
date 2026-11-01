# Satya – Übersicht der nächsten Schritte zur Finalisierung

**Stand: 7. Oktober 2026.** Diese Übersicht trennt nachweislich Erledigtes von noch ungeprüften oder freigabepflichtigen Schritten. Ziel ist zunächst eine **saubere Celo-Sepolia-Hackathon-Einreichung**, nicht ein Mainnet-Produkt.

## Kurzfassung

Satya hat bereits einen verifizierten Contract auf Celo Sepolia, eine funktionierende Frontend-Demo, eine Wallet-/Self-Integration, einen x402-UI-Prototyp und ein kurzes Demo-Video. Die Solidity-Suite besteht mit **46 Tests**; der Frontend-TypeScript-Check und `next build` waren erfolgreich.

Die wichtigsten offenen Punkte sind **(1) Anmelde- und Abgabefrist beim Hackathon bestätigen, (2) den Backenddienst für die x402-UI wieder sicher bereitstellen, (3) Wallet- und bezahlten Testnet-Ablauf mit echten Testkonten Ende zu Ende prüfen und (4) eine stabile Demo-URL und das öffentliche Repository klären**. Der aktuelle x402-Backenddienst ist nicht aktiv. Das Video zeigt daher eine zuvor aufgezeichnete Testnet-Quote, keine aktuell live abrufbare Quote.

## Statusübersicht

| Bereich | Stand | Bedeutung |
|---|---|---|
| Celo-Contract | `SatyaCelo` ist auf Celo Sepolia deployed und verifiziert | Für eine Testnet-Demo vorhanden; kein Mainnet-Deployment |
| Smart-Contract-Tests | 46 Foundry-Tests bestanden, zuletzt geprüft am 7. Oktober | Ersetzt kein unabhängiges Audit |
| Frontend | Next.js-Build und TypeScript-Check erfolgreich; Demo-Seite und Live-Registerabfrage antworteten zuletzt mit HTTP 200 | Preview-URL ist temporär, keine dauerhafte Hosting-Zusage |
| Self/Wallet | Prüf- und nutzerbestätigter `declareAsHuman`-Flow implementiert | Noch mit einer realen Wallet und frischer Self Agent ID praktisch abnehmen |
| x402 | Quote-/EIP-3009-UI und sicherer 503-Fallback implementiert; eine frühere separate Backend-Demo hatte eine Celo-Sepolia-Testzahlung | Der Backenddienst läuft derzeit nicht; der aktuelle Browserflow ist dadurch nicht live Ende zu Ende verifiziert |
| Demo-Material | MP4 (16,6 s), SRT, Poster und Aufnahmeskripte erstellt | Clip zeigt eine echte UI-Aufnahme, aber die Quote ist ein aufgezeichneter Testnet-Zustand |
| Lokale Übergabe | Lokales Git-Repository, Commit `5c551ab`, ZIP ohne lokale Schlüsseldateien | Noch kein Satya-Remote oder öffentlicher Push |
| Hackathon | Kick-off war am 6. Oktober; Teilnahme/Einreichung nicht vorgenommen | Frist und genaues Einreichungsformat beim offiziellen Portal sofort prüfen |
| KI-Erkennung | Produktgrenze in UI und README klargestellt | Satya prüft signierte Herkunftsaussagen; es kann nicht beweisen, ob beliebiger Inhalt von KI stammt |

## Priorisierte Schritte

### P0 – Hackathon-Fenster und Einreichungsregeln verifizieren

**Warum zuerst:** Die offizielle Celo-Ankündigung sagt, dass „Agents on Open Rails“ am 6. Oktober startet und verweist für die Anmeldung auf Loops House. Die von uns geprüfte Kick-off-Eventseite nennt selbst keine Schlussfrist. Deshalb darf keine Frist angenommen werden.

1. Beim offiziellen Loops-House-/Hackathon-Portal prüfen: Anmeldestatus, Abgabefrist mit Zeitzone, erlaubte Vorarbeit, Team-/Teilnahmebedingungen und verpflichtende Artefakte.
2. Den **konkreten Track/Preis** auswählen. Satya sollte nicht gleichzeitig als beliebiger Proof-of-Personhood-, Content-Forensics- und Payments-Prototyp eingereicht werden; den stärksten belegbaren Celo-Nutzen und die Anforderungen des ausgewählten Tracks in einem Satz zuspitzen.
3. Falls Frist oder Teilnahmeberechtigung unklar ist, Celo/Loops House fragen, bevor öffentliche Einreichungsangaben gemacht werden.

**Ergebnis:** dokumentierte Deadline, Track, Einreichungslink, benötigte Felder und zulässige Demoform.

### P1 – x402-Backend sicher aktivieren und Verbindung stabilisieren

1. Backend-Hosting und URL festlegen; die aktuelle Next.js-Preview läuft unabhängig davon und ersetzt keinen dauerhaften Backenddienst.
2. Backend-Geheimnisse nur serverseitig in einem Secret-Store setzen. **Keine** Deployer-/Settlement-Schlüssel in Frontend-Variablen, ZIP oder öffentlichem Git ablegen. Wo möglich einen geeigneten Facilitator nutzen statt einen privaten Settlement-Schlüssel als Gas-Payer zu betreiben.
3. `SATYA_X402_URL` auf die gewählte Backend-URL konfigurieren und zuerst nur die unverbindliche 402-Quote testen.
4. Sicherheitsgrenzen prüfen: unterstütztes Netzwerk und Asset, Betrag, Empfänger, Ablaufzeit, Nonce, Eingabegröße sowie klare Meldung, dass der Inhalt erst nach Wallet-Freigabe gesendet wird.
5. Logs, Speicherfristen und Inhaltsverarbeitung des Prüfdienstes dokumentieren; keine Zusage „wird nicht gespeichert/trainiert“ machen, bevor das technisch verifiziert ist.

**Ergebnis:** öffentlich erreichbare Quote-API, stabile Fehlerbehandlung und dokumentierter Datenfluss. Keine Mainnet-Zahlung.

### P1 – Wallet- und Testnet-Abläufe Ende zu Ende abnehmen

Mit einer dafür vorgesehenen Test-Wallet und Testmitteln auf Celo Sepolia:

- Gültige Self Agent ID: Eigentümer stimmt überein, Menschenbeweis vorhanden und aktuell.
- Negative Fälle: andere Wallet, unbekannte ID, abgelaufener/fehlender Beweis, falsche Chain sowie abgelehnte Wallet-Anfrage.
- Prüfen, dass `declareAsHuman` nur nach den Self-Prüfungen verfügbar ist und die Wallet den tatsächlichen Inhalt/Chain-/Contract-Aufruf zur Bestätigung zeigt.
- x402-Flow im Browser: Quote ohne Inhaltsversand → genaue Betrag-/Asset-/Empfängeranzeige → explizite EIP-3009-Signatur → Serverantwort/Settlement-Beleg. Danach die Zahlung auf Blockscout nachvollziehen.
- Unautorisierter Aufruf und nicht erreichbarer Dienst: keine Zahlung, kein Inhaltsupload; erwartete sichere Fehlermeldung.

**Wichtig:** In der bisherigen Frontendprüfung wurde keine Wallet-Signatur und keine Zahlung ausgelöst. Der jetzige x402-Dienst antwortet ohne Backend mit HTTP 503. Diesen Test erst durchführen, wenn Quote, Empfänger und Test-Asset verifiziert und bewusst freigegeben sind.

### P2 – Einreichungsreife und dauerhafte Demo herstellen

1. Dauerhafte, für Juroren erreichbare Hosting-URL für Frontend und Backend bereitstellen; die aktuelle `*.manus.computer`-Preview ist temporär.
2. Demo-Video gegen finale URL neu aufnehmen, falls sich UI, Quote oder Contractdaten ändern. In der Einreichung kenntlich machen: **Celo Sepolia/Testnet**, keine Mainnet-Zahlung, kein unabhängiger KI-Ursprungsbeweis.
3. Kurzen Pitch und README auf den gewählten Track ausrichten: Problem → Celo-/Self-/x402-Beitrag → nachprüfbare Live-Demo → klare Grenzen.
4. Einreichungscheckliste des Portals abarbeiten: Projektname, kurze Beschreibung, Repo, Demo-URL, Video, Teamangaben und nötige Screenshots.

### P2 – Repository und Release vorbereiten

- Vor dem Upload Ziel klären: neues öffentliches Satya-Repository oder ein anderes, ausdrücklich ausgewähltes Ziel. Der aktuelle Stand ist **lokales Git plus ZIP**; es wurde nichts gepusht.
- Vor einem öffentlichen Push: `.env*`, `.secrets/`, Wallet-/Deployerschlüssel, Testkäuferdaten, lokale Chainzustände und sensible Rohdaten ausschließen; Secret-Scan und `git diff` durchführen.
- Lizenz bewusst wählen, `README.md`, Installationsschritte, Contractadresse, Testnetz-Warnung und Grenzen beilegen.
- Falls das gewählte Ziel öffentlich ist, finale Repo-/Branch-/Dateiliste vor der Veröffentlichung bestätigen.

### P3 – Datenschutz, Sicherheit und Betrieb

Vor einer Nutzung mit echten Nutzern oder wertvollen Inhalten:

- Threat Model und unabhängige Prüfung des Contracts, Self-ID-Zuordnungsflows, x402-Settlement und Backendlimits.
- Datenschutz-/Nutzungsinformation: welche Datei-/Textdaten übertragen werden, warum, wer sie sieht, wie lange sie gespeichert werden und wie Nutzer sie löschen lassen können.
- Rate Limits, Monitoring, Abuse-/Replay-Schutz, Fehleralarme, Backup und Verantwortlichkeit für Backend-/Key-Rotation.
- Mainnet, echte USDC oder produktive Identitätsaussagen erst nach Review, Tests und eigener Freigabe. Für den Hackathon ist der bestehende Testnet-Stand die risikoärmere Option.

## Abnahmekriterien für „Hackathon-fertig“

- [ ] Deadline, Teilnahmebedingungen und gewählter Track sind anhand des offiziellen Portals bestätigt.
- [ ] Permanente Demo-URL funktioniert auch ohne lokale/sandboxgebundene Prozesse.
- [ ] Live-Celo-Beispiel, gültige Self-Prüfung und negative Self-Fälle wurden nachvollzogen.
- [ ] Quote und eine bewusst ausgelöste Testnet-Zahlung des **aktuellen Browserflows** wurden auf dem Explorer geprüft — oder die Zahlungsfunktion wird in der Einreichung klar als nicht live verfügbar gekennzeichnet.
- [ ] Kein privater Schlüssel oder nicht freigegebener Inhalt liegt im öffentlichen Repo.
- [ ] README, kurze Pitchbeschreibung und Video stimmen mit der finalen Version überein.
- [ ] Keine Aussage erweckt den Eindruck, Satya könne beliebigen KI-Inhalt todsicher klassifizieren.
- [ ] Einreichung wurde im offiziellen Portal bestätigt und der endgültige Link archiviert.

## Entscheidungen, die noch vom Projektverantwortlichen abhängen

1. Welcher offizielle Track und welche Abgabefrist gelten laut Loops House?
2. Wo soll das Frontend und insbesondere der x402-Backenddienst dauerhaft laufen?
3. Soll ein neues **öffentliches** Satya-Repository erstellt werden, und falls ja: unter welchem exakten Namen?
4. Soll die x402-Zahlung für die Demonstration live ausgeführt werden? Wenn ja, nur nach Prüfung der exakten Testnet-Quote und mit Testmitteln.
5. Soll das Video nur in der Hackathon-Einreichung liegen oder zusätzlich öffentlich veröffentlicht werden?

## Quellen und Übergabe

- [CeloDev-Ankündigung: Kick-off am 6. Oktober und Anmeldung über Loops House](https://x.com/CeloDevs/status/2106021545999258063)
- [Agents on Open Rails – Kick-off und Programmbeschreibung](https://lu.ma/uk27jw1q)
- [Celo-Dokumentation zu Agents, x402 und Celo](https://docs.celo.org/build-on-celo/build-with-ai/overview)
- [Lokaler Projektstand und offene Punkte](../TODO.md)
- [README und Demo-Artefakte](../README.md)

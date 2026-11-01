# Satya – Agents on Open Rails: Readiness

**Prüfstand:** 26. Oktober 2026 · offizielle Loops-House- und Celo-Dokumentation, Live-Abfrage des x402-Facilitators

## Frist und Anforderungen

Die Registrierung und Einreichung schließen am **9. November 2026 um 09:00 GMT**. Die Regeln verlangen Celo Mainnet, ein bei Registrierung öffentliches und bis zur Jurierung erreichbares GitHub-Repository, eine ERC-8004-Agentenidentität und ERC-8021-Attribution in wertungsrelevanten Transaktionen. Tags können nicht rückwirkend ergänzt werden. Die Eventseite sagt außerdem, der Code müsse während des Hackathons geschrieben worden sein. Da Satya schon vor dem Start am 6. Oktober existierte, muss die Zulässigkeit des bestehenden Projekts vor einer Bewerbung mit den Veranstaltern geklärt werden. [1]

Die möglichen Tracks sind Stable Agents: LatAm mit Ripio-wFIAT und LatAm-Nutzung, Open Corridors mit Textile FX oder USA₮ über x402, sowie Build with buy für bezahlte Aufrufe an externe Dienste, die das Team nicht selbst betreibt. Beim USA₮-Track verlangt die Seite echte Settlements zwischen unabhängigen Parteien; beim Build-with-buy-Track zählen nachweisbare bezahlte Calls an fremde Dienste. [1]

## Satya-Stand und Track-Fit

Satya hat einen x402-Prototyp für **Celo Sepolia und Test-USDC**. Die vorhandene Payment-Konfiguration bietet USDC an; ein Mainnet-USA₮-Flow ist nicht fertig. Außerdem bezahlt der derzeitige Käuferfluss Satyas eigenen Prüf-Endpunkt. Das allein erfüllt nicht Build with buy, weil der Track externe, vom Team unabhängige Dienste bewertet. Für Stable Agents: LatAm sind weder Ripio-wFIAT-Nutzung noch echte LatAm-Nutzer nachgewiesen.

Die nächstliegende, aber **bedingte** Route ist Open Corridors / USA₮ x402. Die Live-API `https://api.x402.celo.org/supported` führt USA₮ (`USAT`, `0xD2ab3C9A02DBBAB236BfEC45D1d755DF4267F771`) für x402 v1 und v2. Die bestehende Satya-Konfiguration wählt dieses Asset jedoch noch nicht aus. Für eine belastbare Einreichung müsste eine unabhängige Person eine sinnvolle Satya-Leistung tatsächlich mit USA₮ bezahlen.

Ein wichtiger Attributionsblocker bleibt: Celo dokumentiert, dass der gehostete x402-Facilitator seine Settlement-Transaktionen **noch nicht** mit ERC-8021-Rollen-Tags versieht. Beim x402-Kauf signiert der Nutzer eine Autorisierung, aber der Facilitator sendet die Settlement-Transaktion. Die offizielle `@celo/attribution-tags`-Bibliothek kann Satya-eigene Wallet-Transaktionen taggen; sie kann ein Facilitator-Settlement nicht nachträglich taggen. Loops House muss deshalb klären, ob solche USA₮-x402-Settlements gewertet werden und ob es einen anerkannten Workaround gibt. [2] [3] [4]

## Weitere Blocker

- Aktuelle Registry- und Zahlungsdemonstration sind auf Sepolia/Test-USDC ausgerichtet; Testnet-Aktivität zählt nicht als Mainnet-Nachweis.
- In der aktuellen Sandbox-Kopie gibt es kein Git-Metadatenverzeichnis oder Remote. Das vollständige Projekt wurde aus dem geprüften ZIP nach `/home/ubuntu/satya-hackathon-work/` wiederhergestellt. Es wurde nichts öffentlich gepusht.
- Ein Mainnet-ERC-8004-Agent, eine Loops-Registrierung und ein zugewiesener Attribution-Code sind nicht nachgewiesen.
- `SatyaCelo` v1 speichert und veröffentlicht den Self-Human-Nullifier und verknüpft Aussagen mit Agent-ID und Wallet. Der ownerless Vertrag ist nicht upgradefähig. Vor einem Mainnet-Einsatz sollte eine datenschutzärmere V2 entwickelt werden; vorhandene On-chain-Daten lassen sich nicht rückwirkend löschen.
- Der vorhandene Code stammt aus der Zeit vor dem Hackathon. Keine Einreichung sollte behaupten, die Hackathon-Code-Regel sei erfüllt, bevor Loops House die Wiederverwendung bestehender Komponenten schriftlich eingeordnet hat.
- Im wiederhergestellten Projekt bestanden **60/60 Foundry-Tests**. Die Python-Suite war in einem früheren Lauf mit **20/20** Tests grün; in dieser Sandbox fehlt `pytest`, daher konnte sie hier nicht erneut ausgeführt werden.

## Empfohlene Reihenfolge

Zuerst Loops House um schriftliche Klärung bitten: (1) Ist Satya mit einer vor dem Hackathon begonnenen Codebasis teilnahmeberechtigt, wenn neue, klar abgegrenzte Arbeit während des Events entsteht? (2) Wie werden USA₮-x402-Settlements ohne ERC-8021-Tag des gehosteten Facilitators gewertet? Vor einer Antwort sollten keine Mainnet-Transaktionen oder öffentlichen Veröffentlichungen gestartet werden.

Wenn Loops House die Teilnahme und Abrechnung bestätigt, kann der Nutzer die öffentliche Repository-Veröffentlichung und Registrierung freigeben. Danach den tatsächlichen Event-Attribution-Code in sämtliche Satya-kontrollierten Transaktionen einbauen. Erst dann Mainnet-Aktivität beginnen und eine echte Zahlung durch eine unabhängige Person demonstrieren. Die bestehende SatyaCelo-v1-Adresse nicht als privacy-preserving Mainnet-Ziel verwenden.

### Entwurf für Loops House

> Hi Loops House team — I’m considering entering Satya in Agents on Open Rails. Satya is an existing provenance project whose codebase predates the October 6 hackathon. We would build and document a clearly scoped new feature during the event. Is this eligible under “code is written during the hackathon,” and what existing components must be disclosed? Also, Satya’s closest track is Open Corridors / USA₮ x402, but Celo’s current x402 documentation says the hosted facilitator does not yet add ERC-8021 role tags to settlement transactions. Can such a settlement qualify if the app’s own on-chain transactions are tagged, and is there an approved workaround or planned support?

*Der Entwurf wurde nicht gesendet.* Keine Registrierung, Veröffentlichung, Wallet-Signatur, Mainnet-Transaktion oder Einreichung wurde vorgenommen.

## Quellen

[1]: https://www.loops.house/agents-on-open-rails "Agents on Open Rails Hackathon – offizielle Eventseite"
[2]: https://docs.celo.org/build/agents/x402 "Celo x402-Agentenzahlungen und Facilitator"
[3]: https://api.x402.celo.org/supported "Live unterstützte Netzwerke und Assets des Celo-x402-Facilitators"
[4]: https://github.com/celo-org/attribution-tags/blob/main/sdk/README.md "Celo ERC-8021 Attribution-Tags SDK und Status der Facilitator-Unterstützung"

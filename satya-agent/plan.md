# Satya – Hackathon-Finish Plan (26.10.2026)

## Ziel und Grenzen

Die Demo soll die stärkste ehrliche Aussage über Content-Provenienz auf Celo zeigen: Aussagen sind zurechenbar und kryptografisch prüfbar; ohne gültigen Beleg bleibt das Ergebnis unbestimmt. Keine Behauptung, beliebige KI-Erzeugung zuverlässig zu erkennen. Zieltrack bleibt vorläufig Open Corridors / USA₮ x402, vorbehaltlich Veranstalterklärung zu vorbestehendem Code und Attribution der Settlements. Keine Sybil-Nutzung, erfundenen Nutzer, künstlichen Volumina, öffentliche Veröffentlichung, Hackathon-Nachricht oder Mainnet-Transaktion ohne ausdrückliche Freigabe.

## Umsetzung

1. **ERC-8021:** Satya-kontrollierte Wallet-Schreibvorgänge verwenden `@celo/attribution-tags` mit dem tatsächlich von Loops zugewiesenen App-Code. Wenn der erforderliche Code fehlt, wird der Schreibvorgang vor Wallet-Autorisierung blockiert. Für den x402-Relayer eine Rolle-basierte ERC-8021-Suffix-Funktion nach der offiziellen Schema-2-Spezifikation implementieren und gegen das offizielle SDK abgleichen.
2. **USA₮-x402:** Backend-Assetkonfiguration um die vom Live-Facilitator bestätigte Mainnet-USA₮-Adresse und deren EIP-712-Domäne erweitern; standardmäßig bleibt die produktive Mainnet-Konfiguration deaktiviert, bis Empfänger, Relayer-Key, App-Code und Nutzerhinweis explizit konfiguriert sind. Kundendaten werden erst nach unterschriebener Zahlung übermittelt.
3. **Settlement-Sicherheit:** Ergebnisse nur nach bestätigtem Settlement ausliefern. Erfolgreiche Receipt-Antwort allein reicht nicht; mindestens erfolgreicher On-chain-Beleg und erwarteter Transfer werden geprüft. Mainnet-Settlement ohne gültige Attribution-Konfiguration wird fail-closed abgelehnt. Keine automatische Zahlung oder Transaktion.
4. **Privacy:** Die bestehende, unveränderliche SatyaCelo-v1 nicht als Mainnet-Privacy-Lösung verwenden. Eine separate, ownerless V2 auf Basis eines Satya-spezifischen Self-Hub-V2-Scopes technisch verifizieren. V2 speichert keine Self-Agent-ID und keinen globalen Self-Nullifier; öffentliche Bindungen an Wallet/Content werden minimiert. Eine Aussage muss weiterhin gegen Manipulation und Replay gebunden sein. Unklare Self-Proof-Details vor Implementierung im Quellcode und anhand offizieller Referenz verifizieren.
5. **Agent discovery und Erklärung:** ERC-8004-Registry-Adresse pro Chain korrekt ausweisen, der Agent-Card tatsächliches Zahlungsasset und Preis zuordnen, Demo- und Bewertungsgrenzen klar kennzeichnen. Vorhandene Oberfläche und visuelle Sprache beibehalten.

## Projektstruktur

- `satya-agent/app/components/WalletPanel.tsx`: Wallet-/Self-Flow und Satya-eigene getaggte Contract-Writes.
- `satya-agent/app/components/X402Panel.tsx`: kontrollierte Quote, explizite Wallet-Signatur, Chain-/Asset-Anzeige und Settlement-Beleg.
- `satya-agent/app/lib/celo.ts`: Chain-, Contract- und Attribution-Konfiguration.
- `satya-agent/app/api/x402/route.ts`: Same-origin-Proxy; keine Geheimnisse in den Browser.
- `satya/satya/x402.py`: x402-Asset-Metadaten, Verifikation, getaggter EIP-3009-Relayer und bestätigte Abrechnung.
- `satya/satya/server.py`: kostenpflichtige Route liefert Analyse nur nach erfolgreicher Abrechnung.
- `satya-agent/contracts/src/`: bestehende Verträge bleiben unverändert; separate V2-Datei und Tests erst nach Self-Protokollprüfung.
- `docs/`: aktueller Hackathon-Status, Datenschutzgrenzen, Setup- und reproduzierbare Nachweise.

## Materiale Abhängigkeiten und Status

Die offizielle Event-Attribution-ID fehlt noch; bis dahin ist nur lokales Testen mit einem ausdrücklich nicht produktiven Code zulässig. Ein mainnetfähiger x402-Betriebs-/Relayer-Key und ein ERC-8004-Mainnet-Agent sind nicht vorhanden. Die Celo x402-Hosted-Facilitator-Settlement-Transaktionen sind derzeit ungetaggt; ein getaggter Satya-Relayer wäre ein technischer Ansatz, aber seine Zulässigkeit als Event-Settlement ist noch nicht bestätigt. Keine Mainnet-V2-Adresse oder Self-Hub-V2-Integration ist bisher bereitgestellt.

# Satya – Readiness für Agents on Open Rails

**Prüfstand:** 12. Oktober 2026 · offizielle Loops-House-Seite

## Frist

Die Anmeldung und die Projekteinreichung enden laut Loops House am **Montag, 9. November 2026 um 09:00 GMT**. Die Gewinner sollen am **Freitag, 13. November** bekannt gegeben werden. Der Hackathon startete am 6. Oktober um 12:00 GMT. [1]

## Verbindliche Anforderungen laut Eventseite

- **Celo Mainnet:** Für die Wertung zählt Mainnet-Aktivität. Sepolia-/Testnet-Verweise im Repository sind zulässig, aber Testnet-Transaktionen zählen nicht.
- **Attribution Tag:** Nach der Anmeldung gibt es einen Attribution Tag. Er muss von der ersten relevanten Transaktion an in **jede** Celo-Transaktion eingebaut sein; nachträgliche Zuordnung ist nicht möglich.
- **ERC-8004:** Die Agent-Wallet muss dem Eintrag hinzugefügt werden. Die ERC-8004-Identität muss vor der Frist aus genau dieser Wallet registriert werden.
- **Öffentliches GitHub-Repository:** Bei der Anmeldung muss ein öffentliches Repository angegeben werden, das auch zum Bewertungszeitpunkt noch erreichbar ist.
- **Entstehung der Arbeit:** Die Regeln sagen, dass der Code während des Hackathons geschrieben wird. Bei einer Weiterentwicklung eines bereits begonnenen Projekts sollte vor der Anmeldung mit dem Veranstalter geklärt werden, welche vorhandene Basis akzeptiert wird.
- **Gas-Sponsoring:** Gesponserte Gasgebühren zählen nicht als Beitrag des Builders. Ein Team kann mehrere Tracks einreichen, aber höchstens einen Preis pro Track gewinnen.

## Satya – aktueller Abstand zu einer wertbaren Einreichung

Satya ist derzeit auf **Celo Sepolia** ausgerichtet. Die Registry und das Frontend protokollieren beziehungsweise prüfen Testnet-Erklärungen; der neue `SatyaHumanSBT` ist noch nicht deployed. Daher ist noch keine Mainnet-Aktivität für die Hackathon-Wertung belegt. Das lokale x402-Backend war auf Port 8000 nicht aktiv. Ein sicherer lokaler Starttest funktionierte, meldete aber `celo: null` und `x402: null`, weil hier keine Celo-/x402-Konfiguration bereitgestellt ist.

Der Solidity-Code enthält bereits eine ERC-8004-Registry-Schnittstelle und unterstützt entsprechende Agent-Erklärungen. Eine hackathonspezifische Anmeldung der Agent-Wallet aus dem Loops-Eintrag ist jedoch nicht nachgewiesen. Ebenso ist im Repository noch kein Celo-Attribution-Tag integriert oder nachgewiesen. Die Arbeitskopie hat außerdem kein konfiguriertes Git-Remote und ist nicht öffentlich gepusht.

**Fazit:** Satya ist nicht im aktuellen Sepolia-/Test-USDC-Zustand einreichungsbereit. Das Konzept könnte zum Track **Build with buy** passen, wenn Satya tatsächlich über `buy` für eine externe Leistung bezahlt und die erforderlichen Mainnet-Nachweise erzeugt. Der Track **USA₮ with x402** wäre eine alternative Richtung, erfordert aber echte Mainnet-Abwicklung mit USA₮ und passende Nutzeraktivität. Der bestehende x402-Testnet-Flow erfüllt diese Voraussetzungen nicht.

## Nächste Schritte vor einer Einreichung

1. Ziel-Track und die konkrete, wertbare Nutzeraktion festlegen.
2. Mit Loops House klären, wie die bestehende Satya-Codebasis zur Regel „Code is written during the hackathon“ behandelt wird.
3. Öffentliches GitHub-Ziel bestimmen und die erforderliche Veröffentlichung freigeben.
4. Agent-Wallet und ERC-8004-Identität mit dem Loops-Eintrag verbinden.
5. Den Tag aus dem Eintrag vor der ersten relevanten Transaktion integrieren und Mainnet-Aktivität verifizieren.
6. SBT-Mainnet-Deployment und x402-/`buy`-Integration erst nach getrennter technischer und Nutzerfreigabe planen.

Es wurden **keine** Registrierung, Veröffentlichung, Wallet-Signatur, Mainnet-Transaktion oder Hackathon-Einreichung vorgenommen.

## Quelle

[1]: https://www.loops.house/agents-on-open-rails "Agents on Open Rails Hackathon – offizielle Loops-House-Seite"


---

**Aktualisierung:** Dieser Bericht spiegelt den Stand vom 12. Oktober 2026 wider. Bitte den neueren Prüfbericht [`HACKATHON_READINESS_2026-10-26.md`](HACKATHON_READINESS_2026-10-26.md) verwenden; dort sind die aktuellen Anforderungen, die USA₮-Supportprüfung und der ERC-8021-Attributionsblocker dokumentiert.
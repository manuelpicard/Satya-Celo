# Satya

Nachvollziehbare Herkunft für digitale Inhalte auf **Celo**: Satya bindet prüfbare, signierte Aussagen an einen Content-Hash und bietet eine bezahlbare Prüfung pro Anfrage über **x402**.

> **Status:** Hackathon-Projekt für [Agents on Open Rails](https://www.loops.house/agents-on-open-rails). Der Quellcode wird in diesem Repository veröffentlicht; bis dahin ist es ein Platzhalter mit der Projektbeschreibung.

## Was Satya ist — und was nicht

Satya ist **kein** universeller KI-Detektor. Es geht um Provenienz und Rechenschaft:

- Ein Ergebnis gilt nur dann als **gewiss**, wenn ein passender kryptografischer Beleg geprüft wurde (z. B. gültiges C2PA-Manifest, signierte Aussage).
- Ohne passenden, gültigen Beleg lautet das Ergebnis **unbestimmt**. Fehlende Metadaten oder Registry-Einträge beweisen keine menschliche Urheberschaft.
- Eine signierte Aussage belegt, *wer* sie abgegeben hat — nicht, dass sie wahr ist.
- Ein Proof-of-Personhood (Self) belegt für sich allein nicht, dass eine Person einen bestimmten Inhalt erstellt hat.

## Geplante Bestandteile

- **Contracts (Solidity, Celo):** Register für Herkunftsaussagen (Self-Human, Self-Agent, ERC-8004-Agent), Widerruf, EIP-712-Siegel; optional ein Soulbound-Menschennachweis (ERC-5192).
- **Engine (Python/FastAPI):** Hashing, C2PA-Prüfung, Metadaten-/Wasserzeichenhinweise, deterministische Urteilslogik (`Beleg` vs. `Hinweis`).
- **dApp (Next.js):** Hashing im Browser, Anzeige der Befunde, Wallet-Aktionen bleiben beim Nutzer.
- **x402:** Prüfdienst pro Anfrage, bezahlt über den Celo-x402-Facilitator.

## Sicherheit

- Keine privaten Schlüssel, Seed-Phrasen oder Zugangsdaten im Repository.
- Test-/Demo-Schlüsselmaterial ist ausschließlich lokal und nie produktiv zu verwenden.
- Vor einem Produktiv-Einsatz sind ein Contract-Audit und eine Datenschutzprüfung nötig (On-Chain-Kennungen sind öffentlich lesbar).

## Lizenz

Wird mit der Code-Veröffentlichung festgelegt.

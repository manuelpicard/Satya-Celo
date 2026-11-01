# Satya – Celo-Prototyp für Herkunftserklärungen

Satya ist eine Celo-Sepolia-dApp für überprüfbare, signierte Herkunftserklärungen. Sie kann feststellen, **welche Aussage zu einem passenden Content-Hash im Register steht**. Sie kann nicht beweisen, dass irgendein Inhalt durch KI oder einen Menschen erzeugt wurde, und verspricht ausdrücklich keine todsichere KI-Erkennung.

## Funktionen

- Datei auswählen und SHA-256 lokal im Browser berechnen (bis 50 MB); der Demo-Button lädt ein Testbild und fragt den passenden Registereintrag live auf Celo Sepolia ab.
- Text nach Satya `satya-text-v1` normalisieren und hashen oder einen vorhandenen SHA-256-Hash prüfen.
- Registeraussagen, Urheber-Erklärungsart, Identitätsquelle, Zeitstempel und Widerspruchsstatus direkt aus `SatyaCelo` lesen.
- EIP-1193-Wallet verbinden, auf Celo Sepolia wechseln und eine eingegebene Self Agent ID hinsichtlich Wallet-Eigentum, vorhandenem Menschenbeweis und dessen Aktualität prüfen.
- Nur bei erfüllten Voraussetzungen kann eine Erklärung mit `declareAsHuman` erstellt werden. Die Wallet zeigt die Transaktion zur Bestätigung an; der Dienst signiert oder sendet sie nicht selbst.
- Für optionale x402-Prüfungen erst den Preis ohne Inhaltsübermittlung abfragen. Betrag, Asset, Netzwerk und Empfänger werden vor dem separaten Wallet-Signierschritt angezeigt. Erst nach der EIP-3009-Autorisierung übermittelt der Browser den ausgewählten Inhalt an den Prüfdienst.

## Live-Demo-Video

- [Satya-Demo (MP4, 16,6 Sekunden, 1280×720)](demo-video/satya-demo.mp4)
- [Deutsche Untertitel (SRT)](demo-video/satya-demo.de.srt)
- [Posterbild](demo-video/satya-demo-poster.png)

Der Clip zeigt die echte Produktoberfläche und einen zuvor live gelesenen Celo-Sepolia-Registerbefund. Die x402-Karte zeigt eine Testnet-Quote; es wurde während der Aufnahme keine Zahlung signiert oder ausgelöst. Eine Testnet-Quote bzw. ein gespeicherter UI-Aufnahmebeleg ist kein Beweis für Inhaltserzeugung. Der Clip enthält nur zurückhaltende, synthetisch erzeugte UI-Sounds, keine gesprochene Narration.

### Videoaufnahme reproduzieren

Voraussetzungen: laufende Satya-Webapp, erreichbarer x402-Backenddienst für die unverbindliche Quote, Python-Pakete aus `requirements-demo.txt`, Chromium und FFmpeg. Der Aufnahme-Workflow sendet weder Wallet-Signaturen noch Zahlungen.

```bash
npm install
npm run build
npm run start -- --hostname 0.0.0.0 --port 3000
```

In einem zweiten Terminal:

```bash
python3 -m pip install -r requirements-demo.txt
python3 -m playwright install chromium
SATYA_DEMO_URL=http://localhost:3000 \
  SATYA_DEMO_DIR="$PWD/demo-video" \
  python3 scripts/record_demo.py
SATYA_DEMO_DIR="$PWD/demo-video" python3 scripts/render_demo_video.py
```

Für Systeme mit bereits installiertem Chromium kann `CHROMIUM_PATH=/usr/bin/chromium` gesetzt werden. `record_demo.py` nimmt Live-UI-Zustände auf; `render_demo_video.py` baut daraus den MP4-Clip mit Schlusskarte und Audioeffekten.

## Lokal starten

```bash
npm install
npm run dev
```

Öffne <http://localhost:3000>. Eine EVM-Wallet wie MetaMask wird nur für die Self-Prüfung/Erklärung und den optionalen x402-Schritt benötigt. Der Browserproxy liefert bei unerreichbarem x402-Backend eine Fehlermeldung, statt eine Zahlung auszulösen.

## Konfiguration

Standardmäßig werden Celo Sepolia und der Satya-Contract verwendet. Optional:

```env
CELO_RPC_URL=https://forno.celo-sepolia.celo-testnet.org
NEXT_PUBLIC_SATYA_CELO_ADDRESS=0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001
SATYA_X402_URL=http://127.0.0.1:8000
```

`SATYA_X402_URL` muss auf einen Satya-Backenddienst mit `POST /api/x402/verify` zeigen. Es werden keine privaten Schlüssel aus der Frontendkonfiguration gelesen. Lokale `.env`-Dateien sind in `.gitignore` ausgeschlossen.

## Celo Sepolia

| Wert | Angabe |
|---|---|
| Chain ID | `11142220` |
| RPC | `https://forno.celo-sepolia.celo-testnet.org` |
| SatyaCelo | `0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001` |
| Self Agent ID Registry | `0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379` |
| x402-Test-USDC | `0x01C5C0122039549AD1493B8220cABEdD739BC44E` |
| Explorer | [SatyaCelo in Blockscout](https://celo-sepolia.blockscout.com/address/0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001) |

## Soulbound Human Credential

Der Foundry-Vertrag für das Self-verifizierte, nicht übertragbare Menschennachweis-Credential liegt versioniert unter [`contracts/`](contracts/README.md). Er implementiert ERC-5192, beschränkt Claims auf einen Self-Nullifier und unterstützt explizite Recovery für dieselbe Person. Die vollständigen Design-, Datenschutz- und Testhinweise stehen in [`contracts/README.md`](contracts/README.md).

Der neue SBT ist **noch nicht auf Celo Sepolia deployed** und noch nicht an einen Mint-/Recovery-Button im Frontend angeschlossen. Das Deployment-Skript ist testnet-only; kein Deployment oder Wallet-Transaktion wurde in dieser Arbeit ausgelöst.

Die Solidity-Dependencies sind im Git-Repository als taggepinnten Submodule (`openzeppelin-contracts v5.7.0`, `forge-std v1.17.0`) abgelegt. Nach einem normalen Clone lassen sie sich so laden und testen:

```bash
git submodule update --init --recursive
cd contracts && forge test
```

## Sicherheits- und Produktgrenzen

Das Register weist signierte Erklärungen nach. Es beweist nicht unabhängig, wer einen Inhalt tatsächlich erstellt hat. Ein Self-Menschenbeweis attestiert die Erfüllung der Self-Prüfung für ein Konto; er macht die Inhaltserklärung nicht automatisch wahr. Ein fehlender Registereintrag bedeutet **nicht**, dass der Inhalt menschlich erstellt wurde. x402 in dieser Demo ist auf Celo Sepolia und Test-USDC begrenzt. Es wird keine Mainnet-Zahlung durch Satya angeboten oder ohne ausdrückliche Wallet-Freigabe initiiert.

## Entwicklungsstand

Der TypeScript-Check und `next build` sind erfolgreich. GitHub-Push, öffentliche Videoveröffentlichung und Hackathon-Registrierung sind nicht Teil dieses lokalen Pakets; sie bleiben bis zu einer ausdrücklichen Freigabe aus. Die geprüfte Frist und die noch offenen Hackathon-Voraussetzungen stehen in [`docs/HACKATHON_READINESS.md`](docs/HACKATHON_READINESS.md); der allgemeine Übergabestatus steht in [`TODO.md`](TODO.md).


**Aktualisierung 26.10.2026:** Die neueste Hackathon-Einschätzung mit aktuellem Track-Fit und ERC-8021/x402-Blocker steht in [`docs/HACKATHON_READINESS_2026-10-26.md`](docs/HACKATHON_READINESS_2026-10-26.md). Diese Fassung ergänzt den älteren Stand unter `docs/HACKATHON_READINESS.md`.


**Security- und Attribution-Baseline (26.10.2026):** Next.js 15.5.28 und PostCSS 8.5.31; `npm audit` meldet null Advisories. Die ERC-8021-/x402-Weiterarbeit und ihre Stop-Bedingungen stehen im [Hackathon-Finish-Plan](plan.md) und in der [Security-Baseline](docs/SECURITY_BASELINE_2026-10-26.md).
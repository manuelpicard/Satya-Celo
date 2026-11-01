# Satya – Herkunft prüfen statt raten

*satya* (सत्य) – Sanskrit für Wahrheit.

Satya beantwortet die Frage, ob ein Inhalt von einer KI stammt, nur dann mit Sicherheit, wenn eine haftbare Stelle das **kryptografisch überprüfbar erklärt** hat. Fehlt ein solcher Nachweis, lautet das Urteil ehrlich `UNBESTIMMT`. Satya rät nicht anhand von Stil, Wortstatistik oder Wasserzeichen-Wahrscheinlichkeiten.

Das Projekt hat zwei Schichten:

1. **Wer ist ein Mensch** – das HMN-Credential (`../human-token`) sowie das optionale, Self-verifizierte `SatyaHumanSBT` (ERC-5192) unter `contracts/src/credentials/`.
2. **Wer verbürgt sich für einen Inhalt** – das Herkunftsregister, live auf Celo.

Das vollständige Konzept mit Begründung, Auswertung und Quellen steht in [`docs/Satya-Konzept.md`](docs/Satya-Konzept.md).

## Live auf Celo

Das öffentliche Herkunftsregister läuft auf **Celo Sepolia**. Jede Erklärung ist über Self Agent ID an den ZK-Nullifier eines echten Ausweises gebunden: eine Person, eine Stimme – nicht eine Wallet, eine Stimme. Wer sich widerspricht, kann von **jedem** widerlegt werden, ohne Betreiber. Der Vertrag hat keinen Eigentümer.

| | |
|---|---|
| `SatyaCelo` | [`0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001`](https://celo-sepolia.blockscout.com/address/0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001) (Quellcode verifiziert) |
| Self Agent ID | `0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379` |
| ERC-8004 | `0x8004A818BFB912233c491871b3d84c89A494BD9e`, Satya agentId **453** |
| Bezahlter Endpunkt | `POST /api/x402/verify` · 0,01 USDC je Anfrage über EIP-3009, kein Konto |

Begründung, Live-Daten und Messergebnisse: [`docs/Satya-Celo.md`](docs/Satya-Celo.md).

```bash
./demo/serve.sh 8000          # Dienst mit Celo-Register und lokalem Demo-Register
python3 demo/celo_flow.py     # vollständiger Ablauf gegen die Live-Chain
python3 demo/x402_client.py   # als Agent eine Prüfung kaufen (braucht Test-USDC)
```

## Urteile

| Urteil | Sicher | Grundlage |
|---|---|---|
| `KI_NACHGEWIESEN` | ja | C2PA-Signatur eines KI-Anbieters auf der offiziellen Vertrauensliste, Registereintrag eines KI-Anbieters oder ehrliches Siegel „mit KI“ |
| `MENSCH_BEZEUGT` | ja | Siegel oder Registereintrag eines verifizierten Menschen (HMN-Credential bzw. Self Agent ID) |
| `KAMERA_NACHGEWIESEN` | ja | C2PA-Signatur eines vertrauenswürdigen Aufnahmegeräts |
| `WIDERSPRUCH` | nein | Gültige Nachweise widersprechen sich |
| `HERKUNFT_GEBROCHEN` | nein | Inhalt nach der Signatur verändert |
| `UNBESTIMMT` | nein | Kein überprüfbarer Nachweis |

## Aufbau

```
satya/          Python-Paket: Engine, Prüfmodule, Urteilslogik, CLI, Web-API
  verdict.py        reine Urteilsfunktion (nur Beweise entscheiden)
  c2pa_check.py     C2PA gegen offizielle Trust List (trust/)
  seal.py           EIP-712-Siegel für Texte und Dateien
  ledger.py         Anbindung an SatyaRegistry und HMN
  celo_ledger.py    Leser für SatyaCelo (Self Agent ID, ERC-8004)
  x402.py           Bezahlschicht: 402-Angebot, Verifikation, Abrechnung
  metadata_check.py, watermark_check.py, hashing.py
contracts/          SatyaCelo.sol, SatyaRegistry.sol, SatyaHumanSBT + Foundry-Tests
web/                Weboberfläche (Deutsch)
demo/               Demo-CA, lokale Chain, Korpus mit 22 Fällen, Auswertung
tests/              pytest inkl. Eigenschaftstests (hypothesis)
docs/               Konzept (MD/PDF), Architekturdiagramm
```

## Schnellstart

Voraussetzungen sind Python 3.11, [Foundry](https://book.getfoundry.sh/) und das Repository `human-token` (Schicht 1) im Nachbarverzeichnis.

```bash
pip install -r requirements.txt
bash demo/run_demo.sh          # Chain, Contracts, Korpus, Auswertung, Web-UI auf :8000
```

Einzelne Dateien prüfen:

```bash
python -m satya pruefen bild.png
python -m satya pruefen --text "Beliebiger Text"
python -m satya pruefen bild.png --json
```

Mit Register (Umgebungsvariablen `SATYA_RPC`, `SATYA_REGISTRY`) lassen sich Texte versiegeln und verankern. Der private Schlüssel wird nur über `SATYA_KEY` übergeben:

```bash
python -m satya siegeln aufsatz.txt --ki 0      # 0 = ohne KI, 1 = mit KI-Unterstützung, 2 = KI-generiert
python -m satya verankern aufsatz.versiegelt.txt
```

## Tests

```bash
python -m pytest -q                     # 20 Tests
(cd contracts && forge test)            # 60 Tests, davon 14 für das Soulbound-Credential
python demo/evaluate.py                 # Auswertung auf dem Korpus
```

Im GitHub-Arbeitsbaum liegen die Contracts unter `satya-agent/contracts/`. Nach einem Clone dort zuerst `git submodule update --init --recursive` ausführen; die Foundry-Abhängigkeiten sind auf Versionen festgelegt.

## Ergebnis der Auswertung

Auf 22 Fällen mit bekannter Wahrheit (echte OpenAI- und Google-Bilder, echte KI-Texte, echte Fotos, Fälschungsangriffe) trifft Satya 9 sichere Urteile, davon **eines falsch**. Echte menschliche Inhalte wurden **nie** fälschlich als KI eingestuft. Der eine Fehler ist die konsistente Lüge einer verifizierten Person – nach Aufdeckung des Widerspruchs sinkt er auf null. Ein naiver Indizien-Detektor liegt im selben Korpus fünfmal falsch, davon dreimal mit einer falschen KI-Beschuldigung.

## Sicherheitshinweis

Die Demo-CA, die Anvil-Schlüssel und der Endpunkt `/api/demo/siegeln` dienen nur der Vorführung. Sie dürfen nie produktiv eingesetzt werden. Vor einem produktiven Einsatz sind ein externes Audit der Contracts und eine Datenschutz-Folgenabschätzung nötig.

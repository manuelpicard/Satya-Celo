# Satya kauft ein — Konzept und Ablauf für „Build with buy“

**Stand:** 2. November 2026. Quellen: Hackathon-Seite, `celo-org/buy-skill`. Nichts hier wurde bezahlt oder auf Mainnet ausgeführt.

## Idee

Satya sagt nur dann „sicher“, wenn ein kryptografischer Beleg vorliegt. Zusätzliche Signale, die Satya **bei Dritten kauft**, sind deshalb immer nur **Indizien** (`Tier.HINT`): Sie werden angezeigt, können aber nie ein Urteil ändern. Beispiel: „Dieser Text wurde laut einer bezahlten Suche schon früher veröffentlicht“ (Zeitleiste), „Kursdaten stimmen mit der Behauptung überein“. Das passt zur Regel des Projekts und ist ehrlich.

## Technik (so ist es gebaut)

- Bezahlt wird **nicht von Satya selbst**, sondern vom x402-Client `@celo/buy` (MCP-Server). Sein Schlüssel liegt im Betriebssystem-Schlüsselbund, der Agent sieht ihn nie. Gas zahlt das Gateway; nötig sind nur USDC/USDT auf Celo Mainnet.
- `satya/purchases.py` erledigt die Satya-Seite:
  1. `SpendPolicy.authorize(quote)` — vor dem Bezahlen: nur https, nur Hosts auf der Erlaubnisliste, nur Celo Mainnet, nur Stablecoins, Limit je Aufruf (Standard 0,05) und je Tag (Standard 1,00).
  2. `PurchaseLedger` — nach dem Bezahlen: Beleg (Dienst, URL, Betrag, Tx-Hash, Zweck) in `purchases.jsonl`; ein Tx-Hash zählt nur einmal; `summary()` liefert die Liste für die Einreichung.
  3. `purchase_as_hint()` — macht aus dem gekauften Signal ein Indiz mit angehängtem Beleg.
- Tests: `tests/test_purchases.py` (16 Tests, lokal grün).

## Ablauf (braucht den Menschen)

1. `buy` einrichten (Wallet im Schlüsselbund) und mit **wenigen Dollar USDC** auf Celo Mainnet füllen. Das erledigt der Mensch; der Agent bekommt keinen Schlüssel.
2. Katalog durchsuchen (lesend): `npx @celo/buy skills search <stichwort>` — aktuelle Version vorher prüfen; in den Unterlagen tauchen 0.7.0 und 0.8.5 auf.
3. Für jeden Kauf **zuerst die Quote ansehen** (`buy_pay_quote`), gegen `SpendPolicy` prüfen, erst dann bezahlen. x402-Zahlungen sind nicht erstattbar; ein 500er kann heißen, dass bezahlt wurde — nicht blind wiederholen.
4. Beleg sofort eintragen: `SATYA_PURCHASES=purchases.jsonl python -m satya.purchases add SERVICE URL BETRAG ASSET eip155:42220 TX ZWECK`.
5. Zur Einreichung: `python -m satya.purchases summary` — liefert Dienste, Hosts, Summe und alle Tx-Hashes.

## Was noch offen ist (ehrlich)

- **Welcher Dienst?** Aus den Unterlagen bekannt sind u. a. „Naira Rates“ (USD/NGN, Preis ca. 0,003–0,01 USAT je Aufruf), X-Suche, LinkedIn-Beiträge und GCP-VMs. Welcher davon **sinnvoll** für Herkunftsprüfung ist, ist nicht belegt. Gewertet wird die Tiefe der Integration und dass Dritte die Dienste betreiben; billiges Massen-Aufrufen zählt nichts. Es braucht mindestens einen Kauf, der Satyas Ergebnis wirklich verbessert und im Pitch erklärbar ist.
- Die Verbindung zwischen Engine und Kauf (Aufruf des Dienstes im Prüfablauf) ist **noch nicht gebaut**; erst wenn der Dienst feststeht.
- Belege werden nur eingetragen, nicht automatisch on-chain gegengeprüft.

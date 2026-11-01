# Technische Quellen für Celo-, Self- und x402-Integration

Recherchestand: 6. Oktober 2026. Die App bleibt auf Celo Sepolia beschränkt.

## Self Agent ID

Quelle: [Self Agent ID Troubleshooting](https://docs.self.xyz/docs/agent-id/troubleshooting/)

Self beschreibt `hasHumanProof(agentId)` als Nachweis, dass eine Zero-Knowledge-Menschenprüfung mit der Agent-ID verbunden ist, und `isProofFresh(agentId)` als aktuelle Gültigkeitsprüfung. Läuft der Nachweis ab, muss der Mensch sich über die Self-App erneut authentifizieren; die Dokumentation nennt als Standard die frühere Grenze aus einem Jahr und Dokumentablauf. Satya prüft die beiden Flags on-chain, versucht aber keine Self-Reauthentifizierung zu imitieren.

Celo-Sepolia-Parameter laut derselben Quelle: Chain ID `11142220`, RPC `https://forno.celo-sepolia.celo-testnet.org`. Die konkrete Agent-ID muss vom Nutzer eingegeben werden; die dApp verlangt zusätzlich, dass die verbundene Wallet `ownerOf(agentId)` entspricht, bevor `declareAsHuman` angeboten wird.

## Celo x402

Quelle: [Celo Docs – x402: Agent Payments](https://docs.celo.org/build-on-celo/build-with-ai/x402)

Die Dokumentation beschreibt die HTTP-402-Abfolge: Ressource zunächst ohne Zahlung anfragen, Zahlungsanforderung lesen, EIP-3009-Autorisierung im Wallet signieren, Request mit Zahlungsheader wiederholen und den Settlement-Beleg erhalten. Der Celo-Facilitator nutzt `https://api.x402.sepolia.celo.org` für Sepolia und unterstützt USDC/USDT. Die `/settle`-Route der gehosteten Variante erfordert laut Dokumentation einen API-Key; der jeweilige Backenddienst bleibt für Abwicklung und Fehlerbehandlung verantwortlich.

Der Satya-Backenddienst dieser Demo liefert aktuell x402 v1 für Celo Sepolia, 0,01 Test-USDC und Asset `0x01C5C0122039549AD1493B8220cABEdD739BC44E`. Die UI übernimmt den Preis und Empfänger dynamisch aus der Antwort, prüft Netzwerk und Tokenadresse und fordert keinen bezahlten Request an, bevor die Wallet den Typed-Data-Schritt freigegeben hat.

## Produktgrenze

Ein Self proof stützt die Identitäts-/Einzigartigkeitsaussage für eine Wallet/Agent-ID. Er macht die konkrete Herkunftsaussage nicht automatisch wahr und ist kein KI-Detektor. Satya zeigt deshalb Registerbehauptungen als solche an.

"use client";

import { useState } from "react";
import { createWalletClient, custom, formatUnits, isAddress, type Address, type Chain, type Hex } from "viem";
import { celoMainnet, celoSepolia, ensureCeloNetwork } from "@/app/lib/celo";
import { getInjectedProvider } from "@/app/components/WalletPanel";

const SEPOLIA_USDC = "0x01C5C0122039549AD1493B8220cABEdD739BC44E" as Address;
const MAINNET_USAT = "0xD2ab3C9A02DBBAB236BfEC45D1d755DF4267F771" as Address;
const MAINNET_X402_ENABLED = process.env.NEXT_PUBLIC_SATYA_MAINNET_X402 === "true";
const paymentTypes = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
  ],
} as const;

type PaymentNetwork = {
  chainId: number;
  chain: Chain;
  aliases: string[];
  token: Address;
  symbol: "USDC" | "USAT";
  label: string;
  explorer: string;
  mainnet: boolean;
};
const PAYMENT_NETWORKS: Record<number, PaymentNetwork> = {
  11142220: {
    chainId: 11142220,
    chain: celoSepolia,
    aliases: ["celo-sepolia", "eip155:11142220"],
    token: SEPOLIA_USDC,
    symbol: "USDC",
    label: "Celo Sepolia · Testnet",
    explorer: "https://celo-sepolia.blockscout.com",
    mainnet: false,
  },
  42220: {
    chainId: 42220,
    chain: celoMainnet,
    aliases: ["celo", "eip155:42220"],
    token: MAINNET_USAT,
    symbol: "USAT",
    label: "Celo Mainnet · echtes Geld",
    explorer: "https://celoscan.io",
    mainnet: true,
  },
};

type X402Accept = {
  scheme: string;
  network: string;
  maxAmountRequired: string;
  resource: string;
  description: string;
  payTo: Address;
  maxTimeoutSeconds?: number;
  asset: Address;
  extra?: { name?: string; version?: string; decimals?: number; symbol?: string; chainId?: number; assetTransferMethod?: string };
};
type X402Quote = { x402Version: number; error?: string; settlementReady?: boolean; accepts?: X402Accept[] };
type Settlement = { settled?: boolean; confirmed?: boolean; transferVerified?: boolean; attributed?: boolean; via?: string; transaction?: string; note?: string };
type PaidResponse = {
  contentHash?: string;
  pruefung?: { urteil?: string; sicher?: boolean; ueberschrift?: string; beweise?: { title?: string; detail?: string }[]; indizien?: { title?: string; detail?: string }[] };
  zahlung?: Settlement;
  error?: string;
};

function friendly(error: unknown) {
  if (error instanceof Error && /rejected|denied|cancelled/i.test(error.message)) return "Wallet-Signatur abgebrochen.";
  return error instanceof Error ? error.message : "x402-Anfrage fehlgeschlagen.";
}

function formFor(text: string, file: File | null) {
  const body = new FormData();
  if (file) body.append("datei", file, file.name);
  else if (text.trim()) body.append("text", text);
  else throw new Error("Gib erst einen Text ein oder wähle eine Datei aus.");
  return body;
}

function resolveNetwork(requirement: X402Accept): PaymentNetwork {
  const chainId = Number(requirement.extra?.chainId);
  const network = PAYMENT_NETWORKS[chainId];
  if (!network || !network.aliases.includes(requirement.network)) {
    throw new Error("Nicht unterstütztes Celo-Netzwerk; es wurde nichts signiert.");
  }
  if (network.mainnet && !MAINNET_X402_ENABLED) {
    throw new Error("Celo-Mainnet-Zahlungen sind in diesem Build deaktiviert; es wurde nichts signiert.");
  }
  if (requirement.asset.toLowerCase() !== network.token.toLowerCase()) {
    throw new Error(`Das Asset ist nicht die freigegebene ${network.symbol}-Adresse; es wurde nichts signiert.`);
  }
  if (requirement.scheme !== "exact" || requirement.extra?.assetTransferMethod !== "eip3009") {
    throw new Error("Der Dienst bietet kein unterstütztes EIP-3009-Zahlungsschema an.");
  }
  if (requirement.extra?.symbol && requirement.extra.symbol !== network.symbol) {
    throw new Error("Asset-Symbol und freigegebene Tokenadresse stimmen nicht überein.");
  }
  if (requirement.extra?.decimals !== 6) throw new Error("Unerwartete Token-Dezimalstellen; es wurde nichts signiert.");
  if (!isAddress(requirement.payTo)) throw new Error("Ungültiger Zahlungsempfänger; es wurde nichts signiert.");
  return network;
}

function approvedPayTo(network: PaymentNetwork): string {
  const raw = network.mainnet
    ? process.env.NEXT_PUBLIC_SATYA_X402_PAY_TO_MAINNET?.trim()
    : process.env.NEXT_PUBLIC_SATYA_X402_PAY_TO_SEPOLIA?.trim();
  if (!raw || !isAddress(raw)) throw new Error("Der Zahlungsempfänger ist nicht lokal freigegeben. Es wurde nichts signiert oder gesendet.");
  return raw.toLowerCase();
}

export default function X402Panel({ text, file }: { text: string; file: File | null }) {
  const [quote, setQuote] = useState<X402Accept | null>(null);
  const [settlementReady, setSettlementReady] = useState(false);
  const [version, setVersion] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<PaidResponse | null>(null);
  const [status, setStatus] = useState("");

  async function getQuote() {
    setBusy(true); setError(""); setReceipt(null); setStatus(""); setQuote(null); setSettlementReady(false);
    try {
      const response = await fetch("/api/x402", { method: "POST", cache: "no-store" });
      const payload = await response.json() as X402Quote;
      if (response.status !== 402) throw new Error(payload.error || `Unerwartete Antwort: HTTP ${response.status}`);
      const requirement = payload.accepts?.[0];
      if (!requirement) throw new Error("Der Prüfdienst hat keine Zahlungsanforderung geliefert.");
      resolveNetwork(requirement);
      setVersion(payload.x402Version || 1);
      setSettlementReady(payload.settlementReady === true);
      setQuote(requirement);
    } catch (e) { setError(friendly(e)); }
    finally { setBusy(false); }
  }

  async function signAndPay() {
    if (!quote) return;
    setBusy(true); setError(""); setReceipt(null); setStatus("");
    try {
      if (!settlementReady) throw new Error("Der Dienst kann die Zahlung nicht sicher abwickeln. Es wurde nichts signiert.");
      const network = resolveNetwork(quote);
      const expectedPayTo = approvedPayTo(network);
      if (quote.payTo.toLowerCase() !== expectedPayTo) {
        throw new Error("Der angebotene Empfänger stimmt nicht mit der lokalen Allowlist überein. Es wurde nichts signiert.");
      }
      const content = formFor(text, file);
      const provider = getInjectedProvider();
      await ensureCeloNetwork(provider, network.chain);
      const accounts = await provider.request({ method: "eth_requestAccounts" }) as string[];
      const account = accounts[0] as Address | undefined;
      if (!account) throw new Error("Wallet hat kein Konto zurückgegeben.");
      const wallet = createWalletClient({ account, chain: network.chain, transport: custom(provider as never) });
      const now = Math.floor(Date.now() / 1000);
      const timeout = Math.min(Math.max(Number(quote.maxTimeoutSeconds || 120), 30), 300);
      const validAfter = String(now - 1);
      const validBefore = String(now + timeout);
      const nonce = `0x${Array.from(crypto.getRandomValues(new Uint8Array(32)), (b) => b.toString(16).padStart(2, "0")).join("")}` as Hex;
      const amount = BigInt(quote.maxAmountRequired);
      if (amount <= 0n) throw new Error("Ungültiger Zahlungsbetrag; nichts wurde signiert.");
      const decimals = quote.extra?.decimals ?? 6;
      const price = formatUnits(amount, decimals);

      setStatus(`Wallet-Signatur angefordert: ${price} ${network.symbol} an ${quote.payTo} auf ${network.label}.`);
      const signature = await wallet.signTypedData({
        account,
        domain: {
          name: quote.extra?.name || network.symbol,
          version: quote.extra?.version || (network.symbol === "USAT" ? "1" : "2"),
          chainId: network.chainId,
          verifyingContract: quote.asset,
        },
        types: paymentTypes,
        primaryType: "TransferWithAuthorization",
        message: {
          from: account,
          to: quote.payTo,
          value: amount,
          validAfter: BigInt(validAfter),
          validBefore: BigInt(validBefore),
          nonce,
        },
      });
      const payment = {
        x402Version: version,
        scheme: quote.scheme,
        network: quote.network,
        payload: { signature, authorization: {
          from: account,
          to: quote.payTo,
          value: amount.toString(),
          validAfter,
          validBefore,
          nonce,
        } },
      };
      setStatus("Autorisierung signiert. Der ausgewählte Inhalt wird nun an den kostenpflichtigen Prüfdienst gesendet.");
      const response = await fetch("/api/x402", {
        method: "POST",
        headers: { "X-PAYMENT": btoa(JSON.stringify(payment)) },
        body: content,
        cache: "no-store",
      });
      const payload = await response.json() as PaidResponse;
      if (!response.ok) throw new Error(payload.error || `Prüfdienst antwortete mit HTTP ${response.status}.`);
      if (payload.zahlung?.settled !== true || payload.zahlung.confirmed !== true || payload.zahlung.transferVerified !== true) {
        throw new Error("Das On-chain-Settlement wurde nicht vollständig bestätigt; Satya zeigt deshalb kein Prüfergebnis.");
      }
      if (network.mainnet && payload.zahlung.attributed !== true) {
        throw new Error("Der Mainnet-Settlement-Beleg enthält keine ERC-8021-Attribution; Satya zeigt deshalb kein Prüfergebnis.");
      }
      setReceipt(payload);
      setQuote(null);
      setStatus("Settlement, erwarteter Token-Transfer und Prüfergebnis bestätigt.");
    } catch (e) { setError(friendly(e)); }
    finally { setBusy(false); }
  }

  const network = quote ? resolveNetwork(quote) : null;
  const decimals = quote?.extra?.decimals ?? 6;
  const price = quote ? formatUnits(BigInt(quote.maxAmountRequired), decimals) : "";
  const payToReady = network ? (() => {
    try { return quote?.payTo.toLowerCase() === approvedPayTo(network); }
    catch { return false; }
  })() : false;

  return <section className="x402-card">
    <div className="card-heading"><span className="step">04</span><div><h2>Erweiterte Prüfung per x402</h2><p>Pay-per-Check für zusätzliche Serveranalyse und Zahlungsbeleg</p></div></div>
    <p className="x402-copy">Die Preisabfrage sendet keinen Inhalt und löst keine Zahlung aus. Erst nach deiner Wallet-Signatur wird die EIP-3009-Autorisierung mit der ausgewählten Datei oder dem Text an den Prüfdienst gesendet. Ein Prüfergebnis erscheint erst nach bestätigtem On-chain-Transfer.</p>
    {!quote && !receipt && <button className="secondary" onClick={getQuote} disabled={busy}>{busy ? "Preis wird abgefragt…" : "Preis unverbindlich anzeigen"}<span>→</span></button>}
    {quote && network && <div className="quote-box">
      <div className="quote-title">ZAHLUNGSANFORDERUNG · x402 V{version}</div>
      <div className="quote-price">{price} <small>{network.symbol} · {network.mainnet ? "Mainnet" : "Testnet"}</small></div>
      <dl><div><dt>Netzwerk</dt><dd>{network.label} · {network.chainId}</dd></div><div><dt>Empfänger</dt><dd className="address-wrap">{quote.payTo}</dd></div><div><dt>Asset</dt><dd className="address-wrap">{quote.asset}</dd></div></dl>
      <p className="quote-content">Prüfungseingabe: {file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : text.trim() ? `Text (${text.trim().length} Zeichen)` : "noch nicht ausgewählt"}</p>
      <p className="quote-warning">{network.mainnet ? "Echte, nicht automatisch rückgängig zu machende Mainnet-Zahlung. Du signierst nur nach sichtbarer Prüfung von Betrag, Token, Netzwerk und freigegebenem Empfänger." : "Testnet-Autorisierung: vor der Freigabe werden Betrag, Token, Netzwerk und Empfänger geprüft."}</p>
      {!settlementReady && <small className="quote-hint">Nur Preisvorschau: Es fehlt eine sichere Settlement-Konfiguration. Die Wallet-Signatur ist gesperrt.</small>}
      {!payToReady && <small className="quote-hint">Wallet-Signatur gesperrt: Der Betreiber muss zuerst genau diesen Empfänger in der Frontend-Allowlist konfigurieren.</small>}
      <button className="primary" onClick={signAndPay} disabled={busy || (!file && !text.trim()) || !payToReady || !settlementReady}>{busy ? "Wallet / Dienst wartet…" : `Wallet öffnen und ${price} ${network.symbol} autorisieren`}<span>↗</span></button>
      {!file && !text.trim() && <small className="quote-hint">Text eingeben oder Datei auswählen, bevor die Wallet-Autorisierung starten kann.</small>}
      <button className="cancel-quote" onClick={() => setQuote(null)} disabled={busy}>Abbrechen</button>
    </div>}
    {status && <p className="inline-status">{status}</p>}{error && <p className="inline-error">{error}</p>}
    {receipt && <div className="paid-result">
      <strong>{receipt.pruefung?.ueberschrift || receipt.pruefung?.urteil || "Satya-Prüfung abgeschlossen"}</strong>
      {receipt.contentHash && <code>{receipt.contentHash}</code>}
      {receipt.pruefung?.sicher === false && <small>Satya markiert dieses Ergebnis nicht als sicher. Ohne passenden kryptografischen Herkunftsnachweis bleibt es unbestimmt.</small>}
      {receipt.pruefung?.beweise?.slice(0, 3).map((item, i) => <p key={`proof-${i}`}><b>{item.title}</b> — {item.detail}</p>)}
      {receipt.pruefung?.indizien?.slice(0, 3).map((item, i) => <p key={`hint-${i}`}><b>{item.title}</b> — {item.detail}</p>)}
      {receipt.zahlung && <p className="settlement">Settlement: bestätigt · {receipt.zahlung.via || "unbekannter Pfad"}</p>}
      {receipt.zahlung?.transaction && <a className="tx-link" href={`${network?.explorer || "https://celoscan.io"}/tx/${receipt.zahlung.transaction.startsWith("0x") ? receipt.zahlung.transaction : `0x${receipt.zahlung.transaction}`}`} target="_blank" rel="noreferrer">Settlement on-chain ansehen ↗</a>}
      {receipt.zahlung?.note && <small>{receipt.zahlung.note}</small>}
    </div>}
    <p className="wallet-footnote">Unterstützt werden nur Celo-Sepolia-USDC und – nach expliziter Betreiberfreigabe – Celo-Mainnet-USA₮. Mainnet bleibt in diesem Build standardmäßig deaktiviert.</p>
  </section>;
}

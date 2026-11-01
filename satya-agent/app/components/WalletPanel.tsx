"use client";

import { useMemo, useState } from "react";
import { createPublicClient, createWalletClient, custom, http, parseAbi, type Address, type Hex } from "viem";
import { withAttribution } from "@celo/attribution-tags";
import { celoSepolia, ensureCeloNetwork, SELF_AGENT_REGISTRY, SATYA_CONTRACT, type Eip1193Provider } from "@/app/lib/celo";

declare global {
  interface Window { ethereum?: Eip1193Provider }
}

const selfAbi = parseAbi([
  "function ownerOf(uint256 tokenId) view returns (address)",
  "function hasHumanProof(uint256 agentId) view returns (bool)",
  "function isProofFresh(uint256 agentId) view returns (bool)",
  "function proofExpiresAt(uint256 agentId) view returns (uint256)",
]);
const satyaAbi = parseAbi([
  "function declareAsHuman(uint256 agentId, bytes32 contentHash, uint8 origin, bytes8 softHash) returns (uint256)",
]);
const publicClient = createPublicClient({ chain: celoSepolia, transport: http() });
const attributionCode = process.env.NEXT_PUBLIC_CELO_ATTRIBUTION_CODE?.trim() || "";
const attributionReady = /^celo_[a-z0-9_]{1,27}$/.test(attributionCode);

export function getInjectedProvider(): Eip1193Provider {
  if (typeof window === "undefined" || !window.ethereum) throw new Error("Keine EVM-Wallet gefunden. Installiere oder öffne MetaMask bzw. eine EIP-1193-kompatible Wallet.");
  return window.ethereum;
}

function message(error: unknown): string {
  if (error instanceof Error) return error.message.replace(/^User rejected the request\./, "Du hast die Wallet-Anfrage abgelehnt.");
  return "Wallet-Aktion fehlgeschlagen.";
}

export default function WalletPanel({ contentHash, onDeclared }: { contentHash: string; onDeclared: (hash: string) => Promise<void> }) {
  const [account, setAccount] = useState<Address | null>(null);
  const [agentId, setAgentId] = useState("");
  const [proof, setProof] = useState<{ owner: Address; owns: boolean; hasProof: boolean; fresh: boolean; expiry: bigint } | null>(null);
  const [origin, setOrigin] = useState<0 | 1>(0);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [txHash, setTxHash] = useState<Hex | null>(null);
  const validHash = /^0x[0-9a-fA-F]{64}$/.test(contentHash);
  const eligible = !!account && !!proof?.owns && proof.hasProof && proof.fresh && validHash;
  const shortAccount = useMemo(() => account ? `${account.slice(0, 6)}…${account.slice(-4)}` : "", [account]);

  async function connect() {
    setBusy(true); setError(""); setStatus("");
    try {
      const provider = getInjectedProvider();
      await ensureCeloNetwork(provider, celoSepolia);
      const accounts = await provider.request({ method: "eth_requestAccounts" }) as string[];
      if (!accounts?.[0]) throw new Error("Wallet hat kein Konto zurückgegeben.");
      setAccount(accounts[0] as Address);
      setProof(null);
      setStatus("Wallet verbunden. Prüfe jetzt deine Self Agent ID.");
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }

  async function checkProof(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setStatus(""); setProof(null); setTxHash(null);
    try {
      if (!account) throw new Error("Verbinde zuerst deine Wallet.");
      if (!/^\d{1,78}$/.test(agentId.trim()) || BigInt(agentId) === 0n) throw new Error("Gib eine gültige positive Agent-ID ein.");
      const id = BigInt(agentId.trim());
      const [owner, hasProof, fresh, expiry] = await Promise.all([
        publicClient.readContract({ address: SELF_AGENT_REGISTRY, abi: selfAbi, functionName: "ownerOf", args: [id] }),
        publicClient.readContract({ address: SELF_AGENT_REGISTRY, abi: selfAbi, functionName: "hasHumanProof", args: [id] }),
        publicClient.readContract({ address: SELF_AGENT_REGISTRY, abi: selfAbi, functionName: "isProofFresh", args: [id] }),
        publicClient.readContract({ address: SELF_AGENT_REGISTRY, abi: selfAbi, functionName: "proofExpiresAt", args: [id] }),
      ]);
      const owns = owner.toLowerCase() === account.toLowerCase();
      setProof({ owner, owns, hasProof, fresh, expiry });
      setStatus(owns && hasProof && fresh ? "Self-Agent-ID gehört zu deiner Wallet; der Menschenbeweis ist aktuell." : "Self-Agent-ID geprüft. Details unten zeigen, welche Voraussetzung fehlt.");
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }

  async function declare() {
    if (!account || !eligible) return;
    setBusy(true); setError(""); setStatus(""); setTxHash(null);
    try {
      if (!attributionReady) throw new Error("ERC-8021-App-Code fehlt oder ist ungültig. Ohne den bestätigten Celo-App-Code wird keine Transaktion gesendet.");
      const provider = getInjectedProvider();
      await ensureCeloNetwork(provider, celoSepolia);
      const chain = String(await provider.request({ method: "eth_chainId" })).toLowerCase();
      if (chain !== `0x${celoSepolia.id.toString(16)}`.toLowerCase()) throw new Error("Wallet ist nicht auf Celo Sepolia.");
      const wallet = createWalletClient({ account, chain: celoSepolia, transport: custom(provider as never) })
        .extend(withAttribution(attributionCode));
      const tx = await wallet.writeContract({
        address: SATYA_CONTRACT,
        abi: satyaAbi,
        functionName: "declareAsHuman",
        args: [BigInt(agentId), contentHash as Hex, origin, "0x0000000000000000"],
      });
      setTxHash(tx);
      setStatus("Transaktion gesendet. Warte auf Celo-Bestätigung…");
      await publicClient.waitForTransactionReceipt({ hash: tx });
      setStatus("On-chain-Erklärung bestätigt.");
      await onDeclared(contentHash);
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }

  return <section className="wallet-card">
    <div className="card-heading"><span className="step">03</span><div><h2>Mit Self bezeugen</h2><p>Eine eigene Aussage on-chain verankern — Wallet-Signatur erforderlich</p></div></div>
    <div className="wallet-intro">Verbinde deine Wallet, prüfe den Self-Menschenbeweis und verankere eine Erklärung zu dem oben gehashten Inhalt. Satya löst keine Transaktion selbst aus.</div>
    {!account ? <button className="secondary" onClick={connect} disabled={busy}>{busy ? "Verbinde…" : "Wallet verbinden"}<span>↗</span></button> : <>
      <div className="connected-row"><span className="pulse"/> {shortAccount}<span className="connected-network">Celo Sepolia</span></div>
      <form className="proof-form" onSubmit={checkProof}>
        <label htmlFor="agent-id">SELF AGENT ID</label>
        <div className="agent-id-row"><input id="agent-id" value={agentId} onChange={(e) => { setAgentId(e.target.value); setProof(null); }} inputMode="numeric" placeholder="z. B. deine Self Agent ID"/><button type="submit" className="secondary" disabled={busy || !agentId.trim()}>Beweis prüfen</button></div>
      </form>
      {proof && <div className="proof-state">
        <div className={proof.owns ? "proof-ok" : "proof-no"}><span>{proof.owns ? "✓" : "×"}</span> Wallet ist Eigentümer</div>
        <div className={proof.hasProof ? "proof-ok" : "proof-no"}><span>{proof.hasProof ? "✓" : "×"}</span> Self-Menschenbeweis vorhanden</div>
        <div className={proof.fresh ? "proof-ok" : "proof-no"}><span>{proof.fresh ? "✓" : "×"}</span> Beweis ist aktuell{proof.expiry > 0n ? ` · gültig bis ${new Date(Number(proof.expiry) * 1000).toLocaleDateString("de-DE")}` : ""}</div>
        <small>Registry-Eigentümer: {proof.owner}</small>
      </div>}
      {proof && <div className="declaration-controls">
        <label htmlFor="origin">DEINE ERKLÄRUNG</label>
        <select id="origin" value={origin} onChange={(e) => setOrigin(Number(e.target.value) as 0 | 1)}>
          <option value={0}>Ohne generative KI erstellt</option>
          <option value={1}>Mit KI-Unterstützung erstellt</option>
        </select>
        <button className="primary" onClick={declare} disabled={busy || !eligible || !attributionReady}>{busy ? "Wallet / Celo wartet…" : "Erklärung in Wallet bestätigen"}<span>↗</span></button>
        {!attributionReady && <small className="quote-hint">Transaktion gesperrt: Setze erst den gültigen ERC-8021-App-Code aus dem Loops-Projekt. Es gibt keinen ungetaggten Fallback.</small>}
        {!validHash && <small>Prüfe zuerst Text, Datei oder Hash; die Erklärung muss an genau diesen Content-Hash gebunden sein.</small>}
      </div>}
    </>}
    {status && <p className="inline-status">{status}</p>}{error && <p className="inline-error">{error}</p>}
    {txHash && <a className="tx-link" href={`https://celo-sepolia.blockscout.com/tx/${txHash}`} target="_blank" rel="noreferrer">Transaktion in Blockscout ↗</a>}
    <p className="wallet-footnote">Self proof-of-humanity verhindert nicht jede Fehl- oder Falschaussage. Deine Erklärung ist signiert und öffentlich, aber bleibt eine Erklärung. Wallet-Writes werden mit dem konfigurierten ERC-8021-App-Code markiert.</p>
  </section>;
}

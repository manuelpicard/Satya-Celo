"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { normalizeSatyaText, SAMPLE_HASH, SATYA_CONTRACT, sha256Hex } from "@/app/lib/celo";
import WalletPanel from "@/app/components/WalletPanel";
import X402Panel from "@/app/components/X402Panel";

type Statement = {
  attester: string;
  timestamp: number;
  origin: string;
  identity: string;
  revoked: boolean;
  disputed: boolean;
  active: boolean;
  agentId: string;
  human: string | null;
};

type Result = {
  hash: string;
  verdict: string;
  summary: { humanOnly: number; humanWithAi: number; aiGenerated: number; inactive: number; contradiction: boolean; provenFraud: boolean };
  statements: Statement[];
  recordCount: number;
  checkedAtBlock: string;
  chain: { name: string; chainId: number; contract: string; explorer: string };
  caveat: string;
};

const verdictCopy: Record<string, { title: string; tone: string; description: string }> = {
  NO_RECORD: { title: "Kein Registereintrag", tone: "neutral", description: "Für diesen Hash gibt es keine Erklärung im Satya-Register. Das sagt nichts darüber aus, ob KI beteiligt war." },
  AI_DECLARED: { title: "Als KI-generiert erklärt", tone: "purple", description: "Mindestens eine aktive On-chain-Erklärung ordnet den Inhalt als KI-generiert ein. Das ist eine überprüfbare Aussage, kein unabhängiger Herkunftsbeweis." },
  HUMAN_DECLARED: { title: "Als ohne KI erklärt", tone: "green", description: "Mindestens eine aktive Erklärung bezeichnet den Inhalt als ohne KI erstellt. Das Register verifiziert die Aussage, nicht ihre faktische Wahrheit." },
  AI_ASSISTED_DECLARED: { title: "Als KI-unterstützt erklärt", tone: "amber", description: "Eine aktive Erklärung sagt aus, dass KI beim Erstellen beteiligt war." },
  DISPUTED: { title: "Widerspruch im Register", tone: "red", description: "Das Register enthält widersprüchliche oder als Betrug nachgewiesene Aussagen." },
  MULTIPLE_DECLARATIONS: { title: "Mehrere Erklärungen", tone: "amber", description: "Es liegen mehrere oder gemischte aktive Erklärungen vor. Bitte Einträge einzeln prüfen." },
};

export default function Home() {
  const [hash, setHash] = useState("");
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function verify(targetHash: string) {
    setLoading(true);
    setError("");
    setResult(null);
    setHash(targetHash);
    try {
      const response = await fetch(`/api/satya?hash=${encodeURIComponent(targetHash)}`, { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prüfung fehlgeschlagen.");
      setResult(data as Result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    let targetHash = hash.trim();
    if (text.trim()) targetHash = await sha256Hex(normalizeSatyaText(text));
    if (!/^0x[0-9a-fA-F]{64}$/.test(targetHash)) {
      setError("Bitte Text eingeben oder einen SHA-256-Hash (0x + 64 Hex-Zeichen) angeben.");
      return;
    }
    await verify(targetHash);
  }

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 50 * 1024 * 1024) {
      setSelectedFile(null);
      setFileName("");
      setHash("");
      setResult(null);
      setError("Datei darf höchstens 50 MB groß sein.");
      return;
    }
    setFileName(file.name);
    setSelectedFile(file);
    setText("");
    setHash("");
    setResult(null);
    setError("");
    const digest = await sha256Hex(await file.arrayBuffer());
    await verify(digest);
  }

  async function loadSample() {
    setLoading(true); setError(""); setResult(null); setHash(""); setText(""); setFileName(""); setSelectedFile(null);
    try {
      const response = await fetch("/demo/ki_gpt_image.png", { cache: "force-cache" });
      if (!response.ok) throw new Error("Das eingebettete Demo-Bild ist nicht erreichbar.");
      const file = new File([await response.blob()], "ki_gpt_image.png", { type: "image/png" });
      const digest = await sha256Hex(await file.arrayBuffer());
      if (digest.toLowerCase() !== SAMPLE_HASH.toLowerCase()) throw new Error("Das Demo-Bild stimmt nicht mit seinem dokumentierten Register-Hash überein.");
      setFileName(file.name); setSelectedFile(file); setHash(digest);
      const checked = await fetch(`/api/satya?hash=${encodeURIComponent(digest)}`, { cache: "no-store" });
      const data = await checked.json();
      if (!checked.ok) throw new Error(data.error || "Prüfung fehlgeschlagen.");
      setResult(data as Result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo-Beispiel konnte nicht geladen werden.");
    } finally { setLoading(false); }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark">स</span><span>satya<span className="brand-dot">.</span></span></a>
        <div className="network"><span className="pulse" /> CELO SEPOLIA <span className="network-id">11142220</span></div>
      </header>

      <section className="hero" id="top">
        <p className="eyebrow">CONTENT PROVENANCE · ON-CHAIN</p>
        <h1>Beweise prüfen.<br /><em>Nicht raten.</em></h1>
        <p className="lead">Satya liest Herkunftserklärungen direkt aus dem Celo-Register. Es erkennt keine KI zuverlässig am Inhalt — es zeigt, wer sich wofür verbürgt.</p>
      </section>

      <section className="workspace">
        <div className="input-card">
          <div className="card-heading"><span className="step">01</span><div><h2>Inhalt prüfen</h2><p>Datei, Text oder vorhandenen SHA-256-Hash eingeben</p></div></div>
          <label className="upload" htmlFor="file"><span className="upload-icon">↑</span><span><strong>{fileName || "Datei auswählen"}</strong><small>bis zu 50 MB · SHA-256 lokal berechnet</small></span><span className="choose">Durchsuchen</span></label>
          <input id="file" className="hidden" type="file" onChange={onFile} />
          <div className="divider"><span>ODER TEXT PRÜFEN</span></div>
          <form onSubmit={onSubmit}>
          <textarea value={text} onChange={(e) => { setText(e.target.value); setFileName(""); setSelectedFile(null); setHash(""); setResult(null); setError(""); }} placeholder="Text hier einfügen. Satya normalisiert ihn nach satya-text-v1, bevor der Hash berechnet wird." rows={4} />
            <div className="hash-row"><label htmlFor="hash">ODER HASH</label><input id="hash" value={hash} onChange={(e) => { setHash(e.target.value); setText(""); setSelectedFile(null); setFileName(""); setResult(null); setError(""); }} placeholder="0x + 64 hexadezimale Zeichen" spellCheck={false} /></div>
            <button className="primary" type="submit" disabled={loading}>{loading ? <><span className="spinner" /> Lese Celo-Register…</> : <>Register prüfen <span>↗</span></>}</button>
          </form>
          <button className="sample" onClick={() => void loadSample()} disabled={loading}>Beispiel laden <span>KI-Bild + echter Hash ↗</span></button>
        </div>

        <div className="result-card" aria-live="polite">
          <div className="card-heading"><span className="step">02</span><div><h2>Registerbefund</h2><p>Direkte Abfrage des Smart Contracts</p></div></div>
          {!result && !loading && !error && <div className="empty"><div className="empty-glyph">⌕</div><p>Noch keine Prüfung</p><small>Hash, Text oder Datei eingeben, um loszulegen.</small></div>}
          {loading && <div className="empty"><span className="spinner large" /><p>Abfrage läuft</p><small>Verbinde mit Celo Sepolia RPC</small></div>}
          {error && <div className="error-box"><strong>Abfrage nicht möglich</strong><p>{error}</p><small>Prüfe die RPC-Erreichbarkeit und versuche es erneut.</small></div>}
          {result && <div className="result-body">
            <div className={`verdict ${verdictCopy[result.verdict]?.tone || "neutral"}`}><span className="verdict-label">{verdictCopy[result.verdict]?.title || result.verdict}</span><p>{verdictCopy[result.verdict]?.description || "Unbekannter Status."}</p></div>
            <div className="summary-grid"><div><strong>{result.recordCount}</strong><span>Einträge</span></div><div><strong>{result.summary.aiGenerated}</strong><span>KI-Erklärungen</span></div><div><strong>{result.summary.humanOnly}</strong><span>Mensch-Erklärungen</span></div></div>
            <div className="hash-display"><span>CONTENT HASH</span><code>{result.hash}</code></div>
            {result.statements.length > 0 && <div className="statements"><h3>Erklärungen</h3>{result.statements.map((s, i) => <article className={`statement ${!s.active ? "inactive" : ""}`} key={`${s.attester}-${i}`}><div className="statement-top"><b>{s.origin.replaceAll("_", " ")}</b><span className={s.active ? "active-tag" : "inactive-tag"}>{s.active ? "AKTIV" : s.disputed ? "WIDERSPROCHEN" : "ZURÜCKGEZOGEN"}</span></div><small>{s.identity.replaceAll("_", " ")} · {new Date(s.timestamp * 1000).toLocaleString("de-DE")}</small><code>{s.attester}</code>{s.agentId !== "0" && <small>Agent-ID: {s.agentId}</small>}</article>)}</div>}
            <p className="caveat">{result.caveat}</p>
            <a className="explorer-link" href={result.chain.explorer} target="_blank" rel="noreferrer">Vertrag in Blockscout ansehen <span>↗</span></a>
            <p className="block-note">Stand: Block {result.checkedAtBlock} · Celo Sepolia</p>
          </div>}
        </div>
      </section>

      <div className="feature-row">
        <WalletPanel contentHash={hash} onDeclared={verify} />
        <X402Panel text={text} file={selectedFile} />
      </div>

      <footer><div><span className="footer-brand">satya.</span><span>Herkunftserklärungen, transparent und überprüfbar.</span></div><a href="https://celo-sepolia.blockscout.com/address/0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001" target="_blank" rel="noreferrer">SatyaCelo Contract ↗</a></footer>
    </main>
  );
}

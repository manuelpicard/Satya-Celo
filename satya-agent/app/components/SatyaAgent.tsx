"use client";

import { useState } from "react";
import { SATYA_CONTRACT, celoSepolia } from "@/app/lib/celo";

export function SatyaAgent() {
  const [hash, setHash] = useState(
    "0xd7c2d77c62016c1038466eb73df60ae1a01ba8ba2755510bdcbedbeb1dab2364"
  );
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const checkContent = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/satya?hash=${hash}`);
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (error) {
      setResult(`Error: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <h1>Satya Agent</h1>
        <p style={{ fontSize: "1.1rem", color: "#aaa", marginBottom: "1rem" }}>
          Verify AI-generated content on Celo
        </p>
        <div style={{ fontSize: "0.9rem", color: "#888" }}>
          <p>Chain: {celoSepolia.name}</p>
          <p>Contract: {SATYA_CONTRACT}</p>
          <p>
            Explorer:{" "}
            <a
              href={`${celoSepolia.blockExplorers?.default.url}/address/${SATYA_CONTRACT}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#667eea", textDecoration: "none" }}
            >
              Blockscout
            </a>
          </p>
        </div>
      </div>

      <div
        style={{
          maxWidth: "800px",
          margin: "0 auto",
          background: "rgba(20, 25, 35, 0.8)",
          padding: "2rem",
          borderRadius: "8px",
          border: "1px solid #333",
        }}
      >
        <h2 style={{ marginBottom: "1rem", color: "#667eea" }}>Check Content</h2>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "0.5rem" }}>
            Content Hash (SHA-256):
          </label>
          <input
            type="text"
            value={hash}
            onChange={(e) => setHash(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>

        <button onClick={checkContent} disabled={loading} style={{ width: "100%" }}>
          {loading ? "Querying..." : "Verify on Celo"}
        </button>

        {result && (
          <div style={{ marginTop: "2rem" }}>
            <h3 style={{ color: "#4caf50", marginBottom: "0.5rem" }}>Result:</h3>
            <pre>{result}</pre>
          </div>
        )}

        <div style={{ marginTop: "2rem", padding: "1rem", background: "rgba(76, 175, 80, 0.1)", borderLeft: "4px solid #4caf50", borderRadius: "4px" }}>
          <h3 style={{ color: "#4caf50", marginBottom: "0.5rem" }}>How it works</h3>
          <ul style={{ marginLeft: "1.5rem" }}>
            <li>Input a content hash (SHA-256 of file or normalized text)</li>
            <li>Query the live Satya registry on Celo Sepolia</li>
            <li>See cryptographic proof: C2PA signatures, human seals, registrations</li>
            <li>Discover Self Agent ID bindings (proof of personhood)</li>
          </ul>
        </div>

        <div style={{ marginTop: "2rem", padding: "1rem", background: "rgba(102, 126, 234, 0.1)", borderLeft: "4px solid #667eea", borderRadius: "4px" }}>
          <h3 style={{ color: "#667eea", marginBottom: "0.5rem" }}>About this hackathon</h3>
          <p>
            <strong>Event:</strong> Celo Agents on Open Rails<br />
            <strong>Tracks:</strong> Content Provenance, Trust & Identity, Payments<br />
            <strong>Prize:</strong> $5,000 CELO<br />
            <a href="https://lu.ma/uk27jw1q" style={{ color: "#667eea", textDecoration: "none" }}>
              Register →
            </a>
          </p>
        </div>
      </div>
    </main>
  );
}

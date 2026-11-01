import { NextRequest, NextResponse } from "next/server";
import { createPublicClient, http } from "viem";
import { celoSepolia } from "@/app/lib/celo";

export const dynamic = "force-dynamic";

const address = (process.env.NEXT_PUBLIC_SATYA_CELO_ADDRESS || process.env.SATYA_CELO_ADDRESS || "0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001") as `0x${string}`;
const rpcUrl = process.env.CELO_RPC_URL || "https://forno.celo-sepolia.celo-testnet.org";
const client = createPublicClient({ chain: celoSepolia, transport: http(rpcUrl) });

const abi = [
  {
    type: "function",
    name: "attestations",
    stateMutability: "view",
    inputs: [{ name: "contentHash", type: "bytes32" }],
    outputs: [{ name: "", type: "tuple[]", components: [
      { name: "attester", type: "address" },
      { name: "at", type: "uint64" },
      { name: "origin", type: "uint8" },
      { name: "via_", type: "uint8" },
      { name: "revoked", type: "bool" },
      { name: "disputed", type: "bool" },
      { name: "agentId", type: "uint256" },
      { name: "nullifier", type: "uint256" },
    ] }],
  },
  {
    type: "function",
    name: "summary",
    stateMutability: "view",
    inputs: [{ name: "contentHash", type: "bytes32" }],
    outputs: [{ name: "", type: "tuple", components: [
      { name: "humanOnly", type: "uint32" },
      { name: "humanWithAi", type: "uint32" },
      { name: "aiGenerated", type: "uint32" },
      { name: "inactive", type: "uint32" },
      { name: "contradiction", type: "bool" },
      { name: "provenFraud", type: "bool" },
    ] }],
  },
] as const;

const originNames = ["HUMAN_ONLY", "HUMAN_WITH_AI", "AI_GENERATED"] as const;
const viaNames = ["SELF_HUMAN", "SELF_AGENT", "AGENT_8004"] as const;

export async function GET(request: NextRequest) {
  const hash = new URL(request.url).searchParams.get("hash")?.toLowerCase();
  if (!hash || !/^0x[0-9a-f]{64}$/.test(hash)) {
    return NextResponse.json({ error: "Bitte einen 32-Byte-SHA-256-Hash im Format 0x… eingeben." }, { status: 400 });
  }

  try {
    const contentHash = hash as `0x${string}`;
    const [rows, summary, blockNumber] = await Promise.all([
      client.readContract({ address, abi, functionName: "attestations", args: [contentHash] }),
      client.readContract({ address, abi, functionName: "summary", args: [contentHash] }),
      client.getBlockNumber(),
    ]);

    const statements = rows.map((row) => ({
      attester: row.attester,
      timestamp: Number(row.at),
      origin: originNames[Number(row.origin)] ?? "UNKNOWN",
      identity: viaNames[Number(row.via_)] ?? "UNKNOWN",
      revoked: row.revoked,
      disputed: row.disputed,
      active: !row.revoked && !row.disputed,
      agentId: row.agentId.toString(),
      human: row.nullifier === 0n ? null : `human:${row.nullifier.toString(16).slice(0, 12)}`,
    }));

    const normalizedSummary = {
      humanOnly: Number(summary.humanOnly),
      humanWithAi: Number(summary.humanWithAi),
      aiGenerated: Number(summary.aiGenerated),
      inactive: Number(summary.inactive),
      contradiction: summary.contradiction,
      provenFraud: summary.provenFraud,
    };

    let verdict = "NO_RECORD";
    if (normalizedSummary.provenFraud || normalizedSummary.contradiction) verdict = "DISPUTED";
    else if (normalizedSummary.aiGenerated > 0 && normalizedSummary.humanOnly === 0 && normalizedSummary.humanWithAi === 0) verdict = "AI_DECLARED";
    else if (normalizedSummary.humanOnly > 0 && normalizedSummary.aiGenerated === 0 && normalizedSummary.humanWithAi === 0) verdict = "HUMAN_DECLARED";
    else if (normalizedSummary.humanWithAi > 0 && normalizedSummary.aiGenerated === 0 && normalizedSummary.humanOnly === 0) verdict = "AI_ASSISTED_DECLARED";
    else if (statements.some((s) => s.active)) verdict = "MULTIPLE_DECLARATIONS";

    return NextResponse.json({
      hash: contentHash,
      verdict,
      summary: normalizedSummary,
      statements,
      recordCount: statements.length,
      checkedAtBlock: blockNumber.toString(),
      chain: { name: "Celo Sepolia", chainId: 11142220, contract: address,
        explorer: `https://celo-sepolia.blockscout.com/address/${address}`,
        transactionSearch: `https://celo-sepolia.blockscout.com/token-transfers?address=${address}` },
      caveat: "Das Register zeigt signierte Erklärungen und deren Widersprüche. Es beweist nicht unabhängig, wer den Inhalt tatsächlich erzeugt hat.",
    }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    console.error("Satya on-chain read failed", error);
    return NextResponse.json({ error: "Celo-Register konnte nicht abgefragt werden.", details: String(error) }, { status: 502 });
  }
}

import { defineChain, type Chain } from "viem";

export const celoSepolia = defineChain({
  id: 11142220,
  name: "Celo Sepolia",
  nativeCurrency: { name: "CELO", symbol: "CELO", decimals: 18 },
  rpcUrls: { default: { http: ["https://forno.celo-sepolia.celo-testnet.org"] } },
  blockExplorers: { default: { name: "Blockscout", url: "https://celo-sepolia.blockscout.com" } },
});

export const celoMainnet = defineChain({
  id: 42220,
  name: "Celo",
  nativeCurrency: { name: "CELO", symbol: "CELO", decimals: 18 },
  rpcUrls: { default: { http: ["https://forno.celo.org"] } },
  blockExplorers: { default: { name: "Celoscan", url: "https://celoscan.io" } },
});

export const SATYA_CONTRACT = (process.env.NEXT_PUBLIC_SATYA_CELO_ADDRESS || "0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001") as `0x${string}`;
export const SELF_AGENT_REGISTRY = "0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379" as const;
export const SAMPLE_HASH = "0xd7c2d77c62016c1038466eb73df60ae1a01ba8ba2755510bdcbedbeb1dab2364";

export interface Eip1193Provider {
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
}

export async function ensureCeloNetwork(provider: Eip1193Provider, chain: Chain): Promise<void> {
  const target = `0x${chain.id.toString(16)}`;
  const current = String(await provider.request({ method: "eth_chainId" })).toLowerCase();
  if (current === target.toLowerCase()) return;
  try {
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: target }] });
  } catch (error) {
    const code = (error as { code?: number })?.code;
    if (code !== 4902) throw error;
    const explorer = chain.blockExplorers?.default.url;
    await provider.request({
      method: "wallet_addEthereumChain",
      params: [{
        chainId: target,
        chainName: chain.name,
        nativeCurrency: chain.nativeCurrency,
        rpcUrls: chain.rpcUrls.default.http,
        ...(explorer ? { blockExplorerUrls: [explorer] } : {}),
      }],
    });
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: target }] });
  }
  const confirmed = String(await provider.request({ method: "eth_chainId" })).toLowerCase();
  if (confirmed !== target.toLowerCase()) throw new Error(`Wallet ist nicht auf ${chain.name}.`);
}

export function normalizeSatyaText(input: string): string {
  return input.normalize("NFC").replace(/\r\n?/g, "\n")
    .replace(/[\u200b\u200c\u200d\u2060-\u2064\ufeff\u00ad\u180e\ufe00-\ufe0f\u{e0000}-\u{e007f}\u{e0100}-\u{e01ef}]/gu, "")
    .split("\n").map((line) => line.replace(/[ \t]+$/g, "")).join("\n").trim();
}

export async function sha256Hex(data: ArrayBuffer | string): Promise<`0x${string}`> {
  const bytes = typeof data === "string" ? new TextEncoder().encode(data) : data;
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return `0x${Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("")}`;
}

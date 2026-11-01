#!/usr/bin/env bash
# Start the Satya service wired to both registers:
#   - Celo Sepolia  : the live provenance register and the x402 paid endpoint
#   - local chain   : the demo register behind the 22-case test corpus
#
#   ./demo/serve.sh [port]
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8000}"

# --- Celo (live) ------------------------------------------------------------
export SATYA_CELO_ADDRESS="${SATYA_CELO_ADDRESS:-0x58d5f2c2ac866D7828b7e2Bf1A3542C3536c3001}"
export CELO_CHAIN_ID="${CELO_CHAIN_ID:-11142220}"
export SATYA_AGENT_ID="${SATYA_AGENT_ID:-453}"

# --- x402 (paid endpoint for agents) ----------------------------------------
export X402_PAY_TO="${X402_PAY_TO:?set X402_PAY_TO to your own payout address}"
export X402_PRICE_USDC="${X402_PRICE_USDC:-0.01}"
# Settlement: a facilitator API key if you have one, otherwise the service
# submits the buyer's own EIP-3009 authorisation and pays the gas.
if [ -z "${X402_API_KEY:-}" ] && [ -z "${X402_SETTLE_KEY:-}" ] && [ -f .secrets/deployer.json ]; then
  X402_SETTLE_KEY="$(python3 -c "import json;print(json.load(open('.secrets/deployer.json'))['data'][0]['private_key'])")"
  export X402_SETTLE_KEY
fi

# --- local demo chain (test corpus) -----------------------------------------
# The demo CA signs the test corpus's camera photo. The UI labels it
# "Satya DEMO"; it must never be trusted outside this demo.
[ -f demo/pki/demo-root.pem ] && export SATYA_DEMO_CA="demo/pki/demo-root.pem"

if [ -f demo/deployment.json ]; then
  SATYA_RPC="$(python3 -c "import json;print(json.load(open('demo/deployment.json'))['rpc'])")"
  SATYA_REGISTRY="$(python3 -c "import json;print(json.load(open('demo/deployment.json'))['registry'])")"
  SATYA_HMN="$(python3 -c "import json;print(json.load(open('demo/deployment.json'))['hmn'])")"
  export SATYA_RPC SATYA_REGISTRY SATYA_HMN SATYA_DEMO_KEYS=1
fi

echo "Celo register : $SATYA_CELO_ADDRESS (chain $CELO_CHAIN_ID)"
echo "x402 price    : $X402_PRICE_USDC USDC -> $X402_PAY_TO"
echo "demo register : ${SATYA_REGISTRY:-none}"
echo "demo CA       : ${SATYA_DEMO_CA:-none}"
exec uvicorn satya.server:app --host 0.0.0.0 --port "$PORT"

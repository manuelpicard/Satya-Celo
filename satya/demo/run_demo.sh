#!/usr/bin/env bash
# Start the complete Satya demo: local chain, contracts, corpus, evaluation, web UI.
# Requirements: Foundry (anvil, forge), Python 3.11 with requirements.txt, ../human-token (Layer 1).
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.foundry/bin:$PATH"

echo "[1/6] Contracts bauen (Schicht 1 + 2)"
(cd ../human-token && forge build >/dev/null)
(cd contracts && forge build >/dev/null)
python3 - <<'EOF'
import json
for src, dst in [("../human-token/out/HumanCredential.sol/HumanCredential.json", "satya/abi/HumanCredential.json"),
                 ("contracts/out/SatyaRegistry.sol/SatyaRegistry.json", "satya/abi/SatyaRegistry.json")]:
    json.dump({"abi": json.load(open(src))["abi"]}, open(dst, "w"))
EOF

echo "[2/6] Lokale Chain starten"
if ! curl -s -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' http://127.0.0.1:8545 >/dev/null; then
  anvil --host 127.0.0.1 --port 8545 --silent &
  sleep 3
fi

echo "[3/6] HMN + Register deployen, Demo-Identitäten anlegen"
python3 demo/seed_chain.py >/dev/null
[ -f demo/pki/demo-root.pem ] || python3 demo/make_demo_ca.py

echo "[4/6] Korpus bauen (KI-Texte werden nur erzeugt, wenn sie fehlen)"
[ -f demo/corpus_src/ki_text_bienen.txt ] || python3 demo/generate_ai_texts.py
python3 demo/build_corpus.py

echo "[5/6] Auswertung"
python3 demo/evaluate.py | tail -24

echo "[6/6] Weboberfläche auf http://0.0.0.0:8000"
export SATYA_RPC=http://127.0.0.1:8545
export SATYA_REGISTRY=$(python3 -c "import json;print(json.load(open('demo/deployment.json'))['registry'])")
export SATYA_DEMO_CA="$PWD/demo/pki/demo-root.pem"
export SATYA_DEMO_KEYS=1
exec python3 -m uvicorn satya.server:app --host 0.0.0.0 --port 8000

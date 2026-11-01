"""x402 payment layer for the Satya verification service on Celo.

The buyer signs an EIP-3009 transfer authorization and retries the HTTP request
with X-PAYMENT. Satya verifies the authorization with Celo's x402 facilitator,
then settles through an explicitly configured path. The paid result is safe to
release only after an on-chain receipt and the expected ERC-20 Transfer log are
confirmed. Mainnet is fail-closed unless the settlement transaction carries a
valid role-based ERC-8021 attribution tag (unless an operator explicitly opts
out, which is not the hackathon-safe default).
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from .attribution import append_role_data_suffix

# --------------------------------------------------------------------- config

NETWORKS: dict[int, dict[str, Any]] = {
    42220: {
        "name": "Celo Mainnet",
        "caip2": "eip155:42220",
        "slug": "celo",
        "facilitator": "https://api.x402.celo.org",
        "rpc": "https://forno.celo.org",
    },
    11142220: {
        "name": "Celo Sepolia",
        "caip2": "eip155:11142220",
        "slug": "celo-sepolia",
        "facilitator": "https://api.x402.sepolia.celo.org",
        "rpc": "https://forno.celo-sepolia.celo-testnet.org",
    },
}

# Exact addresses and EIP-712 domains are taken from the Celo facilitator's
# live /supported response. Only EIP-3009 assets are included here; Permit2
# assets are deliberately not accepted by this narrow payment client.
ASSETS: dict[int, dict[str, dict[str, Any]]] = {
    42220: {
        "USDC": {"asset": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C", "symbol": "USDC", "name": "USDC", "version": "2", "decimals": 6, "assetTransferMethod": "eip3009"},
        "USDT": {"asset": "0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e", "symbol": "USDT", "name": "Tether USD", "version": "1", "decimals": 6, "assetTransferMethod": "eip3009"},
        "USAT": {"asset": "0xD2ab3C9A02DBBAB236BfEC45D1d755DF4267F771", "symbol": "USAT", "name": "Tether America USD", "version": "1", "decimals": 6, "assetTransferMethod": "eip3009"},
    },
    11142220: {
        "USDC": {"asset": "0x01C5C0122039549AD1493B8220cABEdD739BC44E", "symbol": "USDC", "name": "USDC", "version": "2", "decimals": 6, "assetTransferMethod": "eip3009"},
    },
}

ERC8004_REGISTRY = {
    42220: "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    11142220: "0x8004A818BFB912233c491871b3d84c89A494BD9e",
}
SELF_AGENT_REGISTRY = {
    42220: "0xaC3DF9ABf80d0F5c020C06B04Cced27763355944",
    11142220: "0x043DaCac8b0771DD5b444bCC88f2f8BBDBEdd379",
}

X402_VERSION = 1
TRANSFER_WITH_AUTHORIZATION_ABI = [{
    "inputs": [
        {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
        {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"},
        {"name": "v", "type": "uint8"}, {"name": "r", "type": "bytes32"}, {"name": "s", "type": "bytes32"},
    ],
    "name": "transferWithAuthorization", "outputs": [],
    "stateMutability": "nonpayable", "type": "function",
}]
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
_TX_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


class PaymentError(Exception):
    """Raised when an attached payment cannot be accepted or safely settled."""

    def __init__(self, reason: str, status: int = 402):
        super().__init__(reason)
        self.reason = reason
        self.status = status


@dataclass
class X402Config:
    """How the verification service charges for a request."""

    pay_to: str
    chain_id: int = 11142220
    price_usdc: str = "0.01"  # Kept for backward compatibility; symbol is asset_symbol.
    description: str = "Satya content provenance check"
    resource: str = "/api/x402/verify"
    max_timeout_seconds: int = 120
    x402_version: int = X402_VERSION
    asset_symbol: str = "USDC"
    settlement_mode: str = "auto"
    api_key: str | None = field(default=None, repr=False)
    settle_private_key: str | None = field(default=None, repr=False)
    attribution_app_code: str | None = None
    attribution_wallet_code: str | None = None
    allow_untagged_mainnet: bool = False

    def __post_init__(self) -> None:
        self.asset_symbol = self.asset_symbol.upper()
        self.settlement_mode = self.settlement_mode.lower()
        if not _ADDRESS.fullmatch(self.pay_to):
            raise ValueError("X402_PAY_TO must be a 0x-prefixed EVM address")
        if self.chain_id not in NETWORKS:
            raise ValueError(f"unsupported Celo chain id: {self.chain_id}")
        if self.asset_symbol not in ASSETS[self.chain_id]:
            supported = ", ".join(sorted(ASSETS[self.chain_id]))
            raise ValueError(f"unsupported {self.asset_symbol} asset on {self.chain_id}; supported: {supported}")
        if self.x402_version not in (1, 2):
            raise ValueError("X402_VERSION must be 1 or 2")
        if self.settlement_mode not in {"auto", "hosted", "tagged-relayer", "direct-eip3009", "none"}:
            raise ValueError("invalid X402_SETTLEMENT_MODE")
        if self.attribution_app_code and self.attribution_wallet_code:
            # Validate codes at startup, before any payment authorization is requested.
            append_role_data_suffix("0x", self.attribution_app_code, self.attribution_wallet_code)
        _ = self.amount_atomic

    @property
    def network(self) -> dict[str, Any]:
        return NETWORKS[self.chain_id]

    @property
    def asset(self) -> dict[str, Any]:
        return ASSETS[self.chain_id][self.asset_symbol]

    @property
    def amount_atomic(self) -> str:
        try:
            price = Decimal(self.price_usdc)
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("x402 price must be a positive decimal string") from exc
        if not price.is_finite() or price <= 0:
            raise ValueError("x402 price must be a positive finite amount")
        scale = Decimal(10) ** int(self.asset["decimals"])
        atomic = price * scale
        if atomic != atomic.to_integral_value():
            raise ValueError(f"x402 price supports at most {self.asset['decimals']} decimal places")
        return str(int(atomic))

    @property
    def resolved_settlement_mode(self) -> str:
        if self.settlement_mode != "auto":
            return self.settlement_mode
        if self.chain_id == 42220 and self.settle_private_key and self.attribution_app_code and self.attribution_wallet_code:
            return "tagged-relayer"
        if self.api_key:
            return "hosted"
        if self.settle_private_key:
            return "direct-eip3009"
        return "none"

    @property
    def can_accept_paid_requests(self) -> bool:
        mode = self.resolved_settlement_mode
        if mode == "none":
            return False
        if self.chain_id == 42220 and mode != "tagged-relayer" and not self.allow_untagged_mainnet:
            return False
        if mode == "hosted":
            return bool(self.api_key)
        if mode == "tagged-relayer":
            return bool(self.settle_private_key and self.attribution_app_code and self.attribution_wallet_code)
        if mode == "direct-eip3009":
            return bool(self.settle_private_key)
        return False

    @classmethod
    def from_env(cls) -> "X402Config | None":
        pay_to = os.environ.get("X402_PAY_TO")
        if not pay_to:
            return None
        return cls(
            pay_to=pay_to,
            chain_id=int(os.environ.get("CELO_CHAIN_ID", "11142220")),
            price_usdc=os.environ.get("X402_PRICE", os.environ.get("X402_PRICE_USDC", "0.01")),
            asset_symbol=os.environ.get("X402_ASSET_SYMBOL", "USDC"),
            settlement_mode=os.environ.get("X402_SETTLEMENT_MODE", "auto"),
            x402_version=int(os.environ.get("X402_VERSION", X402_VERSION)),
            api_key=os.environ.get("X402_API_KEY") or None,
            settle_private_key=os.environ.get("X402_SETTLE_KEY") or None,
            attribution_app_code=os.environ.get("X402_ATTRIBUTION_APP_CODE") or None,
            attribution_wallet_code=os.environ.get("X402_ATTRIBUTION_WALLET_CODE") or None,
            allow_untagged_mainnet=os.environ.get("X402_ALLOW_UNTAGGED_MAINNET", "").lower() in {"1", "true", "yes"},
        )

    # ------------------------------------------------------------- 402 body

    def payment_required(self, resource: str | None = None) -> dict[str, Any]:
        """The body served with `402 Payment Required`."""
        net = self.network
        asset = self.asset
        return {
            "x402Version": self.x402_version,
            "error": "payment required",
            "accepts": [{
                "scheme": "exact",
                "network": net["slug"] if self.x402_version == 1 else net["caip2"],
                "maxAmountRequired": self.amount_atomic,
                "resource": resource or self.resource,
                "description": self.description,
                "mimeType": "application/json",
                "payTo": self.pay_to,
                "maxTimeoutSeconds": self.max_timeout_seconds,
                "asset": asset["asset"],
                "extra": {
                    "name": asset["name"], "version": asset["version"],
                    "decimals": asset["decimals"], "symbol": asset["symbol"],
                    "assetTransferMethod": asset["assetTransferMethod"], "chainId": self.chain_id,
                },
            }],
        }


# ------------------------------------------------------------------- gateway


class X402Gateway:
    """Verifies and safely settles x402 payments for a Celo resource server."""

    def __init__(self, config: X402Config):
        self.config = config
        self.facilitator = config.network["facilitator"]

    @staticmethod
    def decode_header(header: str) -> dict[str, Any]:
        """`X-PAYMENT` is base64-encoded JSON; some clients send raw JSON."""
        raw = header.strip()
        try:
            decoded = base64.b64decode(raw, validate=True)
            return json.loads(decoded)
        except Exception:
            try:
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise ValueError("payment header must decode to an object")
                return value
            except Exception as exc:  # pragma: no cover - malformed client input
                raise PaymentError(f"malformed X-PAYMENT header: {exc}") from exc

    def requirements(self, resource: str | None = None) -> dict[str, Any]:
        return self.config.payment_required(resource)["accepts"][0]

    async def verify(self, payment: dict[str, Any], resource: str | None = None) -> dict[str, Any]:
        """Ask the Celo facilitator whether the authorization matches the quote."""
        body = {
            "x402Version": payment.get("x402Version", self.config.x402_version),
            "paymentPayload": payment,
            "paymentRequirements": self.requirements(resource),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.facilitator}/verify", json=body)
        if r.status_code != 200:
            raise PaymentError(f"facilitator rejected the payment ({r.status_code}): {r.text[:200]}")
        data = r.json()
        if not data.get("isValid", False):
            raise PaymentError(data.get("invalidReason") or "payment authorization is not valid")
        return data

    async def settle(self, payment: dict[str, Any], resource: str | None = None) -> dict[str, Any]:
        """Settle and confirm the expected on-chain transfer before releasing content."""
        if not self.config.can_accept_paid_requests:
            raise PaymentError("paid endpoint disabled: safe settlement configuration is incomplete", status=503)
        mode = self.config.resolved_settlement_mode
        if mode == "hosted":
            return await self._settle_hosted(payment, resource)
        if mode in {"tagged-relayer", "direct-eip3009"}:
            tagged = mode == "tagged-relayer" or bool(self.config.attribution_app_code and self.config.attribution_wallet_code)
            return await asyncio.to_thread(self._settle_onchain, payment, tagged)
        raise PaymentError("no settlement mode configured", status=503)

    async def _settle_hosted(self, payment: dict[str, Any], resource: str | None) -> dict[str, Any]:
        body = {
            "x402Version": payment.get("x402Version", self.config.x402_version),
            "paymentPayload": payment,
            "paymentRequirements": self.requirements(resource),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.facilitator}/settle", json=body,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
        if r.status_code != 200:
            # Do not retry through another relayer after an uncertain/failed hosted call.
            raise PaymentError(f"settlement failed ({r.status_code}): {r.text[:200]}", status=502)
        data = r.json()
        if not data.get("success", False):
            return {"settled": False, "confirmed": False, "transferVerified": False,
                    "attributed": False, "via": "celo-facilitator", "note": "facilitator did not confirm settlement"}
        tx_hash = self._extract_tx_hash(data)
        if not tx_hash:
            raise PaymentError("facilitator reported success without a transaction hash; result withheld", status=502)
        return await asyncio.to_thread(self._confirm_transaction, tx_hash, payment, "celo-facilitator", False)

    @staticmethod
    def _extract_tx_hash(data: dict[str, Any]) -> str | None:
        for key in ("transaction", "transactionHash", "txHash"):
            value = data.get(key)
            if isinstance(value, dict):
                value = value.get("hash") or value.get("transactionHash")
            if isinstance(value, str) and _TX_HASH.fullmatch(value):
                return value
        return None

    def _authorization(self, payment: dict[str, Any]) -> tuple[dict[str, Any], bytes, int, bytes, bytes]:
        payload = payment.get("payload") or {}
        auth = payload.get("authorization") or {}
        sig = payload.get("signature") or ""
        if not isinstance(auth, dict):
            raise PaymentError("missing EIP-3009 authorization")
        try:
            if auth["to"].lower() != self.config.pay_to.lower():
                raise PaymentError("payment recipient does not match the quoted payTo")
            if int(auth["value"]) != int(self.config.amount_atomic):
                raise PaymentError("payment amount does not match the quoted amount")
            if not _ADDRESS.fullmatch(auth["from"]) or not _ADDRESS.fullmatch(auth["to"]):
                raise PaymentError("invalid EIP-3009 address")
            nonce_hex = auth["nonce"][2:] if auth["nonce"].startswith("0x") else auth["nonce"]
            nonce = bytes.fromhex(nonce_hex)
            sig_hex = sig[2:] if isinstance(sig, str) and sig.startswith("0x") else sig
            sig_bytes = bytes.fromhex(sig_hex)
        except PaymentError:
            raise
        except Exception as exc:
            raise PaymentError(f"malformed EIP-3009 authorization: {exc}") from exc
        if len(nonce) != 32 or len(sig_bytes) != 65:
            raise PaymentError("EIP-3009 nonce must be 32 bytes and signature 65 bytes")
        r_, s_, v_ = sig_bytes[:32], sig_bytes[32:64], sig_bytes[64]
        if v_ < 27:
            v_ += 27
        return auth, nonce, v_, r_, s_

    def _settle_onchain(self, payment: dict[str, Any], tagged: bool) -> dict[str, Any]:
        """Submit EIP-3009 authorization; mainnet mode appends ERC-8021 Schema 2."""
        from eth_account import Account
        from web3 import Web3

        if not self.config.settle_private_key:
            raise PaymentError("relayer key is not configured", status=503)
        if self.config.chain_id == 42220 and not tagged and not self.config.allow_untagged_mainnet:
            raise PaymentError("mainnet settlement requires ERC-8021 role tags", status=503)
        if tagged and not (self.config.attribution_app_code and self.config.attribution_wallet_code):
            raise PaymentError("tagged settlement requires app and wallet attribution codes", status=503)

        auth, nonce, v_, r_, s_ = self._authorization(payment)
        net = self.config.network
        asset = self.config.asset
        w3 = Web3(Web3.HTTPProvider(net["rpc"], request_kwargs={"timeout": 20}))
        if w3.eth.chain_id != self.config.chain_id:
            raise PaymentError("configured RPC returned the wrong Celo chain id", status=503)
        acct = Account.from_key(self.config.settle_private_key)
        token = w3.eth.contract(address=Web3.to_checksum_address(asset["asset"]), abi=TRANSFER_WITH_AUTHORIZATION_ABI)
        fn = token.functions.transferWithAuthorization(
            Web3.to_checksum_address(auth["from"]),
            Web3.to_checksum_address(auth["to"]),
            int(auth["value"]),
            int(auth["validAfter"]),
            int(auth["validBefore"]),
            nonce, v_, r_, s_,
        )
        tx = fn.build_transaction({
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "chainId": self.config.chain_id,
            "gas": 300_000,
            "gasPrice": int(w3.eth.gas_price),
        })
        if tagged:
            tx["data"] = append_role_data_suffix(
                tx["data"], self.config.attribution_app_code, self.config.attribution_wallet_code,
            )
        try:
            estimated = int(w3.eth.estimate_gas(tx))
        except Exception as exc:
            raise PaymentError(f"relayer could not estimate settlement gas: {str(exc)[:160]}", status=502) from exc
        tx["gas"] = max(estimated + estimated // 5, 100_000)
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        tx_hex = Web3.to_hex(tx_hash)
        transfer_ok = receipt.status == 1 and self._receipt_has_expected_transfer(
            Web3, receipt, asset["asset"], auth["from"], auth["to"], int(auth["value"]),
        )
        return {
            "settled": bool(receipt.status == 1 and transfer_ok),
            "confirmed": True,
            "transferVerified": bool(transfer_ok),
            "attributed": bool(tagged),
            "via": "satya-tagged-eip3009-relayer" if tagged else "direct-eip3009-testnet",
            "transaction": tx_hex,
            "network": net["caip2"],
        }

    def _confirm_transaction(self, tx_hash: str, payment: dict[str, Any], via: str,
                             attributed: bool) -> dict[str, Any]:
        """Verify the final receipt and matching token Transfer log over RPC."""
        from web3 import Web3

        if not _TX_HASH.fullmatch(tx_hash):
            raise PaymentError("facilitator returned an invalid transaction hash", status=502)
        auth, _, _, _, _ = self._authorization(payment)
        w3 = Web3(Web3.HTTPProvider(self.config.network["rpc"], request_kwargs={"timeout": 20}))
        if w3.eth.chain_id != self.config.chain_id:
            raise PaymentError("configured RPC returned the wrong Celo chain id", status=503)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        except Exception as exc:
            raise PaymentError(f"settlement receipt is not available; result withheld: {str(exc)[:120]}", status=502) from exc
        verified = receipt.status == 1 and self._receipt_has_expected_transfer(
            Web3, receipt, self.config.asset["asset"], auth["from"], auth["to"], int(auth["value"]),
        )
        return {
            "settled": bool(receipt.status == 1 and verified),
            "confirmed": True,
            "transferVerified": bool(verified),
            "attributed": bool(attributed),
            "via": via,
            "transaction": Web3.to_hex(receipt.transactionHash),
            "network": self.config.network["caip2"],
        }

    @staticmethod
    def _receipt_has_expected_transfer(Web3: Any, receipt: Any, token_address: str,
                                       payer: str, pay_to: str, amount: int) -> bool:
        topic = Web3.keccak(text="Transfer(address,address,uint256)")
        expected_token = token_address.lower()
        expected_from = payer.lower()
        expected_to = pay_to.lower()
        for log in receipt.logs:
            try:
                if Web3.to_checksum_address(log["address"]).lower() != expected_token:
                    continue
                topics = log["topics"]
                if len(topics) < 3 or bytes(topics[0]) != bytes(topic):
                    continue
                from_addr = "0x" + bytes(topics[1])[-20:].hex()
                to_addr = "0x" + bytes(topics[2])[-20:].hex()
                value = int.from_bytes(bytes(log["data"]), "big")
                if from_addr.lower() == expected_from and to_addr.lower() == expected_to and value == amount:
                    return True
            except Exception:
                continue
        return False

    def settlement_is_safe(self, settlement: dict[str, Any]) -> bool:
        """Return true only when the payment is confirmed and the expected transfer exists."""
        if not (settlement.get("settled") is True
                and settlement.get("confirmed") is True
                and settlement.get("transferVerified") is True):
            return False
        if self.config.chain_id == 42220 and not self.config.allow_untagged_mainnet:
            return settlement.get("attributed") is True
        return True

    @staticmethod
    def receipt_header(settlement: dict[str, Any]) -> str:
        return base64.b64encode(json.dumps(settlement, separators=(",", ":")).encode()).decode()


# ----------------------------------------------------------- agent manifest


def agent_card(config: X402Config, satya_address: str, agent_id: int | None) -> dict[str, Any]:
    """ERC-8004 registration file describing the service, served at a stable URL."""
    net = config.network
    registry = ERC8004_REGISTRY[config.chain_id]
    self_registry = SELF_AGENT_REGISTRY[config.chain_id]
    asset = config.asset
    return {
        "name": "Satya",
        "description": (
            "Provenance of record for the agent economy. Answers what accountable origin statement "
            "exists for a content hash. A proof establishes a signed claim, not the truth of the claim."
        ),
        "version": "2.0.0",
        "agentId": agent_id,
        "registrations": [{
            "agentId": agent_id,
            "agentRegistry": f"{net['caip2']}:{registry}",
        }] if agent_id else [],
        "endpoints": [
            {"name": "web", "endpoint": config.resource.rsplit("/api", 1)[0] or "/"},
            {"name": "x402", "endpoint": config.resource,
             "price": {"amount": config.price_usdc, "asset": asset["symbol"],
                       "token": asset["asset"], "network": net["caip2"]}},
        ],
        "trustModels": ["self-agent-id", "erc-8004"],
        "contracts": {
            "satya": f"{net['caip2']}:{satya_address}",
            "selfAgentId": f"{net['caip2']}:{self_registry}",
        },
        "updatedAt": int(time.time()),
    }

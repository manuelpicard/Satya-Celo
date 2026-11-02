"""Spend policy and receipt ledger for services Satya buys from third parties ("Build with buy").

Satya never holds a payment key here. Payments are made by a separate x402 client (e.g. the
Celo `buy` MCP server, whose wallet lives in the OS keychain). This module only
  * decides BEFORE paying whether a quote is acceptable (`SpendPolicy.authorize`),
  * records the proof of payment AFTER paying (`PurchaseLedger`), and
  * turns a purchased signal into evidence of tier HINT - a purchase can never change a verdict.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from .model import Direction, Evidence, Tier

MAINNET = "eip155:42220"
STABLECOINS = {"USDC", "USDT", "USAT"}  # treated 1:1 with USD for spend limits
_TX = re.compile(r"0x[0-9a-fA-F]{64}")


class PurchaseError(ValueError):
    pass


@dataclass(frozen=True)
class Quote:
    """The unpaid 402 offer of a service, as shown by the x402 client before paying."""

    url: str
    amount_atomic: int
    decimals: int
    asset: str  # symbol, e.g. "USDC"
    network: str  # CAIP-2, e.g. "eip155:42220"
    pay_to: str

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or "").lower()

    @property
    def amount(self) -> Decimal:
        return Decimal(self.amount_atomic) / (Decimal(10) ** self.decimals)


@dataclass(frozen=True)
class SpendPolicy:
    allowed_hosts: frozenset[str]
    max_per_call: Decimal = Decimal("0.05")
    max_per_day: Decimal = Decimal("1.00")
    network: str = MAINNET
    assets: frozenset[str] = frozenset(STABLECOINS)

    def authorize(self, quote: Quote, spent_today: Decimal = Decimal(0)) -> tuple[bool, str]:
        if urlparse(quote.url).scheme != "https":
            return False, "service must use https"
        if quote.host not in self.allowed_hosts:
            return False, f"host not on the allowlist: {quote.host or '?'}"
        if quote.network != self.network:
            return False, f"wrong network {quote.network}, expected {self.network}"
        if quote.asset.upper() not in self.assets:
            return False, f"asset {quote.asset} not allowed"
        if quote.amount_atomic <= 0 or quote.decimals < 0:
            return False, "invalid amount"
        if quote.amount > self.max_per_call:
            return False, f"price {quote.amount} exceeds per-call cap {self.max_per_call}"
        if spent_today + quote.amount > self.max_per_day:
            return False, f"daily cap {self.max_per_day} would be exceeded"
        return True, "ok"


@dataclass
class Receipt:
    service: str  # human-readable name, e.g. "naira-rates/usd-ngn"
    url: str
    amount: str  # decimal string in the asset's units
    asset: str
    network: str
    tx_hash: str
    purpose: str  # why Satya bought it
    paid_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    content_hash: str | None = None  # content the purchase was about, if any

    def validate(self) -> None:
        if not _TX.fullmatch(self.tx_hash):
            raise PurchaseError("tx_hash must be a 32-byte 0x hex transaction hash")
        try:
            if Decimal(self.amount) <= 0:
                raise PurchaseError("amount must be positive")
        except InvalidOperation as exc:
            raise PurchaseError("amount must be a decimal number") from exc
        if urlparse(self.url).scheme != "https":
            raise PurchaseError("url must be https")
        if not self.network.startswith("eip155:"):
            raise PurchaseError("network must be a CAIP-2 eip155 id")


class PurchaseLedger:
    """Append-only JSON-lines file of receipts; one tx hash is counted only once."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def receipts(self) -> list[Receipt]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(Receipt(**json.loads(line)))
        return out

    def add(self, receipt: Receipt) -> bool:
        """Record a receipt. Returns False (and writes nothing) if the tx hash is already known."""
        receipt.validate()
        if receipt.tx_hash.lower() in {r.tx_hash.lower() for r in self.receipts()}:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(receipt), ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return True

    def spent_today(self, now: datetime | None = None) -> Decimal:
        today = (now or datetime.now(timezone.utc)).date()
        total = Decimal(0)
        for r in self.receipts():
            if r.asset.upper() in STABLECOINS and datetime.fromisoformat(r.paid_at).date() == today:
                total += Decimal(r.amount)
        return total

    def summary(self) -> dict:
        rs = self.receipts()
        mainnet = [r for r in rs if r.network == MAINNET]
        return {
            "purchases": len(rs),
            "mainnet_purchases": len(mainnet),
            "distinct_services": sorted({r.service for r in mainnet}),
            "distinct_hosts": sorted({urlparse(r.url).hostname or "" for r in mainnet}),
            "total_usd": str(sum((Decimal(r.amount) for r in mainnet if r.asset.upper() in STABLECOINS), Decimal(0))),
            "transactions": [r.tx_hash for r in mainnet],
        }


def purchase_as_hint(receipt: Receipt, title: str, detail: str, data: dict | None = None) -> Evidence:
    """A bought signal is a HINT: displayed, never decisive. The receipt is attached for audit."""
    return Evidence(
        source=f"kauf:{receipt.service}",
        tier=Tier.HINT,
        direction=Direction.NEUTRAL,
        title=title,
        detail=detail,
        issuer=None,
        data={"receipt": asdict(receipt), **(data or {})},
    )


def _cli(argv: list[str]) -> int:
    ledger = PurchaseLedger(os.environ.get("SATYA_PURCHASES", "purchases.jsonl"))
    if argv[:1] == ["summary"]:
        print(json.dumps(ledger.summary(), indent=2))
        return 0
    if argv[:1] == ["add"] and len(argv) == 8:
        service, url, amount, asset, network, tx, purpose = argv[1:]
        added = ledger.add(Receipt(service, url, amount, asset, network, tx, purpose))
        print("recorded" if added else "already recorded")
        return 0
    print("usage: python -m satya.purchases summary | add SERVICE URL AMOUNT ASSET NETWORK TX PURPOSE")
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))

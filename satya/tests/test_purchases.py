from datetime import datetime, timezone
from decimal import Decimal

import pytest

from satya.model import Direction, Tier
from satya.purchases import MAINNET, PurchaseError, PurchaseLedger, Quote, Receipt, SpendPolicy, purchase_as_hint

TX1 = "0x" + "ab" * 32
TX2 = "0x" + "cd" * 32
POLICY = SpendPolicy(allowed_hosts=frozenset({"naira-rate-api.onrender.com"}))


def quote(**kw):
    base = dict(url="https://naira-rate-api.onrender.com/v1/rates", amount_atomic=10_000, decimals=6,
                asset="USAT", network=MAINNET, pay_to="0x" + "11" * 20)
    return Quote(**{**base, **kw})


def receipt(tx=TX1, **kw):
    base = dict(service="naira-rates/usd-ngn", url="https://naira-rate-api.onrender.com/v1/rates",
                amount="0.01", asset="USAT", network=MAINNET, tx_hash=tx, purpose="test")
    return Receipt(**{**base, **kw})


def test_policy_accepts_small_allowlisted_mainnet_stablecoin_quote():
    assert POLICY.authorize(quote()) == (True, "ok")


@pytest.mark.parametrize("kw", [
    dict(url="http://naira-rate-api.onrender.com/x"),      # not https
    dict(url="https://evil.example/x"),                     # not allowlisted
    dict(network="eip155:11142220"),                        # wrong network
    dict(asset="DOGE"),                                     # asset not allowed
    dict(amount_atomic=60_000),                             # 0.06 > per-call cap 0.05
    dict(amount_atomic=0),
])
def test_policy_rejects(kw):
    ok, reason = POLICY.authorize(quote(**kw))
    assert ok is False and reason


def test_policy_daily_cap():
    assert POLICY.authorize(quote(), spent_today=Decimal("0.995"))[0] is False
    assert POLICY.authorize(quote(), spent_today=Decimal("0.5"))[0] is True


def test_ledger_dedups_and_summarises(tmp_path):
    led = PurchaseLedger(tmp_path / "p.jsonl")
    assert led.add(receipt(TX1)) is True
    assert led.add(receipt(TX1)) is False          # same tx counted once
    assert led.add(receipt(TX2, amount="0.003", service="naira-rates/convert")) is True
    s = led.summary()
    assert s["mainnet_purchases"] == 2 and s["total_usd"] == "0.013"
    assert s["distinct_services"] == ["naira-rates/convert", "naira-rates/usd-ngn"]
    assert led.spent_today(datetime.now(timezone.utc)) == Decimal("0.013")


def test_testnet_receipts_are_not_counted_as_mainnet(tmp_path):
    led = PurchaseLedger(tmp_path / "p.jsonl")
    led.add(receipt(network="eip155:11142220"))
    assert led.summary()["mainnet_purchases"] == 0


@pytest.mark.parametrize("kw", [dict(tx_hash="0x1234"), dict(amount="0"), dict(amount="abc"),
                                dict(url="http://x.example/a"), dict(network="solana")])
def test_invalid_receipts_rejected(tmp_path, kw):
    with pytest.raises(PurchaseError):
        PurchaseLedger(tmp_path / "p.jsonl").add(receipt(**kw))


def test_purchase_is_only_a_hint():
    e = purchase_as_hint(receipt(), "Earlier publication found", "d")
    assert e.tier == Tier.HINT and e.direction == Direction.NEUTRAL and e.data["receipt"]["tx_hash"] == TX1

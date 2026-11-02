"""Mainnet x402 policy: no fail-open override; tagging or hosted-facilitator attribution only."""

import pytest

pytest.importorskip("httpx")

from satya.x402 import X402Config, X402Gateway  # noqa: E402

PAY_TO = "0x" + "11" * 20
CODES = {"attribution_app_code": "satya_app", "attribution_wallet_code": "satya_wallet"}


def cfg(chain_id=42220, mode="auto", **kw):
    return X402Config(pay_to=PAY_TO, chain_id=chain_id, settlement_mode=mode, **kw)


def test_override_switch_is_gone():
    assert not hasattr(cfg(), "allow_untagged_mainnet")


def test_mainnet_direct_untagged_relayer_is_refused(monkeypatch):
    monkeypatch.setenv("X402_ALLOW_UNTAGGED_MAINNET", "1")  # must have no effect anymore
    c = cfg(mode="direct-eip3009", settle_private_key="0x" + "22" * 32)
    assert c.can_accept_paid_requests is False
    with pytest.raises(Exception, match="ERC-8021"):
        X402Gateway(c)._settle_onchain({}, tagged=False)


def test_mainnet_tagged_relayer_needs_codes():
    key = "0x" + "22" * 32
    assert cfg(mode="tagged-relayer", settle_private_key=key).can_accept_paid_requests is False
    assert cfg(mode="tagged-relayer", settle_private_key=key, **CODES).can_accept_paid_requests is True


def test_mainnet_hosted_needs_api_key():
    assert cfg(mode="hosted").can_accept_paid_requests is False
    assert cfg(mode="hosted", api_key="k").can_accept_paid_requests is True


def test_settlement_safety_on_mainnet():
    gw = X402Gateway(cfg(mode="hosted", api_key="k"))
    ok = {"settled": True, "confirmed": True, "transferVerified": True}
    assert gw.settlement_is_safe({**ok, "attributed": True, "via": "satya-tagged-eip3009-relayer"})
    assert gw.settlement_is_safe({**ok, "attributed": False, "via": "celo-facilitator"})
    assert not gw.settlement_is_safe({**ok, "attributed": False, "via": "direct-eip3009-testnet"})
    for missing in ("settled", "confirmed", "transferVerified"):
        assert not gw.settlement_is_safe({**ok, missing: False, "attributed": True, "via": "celo-facilitator"})


def test_testnet_unaffected():
    gw = X402Gateway(cfg(chain_id=11142220, mode="direct-eip3009", settle_private_key="0x" + "22" * 32))
    assert gw.config.can_accept_paid_requests is True
    assert gw.settlement_is_safe({"settled": True, "confirmed": True, "transferVerified": True})

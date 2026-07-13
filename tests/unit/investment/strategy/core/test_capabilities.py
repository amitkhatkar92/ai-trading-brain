"""tests/unit/investment/strategy/core/test_capabilities.py
Tests for capabilities, asset/market/timeframe support, and descriptor.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.core import (
    AssetSupport, MarketSupport, StrategyCapability, StrategyDescriptor,
    StrategyVersion, SupportedAssetClass, SupportedExchangeZone,
    SupportedMarketType, SupportedTimeframe, TimeframeSupport, TradingStyle,
)


# ── StrategyVersion ───────────────────────────────────────────────────────────

class TestStrategyVersion:
    def test_str(self):
        v = StrategyVersion(2, 3, 1)
        assert str(v) == "2.3.1"

    def test_from_string(self):
        v = StrategyVersion.from_string("1.2.3")
        assert v.major == 1 and v.minor == 2 and v.patch == 3

    def test_compatibility_same_major(self):
        assert StrategyVersion(1, 0, 0).is_compatible_with(StrategyVersion(1, 5, 2))

    def test_incompatibility_different_major(self):
        assert not StrategyVersion(1, 0, 0).is_compatible_with(StrategyVersion(2, 0, 0))

    def test_default_version(self):
        v = StrategyVersion()
        assert str(v) == "1.0.0"


# ── AssetSupport ──────────────────────────────────────────────────────────────

class TestAssetSupport:
    def test_equity_only_supports_equity(self):
        s = AssetSupport.equity_only()
        assert s.supports(SupportedAssetClass.EQUITY)
        assert not s.supports(SupportedAssetClass.OPTIONS)

    def test_equity_and_options(self):
        s = AssetSupport.equity_and_options()
        assert s.supports(SupportedAssetClass.EQUITY)
        assert s.supports(SupportedAssetClass.OPTIONS)

    def test_all_assets(self):
        s = AssetSupport.all_assets()
        for asset in SupportedAssetClass:
            assert s.supports(asset)

    def test_is_multi_asset_single(self):
        assert not AssetSupport.equity_only().is_multi_asset()

    def test_is_multi_asset_multiple(self):
        assert AssetSupport.equity_and_options().is_multi_asset()

    def test_to_dict(self):
        d = AssetSupport.equity_only().to_dict()
        assert "supported" in d
        assert "equity" in d["supported"]


# ── MarketSupport ─────────────────────────────────────────────────────────────

class TestMarketSupport:
    def test_indian_equity_supports_nse(self):
        m = MarketSupport.indian_equity()
        assert m.supports_exchange(SupportedExchangeZone.NSE)
        assert m.supports_exchange(SupportedExchangeZone.BSE)
        assert not m.supports_exchange(SupportedExchangeZone.NYSE)

    def test_indian_equity_markets(self):
        m = MarketSupport.indian_equity()
        assert m.supports_market(SupportedMarketType.EQUITY_CASH)
        assert not m.supports_market(SupportedMarketType.CRYPTO)

    def test_global_all(self):
        m = MarketSupport.global_all()
        for mtype in SupportedMarketType:
            assert m.supports_market(mtype)

    def test_to_dict_keys(self):
        d = MarketSupport.indian_equity().to_dict()
        assert all(k in d for k in [
            "market_types", "exchange_zones",
            "requires_premarket", "requires_aftermarket",
        ])


# ── TimeframeSupport ──────────────────────────────────────────────────────────

class TestTimeframeSupport:
    def test_intraday_style(self):
        tf = TimeframeSupport.intraday()
        assert tf.supports_style(TradingStyle.INTRADAY)
        assert not tf.supports_style(TradingStyle.LONG_TERM)

    def test_swing_primary(self):
        tf = TimeframeSupport.swing()
        assert tf.primary_timeframe == SupportedTimeframe.D1

    def test_long_term_styles(self):
        tf = TimeframeSupport.long_term()
        assert tf.supports_style(TradingStyle.LONG_TERM)
        assert tf.supports_style(TradingStyle.POSITION)

    def test_to_dict(self):
        d = TimeframeSupport.intraday().to_dict()
        assert "timeframes" in d and "styles" in d
        assert "intraday" in d["styles"]


# ── StrategyDescriptor ────────────────────────────────────────────────────────

class TestStrategyDescriptor:
    def _make(self, **kwargs) -> StrategyDescriptor:
        from .conftest import make_descriptor
        return make_descriptor(**kwargs)

    def test_has_capability(self):
        d = self._make(
            capabilities=frozenset({StrategyCapability.LONG_ONLY})
        )
        assert d.has_capability(StrategyCapability.LONG_ONLY)
        assert not d.has_capability(StrategyCapability.LEVERAGE)

    def test_supports_asset(self):
        d = self._make(
            asset_support=AssetSupport.equity_only()
        )
        assert d.supports_asset(SupportedAssetClass.EQUITY)
        assert not d.supports_asset(SupportedAssetClass.CRYPTO)

    def test_supports_style(self):
        d = self._make()
        assert d.supports_style(TradingStyle.SWING)
        assert not d.supports_style(TradingStyle.INTRADAY)

    def test_supports_exchange(self):
        d = self._make()
        assert d.supports_exchange(SupportedExchangeZone.NSE)
        assert not d.supports_exchange(SupportedExchangeZone.NYSE)

    def test_to_dict_complete(self):
        d = self._make()
        dd = d.to_dict()
        required = [
            "strategy_id", "name", "version", "author", "description",
            "capabilities", "asset_support", "market_support",
            "timeframe_support", "dependencies", "tags", "min_capital",
            "is_experimental", "is_deprecated",
        ]
        for k in required:
            assert k in dd, f"Missing key: {k}"

    def test_immutability(self):
        d = self._make()
        with pytest.raises(Exception):
            d.strategy_id = "new_id"  # type: ignore[misc]

    def test_experimental_flag(self):
        d = self._make(is_experimental=True)
        assert d.is_experimental is True

    def test_deprecated_flag(self):
        d = self._make(is_deprecated=True)
        assert d.is_deprecated is True

    def test_dependencies_tuple(self):
        d = self._make()
        assert isinstance(d.dependencies, tuple)

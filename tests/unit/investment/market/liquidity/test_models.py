"""tests/unit/investment/market/liquidity/test_models.py"""
from __future__ import annotations

import time

import pytest

from iios.investment.market.liquidity.models import (
    VolumeLevel, VolumeTrend, ParticipationBias, EffortResultType,
    LiquidityEventType, VolumeBar, VolumeProfile, ParticipationSnapshot,
    LiquidityProfile, EffortResultAnalysis, OrderFlowSnapshot,
    LiquidityEvent, VolumeLiquiditySnapshot,
)


class TestEnums:
    def test_volume_level_has_8_values(self):
        assert len(VolumeLevel) == 8

    def test_volume_trend_has_5_values(self):
        assert len(VolumeTrend) == 5

    def test_participation_bias_has_5_values(self):
        assert len(ParticipationBias) == 5

    def test_effort_result_type_has_6_values(self):
        assert len(EffortResultType) == 6

    def test_liquidity_event_type_has_10_values(self):
        assert len(LiquidityEventType) == 10

    def test_volume_level_values(self):
        assert VolumeLevel.EXTREME_HIGH.value == "extreme_high"
        assert VolumeLevel.NONE.value == "none"

    def test_volume_trend_values(self):
        assert VolumeTrend.EXPANDING.value == "expanding"
        assert VolumeTrend.DRYING_UP.value == "drying_up"


class TestVolumeBarToDict:
    def test_to_dict_round_trips(self):
        vbar = VolumeBar(
            index=1, timestamp=1700000001.0, volume=150_000.0,
            relative_volume=1.5, normalized_volume=0.6,
            price_change=2.0, price_change_pct=2.0,
            bar_range=3.0, is_up=True, body_pct=0.7,
            close_position=0.75, volume_level=VolumeLevel.HIGH,
        )
        d = vbar.to_dict()
        assert d["index"] == 1
        assert d["volume"] == 150_000.0
        assert d["relative_volume"] == 1.5
        assert d["volume_level"] == "high"
        assert d["is_up"] is True
        assert d["close_position"] == 0.75


class TestVolumeProfileToDict:
    def test_to_dict_round_trips(self):
        vp = VolumeProfile(
            period_bars=20, avg_volume=100_000.0, std_volume=5_000.0,
            median_volume=99_000.0, peak_volume=180_000.0, min_volume=60_000.0,
            recent_avg=105_000.0, volume_trend=VolumeTrend.STABLE,
            up_volume=1_200_000.0, down_volume=800_000.0, up_down_ratio=1.5,
        )
        d = vp.to_dict()
        assert d["period_bars"] == 20
        assert d["volume_trend"] == "stable"
        assert d["up_down_ratio"] == 1.5


class TestParticipationSnapshotToDict:
    def test_has_correct_keys(self):
        ps = ParticipationSnapshot(
            buying_participation=0.65, selling_participation=0.35,
            institutional_participation=0.5, retail_participation=0.5,
            participation_balance=0.3, participation_bias=ParticipationBias.BUY,
            participation_confidence=0.8, participation_score=70.0,
        )
        d = ps.to_dict()
        expected_keys = {
            "buying_participation", "selling_participation",
            "institutional_participation", "retail_participation",
            "participation_balance", "participation_bias",
            "participation_confidence", "participation_score",
        }
        assert expected_keys.issubset(d.keys())
        assert d["participation_bias"] == "buy"


class TestLiquidityProfileToDict:
    def test_has_correct_keys(self):
        lp = LiquidityProfile(
            availability=0.7, stability=0.8, depth=0.6,
            concentration=0.3, fragmentation=0.7,
            quality=70.0, liquidity_confidence=0.75,
        )
        d = lp.to_dict()
        expected_keys = {
            "availability", "stability", "depth",
            "concentration", "fragmentation", "quality", "liquidity_confidence",
        }
        assert expected_keys.issubset(d.keys())


class TestEffortResultAnalysisToDict:
    def test_has_correct_keys(self):
        era = EffortResultAnalysis(
            effort=0.6, result=0.5, ratio=0.83,
            effort_result_type=EffortResultType.CONFIRMED,
            is_confirmed=True, is_divergent=False,
            is_absorption=False, is_climax=False,
            absorption_strength=0.0, climax_score=0.0,
            initiative_buying=True, initiative_selling=False,
            responsive_buying=False, responsive_selling=False,
        )
        d = era.to_dict()
        assert d["effort_result_type"] == "confirmed"
        assert d["is_confirmed"] is True
        assert "initiative_buying" in d


class TestOrderFlowSnapshotToDict:
    def test_has_l2_data_false_by_default(self):
        ofs = OrderFlowSnapshot(
            estimated_buy_volume=70_000.0, estimated_sell_volume=30_000.0,
            estimated_delta=40_000.0, cumulative_delta=40_000.0,
            buy_imbalance=0.7, sell_imbalance=0.3,
            net_imbalance=0.4, aggressive_buying=True, aggressive_selling=False,
        )
        d = ofs.to_dict()
        assert d["has_l2_data"] is False
        assert d["bid_ask_spread"] is None


class TestLiquidityEventToDict:
    def test_to_dict_round_trips(self):
        ev = LiquidityEvent(
            event_type=LiquidityEventType.VOLUME_SPIKE,
            symbol="TEST", timeframe="1d",
            bar_index=5, severity=0.6, description="test",
        )
        d = ev.to_dict()
        assert d["event_type"] == "volume_spike"
        assert d["symbol"] == "TEST"
        assert d["severity"] == 0.6
        assert "event_id" in d


class TestVolumeLiquiditySnapshotToDict:
    def test_has_all_expected_top_level_keys(self):
        snap = VolumeLiquiditySnapshot(symbol="XYZ", timeframe="1d")
        d = snap.to_dict()
        expected_keys = {
            "snapshot_id", "symbol", "timeframe", "bar_index", "timestamp",
            "volume_bar", "volume_profile", "volume_level", "volume_trend",
            "volume_quality", "participation", "liquidity", "effort_result",
            "order_flow", "active_events", "last_event",
            "overall_confidence", "execution_readiness", "liquidity_score",
            "regime", "trend_stage",
        }
        assert expected_keys.issubset(d.keys())

    def test_nested_objects_are_dicts(self):
        snap = VolumeLiquiditySnapshot(symbol="XYZ", timeframe="1d")
        d = snap.to_dict()
        assert isinstance(d["volume_bar"], dict)
        assert isinstance(d["volume_profile"], dict)
        assert isinstance(d["participation"], dict)
        assert isinstance(d["liquidity"], dict)
        assert isinstance(d["effort_result"], dict)
        assert isinstance(d["order_flow"], dict)

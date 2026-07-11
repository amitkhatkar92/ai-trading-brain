"""tests/unit/investment/market/sector_rotation/test_capital_flow.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.capital_flow_engine import CapitalFlowEngine
from iios.investment.market.sector_rotation.flow_profile import build_flow_profile
from iios.investment.market.sector_rotation.flow_statistics import (
    flow_dispersion,
    top_inflow_sectors,
    top_outflow_sectors,
)
from iios.investment.market.sector_rotation.flow_tracker import FlowTracker
from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
    SecurityData,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


def _sec(r: float, vol: float = 1_200_000, avg_vol: float = 1_000_000) -> SecurityData:
    return SecurityData(
        symbol="X", return_pct=r, sector="IT", industry="Software",
        volume=vol, avg_volume_20d=avg_vol,
    )


class TestBuildFlowProfile:
    def test_empty_is_neutral(self):
        p = build_flow_profile("IT", [], 1)
        assert p.flow_type is FlowType.NEUTRAL
        assert p.net_flow_signal == 0.0

    def test_all_advancing_high_volume_is_institutional_buying(self):
        secs = [_sec(0.02, 2_000_000, 1_000_000) for _ in range(5)]
        p = build_flow_profile("IT", secs, 1)
        assert p.net_flow_signal > 0.0
        assert p.flow_type in (FlowType.INSTITUTIONAL_BUYING, FlowType.ACCUMULATION)

    def test_all_declining_high_volume_is_institutional_selling(self):
        secs = [_sec(-0.02, 2_000_000, 1_000_000) for _ in range(5)]
        p = build_flow_profile("IT", secs, 1)
        assert p.net_flow_signal < 0.0
        assert p.flow_type in (FlowType.INSTITUTIONAL_SELLING, FlowType.DISTRIBUTION)

    def test_scores_in_range(self):
        secs = [_sec(0.01), _sec(-0.01), _sec(0.02)]
        p = build_flow_profile("IT", secs, 1)
        assert 0.0 <= p.accumulation_score <= 100.0
        assert 0.0 <= p.distribution_score <= 100.0
        assert -1.0 <= p.net_flow_signal <= 1.0

    def test_intensity_is_abs_net_signal(self):
        secs = [_sec(0.02)] * 4
        p = build_flow_profile("IT", secs, 1)
        assert p.flow_intensity == pytest.approx(abs(p.net_flow_signal), abs=1e-6)


class TestFlowTracker:
    def test_update_returns_profile(self):
        tracker = FlowTracker("IT")
        secs = [_sec(0.02)] * 3
        p = tracker.update(secs, bar_index=1)
        assert p.sector == "IT"

    def test_rolling_net_signal(self):
        tracker = FlowTracker("IT")
        secs_up   = [_sec(0.02, 2_000_000) for _ in range(5)]
        secs_down = [_sec(-0.02, 2_000_000) for _ in range(5)]
        for i in range(5):
            tracker.update(secs_up, bar_index=i)
        signal_up = tracker.rolling_net_signal(5)
        assert signal_up > 0.0

        for i in range(5):
            tracker.update(secs_down, bar_index=i + 5)
        signal_down = tracker.rolling_net_signal(5)
        assert signal_down < 0.0

    def test_dominant_flow_type(self):
        tracker = FlowTracker("IT")
        secs = [_sec(0.03, 2_000_000) for _ in range(5)]
        for i in range(3):
            tracker.update(secs, bar_index=i)
        dom = tracker.dominant_flow_type()
        assert dom in {FlowType.INSTITUTIONAL_BUYING, FlowType.ACCUMULATION}

    def test_history_length(self):
        tracker = FlowTracker("IT")
        for i in range(7):
            tracker.update([_sec(0.01)], bar_index=i)
        assert tracker.history_length() == 7


class TestFlowStatistics:
    def _make_flows(self, signals: dict) -> dict:
        result = {}
        for sector, sig in signals.items():
            result[sector] = CapitalFlowProfile(
                sector=sector, bar_index=1,
                flow_type=FlowType.ACCUMULATION if sig > 0 else FlowType.DISTRIBUTION,
                flow_intensity=abs(sig), volume_ratio=1.0,
                accumulation_score=50.0 + sig * 50.0,
                distribution_score=50.0 - sig * 50.0,
                net_flow_signal=sig,
            )
        return result

    def test_top_inflow_sectors(self):
        flows = self._make_flows({"IT": 0.8, "Utilities": -0.5, "Financials": 0.3})
        top = top_inflow_sectors(flows, n=2)
        assert top[0] == "IT"

    def test_top_outflow_sectors(self):
        flows = self._make_flows({"IT": 0.8, "Utilities": -0.8, "Financials": 0.0})
        out = top_outflow_sectors(flows, n=1)
        assert out[0] == "Utilities"

    def test_flow_dispersion_uniform(self):
        flows = self._make_flows({"A": 0.5, "B": 0.5, "C": 0.5})
        assert flow_dispersion(flows) == pytest.approx(0.0, abs=1e-9)

    def test_flow_dispersion_spread(self):
        flows = self._make_flows({"A": 1.0, "B": -1.0})
        assert flow_dispersion(flows) > 0.5


class TestCapitalFlowEngine:
    def setup_method(self):
        self.taxonomy = SectorTaxonomy()
        self.engine   = CapitalFlowEngine(self.taxonomy)

    def test_update_returns_flows(self, single_snapshot):
        flows = self.engine.update(single_snapshot)
        assert "Information Technology" in flows
        assert "Financials" in flows

    def test_inflow_and_outflow_sectors(self, multi_snapshot_series):
        for snap in multi_snapshot_series:
            self.engine.update(snap)
        inflow  = self.engine.inflow_sectors(2)
        outflow = self.engine.outflow_sectors(2)
        assert len(inflow)  == 2
        assert len(outflow) == 2

    def test_defensive_risk_on_flags(self, single_snapshot):
        self.engine.update(single_snapshot)
        # Just verify the methods run without error and return bool
        assert isinstance(self.engine.is_defensive_rotation(), bool)
        assert isinstance(self.engine.is_risk_on_rotation(), bool)

    def test_dispersion_is_float(self, single_snapshot):
        self.engine.update(single_snapshot)
        d = self.engine.dispersion()
        assert isinstance(d, float)
        assert d >= 0.0

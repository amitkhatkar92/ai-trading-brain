"""tests/unit/investment/market/liquidity/test_order_flow_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
from iios.investment.market.liquidity.imbalance_detector import ImbalanceDetector
from iios.investment.market.liquidity.flow_statistics import FlowStatistics
from iios.investment.market.liquidity.order_flow_engine import OrderFlowEngine

from tests.unit.investment.market.liquidity.conftest import make_volume_bar


class TestOrderFlowSnapshotBuilder:
    def setup_method(self):
        self.builder = OrderFlowSnapshotBuilder()

    def test_buy_plus_sell_imbalance_eq_1(self):
        vbar = make_volume_bar(close_position=0.7, volume=100_000.0)
        snap = self.builder.build(vbar, 0.0, 1.5)
        assert abs(snap.buy_imbalance + snap.sell_imbalance - 1.0) < 1e-9

    def test_cumulative_delta_accumulates(self):
        vbar = make_volume_bar(close_position=0.7, volume=100_000.0)
        snap1 = self.builder.build(vbar, 0.0, 1.5)
        snap2 = self.builder.build(vbar, snap1.cumulative_delta, 1.5)
        assert snap2.cumulative_delta == snap1.cumulative_delta + snap1.estimated_delta

    def test_aggressive_buying_high_close_high_vol(self):
        vbar = make_volume_bar(close_position=0.75, relative_volume=1.5, volume=100_000.0)
        snap = self.builder.build(vbar, 0.0, 1.5)
        assert snap.aggressive_buying is True

    def test_aggressive_selling_low_close_high_vol(self):
        vbar = make_volume_bar(close_position=0.2, relative_volume=1.5, volume=100_000.0)
        snap = self.builder.build(vbar, 0.0, 1.5)
        assert snap.aggressive_selling is True

    def test_no_aggressive_buying_low_vol(self):
        vbar = make_volume_bar(close_position=0.75, relative_volume=0.8, volume=100_000.0)
        snap = self.builder.build(vbar, 0.0, 0.8)
        assert snap.aggressive_buying is False

    def test_has_l2_data_false(self):
        vbar = make_volume_bar()
        snap = self.builder.build(vbar, 0.0, 1.0)
        assert snap.has_l2_data is False


class TestImbalanceDetector:
    def test_current_imbalance_in_range(self):
        detector = ImbalanceDetector(window=10)
        for i in range(5):
            vbar = make_volume_bar(index=i, close_position=0.7)
            from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
            builder = OrderFlowSnapshotBuilder()
            snap = builder.build(vbar, 0.0, 1.5)
            detector.update(snap)
        imb = detector.current_imbalance()
        assert -1.0 <= imb <= 1.0

    def test_persistent_buy_pressure(self):
        from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
        builder = OrderFlowSnapshotBuilder()
        detector = ImbalanceDetector(window=10)
        for i in range(5):
            # High close_position = net_imbalance > 0.3
            vbar = make_volume_bar(index=i, close_position=0.85)
            snap = builder.build(vbar, 0.0, 1.5)
            detector.update(snap)
        assert detector.has_persistent_buy_pressure(threshold=0.3) is True

    def test_persistent_sell_pressure(self):
        from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
        builder = OrderFlowSnapshotBuilder()
        detector = ImbalanceDetector(window=10)
        for i in range(5):
            vbar = make_volume_bar(index=i, close_position=0.1)
            snap = builder.build(vbar, 0.0, 1.5)
            detector.update(snap)
        assert detector.has_persistent_sell_pressure(threshold=0.3) is True

    def test_imbalance_strength_non_negative(self):
        detector = ImbalanceDetector(window=10)
        assert detector.imbalance_strength() >= 0.0


class TestFlowStatistics:
    def test_record_increments_count(self):
        stats = FlowStatistics()
        from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
        builder = OrderFlowSnapshotBuilder()
        for i in range(5):
            vbar = make_volume_bar(index=i)
            snap = builder.build(vbar, 0.0, 1.0)
            stats.record(snap)
        s = stats.stats()
        assert s.total_bars == 5

    def test_stats_has_correct_types(self):
        stats = FlowStatistics()
        s = stats.stats()
        assert isinstance(s.total_bars, int)
        assert isinstance(s.avg_buy_imbalance, float)

    def test_reset(self):
        stats = FlowStatistics()
        from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
        builder = OrderFlowSnapshotBuilder()
        snap = builder.build(make_volume_bar(), 0.0, 1.0)
        stats.record(snap)
        stats.reset()
        assert stats.stats().total_bars == 0


class TestOrderFlowEngine:
    def test_update_returns_snapshot(self):
        engine = OrderFlowEngine(window=20)
        vbar = make_volume_bar()
        snap = engine.update(vbar, 1.0)
        assert snap is not None

    def test_cumulative_delta_updates(self):
        engine = OrderFlowEngine(window=20)
        vbar = make_volume_bar(close_position=0.7, volume=100_000.0)
        engine.update(vbar, 1.0)
        delta1 = engine.cumulative_delta()
        engine.update(vbar, 1.0)
        delta2 = engine.cumulative_delta()
        assert delta2 != delta1

    def test_reset_cumulative_delta(self):
        engine = OrderFlowEngine(window=20)
        engine.update(make_volume_bar(), 1.0)
        engine.reset_cumulative_delta()
        assert engine.cumulative_delta() == 0.0

    def test_connect_l2_feed_no_crash(self, caplog):
        import logging
        engine = OrderFlowEngine(window=20)
        with caplog.at_level(logging.INFO):
            engine.connect_l2_feed(None)
        assert any("L2" in msg for msg in caplog.messages)

    def test_initialize_bulk(self):
        engine = OrderFlowEngine(window=20)
        vbars = [make_volume_bar(index=i) for i in range(20)]
        snap = engine.initialize(vbars)
        assert snap is not None

    def test_current_none_before_update(self):
        engine = OrderFlowEngine(window=20)
        assert engine.current() is None

    def test_current_after_update(self):
        engine = OrderFlowEngine(window=20)
        engine.update(make_volume_bar(), 1.0)
        assert engine.current() is not None

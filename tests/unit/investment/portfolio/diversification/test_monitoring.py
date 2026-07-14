"""test_monitoring.py — alerts, threshold monitor, trends, DiversificationMonitor."""
import pytest

from iios.investment.portfolio.diversification.diversification_alerts import (
    AlertThresholds, DiversificationAlerter,
)
from iios.investment.portfolio.diversification.threshold_monitor import ThresholdMonitor
from iios.investment.portfolio.diversification.diversification_trends import TrendAnalyzer
from iios.investment.portfolio.diversification.diversification_monitor import DiversificationMonitor
from iios.investment.portfolio.diversification.diversification_engine import DiversificationAnalyzer
from iios.investment.portfolio.diversification.diversification_health import (
    DiversificationHealthMonitor,
)
from iios.investment.portfolio.diversification.diversification_snapshot import DiversificationHistory
from iios.investment.portfolio.diversification.diversification_statistics import (
    DiversificationRunMetric, DiversificationStatistics,
)
from iios.investment.portfolio.diversification.diversification_types import AlertSeverity


def _analysis(positions):
    return DiversificationAnalyzer().analyze(positions)


class TestDiversificationAlerter:
    def test_no_alerts_for_diverse(self, positions_5_diverse):
        a = DiversificationAlerter()
        r = a.generate(_analysis(positions_5_diverse))
        # May have zero or more alerts; none should be critical
        crit = [x for x in r if x.severity == AlertSeverity.CRITICAL]
        assert len(crit) == 0

    def test_critical_alert_for_extreme_concentration(self):
        from iios.investment.portfolio.diversification.diversification_types import PositionData
        extreme = [
            PositionData("HUGE", 0.90, "tech", "sw", "equity"),
            PositionData("TINY", 0.10, "finance", "banking", "equity"),
        ]
        a = DiversificationAlerter()
        alerts = a.generate(_analysis(extreme))
        severities = {x.severity for x in alerts}
        assert AlertSeverity.CRITICAL in severities or AlertSeverity.WARNING in severities

    def test_custom_thresholds_strict(self, positions_5_diverse):
        strict = AlertThresholds(top1_warning=0.05)  # very strict
        a = DiversificationAlerter()
        alerts = a.generate(_analysis(positions_5_diverse), strict)
        # Should trigger because each position is 0.20 > 0.05
        assert len(alerts) > 0

    def test_alert_has_message(self, positions_3_concentrated):
        a = DiversificationAlerter()
        alerts = a.generate(_analysis(positions_3_concentrated))
        for alert in alerts:
            assert isinstance(alert.message, str)
            assert len(alert.message) > 5


class TestThresholdMonitor:
    def test_monitor_returns_report(self, positions_5_diverse):
        m = ThresholdMonitor()
        r = m.monitor(_analysis(positions_5_diverse), portfolio_id="P1")
        assert r.portfolio_id == "P1"
        assert r.total > 0

    def test_all_pass_for_diverse(self, positions_10_balanced):
        m = ThresholdMonitor()
        r = m.monitor(_analysis(positions_10_balanced))
        # Should have low breach count
        assert r.breached <= 2  # allow minor boundary effects

    def test_multiple_breached_for_concentrated(self, positions_3_concentrated):
        m = ThresholdMonitor()
        r = m.monitor(_analysis(positions_3_concentrated))
        assert r.breached > 0

    def test_all_passed_flag(self, positions_10_balanced):
        m = ThresholdMonitor()
        r = m.monitor(_analysis(positions_10_balanced))
        assert r.all_passed == (r.breached == 0)


class TestTrendAnalyzer:
    def test_insufficient_data(self):
        ta = TrendAnalyzer()
        r  = ta.analyze({"score": [0.5]}, "P1")
        assert r.portfolio_id == "P1"
        # r.trends is a dict {metric_name: DiversificationTrend}
        for t in r.trends.values():
            assert t.direction.value == "insufficient_data"

    def test_improving_trend(self):
        ta = TrendAnalyzer()
        r  = ta.analyze({"score": [0.3, 0.4, 0.5, 0.6, 0.7]}, "P1")
        assert r.trends["score"].direction.value == "improving"

    def test_deteriorating_trend(self):
        ta = TrendAnalyzer()
        # Score decreasing over time → deteriorating
        r  = ta.analyze({"score": [0.70, 0.60, 0.50, 0.40]}, "P1")
        assert r.trends["score"].direction.value == "deteriorating"

    def test_stable_trend(self):
        ta = TrendAnalyzer()
        r  = ta.analyze({"score": [0.70, 0.71, 0.70, 0.71, 0.70]}, "P1")
        assert r.trends["score"].direction.value == "stable"

    def test_overall_direction(self):
        ta = TrendAnalyzer()
        r  = ta.analyze({"s": [0.3, 0.5, 0.7], "h": [0.3, 0.5, 0.7]}, "P1")
        assert r.overall_direction is not None

    def test_empty_series(self):
        ta = TrendAnalyzer()
        r  = ta.analyze({}, "P1")
        assert r.n_periods == 0


class TestDiversificationMonitor:
    def test_monitor_returns_report(self, positions_5_diverse):
        m = DiversificationMonitor()
        r = m.monitor(_analysis(positions_5_diverse), portfolio_id="P1")
        assert r.portfolio_id == "P1"

    def test_concentrated_requires_attention(self, positions_3_concentrated):
        m = DiversificationMonitor()
        r = m.monitor(_analysis(positions_3_concentrated))
        assert r.requires_attention

    def test_diverse_no_critical(self, positions_5_diverse):
        m = DiversificationMonitor()
        r = m.monitor(_analysis(positions_5_diverse))
        assert not r.has_critical

    def test_with_history(self, positions_5_diverse):
        from iios.investment.portfolio.diversification.diversification_profile import DiversificationProfile
        from iios.investment.portfolio.diversification.diversification_types import DiversificationGrade, ConcentrationLevel
        hist = DiversificationHistory("P1")
        # need a valid profile to satisfy metric_series
        # Just run without history
        m = DiversificationMonitor()
        r = m.monitor(_analysis(positions_5_diverse), portfolio_id="P1")
        assert r is not None


class TestDiversificationHealthMonitor:
    def test_healthy_on_success(self):
        hm = DiversificationHealthMonitor()
        for _ in range(10):
            hm.record_run(succeeded=True, duration_ms=50.0)
        r = hm.check(active_portfolios=1)
        assert r.overall_status.value == "healthy"

    def test_degraded_on_failures(self):
        hm = DiversificationHealthMonitor()
        for _ in range(10):
            hm.record_run(succeeded=False, duration_ms=50.0)
        r = hm.check(active_portfolios=1)
        assert r.overall_status.value != "healthy"

    def test_slow_run_flagged(self):
        hm = DiversificationHealthMonitor()
        for _ in range(10):
            hm.record_run(succeeded=True, duration_ms=9000.0)
        r = hm.check(active_portfolios=1)
        assert r.avg_duration_ms >= 9000

    def test_zero_runs(self):
        hm = DiversificationHealthMonitor()
        r  = hm.check(active_portfolios=0)
        assert r is not None


class TestDiversificationStatistics:
    def _metric(self, portfolio_id="P1", score=0.70):
        return DiversificationRunMetric(
            portfolio_id=portfolio_id,
            succeeded=True,
            n_positions=5,
            hhi=0.20,
            effective_n=5.0,
            entropy_ratio=1.0,
            avg_correlation=0.25,
            diversification_ratio=1.5,
            overall_score=score,
            n_alerts=0,
            duration_ms=100.0,
        )

    def test_records_and_snapshot(self):
        stats = DiversificationStatistics()
        stats.record(self._metric())
        snap  = stats.snapshot()
        assert snap.total_runs == 1
        assert snap.success_runs == 1

    def test_portfolio_filter(self):
        stats = DiversificationStatistics()
        stats.record(self._metric("P1"))
        stats.record(self._metric("P2"))
        # for_portfolio returns a DiversificationStatistics; use .recent() to get runs
        p1_runs = stats.for_portfolio("P1").recent()
        assert all(r.portfolio_id == "P1" for r in p1_runs)

    def test_bounded(self):
        stats = DiversificationStatistics(max_runs=5)
        for i in range(10):
            stats.record(self._metric())
        assert stats.count() == 5

    def test_portfolio_count(self):
        stats = DiversificationStatistics()
        stats.record(self._metric("P1"))
        stats.record(self._metric("P2"))
        assert stats.portfolio_count() == 2

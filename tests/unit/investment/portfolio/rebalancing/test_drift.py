"""test_drift.py — allocation, risk, exposure, drift engine."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    AllocationDrift,
    DriftEngine,
    DriftLevel,
    DriftReport,
    DriftStatistics,
    ExposureDrift,
    RiskDrift,
    compute_allocation_drift,
    compute_exposure_drift,
    compute_risk_drift,
)


# ---------------------------------------------------------------------------
# AllocationDrift
# ---------------------------------------------------------------------------

class TestAllocationDrift:
    def test_no_drift(self, balanced_current, balanced_target):
        result = compute_allocation_drift(balanced_current, balanced_target, "PF1")
        assert abs(result.total_abs_drift) < 1e-9
        assert result.drift_level == DriftLevel.NONE
        assert result.rebalance_recommended is False

    def test_significant_drift(self, drifted_current, drifted_target):
        result = compute_allocation_drift(drifted_current, drifted_target, "PF2")
        assert result.total_abs_drift > 0.10
        assert result.drift_level in (DriftLevel.SIGNIFICANT, DriftLevel.CRITICAL)
        assert result.rebalance_recommended is True

    def test_new_positions_detected(self, diverse_current, diverse_target):
        # WIPRO in target but not in current
        result = compute_allocation_drift(diverse_current, diverse_target, "PF3")
        assert result.n_new_positions >= 1

    def test_exit_positions_detected(self, diverse_current, diverse_target):
        # DRREDDY in current but not in target
        result = compute_allocation_drift(diverse_current, diverse_target, "PF3")
        assert result.n_exit_positions >= 1

    def test_frozen(self, balanced_current, balanced_target):
        result = compute_allocation_drift(balanced_current, balanced_target, "PF")
        with pytest.raises((TypeError, AttributeError)):
            result.total_abs_drift = 99.0  # type: ignore

    def test_result_id_unique(self, balanced_current, balanced_target):
        r1 = compute_allocation_drift(balanced_current, balanced_target, "PF")
        r2 = compute_allocation_drift(balanced_current, balanced_target, "PF")
        assert r1.result_id != r2.result_id

    def test_portfolio_id_preserved(self, balanced_current, balanced_target):
        result = compute_allocation_drift(balanced_current, balanced_target, "MY_PF")
        assert result.portfolio_id == "MY_PF"

    def test_position_drift_tuple(self, drifted_current, drifted_target):
        result = compute_allocation_drift(drifted_current, drifted_target, "PF")
        assert isinstance(result.position_drifts, tuple)
        assert len(result.position_drifts) > 0

    def test_empty_positions(self):
        result = compute_allocation_drift([], [], "PF")
        assert result.total_abs_drift == 0.0
        assert result.n_positions_current == 0


# ---------------------------------------------------------------------------
# RiskDrift
# ---------------------------------------------------------------------------

class TestRiskDrift:
    def test_no_risk_drift(self, balanced_current, balanced_target):
        result = compute_risk_drift(balanced_current, balanced_target, "PF")
        assert result.abs_risk_drift < 0.05  # small since both are default 0.5

    def test_frozen(self, balanced_current, balanced_target):
        result = compute_risk_drift(balanced_current, balanced_target, "PF")
        with pytest.raises((TypeError, AttributeError)):
            result.current_risk = 99.0  # type: ignore

    def test_result_id_unique(self, balanced_current, balanced_target):
        r1 = compute_risk_drift(balanced_current, balanced_target, "PF")
        r2 = compute_risk_drift(balanced_current, balanced_target, "PF")
        assert r1.result_id != r2.result_id

    def test_requires_rebalance_high_risk(self):
        from iios.investment.portfolio.rebalancing import CurrentPosition, TargetPosition
        high_risk = [
            CurrentPosition("X", 0.5, risk_score=0.9),
            CurrentPosition("Y", 0.5, risk_score=0.9),
        ]
        target = [
            TargetPosition("X", 0.5, risk_score=0.3),
            TargetPosition("Y", 0.5, risk_score=0.3),
        ]
        result = compute_risk_drift(high_risk, target, "PF")
        assert result.abs_risk_drift > 0.30


# ---------------------------------------------------------------------------
# ExposureDrift
# ---------------------------------------------------------------------------

class TestExposureDrift:
    def test_no_exposure_drift(self, balanced_current, balanced_target):
        result = compute_exposure_drift(balanced_current, balanced_target, "PF")
        assert isinstance(result, ExposureDrift)
        assert len(result.sector_drifts) > 0

    def test_sector_drift_detected(self, drifted_current, drifted_target):
        result = compute_exposure_drift(drifted_current, drifted_target, "PF")
        assert result.max_sector_drift >= 0.0

    def test_all_bucket_types(self, diverse_current, diverse_target):
        result = compute_exposure_drift(diverse_current, diverse_target, "PF")
        assert isinstance(result.sector_drifts, tuple)
        assert isinstance(result.country_drifts, tuple)

    def test_frozen(self, balanced_current, balanced_target):
        result = compute_exposure_drift(balanced_current, balanced_target, "PF")
        with pytest.raises((TypeError, AttributeError)):
            result.max_sector_drift = 99.0  # type: ignore


# ---------------------------------------------------------------------------
# DriftStatistics
# ---------------------------------------------------------------------------

class TestDriftStatistics:
    def test_empty_snapshot(self):
        ds = DriftStatistics()
        snap = ds.snapshot()
        assert snap.n_observations == 0

    def test_record_and_snapshot(self, drifted_current, drifted_target):
        ds = DriftStatistics()
        drift = compute_allocation_drift(drifted_current, drifted_target, "PF")
        ds.record(drift)
        snap = ds.snapshot()
        assert snap.n_observations == 1
        assert snap.avg_total_drift > 0.0

    def test_max_observations_bounded(self, balanced_current, balanced_target):
        ds = DriftStatistics(max_observations=5)
        for _ in range(10):
            drift = compute_allocation_drift(balanced_current, balanced_target, "PF")
            ds.record(drift)
        snap = ds.snapshot()
        assert snap.n_observations <= 5

    def test_thread_safety(self, balanced_current, balanced_target):
        import threading
        ds = DriftStatistics()
        drift = compute_allocation_drift(balanced_current, balanced_target, "PF")
        errors = []

        def worker():
            try:
                for _ in range(50):
                    ds.record(drift)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ---------------------------------------------------------------------------
# DriftEngine
# ---------------------------------------------------------------------------

class TestDriftEngine:
    def test_analyze_returns_report(self, drifted_current, drifted_target):
        engine = DriftEngine()
        report = engine.analyze(drifted_current, drifted_target, "PF")
        assert isinstance(report, DriftReport)

    def test_report_frozen(self, balanced_current, balanced_target):
        engine = DriftEngine()
        report = engine.analyze(balanced_current, balanced_target, "PF")
        with pytest.raises((TypeError, AttributeError)):
            report.report_id = "x"  # type: ignore

    def test_rebalance_required_on_drift(self, drifted_current, drifted_target):
        engine = DriftEngine()
        report = engine.analyze(drifted_current, drifted_target, "PF")
        assert report.rebalance_required is True

    def test_no_rebalance_on_balanced(self, balanced_current, balanced_target):
        engine = DriftEngine()
        report = engine.analyze(balanced_current, balanced_target, "PF")
        assert report.rebalance_required is False

    def test_urgency_score_range(self, drifted_current, drifted_target):
        engine = DriftEngine()
        report = engine.analyze(drifted_current, drifted_target, "PF")
        assert 0.0 <= report.urgency_score <= 1.0

    def test_primary_driver_str(self, drifted_current, drifted_target):
        engine = DriftEngine()
        report = engine.analyze(drifted_current, drifted_target, "PF")
        assert isinstance(report.primary_driver, str)

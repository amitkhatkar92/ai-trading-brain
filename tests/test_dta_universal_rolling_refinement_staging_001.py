"""
tests/test_dta_universal_rolling_refinement_staging_001.py
==============================================================
DTA-UNIVERSAL-ROLLING-REFINEMENT-001

Verifies that each of the 5 Track-A (volume-gated) self-learning
modules now computes its evidence requirement via the shared
maturity-staged primitive instead of a bare fixed constant, and that
the EARLY stage (today's real system age) is unchanged from the
pre-existing static floor -- zero behavior change until the system
actually accumulates more real operating history.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import learning_system.rolling_refinement_engine as rre


def _mid_stage_date():
    return date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(
        days=rre.MID_STAGE_THRESHOLD_DAYS + 5,
    )


def _mature_stage_date():
    return date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(
        days=rre.MATURE_STAGE_THRESHOLD_DAYS + 5,
    )


class TestRegimeMapRefinementEngineStaging:
    def test_early_stage_unchanged(self):
        import strategy_lab.regime_map_refinement_engine as mod
        assert mod._effective_min_sample() == mod.MIN_SAMPLE_FOR_VALIDATION == 10

    def test_mid_and_mature_stages_raise_the_bar(self):
        import strategy_lab.regime_map_refinement_engine as mod
        with patch.object(rre, "_today", return_value=_mid_stage_date()):
            assert mod._effective_min_sample() == 30
        with patch.object(rre, "_today", return_value=_mature_stage_date()):
            assert mod._effective_min_sample() == 45

    def test_fails_open_to_static_floor_on_error(self):
        import strategy_lab.regime_map_refinement_engine as mod
        with patch(
            "learning_system.rolling_refinement_engine.get_staged_requirement",
            side_effect=RuntimeError("boom"),
        ):
            assert mod._effective_min_sample() == mod.MIN_SAMPLE_FOR_VALIDATION


class TestStrategyRegimeHealthEngineStaging:
    def test_early_stage_unchanged(self):
        import trade_monitoring.strategy_regime_health_engine as mod
        assert mod._effective_min_sample() == mod.MIN_SAMPLE_FOR_VALIDATION == 10

    def test_mid_and_mature_stages_raise_the_bar(self):
        import trade_monitoring.strategy_regime_health_engine as mod
        with patch.object(rre, "_today", return_value=_mid_stage_date()):
            assert mod._effective_min_sample() == 30
        with patch.object(rre, "_today", return_value=_mature_stage_date()):
            assert mod._effective_min_sample() == 45


class TestSizingBoundsRefinementEngineStaging:
    def test_early_stage_unchanged(self):
        import learning_system.sizing_bounds_refinement_engine as mod
        assert mod._effective_min_sample() == mod.MIN_SAMPLE_FOR_VALIDATION == 30

    def test_mid_and_mature_stages_raise_the_bar(self):
        import learning_system.sizing_bounds_refinement_engine as mod
        with patch.object(rre, "_today", return_value=_mid_stage_date()):
            assert mod._effective_min_sample() == 45
        with patch.object(rre, "_today", return_value=_mature_stage_date()):
            assert mod._effective_min_sample() == 60


class TestStrategyProfileRefinementEngineStaging:
    def test_early_stage_unchanged(self):
        import trade_monitoring.strategy_profile_refinement_engine as mod
        assert mod._effective_min_sample() == mod.MIN_SAMPLE_FOR_AUTO_APPLY == 25

    def test_mid_and_mature_stages_raise_the_bar(self):
        import trade_monitoring.strategy_profile_refinement_engine as mod
        with patch.object(rre, "_today", return_value=_mid_stage_date()):
            assert mod._effective_min_sample() == 40
        with patch.object(rre, "_today", return_value=_mature_stage_date()):
            assert mod._effective_min_sample() == 55


class TestCapitalReserveReadinessEngineStaging:
    def test_readiness_status_reports_staged_requirement(self):
        import analysis.capital_reserve_readiness_engine as mod
        with patch(
            "analysis.rejection_attribution_monitor.get_rejection_attribution_monitor"
        ) as mock_get_monitor:
            mock_get_monitor.return_value.get_reason_reliability.return_value = None
            status = mod.get_readiness_status()
        assert status["min_samples_required"] == mod.MIN_SAMPLES_FOR_READINESS == 30

    def test_mid_stage_raises_the_bar(self):
        import analysis.capital_reserve_readiness_engine as mod
        with patch.object(rre, "_today", return_value=_mid_stage_date()), \
             patch(
                 "analysis.rejection_attribution_monitor.get_rejection_attribution_monitor"
             ) as mock_get_monitor:
            mock_get_monitor.return_value.get_reason_reliability.return_value = None
            status = mod.get_readiness_status()
        assert status["min_samples_required"] == 45

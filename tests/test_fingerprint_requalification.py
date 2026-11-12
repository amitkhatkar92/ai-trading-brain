from datetime import date, timedelta
from unittest.mock import patch

from scripts.knowledge_system import controlled_live_candidates_001 as eligibility
from scripts.knowledge_system.champion_challenger_001 import _consecutive_validated_pass_streak
from scripts.knowledge_system.shadow_challenger_tracker_001 import compute_daily_shadow_entry


def _days(n, start=date(2026, 1, 2), wins=True):
    return [{"trade_date": (start + timedelta(days=i)).isoformat(),
             "challenger_at_least_as_good": wins} for i in range(n)]


def _evaluate(history, days):
    with patch.object(eligibility, "compute_lifecycle_status", return_value={"lifecycle_status": "PASS"}), \
         patch("scripts.knowledge_system.champion_challenger_001.load_registry_history", return_value=history), \
         patch("scripts.knowledge_system.shadow_challenger_tracker_001.load_shadow_history", return_value=days):
        return eligibility.evaluate_live_candidacy("FP", "DOWN")


def test_failure_does_not_permanently_veto_fresh_evidence():
    history = [{"status": "REJECTED", "checked_at": "2026-01-01T18:00:00+00:00"}]
    result = _evaluate(history, _days(10))
    assert result["controlled_live_candidate"]
    assert result["evidence_epoch_after"] == "2026-01-01"
    assert history[0]["status"] == "REJECTED"


def test_old_and_same_day_observations_do_not_requalify():
    history = [{"status": "REJECTED", "checked_at": "2026-01-10T18:00:00"}]
    result = _evaluate(history, _days(10))
    assert not result["controlled_live_candidate"]
    assert result["shadow_days"] == 1


def test_duplicate_trading_date_cannot_manufacture_ten_votes():
    result = _evaluate([], _days(1) * 12)
    assert not result["controlled_live_candidate"]
    assert result["shadow_days"] == 1


def test_later_regression_resets_epoch():
    history = [{"status": "REJECTED", "checked_at": "2026-01-01"},
               {"status": "REJECTED", "checked_at": "2026-01-15"}]
    assert not _evaluate(history, _days(20))["controlled_live_candidate"]


def test_epoch_with_negative_evidence_never_qualifies():
    history = [{"status": "REJECTED", "checked_at": "2026-01-01"}]
    result = _evaluate(history, _days(30, wins=False))
    assert not result["controlled_live_candidate"]
    assert result["review_status"] == "REJECTED_EPOCH"
    fresh = _evaluate(history, _days(30, wins=False) + _days(10, date(2026, 2, 1)))
    assert fresh["controlled_live_candidate"]
    assert fresh["experiment_id"] != result["experiment_id"]


def test_repeat_validation_same_data_does_not_inflate_streak():
    history = [{"as_of_date": "2026-01-01", "validation_verdict": "VALIDATED_PASS"}] * 4
    assert _consecutive_validated_pass_streak(history, "VALIDATED_PASS", "2026-01-01") == 1
    assert _consecutive_validated_pass_streak(history, "VALIDATED_PASS", "2026-01-02") == 2


def test_shadow_thresholds_require_prior_days():
    records = [{"trade_date": "2026-01-01", "direction": "UP", "t1_ret_pct": 5}]
    assert compute_daily_shadow_entry(records, {"name": "FP", "direction": "UP"}, "2026-01-01") is None


def test_pga_does_not_invent_external_event_cause():
    from predictive_gap.pga_analyzer import _classify_was_predictable
    from predictive_gap.pga_collector import DailyData, StockMove
    from predictive_gap.pga_config import PGAConfig
    move = StockMove("ABC", 100, 120, 20, 1000, "GAINER", "UP", "test")
    _, reason = _classify_was_predictable("ABC", move, DailyData("2026-01-01"), PGAConfig())
    assert "UNKNOWN" in reason
    assert "likely ExternalEvent" not in reason

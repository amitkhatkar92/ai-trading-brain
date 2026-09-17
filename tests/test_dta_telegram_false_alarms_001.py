"""
tests/test_dta_telegram_false_alarms_001.py
==============================================
Root-cause fixes for two misleading Telegram messages found while
auditing real production alerts on 2026-09-17:

1. DTA-GOV-VIOLATION-FALSE-ALARM-001: on a zero-trade day, the Daily AI
   Self-Evaluation report showed "Governance Violation: Entry outside
   approved execution window" even though the same message also said
   "No trades executed today — no evaluation possible." Root cause:
   SelfEvalResult's zero-trade early-return path leaves EVERY score
   dimension (governance_compliance included) at its dataclass default
   of 0.0 -- render() only checked `governance_compliance == 0.0`,
   unable to distinguish "nothing was computed" from "a real
   violation was detected".

2. DTA-STABILITY-STALE-READ-001: the same EOD cycle sent "✅ Stability
   Streak: 53/10 BASELINE CONFIRMED" (EOD Summary) followed 4 seconds
   later by "🔄 Stability: Day 0 of 10" (Stability Check) -- both
   individually correct at the instant they were read, but confusing
   and alarming together. Root cause: the EOD Summary read
   `stability_ledger.streak` BEFORE `close_session()` ran (~120 lines
   later in the same function), so it reported yesterday's value; when
   close_session() then found today's session dirty (a real
   BATCH_CORRUPTION_FREEZE flag) and reset the streak, the second
   message correctly showed the new value -- a stale-then-fresh
   ordering issue, not a data bug. Fixed by moving close_session() to
   run once, before either read.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Part A: governance-violation false alarm ──────────────────────────────

class TestGovernanceViolationFalseAlarm:
    def _make_zero_trade_result(self):
        from learning_system.daily_self_evaluation import SelfEvalResult
        return SelfEvalResult(
            date="2026-09-17", overall_score=0.0, grade="N/A",
            learning_notes=["No trades executed today — no evaluation possible."],
        )

    def test_render_suppresses_banner_on_zero_trade_day(self):
        """The exact live bug: zero trades must never show the banner."""
        from learning_system.daily_self_evaluation import DailyAISelfEvaluator
        result = self._make_zero_trade_result()
        assert result.total_trades == 0
        assert result.governance_compliance == 0.0

        rendered = DailyAISelfEvaluator().render(result)
        assert "Governance Violation" not in rendered

    def test_real_violation_still_shown_when_trades_exist(self):
        """Regression guard: a genuine violation (real trades, gc computed
        as 0.0 by _score_governance_compliance) must still be reported."""
        from learning_system.daily_self_evaluation import SelfEvalResult, DailyAISelfEvaluator
        result = SelfEvalResult(
            date="2026-09-17", overall_score=4.0, grade="C",
            total_trades=2, wins=1, losses=1,
            governance_compliance=0.0,
        )
        rendered = DailyAISelfEvaluator().render(result)
        assert "Governance Violation" in rendered

    def test_telegram_html_message_also_suppresses_on_zero_trades(self, monkeypatch):
        from unittest.mock import MagicMock
        from learning_system.daily_self_evaluation import DailyAISelfEvaluator
        import notifications

        result = self._make_zero_trade_result()
        fake_notifier = MagicMock()
        monkeypatch.setattr(notifications, "get_notifier", lambda: fake_notifier)

        DailyAISelfEvaluator().notify(result, "report_text_unused")

        fake_notifier.market_alert.assert_called_once()
        _, msg = fake_notifier.market_alert.call_args[0]
        assert "Governance Violation" not in msg


# ── Part B: stability streak stale-read ordering ──────────────────────────

class TestStabilityCloseSessionOrdering:
    def test_close_session_called_exactly_once_in_eod_learning(self):
        """Source-scan regression guard: close_session() must never be
        called twice in the same EOD cycle (would double-increment or
        double-reset the streak)."""
        src = Path("orchestrator/master_orchestrator.py").read_text(encoding="utf-8")
        start = src.find("def _do_eod_learning")
        end = src.find("\n    def ", start + 10)
        body = src[start:end] if end > start else src[start:]
        assert body.count(".close_session()") == 1

    def test_close_session_runs_before_eod_summary_dispatch(self):
        """The streak read for the EOD Summary notification must happen
        AFTER close_session(), not before it."""
        src = Path("orchestrator/master_orchestrator.py").read_text(encoding="utf-8")
        start = src.find("def _do_eod_learning")
        end = src.find("\n    def ", start + 10)
        body = src[start:end] if end > start else src[start:]

        close_idx = body.find(".close_session()")
        streak_read_idx = body.find("_stab_streak   = _sl.streak")
        eod_summary_idx = body.find("self.notifier.eod_summary(")

        assert close_idx != -1 and streak_read_idx != -1 and eod_summary_idx != -1
        assert close_idx < streak_read_idx < eod_summary_idx

    def test_stability_ledger_close_session_semantics_unchanged(self, tmp_path, monkeypatch):
        """Regression guard on the underlying StabilityLedger itself:
        close_session() still increments on clean / resets on dirty."""
        import learning_system.strategy_performance_tracker as spt
        state_path = tmp_path / "stability_ledger.json"
        monkeypatch.setattr(spt, "STABILITY_FILE", str(state_path))

        ledger = spt.StabilityLedger()
        ledger.streak = 5
        result = ledger.close_session()
        assert result["clean"] is True
        assert ledger.streak == 6

        ledger.flag_session_issue("TEST_ISSUE")
        result2 = ledger.close_session()
        assert result2["clean"] is False
        assert ledger.streak == 0

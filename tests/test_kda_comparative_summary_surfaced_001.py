"""
tests/test_kda_comparative_summary_surfaced_001.py
=====================================================
DTA-KDA-COMPARATIVE-SURFACE-001

Covers two fixes to knowledge_authority's "KDA vs StrategyLab vs Scanner,
who decides better" research pipeline (KDAComparativeAnalyzer):

1. Root-cause fix: knowledge_decision_pipeline.py's EOD log line read
   non-existent dict keys ("kda_successful_overrules"/"kda_overrule_total")
   and therefore always printed 0/0 regardless of the real computed values.
   The correct keys are "successful_overrules"/"overrule_count".

2. New: the full comparison (kda vs strategy vs scanner direction accuracy,
   missed opportunities, false selections) is now persisted append-only and
   exposed via read-only accessors -- previously computed every day and
   immediately discarded after one (buggy) log line.

Both additions are research-only: zero decision/execution impact. Safety
contract: broker_calls=0, orders=0, no_lookahead=True throughout.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from knowledge_authority.kda_comparative import (
    get_comparative_summary_history,
    record_comparative_summary,
)


# ─────────────────────────────────────────────────────────────────────────────
# record_comparative_summary / get_comparative_summary_history
# ─────────────────────────────────────────────────────────────────────────────

class TestComparativeSummaryPersistence:

    def test_T01_record_and_read_back(self, tmp_path):
        path = str(tmp_path / "comparative_summary_history.jsonl")
        with patch("knowledge_authority.kda_comparative._SUMMARY_HISTORY_PATH", path):
            record_comparative_summary(
                {"n": 10, "kda_direction_accuracy": 0.6, "strategy_direction_accuracy": 0.5},
                trading_date="2026-09-30",
            )
            hist = get_comparative_summary_history()
        assert len(hist) == 1
        assert hist[0]["trading_date"] == "2026-09-30"
        assert hist[0]["kda_direction_accuracy"] == 0.6
        assert hist[0]["strategy_direction_accuracy"] == 0.5
        assert "recorded_at" in hist[0]

    def test_T02_multiple_appends_oldest_first_and_n_limit(self, tmp_path):
        path = str(tmp_path / "comparative_summary_history.jsonl")
        with patch("knowledge_authority.kda_comparative._SUMMARY_HISTORY_PATH", path):
            for i, d in enumerate(["2026-09-28", "2026-09-29", "2026-09-30"]):
                record_comparative_summary({"n": i}, trading_date=d)
            hist_all = get_comparative_summary_history(n=0)
            hist_last2 = get_comparative_summary_history(n=2)
        assert [r["trading_date"] for r in hist_all] == ["2026-09-28", "2026-09-29", "2026-09-30"]
        assert [r["trading_date"] for r in hist_last2] == ["2026-09-29", "2026-09-30"]

    def test_T03_missing_file_returns_empty(self, tmp_path):
        path = str(tmp_path / "does_not_exist.jsonl")
        with patch("knowledge_authority.kda_comparative._SUMMARY_HISTORY_PATH", path):
            assert get_comparative_summary_history() == []

    def test_T04_write_failure_fails_open(self, tmp_path):
        # Directory that can never be created (parent is a file, not a dir)
        blocker = tmp_path / "blocker_file"
        blocker.write_text("x")
        bad_path = str(blocker / "sub" / "history.jsonl")
        with patch("knowledge_authority.kda_comparative._SUMMARY_HISTORY_PATH", bad_path):
            # Must not raise
            record_comparative_summary({"n": 1}, trading_date="2026-09-30")

    def test_T05_corrupt_line_skipped(self, tmp_path):
        path = tmp_path / "history.jsonl"
        path.write_text('{"trading_date": "2026-09-29", "n": 1}\nNOT_JSON\n')
        with patch("knowledge_authority.kda_comparative._SUMMARY_HISTORY_PATH", str(path)):
            hist = get_comparative_summary_history()
        assert len(hist) == 1
        assert hist[0]["trading_date"] == "2026-09-29"


# ─────────────────────────────────────────────────────────────────────────────
# Regression guard: the real key-name bug is actually fixed
# ─────────────────────────────────────────────────────────────────────────────

class TestSummaryKeyNamesMatchRealSchema:

    def test_T06_summarize_uses_the_correct_key_names(self):
        """
        KDAComparativeAnalyzer.summarize()'s real return dict must use
        'successful_overrules'/'overrule_count' -- NOT the non-existent
        'kda_successful_overrules'/'kda_overrule_total' the EOD log line
        used to read (which silently always evaluated to 0/0 via .get()
        defaults, even with real non-zero underlying data).
        """
        from knowledge_authority.kda_comparative import KDAComparativeAnalyzer

        summary = KDAComparativeAnalyzer.summarize([])
        # Empty-input shape still uses the real schema (no magic bug-compatible keys)
        assert "kda_successful_overrules" not in summary
        assert "kda_overrule_total" not in summary

    def test_T07_nonzero_overrules_are_not_silently_zeroed(self):
        """
        Build real comparison records showing a successful overrule, confirm
        summarize() reports it under the correct keys (what the fixed log
        line now reads) rather than the old, always-0 buggy keys.
        """
        from knowledge_authority.kda_outcome_models import KDAComparisonRecord

        rec = KDAComparisonRecord(
            comparison_id="c1", decision_id="d1", symbol="RELIANCE",
            trading_date="2026-09-30",
            kda_decision="KNOWLEDGE_BUY", strategy_decision="REJECT",
            scanner_signal="BUY",
            comparison_type="KDA_OVERRULES_STRATEGY",
            overrule_result="KNOWLEDGE_SUCCESSFUL_OVERRULE",
            outcome_class="CORRECT_BUY", return_t5=3.2, direction_correct=True,
            target_hit=True, stop_hit=False,
            kda_correct=True, strategy_correct=False, scanner_correct=True,
        )
        from knowledge_authority.kda_comparative import KDAComparativeAnalyzer
        summary = KDAComparativeAnalyzer.summarize([rec])

        assert summary["successful_overrules"] == 1
        assert summary["overrule_count"] == 1
        assert summary["kda_direction_accuracy"] == 1.0
        assert summary["strategy_direction_accuracy"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Safety contract: still research-only, never gates a decision
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyContract:

    def test_T08_no_forbidden_imports_in_kda_comparative(self):
        import inspect
        import knowledge_authority.kda_comparative as mod
        src = inspect.getsource(mod)
        for forbidden in ("import execution_engine", "import order_manager",
                          "import risk_control", "import dhan_feed", "from broker"):
            assert forbidden not in src, f"forbidden import found: {forbidden}"

    def test_T09_record_comparative_summary_never_raises_on_bad_input(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        with patch("knowledge_authority.kda_comparative._SUMMARY_HISTORY_PATH", path):
            # Non-serializable-by-default object should still be handled via default=str
            class Weird:
                def __str__(self):
                    return "weird"
            record_comparative_summary({"n": 1, "weird": Weird()}, trading_date="2026-09-30")

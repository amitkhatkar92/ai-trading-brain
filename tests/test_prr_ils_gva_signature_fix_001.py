"""
tests/test_prr_ils_gva_signature_fix_001.py
=============================================
Root-cause fix: production_readiness/prr_runner.py's _get_ils_score() and
_get_gva_score() always silently failed (caught by a blanket
`except Exception: return 0.0`), so ILS_Score/GVA_Score were ALWAYS 0.0 on
every single PRR run regardless of real underlying evidence -- confirmed
live: 1,018 real institutional_learning records existed, but ILS/GVA both
reported 0.0 for a full week (2026-09-28 .. 2026-10-05) of certification
history.

Two independent, confirmed-live bugs:
  1. _get_ils_score() called `run_verification_pass(dry_run=True)` and
     `update_lifecycle(verified, dry_run=True)` -- both real functions
     require a positional `today: str` argument with no default, so both
     calls always raised TypeError.
  2. _get_gva_score() imported `growth_validator.growth_validator_ai
     .GrowthValidatorAI` -- a module/class that has never existed. The
     real public entry point is `growth_validator.run_gva()`.

Fix: _get_ils_score(data) now threads `data.get("date")` through as the
required `today` argument to both calls. _get_gva_score() now imports and
calls the real `growth_validator.run_gva()` and reads `overall_score`.

T01  _get_ils_score() passes `today` to run_verification_pass()
T02  _get_ils_score() passes `today` to update_lifecycle()
T03  _get_ils_score() falls back to today's date when "date" key is absent
T04  _get_ils_score() still fails open (returns 0.0) on any exception
T05  _get_gva_score() calls the real growth_validator.run_gva(), not the
     non-existent GrowthValidatorAI
T06  _get_gva_score() returns overall_score from a dict result
T07  _get_gva_score() still fails open (returns 0.0) on any exception
T08  safety-contract: neither function can ever raise out of
     _collect_prr_data()'s Phase 9 block
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from production_readiness.prr_runner import _get_ils_score, _get_gva_score


class TestGetIlsScore:
    def test_T01_passes_today_to_run_verification_pass(self):
        mock_verify = MagicMock(return_value=[])
        with patch("institutional_learning.ilc_score.compute_ils_score", return_value=MagicMock(overall_score=42.0)), \
             patch("institutional_learning.ilc_verification.get_all_records", return_value=[]), \
             patch("institutional_learning.ilc_verification.run_verification_pass", mock_verify), \
             patch("institutional_learning.ilc_roi.compute_all_roi", return_value=[]), \
             patch("institutional_learning.ilc_lifecycle.update_lifecycle", return_value=[]):
            score = _get_ils_score({"date": "2026-10-05"})
        mock_verify.assert_called_once_with("2026-10-05", dry_run=True)
        assert score == 42.0

    def test_T02_passes_today_to_update_lifecycle(self):
        mock_lifecycle = MagicMock(return_value=[])
        with patch("institutional_learning.ilc_score.compute_ils_score", return_value=MagicMock(overall_score=10.0)), \
             patch("institutional_learning.ilc_verification.get_all_records", return_value=[]), \
             patch("institutional_learning.ilc_verification.run_verification_pass", return_value=[]), \
             patch("institutional_learning.ilc_roi.compute_all_roi", return_value=[]), \
             patch("institutional_learning.ilc_lifecycle.update_lifecycle", mock_lifecycle):
            _get_ils_score({"date": "2026-10-05"})
        mock_lifecycle.assert_called_once_with([], "2026-10-05", dry_run=True)

    def test_T03_falls_back_to_today_when_date_absent(self):
        mock_verify = MagicMock(return_value=[])
        with patch("institutional_learning.ilc_score.compute_ils_score", return_value=MagicMock(overall_score=0.0)), \
             patch("institutional_learning.ilc_verification.get_all_records", return_value=[]), \
             patch("institutional_learning.ilc_verification.run_verification_pass", mock_verify), \
             patch("institutional_learning.ilc_roi.compute_all_roi", return_value=[]), \
             patch("institutional_learning.ilc_lifecycle.update_lifecycle", return_value=[]):
            _get_ils_score({})
        called_today = mock_verify.call_args[0][0]
        assert isinstance(called_today, str) and len(called_today) == 10  # YYYY-MM-DD

    def test_T04_fails_open_on_exception(self):
        with patch("institutional_learning.ilc_verification.get_all_records", side_effect=RuntimeError("boom")):
            score = _get_ils_score({"date": "2026-10-05"})
        assert score == 0.0


class TestGetGvaScore:
    def test_T05_calls_real_run_gva(self):
        mock_run_gva = MagicMock(return_value={"overall_score": 69.1})
        with patch("growth_validator.run_gva", mock_run_gva):
            score = _get_gva_score()
        mock_run_gva.assert_called_once_with()
        assert score == 69.1

    def test_T06_returns_overall_score_from_dict(self):
        with patch("growth_validator.run_gva", return_value={"overall_score": 55.5, "other": "x"}):
            assert _get_gva_score() == 55.5

    def test_T07_fails_open_on_exception(self):
        with patch("growth_validator.run_gva", side_effect=RuntimeError("boom")):
            assert _get_gva_score() == 0.0

    def test_T08_no_module_not_found_regression(self):
        # Regression guard: the old buggy import path must never come back.
        import inspect
        from production_readiness import prr_runner
        src = inspect.getsource(prr_runner._get_gva_score)
        assert "growth_validator_ai" not in src
        assert "GrowthValidatorAI" not in src
        assert "run_gva" in src

    def test_T09_exception_is_logged_not_silent(self, caplog):
        """DTA-PRR-GVA-SILENT-FAIL-001: confirmed live on 2026-10-06 -- a real
        failure inside run_gva() produced gva=0.0 in the certification
        history with zero trace anywhere. The exception must now be logged."""
        import logging
        with caplog.at_level(logging.WARNING, logger="production_readiness.prr_runner"):
            with patch("growth_validator.run_gva", side_effect=RuntimeError("boom")):
                score = _get_gva_score()
        assert score == 0.0
        assert any("GVA score calculation failed" in r.message for r in caplog.records)


class TestIlsScoreLogging:
    def test_T10_exception_is_logged_not_silent(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="production_readiness.prr_runner"):
            with patch("institutional_learning.ilc_verification.get_all_records",
                       side_effect=RuntimeError("boom")):
                score = _get_ils_score({"date": "2026-10-05"})
        assert score == 0.0
        assert any("ILS score calculation failed" in r.message for r in caplog.records)


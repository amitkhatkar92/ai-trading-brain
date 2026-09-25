"""
tests/test_cle_fingerprint_combination_001.py
================================================
DTA-RESEARCH-QUALITY-001 -- CLE-001 combination fingerprint testing.

Verifies cle_research.py now tests multiple domain-reasoned combination
fingerprints (not just the original single volume+momentum condition) and
picks whichever clears the exact same evidence bar with the highest lift,
while preserving full backward compatibility with the pre-existing
_assess_evidence() contract (still directly patchable, still the sole
evidence source in the existing test_cle.py suite's mocked scenarios).

T01  _compute_features adds rsi_14 and mom_accel columns
T02  _assess_evidence_rsi_accel returns (0,0,0,0) when required columns
     are missing (never crashes)
T03  _assess_evidence_atr_momentum returns (0,0,0,0) when required
     columns are missing (never crashes)
T04  _select_best_fingerprint picks the highest-lift QUALIFYING
     fingerprint among several candidates
T05  _select_best_fingerprint falls back to the volume_momentum result
     when nothing qualifies (preserves original failure behavior)
T06  _select_best_fingerprint correctly re-resolves a patched
     _assess_evidence at call time (not bound at import time)
T07  run_historical_research's feature_name reflects whichever
     fingerprint was actually selected
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from cle_learning_executor import cle_research as _res


def _synthetic_df(n=250, seed=7):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0, 1.0, n))
    close = np.maximum(close, 1.0)
    high = close + rng.uniform(0.1, 2.0, n)
    low = close - rng.uniform(0.1, 2.0, n)
    volume = rng.uniform(1000, 5000, n)
    return pd.DataFrame({"Open": close, "High": high, "Low": low,
                          "Close": close, "Volume": volume}, index=dates)


class TestFeatureComputation:
    def test_t01_adds_rsi_and_mom_accel(self):
        df = _res._compute_features(_synthetic_df())
        assert "rsi_14" in df.columns
        assert "mom_accel" in df.columns


class TestFingerprintRobustness:
    def test_t02_rsi_accel_missing_columns_safe(self):
        df = pd.DataFrame({"daily_return": [1.0, 2.0, -1.0]})
        result = _res._assess_evidence_rsi_accel(df, "UP", 2.0)
        assert result == (0, 0.0, 0.0, 0.0)

    def test_t03_atr_momentum_missing_columns_safe(self):
        df = pd.DataFrame({"daily_return": [1.0, 2.0, -1.0]})
        result = _res._assess_evidence_atr_momentum(df, "UP", 2.0)
        assert result == (0, 0.0, 0.0, 0.0)


class TestSelectBestFingerprint:
    def test_t04_picks_highest_lift_qualifying(self):
        with (
            patch.object(_res, "_assess_evidence", return_value=(20, 0.10, 0.55, 1.4)),
            patch.object(_res, "_assess_evidence_rsi_accel", return_value=(25, 0.10, 0.70, 2.8)),
            patch.object(_res, "_assess_evidence_atr_momentum", return_value=(0, 0.0, 0.0, 0.0)),
        ):
            best, all_results = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
        assert best["name"] == "low_rsi_high_mom_accel"
        assert len(all_results) == 3

    def test_t05_falls_back_when_nothing_qualifies(self):
        with (
            patch.object(_res, "_assess_evidence", return_value=(5, 0.10, 0.30, 0.9)),
            patch.object(_res, "_assess_evidence_rsi_accel", return_value=(0, 0.0, 0.0, 0.0)),
            patch.object(_res, "_assess_evidence_atr_momentum", return_value=(0, 0.0, 0.0, 0.0)),
        ):
            best, _ = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
        assert best["name"] == "volume_momentum"

    def test_t06_resolves_patched_function_at_call_time(self):
        # Confirms fingerprint_fns is built INSIDE the function (not bound
        # at module-load time) -- patching _assess_evidence must actually
        # take effect.
        with patch.object(_res, "_assess_evidence", return_value=(50, 0.05, 0.90, 5.0)):
            best, _ = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
        assert best["name"] == "volume_momentum"
        assert best["lift"] == 5.0


class TestFeatureNameReflectsSelection:
    def test_t07_feature_name_uses_selected_fingerprint(self):
        mock_df = pd.DataFrame({"Close": range(252)})
        with (
            patch.object(_res, "_fetch_ohlcv", return_value=mock_df),
            patch.object(_res, "_compute_features", return_value=mock_df),
            patch.object(_res, "_assess_evidence", return_value=(5, 0.10, 0.30, 0.9)),
            patch.object(_res, "_assess_evidence_rsi_accel", return_value=(30, 0.10, 0.75, 3.0)),
            patch.object(_res, "_assess_evidence_atr_momentum", return_value=(0, 0.0, 0.0, 0.0)),
        ):
            result = _res.run_historical_research(
                action_id="PGA-TEST", symbol="TESTSTOCK", direction="UP",
                return_pct=4.0, today="2026-08-11", dry_run=True,
            )
        assert result.status == "CANDIDATE_CREATED"
        assert result.feature_name == "low_rsi_high_mom_accel_up"

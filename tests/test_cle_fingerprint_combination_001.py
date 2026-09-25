"""
tests/test_cle_fingerprint_combination_001.py
================================================
DTA-RESEARCH-QUALITY-001 (revised) -- CLE-001 now reuses the REAL,
already-certified fingerprint library (Selection Intelligence Phase 7's
auto-promoted list + the original Phase 2D finding) instead of hand-
invented combinations. See cle_research.py's module note above
_load_certified_fingerprints() for the full rationale.

T01  _compute_features adds rsi_14, mom_accel, and hv_20 columns
T02  _load_certified_fingerprints always includes the static Phase 2D
     entry even with no JSON file present
T03  _load_certified_fingerprints merges real JSON-file entries and
     de-duplicates against the static entry
T04  _load_certified_fingerprints fails open (static entry only) on a
     corrupt JSON file
T05  _evaluate_certified_fingerprint safely skips (0,0,0,0) when a
     condition references an unavailable feature (e.g. rs_pct_5d)
T06  _evaluate_certified_fingerprint correctly evaluates a computable
     single-feature condition
T07  _select_best_fingerprint only tests certified fingerprints whose
     OWN direction matches the requested direction
T08  _select_best_fingerprint picks the highest-lift QUALIFYING
     fingerprint among several candidates
T09  _select_best_fingerprint falls back to the volume_momentum result
     when nothing qualifies (preserves original failure behavior)
T10  _select_best_fingerprint correctly re-resolves a patched
     _assess_evidence at call time (not bound at import time)
T11  run_historical_research's feature_name reflects whichever
     fingerprint was actually selected (certified name, not invented)
"""
from __future__ import annotations

import json
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
    def test_t01_adds_rsi_mom_accel_and_hv20(self):
        df = _res._compute_features(_synthetic_df())
        assert "rsi_14" in df.columns
        assert "mom_accel" in df.columns
        assert "hv_20" in df.columns


class TestLoadCertifiedFingerprints:
    def test_t02_static_entry_always_present(self, tmp_path):
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(tmp_path / "missing.json")):
            fps = _res._load_certified_fingerprints()
        names = {(f["name"], f["direction"]) for f in fps}
        assert ("UP_low_rsi_high_accel", "UP") in names
        assert len(fps) == 1

    def test_t03_merges_and_dedupes_json_entries(self, tmp_path):
        p = tmp_path / "discovered.json"
        p.write_text(json.dumps([
            {"name": "hkap_high_mom5d", "label": "x", "direction": "UP",
             "conditions": [["mom_5d", "high"]]},
            {"name": "UP_low_rsi_high_accel", "label": "dup", "direction": "UP",
             "conditions": [["rsi_14", "low"], ["mom_accel", "high"]]},
        ]), encoding="utf-8")
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(p)):
            fps = _res._load_certified_fingerprints()
        names = [(f["name"], f["direction"]) for f in fps]
        assert names.count(("UP_low_rsi_high_accel", "UP")) == 1
        assert ("hkap_high_mom5d", "UP") in names
        assert len(fps) == 2

    def test_t04_fails_open_on_corrupt_file(self, tmp_path):
        p = tmp_path / "corrupt.json"
        p.write_text("NOT VALID JSON", encoding="utf-8")
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(p)):
            fps = _res._load_certified_fingerprints()
        assert len(fps) == 1
        assert fps[0]["name"] == "UP_low_rsi_high_accel"


class TestEvaluateCertifiedFingerprint:
    def test_t05_skips_unavailable_feature(self):
        df = _res._compute_features(_synthetic_df())
        result = _res._evaluate_certified_fingerprint(
            df, "UP", 2.0, [("rs_pct_5d", "high")])
        assert result == (0, 0.0, 0.0, 0.0)

    def test_t06_evaluates_computable_condition(self):
        df = _res._compute_features(_synthetic_df())
        count, base, wr, lift = _res._evaluate_certified_fingerprint(
            df, "UP", 2.0, [("mom_5d", "high")])
        assert isinstance(count, int)
        assert 0.0 <= base <= 1.0


class TestSelectBestFingerprint:
    def test_t07_only_matching_direction_tested(self, tmp_path):
        p = tmp_path / "discovered.json"
        p.write_text(json.dumps([
            {"name": "up_only_combo", "label": "x", "direction": "UP",
             "conditions": [["mom_5d", "high"]]},
        ]), encoding="utf-8")
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(p)):
            _, all_results_up = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
            _, all_results_down = _res._select_best_fingerprint(_synthetic_df(), "DOWN", 2.0)
        names_up = {r["name"] for r in all_results_up}
        names_down = {r["name"] for r in all_results_down}
        assert "up_only_combo" in names_up
        assert "up_only_combo" not in names_down
        # static entry is UP-only too
        assert "UP_low_rsi_high_accel" in names_up
        assert "UP_low_rsi_high_accel" not in names_down

    def test_t08_picks_highest_lift_qualifying(self, tmp_path):
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(tmp_path / "missing.json")):
            with (
                patch.object(_res, "_assess_evidence", return_value=(20, 0.10, 0.55, 1.4)),
                patch.object(_res, "_evaluate_certified_fingerprint",
                             return_value=(25, 0.10, 0.70, 2.8)),
            ):
                best, all_results = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
        assert best["name"] == "UP_low_rsi_high_accel"
        assert len(all_results) == 2  # volume_momentum + the one static UP entry

    def test_t09_falls_back_when_nothing_qualifies(self, tmp_path):
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(tmp_path / "missing.json")):
            with (
                patch.object(_res, "_assess_evidence", return_value=(5, 0.10, 0.30, 0.9)),
                patch.object(_res, "_evaluate_certified_fingerprint",
                             return_value=(0, 0.0, 0.0, 0.0)),
            ):
                best, _ = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
        assert best["name"] == "volume_momentum"

    def test_t10_resolves_patched_function_at_call_time(self, tmp_path):
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(tmp_path / "missing.json")):
            with patch.object(_res, "_assess_evidence", return_value=(50, 0.05, 0.90, 5.0)):
                best, _ = _res._select_best_fingerprint(_synthetic_df(), "UP", 2.0)
        assert best["name"] == "volume_momentum"
        assert best["lift"] == 5.0


class TestFeatureNameReflectsSelection:
    def test_t11_feature_name_uses_selected_fingerprint(self, tmp_path):
        mock_df = pd.DataFrame({"Close": range(252)})
        with patch.object(_res, "_CERTIFIED_FINGERPRINTS_PATH", str(tmp_path / "missing.json")):
            with (
                patch.object(_res, "_fetch_ohlcv", return_value=mock_df),
                patch.object(_res, "_compute_features", return_value=mock_df),
                patch.object(_res, "_assess_evidence", return_value=(5, 0.10, 0.30, 0.9)),
                patch.object(_res, "_evaluate_certified_fingerprint",
                             return_value=(30, 0.10, 0.75, 3.0)),
            ):
                result = _res.run_historical_research(
                    action_id="PGA-TEST", symbol="TESTSTOCK", direction="UP",
                    return_pct=4.0, today="2026-08-11", dry_run=True,
                )
        assert result.status == "CANDIDATE_CREATED"
        assert result.feature_name == "UP_low_rsi_high_accel_up"

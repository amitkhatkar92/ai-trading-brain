"""
tests/test_ranking_self_learning_001.py
=========================================
Ranking Self-Learning Loop (RSL-001) — test suite.

Covers:
  - ranking_hypothesis_validator_001.py: statistics (time split, bootstrap CI,
    scorecard verdicts), title parsing, automated lifecycle chain.
  - ranking_adjustment_engine_001.py: shadow-candidate registration + cooldown/
    concurrency guardrails, shadow-tracking state machine, rollback monitor,
    annotate_adjusted_scores hook (no-op vs active).
  - Safety: no execution/broker imports in either new module.

All file I/O in these tests is redirected to tmp_path — never touches the
real data/ files or the live ARS hypothesis registry.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.knowledge_system.ksl_models import Classification, FindingVerdict, KnowledgeFinding, KSLShadowCandidate
from scripts.knowledge_system import ranking_hypothesis_validator_001 as rhv
from scripts.knowledge_system import ranking_adjustment_engine_001 as rae


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rec(trade_date: str, classification: str, direction: str = "UP") -> dict:
    return {
        "trade_date": trade_date,
        "direction": direction,
        "classification": classification,
        "miss_reason": "OUTRANKED_BY_STRONGER_OPENERS" if classification == "RANKING_MISS" else "NOT_APPLICABLE",
        "ge2": True,
    }


def _make_evidence(n_train_miss, n_train_hit, n_oos_miss, n_oos_hit, direction="UP"):
    """Build a synthetic time-ordered evidence set with a controllable effect."""
    records = []
    d = 1
    for _ in range(n_train_miss):
        records.append(_rec(f"2026-01-{d:02d}", "RANKING_MISS", direction)); d += 1
    for _ in range(n_train_hit):
        records.append(_rec(f"2026-01-{d:02d}", "CORRECT_SELECT", direction)); d += 1
    # push into a later month so time-split cleanly separates OOS
    d = 1
    for _ in range(n_oos_miss):
        records.append(_rec(f"2026-03-{d:02d}", "RANKING_MISS", direction)); d += 1
    for _ in range(n_oos_hit):
        records.append(_rec(f"2026-03-{d:02d}", "CORRECT_SELECT", direction)); d += 1
    return records


# ─────────────────────────────────────────────────────────────────────────────
# T001-T010 — statistics (pure functions, no I/O)
# ─────────────────────────────────────────────────────────────────────────────

def test_t001_time_split_never_shuffles():
    records = _make_evidence(5, 5, 5, 5)
    train, oos = rhv._time_split(records)
    if train and oos:
        assert max(r["trade_date"] for r in train) <= min(r["trade_date"] for r in oos)


def test_t002_time_split_empty_input():
    train, oos = rhv._time_split([])
    assert train == [] and oos == []


def test_t003_miss_rate_basic():
    records = [_rec("2026-01-01", "RANKING_MISS"), _rec("2026-01-02", "CORRECT_SELECT")]
    rate, n = rhv._miss_rate(records)
    assert n == 2 and rate == 0.5


def test_t004_miss_rate_empty():
    rate, n = rhv._miss_rate([])
    assert rate == 0.0 and n == 0


def test_t005_bootstrap_ci_bounds_valid():
    records = [_rec("2026-01-01", "RANKING_MISS")] * 30 + [_rec("2026-01-02", "CORRECT_SELECT")] * 20
    lo, hi = rhv._bootstrap_ci(records, iters=200)
    assert 0.0 <= lo <= hi <= 1.0


def test_t006_bootstrap_ci_deterministic_with_seed():
    records = [_rec("2026-01-01", "RANKING_MISS")] * 15 + [_rec("2026-01-02", "CORRECT_SELECT")] * 15
    lo1, hi1 = rhv._bootstrap_ci(records, iters=300, seed=42)
    lo2, hi2 = rhv._bootstrap_ci(records, iters=300, seed=42)
    assert lo1 == lo2 and hi1 == hi2


def test_t007_scorecard_validated_strong_effect():
    # Strong, consistent, high-miss-rate signal in both train and OOS -> VALIDATED
    records = _make_evidence(n_train_miss=35, n_train_hit=5, n_oos_miss=30, n_oos_hit=5)
    result = rhv.run_scorecard(records)
    assert result["verdict"] == FindingVerdict.VALIDATED
    assert result["checks_passed"] >= 3


def test_t008_scorecard_no_incremental_value_when_effect_absent():
    # Low miss rate (well below baseline 0.55), no real effect, small OOS sample
    records = _make_evidence(n_train_miss=5, n_train_hit=35, n_oos_miss=2, n_oos_hit=8)
    result = rhv.run_scorecard(records)
    assert result["verdict"] != FindingVerdict.VALIDATED
    assert result["checks_passed"] <= 1
    assert result["verdict"] == FindingVerdict.NO_INCREMENTAL_VALUE


def test_t009_scorecard_insufficient_sample_small_oos():
    records = _make_evidence(n_train_miss=30, n_train_hit=5, n_oos_miss=3, n_oos_hit=2)
    result = rhv.run_scorecard(records)
    assert result["oos_n"] < rhv.MIN_OOS_N
    assert result["verdict"] != FindingVerdict.VALIDATED


def test_t010_scorecard_inconsistent_train_oos_not_validated():
    # Train shows high miss rate, OOS shows the opposite sign -> C3 fails -> not VALIDATED
    records = _make_evidence(n_train_miss=35, n_train_hit=5, n_oos_miss=2, n_oos_hit=30)
    result = rhv.run_scorecard(records)
    assert result["checks"]["C3_train_oos_consistent"] is False
    assert result["verdict"] != FindingVerdict.VALIDATED


# ─────────────────────────────────────────────────────────────────────────────
# T011-T015 — title parsing / miss-reason extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_t011_parse_title_valid():
    parsed = rhv._parse_title("KSL-001 Auto: C2_RANKING — UP")
    assert parsed == ("C2_RANKING", "UP")


def test_t012_parse_title_invalid_prefix():
    assert rhv._parse_title("Some other hypothesis") is None


def test_t013_parse_title_missing_separator():
    assert rhv._parse_title("KSL-001 Auto: C2_RANKING UP") is None


def test_t014_dominant_miss_reason():
    records = [_rec("2026-01-01", "RANKING_MISS")] * 3
    records[0]["miss_reason"] = "ADVERSE_OPEN_GAP"
    records[1]["miss_reason"] = "OUTRANKED_BY_STRONGER_OPENERS"
    records[2]["miss_reason"] = "OUTRANKED_BY_STRONGER_OPENERS"
    assert rhv._dominant_miss_reason(records) == "OUTRANKED_BY_STRONGER_OPENERS"


def test_t015_dominant_miss_reason_empty():
    assert rhv._dominant_miss_reason([]) is None


# ─────────────────────────────────────────────────────────────────────────────
# T016-T020 — automated hypothesis lifecycle (fake registry, no real files)
# ─────────────────────────────────────────────────────────────────────────────

from enum import Enum as _Enum


class _FakeStatus(str, _Enum):
    """Minimal stand-in mirroring HypothesisStatus for lifecycle tests."""
    PROPOSED = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class _FakeHypothesis:
    def __init__(self, hypothesis_id, status):
        self.hypothesis_id = hypothesis_id
        self.status = status


class _FakeRegistry:
    def __init__(self):
        self.calls = []

    def update_status(self, hypothesis_id, new_status, actor, reason, metadata=None):
        self.calls.append((hypothesis_id, new_status, actor))


@pytest.fixture()
def _patch_hypothesis_status(monkeypatch):
    """Patch the HypothesisStatus import used inside _advance_to_running/_apply_verdict."""
    import types
    fake_module = types.ModuleType("autonomous_research.hypothesis_models")
    fake_module.HypothesisStatus = _FakeStatus
    monkeypatch.setitem(sys.modules, "autonomous_research.hypothesis_models", fake_module)
    yield


def test_t016_advance_to_running_from_proposed(_patch_hypothesis_status):
    hr = _FakeRegistry()
    hyp = _FakeHypothesis("H1", _FakeStatus.PROPOSED)
    ok = rhv._advance_to_running(hr, hyp)
    assert ok is True
    statuses_called = [c[1] for c in hr.calls]
    assert statuses_called == [_FakeStatus.UNDER_REVIEW, _FakeStatus.APPROVED,
                                _FakeStatus.PLANNED, _FakeStatus.RUNNING]


def test_t017_advance_to_running_already_running_is_noop(_patch_hypothesis_status):
    hr = _FakeRegistry()
    hyp = _FakeHypothesis("H1", _FakeStatus.RUNNING)
    ok = rhv._advance_to_running(hr, hyp)
    assert ok is True
    assert hr.calls == []


def test_t018_advance_to_running_terminal_status_blocked(_patch_hypothesis_status):
    hr = _FakeRegistry()
    hyp = _FakeHypothesis("H1", _FakeStatus.REJECTED)
    ok = rhv._advance_to_running(hr, hyp)
    assert ok is False


def test_t019_apply_verdict_validated(_patch_hypothesis_status):
    hr = _FakeRegistry()
    hyp = _FakeHypothesis("H1", _FakeStatus.RUNNING)
    scorecard = {"verdict": FindingVerdict.VALIDATED, "checks_passed": 4, "checks_total": 4,
                 "oos_n": 30, "oos_effect": 0.1}
    final = rhv._apply_verdict(hr, hyp, scorecard)
    assert final == _FakeStatus.VALIDATED
    assert hr.calls[-1][1] == _FakeStatus.VALIDATED


def test_t020_apply_verdict_rejected(_patch_hypothesis_status):
    hr = _FakeRegistry()
    hyp = _FakeHypothesis("H1", _FakeStatus.RUNNING)
    scorecard = {"verdict": FindingVerdict.NO_INCREMENTAL_VALUE, "checks_passed": 0, "checks_total": 4,
                 "oos_n": 30, "oos_effect": -0.1}
    final = rhv._apply_verdict(hr, hyp, scorecard)
    assert final == _FakeStatus.REJECTED


def test_t021_apply_verdict_insufficient_stays_running(_patch_hypothesis_status):
    hr = _FakeRegistry()
    hyp = _FakeHypothesis("H1", _FakeStatus.RUNNING)
    scorecard = {"verdict": FindingVerdict.INSUFFICIENT_SAMPLE, "checks_passed": 2, "checks_total": 4,
                 "oos_n": 10, "oos_effect": 0.02}
    final = rhv._apply_verdict(hr, hyp, scorecard)
    assert final == _FakeStatus.RUNNING
    assert hr.calls == []  # no registry write for inconclusive results


# ─────────────────────────────────────────────────────────────────────────────
# T022-T035 — adjustment engine: store isolation + registration guardrails
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def _isolated_store(tmp_path, monkeypatch):
    """Redirect all RAE-001 storage to tmp_path — never touches real data/."""
    candidates_path = tmp_path / "ranking_shadow_candidates.json"
    active_config_path = tmp_path / "active_ranking_adjustments.json"
    shadow_jsonl_path = tmp_path / "shadow.jsonl"
    monkeypatch.setattr(rae, "CANDIDATES_PATH", candidates_path)
    monkeypatch.setattr(rae, "ACTIVE_CONFIG_PATH", active_config_path)
    monkeypatch.setattr(rae, "SHADOW_JSONL_PATH", shadow_jsonl_path)
    return {"candidates": candidates_path, "active_config": active_config_path, "shadow": shadow_jsonl_path}


def _finding(verdict=FindingVerdict.VALIDATED) -> KnowledgeFinding:
    return KnowledgeFinding(
        finding_id="F1", research_question_id="RQ1", experiment_id="H1", verdict=verdict,
        baseline_metrics={}, candidate_metrics={}, delta={}, oos_result="", leakage_result="",
        sample_size=30, confidence=0.9, limitations="", recommendation="", created_at="2026-09-12",
    )


def _scorecard(**overrides):
    base = {"checks_passed": 4, "checks_total": 4, "oos_effect": 0.1, "oos_miss_rate": 0.65,
            "baseline": 0.55, "ci_low": 0.6, "ci_high": 0.7, "train_n": 30, "oos_n": 30}
    base.update(overrides)
    return base


def test_t022_register_shadow_candidate_creates_entry(_isolated_store):
    cand = rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP",
                                          "OUTRANKED_BY_STRONGER_OPENERS", _scorecard())
    assert cand is not None
    assert cand.status == rae.STATUS_SHADOW_ELIGIBLE
    assert _isolated_store["candidates"].exists()


def test_t023_register_shadow_candidate_blocks_duplicate_feature(_isolated_store):
    rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS", _scorecard())
    second = rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS", _scorecard())
    assert second is None  # already active for this feature


def test_t024_register_shadow_candidate_max_concurrent_guardrail(_isolated_store):
    for i in range(rae.MAX_CONCURRENT_SHADOW):
        result = rae.register_shadow_candidate(_finding(), "C2_RANKING", f"DIR{i}", "REASON", _scorecard())
        assert result is not None
    blocked = rae.register_shadow_candidate(_finding(), "C2_RANKING", "OVERFLOW", "REASON", _scorecard())
    assert blocked is None


def test_t025_feature_id_format():
    fid = rae._feature_id("C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS")
    assert fid == "C2_RANKING|UP|OUTRANKED_BY_STRONGER_OPENERS"


# ─────────────────────────────────────────────────────────────────────────────
# T026-T035 — shadow tracking state machine
# ─────────────────────────────────────────────────────────────────────────────

def _write_shadow_jsonl(path: Path, records: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            r.setdefault("record_type", "SHADOW_CANDIDATE")
            f.write(json.dumps(r) + "\n")


def test_t026_advance_shadow_tracking_activates_eligible(_isolated_store):
    rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS", _scorecard())
    summary = rae.advance_shadow_tracking()
    assert summary["activated_shadow"] == 1
    candidates = rae._load_candidates()
    assert candidates[0].status == rae.STATUS_SHADOW_ACTIVE
    assert candidates[0].shadow_start_date is not None


def test_t027_advance_shadow_tracking_waits_for_min_days(_isolated_store):
    rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS", _scorecard())
    rae.advance_shadow_tracking()  # -> SHADOW_ACTIVE
    # Only 3 distinct dates of shadow evidence — below REQUIRED_OBSERVATION_DAYS
    recs = []
    for d in range(3):
        recs.append({"trade_date": f"2026-09-{d+1:02d}", "direction": "UP",
                      "would_select_adjusted": True, "selected_final_5": False, "t1_ret_pct": 3.0})
    _write_shadow_jsonl(_isolated_store["shadow"], recs)
    summary = rae.advance_shadow_tracking()
    candidates = rae._load_candidates()
    assert candidates[0].status == rae.STATUS_SHADOW_ACTIVE  # still waiting


def test_t028_advance_shadow_tracking_promotes_on_confirmed_effect(_isolated_store, monkeypatch):
    monkeypatch.setattr(rae, "REQUIRED_OBSERVATION_DAYS", 5)
    monkeypatch.setattr(rae, "MIN_OBS_FOR_ACTIVATION", 5)
    cand = rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS",
                                          _scorecard(oos_miss_rate=0.65))
    rae.advance_shadow_tracking()  # -> SHADOW_ACTIVE

    # Dates must be >= shadow_start_date (today's real date) to be counted.
    recs = []
    for d in range(6):
        recs.append({"trade_date": f"2099-01-{d+1:02d}", "direction": "UP",
                      "would_select_adjusted": True, "selected_final_5": False,
                      "t1_ret_pct": 3.0})  # all real >=2% winners -> confirms
    _write_shadow_jsonl(_isolated_store["shadow"], recs)

    summary = rae.advance_shadow_tracking()
    candidates = rae._load_candidates()
    assert summary["promoted_live"] == 1
    assert candidates[0].status == rae.STATUS_ACTIVE
    active_config = json.loads(_isolated_store["active_config"].read_text())
    assert "UP" in active_config


def test_t029_advance_shadow_tracking_rejects_on_unconfirmed_effect(_isolated_store, monkeypatch):
    monkeypatch.setattr(rae, "REQUIRED_OBSERVATION_DAYS", 5)
    monkeypatch.setattr(rae, "MIN_OBS_FOR_ACTIVATION", 5)
    rae.register_shadow_candidate(_finding(), "C2_RANKING", "UP", "OUTRANKED_BY_STRONGER_OPENERS",
                                   _scorecard(oos_miss_rate=0.90))  # very high bar to confirm
    rae.advance_shadow_tracking()  # -> SHADOW_ACTIVE

    recs = []
    for d in range(6):
        recs.append({"trade_date": f"2099-01-{d+1:02d}", "direction": "UP",
                      "would_select_adjusted": True, "selected_final_5": False,
                      "t1_ret_pct": -3.0})  # all losers -> fails to confirm
    _write_shadow_jsonl(_isolated_store["shadow"], recs)

    summary = rae.advance_shadow_tracking()
    candidates = rae._load_candidates()
    assert summary["rejected"] == 1
    assert candidates[0].status == rae.STATUS_REJECTED


def test_t030_check_rollback_reverts_on_degradation(_isolated_store):
    cand = KSLShadowCandidate(
        candidate_id="C1", research_question_id="RQ1", finding_id="F1", created_at="2026-09-01",
        baseline_version="v1", candidate_version="v1+ADJ", reason="", evidence="",
        oos_dir_acc=0.9, oos_ge2_rate=0.6, expected_improvement="", risk="",
        required_observation_days=10, promotion_requirements="",
        status=rae.STATUS_ACTIVE, feature_id="C2_RANKING|UP|X",
        live_activated_at="2026-09-01T00:00:00+00:00",
    )
    rae._save_candidates([cand])
    recs = []
    for d in range(25):
        recs.append({"trade_date": f"2099-01-{d+1:02d}", "direction": "UP",
                      "selected_final_5": True, "t1_ret_pct": -3.0})  # all losers
    _write_shadow_jsonl(_isolated_store["shadow"], recs)

    summary = rae.check_rollback()
    candidates = rae._load_candidates()
    assert summary["rolled_back"] == 1
    assert candidates[0].status == rae.STATUS_ROLLED_BACK


def test_t031_check_rollback_no_action_when_insufficient_data(_isolated_store):
    cand = KSLShadowCandidate(
        candidate_id="C1", research_question_id="RQ1", finding_id="F1", created_at="2026-09-01",
        baseline_version="v1", candidate_version="v1+ADJ", reason="", evidence="",
        oos_dir_acc=0.9, oos_ge2_rate=0.6, expected_improvement="", risk="",
        required_observation_days=10, promotion_requirements="",
        status=rae.STATUS_ACTIVE, feature_id="C2_RANKING|UP|X",
        live_activated_at="2026-09-01T00:00:00+00:00",
    )
    rae._save_candidates([cand])
    summary = rae.check_rollback()
    candidates = rae._load_candidates()
    assert summary["rolled_back"] == 0
    assert candidates[0].status == rae.STATUS_ACTIVE


# ─────────────────────────────────────────────────────────────────────────────
# T032-T038 — annotate_adjusted_scores hook
# ─────────────────────────────────────────────────────────────────────────────

def test_t032_annotate_no_active_config_computes_shadow_fields_only(_isolated_store):
    recs = [
        {"symbol": "A", "direction": "UP", "c2_score": 1.0, "v3_score": 0.9},
        {"symbol": "B", "direction": "UP", "c2_score": 0.5, "v3_score": 0.1},
    ]
    out = rae.annotate_adjusted_scores(recs, "UP")
    assert all("c2_score_shadow_adjusted" in r for r in out)
    assert all("would_select_adjusted" in r for r in out)
    # No active config -> real c2_score must be untouched
    assert out[0]["c2_score"] == 1.0
    assert out[1]["c2_score"] == 0.5
    assert "ranking_adjustment_applied" not in out[0]


def test_t033_annotate_with_active_config_overrides_c2_score(_isolated_store):
    rae._save_active_config({"UP": {"candidate_id": "C1", "feature_id": "X", "miss_reason": "Y",
                                     "weight": 0.15, "activated_at": "now", "baseline_oos_dir_acc": 0.9}})
    recs = [
        {"symbol": "A", "direction": "UP", "c2_score": 1.0, "v3_score": 0.9},
        {"symbol": "B", "direction": "UP", "c2_score": 0.5, "v3_score": 0.1},
    ]
    out = rae.annotate_adjusted_scores(recs, "UP")
    assert out[0]["ranking_adjustment_applied"] == "C1"
    assert out[0]["c2_score"] == out[0]["c2_score_shadow_adjusted"]


def test_t034_annotate_never_raises_on_malformed_input(_isolated_store):
    # Missing 'symbol' key etc. — must degrade gracefully, never raise
    recs = [{"direction": "UP"}]
    out = rae.annotate_adjusted_scores(recs, "UP")
    assert out == recs or isinstance(out, list)


def test_t035_annotate_bounded_weight_never_exceeds_max(_isolated_store):
    rae._save_active_config({"UP": {"candidate_id": "C1", "feature_id": "X", "miss_reason": "Y",
                                     "weight": 999.0,  # malicious/corrupt value
                                     "activated_at": "now", "baseline_oos_dir_acc": 0.9}})
    recs = [{"symbol": "A", "direction": "UP", "c2_score": 1.0, "v3_score": 1.0}]
    out = rae.annotate_adjusted_scores(recs, "UP")
    # adjusted = c2_score + weight * v3_norm; weight must be clamped to MAX_WEIGHT
    assert out[0]["c2_score_shadow_adjusted"] <= 1.0 + rae.MAX_WEIGHT + 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# T036-T040 — safety: no execution/broker imports
# ─────────────────────────────────────────────────────────────────────────────

_FORBIDDEN = ("execution_engine", "order_manager", "dhan_feed", "zerodha_broker",
              "risk_control", "candidate_store")


def test_t036_validator_module_has_no_forbidden_imports():
    src = Path(rhv.__file__).read_text()
    for forbidden in _FORBIDDEN:
        assert f"import {forbidden}" not in src and f"from {forbidden}" not in src


def test_t037_adjustment_engine_module_has_no_forbidden_imports():
    src = Path(rae.__file__).read_text()
    for forbidden in _FORBIDDEN:
        assert f"import {forbidden}" not in src and f"from {forbidden}" not in src


def test_t038_adjustment_engine_isolated_from_oios():
    import re
    src = Path(rae.__file__).read_text()
    assert re.search(r"(?m)^\s*(import\s+oios\b|from\s+oios\b)", src) is None


def test_t039_final_c2_selector_frozen_file_untouched():
    # The frozen selector's core sort logic must remain byte-identical.
    src = Path(ROOT / "opportunity_engine" / "final_c2_selector.py").read_text()
    assert "valid.sort(key=lambda c: (-c.c2_score, c.v3_rank))" in src


def test_t040_shadow_generator_hook_is_additive_and_wrapped_in_try_except():
    src = Path(ROOT / "scripts" / "final_trading_architecture_shadow_001.py").read_text()
    assert "annotate_adjusted_scores" in src
    assert "except Exception as _rae_exc" in src

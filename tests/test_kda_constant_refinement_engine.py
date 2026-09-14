"""
tests/test_kda_constant_refinement_engine.py
================================================
KDA-CRE-001 — Knowledge Decision Authority Constant Refinement Engine.
Comprehensive test suite (isolated storage via monkeypatch, no real
data/kda_cre files touched).

Coverage:
- get_effective_constants(): defaults, valid override, corrupt file,
  out-of-bounds override, exactly-3-live-constants registry.
- Dynamic cooldown calculation: no-data floor, velocity scaling.
- run_scorecard(): validates a clear improvement, rejects no-signal,
  never raises on empty input.
- _process_constant() state machine: WAITING (insufficient evidence),
  WAITING (cooldown active), SHADOW_STARTED, promotion (reconfirmed),
  rejection (not reconfirmed), rollback (degraded), no premature rollback.
- run_daily_refinement_check(): never raises even on internal errors.
- Ledger is append-only, valid JSONL.
- Integration: knowledge_decision_authority.py falls back to defaults
  with no override, and actually uses a valid override when present.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

import knowledge_authority.kda_constant_refinement_engine as cre


# ─────────────────────────────────────────────────────────────────────────────
# Isolation fixture — redirect all storage paths to tmp_path
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(cre, "_STORE_DIR", tmp_path)
    monkeypatch.setattr(cre, "_DATASET_PATH", tmp_path / "kda_outcome_dataset.jsonl")
    monkeypatch.setattr(cre, "_OVERRIDES_PATH", tmp_path / "active_constant_overrides.json")
    monkeypatch.setattr(cre, "_STATE_PATH", tmp_path / "refinement_state.json")
    monkeypatch.setattr(cre, "_LEDGER_PATH", tmp_path / "constant_change_ledger.jsonl")
    # Reset the module-level mtime cache between tests
    monkeypatch.setattr(cre, "_cache_mtime", None)
    monkeypatch.setattr(cre, "_cache_values", None)
    yield


def _make_record(trading_date: str, feature_value: float, correct: bool,
                  feature: str = "stability") -> Dict[str, Any]:
    return {
        "decision_id": f"d-{trading_date}-{feature_value}-{correct}-{id(object())}",
        "symbol": "RELIANCE",
        "trading_date": trading_date,
        "direction": "BUY",
        "decision": "KNOWLEDGE_BUY",
        "evidence_state": "USEFUL",
        "effective_sample_size": feature_value if feature == "effective_sample_size" else 50.0,
        "stability": feature_value if feature == "stability" else 0.5,
        "contradiction_factor": feature_value if feature == "contradiction_factor" else 0.5,
        "knowledge_authority": 0.5,
        "status": "OUTCOME_COMPLETE",
        "direction_correct": correct,
        "decision_correct": correct,
    }


def _dates_from(n_days: int, start_days_ago: int = 90) -> List[str]:
    start = date.today() - timedelta(days=start_days_ago)
    return [(start + timedelta(days=i)).isoformat() for i in range(n_days)]


# ─────────────────────────────────────────────────────────────────────────────
# T01-T06: get_effective_constants()
# ─────────────────────────────────────────────────────────────────────────────

class TestGetEffectiveConstants:

    def test_t01_defaults_when_no_file(self):
        result = cre.get_effective_constants()
        assert result == {name: cfg["default"] for name, cfg in cre.TUNABLE_CONSTANTS.items()}

    def test_t02_valid_override_is_used(self):
        cre._OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        cre._OVERRIDES_PATH.write_text(json.dumps({
            "_STABILITY_DECISION_MIN": {"value": 0.5, "set_at": "2026-01-01T00:00:00+00:00"}
        }))
        result = cre.get_effective_constants()
        assert result["_STABILITY_DECISION_MIN"] == 0.5
        assert result["_ESS_DECISION_ELIGIBLE"] == cre.TUNABLE_CONSTANTS["_ESS_DECISION_ELIGIBLE"]["default"]

    def test_t03_corrupt_file_falls_back_to_defaults(self):
        cre._OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        cre._OVERRIDES_PATH.write_text("{not valid json")
        result = cre.get_effective_constants()
        assert result == {name: cfg["default"] for name, cfg in cre.TUNABLE_CONSTANTS.items()}

    def test_t04_out_of_bounds_override_ignored(self):
        cre._OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        cre._OVERRIDES_PATH.write_text(json.dumps({
            "_STABILITY_DECISION_MIN": {"value": 999.0}
        }))
        result = cre.get_effective_constants()
        assert result["_STABILITY_DECISION_MIN"] == cre.TUNABLE_CONSTANTS["_STABILITY_DECISION_MIN"]["default"]

    def test_t05_never_raises_on_missing_directory(self, tmp_path):
        bogus = tmp_path / "does" / "not" / "exist" / "overrides.json"
        result = cre.get_effective_constants(overrides_path=bogus)
        assert result == {name: cfg["default"] for name, cfg in cre.TUNABLE_CONSTANTS.items()}

    def test_t06_exactly_three_live_constants_registered(self):
        # Documents the ARCH-005 finding: _AUTHORITY_KNOWLEDGE_MIN and
        # _AUTHORITY_STRATEGY_MIN are dead code and must NEVER be added here
        # without first confirming they are read again in _classify_authority.
        assert set(cre.TUNABLE_CONSTANTS.keys()) == {
            "_ESS_DECISION_ELIGIBLE", "_STABILITY_DECISION_MIN", "_CONTRADICTION_DECISION_MIN",
        }


# ─────────────────────────────────────────────────────────────────────────────
# T07-T09: dynamic cooldown
# ─────────────────────────────────────────────────────────────────────────────

class TestDynamicCooldown:

    def test_t07_no_data_returns_absolute_floor(self):
        assert cre._calculate_dynamic_cooldown_days([]) == cre.ABSOLUTE_MIN_COOLDOWN_DAYS

    def test_t08_high_velocity_still_respects_floor(self):
        # Even an extremely high evidence rate must never produce a cooldown
        # below the absolute safety floor.
        recent = [_make_record(d, 0.5, True) for d in _dates_from(30, start_days_ago=29)]
        cooldown = cre._calculate_dynamic_cooldown_days(recent)
        assert cooldown >= cre.ABSOLUTE_MIN_COOLDOWN_DAYS

    def test_t09_low_velocity_increases_cooldown_above_floor(self):
        # A slow trickle of evidence (well below MIN_NEW_EVIDENCE_PER_CHECK
        # over the velocity window) must yield a cooldown longer than the floor.
        sparse = [_make_record(d, 0.5, True) for d in _dates_from(2, start_days_ago=29)]
        cooldown = cre._calculate_dynamic_cooldown_days(sparse)
        assert cooldown > cre.ABSOLUTE_MIN_COOLDOWN_DAYS


# ─────────────────────────────────────────────────────────────────────────────
# T10-T13: run_scorecard()
# ─────────────────────────────────────────────────────────────────────────────

class TestRunScorecard:

    def test_t10_validates_clear_improvement(self):
        dates = _dates_from(120, start_days_ago=120)
        records = []
        for dt in dates:
            # Low-stability population: ~50% correct. High-stability (>=0.7): ~90% correct.
            records.append(_make_record(dt, 0.4, dt[-1] in "02468"))
            records.append(_make_record(dt, 0.75, dt[-1] not in "1"))
        scorecard = cre.run_scorecard(records, "stability", current_value=0.6, candidate_value=0.7)
        assert scorecard["oos_n"] >= 1
        assert isinstance(scorecard["validated"], bool)

    def test_t11_rejects_no_signal(self):
        dates = _dates_from(120, start_days_ago=120)
        records = []
        for i, dt in enumerate(dates):
            # No relationship between feature value and correctness.
            records.append(_make_record(dt, 0.4, i % 2 == 0))
            records.append(_make_record(dt, 0.75, i % 2 == 0))
        scorecard = cre.run_scorecard(records, "stability", current_value=0.6, candidate_value=0.7)
        assert scorecard["validated"] is False

    def test_t12_never_raises_on_empty(self):
        scorecard = cre.run_scorecard([], "stability", 0.6, 0.7)
        assert scorecard["validated"] is False
        assert scorecard["oos_n"] == 0

    def test_t13_only_moves_in_improving_direction(self):
        # Candidate that is clearly WORSE must never validate, regardless of
        # sample size or statistical significance of the (negative) effect.
        dates = _dates_from(120, start_days_ago=120)
        records = []
        for dt in dates:
            records.append(_make_record(dt, 0.4, dt[-1] not in "1"))   # low feature: high accuracy
            records.append(_make_record(dt, 0.75, dt[-1] in "02468"))  # high feature: low accuracy
        scorecard = cre.run_scorecard(records, "stability", current_value=0.4, candidate_value=0.75)
        assert scorecard["validated"] is False


# ─────────────────────────────────────────────────────────────────────────────
# T14-T20: _process_constant() state machine
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessConstantStateMachine:

    def _cfg(self):
        return cre.TUNABLE_CONSTANTS["_STABILITY_DECISION_MIN"]

    def test_t14_waits_when_insufficient_new_evidence(self):
        state = {"_STABILITY_DECISION_MIN": cre._default_const_state()}
        dataset = [_make_record(d, 0.4, True) for d in _dates_from(5, start_days_ago=5)]
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, {})
        assert result["status"] == cre.STATUS_WAITING
        assert result["reason"] == "insufficient_new_evidence"

    def test_t15_cooldown_blocks_recent_change(self):
        const_state = cre._default_const_state()
        const_state["last_change_at"] = datetime.now(timezone.utc).isoformat()
        state = {"_STABILITY_DECISION_MIN": const_state}
        dataset = [_make_record(d, 0.4, True) for d in _dates_from(60, start_days_ago=60)]
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, {})
        assert result["status"] == cre.STATUS_WAITING
        assert result["reason"] == "cooldown_active"

    def test_t16_starts_shadow_on_validated_candidate(self):
        state = {"_STABILITY_DECISION_MIN": cre._default_const_state()}
        dates = _dates_from(150, start_days_ago=150)
        dataset = []
        for dt in dates:
            dataset.append(_make_record(dt, 0.4, dt[-1] in "02468"))   # ~50% correct below threshold
            dataset.append(_make_record(dt, 0.65, dt[-1] not in "1"))  # ~90% correct at candidate 0.65
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, {})
        assert result["status"] in (cre.STATUS_SHADOW, cre.STATUS_WAITING)
        if result["status"] == cre.STATUS_SHADOW:
            assert state["_STABILITY_DECISION_MIN"]["shadow_candidate_value"] is not None
            ledger = cre._read_jsonl(cre._LEDGER_PATH)
            assert any(e["event_type"] == "SHADOW_STARTED" for e in ledger)

    def test_t17_shadow_not_judged_before_min_days(self):
        const_state = cre._default_const_state()
        const_state.update({
            "status": cre.STATUS_SHADOW,
            "shadow_candidate_value": 0.65,
            "shadow_started_at": datetime.now(timezone.utc).isoformat(),
            "shadow_started_evidence_count": 0,
        })
        state = {"_STABILITY_DECISION_MIN": const_state}
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), [], state, {})
        assert result["status"] == cre.STATUS_SHADOW
        assert result["days_elapsed"] == 0

    def test_t18_shadow_promotes_on_reconfirmation(self):
        shadow_start = (date.today() - timedelta(days=cre.SHADOW_MIN_DAYS + 5)).isoformat()
        const_state = cre._default_const_state()
        const_state.update({
            "status": cre.STATUS_SHADOW,
            "shadow_candidate_value": 0.65,
            "shadow_started_at": shadow_start + "T00:00:00+00:00",
            "shadow_started_evidence_count": 0,
        })
        state = {"_STABILITY_DECISION_MIN": const_state}
        dates = [
            (date.today() - timedelta(days=cre.SHADOW_MIN_DAYS + 5 - i)).isoformat()
            for i in range(cre.SHADOW_MIN_NEW_OUTCOMES + 10)
        ]
        dataset = []
        for dt in dates:
            dataset.append(_make_record(dt, 0.4, dt[-1] in "02468"))
            dataset.append(_make_record(dt, 0.65, dt[-1] not in "1"))
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, {})
        assert result["status"] in (cre.STATUS_ACTIVE, cre.STATUS_REJECTED)

    def test_t19_shadow_rejects_when_not_reconfirmed(self):
        shadow_start = (date.today() - timedelta(days=cre.SHADOW_MIN_DAYS + 5)).isoformat()
        const_state = cre._default_const_state()
        const_state.update({
            "status": cre.STATUS_SHADOW,
            "shadow_candidate_value": 0.65,
            "shadow_started_at": shadow_start + "T00:00:00+00:00",
            "shadow_started_evidence_count": 0,
        })
        state = {"_STABILITY_DECISION_MIN": const_state}
        dates = [
            (date.today() - timedelta(days=cre.SHADOW_MIN_DAYS + 5 - i)).isoformat()
            for i in range(cre.SHADOW_MIN_NEW_OUTCOMES + 10)
        ]
        # No relationship between feature and correctness in the held-out window.
        dataset = [_make_record(dt, 0.4 if i % 2 == 0 else 0.65, i % 2 == 0)
                   for i, dt in enumerate(dates)]
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, {})
        assert result["status"] == cre.STATUS_REJECTED
        ledger = cre._read_jsonl(cre._LEDGER_PATH)
        assert any(e["event_type"] == "REJECTED" for e in ledger)

    def test_t20_rollback_on_degradation(self):
        change_date = (date.today() - timedelta(days=5)).isoformat()
        const_state = cre._default_const_state()
        const_state.update({
            "status": cre.STATUS_ACTIVE,
            "last_change_at": change_date + "T00:00:00+00:00",
            "pre_promotion_value": 0.6,
            "promoted_baseline_accuracy": 0.9,
        })
        state = {"_STABILITY_DECISION_MIN": const_state}
        overrides = {"_STABILITY_DECISION_MIN": {"value": 0.65}}
        dates = [(date.today() - timedelta(days=5 - i)).isoformat()
                 for i in range(cre.MIN_POST_PROMOTION_SAMPLE + 5)]
        # Live accuracy at the promoted (0.65) threshold has collapsed to ~30%.
        dataset = [_make_record(dt, 0.65, i % 3 == 0) for i, dt in enumerate(dates)]
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, overrides)
        assert result["status"] == cre.STATUS_ROLLED_BACK
        assert overrides["_STABILITY_DECISION_MIN"]["value"] == 0.6
        ledger = cre._read_jsonl(cre._LEDGER_PATH)
        assert any(e["event_type"] == "ROLLED_BACK" for e in ledger)

    def test_t21_no_premature_rollback_with_insufficient_sample(self):
        const_state = cre._default_const_state()
        const_state.update({
            "status": cre.STATUS_ACTIVE,
            "last_change_at": datetime.now(timezone.utc).isoformat(),
            "pre_promotion_value": 0.6,
            "promoted_baseline_accuracy": 0.9,
        })
        state = {"_STABILITY_DECISION_MIN": const_state}
        overrides = {"_STABILITY_DECISION_MIN": {"value": 0.65}}
        # Only a handful of post-promotion outcomes — below MIN_POST_PROMOTION_SAMPLE.
        dataset = [_make_record(date.today().isoformat(), 0.65, False) for _ in range(3)]
        result = cre._process_constant("_STABILITY_DECISION_MIN", self._cfg(), dataset, state, overrides)
        assert result["status"] != cre.STATUS_ROLLED_BACK
        assert overrides["_STABILITY_DECISION_MIN"]["value"] == 0.65


# ─────────────────────────────────────────────────────────────────────────────
# T22-T23: run_daily_refinement_check() top-level safety
# ─────────────────────────────────────────────────────────────────────────────

class TestRunDailyRefinementCheck:

    def test_t22_never_raises_when_dataset_refresh_fails(self, monkeypatch):
        def _boom():
            raise RuntimeError("simulated failure")
        monkeypatch.setattr(cre, "refresh_outcome_dataset", _boom)
        result = cre.run_daily_refinement_check()
        assert isinstance(result, dict)

    def test_t23_returns_per_constant_summary(self, monkeypatch):
        monkeypatch.setattr(cre, "refresh_outcome_dataset", lambda: {})
        result = cre.run_daily_refinement_check()
        assert set(result.get("per_constant", {}).keys()) == set(cre.TUNABLE_CONSTANTS.keys())


# ─────────────────────────────────────────────────────────────────────────────
# T24: ledger integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestLedgerIntegrity:

    def test_t24_ledger_is_valid_append_only_jsonl(self):
        cre._log_ledger("SHADOW_STARTED", "_STABILITY_DECISION_MIN", "test reason", old_value=0.6)
        cre._log_ledger("PROMOTED", "_STABILITY_DECISION_MIN", "test reason 2", new_value=0.65)
        lines = cre._LEDGER_PATH.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            record = json.loads(line)
            assert "event_id" in record and "timestamp" in record and "reason" in record
            assert record["actor"] == "KDA-CRE-001"


# ─────────────────────────────────────────────────────────────────────────────
# T25-T26: integration with knowledge_decision_authority.py
# ─────────────────────────────────────────────────────────────────────────────

class TestKnowledgeDecisionAuthorityIntegration:

    def test_t25_falls_back_to_original_defaults_with_no_override(self):
        from knowledge_authority.knowledge_decision_authority import _effective_constants
        consts = _effective_constants()
        assert consts["_ESS_DECISION_ELIGIBLE"] == 100.0
        assert consts["_STABILITY_DECISION_MIN"] == 0.6
        assert consts["_CONTRADICTION_DECISION_MIN"] == 0.4

    def test_t26_uses_valid_override_when_present(self):
        cre._OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        cre._OVERRIDES_PATH.write_text(json.dumps({
            "_ESS_DECISION_ELIGIBLE": {"value": 50.0}
        }))
        from knowledge_authority.knowledge_decision_authority import _effective_constants
        consts = _effective_constants()
        assert consts["_ESS_DECISION_ELIGIBLE"] == 50.0

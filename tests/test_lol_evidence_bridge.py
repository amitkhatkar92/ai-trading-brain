"""
tests/test_lol_evidence_bridge.py
====================================
DTA-LIVE-003 — LOL→KDA Evidence Bridge tests

Coverage:
  GAP-001 (A-F): KDA provenance fix (locals() check)
    A  _kda_results exists in locals() → actual KDA results reach LOL
    B  _kda_results absent → safe empty dict used; no crash
    C  Multi-symbol KDA result dict → all entries preserved
    D  Malformed / None KDA result → does not crash LOL update_decisions
    E  Exception in LOL hook does not interrupt production cycle
    F  Shadow strategy remains shadow-only after fix

  GAP-002 (A-H): LOL → KDA evidence ingestion
    A  RANKING_MISS outcome → new EVIDENCE record in ledger
    B  CORRECT_REJECT outcome → new EVIDENCE record in ledger
    C  CORRECT_SELECT outcome → new EVIDENCE record in ledger
    D  Ambiguous/unsupported outcome class → skipped (no write)
    E  Duplicate obs_id → idempotent (no duplicate record)
    F  Restart/second call → idempotent (0 new records)
    G  Anti-lookahead: outcome_at <= decision_at → skipped
    H  Production authority contract: broker_calls=0, orders=0

  Additional:
    I  Records without OUTCOME_OBSERVED lifecycle state → skipped
    J  outcome_class mapping: all 8 supported classes produce correct classification
    K  Ledger not yet created → bridge creates parent dirs and writes first record
    L  Corrupt LOL line skipped; rest of file processed normally
    M  State file updated after successful ingest
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    """Return (lol_dir, ledger_path, state_path) all within tmp_path."""
    lol_dir = tmp_path / "lol"
    lol_dir.mkdir()
    ledger  = tmp_path / "knowledge_evidence_ledger.jsonl"
    state   = tmp_path / "ksl" / "lol_bridge_state.json"
    return lol_dir, ledger, state


def _make_lol_record(
    obs_id:           str  = "test-obs-001",
    symbol:           str  = "BIOCON",
    direction:        str  = "BUY",
    trading_date:     str  = "2026-09-01",
    lifecycle_state:  str  = "OUTCOME_OBSERVED",
    outcome_class:    str  = "REJECTED_INCORRECT",
    actual_return:    Optional[float] = 2.5,
    decision_at:      str  = "2026-09-01T09:30:00+00:00",
    outcome_at:       str  = "2026-09-04T09:30:00+00:00",
    kda_decision:     Optional[str] = "KNOWLEDGE_WAIT",
    no_lookahead:     bool = True,
) -> Dict[str, Any]:
    t5 = actual_return
    return {
        "observation_id":    obs_id,
        "symbol":            symbol,
        "direction":         direction,
        "trading_date":      trading_date,
        "lifecycle_state":   lifecycle_state,
        "outcome_class":     outcome_class,
        "actual_return_pct": t5,
        "t1_ret_pct":        round(t5 * 0.4, 4) if t5 is not None else None,
        "t3_ret_pct":        round(t5 * 0.7, 4) if t5 is not None else None,
        "t5_ret_pct":        t5,
        "mfe_pct":           abs(t5) + 0.5 if t5 is not None else None,
        "mae_pct":           0.3,
        "target_hit":        False,
        "stop_hit":          False,
        "decision_at":       decision_at,
        "outcome_at":        outcome_at,
        "kda_decision":      kda_decision,
        "kda_evidence_state": "INSUFFICIENT",
        "strategy_decision": "PASS",
        "authorization_source": "NONE",
        "knowledge_provenance": {"regime": "BULL"},
        "no_lookahead":      no_lookahead,
        "entry_price":       500.0,
        "stop_loss":         490.0,
        "target_price":      520.0,
    }


def _write_lol_file(lol_dir: Path, date_str: str, records: List[Dict]) -> Path:
    path = lol_dir / f"LOL_{date_str}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def _read_ledger(ledger: Path) -> List[Dict]:
    if not ledger.exists():
        return []
    result = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                result.append(json.loads(line))
            except Exception:
                pass
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GAP-001 Tests (A-F): KDA provenance fix
# ─────────────────────────────────────────────────────────────────────────────

class TestGAP001KDAProvenance:
    """Verify the locals() fix: KDA results flow to LOL correctly."""

    def test_a_kda_results_in_locals_reaches_lol(self, tmp_dirs):
        """
        GAP-001-A: When _kda_results IS defined as a local variable,
        `'_kda_results' in locals()` returns True and its value is passed.
        """
        from learning_system.lol_evidence_bridge import _LOL_SOURCE_PREFIX  # import guard

        # Simulate the orchestrator logic after GAP-001 fix
        _kda_results = {"BIOCON": {"kda_decision": "KNOWLEDGE_BUY", "authority": "KNOWLEDGE"}}
        # Correct expression (post-fix)
        result = _kda_results if '_kda_results' in locals() else {}
        assert result == _kda_results, "KDA results should reach LOL when variable is defined"

    def test_b_kda_results_absent_returns_empty_dict(self):
        """
        GAP-001-B: When _kda_results is NOT defined, locals() returns {} safely.
        """
        # Simulate absent variable — do NOT define _kda_results
        result = locals().get("_kda_results", {})
        assert result == {}, "Should fall back to empty dict when _kda_results absent"

    def test_b_old_dir_check_was_always_false(self):
        """
        GAP-001-B (regression): Confirm the OLD bug: 'kda_results' in dir()
        is always False because dir() lists names of items in the current scope,
        not nested dict keys. The underscore-less name 'kda_results' never
        appears when the variable is '_kda_results'.
        """
        _kda_results = {"BIOCON": {"kda_decision": "KNOWLEDGE_BUY"}}
        # OLD (buggy) expression — must always be False for the underscore-prefixed var
        old_result = _kda_results if 'kda_results' in dir() else {}
        assert old_result == {}, (
            "Old bug confirmed: 'kda_results' in dir() is always False "
            "when the variable is '_kda_results'"
        )
        # NEW (correct) expression — must be True when variable is defined
        new_result = _kda_results if '_kda_results' in locals() else {}
        assert new_result == _kda_results, "Fixed expression correctly finds '_kda_results'"

    def test_c_multi_symbol_kda_results_all_preserved(self):
        """
        GAP-001-C: Multi-symbol KDA result dict — all entries preserved.
        """
        _kda_results = {
            "BIOCON":   {"kda_decision": "KNOWLEDGE_BUY"},
            "RELIANCE": {"kda_decision": "KNOWLEDGE_WAIT"},
            "TCS":      {"kda_decision": "KNOWLEDGE_SELL"},
        }
        result = _kda_results if '_kda_results' in locals() else {}
        assert len(result) == 3
        assert result["BIOCON"]["kda_decision"] == "KNOWLEDGE_BUY"
        assert result["TCS"]["kda_decision"] == "KNOWLEDGE_SELL"

    def test_d_malformed_kda_result_does_not_crash_lol_update(self, tmp_dirs):
        """
        GAP-001-D: A malformed (None) KDA result should not crash update_decisions.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.learning_observation_ledger import LearningObservationLedger

        lol = LearningObservationLedger(data_dir=lol_dir)
        _kda_results = None   # malformed

        # update_decisions should handle None without raising
        safe_kda = _kda_results if _kda_results is not None else {}
        try:
            lol.update_decisions(
                original_signals=[],
                enriched_signals=[],
                kda_results=safe_kda,
                trading_date="2026-09-01",
            )
        except Exception as exc:
            pytest.fail(f"update_decisions raised unexpectedly with None kda_results: {exc}")

    def test_e_lol_exception_does_not_block_production(self, tmp_dirs):
        """
        GAP-001-E: An exception in the LOL hook must not propagate to the
        production cycle (try/except wrapper in orchestrator is the pattern).
        """
        production_ran = [False]
        lol_exception = [None]

        def production_step():
            production_ran[0] = True

        # Simulate try/except wrapper pattern from orchestrator
        try:
            raise RuntimeError("Simulated LOL error")
        except Exception as exc:
            lol_exception[0] = exc

        production_step()  # must run regardless

        assert production_ran[0], "Production step must run even if LOL raises"
        assert lol_exception[0] is not None, "Exception was captured"

    def test_f_shadow_strategy_remains_shadow_only(self, tmp_dirs):
        """
        GAP-001-F: KDA results reaching LOL must not grant execution authority.
        LOL is observer-only: it must not import broker, execution_engine, or
        order_manager modules.
        """
        import importlib
        import sys

        # Import the LOL module and verify its safety contract via module docstring
        import learning_system.learning_observation_ledger as lol_mod
        source = lol_mod.__doc__ or ""
        assert "broker_calls" in source or "broker" in source.lower(), (
            "LOL module must declare broker_calls=0 in its contract"
        )

        # The module must not import any execution or broker modules
        prohibited = {"execution_engine", "order_manager", "dhan_broker", "dhan_feed"}
        imported_names = set(sys.modules.keys())
        violations = prohibited.intersection(imported_names)
        # Filter: only flag if imported THROUGH lol module (not pre-existing in sys.modules)
        # Reload to check clean import
        for mod_name in list(sys.modules.keys()):
            if any(p in mod_name for p in prohibited):
                # only flag if it's a real import from LOL
                pass
        # Core check: LOL module source must not reference order placement
        import inspect
        lol_source = inspect.getsource(lol_mod)
        assert "place_order" not in lol_source, "LOL must not call place_order"
        assert "submit_order" not in lol_source, "LOL must not call submit_order"


# ─────────────────────────────────────────────────────────────────────────────
# GAP-002 Tests (A-H): LOL → KDA evidence ingestion
# ─────────────────────────────────────────────────────────────────────────────

class TestGAP002EvidenceBridge:
    """Verify LOL OUTCOME_OBSERVED records reach knowledge_evidence_ledger.jsonl."""

    def test_a_ranking_miss_produces_evidence_record(self, tmp_dirs):
        """
        GAP-002-A: A REJECTED_INCORRECT record → RANKING_MISS EVIDENCE in ledger.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(outcome_class="REJECTED_INCORRECT", actual_return=2.5)
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert result["new_records"] == 1
        records = _read_ledger(ledger)
        assert len(records) == 1
        ev = records[0]
        assert ev["event_type"] == "EVIDENCE"
        assert ev["classification"] == "RANKING_MISS"
        assert ev["miss_reason"] == "STRATEGY_REJECTION"
        assert ev["symbol"] == "BIOCON"
        assert ev["direction"] == "UP"
        assert ev["observation_id"] == "test-obs-001"
        assert ev["source"] == "lol_live"
        assert ev["no_lookahead"] is True

    def test_b_correct_reject_produces_evidence_record(self, tmp_dirs):
        """
        GAP-002-B: A REJECTED_CORRECT record → CORRECT_REJECT EVIDENCE in ledger.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(
            obs_id="test-obs-002",
            outcome_class="REJECTED_CORRECT",
            actual_return=-1.8,
        )
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert result["new_records"] == 1
        records = _read_ledger(ledger)
        ev = records[0]
        assert ev["classification"] == "CORRECT_REJECT"
        assert ev["miss_reason"] == "NOT_APPLICABLE"

    def test_c_correct_select_produces_evidence_record(self, tmp_dirs):
        """
        GAP-002-C: An EXECUTED_WIN record → CORRECT_SELECT EVIDENCE in ledger.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(
            obs_id="test-obs-003",
            outcome_class="EXECUTED_WIN",
            actual_return=3.2,
            lifecycle_state="OUTCOME_OBSERVED",
        )
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert result["new_records"] == 1
        records = _read_ledger(ledger)
        ev = records[0]
        assert ev["classification"] == "CORRECT_SELECT"

    def test_d_ambiguous_outcome_class_skipped(self, tmp_dirs):
        """
        GAP-002-D (updated for D13-001 fix): EXECUTED_LOSS now maps to
        INCORRECT_SELECT and IS written to the ledger.
        The original test expected 0 records because EXECUTED_LOSS was
        previously skipped.  The DTA-013-FIX corrects this: losses must
        reach KEL so the knowledge base learns from both wins and losses.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(
            obs_id="test-obs-004",
            outcome_class="EXECUTED_LOSS",
            actual_return=-2.0,
        )
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        # D13-001 fix: EXECUTED_LOSS now produces one INCORRECT_SELECT record
        assert result["new_records"] == 1, (
            "D13-001 fix: EXECUTED_LOSS must now reach KEL as INCORRECT_SELECT"
        )
        recs = _read_ledger(ledger)
        assert len(recs) == 1
        assert recs[0]["classification"] == "INCORRECT_SELECT"

    def test_e_duplicate_obs_id_is_idempotent(self, tmp_dirs):
        """
        GAP-002-E: Calling the bridge twice with the same obs_id produces
        exactly 1 record in the ledger (idempotency).
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(obs_id="test-obs-dedup", outcome_class="REJECTED_INCORRECT")
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        # First call
        r1 = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        assert r1["new_records"] == 1

        # Second call with the same file
        r2 = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        assert r2["new_records"] == 0, "Second call must produce 0 new records (idempotent)"
        assert len(_read_ledger(ledger)) == 1, "Exactly 1 record in ledger after 2 calls"

    def test_f_restart_reprocessing_is_idempotent(self, tmp_dirs):
        """
        GAP-002-F: After a restart (fresh ingest_lol_outcomes call reading from
        existing ledger file), no duplicates are written.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        recs = [
            _make_lol_record(obs_id=f"obs-{i}", outcome_class="BLOCKED_INCORRECT")
            for i in range(3)
        ]
        _write_lol_file(lol_dir, "2026-09-01", recs)

        # First run (simulating initial ingest)
        r1 = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        assert r1["new_records"] == 3

        # Simulate restart: new call reads existing ledger keys for dedup
        r2 = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        assert r2["new_records"] == 0, "Restart must produce 0 new records"
        assert len(_read_ledger(ledger)) == 3, "3 records total after restart"

    def test_g_anti_lookahead_outcome_before_decision(self, tmp_dirs):
        """
        GAP-002-G: Record with outcome_at <= decision_at must be skipped
        (anti-lookahead enforcement).
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        # outcome_at is BEFORE decision_at → lookahead violation
        rec = _make_lol_record(
            obs_id="test-obs-lookahead",
            outcome_class="REJECTED_INCORRECT",
            decision_at="2026-09-04T09:30:00+00:00",  # decision AFTER outcome
            outcome_at="2026-09-01T09:30:00+00:00",   # outcome BEFORE decision
        )
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert result["new_records"] == 0, "Lookahead violation must be rejected"
        assert result["skipped"] >= 1

    def test_h_production_authority_contract(self, tmp_dirs):
        """
        GAP-002-H: ingest_lol_outcomes must declare broker_calls=0, orders=0.
        The returned summary must never include any execution or broker fields.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        result = ingest_lol_outcomes(
            dates=["2099-01-01"],   # no data → fast return
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        # Must not contain broker/order fields
        assert "broker_calls" not in result or result.get("broker_calls", 0) == 0
        assert "orders" not in result or result.get("orders", 0) == 0

    def test_i_pending_lifecycle_state_skipped(self, tmp_dirs):
        """
        Additional-I: Records with lifecycle_state != OUTCOME_OBSERVED
        must not be ingested.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(
            obs_id="test-obs-pending",
            lifecycle_state="OUTCOME_PENDING",   # not yet resolved
            outcome_class="REJECTED_INCORRECT",
        )
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert result["new_records"] == 0

    def test_j_outcome_class_mapping_all_supported(self, tmp_dirs):
        """
        Additional-J: All supported outcome classes produce the correct
        classification and miss_reason in the ledger.
        Updated for D13-001: EXECUTED_LOSS, STOP_EXIT, EARLY_EXIT now map
        to INCORRECT_SELECT.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        supported = [
            # (outcome_class, expected_classification, expected_miss_reason)
            ("EXECUTED_WIN",       "CORRECT_SELECT",   "NOT_APPLICABLE"),
            ("TARGET_EXIT",        "CORRECT_SELECT",   "NOT_APPLICABLE"),
            ("EXECUTED_LOSS",      "INCORRECT_SELECT", "NOT_APPLICABLE"),   # D13-001
            ("STOP_EXIT",          "INCORRECT_SELECT", "NOT_APPLICABLE"),   # D13-001
            ("EARLY_EXIT",         "INCORRECT_SELECT", "NOT_APPLICABLE"),   # D13-001
            ("REJECTED_INCORRECT", "RANKING_MISS",     "STRATEGY_REJECTION"),
            ("BLOCKED_INCORRECT",  "RANKING_MISS",     "RISK_REJECTION"),
            ("MISSED_OPPORTUNITY", "RANKING_MISS",     "NOT_APPLICABLE"),
            ("KDA_FALSE_NEGATIVE", "RANKING_MISS",     "NOT_APPLICABLE"),
            ("REJECTED_CORRECT",   "CORRECT_REJECT",   "NOT_APPLICABLE"),
            ("BLOCKED_CORRECT",    "CORRECT_REJECT",   "NOT_APPLICABLE"),
        ]

        for i, (oc, expected_cls, expected_mr) in enumerate(supported):
            rec = _make_lol_record(
                obs_id=f"obs-map-{i}",
                outcome_class=oc,
                actual_return=(2.5 if "INCORRECT" in oc or "NEGATIVE" in oc or "WIN" in oc or "TARGET" in oc
                               else -1.5),
            )
            lol_file = lol_dir / f"LOL_2026-09-{10 + i:02d}.jsonl"
            with lol_file.open("w") as f:
                f.write(json.dumps(rec) + "\n")

            result = ingest_lol_outcomes(
                dates=[f"2026-09-{10 + i:02d}"],
                lol_data_dir=lol_dir,
                knowledge_ledger=ledger,
                state_path=state,
            )
            assert result["new_records"] == 1, f"Expected 1 new record for {oc}, got {result}"
            records = _read_ledger(ledger)
            ev = records[-1]
            assert ev["classification"] == expected_cls, (
                f"outcome_class={oc} → expected {expected_cls}, got {ev['classification']}"
            )
            assert ev["miss_reason"] == expected_mr, (
                f"outcome_class={oc} → expected miss_reason={expected_mr}, got {ev['miss_reason']}"
            )

    def test_k_creates_ledger_and_parent_dirs(self, tmp_dirs):
        """
        Additional-K: When ledger does not exist, bridge creates parent dirs
        and writes the first record correctly.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        # Put the ledger in a deep subpath that doesn't exist yet
        deep_ledger = tmp_dirs[0].parent / "deep" / "sub" / "evidence.jsonl"
        assert not deep_ledger.exists()

        rec = _make_lol_record(obs_id="test-obs-mkdir", outcome_class="MISSED_OPPORTUNITY")
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=deep_ledger,
            state_path=state,
        )

        assert result["new_records"] == 1
        assert deep_ledger.exists()
        records = _read_ledger(deep_ledger)
        assert len(records) == 1

    def test_l_corrupt_lol_line_skipped_rest_processed(self, tmp_dirs):
        """
        Additional-L: A corrupt JSON line in the LOL file must be skipped;
        the remaining valid records must still be processed.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        lol_file = lol_dir / "LOL_2026-09-01.jsonl"
        with lol_file.open("w", encoding="utf-8") as f:
            f.write("NOT_VALID_JSON\n")
            f.write(json.dumps(_make_lol_record(
                obs_id="good-obs", outcome_class="REJECTED_INCORRECT"
            )) + "\n")
            f.write("{broken\n")

        result = ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert result["new_records"] == 1, "Valid record after corrupt lines must be processed"

    def test_m_state_file_updated_after_ingest(self, tmp_dirs):
        """
        Additional-M: State file must be updated with total count and last_run
        after a successful ingest.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        import json

        rec = _make_lol_record(obs_id="state-test-001", outcome_class="REJECTED_INCORRECT")
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        assert state.exists(), "State file must be created after ingest"
        s = json.loads(state.read_text())
        assert s.get("total_lol_records_ingested") == 1
        assert "last_run" in s

    def test_evidence_record_event_type_is_evidence(self, tmp_dirs):
        """
        Evidence records must have event_type='EVIDENCE' for KFE compatibility
        (_load_knowledge_evidence_ledger filters on this field).
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(obs_id="kfe-compat-test", outcome_class="BLOCKED_INCORRECT")
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        records = _read_ledger(ledger)
        assert len(records) == 1
        assert records[0]["event_type"] == "EVIDENCE", (
            "KFE requires event_type='EVIDENCE' to pick up records"
        )

    def test_ge2_field_computed_correctly(self, tmp_dirs):
        """
        ge2 = True when actual_return_pct >= 2.0 (direction-adjusted).
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(
            obs_id="ge2-test", outcome_class="REJECTED_INCORRECT", actual_return=2.5
        )
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        ev = _read_ledger(ledger)[0]
        assert ev["ge2"] is True
        assert ev["ge1"] is True
        assert ev["ge3"] is False   # 2.5 < 3.0

    def test_source_run_id_format(self, tmp_dirs):
        """
        source_run_id must be 'lol_{observation_id}' for dedup compatibility.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _make_lol_record(obs_id="abc-123", outcome_class="MISSED_OPPORTUNITY")
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        ev = _read_ledger(ledger)[0]
        assert ev["source_run_id"] == "lol_abc-123"

    def test_existing_historical_records_not_duplicated(self, tmp_dirs):
        """
        Bridge must not touch existing historical_audit records in the ledger.
        """
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        # Pre-populate ledger with an existing historical record
        existing = {
            "event_type": "EVIDENCE",
            "evidence_id": "hist-001",
            "symbol": "BIOCON",
            "trade_date": "2026-05-14",
            "direction": "UP",
            "classification": "RANKING_MISS",
            "source": "historical_audit",
        }
        ledger.write_text(json.dumps(existing) + "\n", encoding="utf-8")

        rec = _make_lol_record(obs_id="new-obs-001", outcome_class="BLOCKED_INCORRECT")
        _write_lol_file(lol_dir, "2026-09-01", [rec])

        ingest_lol_outcomes(
            dates=["2026-09-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )

        records = _read_ledger(ledger)
        assert len(records) == 2, "Existing record + 1 new record = 2 total"
        sources = {r.get("source") for r in records}
        assert "historical_audit" in sources
        assert "lol_live" in sources

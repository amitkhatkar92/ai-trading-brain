"""
tests/test_dta_live_005.py
============================
DTA-LIVE-005: Learning Last-Mile — comprehensive test suite.

Tests (A–W, 23 minimum):
  A: sector_flows fix — non-empty List[SectorFlow] converts without TypeError
  B: sector_flows fix — empty sector_flows returns empty dict
  C: sector_flows fix — None / missing sector_flows returns empty dict
  D: sector_flows fix — SectorFlow without sector_name attribute is skipped
  E: KDA pipeline error → LOL records KDA_PIPELINE_ERROR, not KNOWLEDGE_INSUFFICIENT_EVIDENCE
  F: KDA not reached (empty results dict) → LOL records KDA_NOT_REACHED
  G: Genuine KDA insufficient evidence → LOL records KNOWLEDGE_INSUFFICIENT_EVIDENCE (not error sentinel)
  H: KDA genuine decision (KNOWLEDGE_BUY) passes through unchanged
  I: CRE QTY_ZERO → update_cre_blocking records BLOCKED with block_reason
  J: CRE block sets strategy_decision="PASS" (strategy approved)
  K: CRE block preserves prior kda_decision if already set
  L: CRE block fills kda_decision=KDA_NOT_REACHED when missing
  M: update_cre_blocking on unknown obs_id → returns 0, no crash
  N: update_cre_blocking multiple signals → all get block_reason recorded
  O: Recovery records have lifecycle_state="OUTCOME_PENDING" (not "OBSERVED")
  P: Recovery records have kda_decision="KDA_NOT_REACHED"
  Q: Recovery records have strategy_decision="NOT_REACHED"
  R: Recovery is idempotent — running twice skips duplicates
  S: Recovery no_lookahead=True preserved
  T: fill_pending_outcomes honours anti-lookahead (T+1 > today → skip)
  U: fill_pending_outcomes processes OUTCOME_PENDING recovery records at T+1
  V: KDA_NOT_REACHED and KDA_PIPELINE_ERROR constants are exported from LOL module
  W: Authority invariants — LOL has broker_calls=0, no order creation
"""
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO))

from models.market_data import SectorFlow
from learning_system.learning_observation_ledger import (
    LearningObservationLedger,
    OBSERVED,
    DECISION_RECORDED,
    REJECTED,
    BLOCKED,
    OUTCOME_PENDING,
    OUTCOME_OBSERVED,
    KDA_NOT_REACHED,
    KDA_PIPELINE_ERROR,
    SHORTLISTED_NOT_EXECUTED,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_signal(symbol="AAPL", entry=100.0, stop=95.0, target=110.0,
                 direction="BUY", confidence=0.75, strategy_name="TestStrat",
                 regime="BULL", **kwargs):
    sig = SimpleNamespace(
        symbol=symbol,
        entry_price=entry,
        stop_loss=stop,
        target_price=target,
        direction=direction,
        confidence=confidence,
        strategy_name=strategy_name,
        regime=regime,
        risk_reward_ratio=kwargs.get("rr", 2.0),
        knowledge_selected=kwargs.get("knowledge_selected", False),
        knowledge_rank=kwargs.get("knowledge_rank", None),
        _obs_candidate_score=kwargs.get("_obs_candidate_score", confidence),
        _obs_regime=kwargs.get("_obs_regime", regime),
        expected_move_pct=kwargs.get("expected_move_pct", None),
    )
    return sig


def _make_lol(tmp_path: Path) -> LearningObservationLedger:
    """Create a fresh LOL instance in a temp directory."""
    lol_dir = tmp_path / "lol"
    lol_dir.mkdir(parents=True, exist_ok=True)
    return LearningObservationLedger(data_dir=lol_dir)


def _sector_flows_convert(sector_flows_value):
    """Reproduce the fixed conversion logic from master_orchestrator."""
    return {
        sf.sector_name: sf.flow_score
        for sf in (sector_flows_value or [])
        if hasattr(sf, "sector_name")
    }


# ════════════════════════════════════════════════════════════════════════════
# GROUP A–D — sector_flows fix
# ════════════════════════════════════════════════════════════════════════════

class TestSectorFlowsConversion:
    """Verify the root-cause fix: SectorFlow list → dict conversion."""

    def test_A_non_empty_list_converts_without_typeerror(self):
        """Non-empty List[SectorFlow] must not raise TypeError."""
        flows = [
            SectorFlow(sector_name="IT",     flow_score=0.85, rank=1, leaders=["INFY", "TCS"]),
            SectorFlow(sector_name="FMCG",   flow_score=0.42, rank=2, leaders=["HUL"]),
            SectorFlow(sector_name="METALS", flow_score=-0.3, rank=3, leaders=["TATASTEEL"]),
        ]
        result = _sector_flows_convert(flows)
        assert isinstance(result, dict), "Result must be a dict"
        assert result["IT"]     == 0.85
        assert result["FMCG"]   == 0.42
        assert result["METALS"] == pytest.approx(-0.3)
        assert len(result) == 3

    def test_B_empty_list_returns_empty_dict(self):
        """Empty sector_flows list must return empty dict."""
        result = _sector_flows_convert([])
        assert result == {}

    def test_C_none_returns_empty_dict(self):
        """None sector_flows must return empty dict (via `or []` guard)."""
        result = _sector_flows_convert(None)
        assert result == {}

    def test_D_object_without_sector_name_is_skipped(self):
        """Objects missing sector_name attribute are silently skipped."""
        bad_obj = SimpleNamespace(flow_score=0.5, rank=1)  # no sector_name
        good_obj = SectorFlow(sector_name="BANKING", flow_score=0.9, rank=1)
        result = _sector_flows_convert([bad_obj, good_obj])
        assert len(result) == 1
        assert "BANKING" in result

    def test_D2_old_dict_call_would_have_raised(self):
        """Confirm that dict(List[SectorFlow]) raises TypeError — validating the bug."""
        flows = [SectorFlow(sector_name="IT", flow_score=0.5, rank=1)]
        with pytest.raises(TypeError):
            dict(flows)  # this is what the original buggy code did


# ════════════════════════════════════════════════════════════════════════════
# GROUP E–H — KDA error vs insufficient evidence distinction
# ════════════════════════════════════════════════════════════════════════════

class TestKdaErrorDistinction:
    """Verify that pipeline errors are not silently mapped to insufficient evidence."""

    def test_E_pipeline_error_status_maps_to_kda_pipeline_error(self, tmp_path):
        """status=KNOWLEDGE_PIPELINE_ERROR → kda_decision=KDA_PIPELINE_ERROR."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("RELIANCE", entry=2800.0)

        lol.record_observations([sig], td)

        kda_results = {
            "RELIANCE": {
                "status":      "KNOWLEDGE_PIPELINE_ERROR",
                "kda_decision": None,
                "evidence_state": None,
            }
        }
        lol.update_decisions([sig], [sig], kda_results, td)

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "RELIANCE"), None)
        assert rec is not None
        assert rec["kda_decision"] == KDA_PIPELINE_ERROR, (
            f"Expected KDA_PIPELINE_ERROR, got {rec['kda_decision']!r}"
        )
        assert rec["kda_evidence_state"] == "PIPELINE_ERROR"

    def test_F_empty_kda_results_maps_to_kda_not_reached(self, tmp_path):
        """Empty kda_results dict (outer KDA crash) → kda_decision=KDA_NOT_REACHED."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("TCS", entry=3500.0)

        lol.record_observations([sig], td)
        lol.update_decisions([sig], [sig], {}, td)  # empty = KDA never ran

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "TCS"), None)
        assert rec is not None
        assert rec["kda_decision"] == KDA_NOT_REACHED, (
            f"Expected KDA_NOT_REACHED, got {rec['kda_decision']!r}"
        )
        assert rec["kda_evidence_state"] == "NOT_REACHED"

    def test_G_genuine_insufficient_evidence_preserved(self, tmp_path):
        """Genuine insufficient evidence → kda_decision=KNOWLEDGE_INSUFFICIENT_EVIDENCE (not error)."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("INFY", entry=1500.0)

        lol.record_observations([sig], td)
        kda_results = {
            "INFY": {
                "kda_decision":  "KNOWLEDGE_INSUFFICIENT_EVIDENCE",
                "evidence_state": "INSUFFICIENT_EVIDENCE",
            }
        }
        lol.update_decisions([sig], [sig], kda_results, td)

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "INFY"), None)
        assert rec is not None
        assert rec["kda_decision"] == "KNOWLEDGE_INSUFFICIENT_EVIDENCE"
        assert rec["kda_decision"] not in (KDA_NOT_REACHED, KDA_PIPELINE_ERROR)

    def test_H_genuine_kda_buy_passes_through(self, tmp_path):
        """KNOWLEDGE_BUY from KDA passes through without corruption."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("HDFCBANK", entry=1600.0)

        lol.record_observations([sig], td)
        kda_results = {
            "HDFCBANK": {
                "kda_decision":  "KNOWLEDGE_BUY",
                "evidence_state": "VALIDATED",
            }
        }
        lol.update_decisions([sig], [sig], kda_results, td)

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "HDFCBANK"), None)
        assert rec is not None
        assert rec["kda_decision"] == "KNOWLEDGE_BUY"
        assert rec["kda_evidence_state"] == "VALIDATED"


# ════════════════════════════════════════════════════════════════════════════
# GROUP I–N — CRE QTY_ZERO non-executed learning
# ════════════════════════════════════════════════════════════════════════════

class TestCREQtyZeroLearning:
    """Verify CRE-blocked signals are correctly recorded in the LOL."""

    def test_I_cre_blocking_records_blocked_state_and_block_reason(self, tmp_path):
        """update_cre_blocking writes a BLOCKED record with block_reason=CRE_QTY_ZERO."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("TATASTEEL", entry=150.0)

        # First record the observation (OBSERVED state)
        lol.record_observations([sig], td)
        # Then KDA/StrategyLab ran (update_decisions sets OUTCOME_PENDING)
        lol.update_decisions([sig], [sig], {}, td)
        # Then CRE blocks it
        count = lol.update_cre_blocking([sig], "CRE_QTY_ZERO", td)

        assert count == 1
        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "TATASTEEL"), None)
        assert rec is not None
        assert rec["lifecycle_state"] == BLOCKED
        assert rec["block_reason"] == "CRE_QTY_ZERO"

    def test_J_cre_block_sets_strategy_decision_pass(self, tmp_path):
        """CRE-blocked signals have strategy_decision='PASS' (strategy approved them)."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("WIPRO", entry=450.0)

        lol.record_observations([sig], td)
        lol.update_decisions([sig], [sig], {}, td)
        lol.update_cre_blocking([sig], "CRE_QTY_ZERO", td)

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "WIPRO"), None)
        assert rec is not None
        assert rec["strategy_decision"] == "PASS"

    def test_K_cre_block_preserves_existing_kda_decision(self, tmp_path):
        """CRE block preserves a kda_decision already set by update_decisions."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("ICICIBANK", entry=900.0)

        lol.record_observations([sig], td)
        kda_results = {
            "ICICIBANK": {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
        }
        lol.update_decisions([sig], [sig], kda_results, td)
        lol.update_cre_blocking([sig], "CRE_QTY_ZERO", td)

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "ICICIBANK"), None)
        assert rec is not None
        assert rec["lifecycle_state"] == BLOCKED
        assert rec["kda_decision"] == "KNOWLEDGE_BUY", (
            "KDA decision must be preserved when CRE blocks"
        )

    def test_L_cre_block_fills_kda_not_reached_when_missing(self, tmp_path):
        """CRE block fills kda_decision=KDA_NOT_REACHED when KDA never ran."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("BAJFINANCE", entry=7000.0)

        # Only observation recorded, no decisions update (KDA never ran)
        lol.record_observations([sig], td)
        lol.update_cre_blocking([sig], "CRE_QTY_ZERO", td)

        records = lol.load_day(td)
        rec = next((r for r in records if r.get("symbol") == "BAJFINANCE"), None)
        assert rec is not None
        assert rec["lifecycle_state"] == BLOCKED
        assert rec["kda_decision"] == KDA_NOT_REACHED

    def test_M_cre_blocking_unknown_obs_id_returns_zero(self, tmp_path):
        """update_cre_blocking on an unrecorded signal returns 0 without crash."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("UNKNOWN_CORP", entry=999.0)

        # Never record observation first — obs_id won't be in _pending
        count = lol.update_cre_blocking([sig], "CRE_QTY_ZERO", td)
        assert count == 0

    def test_N_cre_blocking_multiple_signals_all_recorded(self, tmp_path):
        """All signals in a batch get BLOCKED + block_reason recorded."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        signals = [
            _make_signal("SBIN",      entry=600.0),
            _make_signal("AXISBANK",  entry=1100.0),
            _make_signal("KOTAKBANK", entry=1800.0),
        ]

        lol.record_observations(signals, td)
        lol.update_decisions(signals, signals, {}, td)
        count = lol.update_cre_blocking(signals, "CRE_QTY_ZERO", td)

        assert count == 3
        records = {r["symbol"]: r for r in lol.load_day(td)}
        for sym in ("SBIN", "AXISBANK", "KOTAKBANK"):
            assert records[sym]["lifecycle_state"] == BLOCKED
            assert records[sym]["block_reason"] == "CRE_QTY_ZERO"


# ════════════════════════════════════════════════════════════════════════════
# GROUP O–S — Recovery script: lifecycle_state and honest decision fields
# ════════════════════════════════════════════════════════════════════════════

class TestRecoveryScript:
    """Verify recover_mop_rc001_to_lol.py produces correctly-structured LOL records."""

    def _run_recovery(self, tmp_path: Path, mop_rows: list, trading_date: str) -> dict:
        """Inject a fake MOP_RC001 file and run the recovery function."""
        mop_dir = tmp_path / "data" / "mop_rc001"
        lol_dir = tmp_path / "data" / "lol"
        mop_dir.mkdir(parents=True, exist_ok=True)
        lol_dir.mkdir(parents=True, exist_ok=True)

        mop_file = mop_dir / f"MOP_RC001_{trading_date}.json"
        with open(mop_file, "w") as f:
            for row in mop_rows:
                f.write(json.dumps(row) + "\n")

        # Patch the directory constants in the recovery module
        import scripts.recover_mop_rc001_to_lol as rc_mod
        orig_mop = rc_mod._MOP_DIR
        orig_lol = rc_mod._LOL_DIR
        try:
            rc_mod._MOP_DIR = mop_dir
            rc_mod._LOL_DIR = lol_dir
            return rc_mod.recover(trading_date)
        finally:
            rc_mod._MOP_DIR = orig_mop
            rc_mod._LOL_DIR = orig_lol

    def _load_lol_records(self, tmp_path: Path, trading_date: str) -> list:
        lol_file = tmp_path / "data" / "lol" / f"LOL_{trading_date}.jsonl"
        if not lol_file.exists():
            return []
        records = {}
        for line in lol_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            oid = rec.get("observation_id")
            if oid:
                records[oid] = rec
        return list(records.values())

    def test_O_recovery_lifecycle_state_is_outcome_pending(self, tmp_path):
        """Recovered records must have lifecycle_state='OUTCOME_PENDING' for outcome fill."""
        td = "2026-08-25"
        mop_rows = [{"symbol": "RELIANCE", "direction": "BUY",
                     "entry_price": 2800.0, "stop_loss": 2750.0,
                     "target_price": 2900.0, "confidence": 0.72}]
        result = self._run_recovery(tmp_path, mop_rows, td)
        assert result["status"] == "SUCCESS"
        records = self._load_lol_records(tmp_path, td)
        assert len(records) == 1
        assert records[0]["lifecycle_state"] == "OUTCOME_PENDING", (
            f"Expected OUTCOME_PENDING, got {records[0]['lifecycle_state']!r}"
        )

    def test_P_recovery_kda_decision_is_not_reached(self, tmp_path):
        """Recovered records have kda_decision=KDA_NOT_REACHED (pipeline never ran)."""
        td = "2026-08-25"
        mop_rows = [{"symbol": "TCS", "direction": "BUY",
                     "entry_price": 3500.0, "stop_loss": 3400.0,
                     "target_price": 3600.0, "confidence": 0.65}]
        self._run_recovery(tmp_path, mop_rows, td)
        records = self._load_lol_records(tmp_path, td)
        assert records[0]["kda_decision"] == KDA_NOT_REACHED

    def test_Q_recovery_strategy_decision_is_not_reached(self, tmp_path):
        """Recovered records have strategy_decision='NOT_REACHED'."""
        td = "2026-08-25"
        mop_rows = [{"symbol": "INFY", "direction": "BUY",
                     "entry_price": 1500.0, "stop_loss": 1450.0,
                     "target_price": 1560.0, "confidence": 0.68}]
        self._run_recovery(tmp_path, mop_rows, td)
        records = self._load_lol_records(tmp_path, td)
        assert records[0]["strategy_decision"] == "NOT_REACHED"

    def test_R_recovery_is_idempotent(self, tmp_path):
        """Running recovery twice writes no additional records for the same obs_ids."""
        td = "2026-08-25"
        mop_rows = [
            {"symbol": "WIPRO", "direction": "BUY", "entry_price": 450.0,
             "stop_loss": 430.0, "target_price": 480.0, "confidence": 0.6},
            {"symbol": "HCLTECH", "direction": "BUY", "entry_price": 1200.0,
             "stop_loss": 1150.0, "target_price": 1270.0, "confidence": 0.7},
        ]
        result1 = self._run_recovery(tmp_path, mop_rows, td)
        result2 = self._run_recovery(tmp_path, mop_rows, td)

        assert result1["recovered"] == 2
        assert result2["recovered"] == 0, "Second run must skip all duplicates"
        assert result2["skipped"] == 2

    def test_S_recovery_no_lookahead_true(self, tmp_path):
        """Recovered records must have no_lookahead=True."""
        td = "2026-08-25"
        mop_rows = [{"symbol": "BAJFINANCE", "direction": "BUY",
                     "entry_price": 7000.0, "stop_loss": 6800.0,
                     "target_price": 7300.0, "confidence": 0.71}]
        self._run_recovery(tmp_path, mop_rows, td)
        records = self._load_lol_records(tmp_path, td)
        assert records[0]["no_lookahead"] is True


# ════════════════════════════════════════════════════════════════════════════
# GROUP T–U — fill_pending_outcomes anti-lookahead and eligibility
# ════════════════════════════════════════════════════════════════════════════

class TestFillPendingOutcomes:
    """Verify outcome fill eligibility and anti-lookahead rules."""

    def test_T_fill_skips_today_records_anti_lookahead(self, tmp_path):
        """Records with trading_date=today are skipped (T+1 is tomorrow)."""
        lol = _make_lol(tmp_path)
        td  = date.today().isoformat()
        sig = _make_signal("SBIN", entry=600.0)

        lol.record_observations([sig], td)
        lol.update_decisions([sig], [sig], {}, td)

        result = lol.fill_pending_outcomes(lookback_days=1)
        # Today's records must be skipped (T+1 hasn't happened yet)
        assert result.get("skipped_pending", 0) >= 1, (
            "Today's records must be in skipped_pending"
        )
        assert result.get("processed", 0) == 0, (
            "No outcomes should be filled for today's records"
        )

    def test_U_fill_processes_yesterday_outcome_pending_records(self, tmp_path):
        """OUTCOME_PENDING records from yesterday are processed if bars available."""
        lol = _make_lol(tmp_path)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        sig = _make_signal("AXISBANK", entry=1100.0, stop=1060.0, target=1160.0)

        lol.record_observations([sig], yesterday)
        lol.update_decisions([sig], [sig], {}, yesterday)

        # Provide fake bars for T+1 onwards
        def _fake_fetcher(symbol, decision_date, horizon):
            return [{"date": (date.fromisoformat(decision_date) + timedelta(days=i)).isoformat(),
                     "open": 1110.0, "high": 1120.0, "low": 1100.0, "close": 1115.0}
                    for i in range(1, horizon + 1)]

        result = lol.fill_pending_outcomes(lookback_days=2, _ohlcv_fetcher=_fake_fetcher)
        assert result.get("processed", 0) == 1, (
            f"Expected 1 processed, got {result}"
        )

        records = lol.load_day(yesterday)
        rec = next((r for r in records if r.get("symbol") == "AXISBANK"), None)
        assert rec is not None
        assert rec["lifecycle_state"] == OUTCOME_OBSERVED


# ════════════════════════════════════════════════════════════════════════════
# GROUP V–W — constants export and authority invariants
# ════════════════════════════════════════════════════════════════════════════

class TestConstantsAndAuthority:
    """Verify constants and authority invariants."""

    def test_V_kda_error_constants_exported_from_lol_module(self):
        """KDA_NOT_REACHED and KDA_PIPELINE_ERROR are importable from LOL module."""
        from learning_system.learning_observation_ledger import (
            KDA_NOT_REACHED as kda_nr,
            KDA_PIPELINE_ERROR as kda_pe,
        )
        assert kda_nr == "KDA_NOT_REACHED"
        assert kda_pe == "KDA_PIPELINE_ERROR"
        # They must differ from the legitimate evidence insufficiency constant
        assert kda_nr != "KNOWLEDGE_INSUFFICIENT_EVIDENCE"
        assert kda_pe != "KNOWLEDGE_INSUFFICIENT_EVIDENCE"

    def test_W_lol_has_no_broker_calls(self, tmp_path):
        """LOL module must make zero broker calls — no orders, no broker auth."""
        import learning_system.learning_observation_ledger as lol_mod
        source = Path(lol_mod.__file__).read_text(encoding="utf-8")
        forbidden = [
            "DhanBroker",
            "ZerodhaBroker",
            "place_order",
            "execution_authority",
            "broker_calls",
        ]
        for term in forbidden:
            if term in ("execution_authority", "broker_calls"):
                # These should only appear in comments/docstring (as "= False" / "= 0")
                # not as live code that sets them to True/non-zero
                assert "execution_authority = True" not in source, (
                    f"LOL must not set execution_authority=True"
                )
                assert "broker_calls = 1" not in source
            else:
                assert term not in source, (
                    f"LOL module must not reference {term!r}"
                )


# ════════════════════════════════════════════════════════════════════════════
# GROUP — Sector flows wire-up in orchestrator source
# ════════════════════════════════════════════════════════════════════════════

class TestOrchestratorSectorFlowsFix:
    """Verify the fix is present in the orchestrator source."""

    def test_orchestrator_no_longer_has_dict_sector_flows_pattern(self):
        """The buggy dict(getattr(snapshot, 'sector_flows'...)) pattern must not exist."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        source = orches.read_text(encoding="utf-8")
        assert 'dict(getattr(snapshot, "sector_flows"' not in source, (
            "Buggy dict() conversion of sector_flows must be removed"
        )

    def test_orchestrator_has_comprehension_sector_flows(self):
        """The fixed comprehension pattern must be present."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        source = orches.read_text(encoding="utf-8")
        assert "sf.sector_name: sf.flow_score" in source, (
            "Fixed sector_flows comprehension must be in orchestrator"
        )

    def test_orchestrator_has_cre_blocking_lol_call(self):
        """Orchestrator must call update_cre_blocking after CRE step."""
        orches = _REPO / "orchestrator" / "master_orchestrator.py"
        source = orches.read_text(encoding="utf-8")
        assert "update_cre_blocking" in source, (
            "Orchestrator must call LOL.update_cre_blocking for CRE-blocked signals"
        )
        assert "CRE_QTY_ZERO" in source


# ════════════════════════════════════════════════════════════════════════════
# Pytest runner
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

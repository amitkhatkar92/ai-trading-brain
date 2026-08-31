"""
tests/test_dta_028a_path_outcomes.py
======================================
DTA-KNOWLEDGE-FIX-028A regression tests

Covers the four defects identified by DTA-KNOWLEDGE-ARCH-INVESTIGATION-028:

  Fix C  — REJECTED/BLOCKED path classification uses first_event
  Fix D  — MFE/MAE bounded at first terminal event (path-bounded)
  Fix E  — Gap-down / gap-up stop/target detection (lo<=stop, hi>=target)
  Fix F  — LOL evidence bridge ge1/ge2/ge3 derived from path outcome, not t5_ret

T001  rejected BUY, stop first, later recovery → REJECTED_CORRECT
T002  rejected BUY, target first → REJECTED_INCORRECT
T003  rejected BUY, no terminal event → existing directional behaviour preserved
T004  MFE stops after STOP_HIT (post-stop recovery does NOT inflate MFE)
T005  MAE stops after TARGET_HIT (post-target drop does NOT worsen MAE)
T006  gap-down completely through stop → STOP_HIT detected
T007  gap-up completely above target → TARGET_HIT detected
T008  same-bar target AND stop → OUTCOME_AMBIGUOUS
T009  bridge: STOP_HIT + positive t5_ret → ge2/ge3=False (no contradictory evidence)
T010  bridge: directional t5_ret preserved even when STOP_HIT
T011  executed STOP_FIRST (STOP_EXIT) unchanged
T012  executed TARGET_FIRST (TARGET_EXIT) unchanged
T013  no-lookahead flag preserved on OUTCOME_UPDATE records
T014  frozen entry/SL/target: outcome references reference_entry, not a future price
T015  actual P&L null for non-executed KLP observations
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers shared across tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_bars(specs: List[Dict[str, float]], base_date: Optional[str] = None) -> List[Dict]:
    """
    Build a list of OHLCV bar dicts from compact specs.
    spec keys: high, low, close (open defaults to prev close or 100).
    Dates are consecutive calendar days starting from base_date or 5 days ago.
    """
    if base_date is None:
        start = date.today() - timedelta(days=len(specs) + 1)
    else:
        start = date.fromisoformat(base_date)
    bars = []
    for i, s in enumerate(specs):
        d = start + timedelta(days=i)
        bars.append({
            "date":   str(d),
            "open":   s.get("open", s.get("close", 100.0)),
            "high":   float(s["high"]),
            "low":    float(s["low"]),
            "close":  float(s["close"]),
            "volume": 1_000_000.0,
        })
    return bars


def _lol_rec(
    obs_id:           str  = "obs-028a-001",
    symbol:           str  = "SUNPHARMA",
    direction:        str  = "BUY",
    trading_date:     str  = "2026-08-01",
    lifecycle_state:  str  = "REJECTED",
    outcome_class:    str  = "REJECTED_INCORRECT",
    actual_return:    Optional[float] = 4.0,
    outcome_first_event: str = "",
    stop_hit:         bool = False,
    target_hit:       bool = False,
    decision_at:      str  = "2026-08-01T09:30:00+00:00",
    outcome_at:       str  = "2026-08-06T15:30:00+00:00",
    t1:               Optional[float] = None,
    t5:               Optional[float] = None,
    no_lookahead:     bool = True,
) -> Dict[str, Any]:
    _t5 = t5 if t5 is not None else actual_return
    return {
        "observation_id":      obs_id,
        "symbol":              symbol,
        "direction":           direction,
        "trading_date":        trading_date,
        "lifecycle_state":     lifecycle_state,
        "outcome_class":       outcome_class,
        "actual_return_pct":   actual_return,
        "t1_ret_pct":          t1,
        "t3_ret_pct":          round(_t5 * 0.7, 4) if _t5 is not None else None,
        "t5_ret_pct":          _t5,
        "mfe_pct":             abs(actual_return) + 0.5 if actual_return else None,
        "mae_pct":             0.8,
        "target_hit":          target_hit,
        "stop_hit":            stop_hit,
        "outcome_first_event": outcome_first_event,
        "decision_at":         decision_at,
        "outcome_at":          outcome_at,
        "kda_decision":        "KNOWLEDGE_WAIT",
        "kda_evidence_state":  "INSUFFICIENT",
        "strategy_decision":   "REJECT",
        "authorization_source": "NONE",
        "knowledge_provenance": {"regime": "RANGE"},
        "no_lookahead":        no_lookahead,
        "entry_price":         100.0,
        "stop_loss":           95.0,
        "target_price":        108.0,
        "opportunity_id":      "opp-028a",
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
    out = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    lol_dir = tmp_path / "lol"
    lol_dir.mkdir()
    ledger  = tmp_path / "knowledge_evidence_ledger.jsonl"
    state   = tmp_path / "ksl" / "lol_bridge_state.json"
    return lol_dir, ledger, state


# ─────────────────────────────────────────────────────────────────────────────
# Fix C — T001-T003: rejected classification uses first_event
# ─────────────────────────────────────────────────────────────────────────────

class TestFixC_RejectedClassification:

    def test_T001_stop_first_recovery_rejected_correct(self):
        """T001: BUY rejected, stop hit first, stock later recovers (+4% EOD).
        Fix C: must be REJECTED_CORRECT not REJECTED_INCORRECT."""
        from learning_system.learning_observation_ledger import _classify_outcome, REJECTED

        result = _classify_outcome(
            target_hit=False,
            stop_hit=True,
            t5_ret=4.0,        # positive — stock eventually recovered
            first_event="STOP_HIT",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
            is_buy=True,
        )
        assert result == "REJECTED_CORRECT", (
            f"Stop-first-then-recovery must be REJECTED_CORRECT, got {result!r}"
        )

    def test_T002_target_first_rejected_incorrect(self):
        """T002: BUY rejected, target hit first → REJECTED_INCORRECT."""
        from learning_system.learning_observation_ledger import _classify_outcome, REJECTED

        result = _classify_outcome(
            target_hit=True,
            stop_hit=False,
            t5_ret=8.0,
            first_event="TARGET_HIT",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
            is_buy=True,
        )
        assert result == "REJECTED_INCORRECT", (
            f"Target-first rejection must be REJECTED_INCORRECT, got {result!r}"
        )

    def test_T003_no_event_directional_logic_preserved(self):
        """T003: No terminal event — existing directional fallback still applies."""
        from learning_system.learning_observation_ledger import _classify_outcome, REJECTED

        # Significant positive directional move with no terminal event
        result = _classify_outcome(
            target_hit=False,
            stop_hit=False,
            t5_ret=3.0,
            first_event="OUTCOME_EXPIRED",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
            is_buy=True,
        )
        assert result == "REJECTED_INCORRECT", (
            f"Positive t5_ret + no terminal event should be REJECTED_INCORRECT, got {result!r}"
        )

        # Significant adverse move
        result_neg = _classify_outcome(
            target_hit=False,
            stop_hit=False,
            t5_ret=-2.0,
            first_event="OUTCOME_EXPIRED",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
            is_buy=True,
        )
        assert result_neg == "REJECTED_CORRECT", (
            f"Negative t5_ret + no event should be REJECTED_CORRECT, got {result_neg!r}"
        )

    def test_T001b_blocked_stop_first_correct(self):
        """T001-BLOCKED: Same scenario but BLOCKED state → BLOCKED_CORRECT."""
        from learning_system.learning_observation_ledger import _classify_outcome, BLOCKED

        result = _classify_outcome(
            target_hit=False,
            stop_hit=True,
            t5_ret=4.0,
            first_event="STOP_HIT",
            decision_state=BLOCKED,
            kda_decision="KNOWLEDGE_HOLD",
            strategy_decision="PASS",
            authorization_source="NONE",
            is_buy=True,
        )
        assert result == "BLOCKED_CORRECT", (
            f"Stop-first blocked signal must be BLOCKED_CORRECT, got {result!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fix D — T004-T005: MFE/MAE bounded at first event
# ─────────────────────────────────────────────────────────────────────────────

class TestFixD_BoundedMFEMAE:

    def test_T004_mfe_stops_after_stop_hit(self):
        """T004: Post-stop recovery must NOT inflate MFE.
        BUY@100, SL=95, Target=108.
        Day1: low=94 (stop hit), high=100.5
        Day3: high=109 (above target, but after stop)
        Path MFE should reflect only up to stop bar (~+0.5%), not post-stop +9%."""
        from opportunity_engine.klp_outcome_engine import compute_outcome_from_bars, STOP_HIT

        # Day1: stop hit (low=94 < SL=95)
        # Day2: recovery begins
        # Day3: above target
        start = date.today() - timedelta(days=6)
        bars = [
            {"date": str(start),                   "high": 100.5, "low": 94.0,  "close": 97.0,  "open": 100.0},
            {"date": str(start + timedelta(days=1)), "high": 102.0, "low": 97.0,  "close": 101.0, "open": 97.0},
            {"date": str(start + timedelta(days=2)), "high": 109.0, "low": 101.0, "close": 104.0, "open": 101.0},
            {"date": str(start + timedelta(days=3)), "high": 105.0, "low": 102.0, "close": 104.0, "open": 104.0},
            {"date": str(start + timedelta(days=4)), "high": 105.0, "low": 103.0, "close": 104.0, "open": 104.0},
        ]
        out = compute_outcome_from_bars(
            entry=100.0, target=108.0, stop=95.0, direction="BUY", bars=bars
        )
        assert out["first_event"] == STOP_HIT, f"Expected STOP_HIT, got {out['first_event']}"
        assert out["first_event_day"] == str(start), "Stop hit on Day1"
        # MFE must only include Day1 data (high=100.5 → +0.5%)
        assert out["mfe_pct"] is not None
        assert out["mfe_pct"] <= 1.0, (
            f"Path MFE should be ≤1% (only Day1 high=100.5), got {out['mfe_pct']}"
        )
        # t5_ret should still reflect directional EOD return
        assert out["t5_ret_pct"] is not None
        assert out["t5_ret_pct"] > 3.0, "Directional t5_ret should reflect +4% EOD close"

    def test_T005_mae_stops_after_target_hit(self):
        """T005: Post-target adverse movement must NOT worsen MAE.
        BUY@100, SL=90, Target=108.
        Day1: high=109 (target hit), low=99
        Day2: drops hard, low=88 (below SL, but after target)
        Path MAE should reflect only up to target bar (~-1%), not post-target -12%."""
        from opportunity_engine.klp_outcome_engine import compute_outcome_from_bars, TARGET_HIT

        start = date.today() - timedelta(days=7)
        bars = [
            {"date": str(start),                   "high": 109.0, "low": 99.0, "close": 106.0, "open": 100.0},
            {"date": str(start + timedelta(days=1)), "high": 103.0, "low": 88.0, "close": 90.0,  "open": 106.0},
            {"date": str(start + timedelta(days=2)), "high": 92.0,  "low": 87.0, "close": 89.0,  "open": 90.0},
            {"date": str(start + timedelta(days=3)), "high": 91.0,  "low": 86.0, "close": 88.0,  "open": 89.0},
            {"date": str(start + timedelta(days=4)), "high": 90.0,  "low": 85.0, "close": 87.0,  "open": 88.0},
        ]
        out = compute_outcome_from_bars(
            entry=100.0, target=108.0, stop=90.0, direction="BUY", bars=bars
        )
        assert out["first_event"] == TARGET_HIT, f"Expected TARGET_HIT, got {out['first_event']}"
        assert out["first_event_day"] == str(start), "Target hit on Day1"
        # MAE must only include Day1 data (low=99 → -1%)
        assert out["mae_pct"] is not None
        assert out["mae_pct"] >= -2.0, (
            f"Path MAE should be ≥-2% (only Day1 low=99), got {out['mae_pct']}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fix E — T006-T008: gap-down/gap-up detection
# ─────────────────────────────────────────────────────────────────────────────

class TestFixE_GapDetection:

    def _single_bar(self, high: float, low: float, close: float) -> List[Dict]:
        d = str(date.today() - timedelta(days=2))
        bars = []
        for i in range(5):
            day = str(date.today() - timedelta(days=6 - i))
            bars.append({"date": day, "high": high if i == 0 else 101.0,
                         "low": low if i == 0 else 99.0,
                         "close": close if i == 0 else 100.0, "open": 100.0})
        return bars

    def test_T006_gap_down_completely_through_stop(self):
        """T006: Entire bar is BELOW stop level (high < stop) → stop must still be detected.
        BUY@100, SL=95. Bar: high=93, low=91 — entire bar below stop."""
        from opportunity_engine.klp_outcome_engine import compute_outcome_from_bars, STOP_HIT

        bars = self._single_bar(high=93.0, low=91.0, close=92.0)
        out = compute_outcome_from_bars(
            entry=100.0, target=115.0, stop=95.0, direction="BUY", bars=bars
        )
        assert out["stop_hit"] is True, "Gap-down through stop must set stop_hit=True"
        assert out["first_event"] == STOP_HIT, f"Expected STOP_HIT, got {out['first_event']}"

    def test_T006_lol_gap_down_stop(self):
        """T006-LOL: LOL _compute_outcome must also detect gap-down through stop."""
        from learning_system.learning_observation_ledger import _compute_outcome, REJECTED

        bars = self._single_bar(high=93.0, low=91.0, close=92.0)
        result = _compute_outcome(
            bars=bars,
            entry=100.0,
            stop=95.0,
            target=115.0,
            direction="BUY",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
        )
        assert result["stop_hit"] is True, "LOL gap-down must set stop_hit=True"
        assert result["outcome_first_event"] == "STOP_HIT"

    def test_T007_gap_up_completely_above_target(self):
        """T007: Entire bar is ABOVE target (low > target) → target must be detected.
        BUY@100, Target=108. Bar: low=109, high=115 — entire bar above target."""
        from opportunity_engine.klp_outcome_engine import compute_outcome_from_bars, TARGET_HIT

        bars = self._single_bar(high=115.0, low=109.0, close=111.0)
        out = compute_outcome_from_bars(
            entry=100.0, target=108.0, stop=90.0, direction="BUY", bars=bars
        )
        assert out["target_hit"] is True, "Gap-up through target must set target_hit=True"
        assert out["first_event"] == TARGET_HIT, f"Expected TARGET_HIT, got {out['first_event']}"

    def test_T007_lol_gap_up_target(self):
        """T007-LOL: LOL must detect gap-up through target."""
        from learning_system.learning_observation_ledger import _compute_outcome, REJECTED

        bars = self._single_bar(high=115.0, low=109.0, close=111.0)
        result = _compute_outcome(
            bars=bars,
            entry=100.0,
            stop=90.0,
            target=108.0,
            direction="BUY",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
        )
        assert result["target_hit"] is True, "LOL gap-up must set target_hit=True"
        assert result["outcome_first_event"] == "TARGET_HIT"

    def test_T008_same_bar_ambiguous(self):
        """T008: Same bar hits both stop AND target → OUTCOME_AMBIGUOUS."""
        from opportunity_engine.klp_outcome_engine import compute_outcome_from_bars, OUTCOME_AMBIGUOUS

        bars = self._single_bar(high=115.0, low=91.0, close=100.0)
        out = compute_outcome_from_bars(
            entry=100.0, target=108.0, stop=95.0, direction="BUY", bars=bars
        )
        assert out["first_event"] == OUTCOME_AMBIGUOUS, (
            f"Same-bar stop+target must be OUTCOME_AMBIGUOUS, got {out['first_event']}"
        )
        assert out["target_hit"] is True
        assert out["stop_hit"]   is True

    def test_T008_lol_same_bar_ambiguous(self):
        """T008-LOL: LOL must also produce OUTCOME_AMBIGUOUS for same-bar hit."""
        from learning_system.learning_observation_ledger import _compute_outcome, REJECTED

        bars = self._single_bar(high=115.0, low=91.0, close=100.0)
        result = _compute_outcome(
            bars=bars,
            entry=100.0,
            stop=95.0,
            target=108.0,
            direction="BUY",
            decision_state=REJECTED,
            kda_decision="KNOWLEDGE_WAIT",
            strategy_decision="REJECT",
            authorization_source="NONE",
        )
        assert result["outcome_first_event"] == "OUTCOME_AMBIGUOUS"
        assert result["stop_hit"]   is True
        assert result["target_hit"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Fix F — T009-T010: evidence bridge ge1/ge2/ge3 from path outcome
# ─────────────────────────────────────────────────────────────────────────────

class TestFixF_EvidenceBridgeGe:

    def test_T009_stop_hit_plus_positive_t5_no_ge_credit(self, tmp_dirs):
        """T009: STOP_HIT + positive t5_ret → ge1/ge2/ge3 = False (no trade-success credit).
        This is the core scenario: BUY prediction stopped out but stock later recovers."""
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _lol_rec(
            outcome_class="REJECTED_CORRECT",     # Fix C correctly classifies this
            actual_return=4.0,                    # positive directional recovery
            outcome_first_event="STOP_HIT",       # but stop was hit first
            stop_hit=True,
            target_hit=False,
            lifecycle_state="OUTCOME_OBSERVED",
        )
        _write_lol_file(lol_dir, "2026-08-01", [rec])
        result = ingest_lol_outcomes(
            dates=["2026-08-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        assert result["new_records"] == 1
        records = _read_ledger(ledger)
        ev = records[0]
        assert ev["ge1"] is False, f"STOP_HIT must not produce ge1=True, got {ev['ge1']}"
        assert ev["ge2"] is False, f"STOP_HIT must not produce ge2=True, got {ev['ge2']}"
        assert ev["ge3"] is False, f"STOP_HIT must not produce ge3=True, got {ev['ge3']}"

    def test_T010_directional_return_preserved_in_record(self, tmp_dirs):
        """T010: t5_ret and actual_return_pct are preserved in the evidence record
        even when ge is suppressed due to STOP_HIT."""
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _lol_rec(
            outcome_class="REJECTED_CORRECT",
            actual_return=4.0,
            t5=4.0,
            outcome_first_event="STOP_HIT",
            stop_hit=True,
            lifecycle_state="OUTCOME_OBSERVED",
        )
        _write_lol_file(lol_dir, "2026-08-01", [rec])
        ingest_lol_outcomes(
            dates=["2026-08-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        records = _read_ledger(ledger)
        ev = records[0]
        # Directional return must be preserved — not removed
        assert ev["t5_ret_pct"] == 4.0, "t5_ret_pct must be preserved in evidence record"
        # ge suppressed
        assert ev["ge2"] is False

    def test_T010b_target_hit_ge_positive(self, tmp_dirs):
        """T010b: TARGET_HIT with positive return → ge reflects directional return normally."""
        lol_dir, ledger, state = tmp_dirs
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes

        rec = _lol_rec(
            outcome_class="REJECTED_INCORRECT",
            actual_return=8.0,
            t5=8.0,
            outcome_first_event="TARGET_HIT",
            target_hit=True,
            stop_hit=False,
            lifecycle_state="OUTCOME_OBSERVED",
        )
        _write_lol_file(lol_dir, "2026-08-01", [rec])
        ingest_lol_outcomes(
            dates=["2026-08-01"],
            lol_data_dir=lol_dir,
            knowledge_ledger=ledger,
            state_path=state,
        )
        records = _read_ledger(ledger)
        ev = records[0]
        assert ev["ge2"] is True, f"TARGET_HIT + t5=8% should give ge2=True, got {ev['ge2']}"
        assert ev["ge3"] is True, f"TARGET_HIT + t5=8% should give ge3=True, got {ev['ge3']}"


# ─────────────────────────────────────────────────────────────────────────────
# T011-T012: Executed trade behaviour unchanged
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutedTradeUnchanged:

    def test_T011_executed_stop_first_unchanged(self):
        """T011: EXECUTED + first_event=STOP_HIT → STOP_EXIT (unchanged)."""
        from learning_system.learning_observation_ledger import (
            _classify_outcome, EXECUTED, STOP_EXIT,
        )
        result = _classify_outcome(
            target_hit=False,
            stop_hit=True,
            t5_ret=-2.5,
            first_event="STOP_HIT",
            decision_state=EXECUTED,
            kda_decision="KNOWLEDGE_BUY",
            strategy_decision="PASS",
            authorization_source="STRATEGY_LAB",
            is_buy=True,
        )
        assert result == STOP_EXIT, f"Executed stop must be STOP_EXIT, got {result!r}"

    def test_T012_executed_target_first_unchanged(self):
        """T012: EXECUTED + first_event=TARGET_HIT → TARGET_EXIT (unchanged)."""
        from learning_system.learning_observation_ledger import (
            _classify_outcome, EXECUTED, TARGET_EXIT,
        )
        result = _classify_outcome(
            target_hit=True,
            stop_hit=False,
            t5_ret=8.0,
            first_event="TARGET_HIT",
            decision_state=EXECUTED,
            kda_decision="KNOWLEDGE_BUY",
            strategy_decision="PASS",
            authorization_source="STRATEGY_LAB",
            is_buy=True,
        )
        assert result == TARGET_EXIT, f"Executed target must be TARGET_EXIT, got {result!r}"


# ─────────────────────────────────────────────────────────────────────────────
# T013-T015: Look-ahead, frozen entry, null P&L for non-executed
# ─────────────────────────────────────────────────────────────────────────────

class TestLookAheadAndIntegrity:

    def test_T013_no_lookahead_flag_preserved_on_outcome_update(self, tmp_path: Path):
        """T013: KLPOutcomeEngine OUTCOME_UPDATE records carry no_lookahead=True."""
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine

        date_str = str(date.today() - timedelta(days=3))
        obs = {
            "obs_id":              f"TATASTEEL_{date_str}_500.00_klp",
            "event_type":          "KNOWLEDGE_OBSERVATION",
            "trading_date":        date_str,
            "symbol":              "TATASTEEL",
            "direction":           "BUY",
            "reference_entry":     500.0,
            "knowledge_target":    525.0,
            "knowledge_stop_loss": 488.0,
            "knowledge_RR":        2.1,
            "no_lookahead":        True,
        }
        klp_path = tmp_path / f"KLP_{date_str}.jsonl"
        with klp_path.open("w") as f:
            f.write(json.dumps(obs) + "\n")

        start = date.today() - timedelta(days=4)
        bars = [
            {"date": str(start + timedelta(days=i)), "open": 502.0,
             "high": 503.0, "low": 499.0, "close": 502.0}
            for i in range(5)
        ]
        engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=lambda s, d: bars)
        engine.fill_pending_outcomes(dates=[date_str])

        records = [json.loads(l) for l in klp_path.read_text().splitlines() if l.strip()]
        updates = [r for r in records if r.get("event_type") == "OUTCOME_UPDATE"]
        assert updates, "Expected at least one OUTCOME_UPDATE"
        assert all(r.get("no_lookahead") is True for r in updates), (
            "All OUTCOME_UPDATE records must have no_lookahead=True"
        )

    def test_T014_entry_frozen_from_observation(self, tmp_path: Path):
        """T014: Outcome engine uses reference_entry from the observation record,
        not any future price, and passes it through unchanged to OUTCOME_UPDATE."""
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine

        date_str = str(date.today() - timedelta(days=3))
        frozen_entry = 500.0
        obs = {
            "obs_id":              "FROZEN_ENTRY_TEST",
            "event_type":          "KNOWLEDGE_OBSERVATION",
            "trading_date":        date_str,
            "symbol":              "INFY",
            "direction":           "BUY",
            "reference_entry":     frozen_entry,
            "knowledge_target":    530.0,
            "knowledge_stop_loss": 485.0,
            "no_lookahead":        True,
        }
        klp_path = tmp_path / f"KLP_{date_str}.jsonl"
        with klp_path.open("w") as f:
            f.write(json.dumps(obs) + "\n")

        start = date.today() - timedelta(days=4)
        bars = [
            {"date": str(start + timedelta(days=i)), "open": 510.0,
             "high": 520.0, "low": 508.0, "close": 512.0}
            for i in range(5)
        ]
        engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=lambda s, d: bars)
        engine.fill_pending_outcomes(dates=[date_str])

        records = [json.loads(l) for l in klp_path.read_text().splitlines() if l.strip()]
        updates = [r for r in records if r.get("event_type") == "OUTCOME_UPDATE"]
        assert updates, "Expected OUTCOME_UPDATE"
        assert updates[0].get("reference_entry") == frozen_entry, (
            f"OUTCOME_UPDATE must carry frozen reference_entry={frozen_entry}"
        )

    def test_T015_actual_pnl_null_for_non_executed_klp(self, tmp_path: Path):
        """T015: KNOWLEDGE_OBSERVATION records must have actual_return_pct=None.
        For non-executed observations, no P&L should be fabricated."""
        from opportunity_engine.klp_evaluator import KLPEvaluator
        from unittest.mock import MagicMock

        ev  = KLPEvaluator(data_dir=tmp_path)
        sig = MagicMock()
        sig.symbol               = "WIPRO"
        sig.direction            = MagicMock(value="BUY")
        sig.entry_price          = 300.0
        sig.stop_loss            = 288.0
        sig.target_price         = 324.0
        sig.atr                  = 6.0
        sig.confidence           = 6.0
        sig._obs_candidate_score = 0.7
        sig.expected_move_pct    = 4.0
        sig._obs_regime          = "range_market"
        sig.strategy_name        = "momentum"
        sig.risk_reward_ratio    = 2.0
        sig.opportunity_id       = "opp-t015"

        recs = ev.evaluate_and_record([sig])
        assert recs, "Expected at least one observation record"
        obs = recs[0]
        assert obs.get("actual_return_pct") is None, (
            "Non-executed KNOWLEDGE_OBSERVATION must have actual_return_pct=None"
        )
        assert obs.get("no_lookahead") is True, "no_lookahead must be True"

"""
tests/test_klp_002_outcome_tracking.py
=======================================
35 tests for KLP-002: Outcome tracking, evidence adapter, and decision-time
freezing.

Test groups:
  T01–T07  : _compute_outcome_from_bars — core outcome logic
  T08–T10  : MFE / MAE direction-awareness
  T11–T15  : KLPOutcomeEngine — pending detection, fill, dedup
  T16–T20  : Decision-time versioning fields
  T21–T25  : KLP evidence adapter — classification, dedup, ingestion
  T26–T30  : Safety: no look-ahead, no mutation, no broker calls
  T31–T35  : Integration: bridge integrity, full-chain field presence
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from opportunity_engine.klp_outcome_engine import (
    KLPOutcomeEngine,
    compute_outcome_from_bars,
    TARGET_HIT,
    STOP_HIT,
    OUTCOME_AMBIGUOUS,
    OUTCOME_EXPIRED,
    OUTCOME_PENDING,
    OUTCOME_NO_DATA,
    _OUTCOME_HORIZON_DAYS,
)
from opportunity_engine.klp_evaluator import KLPEvaluator
from scripts.knowledge_system.klp_evidence_adapter_001 import (
    ingest_klp_outcomes,
    _classify_klp,
    _build_evidence_record,
)
from scripts.knowledge_system.ksl_models import Classification, MissReason


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bars(
    n: int,
    base_close: float = 100.0,
    base_high: float  = 102.0,
    base_low: float   = 98.0,
) -> List[Dict[str, Any]]:
    """Generate n synthetic daily OHLCV bars starting from yesterday."""
    result = []
    today  = date.today()
    for i in range(n):
        d = today - timedelta(days=n - i)
        result.append({
            "date":  str(d),
            "open":  100.0,
            "high":  base_high,
            "low":   base_low,
            "close": base_close,
            "volume": 1000000.0,
        })
    return result


def _bars_with_hit(target_on_day: Optional[int] = None, stop_on_day: Optional[int] = None,
                   n: int = 5) -> List[Dict[str, Any]]:
    """
    Bars where high reaches 115.0 on target_on_day and low reaches 90.0 on stop_on_day.
    Days are 1-indexed.
    """
    today  = date.today()
    result = []
    for i in range(1, n + 1):
        d    = today - timedelta(days=n - i + 1)
        high = 115.0 if i == target_on_day else 102.0
        low  = 90.0  if i == stop_on_day  else 98.0
        result.append({
            "date":  str(d),
            "open":  100.0,
            "high":  high,
            "low":   low,
            "close": 100.0,
            "volume": 1000000.0,
        })
    return result


def _fresh_engine(tmp_path: Path) -> KLPOutcomeEngine:
    return KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=None)


def _write_klp_obs(tmp_path: Path, date_str: str, obs: Dict) -> None:
    klp_file = tmp_path / f"KLP_{date_str}.jsonl"
    with klp_file.open("a") as fh:
        fh.write(json.dumps(obs) + "\n")


def _make_obs(symbol: str = "RELIANCE", date_str: Optional[str] = None,
              entry: float = 100.0, target: float = 112.5, stop: float = 95.0,
              direction: str = "BUY") -> Dict:
    if date_str is None:
        date_str = str(date.today() - timedelta(days=2))  # yesterday - 1
    return {
        "obs_id":             f"{symbol}_{date_str}_100.00_klp",
        "event_type":         "KNOWLEDGE_OBSERVATION",
        "ts_utc":             "2026-08-20T09:15:00Z",
        "trading_date":       date_str,
        "symbol":             symbol,
        "direction":          direction,
        "reference_entry":    entry,
        "knowledge_target":   target,
        "knowledge_stop_loss": stop,
        "knowledge_RR":       2.5,
        "knowledge_selected": True,
        "no_lookahead":       True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# T01–T07 : compute_outcome_from_bars
# ─────────────────────────────────────────────────────────────────────────────

def test_T01_target_hit_when_high_reaches_target() -> None:
    """T01: first_event=TARGET_HIT when any bar's high >= target."""
    bars = _bars_with_hit(target_on_day=2, n=5)
    out  = compute_outcome_from_bars(entry=100.0, target=110.0, stop=90.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == TARGET_HIT
    assert out["target_hit"]  is True
    assert out["stop_hit"]    is False


def test_T02_stop_hit_when_low_reaches_stop() -> None:
    """T02: first_event=STOP_HIT when any bar's low <= stop."""
    bars = _bars_with_hit(stop_on_day=1, n=5)
    out  = compute_outcome_from_bars(entry=100.0, target=110.0, stop=95.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == STOP_HIT
    assert out["stop_hit"]    is True
    assert out["target_hit"]  is False


def test_T03_outcome_ambiguous_when_same_bar() -> None:
    """T03: OUTCOME_AMBIGUOUS when target and stop are both hit on the same bar."""
    bars = _bars_with_hit(target_on_day=2, stop_on_day=2, n=5)
    out  = compute_outcome_from_bars(entry=100.0, target=110.0, stop=90.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == OUTCOME_AMBIGUOUS
    assert out["target_hit"]  is True
    assert out["stop_hit"]    is True


def test_T04_target_first_when_target_day_less_than_stop_day() -> None:
    """T04: TARGET_HIT when target bar < stop bar."""
    bars = _bars_with_hit(target_on_day=2, stop_on_day=4, n=5)
    out  = compute_outcome_from_bars(entry=100.0, target=110.0, stop=90.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == TARGET_HIT


def test_T05_outcome_expired_when_horizon_passed_no_hit() -> None:
    """T05: OUTCOME_EXPIRED when T+5 bars available but no target or stop hit."""
    bars = _bars(n=5, base_high=102.0, base_low=98.0)
    out  = compute_outcome_from_bars(entry=100.0, target=115.0, stop=85.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == OUTCOME_EXPIRED


def test_T06_outcome_pending_when_fewer_than_horizon_bars() -> None:
    """T06: OUTCOME_PENDING when fewer than T+5 bars and no hit."""
    bars = _bars(n=2, base_high=102.0, base_low=98.0)
    out  = compute_outcome_from_bars(entry=100.0, target=115.0, stop=85.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == OUTCOME_PENDING


def test_T07_no_data_when_bars_empty() -> None:
    """T07: OUTCOME_NO_DATA when bars list is empty."""
    out = compute_outcome_from_bars(entry=100.0, target=110.0, stop=90.0,
                                    direction="BUY", bars=[])
    assert out["first_event"] == OUTCOME_NO_DATA


# ─────────────────────────────────────────────────────────────────────────────
# T08–T10 : MFE / MAE direction-awareness
# ─────────────────────────────────────────────────────────────────────────────

def test_T08_mfe_positive_for_buy_when_high_exceeds_entry() -> None:
    """T08: MFE is positive (%) when price goes above entry for BUY."""
    bars = _bars(n=5, base_high=108.0, base_low=97.0)
    out  = compute_outcome_from_bars(entry=100.0, target=115.0, stop=85.0,
                                     direction="BUY", bars=bars)
    assert out["mfe_pct"] is not None
    assert out["mfe_pct"] > 0.0


def test_T09_mae_negative_for_buy_when_low_below_entry() -> None:
    """T09: MAE is negative (%) when price dips below entry for BUY."""
    bars = _bars(n=5, base_high=102.0, base_low=95.0)
    out  = compute_outcome_from_bars(entry=100.0, target=115.0, stop=90.0,
                                     direction="BUY", bars=bars)
    assert out["mae_pct"] is not None
    assert out["mae_pct"] < 0.0


def test_T10_t1_ret_pct_correct() -> None:
    """T10: T+1 return % = (close_T+1 / entry - 1) × 100."""
    bars = [{"date": "2026-08-21", "open": 100.0, "high": 105.0,
             "low": 98.0, "close": 103.0, "volume": 1e6}]
    out  = compute_outcome_from_bars(entry=100.0, target=115.0, stop=90.0,
                                     direction="BUY", bars=bars)
    assert abs((out["t1_ret_pct"] or 0) - 3.0) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# T11–T15 : KLPOutcomeEngine
# ─────────────────────────────────────────────────────────────────────────────

def test_T11_pending_count_returns_zero_for_empty_dir(tmp_path: Path) -> None:
    """T11: get_pending_count returns 0 when no KLP file exists."""
    engine = _fresh_engine(tmp_path)
    assert engine.get_pending_count("2026-08-20") == 0


def test_T12_fill_pending_writes_outcome_update(tmp_path: Path) -> None:
    """T12: fill_pending_outcomes writes OUTCOME_UPDATE for completed obs."""
    date_str = str(date.today() - timedelta(days=2))
    obs = _make_obs(date_str=date_str)
    _write_klp_obs(tmp_path, date_str, obs)

    bars = _bars_with_hit(target_on_day=1, n=5)

    def mock_fetcher(symbol, trading_date):
        return bars

    engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=mock_fetcher)
    result = engine.fill_pending_outcomes(dates=[date_str])
    assert result["processed"] >= 1

    klp_file = tmp_path / f"KLP_{date_str}.jsonl"
    records  = [json.loads(l) for l in klp_file.read_text().splitlines() if l.strip()]
    updates  = [r for r in records if r.get("event_type") == "OUTCOME_UPDATE"]
    assert len(updates) == 1
    assert updates[0]["first_event"] == TARGET_HIT


def test_T13_fill_skips_today_observations(tmp_path: Path) -> None:
    """T13: fill_pending_outcomes skips observations with trading_date = today."""
    today = str(date.today())
    obs   = _make_obs(date_str=today)
    _write_klp_obs(tmp_path, today, obs)

    engine = KLPOutcomeEngine(data_dir=tmp_path)
    result = engine.fill_pending_outcomes(dates=[today])
    assert result.get("skipped_pending", 0) >= 1


def test_T14_no_duplicate_outcome_update_for_same_obs(tmp_path: Path) -> None:
    """T14: Second fill call for same obs_id does not write duplicate OUTCOME_UPDATE."""
    date_str = str(date.today() - timedelta(days=3))
    obs  = _make_obs(date_str=date_str)
    _write_klp_obs(tmp_path, date_str, obs)
    bars = _bars_with_hit(target_on_day=1, n=5)

    engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=lambda s, d: bars)
    engine.fill_pending_outcomes(dates=[date_str])
    engine.fill_pending_outcomes(dates=[date_str])   # second call

    klp_file = tmp_path / f"KLP_{date_str}.jsonl"
    records  = [json.loads(l) for l in klp_file.read_text().splitlines() if l.strip()]
    updates  = [r for r in records if r.get("event_type") == "OUTCOME_UPDATE"]
    assert len(updates) == 1, f"Expected 1 OUTCOME_UPDATE, got {len(updates)}"


def test_T15_outcome_update_has_no_lookahead_true(tmp_path: Path) -> None:
    """T15: OUTCOME_UPDATE records have no_lookahead=True."""
    date_str = str(date.today() - timedelta(days=4))
    obs  = _make_obs(date_str=date_str)
    _write_klp_obs(tmp_path, date_str, obs)
    bars = _bars(n=5)

    engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=lambda s, d: bars)
    engine.fill_pending_outcomes(dates=[date_str])

    klp_file = tmp_path / f"KLP_{date_str}.jsonl"
    records  = [json.loads(l) for l in klp_file.read_text().splitlines() if l.strip()]
    updates  = [r for r in records if r.get("event_type") == "OUTCOME_UPDATE"]
    assert all(r.get("no_lookahead") is True for r in updates)


# ─────────────────────────────────────────────────────────────────────────────
# T16–T20 : Decision-time versioning fields
# ─────────────────────────────────────────────────────────────────────────────

def _make_signal_mock(symbol: str = "RELIANCE") -> MagicMock:
    sig = MagicMock()
    sig.symbol               = symbol
    sig.direction            = MagicMock(value="BUY")
    sig.entry_price          = 100.0
    sig.stop_loss            = 95.0
    sig.target_price         = 112.5
    sig.atr                  = 3.0
    sig.confidence           = 7.5
    sig._obs_candidate_score = 0.8
    sig.expected_move_pct    = 5.0
    sig._obs_regime          = "range_market"
    sig.strategy_name        = "breakout"
    sig.risk_reward_ratio    = 2.5
    return sig


def test_T16_calculation_version_present_in_observation(tmp_path: Path) -> None:
    """T16: KNOWLEDGE_OBSERVATION records contain calculation_version field."""
    ev   = KLPEvaluator(data_dir=tmp_path)
    sigs = [_make_signal_mock()]
    recs = ev.evaluate_and_record(sigs)
    assert recs, "Expected at least one record"
    assert "calculation_version" in recs[0], "Missing calculation_version"
    assert recs[0]["calculation_version"] == "KLP_001_v1"


def test_T17_target_method_version_present(tmp_path: Path) -> None:
    """T17: target_method_version field is present in KNOWLEDGE_OBSERVATION."""
    ev   = KLPEvaluator(data_dir=tmp_path)
    sigs = [_make_signal_mock()]
    recs = ev.evaluate_and_record(sigs)
    assert recs[0].get("target_method_version") is not None


def test_T18_stop_method_version_present(tmp_path: Path) -> None:
    """T18: stop_method_version field is present in KNOWLEDGE_OBSERVATION."""
    ev   = KLPEvaluator(data_dir=tmp_path)
    sigs = [_make_signal_mock()]
    recs = ev.evaluate_and_record(sigs)
    assert recs[0].get("stop_method_version") is not None


def test_T19_knowledge_execution_status_not_executed_for_rejected(tmp_path: Path) -> None:
    """T19: STRATEGY_ANNOTATION has knowledge_execution_status=NOT_EXECUTED when strategy rejects."""
    ev    = KLPEvaluator(data_dir=tmp_path)
    sigs  = [_make_signal_mock("WIPRO")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, set(), {"WIPRO": "STRATEGY_DISABLED"})

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    klp_file = tmp_path / f"KLP_{today}.jsonl"
    records  = [json.loads(l) for l in klp_file.read_text().splitlines() if l.strip()]
    ann = [r for r in records if r.get("event_type") == "STRATEGY_ANNOTATION"]
    assert ann, "Expected STRATEGY_ANNOTATION"
    assert ann[0]["knowledge_execution_status"] == "NOT_EXECUTED"


def test_T20_observation_type_knowledge_only_for_selected_rejected(tmp_path: Path) -> None:
    """T20: knowledge_selected+strategy_rejected → observation_type=KNOWLEDGE_ONLY_OBSERVATION."""
    ev    = KLPEvaluator(data_dir=tmp_path)
    sigs  = [_make_signal_mock("BPCL")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, set(), {"BPCL": "STRATEGY_DISABLED"})

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    klp_file = tmp_path / f"KLP_{today}.jsonl"
    records  = [json.loads(l) for l in klp_file.read_text().splitlines() if l.strip()]
    ann      = [r for r in records if r.get("event_type") == "STRATEGY_ANNOTATION"]
    assert ann[0].get("observation_type") == "KNOWLEDGE_ONLY_OBSERVATION"


# ─────────────────────────────────────────────────────────────────────────────
# T21–T25 : KLP evidence adapter
# ─────────────────────────────────────────────────────────────────────────────

def _write_completed_klp(tmp_dir: Path, date_str: str) -> None:
    """Write a KLP file with observation + outcome pair."""
    obs = _make_obs(date_str=date_str, direction="BUY")
    outcome = {
        "obs_id":          obs["obs_id"],
        "event_type":      "OUTCOME_UPDATE",
        "trading_date":    date_str,
        "symbol":          obs["symbol"],
        "direction":       "BUY",
        "first_event":     TARGET_HIT,
        "target_hit":      True,
        "stop_hit":        False,
        "t1_ret_pct":      4.5,
        "t3_ret_pct":      6.1,
        "t5_ret_pct":      7.2,
        "mfe_pct":         8.0,
        "mae_pct":         -1.2,
        "direction_correct": True,
        "ge1":             True,
        "ge2":             True,
        "ge3":             False,
        "theoretical_R":   2.5,
        "no_lookahead":    True,
    }
    klp_file = tmp_dir / f"KLP_{date_str}.jsonl"
    with klp_file.open("a") as fh:
        fh.write(json.dumps(obs) + "\n")
        fh.write(json.dumps(outcome) + "\n")


def test_T21_ingest_adds_record_to_shadow_ledger(tmp_path: Path) -> None:
    """T21: ingest_klp_outcomes appends an EvidenceRecord to the shadow ledger."""
    klp_dir   = tmp_path / "klp"
    klp_dir.mkdir()
    ledger    = tmp_path / "ledger.jsonl"
    k_ledger  = tmp_path / "k_ledger.jsonl"
    state_p   = tmp_path / "state.json"
    date_str  = str(date.today() - timedelta(days=2))

    _write_completed_klp(klp_dir, date_str)

    result = ingest_klp_outcomes(
        dates=[date_str],
        klp_data_dir=klp_dir,
        shadow_ledger=ledger,
        knowledge_ledger=k_ledger,
        state_path=state_p,
    )
    assert result["new_records"] == 1
    assert ledger.exists()
    records = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert len(records) == 1
    assert records[0]["symbol"] == "RELIANCE"


def test_T22_ingest_dedup_prevents_double_ingest(tmp_path: Path) -> None:
    """T22: Running ingest twice for the same date produces 0 new records on second run."""
    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    ledger   = tmp_path / "ledger.jsonl"
    k_ledger = tmp_path / "k_ledger.jsonl"
    state_p  = tmp_path / "state.json"
    date_str = str(date.today() - timedelta(days=3))

    _write_completed_klp(klp_dir, date_str)

    r1 = ingest_klp_outcomes(dates=[date_str], klp_data_dir=klp_dir,
                              shadow_ledger=ledger, knowledge_ledger=k_ledger, state_path=state_p)
    r2 = ingest_klp_outcomes(dates=[date_str], klp_data_dir=klp_dir,
                              shadow_ledger=ledger, knowledge_ledger=k_ledger, state_path=state_p)
    assert r1["new_records"] == 1
    assert r2["new_records"] == 0


def test_T23_classify_correct_select_for_selected_and_correct(tmp_path: Path) -> None:
    """T23: CORRECT_SELECT when knowledge_selected=True and direction_correct=True."""
    classif, _ = _classify_klp(k_selected=True, strat_rejected=False,
                                direction_correct=True, ge1=True, ge2=True)
    assert classif == Classification.CORRECT_SELECT


def test_T24_classify_ranking_miss_for_unselected_ge2(tmp_path: Path) -> None:
    """T24: RANKING_MISS when knowledge_selected=False and ge2=True."""
    classif, _ = _classify_klp(k_selected=False, strat_rejected=False,
                                direction_correct=True, ge1=True, ge2=True)
    assert classif == Classification.RANKING_MISS


def test_T25_ingest_skips_pending_outcomes(tmp_path: Path) -> None:
    """T25: Observations with OUTCOME_PENDING first_event are not ingested."""
    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    ledger   = tmp_path / "ledger.jsonl"
    k_ledger = tmp_path / "k_ledger.jsonl"
    state_p  = tmp_path / "state.json"
    date_str = str(date.today() - timedelta(days=1))

    obs = _make_obs(date_str=date_str)
    pending_outcome = {
        "obs_id": obs["obs_id"], "event_type": "OUTCOME_UPDATE",
        "trading_date": date_str, "symbol": "RELIANCE", "direction": "BUY",
        "first_event": OUTCOME_PENDING, "no_lookahead": True,
    }
    klp_file = klp_dir / f"KLP_{date_str}.jsonl"
    with klp_file.open("a") as fh:
        fh.write(json.dumps(obs) + "\n")
        fh.write(json.dumps(pending_outcome) + "\n")

    result = ingest_klp_outcomes(dates=[date_str], klp_data_dir=klp_dir,
                                 shadow_ledger=ledger, knowledge_ledger=k_ledger, state_path=state_p)
    assert result["new_records"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# T26–T30 : Safety
# ─────────────────────────────────────────────────────────────────────────────

def test_T26_outcome_uses_reference_entry_not_t1_open(tmp_path: Path) -> None:
    """T26: Outcome uses reference_entry (frozen), not T+1 open (look-ahead)."""
    entry = 100.0
    bars  = [{"date": "2026-08-21", "open": 105.0,   # T+1 open differs from entry
              "high": 110.0, "low": 98.0, "close": 108.0, "volume": 1e6}]
    out   = compute_outcome_from_bars(entry=entry, target=108.0, stop=90.0,
                                      direction="BUY", bars=bars)
    # T+1 return should be vs entry=100, not vs open=105
    assert abs((out["t1_ret_pct"] or 0) - 8.0) < 0.1


def test_T27_outcome_computation_never_raises() -> None:
    """T27: compute_outcome_from_bars never raises regardless of bad input."""
    compute_outcome_from_bars(entry=0, target=None, stop=None, direction="BUY", bars=[])
    compute_outcome_from_bars(entry=-1, target=100, stop=90, direction="SELL", bars=[])
    compute_outcome_from_bars(entry=100, target=110, stop=90, direction="UNKNOWN", bars=_bars(3))


def test_T28_fill_pending_never_raises(tmp_path: Path) -> None:
    """T28: KLPOutcomeEngine.fill_pending_outcomes never raises on any input."""
    engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=lambda s, d: None)
    result = engine.fill_pending_outcomes(dates=["not-a-date", "2026-08-20"])
    assert isinstance(result, dict)


def test_T29_ingest_never_raises_on_corrupt_file(tmp_path: Path) -> None:
    """T29: ingest_klp_outcomes never raises on a corrupt KLP file."""
    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    klp_file = klp_dir / "KLP_2026-08-01.jsonl"
    klp_file.write_text("CORRUPT{{{NOT_JSON\n{}\n")

    result = ingest_klp_outcomes(
        dates=["2026-08-01"],
        klp_data_dir=klp_dir,
        shadow_ledger=tmp_path / "ledger.jsonl",
        knowledge_ledger=tmp_path / "k_ledger.jsonl",
        state_path=tmp_path / "state.json",
    )
    assert isinstance(result, dict)


def test_T30_outcome_engine_broker_calls_zero(tmp_path: Path) -> None:
    """T30: KLPOutcomeEngine imports no broker, execution, or order manager modules."""
    source = Path(__file__).resolve().parents[1] / "opportunity_engine" / "klp_outcome_engine.py"
    content = source.read_text(encoding="utf-8")
    forbidden_imports = [
        "from execution_engine",
        "import order_manager",
        "from order_manager",
        "from risk_control",
        "place_order",
        "ZerodhaBroker",
        "DhanFeed",
    ]
    for kw in forbidden_imports:
        assert kw not in content, f"Forbidden import/call '{kw}' found in klp_outcome_engine.py"


# ─────────────────────────────────────────────────────────────────────────────
# T31–T35 : Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_T31_outcome_update_has_all_required_fields(tmp_path: Path) -> None:
    """T31: OUTCOME_UPDATE records contain all required outcome fields."""
    required = {
        "obs_id", "event_type", "ts_utc", "trading_date", "symbol", "direction",
        "reference_entry", "knowledge_target", "knowledge_stop_loss",
        "first_event", "target_hit", "stop_hit",
        "t1_ret_pct", "mfe_pct", "mae_pct",
        "bars_available", "outcome_version", "no_lookahead",
    }
    date_str = str(date.today() - timedelta(days=2))
    obs  = _make_obs(date_str=date_str)
    _write_klp_obs(tmp_path, date_str, obs)
    bars = _bars_with_hit(target_on_day=1, n=5)

    engine = KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=lambda s, d: bars)
    engine.fill_pending_outcomes(dates=[date_str])

    klp_file = tmp_path / f"KLP_{date_str}.jsonl"
    records  = [json.loads(l) for l in klp_file.read_text().splitlines() if l.strip()]
    updates  = [r for r in records if r.get("event_type") == "OUTCOME_UPDATE"]
    assert updates, "No OUTCOME_UPDATE written"
    missing  = required - set(updates[0].keys())
    assert not missing, f"Missing fields: {missing}"


def test_T32_theoretical_r_positive_for_target_hit(tmp_path: Path) -> None:
    """T32: theoretical_R is positive when target is hit before stop."""
    bars = _bars_with_hit(target_on_day=2, n=5)
    out  = compute_outcome_from_bars(entry=100.0, target=112.5, stop=95.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == TARGET_HIT
    assert out["theoretical_R"] is not None
    assert out["theoretical_R"] > 0


def test_T33_theoretical_r_negative_one_for_stop_hit(tmp_path: Path) -> None:
    """T33: theoretical_R = -1.0 when stop is hit before target."""
    bars = _bars_with_hit(stop_on_day=1, n=5)
    out  = compute_outcome_from_bars(entry=100.0, target=115.0, stop=95.0,
                                     direction="BUY", bars=bars)
    assert out["first_event"] == STOP_HIT
    assert out["theoretical_R"] == -1.0


def test_T34_short_direction_target_hit_on_low(tmp_path: Path) -> None:
    """T34: For SHORT direction, target is hit when bar LOW <= target (below entry)."""
    # SHORT: entry=100, target=88 (below), stop=108 (above)
    # Bar 1 has low=87 which is <= target=88 → TARGET_HIT
    bars = [
        {"date": "2026-08-20", "open": 100.0, "high": 103.0, "low": 87.0,
         "close": 89.0, "volume": 1e6},
        {"date": "2026-08-21", "open": 89.0,  "high": 91.0,  "low": 86.0,
         "close": 88.0, "volume": 1e6},
    ]
    out = compute_outcome_from_bars(entry=100.0, target=88.0, stop=108.0,
                                    direction="SHORT", bars=bars)
    assert out["first_event"] == TARGET_HIT
    assert out["target_hit"]  is True


def test_T35_klp_chain_obs_to_outcome_to_evidence(tmp_path: Path) -> None:
    """T35: Full chain OBSERVATION → OUTCOME_UPDATE → evidence ingest works end-to-end."""
    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    ledger   = tmp_path / "ledger.jsonl"
    k_ledger = tmp_path / "k_ledger.jsonl"
    state_p  = tmp_path / "state.json"
    date_str = str(date.today() - timedelta(days=5))

    # Step 1: Write observation
    obs = _make_obs(date_str=date_str)
    _write_klp_obs(klp_dir, date_str, obs)

    # Step 2: Fill outcome
    bars   = _bars_with_hit(target_on_day=2, n=5)
    engine = KLPOutcomeEngine(data_dir=klp_dir, _ohlcv_fetcher=lambda s, d: bars)
    result = engine.fill_pending_outcomes(dates=[date_str])
    assert result["processed"] == 1, f"Expected 1 processed, got {result}"

    # Step 3: Ingest to evidence ledger
    r = ingest_klp_outcomes(
        dates=[date_str],
        klp_data_dir=klp_dir,
        shadow_ledger=ledger,
        knowledge_ledger=k_ledger,
        state_path=state_p,
    )
    assert r["new_records"] == 1, f"Expected 1 evidence record, got {r}"

    # Step 4: Verify evidence record is valid
    records = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert records[0]["symbol"]  == "RELIANCE"
    assert records[0]["source"]  == "klp"

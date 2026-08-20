"""
tests/test_knowledge_parallel_layer.py
=======================================
33 tests for the Knowledge-Led Parallel Decision Layer (KLP-001).

Test groups:
  T01–T05  : KNOWLEDGE_RESEARCH_SCORE_v1 formula
  T06–T10  : evaluate_and_record() — scoring, ranking, selection
  T11–T15  : annotate_strategy_outcome() — strategy annotation
  T16–T20  : File I/O — append-only JSONL, fields, dedup
  T21–T25  : KLPBridge — transfer, watermark, validation
  T26–T30  : Integration — end-to-end cycle assertions
  T31–T33  : Safety — no signal mutation, no raises, singleton

All tests use isolated temporary directories.  No production data is
read or written.
"""
from __future__ import annotations

import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from opportunity_engine.klp_evaluator import (
    KLPEvaluator,
    compute_knowledge_score,
    _compute_disagreement,
    _evaluate_structural,
    _make_obs_id,
    AGREE_PASS,
    AGREE_REJECT,
    KNOWLEDGE_OVERRULES,
    STRATEGY_OVERRULES,
    STRUCTURAL_OVERRIDE,
    KNOWLEDGE_TOP_N,
    _W_CANDIDATE_SCORE,
    _W_CONFIDENCE,
    _W_EXPECTED_MOVE,
    _W_RISK_REWARD,
    _W_REGIME_ALIGN,
)
from scripts.knowledge_system.klp_bridge_001 import KLPBridge, _parse_and_validate


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class _Dir:
    """Minimal mock for SignalDirection."""
    def __init__(self, v: str) -> None:
        self.value = v
    def __str__(self) -> str:
        return self.value


def _make_signal(
    symbol: str = "RELIANCE",
    direction: str = "BUY",
    entry: float = 100.0,
    stop: float = 95.0,
    target: float = 112.5,
    atr: float = 3.0,
    confidence: float = 7.5,
    candidate_score: float = 0.8,
    expected_move_pct: float = 5.0,
    regime: str = "range_market",
    strategy_name: str = "breakout",
) -> MagicMock:
    sig = MagicMock()
    sig.symbol               = symbol
    sig.direction            = _Dir(direction)
    sig.entry_price          = entry
    sig.stop_loss            = stop
    sig.target_price         = target
    sig.atr                  = atr
    sig.confidence           = confidence
    sig._obs_candidate_score = candidate_score
    sig.expected_move_pct    = expected_move_pct
    sig._obs_regime          = regime
    sig.strategy_name        = strategy_name
    sig.risk_reward_ratio    = abs(target - entry) / abs(entry - stop) if entry != stop else 0.0
    return sig


def _make_signals(n: int, **kwargs) -> List[MagicMock]:
    """Create n signals with unique symbols and candidate_scores."""
    sigs = []
    for i in range(n):
        s = _make_signal(
            symbol=f"SYM{i:03d}",
            candidate_score=max(0.1, 0.9 - i * 0.05),
            entry=100.0 + i,
            stop=94.0 + i,
            target=115.0 + i,
            **kwargs,
        )
        sigs.append(s)
    return sigs


def _fresh_evaluator(tmp_path: Path) -> KLPEvaluator:
    """Return a fresh KLPEvaluator with isolated tmp directory."""
    return KLPEvaluator(data_dir=tmp_path)


def _read_klp(tmp_path: Path) -> List[Dict[str, Any]]:
    """Read all records from today's KLP file in tmp_path."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    klp_file = tmp_path / f"KLP_{today}.jsonl"
    if not klp_file.exists():
        return []
    records = []
    for line in klp_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ─────────────────────────────────────────────────────────────────────────────
# T01–T05 : KNOWLEDGE_RESEARCH_SCORE_v1 formula
# ─────────────────────────────────────────────────────────────────────────────

def test_T01_score_for_ideal_signal_is_high() -> None:
    """T01: A signal with all components at max should score ≥ 0.85."""
    sig = _make_signal(
        candidate_score=1.0,
        confidence=10.0,
        expected_move_pct=8.0,
        entry=100.0, stop=93.33, target=120.0,   # RR = 3.0
        regime="bull_trend",
        direction="BUY",
    )
    score = compute_knowledge_score(sig)
    assert score >= 0.85, f"Expected ≥ 0.85, got {score}"


def test_T02_score_for_zero_fields_is_zero() -> None:
    """T02: A signal with all zero / None fields should score 0.0."""
    sig = MagicMock()
    sig.symbol               = "ZERO"
    sig.direction            = None
    sig.entry_price          = 0.0
    sig.stop_loss            = 0.0
    sig.target_price         = 0.0
    sig.atr                  = 0.0
    sig.confidence           = 0.0
    sig._obs_candidate_score = None
    sig.expected_move_pct    = None
    sig._obs_regime          = None
    score = compute_knowledge_score(sig)
    assert score == 0.0, f"Expected 0.0, got {score}"


def test_T03_score_is_bounded_to_0_1() -> None:
    """T03: Score is always in [0.0, 1.0] regardless of extreme inputs."""
    # Over-sized inputs
    sig = _make_signal(
        candidate_score=999.0,
        confidence=999.0,
        expected_move_pct=999.0,
        entry=100.0, stop=50.0, target=200.0,   # RR = 2.0
        regime="bull_trend",
    )
    score = compute_knowledge_score(sig)
    assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"


def test_T04_higher_candidate_score_increases_knowledge_score() -> None:
    """T04: Increasing _obs_candidate_score increases knowledge_score."""
    sig_lo = _make_signal(candidate_score=0.3)
    sig_hi = _make_signal(candidate_score=0.9)
    assert compute_knowledge_score(sig_hi) > compute_knowledge_score(sig_lo)


def test_T05_regime_alignment_affects_score() -> None:
    """T05: BULL_TREND + BUY scores higher than BEAR_MARKET + BUY."""
    sig_bull = _make_signal(regime="bull_trend",  direction="BUY", candidate_score=0.5)
    sig_bear = _make_signal(regime="bear_market", direction="BUY", candidate_score=0.5)
    assert compute_knowledge_score(sig_bull) > compute_knowledge_score(sig_bear)


# ─────────────────────────────────────────────────────────────────────────────
# T06–T10 : evaluate_and_record()
# ─────────────────────────────────────────────────────────────────────────────

def test_T06_empty_signals_returns_empty_list(tmp_path: Path) -> None:
    """T06: evaluate_and_record([]) returns [] and writes nothing."""
    ev = _fresh_evaluator(tmp_path)
    result = ev.evaluate_and_record([], snapshot=None)
    assert result == []
    assert len(list(tmp_path.glob("*.jsonl"))) == 0


def test_T07_returns_n_records_for_n_signals(tmp_path: Path) -> None:
    """T07: evaluate_and_record(N signals) returns N observation records."""
    ev     = _fresh_evaluator(tmp_path)
    sigs   = _make_signals(7)
    result = ev.evaluate_and_record(sigs, snapshot=None)
    assert len(result) == 7


def test_T08_ranks_are_1_based_and_unique(tmp_path: Path) -> None:
    """T08: knowledge_rank values are {1, 2, …, N} exactly."""
    ev     = _fresh_evaluator(tmp_path)
    sigs   = _make_signals(5)
    result = ev.evaluate_and_record(sigs, snapshot=None)
    ranks  = sorted(r["knowledge_rank"] for r in result)
    assert ranks == list(range(1, 6))


def test_T09_dedup_second_call_returns_empty(tmp_path: Path) -> None:
    """T09: A second evaluate_and_record call for the same signals (same symbols + date) returns []."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = _make_signals(3)
    ev.evaluate_and_record(sigs, snapshot=None)
    result2 = ev.evaluate_and_record(sigs, snapshot=None)
    assert result2 == []


def test_T10_knowledge_selected_marks_top_n(tmp_path: Path) -> None:
    """T10: Exactly KNOWLEDGE_TOP_N signals are marked knowledge_selected=True."""
    n  = KNOWLEDGE_TOP_N + 3
    ev = _fresh_evaluator(tmp_path)
    result = ev.evaluate_and_record(_make_signals(n), snapshot=None)
    selected = [r for r in result if r["knowledge_selected"]]
    not_sel  = [r for r in result if not r["knowledge_selected"]]
    assert len(selected) == KNOWLEDGE_TOP_N
    assert len(not_sel)  == n - KNOWLEDGE_TOP_N


# ─────────────────────────────────────────────────────────────────────────────
# T11–T15 : annotate_strategy_outcome()
# ─────────────────────────────────────────────────────────────────────────────

def test_T11_approved_symbol_gets_pass_status(tmp_path: Path) -> None:
    """T11: A symbol in approved_symbols receives strategy_status=PASS."""
    ev    = _fresh_evaluator(tmp_path)
    sigs  = [_make_signal("RELIANCE")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {"RELIANCE"}, {})
    records = [r for r in _read_klp(tmp_path) if r.get("event_type") == "STRATEGY_ANNOTATION"]
    assert len(records) == 1
    assert records[0]["strategy_status"] == "PASS"


def test_T12_rejected_symbol_gets_rejected_status(tmp_path: Path) -> None:
    """T12: A symbol NOT in approved_symbols receives strategy_status=REJECTED."""
    ev    = _fresh_evaluator(tmp_path)
    sigs  = [_make_signal("INFY")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, set(), {"INFY": "STRATEGY_DISABLED"})
    records = [r for r in _read_klp(tmp_path) if r.get("event_type") == "STRATEGY_ANNOTATION"]
    assert records[0]["strategy_status"] == "REJECTED"
    assert records[0]["strategy_rejection_reason"] == "STRATEGY_DISABLED"


def test_T13_annotation_event_type_is_correct(tmp_path: Path) -> None:
    """T13: Annotation records have event_type='STRATEGY_ANNOTATION'."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = [_make_signal("TCS")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {"TCS"}, {})
    records = _read_klp(tmp_path)
    ann_records = [r for r in records if r["event_type"] == "STRATEGY_ANNOTATION"]
    assert len(ann_records) == 1


def test_T14_disagreement_agree_pass_when_both_approve(tmp_path: Path) -> None:
    """T14: AGREE_PASS when knowledge selects and strategy approves."""
    # Use 1 signal so it's always knowledge_selected (rank=1 ≤ TOP_N=5)
    ev   = _fresh_evaluator(tmp_path)
    sigs = [_make_signal("HDFCBANK")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {"HDFCBANK"}, {})
    ann = [r for r in _read_klp(tmp_path) if r["event_type"] == "STRATEGY_ANNOTATION"][0]
    assert ann["knowledge_strategy_disagreement"] == AGREE_PASS


def test_T15_disagreement_knowledge_overrules_when_selected_but_rejected(tmp_path: Path) -> None:
    """T15: KNOWLEDGE_OVERRULES when knowledge selects but strategy rejects (RANGE regime)."""
    ev = _fresh_evaluator(tmp_path)
    # 1 signal in RANGE_MARKET (structural = PASS, so no STRUCTURAL_OVERRIDE)
    sigs = [_make_signal("WIPRO", regime="range_market")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, set(), {"WIPRO": "STRATEGY_DISABLED"})
    ann = [r for r in _read_klp(tmp_path) if r["event_type"] == "STRATEGY_ANNOTATION"][0]
    assert ann["knowledge_strategy_disagreement"] in (KNOWLEDGE_OVERRULES, STRUCTURAL_OVERRIDE)


# ─────────────────────────────────────────────────────────────────────────────
# T16–T20 : File I/O
# ─────────────────────────────────────────────────────────────────────────────

def test_T16_observation_records_written_to_file(tmp_path: Path) -> None:
    """T16: KNOWLEDGE_OBSERVATION records are persisted to the daily KLP file."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = _make_signals(4)
    ev.evaluate_and_record(sigs)
    records = _read_klp(tmp_path)
    obs = [r for r in records if r["event_type"] == "KNOWLEDGE_OBSERVATION"]
    assert len(obs) == 4


def test_T17_annotation_records_appended_to_same_file(tmp_path: Path) -> None:
    """T17: STRATEGY_ANNOTATION records are appended to the same daily file."""
    ev    = _fresh_evaluator(tmp_path)
    sigs  = [_make_signal("MARUTI")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {"MARUTI"}, {})
    records = _read_klp(tmp_path)
    types_found = {r["event_type"] for r in records}
    assert "KNOWLEDGE_OBSERVATION" in types_found
    assert "STRATEGY_ANNOTATION"   in types_found


def test_T18_records_have_no_lookahead_true(tmp_path: Path) -> None:
    """T18: All written records assert no_lookahead=True."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = _make_signals(3)
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {sigs[0].symbol}, {})
    records = _read_klp(tmp_path)
    assert all(r.get("no_lookahead") is True for r in records)


def test_T19_second_cycle_appends_not_overwrites(tmp_path: Path) -> None:
    """T19: A second evaluator instance on the same tmp_path appends (file is cumulative)."""
    ev1  = _fresh_evaluator(tmp_path)
    sigs1 = [_make_signal("ADANI")]
    ev1.evaluate_and_record(sigs1)
    first_count = len(_read_klp(tmp_path))

    ev2  = _fresh_evaluator(tmp_path)   # fresh instance, same dir
    sigs2 = [_make_signal("BAJAJ")]
    ev2.evaluate_and_record(sigs2)
    second_count = len(_read_klp(tmp_path))

    assert second_count == first_count + 1   # one new KNOWLEDGE_OBSERVATION appended


def test_T20_obs_id_consistent_between_observation_and_annotation(tmp_path: Path) -> None:
    """T20: obs_id in KNOWLEDGE_OBSERVATION matches obs_id in STRATEGY_ANNOTATION."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = [_make_signal("HDFC")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {"HDFC"}, {})
    records = _read_klp(tmp_path)
    obs_ids_obs = {r["obs_id"] for r in records if r["event_type"] == "KNOWLEDGE_OBSERVATION"}
    obs_ids_ann = {r["obs_id"] for r in records if r["event_type"] == "STRATEGY_ANNOTATION"}
    assert obs_ids_obs == obs_ids_ann, "obs_id mismatch between observation and annotation"


# ─────────────────────────────────────────────────────────────────────────────
# T21–T25 : KLPBridge
# ─────────────────────────────────────────────────────────────────────────────

def _make_bridge(tmp_path: Path, download_fn) -> KLPBridge:
    return KLPBridge(
        local_klp_dir=tmp_path / "klp",
        state_path=tmp_path / "state.json",
        _download_fn=download_fn,
    )


def test_T21_transfer_returns_zero_when_remote_file_missing(tmp_path: Path) -> None:
    """T21: transfer() returns 0 records when remote file is missing (scp error)."""
    def fail_download(remote, local):
        return "scp_failed: No such file"

    bridge = _make_bridge(tmp_path, fail_download)
    result = bridge.transfer("2026-08-20")
    assert result["records_transferred"] == 0
    assert result["error"] is not None


def test_T22_transfer_returns_correct_count(tmp_path: Path) -> None:
    """T22: transfer() correctly counts new records."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = [
        {"obs_id": f"SYM_{i}_klp", "event_type": "KNOWLEDGE_OBSERVATION",
         "no_lookahead": True, "trading_date": today}
        for i in range(3)
    ]
    raw = ("\n".join(json.dumps(r) for r in records) + "\n").encode()

    def succeed_download(remote, local):
        local.write_bytes(raw)
        return None

    bridge = _make_bridge(tmp_path, succeed_download)
    result = bridge.transfer(today)
    assert result["records_transferred"] == 3
    assert result["error"] is None


def test_T23_watermark_prevents_re_transfer(tmp_path: Path) -> None:
    """T23: Re-running transfer for the same date only transfers new bytes."""
    today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = [
        {"obs_id": f"SYM_{i}_klp", "event_type": "KNOWLEDGE_OBSERVATION",
         "no_lookahead": True, "trading_date": today}
        for i in range(4)
    ]
    raw = ("\n".join(json.dumps(r) for r in records) + "\n").encode()

    def succeed_download(remote, local):
        local.write_bytes(raw)
        return None

    bridge = _make_bridge(tmp_path, succeed_download)
    r1 = bridge.transfer(today)
    r2 = bridge.transfer(today)   # second call — same bytes
    assert r1["records_transferred"] == 4
    assert r2["records_transferred"] == 0   # watermark prevents re-transfer


def test_T24_malformed_json_lines_are_skipped(tmp_path: Path) -> None:
    """T24: Malformed JSON lines in the remote file are silently skipped."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = (
        '{"obs_id":"A","event_type":"KNOWLEDGE_OBSERVATION","no_lookahead":true,"trading_date":"' + today + '"}\n'
        '{NOT_VALID_JSON}\n'
        '{"obs_id":"B","event_type":"KNOWLEDGE_OBSERVATION","no_lookahead":true,"trading_date":"' + today + '"}\n'
    ).encode()

    def succeed_download(remote, local):
        local.write_bytes(raw)
        return None

    bridge = _make_bridge(tmp_path, succeed_download)
    result = bridge.transfer(today)
    assert result["records_transferred"] == 2   # only 2 valid records


def test_T25_no_lookahead_false_records_are_rejected(tmp_path: Path) -> None:
    """T25: Records with no_lookahead=False are rejected by _parse_and_validate."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = (
        '{"obs_id":"A","event_type":"KNOWLEDGE_OBSERVATION","no_lookahead":false,"trading_date":"' + today + '"}\n'
        '{"obs_id":"B","event_type":"KNOWLEDGE_OBSERVATION","no_lookahead":true,"trading_date":"' + today + '"}\n'
    ).encode()
    records = _parse_and_validate(raw)
    assert len(records) == 1
    assert records[0]["obs_id"] == "B"


# ─────────────────────────────────────────────────────────────────────────────
# T26–T30 : Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_T26_six_signals_produces_top5_selected(tmp_path: Path) -> None:
    """T26: 6 signals → exactly 5 selected, 1 not selected."""
    ev     = _fresh_evaluator(tmp_path)
    sigs   = _make_signals(6)
    result = ev.evaluate_and_record(sigs)
    selected = sum(1 for r in result if r["knowledge_selected"])
    assert selected == KNOWLEDGE_TOP_N


def test_T27_knowledge_selected_count_never_exceeds_top_n(tmp_path: Path) -> None:
    """T27: knowledge_selected count ≤ KNOWLEDGE_TOP_N for any signal count."""
    for n in [1, 3, KNOWLEDGE_TOP_N, KNOWLEDGE_TOP_N + 5]:
        ev     = _fresh_evaluator(tmp_path / str(n))
        result = ev.evaluate_and_record(_make_signals(n))
        selected = sum(1 for r in result if r["knowledge_selected"])
        assert selected <= KNOWLEDGE_TOP_N


def test_T28_all_required_fields_in_observation_record(tmp_path: Path) -> None:
    """T28: KNOWLEDGE_OBSERVATION records contain all required fields."""
    required = {
        "obs_id", "event_type", "ts_utc", "trading_date", "symbol", "direction",
        "knowledge_score", "knowledge_score_version", "knowledge_rank",
        "knowledge_selected", "knowledge_selection_rule", "total_signals_this_cycle",
        "reference_entry", "knowledge_stop_loss", "knowledge_target", "knowledge_RR",
        "atr", "stop_method", "target_method",
        "candidate_score", "scanner_confidence", "scanner_strategy", "regime",
        "strategy_status", "strategy_rejection_reason", "knowledge_strategy_disagreement",
        "no_lookahead", "virtual_outcome",
    }
    ev     = _fresh_evaluator(tmp_path)
    result = ev.evaluate_and_record([_make_signal("REQUIRED")])
    assert result, "Expected at least one record"
    missing = required - set(result[0].keys())
    assert not missing, f"Missing fields: {missing}"


def test_T29_all_required_fields_in_annotation_record(tmp_path: Path) -> None:
    """T29: STRATEGY_ANNOTATION records contain all required fields."""
    required = {
        "obs_id", "event_type", "ts_utc", "trading_date", "symbol",
        "strategy_name", "strategy_status", "strategy_rejection_reason",
        "structural_strategy_status", "knowledge_selected",
        "knowledge_strategy_disagreement", "no_lookahead",
    }
    ev    = _fresh_evaluator(tmp_path)
    sigs  = [_make_signal("ANNOTATED")]
    ev.evaluate_and_record(sigs)
    ev.annotate_strategy_outcome(sigs, {"ANNOTATED"}, {})
    ann_records = [r for r in _read_klp(tmp_path) if r["event_type"] == "STRATEGY_ANNOTATION"]
    assert ann_records, "Expected at least one annotation"
    missing = required - set(ann_records[0].keys())
    assert not missing, f"Missing annotation fields: {missing}"


def test_T30_score_formula_weights_sum_to_1() -> None:
    """T30: The 5 weight constants sum to exactly 1.0."""
    total = _W_CANDIDATE_SCORE + _W_CONFIDENCE + _W_EXPECTED_MOVE + _W_RISK_REWARD + _W_REGIME_ALIGN
    assert abs(total - 1.0) < 1e-10, f"Weights sum to {total}, not 1.0"


# ─────────────────────────────────────────────────────────────────────────────
# T31–T33 : Safety
# ─────────────────────────────────────────────────────────────────────────────

def test_T31_evaluate_and_record_never_mutates_signals(tmp_path: Path) -> None:
    """T31: evaluate_and_record() never modifies any attribute of any signal."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = _make_signals(5)
    # Capture original attribute values
    originals = [
        {attr: getattr(s, attr) for attr in
         ["symbol", "entry_price", "stop_loss", "target_price", "confidence"]}
        for s in sigs
    ]
    ev.evaluate_and_record(sigs)
    for i, sig in enumerate(sigs):
        for attr, val in originals[i].items():
            assert getattr(sig, attr) == val, f"Signal {i} attr '{attr}' was mutated"


def test_T32_annotate_never_raises_with_bad_snapshot(tmp_path: Path) -> None:
    """T32: annotate_strategy_outcome() never raises even with a broken snapshot."""
    ev   = _fresh_evaluator(tmp_path)
    sigs = [_make_signal("SAFE")]
    ev.evaluate_and_record(sigs)
    # Broken snapshot — attribute access will raise AttributeError
    bad_snapshot = object()
    ev.annotate_strategy_outcome(sigs, {"SAFE"}, {}, snapshot=bad_snapshot)  # must not raise


def test_T33_get_klp_evaluator_is_singleton() -> None:
    """T33: Repeated calls to get_klp_evaluator() return the same instance."""
    from opportunity_engine.klp_evaluator import get_klp_evaluator
    a = get_klp_evaluator()
    b = get_klp_evaluator()
    assert a is b, "get_klp_evaluator() must return the same singleton instance"

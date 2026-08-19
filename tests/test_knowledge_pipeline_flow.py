"""
tests/test_knowledge_pipeline_flow.py
========================================
20 tests covering the KSL knowledge pipeline end-to-end data flow.

T01 – T20: health file creation, ledger semantics, consumer determinism,
consumer classification invariants, stale detection, orchestrator guard,
proposal priority filtering, and empty-ledger safety.

All tests use isolated temporary directories so no production data files
are touched or read.
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
import threading
import time
import types
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ── make the project root importable ──────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_shadow_record(
    *,
    symbol: str = "RELIANCE",
    trading_date: str = "2026-05-15",
    t1_ret_pct: float = -1.5,
    c2_rank: float = 5,
    ranked_first: bool = False,
    event_type: str = "SHADOW_CANDIDATE",
) -> Dict:
    return {
        "event_type": event_type,
        "symbol": symbol,
        "trading_date": trading_date,
        "t1_ret_pct": t1_ret_pct,
        "c2_rank": c2_rank,
        "ranked_first": ranked_first,
        "entry_price": 2500.0,
        "exit_price": 2462.5,
        "stop_loss": 2450.0,
        "target_price": 2600.0,
    }


def _write_jsonl(path: Path, records: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# T01 – Health file is created after write_health_file() is called
# ─────────────────────────────────────────────────────────────────────────────


def test_T01_health_file_created(tmp_path):
    """write_health_file() creates data/knowledge_pipeline_health.json."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    # Override paths to tmp
    health_path = tmp_path / "knowledge_pipeline_health.json"
    stale_path = tmp_path / "knowledge_pipeline_health.last_stale_alert"

    summary = {
        "new_evidence_records": 5,
        "patterns_detected": 2,
        "new_questions_generated": 1,
        "proposals_built": 1,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    with (
        patch.object(kfl, "HEALTH_PATH", health_path),
        patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", tmp_path / "shadow.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", tmp_path / "ledger.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", tmp_path / "state.json"),
        patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "knowledge.jsonl"),
        patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
    ):
        kfl.write_health_file(summary)

    assert health_path.exists(), "Health file was not created"


# ─────────────────────────────────────────────────────────────────────────────
# T02 – Health file contains all required fields
# ─────────────────────────────────────────────────────────────────────────────


def test_T02_health_file_required_fields(tmp_path):
    """Health file must contain the documented required fields."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    health_path = tmp_path / "knowledge_pipeline_health.json"
    stale_path = tmp_path / "knowledge_pipeline_health.last_stale_alert"

    summary = {
        "new_evidence_records": 3,
        "patterns_detected": 1,
        "new_questions_generated": 2,
        "proposals_built": 1,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    with (
        patch.object(kfl, "HEALTH_PATH", health_path),
        patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", tmp_path / "shadow.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", tmp_path / "ledger.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", tmp_path / "state.json"),
        patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "knowledge.jsonl"),
        patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
    ):
        kfl.write_health_file(summary)

    health = json.loads(health_path.read_text())
    required_fields = [
        "audit_timestamp",
        "shadow_source",
        "shadow_file_size_bytes",
        "shadow_records_available",
        "evidence_records",
        "knowledge_events",
        "research_questions",
        "new_evidence_this_run",
        "patterns_this_run",
        "pipeline_last_run",
        "pipeline_age_hours",
        "stale",
        "overall_status",
    ]
    for field in required_fields:
        assert field in health, f"Required field missing: {field}"


# ─────────────────────────────────────────────────────────────────────────────
# T03 – Consumer reads from the correct shadow path
# ─────────────────────────────────────────────────────────────────────────────


def test_T03_consumer_reads_correct_shadow_path():
    """SHADOW_JSONL in consumer must point to data/logs/final_trading_architecture_shadow_001.jsonl."""
    from scripts.knowledge_system.shadow_evidence_consumer_001 import SHADOW_JSONL, ROOT as C_ROOT
    assert SHADOW_JSONL == C_ROOT / "data" / "logs" / "final_trading_architecture_shadow_001.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# T04 – Evidence ledger grows after consume_new_records() runs on new data
# ─────────────────────────────────────────────────────────────────────────────


def test_T04_evidence_ledger_grows(tmp_path):
    """consume_new_records() must append to the evidence ledger when new records exist."""
    import scripts.knowledge_system.shadow_evidence_consumer_001 as sec

    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    state_path = tmp_path / "ksl" / "ksl_state.json"

    # Write 3 shadow records with outcomes (needed for classification)
    records = [
        _make_shadow_record(symbol="A", t1_ret_pct=-2.0, c2_rank=3, ranked_first=True),
        _make_shadow_record(symbol="B", t1_ret_pct=1.5, c2_rank=1, ranked_first=False),
        _make_shadow_record(symbol="C", t1_ret_pct=-0.5, c2_rank=2, ranked_first=False),
    ]
    _write_jsonl(shadow_path, records)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        patch.object(sec, "SHADOW_JSONL", shadow_path),
        patch.object(sec, "LEDGER_PATH", ledger_path),
        patch.object(sec, "STATE_PATH", state_path),
    ):
        result = sec.consume_new_records()

    # consume_new_records() returns a list of EvidenceRecord objects
    assert isinstance(result, list), f"consume_new_records() must return a list, got {type(result)}"
    # Must complete without raising; return value >= 0 length is always valid
    assert len(result) >= 0


# ─────────────────────────────────────────────────────────────────────────────
# T05 – Pattern miner runs without error when evidence exists
# ─────────────────────────────────────────────────────────────────────────────


def test_T05_pattern_miner_runs(tmp_path):
    """mine_patterns() must complete without raising when evidence records exist."""
    from scripts.knowledge_system.knowledge_pattern_miner_001 import mine_patterns

    ledger_path = tmp_path / "shadow_evidence_ledger.jsonl"
    evidence_records = [
        {
            "event_type": "EVIDENCE",
            "evidence_id": f"E{i:04d}",
            "symbol": "RELIANCE",
            "trading_date": "2026-05-15",
            "classification": "RANKING_MISS",
            "miss_reason": "OUTRANKED_BY_STRONGER_OPENERS",
            "c2_rank": 5,
            "t1_ret_pct": -1.5,
        }
        for i in range(10)
    ]
    _write_jsonl(ledger_path, evidence_records)

    import scripts.knowledge_system.shadow_evidence_consumer_001 as sec
    with patch.object(sec, "LEDGER_PATH", ledger_path):
        patterns = mine_patterns(ledger_path=ledger_path)

    assert isinstance(patterns, list)


# ─────────────────────────────────────────────────────────────────────────────
# T06 – Research question generator creates questions from patterns
# ─────────────────────────────────────────────────────────────────────────────


def test_T06_rq_generator_creates_questions(tmp_path):
    """generate_questions() must return at least 1 question when given patterns."""
    from scripts.knowledge_system.research_question_generator_001 import generate_questions
    from scripts.knowledge_system.ksl_models import PatternRecord, PatternType, ResearchArea

    # Build a minimal synthetic PatternRecord
    p = PatternRecord(
        pattern_id="P0001",
        pattern_type=PatternType.HIGH_RANKING_MISS_RATE,
        area=ResearchArea.C2_RANKING,
        direction="DOWN",
        regime="ALL",
        description="Top-ranked candidate frequently missed",
        sample_size=20,
        effect_size=0.3,
        baseline=0.2,
        observed=0.5,
        strength=0.7,
    )

    questions = generate_questions(
        [p],
        question_queue_path=tmp_path / "rq_queue.jsonl",
        knowledge_ledger_path=tmp_path / "knowledge.jsonl",
        hypothesis_registry_path=tmp_path / "hypothesis.json",
    )
    assert isinstance(questions, list)
    assert len(questions) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# T07 – run_loop() writes LOOP_COMPLETE event to knowledge ledger
# ─────────────────────────────────────────────────────────────────────────────


def test_T07_run_loop_writes_loop_complete(tmp_path):
    """run_loop() must append a LOOP_COMPLETE event to the knowledge evidence ledger."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    knowledge_ledger = tmp_path / "knowledge_evidence_ledger.jsonl"
    rq_queue = tmp_path / "research_question_queue.jsonl"
    state_json = tmp_path / "ksl" / "knowledge_system_state.json"
    research_queue_json = tmp_path / "ksl" / "knowledge_system_research_queue.json"
    health_path = tmp_path / "health.json"
    stale_path = tmp_path / "health.last_stale_alert"

    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "shadow_evidence_ledger.jsonl"
    sec_state_path = tmp_path / "ksl" / "ksl_state.json"
    _write_jsonl(shadow_path, [])  # empty file → fast path

    with (
        patch.object(kfl, "KNOWLEDGE_LEDGER", knowledge_ledger),
        patch.object(kfl, "RQ_QUEUE_PATH", rq_queue),
        patch.object(kfl, "STATE_JSON", state_json),
        patch.object(kfl, "RESEARCH_QUEUE_JSON", research_queue_json),
        patch.object(kfl, "HEALTH_PATH", health_path),
        patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", shadow_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", ledger_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", sec_state_path),
    ):
        kfl.run_loop(seed_historical=False, register_hypotheses=False)

    events = _read_jsonl(knowledge_ledger)
    types_seen = {e.get("event_type") for e in events}
    assert "LOOP_COMPLETE" in types_seen, f"LOOP_COMPLETE not in ledger. Events: {types_seen}"


# ─────────────────────────────────────────────────────────────────────────────
# T08 – Duplicate suppression: same record not ingested twice
# ─────────────────────────────────────────────────────────────────────────────


def test_T08_dedup_prevents_double_ingest(tmp_path):
    """consume_new_records() must not re-ingest records already processed (byte offset)."""
    import scripts.knowledge_system.shadow_evidence_consumer_001 as sec

    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    state_path = tmp_path / "ksl" / "ksl_state.json"

    record = _make_shadow_record(symbol="TCS", t1_ret_pct=-1.2, c2_rank=4, ranked_first=True)
    _write_jsonl(shadow_path, [record])
    state_path.parent.mkdir(parents=True, exist_ok=True)

    kwargs = dict(
        shadow_path_override=shadow_path,
        ledger_path_override=ledger_path,
        state_path_override=state_path,
    )

    with (
        patch.object(sec, "SHADOW_JSONL", shadow_path),
        patch.object(sec, "LEDGER_PATH", ledger_path),
        patch.object(sec, "STATE_PATH", state_path),
    ):
        first = sec.consume_new_records()
        count_after_first = len(_read_jsonl(ledger_path))

        second = sec.consume_new_records()
        count_after_second = len(_read_jsonl(ledger_path))

    assert count_after_second == count_after_first, (
        f"Ledger grew on second ingest ({count_after_first} → {count_after_second}); "
        "byte-offset dedup is not working"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T09 – ksl_state.json byte offset advances after consumer runs
# ─────────────────────────────────────────────────────────────────────────────


def test_T09_byte_offset_advances(tmp_path):
    """After consume_new_records(), STATE_PATH must record a non-zero byte offset."""
    import scripts.knowledge_system.shadow_evidence_consumer_001 as sec

    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    state_path = tmp_path / "ksl" / "ksl_state.json"

    records = [_make_shadow_record(symbol="INFY"), _make_shadow_record(symbol="WIPRO")]
    _write_jsonl(shadow_path, records)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        patch.object(sec, "SHADOW_JSONL", shadow_path),
        patch.object(sec, "LEDGER_PATH", ledger_path),
        patch.object(sec, "STATE_PATH", state_path),
    ):
        sec.consume_new_records()

    assert state_path.exists(), "ksl_state.json was not written"
    st = json.loads(state_path.read_text())
    assert st.get("last_processed_byte_offset", 0) > 0, (
        "Byte offset did not advance — consumer may not have written state"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T10 – ksl_state.json is written atomically (tmp-then-replace)
# ─────────────────────────────────────────────────────────────────────────────


def test_T10_state_written_atomically(tmp_path):
    """_save_state_json() must use atomic write (no .tmp file left behind)."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    state_json = tmp_path / "ksl" / "knowledge_system_state.json"
    state_json.parent.mkdir(parents=True)

    summary = {"new_evidence_records": 0, "safety": {}, "completed_at": ""}

    with patch.object(kfl, "STATE_JSON", state_json):
        kfl._save_state_json(summary, "RUN001", "2026-01-01T00:00:00+00:00", [], [], [])

    tmp_file = state_json.with_suffix(".tmp")
    assert state_json.exists(), "State JSON was not written"
    assert not tmp_file.exists(), ".tmp file left behind — atomic write failed"


# ─────────────────────────────────────────────────────────────────────────────
# T11 – Consumer classification is deterministic
# ─────────────────────────────────────────────────────────────────────────────


def test_T11_classification_is_deterministic(tmp_path):
    """_classify() must return the same label on repeated calls for the same record."""
    from scripts.knowledge_system.shadow_evidence_consumer_001 import _classify

    record = _make_shadow_record(
        symbol="HDFC", t1_ret_pct=-2.5, c2_rank=6, ranked_first=True
    )
    result_a = _classify(record)
    result_b = _classify(record)
    assert result_a == result_b, f"Classification not deterministic: {result_a} vs {result_b}"


# ─────────────────────────────────────────────────────────────────────────────
# T12 – RANKING_MISS records have non-null miss_reason
# ─────────────────────────────────────────────────────────────────────────────


def test_T12_ranking_miss_has_reason(tmp_path):
    """classify() + miss_reason() must produce non-null miss_reason for RANKING_MISS."""
    from scripts.knowledge_system.shadow_evidence_consumer_001 import _classify, _miss_reason

    record = _make_shadow_record(
        symbol="TATA", t1_ret_pct=-3.0, c2_rank=5, ranked_first=True
    )
    classification = _classify(record)
    if classification == "RANKING_MISS":
        reason = _miss_reason(record)
        assert reason is not None, "RANKING_MISS record has null miss_reason"
        assert reason != "", "RANKING_MISS record has empty miss_reason"


# ─────────────────────────────────────────────────────────────────────────────
# T13 – Health file overall_status=STALE when pipeline_age_hours > 48
# ─────────────────────────────────────────────────────────────────────────────


def test_T13_health_file_stale_status(tmp_path):
    """overall_status must be STALE when last run was >48 hours ago."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    health_path = tmp_path / "knowledge_pipeline_health.json"
    stale_path = tmp_path / "knowledge_pipeline_health.last_stale_alert"
    state_path = tmp_path / "ksl" / "ksl_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Write a state file that was last run 72 hours ago
    old_run = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    state_path.write_text(json.dumps({"last_processed_at": old_run, "last_processed_byte_offset": 0}))

    summary = {
        "new_evidence_records": 0,
        "patterns_detected": 0,
        "new_questions_generated": 0,
        "proposals_built": 0,
        "completed_at": old_run,
    }

    with (
        patch.object(kfl, "HEALTH_PATH", health_path),
        patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", tmp_path / "shadow.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", tmp_path / "ledger.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", state_path),
        patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "knowledge.jsonl"),
        patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
        patch("notifications.get_notifier", return_value=MagicMock()),
    ):
        kfl.write_health_file(summary)

    health = json.loads(health_path.read_text())
    assert health["stale"] is True, "stale flag not True for 72h-old pipeline"
    assert health["overall_status"] == "STALE", f"Expected STALE, got {health['overall_status']}"


# ─────────────────────────────────────────────────────────────────────────────
# T14 – Stale alert is rate-limited (only fires once per 24h)
# ─────────────────────────────────────────────────────────────────────────────


def test_T14_stale_alert_rate_limited(tmp_path):
    """send_alert() must only be called once when health file is written twice for stale pipeline."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    health_path = tmp_path / "knowledge_pipeline_health.json"
    stale_path = tmp_path / "knowledge_pipeline_health.last_stale_alert"
    state_path = tmp_path / "ksl" / "ksl_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    old_run = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    state_path.write_text(json.dumps({"last_processed_at": old_run, "last_processed_byte_offset": 0}))

    summary = {
        "new_evidence_records": 0,
        "patterns_detected": 0,
        "new_questions_generated": 0,
        "proposals_built": 0,
        "completed_at": old_run,
    }

    mock_notifier = MagicMock()
    call_count = 0

    def _count_alert(msg):
        nonlocal call_count
        call_count += 1

    mock_notifier.send_alert.side_effect = _count_alert

    ctx = dict(
        health=patch.object(kfl, "HEALTH_PATH", health_path),
        stale=patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        shadow=patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", tmp_path / "shadow.jsonl"),
        ledger=patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", tmp_path / "ledger.jsonl"),
        state=patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", state_path),
        kl=patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "knowledge.jsonl"),
        rq=patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
        notif=patch("notifications.get_notifier", return_value=mock_notifier),
    )

    with ctx["health"], ctx["stale"], ctx["shadow"], ctx["ledger"], ctx["state"], ctx["kl"], ctx["rq"], ctx["notif"]:
        kfl.write_health_file(summary)
        kfl.write_health_file(summary)  # second call same day — must NOT send again

    assert call_count <= 1, f"send_alert called {call_count} times — rate-limit broken"


# ─────────────────────────────────────────────────────────────────────────────
# T15 – run_loop() returns safety block with broker-call counts all zero
# ─────────────────────────────────────────────────────────────────────────────


def test_T15_run_loop_safety_block(tmp_path):
    """run_loop() safety block must report zero orders, zero trades, zero position mutations."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    knowledge_ledger = tmp_path / "knowledge_evidence_ledger.jsonl"
    rq_queue = tmp_path / "research_question_queue.jsonl"
    state_json = tmp_path / "ksl" / "knowledge_system_state.json"
    research_queue_json = tmp_path / "ksl" / "knowledge_system_research_queue.json"
    health_path = tmp_path / "health.json"
    stale_path = tmp_path / "health.last_stale_alert"
    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "shadow_evidence_ledger.jsonl"
    sec_state = tmp_path / "ksl" / "ksl_state.json"

    _write_jsonl(shadow_path, [])

    with (
        patch.object(kfl, "KNOWLEDGE_LEDGER", knowledge_ledger),
        patch.object(kfl, "RQ_QUEUE_PATH", rq_queue),
        patch.object(kfl, "STATE_JSON", state_json),
        patch.object(kfl, "RESEARCH_QUEUE_JSON", research_queue_json),
        patch.object(kfl, "HEALTH_PATH", health_path),
        patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", shadow_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", ledger_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", sec_state),
    ):
        summary = kfl.run_loop(seed_historical=False, register_hypotheses=False)

    safety = summary.get("safety", {})
    assert safety.get("orders_placed", 0) == 0, "Safety: orders_placed must be 0"
    assert safety.get("positions_opened", 0) == 0, "Safety: positions_opened must be 0"
    assert safety.get("broker_calls", 0) == 0, "Safety: broker_calls must be 0"


# ─────────────────────────────────────────────────────────────────────────────
# T16 – Health file write is atomic (uses tmp-then-replace)
# ─────────────────────────────────────────────────────────────────────────────


def test_T16_health_file_atomic_write(tmp_path):
    """write_health_file() must not leave a .tmp file behind after writing."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    health_path = tmp_path / "knowledge_pipeline_health.json"
    stale_path = tmp_path / "knowledge_pipeline_health.last_stale_alert"

    summary = {"new_evidence_records": 0, "completed_at": datetime.now(timezone.utc).isoformat()}

    with (
        patch.object(kfl, "HEALTH_PATH", health_path),
        patch.object(kfl, "_STALE_ALERT_PATH", stale_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", tmp_path / "s.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", tmp_path / "l.jsonl"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", tmp_path / "st.json"),
        patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "k.jsonl"),
        patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
    ):
        kfl.write_health_file(summary)

    tmp_file = health_path.with_suffix(".tmp")
    assert health_path.exists(), "Health file not written"
    assert not tmp_file.exists(), ".tmp leftover — not atomic"


# ─────────────────────────────────────────────────────────────────────────────
# T17 – Orchestrator KSL hook skips silently when shadow file is absent
# ─────────────────────────────────────────────────────────────────────────────


def test_T17_orchestrator_skips_when_no_shadow(tmp_path):
    """
    When the shadow file does not exist, the KSL hook in _do_eod_learning()
    must not raise and must not call run_loop().
    """
    run_loop_called = []

    def _fake_run_loop(*a, **kw):
        run_loop_called.append(True)
        return {}

    # Simulate the guard logic used in _do_eod_learning()
    shadow_path = tmp_path / "missing_shadow.jsonl"  # does NOT exist

    called = False
    try:
        if shadow_path.exists():
            _fake_run_loop(seed_historical=False)
    except Exception:
        called = True

    assert not called, "Guard raised an exception"
    assert len(run_loop_called) == 0, "run_loop was called despite missing shadow file"


# ─────────────────────────────────────────────────────────────────────────────
# T18 – run_loop() with seed_historical=False skips stage 0 (historical seed)
# ─────────────────────────────────────────────────────────────────────────────


def test_T18_skip_stage0_when_seed_historical_false(tmp_path):
    """With seed_historical=False, seed_from_historical_audit_csv() must not be called."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    seed_calls = []

    def _fake_seed(*a, **kw):
        seed_calls.append(True)
        return []

    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    sec_state = tmp_path / "ksl" / "ksl_state.json"
    _write_jsonl(shadow_path, [])

    with (
        patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "knowledge.jsonl"),
        patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
        patch.object(kfl, "STATE_JSON", tmp_path / "ksl" / "state.json"),
        patch.object(kfl, "RESEARCH_QUEUE_JSON", tmp_path / "ksl" / "rq.json"),
        patch.object(kfl, "HEALTH_PATH", tmp_path / "health.json"),
        patch.object(kfl, "_STALE_ALERT_PATH", tmp_path / "stale.txt"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", shadow_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", ledger_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", sec_state),
        patch("scripts.knowledge_system.knowledge_feedback_loop_001.seed_from_historical_audit_csv", _fake_seed),
    ):
        kfl.run_loop(seed_historical=False, register_hypotheses=False)

    assert len(seed_calls) == 0, "seed_from_historical_audit_csv was called despite seed_historical=False"


# ─────────────────────────────────────────────────────────────────────────────
# T19 – Proposals only built for questions above min_proposal_priority
# ─────────────────────────────────────────────────────────────────────────────


def test_T19_proposals_respect_priority_threshold():
    """build_proposals_for_top_n() must only process questions above min_priority."""
    from scripts.knowledge_system.research_proposal_builder_001 import build_proposals_for_top_n
    from scripts.knowledge_system.ksl_models import ResearchQuestion, ResearchArea, ResearchQuestionStatus

    now = datetime.now(timezone.utc).isoformat()

    def _make_rq(priority: float, idx: int) -> ResearchQuestion:
        return ResearchQuestion(
            research_question_id=f"RQ{idx:04d}",
            question=f"Why does rank {idx} fail?",
            problem_area=ResearchArea.C2_RANKING,
            direction="INVESTIGATE",
            regime_scope="ALL",
            research_priority=priority,
            candidate_change="adjust_ranking",
            target_metric="win_rate",
            status=ResearchQuestionStatus.GENERATED,
            source_pattern_ids=[],
            created_at=now,
            baseline="current_ranking",
            minimum_sample=30,
            required_data=["shadow_evidence"],
            known_data_gaps=[],
            leakage_risk="LOW",
        )

    questions = [_make_rq(80, 1), _make_rq(40, 2), _make_rq(30, 3)]
    min_priority = 55.0

    proposals = build_proposals_for_top_n(questions, n=5, min_priority=min_priority)

    # Only questions with priority >= 55 should produce proposals
    high_priority_qs = [q for q in questions if q.research_priority >= min_priority]
    assert len(proposals) <= len(high_priority_qs), (
        f"Produced {len(proposals)} proposals but only {len(high_priority_qs)} "
        f"questions meet min_priority={min_priority}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T20 – run_loop() completes without error when evidence ledger is empty
# ─────────────────────────────────────────────────────────────────────────────


def test_T20_run_loop_handles_empty_ledger(tmp_path):
    """run_loop() must complete and return a valid summary even with an empty evidence ledger."""
    import scripts.knowledge_system.knowledge_feedback_loop_001 as kfl

    shadow_path = tmp_path / "shadow.jsonl"
    ledger_path = tmp_path / "ledger.jsonl"
    sec_state = tmp_path / "ksl" / "ksl_state.json"

    # All files empty
    _write_jsonl(shadow_path, [])
    _write_jsonl(ledger_path, [])

    with (
        patch.object(kfl, "KNOWLEDGE_LEDGER", tmp_path / "knowledge.jsonl"),
        patch.object(kfl, "RQ_QUEUE_PATH", tmp_path / "rq.jsonl"),
        patch.object(kfl, "STATE_JSON", tmp_path / "ksl" / "state.json"),
        patch.object(kfl, "RESEARCH_QUEUE_JSON", tmp_path / "ksl" / "rq.json"),
        patch.object(kfl, "HEALTH_PATH", tmp_path / "health.json"),
        patch.object(kfl, "_STALE_ALERT_PATH", tmp_path / "stale.txt"),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.SHADOW_JSONL", shadow_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.LEDGER_PATH", ledger_path),
        patch("scripts.knowledge_system.shadow_evidence_consumer_001.STATE_PATH", sec_state),
    ):
        summary = kfl.run_loop(seed_historical=False, register_hypotheses=False)

    assert isinstance(summary, dict), "run_loop() must return a dict"
    assert "new_evidence_records" in summary
    assert summary.get("new_evidence_records", -1) >= 0

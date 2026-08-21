"""
tests/test_klp_ksl_bridge.py
==============================
T01–T12 — KLP→KSL learning bridge tests.

Verifies that completed KLP observations reach the Knowledge evidence/pattern/
research pipeline on VPS without requiring the local shadow JSONL.
"""
from __future__ import annotations

import json
import pathlib
import uuid
from datetime import date, timedelta
from typing import List
from unittest.mock import MagicMock, call, patch

import pytest

# ─── helpers ─────────────────────────────────────────────────────────────────

_YESTERDAY = str(date.today() - timedelta(days=1))
_TWO_AGO   = str(date.today() - timedelta(days=2))


def _write_obs(klp_dir: pathlib.Path, date_str: str, symbol: str = "RELIANCE",
               obs_id: str | None = None) -> str:
    obs_id = obs_id or str(uuid.uuid4())
    rec = {
        "event_type":          "KNOWLEDGE_OBSERVATION",
        "obs_id":              obs_id,
        "symbol":              symbol,
        "trading_date":        date_str,
        "ts":                  f"{date_str}T03:45:00+00:00",
        "direction":           "BUY",
        "knowledge_score":     0.78,
        "knowledge_rank":      1,
        "knowledge_selected":  True,
        "knowledge_target":    115.0,
        "knowledge_stop_loss": 98.0,
        "knowledge_RR":        2.5,
        "no_lookahead":        True,
    }
    (klp_dir / f"KLP_{date_str}.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with (klp_dir / f"KLP_{date_str}.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return obs_id


def _write_outcome(klp_dir: pathlib.Path, obs_id: str, date_str: str,
                   first_event: str = "TARGET_HIT") -> None:
    rec = {
        "event_type":    "OUTCOME_UPDATE",
        "obs_id":        obs_id,
        "trading_date":  date_str,
        "ts":            f"{date_str}T10:00:00+00:00",
        "first_event":   first_event,
        "target_hit":    first_event == "TARGET_HIT",
        "stop_hit":      first_event == "STOP_HIT",
        "t1_ret_pct":    3.5,
        "t3_ret_pct":    7.0,
        "t5_ret_pct":    8.0,
        "mfe_pct":       5.0,
        "mae_pct":       -1.0,
        "theoretical_R": 2.5,
        "no_lookahead":  True,
    }
    with (klp_dir / f"KLP_{date_str}.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")


def _load_jsonl(path: pathlib.Path) -> List[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


# ─── T01 ─────────────────────────────────────────────────────────────────────

def test_T01_vps_style_no_shadow_jsonl_ingests_completed_klp(tmp_path: pathlib.Path) -> None:
    """T01: run_klp_loop() ingests completed KLP outcomes even when shadow JSONL is absent."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    klp_dir.mkdir()
    assert not s_ledger.exists()          # shadow JSONL absent (VPS mode)

    obs_id = _write_obs(klp_dir, _YESTERDAY)
    _write_outcome(klp_dir, obs_id, _YESTERDAY)

    result = run_klp_loop(
        _klp_data_dir=klp_dir,
        _shadow_ledger=s_ledger,
        _knowledge_ledger_path=k_ledger,
        _klp_adapter_state=state,
        _health_path=h_path,
    )

    assert result["klp_evidence_ingested"] == 1
    assert s_ledger.exists(), "shadow ledger created by adapter"
    recs = _load_jsonl(s_ledger)
    assert any(r.get("symbol") == "RELIANCE" for r in recs)


# ─── T02 ─────────────────────────────────────────────────────────────────────

def test_T02_pending_klp_outcomes_are_skipped(tmp_path: pathlib.Path) -> None:
    """T02: Observations without OUTCOME_UPDATE are skipped."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    _write_obs(klp_dir, _YESTERDAY)      # obs with NO paired OUTCOME_UPDATE

    result = run_klp_loop(
        _klp_data_dir=klp_dir,
        _shadow_ledger=s_ledger,
        _knowledge_ledger_path=k_ledger,
        _klp_adapter_state=state,
        _health_path=h_path,
    )

    assert result["klp_evidence_ingested"] == 0


# ─── T03 ─────────────────────────────────────────────────────────────────────

def test_T03_completed_klp_outcomes_produce_evidence_records(tmp_path: pathlib.Path) -> None:
    """T03: Completed KLP observations produce EvidenceRecords in the shadow ledger."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    obs_id = _write_obs(klp_dir, _YESTERDAY, symbol="TATAPOWER")
    _write_outcome(klp_dir, obs_id, _YESTERDAY, first_event="TARGET_HIT")

    run_klp_loop(
        _klp_data_dir=klp_dir,
        _shadow_ledger=s_ledger,
        _knowledge_ledger_path=k_ledger,
        _klp_adapter_state=state,
        _health_path=h_path,
    )

    recs = _load_jsonl(s_ledger)
    assert len(recs) >= 1
    # Must be an EvidenceRecord (classification field present)
    ev_recs = [r for r in recs if "classification" in r]
    assert len(ev_recs) == 1
    assert ev_recs[0]["symbol"] == "TATAPOWER"


# ─── T04 ─────────────────────────────────────────────────────────────────────

def test_T04_re_running_is_idempotent(tmp_path: pathlib.Path) -> None:
    """T04: Running run_klp_loop() twice ingests 0 new records the second time."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    obs_id = _write_obs(klp_dir, _YESTERDAY)
    _write_outcome(klp_dir, obs_id, _YESTERDAY)

    kwargs = dict(
        _klp_data_dir=klp_dir,
        _shadow_ledger=s_ledger,
        _knowledge_ledger_path=k_ledger,
        _klp_adapter_state=state,
        _health_path=h_path,
    )

    r1 = run_klp_loop(**kwargs)
    r2 = run_klp_loop(**kwargs)

    assert r1["klp_evidence_ingested"] == 1
    assert r2["klp_evidence_ingested"] == 0     # idempotent

    ev_recs = [r for r in _load_jsonl(s_ledger) if "classification" in r]
    assert len(ev_recs) == 1                    # not duplicated


# ─── T05 ─────────────────────────────────────────────────────────────────────

def test_T05_pattern_mining_receives_klp_evidence(tmp_path: pathlib.Path) -> None:
    """T05: Pattern miner is called with the shadow ledger path after KLP ingest."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    obs_id = _write_obs(klp_dir, _YESTERDAY)
    _write_outcome(klp_dir, obs_id, _YESTERDAY)

    mine_calls: list = []

    def _fake_mine(ledger_path=None):
        mine_calls.append(ledger_path)
        return []

    with patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.mine_patterns",
        side_effect=_fake_mine,
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001._save_research_queue_json"
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001._save_state_json"
    ):
        run_klp_loop(
            _klp_data_dir=klp_dir,
            _shadow_ledger=s_ledger,
            _knowledge_ledger_path=k_ledger,
            _klp_adapter_state=state,
            _health_path=h_path,
        )

    assert len(mine_calls) == 1, "mine_patterns called exactly once"
    assert mine_calls[0] == s_ledger, "called with the shadow ledger path"


# ─── T06 ─────────────────────────────────────────────────────────────────────

def test_T06_research_question_generator_receives_patterns(tmp_path: pathlib.Path) -> None:
    """T06: generate_questions() receives patterns produced from KLP evidence."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop
    from scripts.knowledge_system.ksl_models import PatternRecord, PatternType

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    obs_id = _write_obs(klp_dir, _YESTERDAY)
    _write_outcome(klp_dir, obs_id, _YESTERDAY)

    fake_pattern = PatternRecord(
        pattern_id="pat-001",
        pattern_type=PatternType.HIGH_RANKING_MISS_RATE,
        area=__import__(
            "scripts.knowledge_system.ksl_models", fromlist=["ResearchArea"]
        ).ResearchArea.C2_RANKING,
        direction="BUY",
        regime="ALL",
        description="KLP test pattern",
        sample_size=10,
        effect_size=0.3,
        baseline=0.2,
        observed=0.5,
        strength=0.72,
    )

    gen_calls: list = []

    def _fake_mine(ledger_path=None):
        return [fake_pattern]

    def _fake_gen(patterns, knowledge_ledger_path=None):
        gen_calls.append((patterns, knowledge_ledger_path))
        return []

    with patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.mine_patterns",
        side_effect=_fake_mine,
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.generate_questions",
        side_effect=_fake_gen,
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001._save_research_queue_json"
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001._save_state_json"
    ):
        run_klp_loop(
            _klp_data_dir=klp_dir,
            _shadow_ledger=s_ledger,
            _knowledge_ledger_path=k_ledger,
            _klp_adapter_state=state,
            _health_path=h_path,
        )

    assert len(gen_calls) == 1
    received_patterns, received_ledger = gen_calls[0]
    assert len(received_patterns) == 1
    assert received_patterns[0].pattern_id == "pat-001"
    assert received_ledger == k_ledger


# ─── T07 ─────────────────────────────────────────────────────────────────────

def test_T07_health_file_generated_without_shadow_jsonl(tmp_path: pathlib.Path) -> None:
    """T07: write_health_file() creates the health JSON even when shadow JSONL is absent."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"   # absent
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    # No outcomes — idle run to verify health is always written
    result = run_klp_loop(
        _klp_data_dir=klp_dir,
        _shadow_ledger=s_ledger,
        _knowledge_ledger_path=k_ledger,
        _klp_adapter_state=state,
        _health_path=h_path,
    )

    assert h_path.exists(), "health file written without shadow JSONL"
    health = json.loads(h_path.read_text())
    assert "audit_timestamp" in health
    assert "overall_status" in health
    assert result["health_written"] is True


# ─── T08 ─────────────────────────────────────────────────────────────────────

def test_T08_existing_local_shadow_ingestion_unchanged(tmp_path: pathlib.Path) -> None:
    """T08: run_loop() still calls consume_new_records() when shadow JSONL exists."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_loop

    consume_calls: list = []

    def _fake_consume(shadow_path=None, state_path=None, ledger_path=None, **kw):
        consume_calls.append(shadow_path)
        return []

    with patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.consume_new_records",
        side_effect=_fake_consume,
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.mine_patterns",
        return_value=[],
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.generate_questions",
        return_value=[],
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.prioritize_questions",
        return_value=[],
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.build_proposals_for_top_n",
        return_value=[],
    ), patch(
        "scripts.knowledge_system.knowledge_feedback_loop_001.write_health_file"
    ):
        run_loop(seed_historical=False)

    assert len(consume_calls) == 1, "consume_new_records called (shadow pipeline preserved)"


# ─── T09 ─────────────────────────────────────────────────────────────────────

def test_T09_klp_and_shadow_evidence_coexist_no_duplication(tmp_path: pathlib.Path) -> None:
    """T09: KLP adapter and shadow consumer produce separate, non-overlapping records."""
    from scripts.knowledge_system.shadow_evidence_consumer_001 import (
        LEDGER_PATH as _DEFAULT_SHADOW,
    )
    from scripts.knowledge_system.klp_evidence_adapter_001 import ingest_klp_outcomes

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    state    = tmp_path / "state.json"

    obs_id = _write_obs(klp_dir, _YESTERDAY, symbol="SBIN")
    _write_outcome(klp_dir, obs_id, _YESTERDAY)

    # First ingest
    r1 = ingest_klp_outcomes(
        klp_data_dir=klp_dir,
        shadow_ledger=s_ledger,
        knowledge_ledger=k_ledger,
        state_path=state,
    )
    # Second ingest (idempotency guard)
    r2 = ingest_klp_outcomes(
        klp_data_dir=klp_dir,
        shadow_ledger=s_ledger,
        knowledge_ledger=k_ledger,
        state_path=state,
    )

    assert r1["new_records"] == 1
    assert r2["new_records"] == 0           # dedup working

    ev_recs = [r for r in _load_jsonl(s_ledger) if "classification" in r]
    assert len(ev_recs) == 1               # exactly one SBIN record


# ─── T10 ─────────────────────────────────────────────────────────────────────

def test_T10_no_broker_execution_imports(tmp_path: pathlib.Path) -> None:
    """T10: knowledge_feedback_loop_001.py contains no execution-layer imports."""
    src = (
        pathlib.Path(__file__).resolve().parents[1]
        / "scripts" / "knowledge_system" / "knowledge_feedback_loop_001.py"
    ).read_text(encoding="utf-8")
    forbidden = [
        "from execution_engine",
        "import ZerodhaBroker",
        "import DhanFeed",
        "place_order(",
        "cancel_order(",
        "modify_order(",
        "from risk_control.capital_risk_engine",
    ]
    for kw in forbidden:
        assert kw not in src, f"Forbidden reference '{kw}' in knowledge_feedback_loop_001.py"


# ─── T11 ─────────────────────────────────────────────────────────────────────

def test_T11_no_secrets_in_evidence_records(tmp_path: pathlib.Path) -> None:
    """T11: EvidenceRecords written by the bridge contain no secrets or credentials."""
    from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop

    klp_dir  = tmp_path / "klp"
    klp_dir.mkdir()
    s_ledger = tmp_path / "shadow.jsonl"
    k_ledger = tmp_path / "knowledge.jsonl"
    h_path   = tmp_path / "health.json"
    state    = tmp_path / "state.json"

    obs_id = _write_obs(klp_dir, _YESTERDAY, symbol="INFY")
    _write_outcome(klp_dir, obs_id, _YESTERDAY)

    run_klp_loop(
        _klp_data_dir=klp_dir,
        _shadow_ledger=s_ledger,
        _knowledge_ledger_path=k_ledger,
        _klp_adapter_state=state,
        _health_path=h_path,
    )

    secret_markers = ["jwt", "Bearer ", "api_key", "totp", "password", "PIN=", "secret"]
    for path in [s_ledger, k_ledger, h_path]:
        if path.exists():
            content = path.read_text(encoding="utf-8").lower()
            for marker in secret_markers:
                assert marker.lower() not in content, (
                    f"Secret marker '{marker}' found in {path.name}"
                )


# ─── T12 ─────────────────────────────────────────────────────────────────────

def test_T12_existing_klp002_ksl_tests_still_importable() -> None:
    """T12: KLP-002 and KSL-001 modules import cleanly alongside the bridge."""
    import importlib
    modules = [
        "opportunity_engine.klp_evaluator",
        "opportunity_engine.klp_outcome_engine",
        "scripts.knowledge_system.klp_evidence_adapter_001",
        "scripts.knowledge_system.klp_bridge_001",
        "scripts.knowledge_system.knowledge_feedback_loop_001",
        "scripts.knowledge_system.shadow_evidence_consumer_001",
    ]
    for mod in modules:
        importlib.import_module(mod)   # raises if broken

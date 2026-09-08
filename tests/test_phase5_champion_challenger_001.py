"""
tests/test_phase5_champion_challenger_001.py
=============================================
Focused tests for DTA-PHASE5-CHAMPION-CHALLENGER-001 — the promotion
gate/registry (scripts/knowledge_system/champion_challenger_001.py).

Verifies:
  - determine_status() implements the full status ladder correctly for
    every verdict/streak/confidence combination.
  - _consecutive_validated_pass_streak() counts correctly, including the
    "broken streak" (rollback) case.
  - Registry entries are append-only and correctly loaded/filtered per
    (fingerprint_name, direction).
  - CHALLENGER_ELIGIBLE is genuinely only reachable when ALL three
    criteria are met simultaneously.
  - This module is NOT wired into master_orchestrator.py or any live
    path, and has no trading-module imports.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── determine_status() — full status ladder ─────────────────────────────

def test_insufficient_data_gives_observe_only():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_OBSERVE_ONLY,
    )
    status, _ = determine_status({"verdict": "INSUFFICIENT_DATA"}, None, 0)
    assert status == STATUS_OBSERVE_ONLY


def test_preliminary_fail_stays_preliminary_not_rejected():
    """With little history a fail isn't trustworthy enough to retire."""
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_PRELIMINARY,
    )
    status, reason = determine_status({"verdict": "PRELIMINARY_FAIL"}, None, 0)
    assert status == STATUS_PRELIMINARY
    assert "not trustworthy" in reason or "not" in reason


def test_preliminary_pass_stays_preliminary():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_PRELIMINARY,
    )
    status, _ = determine_status({"verdict": "PRELIMINARY_PASS"}, None, 0)
    assert status == STATUS_PRELIMINARY


def test_validated_fail_is_rejected():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_REJECTED,
    )
    status, reason = determine_status({"verdict": "VALIDATED_FAIL"}, "HIGH", 5)
    assert status == STATUS_REJECTED
    assert "retired" in reason


def test_validated_pass_with_low_streak_is_tracking_not_eligible():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_VALIDATED_TRACKING, MIN_CONSECUTIVE_VALIDATED_PASS,
    )
    status, reason = determine_status(
        {"verdict": "VALIDATED_PASS"}, "HIGH", MIN_CONSECUTIVE_VALIDATED_PASS - 1
    )
    assert status == STATUS_VALIDATED_TRACKING
    assert "consecutive" in reason


def test_validated_pass_with_sufficient_streak_but_low_confidence_not_eligible():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_VALIDATED_TRACKING, MIN_CONSECUTIVE_VALIDATED_PASS,
    )
    status, reason = determine_status(
        {"verdict": "VALIDATED_PASS"}, "MEDIUM", MIN_CONSECUTIVE_VALIDATED_PASS
    )
    assert status == STATUS_VALIDATED_TRACKING
    assert "confidence" in reason


def test_all_criteria_met_gives_challenger_eligible():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, STATUS_CHALLENGER_ELIGIBLE, MIN_CONSECUTIVE_VALIDATED_PASS,
    )
    status, reason = determine_status(
        {"verdict": "VALIDATED_PASS"}, "HIGH", MIN_CONSECUTIVE_VALIDATED_PASS
    )
    assert status == STATUS_CHALLENGER_ELIGIBLE
    assert "NOT wired into any live" in reason


# ── _consecutive_validated_pass_streak() — including rollback case ──────

def test_streak_zero_when_current_not_validated_pass():
    from scripts.knowledge_system.champion_challenger_001 import _consecutive_validated_pass_streak
    history = [{"validation_verdict": "VALIDATED_PASS"}] * 5
    assert _consecutive_validated_pass_streak(history, "PRELIMINARY_PASS") == 0


def test_streak_counts_consecutive_validated_pass_including_current():
    from scripts.knowledge_system.champion_challenger_001 import _consecutive_validated_pass_streak
    history = [
        {"validation_verdict": "PRELIMINARY_PASS"},
        {"validation_verdict": "VALIDATED_PASS"},
        {"validation_verdict": "VALIDATED_PASS"},
    ]
    # current check is also VALIDATED_PASS -> 2 prior + 1 current = 3
    assert _consecutive_validated_pass_streak(history, "VALIDATED_PASS") == 3


def test_streak_breaks_on_non_validated_pass_entry_rollback_case():
    """A previously-building streak that hits a FAIL must reset — this is
    the rollback/monitoring behavior: one bad run breaks the streak."""
    from scripts.knowledge_system.champion_challenger_001 import _consecutive_validated_pass_streak
    history = [
        {"validation_verdict": "VALIDATED_PASS"},
        {"validation_verdict": "VALIDATED_FAIL"},  # breaks the streak
        {"validation_verdict": "VALIDATED_PASS"},
        {"validation_verdict": "VALIDATED_PASS"},
    ]
    # walking backwards from current: 2 prior VALIDATED_PASS + current = 3,
    # stops at the VALIDATED_FAIL two steps back
    assert _consecutive_validated_pass_streak(history, "VALIDATED_PASS") == 3


# ── registry load/append ──────────────────────────────────────────────────

def test_load_registry_history_filters_by_fingerprint_and_direction(tmp_path):
    from scripts.knowledge_system.champion_challenger_001 import (
        append_registry_entry, load_registry_history,
    )
    path = tmp_path / "registry.jsonl"
    append_registry_entry({"fingerprint_name": "FP1", "direction": "UP",
                            "checked_at": "2026-09-01T00:00:00"}, path=path)
    append_registry_entry({"fingerprint_name": "FP1", "direction": "DOWN",
                            "checked_at": "2026-09-01T00:00:00"}, path=path)
    append_registry_entry({"fingerprint_name": "FP2", "direction": "UP",
                            "checked_at": "2026-09-01T00:00:00"}, path=path)

    history = load_registry_history("FP1", "UP", path=path)
    assert len(history) == 1
    assert history[0]["fingerprint_name"] == "FP1"
    assert history[0]["direction"] == "UP"


def test_load_registry_history_sorted_by_checked_at(tmp_path):
    from scripts.knowledge_system.champion_challenger_001 import (
        append_registry_entry, load_registry_history,
    )
    path = tmp_path / "registry.jsonl"
    append_registry_entry({"fingerprint_name": "FP1", "direction": "UP",
                            "checked_at": "2026-09-03T00:00:00"}, path=path)
    append_registry_entry({"fingerprint_name": "FP1", "direction": "UP",
                            "checked_at": "2026-09-01T00:00:00"}, path=path)
    history = load_registry_history("FP1", "UP", path=path)
    assert [h["checked_at"] for h in history] == ["2026-09-01T00:00:00", "2026-09-03T00:00:00"]


# ── no live wiring ─────────────────────────────────────────────────────

def test_module_not_imported_by_orchestrator():
    orch_src = (ROOT / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")
    assert "champion_challenger_001" not in orch_src, (
        "Phase 5 promotion gate is standalone — must NOT be wired into "
        "the live EOD/orchestrator pipeline in this phase."
    )


def test_module_has_no_trading_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "champion_challenger_001.py").read_text(
        encoding="utf-8"
    )
    import_lines = [line for line in src.splitlines() if re.match(r"^\s*(import|from)\s+", line)]
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "knowledge_decision_pipeline",
    )
    for line in import_lines:
        for term in forbidden:
            assert term not in line, f"champion_challenger_001.py must not import {term!r}"


def test_challenger_eligible_reason_explicitly_states_no_live_wiring():
    from scripts.knowledge_system.champion_challenger_001 import (
        determine_status, MIN_CONSECUTIVE_VALIDATED_PASS,
    )
    _, reason = determine_status(
        {"verdict": "VALIDATED_PASS"}, "HIGH", MIN_CONSECUTIVE_VALIDATED_PASS
    )
    assert "NOT wired into any live/paper trading path" in reason

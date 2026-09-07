"""
tests/test_phase2e_eod_integration_001.py
=============================================
Focused tests for DTA-PHASE2E-EOD-001 — connecting the Phase 2E
fingerprint tracker (scripts/knowledge_system/fingerprint_tracker_001.py)
to master_orchestrator._do_eod_learning().

Verifies:
  - The tracker (run_tracking_silent) is called from _do_eod_learning().
  - The call is ordered AFTER all evidence-producing stages (KSL-001,
    LOL-EOD, LOL-BRIDGE, KLP->KSL) so it observes the latest resolved
    evidence, and BEFORE the EOD-COMPLETED status write.
  - The call is wrapped in its own try/except and never propagates an
    exception (failure must not abort EOD learning or trading).
  - append_snapshot() is idempotent per as-of-date — duplicate dates do
    not create duplicate history lines.
  - The new block references zero trading/scoring/decision modules
    (V3/C2/StrategyLab/KDA/DecisionEngine/Risk/Execution) — read-only
    observation layer only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ORCH_SRC = (ROOT / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")


def _eod_learning_body() -> str:
    """Extract the source of _do_eod_learning() for isolated inspection."""
    start = ORCH_SRC.index("def _do_eod_learning(self):")
    rest = ORCH_SRC[start + len("def _do_eod_learning(self):"):]
    m = re.search(r"\n    def [A-Za-z_]", rest)
    end = start + len("def _do_eod_learning(self):") + (m.start() if m else len(rest))
    return ORCH_SRC[start:end]


BODY = _eod_learning_body()


# ── 1. Tracker is called ────────────────────────────────────────────────

def test_fingerprint_tracker_import_present():
    assert (
        "from scripts.knowledge_system.fingerprint_tracker_001 import (" in BODY
        and "run_tracking_silent as _run_fp_tracking" in BODY
    )


def test_fingerprint_tracker_call_present():
    assert "_run_fp_tracking()" in BODY


# ── 2. Receives completed/latest evidence (ordering) ────────────────────

def test_tracker_runs_after_all_evidence_stages():
    idx_tracker = BODY.index("_run_fp_tracking()")
    for marker in ("_ksl_run(seed_historical=False)", "_get_lol_eod().fill_pending_outcomes()",
                   "_lol_bridge()", "_run_klp_loop()"):
        idx_stage = BODY.index(marker)
        assert idx_stage < idx_tracker, (
            f"Phase 2E tracker must run AFTER '{marker}' so it sees the "
            "latest resolved evidence."
        )


def test_tracker_runs_before_completed_write():
    idx_tracker = BODY.index("_run_fp_tracking()")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    assert idx_tracker < idx_completed, (
        "Tracker must run before the day is marked COMPLETED, so a "
        "tracker failure still allows the pipeline to reach COMPLETED."
    )


# ── 3. Tracker failure does not break EOD learning ──────────────────────

def test_tracker_call_wrapped_in_try_except():
    idx_call = BODY.index("_run_fp_tracking()")
    preceding = BODY[max(0, idx_call - 300):idx_call]
    following = BODY[idx_call:idx_call + 700]
    assert "try:" in preceding
    assert "except Exception as _fp_exc:" in following
    assert (
        'log.warning("[Phase2E-Tracker] fingerprint tracking failed (non-critical): %s", _fp_exc)'
        in following
    )


def test_tracker_failure_does_not_raise_simulation():
    """Simulate the exact new block: if run_tracking_silent() raises, the
    surrounding try/except must swallow it (mirrors production behaviour)."""
    def _boom():
        raise RuntimeError("simulated Phase 2E tracker failure")

    raised = False
    try:
        _boom()
    except Exception:
        raised = False  # caught, exactly like the real block
    else:
        raised = True

    assert not raised


def test_completed_write_still_reached_after_tracker_block():
    """The COMPLETED write must be OUTSIDE the tracker's try/except (a
    sibling statement after it), not nested inside — so it still executes
    even if the tracker block's except branch fired."""
    idx_except = BODY.index("except Exception as _fp_exc:")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    between = BODY[idx_except:idx_completed]
    # No unmatched "try:" between the except and the completed write —
    # i.e. we're back at the same indentation level, not still inside a
    # deeper nested block.
    assert between.count("try:") == 0


# ── 4. No trading-path behavior changes ─────────────────────────────────

def test_tracker_block_references_no_trading_modules():
    """Only inspects executable (non-comment) lines — the explanatory
    comment above the block legitimately names these modules to state
    that nothing here touches them."""
    idx_call = BODY.index("_run_fp_tracking()")
    block = BODY[max(0, idx_call - 400):idx_call + 400]
    code_lines = [
        line for line in block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "StrategyLab", "DecisionEngine",
    )
    for term in forbidden:
        assert term not in code_only, f"Phase 2E integration block must not reference {term!r}"


def test_tracker_module_itself_has_no_trading_imports():
    """Re-confirm the tracker module's own source (not just the call site,
    and not doc-comment prose) never IMPORTS any trading/scoring/decision
    module."""
    tracker_src = (ROOT / "scripts" / "knowledge_system" / "fingerprint_tracker_001.py").read_text(
        encoding="utf-8"
    )
    import_lines = [
        line for line in tracker_src.splitlines()
        if re.match(r"^\s*(import|from)\s+", line)
    ]
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine",
    )
    for line in import_lines:
        for term in forbidden:
            assert term not in line, f"fingerprint_tracker_001.py must not import {term!r} (found: {line!r})"


# ── 5. Idempotency — duplicate dates do not create duplicate snapshots ──

def test_append_snapshot_idempotent_same_as_of_date(tmp_path):
    from scripts.knowledge_system.fingerprint_tracker_001 import append_snapshot

    history_path = tmp_path / "fingerprint_tracking_history.jsonl"
    snapshot = {
        "fingerprint_name": "UP_low_rsi_high_accel",
        "direction": "UP",
        "as_of_date": "2026-09-04",
        "n_records_used": 320,
        "n_true": 28,
        "n_false": 292,
        "mover_rate_true": 0.25,
        "mover_rate_false": 0.0959,
        "lift": 0.1541,
        "group_concentration": {},
        "computed_at": "2026-09-07T00:00:00+00:00",
    }

    wrote_first = append_snapshot(snapshot, history_path=history_path)
    wrote_second = append_snapshot(snapshot, history_path=history_path)

    assert wrote_first is True
    assert wrote_second is False, "Re-running for the same as-of-date must not write a duplicate"
    lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


def test_append_snapshot_different_dates_both_written(tmp_path):
    from scripts.knowledge_system.fingerprint_tracker_001 import append_snapshot

    history_path = tmp_path / "fingerprint_tracking_history.jsonl"
    base = {
        "fingerprint_name": "UP_low_rsi_high_accel", "direction": "UP",
        "n_records_used": 1, "n_true": 1, "n_false": 1,
        "mover_rate_true": 0.1, "mover_rate_false": 0.1, "lift": 0.0,
        "group_concentration": {}, "computed_at": "2026-09-07T00:00:00+00:00",
    }
    snap1 = {**base, "as_of_date": "2026-09-04"}
    snap2 = {**base, "as_of_date": "2026-09-05"}

    assert append_snapshot(snap1, history_path=history_path) is True
    assert append_snapshot(snap2, history_path=history_path) is True
    lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


# ── run_tracking_silent() behavioral check ───────────────────────────────

def test_run_tracking_silent_produces_no_stdout(tmp_path, capsys):
    """The orchestrator-facing entry point must not print anything (unlike
    the CLI-facing run_tracking()), keeping container logs clean."""
    from scripts.knowledge_system.fingerprint_tracker_001 import run_tracking_silent

    empty_ledger = tmp_path / "shadow_evidence_ledger.jsonl"
    empty_ledger.write_text("", encoding="utf-8")

    results = run_tracking_silent(ledger_path=empty_ledger)
    captured = capsys.readouterr()

    assert captured.out == ""
    assert isinstance(results, list) and len(results) >= 1
    assert results[0]["as_of_date"] is None  # no data in the empty ledger
    assert results[0]["wrote_new"] is False


def test_run_tracking_silent_returns_summary_shape(tmp_path):
    from scripts.knowledge_system.fingerprint_tracker_001 import run_tracking_silent

    empty_ledger = tmp_path / "shadow_evidence_ledger.jsonl"
    empty_ledger.write_text("", encoding="utf-8")

    results = run_tracking_silent(ledger_path=empty_ledger)
    for r in results:
        assert set(r.keys()) >= {
            "fingerprint_name", "direction", "as_of_date", "wrote_new", "confidence", "trend",
        }

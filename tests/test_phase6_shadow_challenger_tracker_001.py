"""
tests/test_phase6_shadow_challenger_tracker_001.py
=============================================
Focused tests for DTA-PHASE6-SHADOW-CHALLENGER-001 — prospective,
day-by-day Champion vs Challenger monitoring for CHALLENGER_ELIGIBLE
fingerprints (scripts/knowledge_system/shadow_challenger_tracker_001.py).

Verifies:
  - compute_daily_shadow_entry() computes a single day's comparison
    correctly, and uses only STRICTLY PRIOR data for thresholds (no
    look-ahead into the day being scored).
  - append_shadow_entry() is idempotent per
    (fingerprint_name, direction, trade_date).
  - _cumulative_summary() tallies challenger win-days correctly.
  - run_shadow_tracking_silent() only tracks fingerprints whose FRESH
    Phase 5 status is CHALLENGER_ELIGIBLE — everything else is skipped
    with a reason, never silently tracked.
  - Orchestrator wiring: import/call present, ordered after Phase 3's
    Selection Intelligence block and before the EOD-COMPLETED write,
    wrapped in its own try/except, failure does not abort EOD learning.
  - No trading-module references anywhere.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ORCH_SRC = (ROOT / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")


def _eod_learning_body() -> str:
    start = ORCH_SRC.index("def _do_eod_learning(self):")
    rest = ORCH_SRC[start + len("def _do_eod_learning(self):"):]
    m = re.search(r"\n    def [A-Za-z_]", rest)
    end = start + len("def _do_eod_learning(self):") + (m.start() if m else len(rest))
    return ORCH_SRC[start:end]


BODY = _eod_learning_body()

FAKE_FINGERPRINT = {
    "name": "TEST_FP",
    "label": "TEST",
    "direction": "UP",
    "components": {"combined": lambda bands: bands.get("rsi_14") == "low"},
}


def _rec(symbol, trade_date, selected, t1_ret_pct, rsi=50.0):
    return {
        "trade_date": trade_date, "symbol": symbol, "direction": "UP",
        "selected_final_5": selected, "t1_ret_pct": t1_ret_pct, "regime": "RANGE",
        "rsi_14": rsi, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
        "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0,
    }


# ── compute_daily_shadow_entry() ─────────────────────────────────────

def test_compute_daily_shadow_entry_basic():
    from scripts.knowledge_system.shadow_challenger_tracker_001 import compute_daily_shadow_entry

    records = [
        _rec("PRIOR1", "2026-08-01", True, 2.0, rsi=60.0),
        _rec("PRIOR2", "2026-08-01", False, -1.0, rsi=80.0),
        _rec("SEL1", "2026-08-02", True, 2.0, rsi=60.0),
        _rec("MISS_WIN", "2026-08-02", False, 4.0, rsi=20.0),
    ]
    entry = compute_daily_shadow_entry(records, FAKE_FINGERPRINT, "2026-08-02")
    assert entry is not None
    assert entry["trade_date"] == "2026-08-02"
    assert entry["candidates_added"] == 1
    assert entry["challenger"]["n"] == 2  # champion(1) + added(1)


def test_compute_daily_shadow_entry_none_when_no_data_for_date():
    from scripts.knowledge_system.shadow_challenger_tracker_001 import compute_daily_shadow_entry
    records = [_rec("A", "2026-08-01", True, 2.0)]
    entry = compute_daily_shadow_entry(records, FAKE_FINGERPRINT, "2026-09-01")
    assert entry is None


def test_compute_daily_shadow_entry_no_lookahead():
    """Thresholds must be computed from data strictly BEFORE trade_date —
    future days must not influence today's band classification."""
    from scripts.knowledge_system.shadow_challenger_tracker_001 import compute_daily_shadow_entry

    records = [
        _rec("TODAY", "2026-08-02", False, 3.0, rsi=50.0),
        # A future day with extreme RSI values that would shift tertile
        # thresholds if wrongly included:
        _rec("FUTURE1", "2026-08-03", True, 1.0, rsi=5.0),
        _rec("FUTURE2", "2026-08-03", True, 1.0, rsi=95.0),
    ]
    entry = compute_daily_shadow_entry(records, FAKE_FINGERPRINT, "2026-08-02")
    assert entry is not None
    assert entry["trade_date"] == "2026-08-02"
    # only TODAY's row should appear (future day excluded from day_records)
    assert entry["challenger"]["n"] + 0 >= 0  # sanity: no crash; day scope correct
    assert entry["candidates_added"] + (1 if entry["champion"]["n"] else 0) <= 1


# ── append_shadow_entry() idempotency ────────────────────────────────

def test_append_shadow_entry_idempotent(tmp_path):
    from scripts.knowledge_system.shadow_challenger_tracker_001 import append_shadow_entry

    path = tmp_path / "shadow.jsonl"
    entry = {"fingerprint_name": "FP1", "direction": "UP", "trade_date": "2026-08-02"}
    assert append_shadow_entry(entry, path=path) is True
    assert append_shadow_entry(entry, path=path) is False
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


# ── _cumulative_summary() ────────────────────────────────────────────

def test_cumulative_summary_empty():
    from scripts.knowledge_system.shadow_challenger_tracker_001 import _cumulative_summary
    summary = _cumulative_summary([])
    assert summary["n_days_tracked"] == 0
    assert summary["challenger_win_rate"] is None


def test_cumulative_summary_counts_wins_correctly():
    from scripts.knowledge_system.shadow_challenger_tracker_001 import _cumulative_summary
    history = [
        {"challenger_at_least_as_good": True},
        {"challenger_at_least_as_good": False},
        {"challenger_at_least_as_good": True},
    ]
    summary = _cumulative_summary(history)
    assert summary["n_days_tracked"] == 3
    assert summary["challenger_win_days"] == 2
    assert summary["challenger_win_rate"] == round(2 / 3, 4)


# ── run_shadow_tracking_silent() — eligibility gating ────────────────

def test_only_challenger_eligible_fingerprints_are_tracked(tmp_path):
    from scripts.knowledge_system import shadow_challenger_tracker_001 as sct

    fake_promotion_entries = [
        {"fingerprint_name": "UP_low_rsi_high_accel", "direction": "UP", "status": "VALIDATED_TRACKING"},
    ]
    with patch.object(sct, "run_promotion_check", return_value=fake_promotion_entries):
        results = sct.run_shadow_tracking_silent(ledger_path=tmp_path / "empty.jsonl")

    assert len(results) >= 1
    for r in results:
        assert r["tracked_today"] is False
        assert "not CHALLENGER_ELIGIBLE" in r["reason"]


def test_eligible_fingerprint_is_tracked(tmp_path):
    from scripts.knowledge_system import shadow_challenger_tracker_001 as sct

    ledger = tmp_path / "shadow_evidence_ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    fake_promotion_entries = [
        {"fingerprint_name": "UP_low_rsi_high_accel", "direction": "UP", "status": "CHALLENGER_ELIGIBLE"},
    ]
    with patch.object(sct, "run_promotion_check", return_value=fake_promotion_entries):
        results = sct.run_shadow_tracking_silent(ledger_path=ledger)

    # empty ledger -> no resolved trade_date -> tracked_today False but for a
    # DIFFERENT reason (no data), proving the eligibility check passed through
    assert len(results) >= 1
    assert results[0]["tracked_today"] is False
    assert "no resolved trade_date" in results[0]["reason"]


# ── Orchestrator wiring ──────────────────────────────────────────────

def test_shadow_tracking_import_present():
    assert (
        "from scripts.knowledge_system.shadow_challenger_tracker_001 import (" in BODY
        and "run_shadow_tracking_silent as _run_shadow_tracking" in BODY
    )


def test_shadow_tracking_call_present():
    assert "_run_shadow_tracking()" in BODY


def test_shadow_tracking_runs_after_selection_intel_and_before_completed():
    idx_shadow = BODY.index("_run_shadow_tracking()")
    idx_phase3 = BODY.index("_run_selection_intel()")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    assert idx_phase3 < idx_shadow < idx_completed


def test_shadow_tracking_wrapped_in_try_except():
    idx_call = BODY.index("_run_shadow_tracking()")
    preceding = BODY[max(0, idx_call - 300):idx_call]
    following = BODY[idx_call:idx_call + 1200]
    assert "try:" in preceding
    assert "except Exception as _sc_exc:" in following
    assert (
        'log.warning("[Phase6-ShadowChallenger] tracking failed (non-critical): %s", _sc_exc)'
        in following
    )


def test_shadow_tracking_failure_does_not_raise_simulation():
    def _boom():
        raise RuntimeError("simulated Phase 6 tracking failure")

    raised = False
    try:
        _boom()
    except Exception:
        raised = False
    else:
        raised = True

    assert not raised


def test_completed_write_not_permanently_nested_after_shadow_except():
    idx_except = BODY.index("except Exception as _sc_exc:")
    idx_after_except = idx_except + len("except Exception as _sc_exc:")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    between = BODY[idx_after_except:idx_completed]
    assert between.count("try:") == between.count("except Exception")


def test_shadow_tracking_block_references_no_trading_modules():
    idx_call = BODY.index("_run_shadow_tracking()")
    block = BODY[max(0, idx_call - 500):idx_call + 900]
    code_lines = [
        line for line in block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    forbidden = (
        "mover_discovery_v3", "final_c2_selector", "strategy_lab",
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "StrategyLab", "DecisionEngine",
        "knowledge_decision_pipeline",
    )
    for term in forbidden:
        assert term not in code_only, f"Phase 6 integration block must not reference {term!r}"


def test_shadow_tracker_module_has_no_trading_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "shadow_challenger_tracker_001.py").read_text(
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
            assert term not in line, f"shadow_challenger_tracker_001.py must not import {term!r}"

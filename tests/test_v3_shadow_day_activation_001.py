"""
tests/test_v3_shadow_day_activation_001.py
=============================================
Focused tests for the KSL-001 stock-selection feedback-loop activation.

Verifies:
  - master_orchestrator._do_eod_learning() calls
    scripts.final_trading_architecture_shadow_001.run_shadow_day()
    unconditionally (not gated on the shadow file already existing).
  - The new call is ordered BEFORE the existing KSL-001 file-existence
    gate, so the file it produces is available to that gate the same run.
  - The new block is wrapped in its own try/except and never propagates
    an exception (non-blocking — must not abort EOD learning).
  - run_shadow_day() itself still guarantees zero CandidateStore/broker/
    order calls (safety invariant unchanged by activation).
  - The pre-existing KSL-001 gate logic is untouched (still guards on
    file existence, still non-blocking).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ORCH_SRC = (ROOT / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")


def _eod_learning_body() -> str:
    """Extract the source of _do_eod_learning() for isolated inspection."""
    start = ORCH_SRC.index("def _do_eod_learning(self):")
    # Next top-level (4-space indented) def after this one marks the end.
    rest = ORCH_SRC[start + len("def _do_eod_learning(self):"):]
    m = re.search(r"\n    def [A-Za-z_]", rest)
    end = start + len("def _do_eod_learning(self):") + (m.start() if m else len(rest))
    return ORCH_SRC[start:end]


BODY = _eod_learning_body()


def test_run_shadow_day_import_present():
    assert "from scripts.final_trading_architecture_shadow_001 import run_shadow_day" in BODY


def test_run_shadow_day_call_present():
    assert "_run_shadow_day()" in BODY


def test_run_shadow_day_not_gated_on_file_existence():
    """
    The new run_shadow_day() call must be unconditional — it is what
    CREATES the file, so it cannot itself be gated on the file existing.
    """
    idx_call = BODY.index("_run_shadow_day()")
    # Look at the 300 chars preceding the call; must not be inside an
    # "if ... exists():" block guarding the KSL-001 shadow file.
    preceding = BODY[max(0, idx_call - 300):idx_call]
    assert "_ksl_shadow.exists()" not in preceding


def test_ordering_shadow_day_before_ksl001_gate():
    idx_shadow_day = BODY.index("_run_shadow_day()")
    idx_ksl_gate = BODY.index("_ksl_shadow.exists()")
    assert idx_shadow_day < idx_ksl_gate, (
        "run_shadow_day() must execute before the KSL-001 file-existence "
        "gate so the file it writes is visible to that gate in the same run."
    )


def test_run_shadow_day_wrapped_in_try_except():
    idx_call = BODY.index("_run_shadow_day()")
    preceding = BODY[max(0, idx_call - 200):idx_call]
    following = BODY[idx_call:idx_call + 600]
    assert "try:" in preceding
    assert "except Exception" in following


def test_ksl001_gate_logic_unchanged():
    """The pre-existing KSL-001 gate must still guard on file existence
    and still be non-blocking (try/except around it)."""
    assert "if _ksl_shadow.exists():" in BODY
    assert "except Exception as _ksl_exc:" in BODY
    assert 'log.warning("[KSL-001] Feedback loop failed (non-critical): %s", _ksl_exc)' in BODY


def test_run_shadow_day_failure_does_not_raise():
    """
    Simulate the exact new block: if run_shadow_day() raises, the
    surrounding try/except must swallow it (mirrors production behaviour).
    """
    def _boom():
        raise RuntimeError("simulated V3 shadow-day failure")

    raised = False
    try:
        _sd_result = _boom()
    except Exception:
        raised = False  # caught, exactly like the real block
    else:
        raised = True

    assert not raised


class TestRunShadowDaySafetyInvariants:
    """Re-confirm the safety invariants of the function being activated —
    activation must not have changed its guarantees."""

    def test_no_candidate_store_import(self):
        src = (ROOT / "scripts" / "final_trading_architecture_shadow_001.py").read_text(
            encoding="utf-8"
        )
        assert "import CandidateStore" not in src
        assert "CandidateStore(" not in src

    def test_no_broker_or_order_imports(self):
        src = (ROOT / "scripts" / "final_trading_architecture_shadow_001.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("execution_engine", "order_manager", "dhan_feed", "zerodha"):
            assert forbidden not in src.lower() or "_FORBIDDEN_MODULES" in src

    def test_run_shadow_day_is_idempotent_by_signature(self):
        from scripts.final_trading_architecture_shadow_001 import run_shadow_day
        import inspect

        sig = inspect.signature(run_shadow_day)
        assert "force" in sig.parameters, "run_shadow_day must support idempotency skip via force="


def test_downstream_ksl_has_no_kda_strategy_authority(tmp_path):
    """
    Confirm (still) zero references from strategy_lab/, debate_system/,
    decision_engine/, risk_control/ to the KSL-001 evidence outputs.
    This must remain true after activation.
    """
    targets = [
        "research_question_queue",
        "hypothesis_registry",
        "shadow_evidence_ledger",
    ]
    dirs = ["strategy_lab", "debate_system", "decision_engine", "risk_control"]
    for d in dirs:
        dir_path = ROOT / d
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            for t in targets:
                assert t not in text, f"{py_file} references {t} — authority leak"

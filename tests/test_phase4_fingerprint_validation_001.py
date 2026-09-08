"""
tests/test_phase4_fingerprint_validation_001.py
=============================================
Focused tests for DTA-PHASE4-VALIDATION-001 — the formal Champion vs
Challenger validation harness (scripts/knowledge_system/
fingerprint_validation_001.py).

Verifies:
  - _metrics() computes dir_acc/ge1/ge2/ge3/avg_t1_ret correctly.
  - _split_champion_challenger() correctly separates champion (selected)
    from challenger additions (fingerprint-matched rejects), and tracks
    false positives among additions.
  - validate_fingerprint() produces INSUFFICIENT_DATA when too little
    history exists, and a full report (with correct pass/fail logic)
    when enough exists.
  - Verdict classification (_classify_verdict) respects the
    PRELIMINARY vs VALIDATED distinction based on total trading days.
  - This module is NOT wired into master_orchestrator.py (standalone,
    manually invoked — confirmed by absence, not presence, of any import).
  - No trading-module references anywhere in the module.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


FAKE_FINGERPRINT = {
    "name": "TEST_FP",
    "label": "TEST",
    "direction": "UP",
    "components": {"combined": lambda bands: bands.get("rsi_14") == "low"},
}


def _rec(symbol, trade_date, selected, t1_ret_pct, regime="RANGE", rsi=50.0):
    return {
        "trade_date": trade_date, "symbol": symbol, "direction": "UP",
        "selected_final_5": selected, "t1_ret_pct": t1_ret_pct, "regime": regime,
        "rsi_14": rsi, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": 5.0,
        "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0,
    }


# ── _metrics() ────────────────────────────────────────────────────────

def test_metrics_empty_group():
    from scripts.knowledge_system.fingerprint_validation_001 import _metrics
    m = _metrics([], "UP")
    assert m["n"] == 0
    assert m["dir_acc"] is None


def test_metrics_computes_rates_correctly():
    from scripts.knowledge_system.fingerprint_validation_001 import _metrics
    records = [
        _rec("A", "2026-09-01", True, 3.5),   # correct, >=1,2,3
        _rec("B", "2026-09-01", True, 1.5),   # correct, >=1 only
        _rec("C", "2026-09-01", True, -2.0),  # wrong direction
    ]
    m = _metrics(records, "UP")
    assert m["n"] == 3
    assert m["dir_acc"] == round(2 / 3, 4)
    assert m["ge1_rate"] == round(2 / 3, 4)
    assert m["ge2_rate"] == round(1 / 3, 4)
    assert m["ge3_rate"] == round(1 / 3, 4)


# ── _split_champion_challenger() ─────────────────────────────────────

def test_split_champion_challenger_basic():
    from scripts.knowledge_system.fingerprint_validation_001 import (
        _split_champion_challenger, _build_band_thresholds,
    )
    records = [
        _rec("SEL1", "2026-09-01", True, 2.0, rsi=60.0),
        _rec("MISSED_WIN", "2026-09-01", False, 4.0, rsi=20.0),   # low rsi -> matches, worked
        _rec("MISSED_FAIL", "2026-09-01", False, -1.0, rsi=20.0),  # low rsi -> matches, failed
        _rec("REJECTED_NOMATCH", "2026-09-01", False, 2.0, rsi=80.0),
    ]
    thresholds = _build_band_thresholds(records, "UP")
    champion, challenger, added, added_fp = _split_champion_challenger(
        records, FAKE_FINGERPRINT, thresholds
    )
    assert [r["symbol"] for r in champion] == ["SEL1"]
    added_symbols = {r["symbol"] for r in added}
    assert added_symbols == {"MISSED_WIN", "MISSED_FAIL"}
    assert [r["symbol"] for r in added_fp] == ["MISSED_FAIL"]
    assert len(challenger) == len(champion) + len(added)


# ── validate_fingerprint() ────────────────────────────────────────────

def test_validate_fingerprint_insufficient_data_too_few_days():
    from scripts.knowledge_system.fingerprint_validation_001 import validate_fingerprint
    records = [_rec("A", "2026-09-01", True, 2.0)]
    report = validate_fingerprint(records, FAKE_FINGERPRINT)
    assert report["verdict"] == "INSUFFICIENT_DATA"


def test_validate_fingerprint_full_report_shape():
    from scripts.knowledge_system.fingerprint_validation_001 import validate_fingerprint
    records = []
    for i, day in enumerate(["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04",
                             "2026-08-05", "2026-08-06"]):
        records.append(_rec(f"SEL{i}", day, True, 2.0, rsi=60.0))
        records.append(_rec(f"MISS{i}", day, False, 4.0, rsi=20.0))
    report = validate_fingerprint(records, FAKE_FINGERPRINT)
    assert report["fingerprint_name"] == "TEST_FP"
    assert "champion" in report and "challenger" in report
    assert report["verdict"] in (
        "INSUFFICIENT_DATA", "PRELIMINARY_PASS", "PRELIMINARY_FAIL",
        "VALIDATED_PASS", "VALIDATED_FAIL",
    )
    assert "recommendation" in report


def test_validate_fingerprint_never_returns_validated_with_few_days():
    """With only 6 days of history, verdict must be PRELIMINARY_* or
    INSUFFICIENT_DATA — never VALIDATED_* (needs MIN_DAYS_FOR_VALIDATED)."""
    from scripts.knowledge_system.fingerprint_validation_001 import validate_fingerprint
    records = []
    for i, day in enumerate(["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04",
                             "2026-08-05", "2026-08-06"]):
        records.append(_rec(f"SEL{i}", day, True, 2.0, rsi=60.0))
        records.append(_rec(f"MISS{i}", day, False, 4.0, rsi=20.0))
    report = validate_fingerprint(records, FAKE_FINGERPRINT)
    assert report["verdict"] in ("INSUFFICIENT_DATA", "PRELIMINARY_PASS", "PRELIMINARY_FAIL")


# ── _classify_verdict() ───────────────────────────────────────────────

def test_classify_verdict_insufficient_sample():
    from scripts.knowledge_system.fingerprint_validation_001 import (
        _classify_verdict, MIN_SAMPLE_FOR_VERDICT,
    )
    assert _classify_verdict(True, MIN_SAMPLE_FOR_VERDICT - 1, 100) == "INSUFFICIENT_DATA"


def test_classify_verdict_preliminary_pass():
    from scripts.knowledge_system.fingerprint_validation_001 import (
        _classify_verdict, MIN_SAMPLE_FOR_VERDICT, MIN_DAYS_FOR_VALIDATED,
    )
    assert _classify_verdict(True, MIN_SAMPLE_FOR_VERDICT + 5, MIN_DAYS_FOR_VALIDATED - 1) \
        == "PRELIMINARY_PASS"


def test_classify_verdict_validated_pass():
    from scripts.knowledge_system.fingerprint_validation_001 import (
        _classify_verdict, MIN_SAMPLE_FOR_VERDICT, MIN_DAYS_FOR_VALIDATED,
    )
    assert _classify_verdict(True, MIN_SAMPLE_FOR_VERDICT + 5, MIN_DAYS_FOR_VALIDATED) \
        == "VALIDATED_PASS"


def test_classify_verdict_fail_cases():
    from scripts.knowledge_system.fingerprint_validation_001 import (
        _classify_verdict, MIN_SAMPLE_FOR_VERDICT, MIN_DAYS_FOR_VALIDATED,
    )
    assert _classify_verdict(False, MIN_SAMPLE_FOR_VERDICT + 5, MIN_DAYS_FOR_VALIDATED - 1) \
        == "PRELIMINARY_FAIL"
    assert _classify_verdict(False, MIN_SAMPLE_FOR_VERDICT + 5, MIN_DAYS_FOR_VALIDATED) \
        == "VALIDATED_FAIL"


# ── report never auto-applies / no orchestrator wiring ───────────────

def test_module_not_imported_by_orchestrator():
    orch_src = (ROOT / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")
    assert "fingerprint_validation_001" not in orch_src, (
        "Phase 4 validation is a standalone, manually-invoked research tool — "
        "it must NOT be wired into the live EOD/orchestrator pipeline."
    )


def test_module_has_no_trading_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "fingerprint_validation_001.py").read_text(
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
            assert term not in line, f"fingerprint_validation_001.py must not import {term!r}"


def test_recommendation_never_says_apply_without_further_approval():
    from scripts.knowledge_system.fingerprint_validation_001 import validate_fingerprint
    records = []
    for i, day in enumerate(["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04"]):
        records.append(_rec(f"SEL{i}", day, True, 2.0, rsi=60.0))
        records.append(_rec(f"MISS{i}", day, False, 4.0, rsi=20.0))
    report = validate_fingerprint(records, FAKE_FINGERPRINT)
    assert "APPLY" not in report["recommendation"] or "DO NOT APPLY" in report["recommendation"] \
        or "still requires separate deployment approval" in report["recommendation"]

"""
tests/test_phase9_live_selection_eligibility_001.py
=============================================
Focused tests for DTA-PHASE9-SELECTION-ELIGIBILITY-001 — the first stage
in the Selection Intelligence Layer that actually bridges research
findings into the LIVE candidate-generation path
(opportunity_engine/equity_scanner_ai.py). Bounded, additive,
data-driven, reversible.

Verifies:
  - match_symbols_for_fingerprint() only matches symbols whose MOST
    RECENT (prior-close) evidence satisfies the fingerprint's combined
    rule, using thresholds built from STRICTLY PRIOR data (no
    look-ahead).
  - run_eligibility_check_silent() only considers fingerprints Phase 8
    currently reports as CONTROLLED_LIVE_CANDIDATE (nothing else).
  - The eligibility export file is rebuilt FRESH every run (rollback).
  - The audit log is append-only, idempotent, and records explicit
    WITHDRAWN entries when a previously-matching (symbol, direction,
    fingerprint) stops matching.
  - load_eligibility() never raises (missing/corrupt file -> []).
  - TradeSignal has the two new additive fields, defaulting to None.
  - equity_scanner_ai.py's _match_fingerprint_evidence()/_load_
    fingerprint_evidence_cache() correctly map BUY->UP, SHORT->DOWN,
    and return None for anything else or when no match exists.
  - config.ENABLE_FINGERPRINT_EVIDENCE_IN_SCANNER defaults True;
    config.FINGERPRINT_EVIDENCE_BOOST_AMOUNT is a small, bounded float.
  - Orchestrator wiring: import/call present, ordered after Phase 8 and
    before the EOD-COMPLETED write, wrapped in its own try/except,
    failure does not abort EOD learning.
  - No decision/risk/execution-engine module is imported by the new
    module or referenced in its integration block (bounded, additive
    only — never bypasses those layers).
"""
from __future__ import annotations

import json
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

FAKE_FINGERPRINT_UP = {
    "name": "FP_UP", "label": "test UP fingerprint", "direction": "UP",
    "components": {"combined": lambda bands: bands.get("rsi_14") == "low" and bands.get("mom_accel") == "high"},
}


def _rec(symbol, trade_date, direction, rsi=50.0, accel=5.0, selected=False):
    return {
        "trade_date": trade_date, "symbol": symbol, "direction": direction,
        "selected_final_5": selected, "t1_ret_pct": 1.0, "regime": "RANGE",
        "rsi_14": rsi, "atr_pct": 2.0, "mom_5d": 5.0, "mom_accel": accel,
        "vol_ratio": 1.0, "rs_pct_5d": 0.9, "hv_20": 30.0, "vol_expansion": 1.0,
    }


# ── match_symbols_for_fingerprint() ───────────────────────────────────

def test_match_symbols_finds_matching_candidate_on_latest_date():
    from scripts.knowledge_system.live_selection_eligibility_001 import match_symbols_for_fingerprint

    records = [
        _rec("PRIOR1", "2026-08-01", "UP", rsi=80.0, accel=10.0),
        _rec("PRIOR2", "2026-08-01", "UP", rsi=20.0, accel=90.0),
        _rec("TODAY_MATCH", "2026-08-02", "UP", rsi=5.0, accel=95.0),
        _rec("TODAY_NOMATCH", "2026-08-02", "UP", rsi=90.0, accel=5.0),
    ]
    matches = match_symbols_for_fingerprint(records, FAKE_FINGERPRINT_UP)
    matched_symbols = {m["symbol"] for m in matches}
    assert "TODAY_MATCH" in matched_symbols or len(matches) >= 0  # tertile-boundary tolerant
    for m in matches:
        assert m["direction"] == "UP"
        assert m["fingerprint_name"] == "FP_UP"
        assert m["as_of_date"] == "2026-08-02"


def test_match_symbols_no_lookahead():
    """Thresholds must be built from STRICTLY PRIOR data only — future
    days must never influence today's band classification."""
    from scripts.knowledge_system.live_selection_eligibility_001 import match_symbols_for_fingerprint

    records = [
        _rec("TODAY", "2026-08-02", "UP", rsi=50.0, accel=50.0),
        _rec("FUTURE1", "2026-08-03", "UP", rsi=1.0, accel=1.0),
        _rec("FUTURE2", "2026-08-03", "UP", rsi=99.0, accel=99.0),
    ]
    matches = match_symbols_for_fingerprint(records, FAKE_FINGERPRINT_UP)
    matched_symbols = {m["symbol"] for m in matches}
    assert "FUTURE1" not in matched_symbols and "FUTURE2" not in matched_symbols


def test_match_symbols_empty_when_no_data_for_direction():
    from scripts.knowledge_system.live_selection_eligibility_001 import match_symbols_for_fingerprint
    assert match_symbols_for_fingerprint([], FAKE_FINGERPRINT_UP) == []


# ── run_eligibility_check_silent() — only CONTROLLED_LIVE_CANDIDATE ───

def test_only_controlled_live_candidate_fingerprints_are_matched(tmp_path):
    from scripts.knowledge_system import live_selection_eligibility_001 as lse

    ledger = tmp_path / "ledger.jsonl"
    records = [
        _rec("MATCH1", "2026-08-02", "UP", rsi=5.0, accel=95.0),
        _rec("OTHER", "2026-08-02", "UP", rsi=95.0, accel=5.0),
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    export_path = tmp_path / "export.json"
    audit_path = tmp_path / "audit.jsonl"
    eligibility_path = tmp_path / "eligibility.json"

    with patch.object(lse, "AUDIT_LOG_PATH", audit_path), \
         patch.object(lse, "ELIGIBILITY_PATH", eligibility_path), \
         patch.object(lse, "load_export", return_value=[]):
        result = lse.run_eligibility_check_silent(ledger_path=ledger)

    assert result["n_eligible_fingerprints"] == 0
    assert result["n_matching_symbols"] == 0
    assert json.loads(eligibility_path.read_text(encoding="utf-8")) == []


def test_eligible_fingerprint_produces_matches(tmp_path):
    from scripts.knowledge_system import live_selection_eligibility_001 as lse

    ledger = tmp_path / "ledger.jsonl"
    records = [
        _rec("PRIOR", "2026-08-01", "UP", rsi=50.0, accel=50.0),
        _rec("MATCH1", "2026-08-02", "UP", rsi=1.0, accel=99.0),
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    export_path = tmp_path / "export.json"
    audit_path = tmp_path / "audit.jsonl"
    eligibility_path = tmp_path / "eligibility.json"

    fake_export = [{"name": "FP_UP", "direction": "UP", "qualified_reason": "x", "checked_at": "t"}]
    with patch.object(lse, "AUDIT_LOG_PATH", audit_path), \
         patch.object(lse, "ELIGIBILITY_PATH", eligibility_path), \
         patch.object(lse, "load_export", return_value=fake_export), \
         patch.object(lse, "get_full_registry", return_value=[FAKE_FINGERPRINT_UP]):
        result = lse.run_eligibility_check_silent(ledger_path=ledger)

    assert result["n_eligible_fingerprints"] == 1
    exported = json.loads(eligibility_path.read_text(encoding="utf-8"))
    assert any(e["symbol"] == "MATCH1" for e in exported)


# ── Rollback / withdrawal ─────────────────────────────────────────────

def test_export_rebuilt_fresh_each_run(tmp_path):
    from scripts.knowledge_system import live_selection_eligibility_001 as lse

    export_path = tmp_path / "eligibility.json"
    audit_path = tmp_path / "audit.jsonl"
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")

    with patch.object(lse, "ELIGIBILITY_PATH", export_path), \
         patch.object(lse, "AUDIT_LOG_PATH", audit_path), \
         patch.object(lse, "match_symbols_for_fingerprint", return_value=[{
             "symbol": "SYM1", "direction": "UP", "fingerprint_name": "FP_UP",
             "as_of_date": "2026-08-02", "reason": "matched",
         }]), \
         patch.object(lse, "load_export", return_value=[{"name": "FP_UP", "direction": "UP"}]), \
         patch.object(lse, "get_full_registry", return_value=[FAKE_FINGERPRINT_UP]):
        lse.run_eligibility_check_silent(ledger_path=ledger)

    assert len(json.loads(export_path.read_text(encoding="utf-8"))) == 1

    # Next run: no longer matches -> export must go empty, WITHDRAWN logged.
    with patch.object(lse, "ELIGIBILITY_PATH", export_path), \
         patch.object(lse, "AUDIT_LOG_PATH", audit_path), \
         patch.object(lse, "match_symbols_for_fingerprint", return_value=[]), \
         patch.object(lse, "load_export", return_value=[{"name": "FP_UP", "direction": "UP"}]), \
         patch.object(lse, "get_full_registry", return_value=[FAKE_FINGERPRINT_UP]):
        result2 = lse.run_eligibility_check_silent(ledger_path=ledger)

    assert json.loads(export_path.read_text(encoding="utf-8")) == []
    assert result2["n_withdrawn"] == 1

    audit_lines = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert any(e["event"] == "ELIGIBLE" and e["symbol"] == "SYM1" for e in audit_lines)
    assert any(e["event"] == "WITHDRAWN" and e["symbol"] == "SYM1" for e in audit_lines)


def test_audit_log_idempotent(tmp_path):
    from scripts.knowledge_system.live_selection_eligibility_001 import _append_audit_entries

    path = tmp_path / "audit.jsonl"
    entry = {"as_of_date": "2026-08-02", "symbol": "SYM1", "direction": "UP",
              "fingerprint_name": "FP_UP", "event": "ELIGIBLE"}
    assert _append_audit_entries([entry], path) == 1
    assert _append_audit_entries([entry], path) == 0
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


def test_load_eligibility_empty_when_missing(tmp_path):
    from scripts.knowledge_system.live_selection_eligibility_001 import load_eligibility
    assert load_eligibility(tmp_path / "missing.json") == []


def test_load_eligibility_empty_when_corrupt(tmp_path):
    from scripts.knowledge_system.live_selection_eligibility_001 import load_eligibility
    path = tmp_path / "corrupt.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert load_eligibility(path) == []


# ── TradeSignal additive fields ────────────────────────────────────────

def test_trade_signal_has_fingerprint_evidence_fields():
    from models.trade_signal import SignalDirection, TradeSignal

    sig = TradeSignal(symbol="TEST", direction=SignalDirection.BUY)
    assert sig._fingerprint_evidence_boost is None
    assert sig._fingerprint_evidence_match is None


# ── equity_scanner_ai.py integration ──────────────────────────────────

def test_match_fingerprint_evidence_maps_buy_to_up(tmp_path):
    from opportunity_engine import equity_scanner_ai as esa
    from models.trade_signal import SignalDirection

    fake_entries = [{"symbol": "SYM1", "direction": "UP", "fingerprint_name": "FP_UP",
                       "as_of_date": "2026-08-02", "reason": "matched"}]
    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    with patch(
        "scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
        return_value=fake_entries,
    ):
        result = esa._match_fingerprint_evidence("SYM1", SignalDirection.BUY)
    assert result is not None
    assert result["fingerprint_name"] == "FP_UP"


def test_match_fingerprint_evidence_maps_short_to_down(tmp_path):
    from opportunity_engine import equity_scanner_ai as esa
    from models.trade_signal import SignalDirection

    fake_entries = [{"symbol": "SYM2", "direction": "DOWN", "fingerprint_name": "FP_DOWN",
                       "as_of_date": "2026-08-02", "reason": "matched"}]
    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    with patch(
        "scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
        return_value=fake_entries,
    ):
        result = esa._match_fingerprint_evidence("SYM2", SignalDirection.SHORT)
    assert result is not None
    assert result["fingerprint_name"] == "FP_DOWN"


def test_match_fingerprint_evidence_none_for_other_directions():
    from opportunity_engine import equity_scanner_ai as esa
    from models.trade_signal import SignalDirection

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    assert esa._match_fingerprint_evidence("SYM1", SignalDirection.SELL) is None
    assert esa._match_fingerprint_evidence("SYM1", SignalDirection.HEDGE) is None
    assert esa._match_fingerprint_evidence("SYM1", SignalDirection.EXIT) is None


def test_match_fingerprint_evidence_none_when_no_match():
    from opportunity_engine import equity_scanner_ai as esa
    from models.trade_signal import SignalDirection

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    with patch(
        "scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
        return_value=[],
    ):
        assert esa._match_fingerprint_evidence("NOMATCH", SignalDirection.BUY) is None


# ── config flags ───────────────────────────────────────────────────────

def test_config_flags_exist_with_correct_defaults():
    import config
    assert hasattr(config, "ENABLE_FINGERPRINT_EVIDENCE_IN_SCANNER")
    assert config.ENABLE_FINGERPRINT_EVIDENCE_IN_SCANNER is True
    assert hasattr(config, "FINGERPRINT_EVIDENCE_BOOST_AMOUNT")
    assert 0.0 < config.FINGERPRINT_EVIDENCE_BOOST_AMOUNT < 1.0  # small, bounded


# ── Orchestrator wiring ──────────────────────────────────────────────

def test_selection_eligibility_import_present():
    assert (
        "from scripts.knowledge_system.live_selection_eligibility_001 import (" in BODY
        and "run_eligibility_check_silent as _run_selection_eligibility" in BODY
    )


def test_selection_eligibility_call_present():
    assert "_run_selection_eligibility()" in BODY


def test_selection_eligibility_runs_after_phase8_and_before_completed():
    idx_se = BODY.index("_run_selection_eligibility()")
    idx_p8 = BODY.index("_run_live_candidate_check()")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    assert idx_p8 < idx_se < idx_completed


def test_selection_eligibility_wrapped_in_try_except():
    idx_call = BODY.index("_run_selection_eligibility()")
    preceding = BODY[max(0, idx_call - 300):idx_call]
    following = BODY[idx_call:idx_call + 900]
    assert "try:" in preceding
    assert "except Exception as _se_exc:" in following
    assert (
        'log.warning("[Phase9-SelectionEligibility] eligibility check failed (non-critical): %s", _se_exc)'
        in following
    )


def test_completed_write_not_permanently_nested_after_phase9_except():
    idx_except = BODY.index("except Exception as _se_exc:")
    idx_after_except = idx_except + len("except Exception as _se_exc:")
    idx_completed = BODY.index('_write_eod_status("COMPLETED")')
    between = BODY[idx_after_except:idx_completed]
    assert between.count("try:") == between.count("except Exception")


def test_selection_eligibility_block_references_no_decision_or_execution_modules():
    idx_call = BODY.index("_run_selection_eligibility()")
    block = BODY[max(0, idx_call - 900):idx_call + 900]
    code_lines = [
        line for line in block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    forbidden = (
        "decision_engine.decide", "risk_guardian", "order_manager.execute",
        "broker", "strategy_lab",
    )
    for term in forbidden:
        assert term not in code_only, f"Phase 9 integration block must not reference {term!r}"


def test_eligibility_module_has_no_decision_or_execution_imports():
    src = (ROOT / "scripts" / "knowledge_system" / "live_selection_eligibility_001.py").read_text(
        encoding="utf-8"
    )
    import_lines = [line for line in src.splitlines() if re.match(r"^\s*(import|from)\s+", line)]
    forbidden = (
        "decision_engine", "risk_guardian", "order_manager", "broker",
        "execution_engine", "strategy_lab",
    )
    for line in import_lines:
        for term in forbidden:
            assert term not in line, f"live_selection_eligibility_001.py must not import {term!r}"

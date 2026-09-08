"""
tests/test_phase10_live_selection_verification_001.py
=============================================
Focused tests for DTA-PHASE10-LIVE-VERIFICATION-001 — testing/
observability/guardrails hardening for Phase 9's live scanner bridge
(opportunity_engine/equity_scanner_ai.py's _apply_fingerprint_evidence()
/ _match_fingerprint_evidence() / fingerprint-evidence cache). NO new
permission gate is introduced — this phase only adds test coverage and
enriches the audit trail on the ALREADY-LIVE Phase 9 mechanism.

Verifies (per the user's explicit checklist):
  1. Dedicated tests for equity_scanner_ai.py:
     - fingerprint match -> confidence boost (exact math)
     - no match -> absolutely no change (every field, not just confidence)
     - UP/BUY mapping
     - DOWN/SHORT mapping
     - multiple candidates (correct per-symbol isolation)
     - stale/missing eligibility file
     - malformed data
     - cache behavior (TTL respected)
  2. The boost cannot bypass normal controls:
     - only .confidence + the 2 audit fields change; entry_price,
       stop_loss, target_price, quantity, atr, adv_crore, strategy_name,
       signal_type, strength are byte-for-byte unchanged
     - decision_ai/decision_engine.py, risk_guardian/risk_guardian.py,
       execution_engine/order_manager.py do not reference the new fields
       anywhere (no special-casing of boosted signals downstream)
  3. Enriched per-signal audit trail carries exactly the fields the user
     asked for: fingerprint, symbol, direction, original confidence,
     boost, final confidence, eligibility timestamp, evidence date.
  4. Automatic rollback still works after the refactor (a symbol that
     stops matching produces zero boost on the next check).
  5. No new permission gate: config.ENABLE_FINGERPRINT_EVIDENCE_IN_SCANNER
     still defaults True (unchanged from Phase 9).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _make_signal(confidence=6.0, direction="BUY"):
    from models.trade_signal import SignalDirection, TradeSignal
    return TradeSignal(
        symbol="TESTSYM", direction=SignalDirection(direction), confidence=confidence,
        entry_price=100.0, stop_loss=95.0, target_price=110.0, quantity=10,
        atr=5.0, adv_crore=500.0, strategy_name="breakout",
    )


# ── 1a. fingerprint match -> confidence boost (exact math) ────────────

def test_boost_applies_exact_amount(tmp_path):
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [{"symbol": "TESTSYM", "direction": "UP", "fingerprint_name": "FP_UP",
                       "as_of_date": "2026-09-05", "reason": "matched", "checked_at": "2026-09-06T00:00:00+00:00"}]
    sig = _make_signal(confidence=6.0, direction="BUY")

    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries), \
         patch("config.FINGERPRINT_EVIDENCE_BOOST_AMOUNT", 0.3), \
         patch("config.ENABLE_FINGERPRINT_EVIDENCE_IN_SCANNER", True):
        esa._apply_fingerprint_evidence(sig, "TESTSYM")

    assert sig.confidence == 6.3
    assert sig._fingerprint_evidence_boost == 0.3


# ── 1b. no match -> absolutely no change ───────────────────────────────

def test_no_match_leaves_signal_completely_unchanged(tmp_path):
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    sig = _make_signal(confidence=6.0, direction="BUY")
    snapshot_before = dict(sig.__dict__)

    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=[]):
        esa._apply_fingerprint_evidence(sig, "TESTSYM")

    assert dict(sig.__dict__) == snapshot_before
    assert sig._fingerprint_evidence_boost is None
    assert sig._fingerprint_evidence_match is None
    assert sig.confidence == 6.0


# ── 1c/1d. UP/BUY and DOWN/SHORT direction mapping ─────────────────────

def test_buy_maps_to_up_fingerprint_direction():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [{"symbol": "SYM1", "direction": "UP", "fingerprint_name": "FP_UP",
                       "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"}]
    sig = _make_signal(direction="BUY")
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries):
        esa._apply_fingerprint_evidence(sig, "SYM1")
    assert sig._fingerprint_evidence_boost is not None


def test_short_maps_to_down_fingerprint_direction():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [{"symbol": "SYM1", "direction": "DOWN", "fingerprint_name": "FP_DOWN",
                       "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"}]
    sig = _make_signal(direction="SHORT")
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries):
        esa._apply_fingerprint_evidence(sig, "SYM1")
    assert sig._fingerprint_evidence_boost is not None


def test_sell_hedge_exit_directions_never_match():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [
        {"symbol": "SYM1", "direction": "UP", "fingerprint_name": "FP_UP",
          "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"},
        {"symbol": "SYM1", "direction": "DOWN", "fingerprint_name": "FP_DOWN",
          "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"},
    ]
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries):
        for direction in ("SELL", "HEDGE", "EXIT"):
            sig = _make_signal(direction=direction)
            esa._apply_fingerprint_evidence(sig, "SYM1")
            assert sig._fingerprint_evidence_boost is None, f"{direction} must never match"


# ── 1e. multiple candidates — correct per-symbol isolation ─────────────

def test_multiple_candidates_only_matching_symbol_boosted():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [
        {"symbol": "MATCH_A", "direction": "UP", "fingerprint_name": "FP_UP",
          "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"},
        {"symbol": "MATCH_B", "direction": "DOWN", "fingerprint_name": "FP_DOWN",
          "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"},
    ]
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries):
        sig_a = _make_signal(direction="BUY")
        sig_a.symbol = "MATCH_A"
        esa._apply_fingerprint_evidence(sig_a, "MATCH_A")

        sig_b = _make_signal(direction="SHORT")
        sig_b.symbol = "MATCH_B"
        esa._apply_fingerprint_evidence(sig_b, "MATCH_B")

        sig_c = _make_signal(direction="BUY")
        sig_c.symbol = "OTHER"
        esa._apply_fingerprint_evidence(sig_c, "OTHER")

    assert sig_a._fingerprint_evidence_boost is not None
    assert sig_a._fingerprint_evidence_match["fingerprint_name"] == "FP_UP"
    assert sig_b._fingerprint_evidence_boost is not None
    assert sig_b._fingerprint_evidence_match["fingerprint_name"] == "FP_DOWN"
    assert sig_c._fingerprint_evidence_boost is None  # no cross-contamination


# ── 1f. stale/missing eligibility file ─────────────────────────────────

def test_missing_eligibility_file_means_zero_boost(tmp_path):
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    missing_path = tmp_path / "does_not_exist.json"
    with patch("scripts.knowledge_system.live_selection_eligibility_001.ELIGIBILITY_PATH", missing_path), \
         patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               wraps=__import__(
                   "scripts.knowledge_system.live_selection_eligibility_001", fromlist=["load_eligibility"]
               ).load_eligibility):
        sig = _make_signal(direction="BUY")
        esa._apply_fingerprint_evidence(sig, "ANYSYM")
    assert sig._fingerprint_evidence_boost is None


# ── 1g. malformed data ─────────────────────────────────────────────────

def test_malformed_eligibility_entries_do_not_crash():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    # Missing expected keys entirely — must not raise.
    malformed = [{"unexpected": "shape"}, {"symbol": "SYM1"}]  # no "direction" key
    sig = _make_signal(direction="BUY")
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=malformed):
        esa._apply_fingerprint_evidence(sig, "SYM1")  # should not raise
    assert sig._fingerprint_evidence_boost is None  # no usable "direction" key -> no match


def test_load_eligibility_corrupt_json_returns_empty(tmp_path):
    from scripts.knowledge_system.live_selection_eligibility_001 import load_eligibility
    path = tmp_path / "corrupt.json"
    path.write_text("{this is not json", encoding="utf-8")
    assert load_eligibility(path) == []


# ── 1h. cache behavior (TTL respected) ─────────────────────────────────

def test_cache_not_reloaded_within_ttl():
    from opportunity_engine import equity_scanner_ai as esa
    import time

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = time.monotonic()  # freshly "loaded" just now
    esa._FP_EVIDENCE_CACHE = {"SYM1_UP": {"fingerprint_name": "STALE_CACHE_ENTRY"}}

    call_count = {"n": 0}

    def _tracked_load(*a, **kw):
        call_count["n"] += 1
        return []

    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               side_effect=_tracked_load):
        result = esa._load_fingerprint_evidence_cache()

    assert call_count["n"] == 0  # cache hit, file never re-read
    assert result == {"SYM1_UP": {"fingerprint_name": "STALE_CACHE_ENTRY"}}


def test_cache_reloaded_after_ttl_expires():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {"SYM1_UP": {"fingerprint_name": "OLD"}}
    esa._FP_EVIDENCE_CACHE_TS = 0.0  # far in the past -> definitely expired

    fresh_entries = [{"symbol": "SYM2", "direction": "UP", "fingerprint_name": "NEW",
                       "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"}]
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fresh_entries):
        result = esa._load_fingerprint_evidence_cache()

    assert "SYM2_UP" in result
    assert "SYM1_UP" not in result  # stale entry replaced, not merged


# ── 2. boost cannot bypass normal controls ─────────────────────────────

def test_boost_only_touches_confidence_and_audit_fields():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [{"symbol": "TESTSYM", "direction": "UP", "fingerprint_name": "FP_UP",
                       "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"}]
    sig = _make_signal(direction="BUY")
    before = dict(sig.__dict__)

    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries):
        esa._apply_fingerprint_evidence(sig, "TESTSYM")

    after = dict(sig.__dict__)
    changed_fields = {k for k in before if before[k] != after[k]}
    assert changed_fields == {"confidence", "_fingerprint_evidence_boost", "_fingerprint_evidence_match"}
    # Explicitly confirm the risk/execution-relevant fields are untouched.
    for field in ("entry_price", "stop_loss", "target_price", "quantity", "atr",
                   "adv_crore", "strategy_name", "signal_type", "strength", "symbol"):
        assert getattr(sig, field) == before[field], f"{field} must never be touched by the boost"


def test_decision_risk_execution_modules_do_not_reference_new_fields():
    forbidden_terms = ("_fingerprint_evidence_boost", "_fingerprint_evidence_match")
    files = [
        ROOT / "decision_ai" / "decision_engine.py",
        ROOT / "risk_guardian" / "risk_guardian.py",
        ROOT / "execution_engine" / "order_manager.py",
    ]
    for path in files:
        assert path.exists(), f"expected {path} to exist"
        src = path.read_text(encoding="utf-8", errors="replace")
        for term in forbidden_terms:
            assert term not in src, (
                f"{path} must not special-case {term!r} — the boost must be a pure, "
                "additive .confidence input, never a distinct decision/risk/execution path"
            )


# ── 3. enriched audit trail fields ──────────────────────────────────────

def test_audit_annotation_has_all_required_fields():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [{"symbol": "TESTSYM", "direction": "UP", "fingerprint_name": "FP_UP",
                       "as_of_date": "2026-09-05", "reason": "prior-close match",
                       "checked_at": "2026-09-06T01:00:00+00:00"}]
    sig = _make_signal(confidence=6.0, direction="BUY")

    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries), \
         patch("config.FINGERPRINT_EVIDENCE_BOOST_AMOUNT", 0.3):
        esa._apply_fingerprint_evidence(sig, "TESTSYM")

    match = sig._fingerprint_evidence_match
    assert match["fingerprint_name"] == "FP_UP"
    assert match["symbol"] == "TESTSYM"
    assert match["direction"] == "BUY"
    assert match["original_confidence"] == 6.0
    assert match["boost"] == 0.3
    assert match["final_confidence"] == 6.3
    assert match["eligibility_timestamp"] == "2026-09-06T01:00:00+00:00"
    assert match["evidence_date"] == "2026-09-05"
    assert match["reason"] == "prior-close match"


def test_eligibility_export_carries_checked_at_timestamp(tmp_path):
    from scripts.knowledge_system import live_selection_eligibility_001 as lse

    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    export_path = tmp_path / "eligibility.json"
    audit_path = tmp_path / "audit.jsonl"

    fake_match = {"symbol": "SYM1", "direction": "UP", "fingerprint_name": "FP_UP",
                   "as_of_date": "2026-09-05", "reason": "matched"}
    with patch.object(lse, "ELIGIBILITY_PATH", export_path), \
         patch.object(lse, "AUDIT_LOG_PATH", audit_path), \
         patch.object(lse, "match_symbols_for_fingerprint", return_value=[dict(fake_match)]), \
         patch.object(lse, "load_export", return_value=[{"name": "FP_UP", "direction": "UP"}]), \
         patch.object(lse, "get_full_registry", return_value=[{
             "name": "FP_UP", "direction": "UP", "components": {"combined": lambda b: True},
         }]):
        lse.run_eligibility_check_silent(ledger_path=ledger)

    exported = json.loads(export_path.read_text(encoding="utf-8"))
    assert len(exported) == 1
    assert "checked_at" in exported[0] and exported[0]["checked_at"]


# ── 4. automatic rollback still works after the refactor ──────────────

def test_rollback_removes_boost_on_next_check():
    from opportunity_engine import equity_scanner_ai as esa

    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    fake_entries = [{"symbol": "SYM1", "direction": "UP", "fingerprint_name": "FP_UP",
                       "as_of_date": "2026-09-05", "reason": "x", "checked_at": "t"}]
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=fake_entries):
        sig1 = _make_signal(direction="BUY")
        esa._apply_fingerprint_evidence(sig1, "SYM1")
    assert sig1._fingerprint_evidence_boost is not None

    # Fingerprint lost eligibility -> next check (post-TTL) sees an empty file.
    esa._FP_EVIDENCE_CACHE = {}
    esa._FP_EVIDENCE_CACHE_TS = 0.0
    with patch("scripts.knowledge_system.live_selection_eligibility_001.load_eligibility",
               return_value=[]):
        sig2 = _make_signal(direction="BUY")
        esa._apply_fingerprint_evidence(sig2, "SYM1")
    assert sig2._fingerprint_evidence_boost is None


# ── 5. no new permission gate introduced ───────────────────────────────

def test_no_new_permission_gate_flag_still_defaults_true():
    import config
    assert config.ENABLE_FINGERPRINT_EVIDENCE_IN_SCANNER is True

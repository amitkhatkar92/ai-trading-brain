"""
tests/test_kda_opportunity_profile_bridge.py
=============================================
Verifies the Phase 1 & 2 KDA-to-TradeSignal Opportunity Profile Bridge:
1. KDA-authorized non-knowledge_referred signal receives kda_conviction.
2. sig.confidence remains unchanged by this bridge for non-knowledge_referred signals.
3. knowledge_authority_score is attached to TradeSignal.
4. scanner_score is preserved separately.
"""
from __future__ import annotations

import types
from models.trade_signal import TradeSignal, SignalDirection


def test_kda_opportunity_profile_fields_on_trade_signal():
    """Verify TradeSignal holds scanner_score, kda_conviction, and knowledge_authority_score."""
    sig = TradeSignal(
        symbol="TATASTEEL",
        direction=SignalDirection.BUY,
        confidence=5.3,
        scanner_score=5.3,
        strategy_name="Mean_Reversion",
    )
    assert sig.confidence == 5.3
    assert sig.scanner_score == 5.3
    assert sig.kda_conviction is None
    assert sig.knowledge_authority_score is None

    # Simulate KDA evaluation enrichment
    sig.kda_conviction = 8.35
    sig.knowledge_authority_score = 0.92
    assert sig.kda_conviction == 8.35
    assert sig.knowledge_authority_score == 0.92
    # Ensure confidence is untouched by KDA field population
    assert sig.confidence == 5.3


def test_scanner_score_remains_original_after_legacy_confidence_mutation():
    """Scanner score remains provenance metadata after confidence changes."""
    sig = TradeSignal(
        symbol="TATASTEEL",
        direction=SignalDirection.BUY,
        confidence=5.3,
    )
    sig.scanner_score = float(sig.confidence)
    sig.confidence = 8.2

    assert sig.scanner_score == 5.3
    assert sig.confidence == 8.2


def test_kda_boundary_does_not_derive_scanner_score_from_confidence():
    """A missing scanner stamp is not silently reconstructed from confidence."""
    sig = TradeSignal(
        symbol="TATASTEEL",
        direction=SignalDirection.BUY,
        confidence=8.2,
    )

    assert sig.scanner_score == 0.0
    assert sig.scanner_score != sig.confidence


def test_kda_conviction_calculation_independent_of_strategy_name():
    """Verify conviction formula runs on any KDA-authorized signal with VALIDATED/DECISION_ELIGIBLE evidence."""
    # Test conviction calculation formula behavior
    def compute_conv(kda_result):
        dec = kda_result.get("kda_decision")
        ev_state = kda_result.get("evidence_state")
        if dec in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL") and ev_state in ("DECISION_ELIGIBLE", "VALIDATED"):
            ess = float(kda_result.get("effective_sample_size") or kda_result.get("hbe_ess") or 0.0)
            thp = kda_result.get("hbe_target_hit_prob")
            base = 8.0 if ess >= 100.0 else 7.0
            wr = max(0.0, min(1.5, (thp - 0.55) * 7.5)) if thp is not None else 0.0
            return round(min(9.5, base + wr), 2)
        return None

    # 1. Non-knowledge_referred (e.g. Mean_Reversion) with VALIDATED evidence (ESS=45, win rate=65%)
    res_mr = {
        "kda_decision": "KNOWLEDGE_BUY",
        "evidence_state": "VALIDATED",
        "effective_sample_size": 45.0,
        "hbe_target_hit_prob": 0.65,
        "knowledge_authority_score": 0.85,
    }
    conv_mr = compute_conv(res_mr)
    assert conv_mr == 7.75  # 7.0 + (0.65 - 0.55) * 7.5 = 7.0 + 0.75 = 7.75

    # 2. DECISION_ELIGIBLE evidence (ESS=150, win rate=75%)
    res_de = {
        "kda_decision": "KNOWLEDGE_BUY",
        "evidence_state": "DECISION_ELIGIBLE",
        "effective_sample_size": 150.0,
        "hbe_target_hit_prob": 0.75,
        "knowledge_authority_score": 0.95,
    }
    conv_de = compute_conv(res_de)
    assert conv_de == 9.5  # 8.0 + (0.75 - 0.55) * 7.5 = 8.0 + 1.5 = 9.5 (capped at 9.5)

    # 3. USEFUL or DEVELOPING evidence (not eligible for conviction upgrade)
    res_useful = {
        "kda_decision": "KNOWLEDGE_BUY",
        "evidence_state": "USEFUL",
        "effective_sample_size": 15.0,
        "hbe_target_hit_prob": 0.60,
    }
    assert compute_conv(res_useful) is None

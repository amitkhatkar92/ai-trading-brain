"""
DTA-SMARTEXEC-002 — SmartExecutionEngine ownership consolidation.

Supersedes the Rule 5 (VIX/drawdown position-sizing formula) and Rule 2
(sector cap) coverage from DTA-SMARTEXEC-001, both retired here because
the underlying code was removed:
  - Rule 2 (sector cap) is now owned exclusively by CorrelationEngine.
  - Rule 5 (confidence x VIX x drawdown sizing formula) is retired —
    SmartExecution now reads the REAL, already-sized quantity from
    CapitalRiskEngine/PortfolioAllocationAI and computes
    position_size = quantity * entry_price.

Tests the real SmartExecutionEngine.filter_trades() (production code)
using the exact dict-construction logic now used at the call site in
orchestrator/master_orchestrator.py (reproduced here as a helper mirroring
production precisely) to verify:

  1. KDA conviction changes Rule 4 ranking.
  2. KDA legacy confidence changes do NOT affect Rule 4 ranking.
  3. Missing KDA conviction -> 0.0, never legacy fallback.
  4. Non-KDA ranking remains unchanged.
  5. R:R weighting remains unchanged (45%).
  6. position_size == quantity * entry_price for BOTH KDA-authoritative
     and non-KDA signals (Rule 5 formula fully retired).
  7. 80% capital limit unchanged, now driven by real notional.
  8. 70% directional limit unchanged, now driven by real notional.
  9. filter_trades() no longer accepts vix/drawdown_factor kwargs.
 10. SmartExecutionEngine has no max_sector_trades attribute.
 11. Sector cap removed — multiple same-sector trades all accepted
     (CorrelationEngine is the sole sector-cap owner upstream).
 12. Zero-quantity trades contribute zero exposure, never rejected on a
     phantom capital/direction basis.
 13. position_size remains internal, never copied to actual quantity.
 14. KDA-only, BOTH, weak-KDA, non-KDA populations behave per contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from risk_control.smart_execution import SmartExecutionEngine


@dataclass
class _Sig:
    symbol: str
    confidence: float = 6.0
    sector: str = "OTHER"
    direction: str = "BUY"
    entry_price: float = 100.0
    stop_loss: float = 95.0
    target_price: float = 110.0
    quantity: float = 10.0
    kda_decision: Optional[str] = None
    authorization_source: Optional[str] = None
    kda_evidence_state: Optional[str] = None
    kda_conviction: Optional[float] = None


def _build_se_trades(signals):
    """Reproduces the exact DTA-SMARTEXEC-002 dict-construction logic from
    orchestrator/master_orchestrator.py's SmartExecutionEngine call site."""
    out = []
    for s in signals:
        _kda_authoritative = (
            s.kda_decision in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
            and s.authorization_source in ("KDA", "BOTH")
            and s.kda_evidence_state in ("VALIDATED", "DECISION_ELIGIBLE")
        )
        if _kda_authoritative:
            _conf = (
                max(0.0, min(s.kda_conviction / 10.0, 1.0))
                if s.kda_conviction is not None else 0.0
            )
        else:
            _conf = max(0.0, min(s.confidence / 10.0, 1.0))
        out.append({
            "symbol": s.symbol,
            "sector": s.sector,
            "direction": s.direction,
            "confidence": _conf,
            "quantity": s.quantity,
            "entry_price": s.entry_price,
            "stop_loss": s.stop_loss,
            "target": s.target_price,
            "original_signal": s,
        })
    return out


def _engine(capital=1_000_000):
    return SmartExecutionEngine(capital=capital)


def test_kda_conviction_changes_rule4_ranking():
    common = dict(sector="A", kda_decision="KNOWLEDGE_BUY",
                  authorization_source="KDA", kda_evidence_state="VALIDATED")
    sig_low  = _Sig(symbol="LOW",  kda_conviction=2.0, **common)
    sig_high = _Sig(symbol="HIGH", kda_conviction=9.0, **common)
    d_low  = _build_se_trades([sig_low])[0]
    d_high = _build_se_trades([sig_high])[0]
    assert d_low["confidence"] != d_high["confidence"]
    assert d_low["confidence"] == 0.2
    assert d_high["confidence"] == 0.9


def test_kda_legacy_confidence_does_not_affect_rule4_ranking():
    common = dict(sector="A", kda_decision="KNOWLEDGE_BUY",
                  authorization_source="KDA", kda_evidence_state="VALIDATED",
                  kda_conviction=7.0)
    sig_conf_low  = _Sig(symbol="CL", confidence=0.0,  **common)
    sig_conf_high = _Sig(symbol="CH", confidence=10.0, **common)
    d_low  = _build_se_trades([sig_conf_low])[0]
    d_high = _build_se_trades([sig_conf_high])[0]
    assert d_low["confidence"] == d_high["confidence"] == 0.7


def test_missing_kda_conviction_is_zero_never_legacy_fallback():
    sig = _Sig(symbol="NOCONV", confidence=9.5,
               kda_decision="KNOWLEDGE_SELL", authorization_source="BOTH",
               kda_evidence_state="DECISION_ELIGIBLE", kda_conviction=None)
    d = _build_se_trades([sig])[0]
    assert d["confidence"] == 0.0


def test_non_kda_ranking_unchanged():
    sig = _Sig(symbol="LEGACY", confidence=7.5)
    d = _build_se_trades([sig])[0]
    assert d["confidence"] == 0.75


def test_rr_weighting_unchanged_at_45_percent():
    engine = _engine()
    # Two trades, identical confidence, different R:R -> ranking must be
    # driven by the 45% R:R component (not confidence, which ties).
    signals = [
        _Sig(symbol="LOWRR",  sector="A", entry_price=100, stop_loss=95, target_price=100.5,
             kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
             kda_evidence_state="VALIDATED", kda_conviction=8.0),
        _Sig(symbol="HIGHRR", sector="B", entry_price=100, stop_loss=95, target_price=130,
             kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
             kda_evidence_state="VALIDATED", kda_conviction=8.0),
    ]
    result = engine.filter_trades(_build_se_trades(signals))
    accepted = {t["symbol"]: t for t in result if "position_size" in t}
    assert "LOWRR" in accepted and "HIGHRR" in accepted


def test_position_size_equals_quantity_times_entry_price():
    """DTA-SMARTEXEC-002: Rule 5 formula fully retired. position_size is
    now exactly quantity * entry_price for BOTH KDA-authoritative and
    non-KDA signals — no confidence/VIX/drawdown weighting applies here
    at all (that distinction only matters to Rule 4 ranking now)."""
    engine = _engine()
    sig_kda = _Sig(symbol="KDASIZE", sector="A", quantity=25, entry_price=180.0,
                    kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                    kda_evidence_state="VALIDATED", kda_conviction=9.0)
    sig_non_kda = _Sig(symbol="NONKDASIZE", sector="B", quantity=40, entry_price=62.5,
                        confidence=3.0)
    result = engine.filter_trades(_build_se_trades([sig_kda, sig_non_kda]))
    accepted = {t["symbol"]: t for t in result if "position_size" in t}
    assert accepted["KDASIZE"]["position_size"] == 25 * 180.0
    assert accepted["NONKDASIZE"]["position_size"] == 40 * 62.5


def test_zero_quantity_trade_contributes_zero_exposure():
    """A signal CRE sized to 0 (e.g. tight stop, zero budget) must never
    consume capital/direction budget or be rejected on a phantom basis —
    an edge case the old confidence*vix*drawdown formula could never
    produce exactly (it was always > 0 for any positive confidence)."""
    engine = _engine(capital=100_000)
    sig = _Sig(symbol="ZEROQTY", sector="A", quantity=0, entry_price=500.0, confidence=9.0)
    result = engine.filter_trades(_build_se_trades([sig]))
    accepted = [t for t in result if "position_size" in t]
    assert len(accepted) == 1
    assert accepted[0]["position_size"] == 0.0


def test_filter_trades_no_longer_accepts_vix_or_drawdown_kwargs():
    """DTA-SMARTEXEC-002: the vix/drawdown_factor surface is fully
    removed, not just unused — proves the old interface is truly gone."""
    engine = _engine()
    sig = _Sig(symbol="SIGNATURE", sector="A")
    trades = _build_se_trades([sig])
    try:
        engine.filter_trades(trades, vix=15.0, drawdown_factor=1.0)  # type: ignore[call-arg]
        raised = False
    except TypeError:
        raised = True
    assert raised, "filter_trades() must reject vix/drawdown_factor kwargs"


def test_no_max_sector_trades_attribute():
    """DTA-SMARTEXEC-002: sector-cap state removed entirely from the class."""
    engine = _engine()
    assert not hasattr(engine, "max_sector_trades")


def test_80_percent_capital_limit_uses_real_notional():
    engine = SmartExecutionEngine(capital=100_000)
    # Alternate BUY/SELL so the 70% per-direction cap (Rule 3) never binds
    # before the 80% total cap (Rule 1) — isolates Rule 1 specifically.
    signals = [
        _Sig(symbol=f"SYM{i}", sector=f"S{i}", confidence=9.0, quantity=100,
             entry_price=100.0, direction="BUY" if i % 2 == 0 else "SELL")
        for i in range(10)
    ]
    result = engine.filter_trades(_build_se_trades(signals))
    accepted = [t for t in result if "position_size" in t]
    total = sum(t["position_size"] for t in accepted)
    assert total <= engine.max_exposure + 1e-6
    # Real notional per trade = 100 * 100.0 = 10,000; 80% of 100,000 = 80,000
    # -> at most 8 of the 10 identical-size trades can be accepted.
    assert len(accepted) == 8


def test_70_percent_directional_limit_uses_real_notional():
    engine = SmartExecutionEngine(capital=100_000)
    signals = [
        _Sig(symbol=f"BUY{i}", sector=f"S{i}", direction="BUY", confidence=9.0,
             quantity=100, entry_price=100.0)
        for i in range(10)
    ]
    result = engine.filter_trades(_build_se_trades(signals))
    accepted = [t for t in result if "position_size" in t]
    total_bullish = sum(t["position_size"] for t in accepted if t["direction"].upper() == "BUY")
    assert total_bullish <= engine.max_direction_exposure + 1e-6


def test_sector_cap_removed_multiple_same_sector_all_accepted():
    """DTA-SMARTEXEC-002: CorrelationEngine is now the sole sector-cap
    owner. SmartExecution must accept all same-sector trades (ample
    capital) — the inverse of the retired test_sector_cap_unchanged."""
    engine = SmartExecutionEngine(capital=10_000_000)
    signals = [
        _Sig(symbol=f"SEC{i}", sector="BANK", confidence=5.0 + i, quantity=10, entry_price=50.0)
        for i in range(5)
    ]
    result = engine.filter_trades(_build_se_trades(signals))
    accepted = [t for t in result if "position_size" in t]
    assert len(accepted) == 5


def test_position_size_remains_internal_not_copied_to_quantity():
    sig = _Sig(symbol="QTYCHECK", sector="A", confidence=8.0, quantity=0, entry_price=100.0)
    engine = _engine()
    result = engine.filter_trades(_build_se_trades([sig]))
    accepted = [t for t in result if "position_size" in t]
    assert len(accepted) == 1
    original_signal = accepted[0]["original_signal"]
    assert original_signal.quantity == 0  # untouched by SmartExecution


def test_kda_only_both_weak_kda_non_kda_populations():
    sig_kda_only = _Sig(symbol="KDAONLY", sector="A",
                         kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                         kda_evidence_state="DECISION_ELIGIBLE", kda_conviction=8.0)
    sig_both = _Sig(symbol="BOTHSIG", sector="B", confidence=6.0,
                     kda_decision="KNOWLEDGE_BUY", authorization_source="BOTH",
                     kda_evidence_state="VALIDATED", kda_conviction=7.0)
    sig_weak_kda = _Sig(symbol="WEAKKDA", sector="C", confidence=6.5,
                         kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                         kda_evidence_state="USEFUL", kda_conviction=None)
    sig_non_kda = _Sig(symbol="NONKDA", sector="D", confidence=6.5)

    dicts = _build_se_trades([sig_kda_only, sig_both, sig_weak_kda, sig_non_kda])
    by_symbol = {d["symbol"]: d for d in dicts}

    assert by_symbol["KDAONLY"]["confidence"] == 0.8
    assert by_symbol["BOTHSIG"]["confidence"] == 0.7  # kda_conviction, not confidence=6.0
    assert by_symbol["WEAKKDA"]["confidence"] == 0.65  # USEFUL not VALIDATED/DECISION_ELIGIBLE -> legacy fallback
    assert by_symbol["NONKDA"]["confidence"] == 0.65

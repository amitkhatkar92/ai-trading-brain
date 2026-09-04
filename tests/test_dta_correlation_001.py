"""
DTA-CORRELATION-001 — CorrelationEngine KDA-aware confidence input fix.

Tests the real CorrelationEngine.reduce_correlation() (production code, not
a simulation) combined with the exact dict-construction logic now used at
the call site in orchestrator/master_orchestrator.py (reproduced here as a
small helper mirroring the production code precisely) to verify:

  1. KDA-authoritative confidence 0 vs 10 identity (legacy field has no
     authority once a signal is KDA-authoritative).
  2. Legacy (non-KDA) signal ranking behavior unchanged (existing docstring
     example: ICICI 0.9 > HDFC 0.8, sector cap keeps top 2).
  3. KDA-authoritative signal with missing kda_conviction -> neutral 0.0,
     never falls back to legacy confidence.
  4. Sector cap (max 2 per sector) behavior completely unchanged.
  5. Mixed KDA + legacy signals in the same sector rank correctly on a
     common 0-1 scale.
  6. Full pipeline dict-shape/keys unaffected by the fix.
  7. KDA-authoritative signal: legacy confidence 2 -> 10 must produce an
     IDENTICAL CorrelationEngine ranking (legacy confidence has no
     authority at this stage).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from risk_control.correlation_engine import CorrelationEngine


@dataclass
class _Sig:
    symbol: str
    confidence: float = 6.0
    sector: str = "OTHER"
    direction: str = "BUY"
    kda_decision: Optional[str] = None
    authorization_source: Optional[str] = None
    kda_evidence_state: Optional[str] = None
    kda_conviction: Optional[float] = None


def _build_corr_dicts(signals):
    """Reproduces the exact DTA-CORRELATION-001 dict-construction logic
    from orchestrator/master_orchestrator.py's call site."""
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
            "_original_signal": s,
        })
    return out


def test_kda_authoritative_confidence_0_and_10_identical_ranking():
    common = dict(sector="BANK", kda_decision="KNOWLEDGE_BUY",
                  authorization_source="KDA", kda_evidence_state="VALIDATED",
                  kda_conviction=8.0)
    sig_low  = _Sig(symbol="LOW",  confidence=0.0,  **common)
    sig_high = _Sig(symbol="HIGH", confidence=10.0, **common)

    engine = CorrelationEngine(max_per_sector=2)
    dicts_low  = _build_corr_dicts([sig_low])
    dicts_high = _build_corr_dicts([sig_high])
    assert dicts_low[0]["confidence"] == dicts_high[0]["confidence"]

    out_low  = engine.reduce_correlation(dicts_low)
    out_high = engine.reduce_correlation(dicts_high)
    assert out_low[0]["confidence"] == out_high[0]["confidence"]


def test_legacy_ranking_behavior_unchanged_docstring_example():
    # Use symbols with a single, unambiguous DEFAULT_SECTOR_MAP entry each
    # (some symbols like "HDFC"/"AXIS" appear twice in the production map
    # under different sectors due to dict-literal key collisions — a
    # pre-existing quirk out of scope for this fix; avoided here for a
    # deterministic test).
    signals = [
        _Sig(symbol="SBIN",     confidence=8.0, sector="BANK"),
        _Sig(symbol="KOTAK",    confidence=9.0, sector="BANK"),
        _Sig(symbol="INDUSIND", confidence=7.0, sector="BANK"),
        _Sig(symbol="INFY",     confidence=8.5, sector="IT"),
        _Sig(symbol="TCS",      confidence=7.5, sector="IT"),
    ]
    engine = CorrelationEngine(max_per_sector=2)
    result = engine.reduce_correlation(_build_corr_dicts(signals))
    kept_symbols = {r["symbol"] for r in result}
    assert kept_symbols == {"KOTAK", "SBIN", "INFY", "TCS"}
    assert "INDUSIND" not in kept_symbols  # lowest confidence in BANK, dropped


def test_kda_authoritative_missing_conviction_is_neutral_not_legacy_fallback():
    sig = _Sig(symbol="NOCONV", confidence=9.5, sector="BANK",
               kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
               kda_evidence_state="VALIDATED", kda_conviction=None)
    d = _build_corr_dicts([sig])
    assert d[0]["confidence"] == 0.0


def test_sector_cap_unchanged():
    signals = [_Sig(symbol=f"BANK{i}", confidence=5.0 + i, sector="BANK")
               for i in range(5)]
    engine = CorrelationEngine(max_per_sector=2)
    result = engine.reduce_correlation(_build_corr_dicts(signals))
    assert len(result) == 2


def test_mixed_kda_and_legacy_signals_rank_on_common_scale():
    sig_kda = _Sig(symbol="KDASIG", sector="BANK",
                    kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                    kda_evidence_state="VALIDATED", kda_conviction=9.0)
    sig_legacy_strong = _Sig(symbol="LEGSTRONG", confidence=9.5, sector="BANK")
    sig_legacy_weak = _Sig(symbol="LEGWEAK", confidence=3.0, sector="BANK")
    engine = CorrelationEngine(max_per_sector=2)
    result = engine.reduce_correlation(
        _build_corr_dicts([sig_kda, sig_legacy_strong, sig_legacy_weak])
    )
    kept = {r["symbol"] for r in result}
    assert kept == {"LEGSTRONG", "KDASIG"}
    assert "LEGWEAK" not in kept


def test_dict_shape_unaffected():
    sig = _Sig(symbol="SHAPE", confidence=6.0, sector="IT")
    d = _build_corr_dicts([sig])[0]
    assert set(d.keys()) == {"symbol", "sector", "direction", "confidence", "_original_signal"}


def test_kda_authoritative_legacy_confidence_2_to_10_identical_ranking():
    """Explicit refinement test: legacy confidence has NO authority at this
    stage once a signal is KDA-authoritative."""
    common = dict(sector="IT", kda_decision="KNOWLEDGE_SELL",
                  authorization_source="BOTH", kda_evidence_state="DECISION_ELIGIBLE",
                  kda_conviction=7.5)
    sig_conf2  = _Sig(symbol="CONF2",  confidence=2.0,  **common)
    sig_conf10 = _Sig(symbol="CONF10", confidence=10.0, **common)

    engine = CorrelationEngine(max_per_sector=2)
    out2  = engine.reduce_correlation(_build_corr_dicts([sig_conf2]))
    out10 = engine.reduce_correlation(_build_corr_dicts([sig_conf10]))
    assert out2[0]["confidence"] == out10[0]["confidence"] == 0.75

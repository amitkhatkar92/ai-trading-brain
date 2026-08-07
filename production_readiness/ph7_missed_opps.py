"""
production_readiness/ph7_missed_opps.py — Phase 7: Missed Opportunity Classification.

Classifies each missed market move into one of 8 categories:
    1. Correctly_Ignored      — risk/fundamental reason; no learning needed
    2. Universe_Limitation    — symbol not in scanning universe
    3. Knowledge_Limitation   — symbol was in universe but IIOS lacked DNA/edge knowledge
    4. Research_Limitation    — hypothesis exists but not yet validated
    5. Threshold_Limitation   — signal generated but confidence was just below gate
    6. Risk_Limitation        — risk rules blocked an otherwise valid signal
    7. Portfolio_Limitation   — position limits/allocation prevented the trade
    8. External_Event         — macro event or news; IIOS correctly had no signal

Categories 3, 4, 5 trigger learning (additional study plan items).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .prr_config import (
    DATA,
    LEARNING_TRIGGERING_MISSES,
    MISS_CORRECTLY_IGNORED,
    MISS_EXTERNAL_EVENT,
    MISS_KNOWLEDGE_LIMITATION,
    MISS_PORTFOLIO_LIMITATION,
    MISS_RESEARCH_LIMITATION,
    MISS_RISK_LIMITATION,
    MISS_THRESHOLD_LIMITATION,
    MISS_UNIVERSE_LIMITATION,
    DNA_DB,
)
from .prr_models import MissClassification, MissedOpportunityReport

log = logging.getLogger(__name__)

_UNIVERSE_FILE = DATA / "nifty500_universe.json"
_HYP_REGISTRY  = DATA / "ars_hypothesis_registry.json"
_EDGES_FILE    = DATA / "discovered_edges.json"


def _in_universe(symbol: str) -> bool:
    """Check if symbol is in nifty500_universe.json."""
    try:
        raw = json.loads(_UNIVERSE_FILE.read_text(encoding="utf-8"))
        universe_symbols = {
            (e.get("symbol") or "").strip().upper()
            for e in raw if isinstance(e, dict)
        }
        return symbol.upper() in universe_symbols
    except Exception:
        return False


def _has_dna_coverage(symbol: str) -> bool:
    """
    DNA is feature-based (not per-symbol).
    Treat as coverage exists if ANY loser/winner DNA is INSTITUTIONAL.
    """
    try:
        if not DNA_DB.exists():
            return False
        with sqlite3.connect(DNA_DB) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM dna WHERE lifecycle='INSTITUTIONAL' AND is_current=1"
            ).fetchone()[0]
        return count > 0
    except Exception:
        return False


def _has_active_hypothesis() -> bool:
    """Check if any CONFIRMED/ACTIVE hypothesis exists."""
    try:
        reg = json.loads(_HYP_REGISTRY.read_text(encoding="utf-8"))
        hyps = reg.get("hypotheses", {})
        return any(
            h.get("status") in ("CONFIRMED", "ACTIVE")
            for h in hyps.values()
        )
    except Exception:
        return False


def classify_single_miss(
    symbol: str,
    move_pct: float,
    direction: str = "UP",
    was_in_universe: Optional[bool] = None,
    had_signal: bool = False,
    signal_confidence: float = 0.0,
    confidence_gate: float = 6.8,
    was_risk_blocked: bool = False,
    was_portfolio_blocked: bool = False,
    is_external_event: bool = False,
    context: Optional[Dict[str, Any]] = None,
) -> MissClassification:
    """Classify a single missed opportunity into one of 8 categories."""
    context = context or {}
    evidence: List[str] = []

    # 1. External event — macro catalyst not predictable from IIOS knowledge
    if is_external_event:
        evidence.append("Macro/news-driven move: IIOS correctly had no signal")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_EXTERNAL_EVENT,
            triggers_learning=False,
            evidence=evidence,
        )

    # 2. Portfolio limit — valid signal was blocked by portfolio allocation
    if was_portfolio_blocked:
        evidence.append("Max position limit or sector allocation cap prevented entry")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_PORTFOLIO_LIMITATION,
            triggers_learning=False,
            evidence=evidence,
        )

    # 3. Risk rule block — risk management correctly prevented the entry
    if was_risk_blocked:
        evidence.append("RiskManagerAI or PortfolioAllocation blocked the order")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_RISK_LIMITATION,
            triggers_learning=False,
            evidence=evidence,
        )

    # 4. Signal generated but confidence just below gate
    if had_signal and signal_confidence > 0 and signal_confidence < confidence_gate:
        evidence.append(f"Signal confidence={signal_confidence:.1f} was below gate={confidence_gate:.1f}")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_THRESHOLD_LIMITATION,
            triggers_learning=True,
            evidence=evidence,
            detail=f"Consider: review confidence gate or add supporting DNA evidence",
        )

    # 5. Not in universe at all
    in_universe = was_in_universe if was_in_universe is not None else _in_universe(symbol)
    if not in_universe:
        evidence.append(f"{symbol} was not in nifty500_universe.json scanning universe")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_UNIVERSE_LIMITATION,
            triggers_learning=False,
            evidence=evidence,
        )

    # 6. In universe, has DNA, but IIOS didn't pick up the move
    if _has_dna_coverage(symbol):
        evidence.append(f"{symbol} was in universe; institutional DNA exists but did not generate signal")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_KNOWLEDGE_LIMITATION,
            triggers_learning=True,
            evidence=evidence,
            detail=f"Triggers study: why did loser/winner DNA not predict this {direction} move?",
        )

    # 7. In universe but no validated hypothesis covers this pattern
    if _has_active_hypothesis():
        evidence.append(f"{symbol} in universe; existing hypothesis didn't cover this pattern")
        return MissClassification(
            symbol=symbol, move_pct=move_pct, direction=direction,
            classification=MISS_RESEARCH_LIMITATION,
            triggers_learning=True,
            evidence=evidence,
            detail=f"Triggers study: new hypothesis required to cover {direction} move",
        )

    # 8. Default: correctly ignored based on available knowledge
    evidence.append("No competing signal, risk block, or knowledge gap — IIOS correctly passed")
    return MissClassification(
        symbol=symbol, move_pct=move_pct, direction=direction,
        classification=MISS_CORRECTLY_IGNORED,
        triggers_learning=False,
        evidence=evidence,
    )


def classify_all_misses(
    misses: List[Dict[str, Any]],
    confidence_gate: float = 6.8,
) -> List[MissClassification]:
    """
    Classify a list of missed opportunities.
    Each miss dict: {symbol, move_pct, direction, context, ...optional flags}
    """
    return [
        classify_single_miss(
            symbol             = m.get("symbol", "?"),
            move_pct           = m.get("move_pct", 0.0),
            direction          = m.get("direction", "UP"),
            was_in_universe    = m.get("in_universe"),
            had_signal         = m.get("had_signal", False),
            signal_confidence  = m.get("signal_confidence", 0.0),
            confidence_gate    = confidence_gate,
            was_risk_blocked   = m.get("risk_blocked", False),
            was_portfolio_blocked = m.get("portfolio_blocked", False),
            is_external_event  = m.get("external_event", False),
            context            = m.get("context", {}),
        )
        for m in misses
    ]


def build_missed_opportunity_report(
    misses: List[Dict[str, Any]],
    today: Optional[str] = None,
    confidence_gate: float = 6.8,
) -> MissedOpportunityReport:
    """Classify all misses and aggregate into a report."""
    today         = today or datetime.now().date().isoformat()
    classifications = classify_all_misses(misses, confidence_gate)

    counts: Dict[str, int] = {
        MISS_CORRECTLY_IGNORED:   0,
        MISS_UNIVERSE_LIMITATION: 0,
        MISS_KNOWLEDGE_LIMITATION: 0,
        MISS_RESEARCH_LIMITATION: 0,
        MISS_THRESHOLD_LIMITATION: 0,
        MISS_RISK_LIMITATION:     0,
        MISS_PORTFOLIO_LIMITATION: 0,
        MISS_EXTERNAL_EVENT:      0,
    }
    for c in classifications:
        counts[c.classification] = counts.get(c.classification, 0) + 1

    trigger_count = sum(1 for c in classifications if c.triggers_learning)

    return MissedOpportunityReport(
        date=today,
        total_misses=len(classifications),
        correctly_ignored   = counts[MISS_CORRECTLY_IGNORED],
        universe_limitation = counts[MISS_UNIVERSE_LIMITATION],
        knowledge_limitation= counts[MISS_KNOWLEDGE_LIMITATION],
        research_limitation = counts[MISS_RESEARCH_LIMITATION],
        threshold_limitation= counts[MISS_THRESHOLD_LIMITATION],
        risk_limitation     = counts[MISS_RISK_LIMITATION],
        portfolio_limitation= counts[MISS_PORTFOLIO_LIMITATION],
        external_event      = counts[MISS_EXTERNAL_EVENT],
        triggers_learning   = trigger_count,
        classifications     = classifications,
    )

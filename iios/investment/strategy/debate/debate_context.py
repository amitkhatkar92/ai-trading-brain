"""iios/investment/strategy/debate/debate_context.py
DebateContext — the full input to a debate session.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class StrategyDebateInput:
    """Minimal strategy information needed to seed the debate."""
    strategy_id:   str
    strategy_name: str
    category:      str
    direction:     str                # BUY / SELL / NEUTRAL
    min_rr:        float
    max_loss_pct:  float
    extra:         Dict[str, Any]     = field(default_factory=dict)


@dataclass
class OpportunityDebateInput:
    """The opportunity being evaluated."""
    opportunity_id:  str
    symbol:          str
    asset_class:     str
    entry_price:     float
    target_price:    Optional[float]  = None
    stop_price:      Optional[float]  = None
    holding_period:  str              = "intraday"
    extra:           Dict[str, Any]   = field(default_factory=dict)


@dataclass
class MarketSnapshot:
    """Current market snapshot for context."""
    regime:           str                  = "unknown"
    nifty_level:      Optional[float]      = None
    nifty_change_pct: Optional[float]      = None
    vix:              Optional[float]      = None
    sector:           str                  = "unknown"
    sector_trend:     str                  = "neutral"
    breadth_score:    Optional[float]      = None
    timestamp:        Optional[datetime]   = None
    extra:            Dict[str, Any]       = field(default_factory=dict)


@dataclass
class DebateContext:
    """
    Complete context for one debate session.
    Passed to all participants and the orchestrator.
    """
    context_id:  str                        = field(default_factory=lambda: str(uuid.uuid4()))
    strategy:    Optional[StrategyDebateInput]     = None
    opportunity: Optional[OpportunityDebateInput]  = None
    market:      Optional[MarketSnapshot]          = None
    metadata:    Dict[str, Any]             = field(default_factory=dict)
    created_at:  datetime                   = field(default_factory=lambda: datetime.now(timezone.utc))

    # Pre-loaded external data (injected by EvidenceCollector before debate starts)
    pre_loaded_evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":   self.context_id,
            "strategy":     _asdict(self.strategy),
            "opportunity":  _asdict(self.opportunity),
            "market":       _asdict(self.market),
            "metadata":     self.metadata,
            "created_at":   self.created_at.isoformat(),
            "evidence_count": len(self.pre_loaded_evidence),
        }

    @property
    def symbol(self) -> str:
        return self.opportunity.symbol if self.opportunity else "UNKNOWN"

    @property
    def strategy_name(self) -> str:
        return self.strategy.strategy_name if self.strategy else "UNKNOWN"


def _asdict(obj) -> Optional[Dict]:
    if obj is None:
        return None
    import dataclasses
    if dataclasses.is_dataclass(obj):
        result = {}
        for f in dataclasses.fields(obj):
            val = getattr(obj, f.name)
            if isinstance(val, datetime):
                result[f.name] = val.isoformat()
            else:
                result[f.name] = val
        return result
    return None

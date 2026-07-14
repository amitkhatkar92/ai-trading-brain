"""iios/investment/strategy/migration/legacy_metadata.py
Metadata structures for legacy strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class LegacyStrategySource(str, Enum):
    """Where the legacy strategy definition came from."""
    STRATEGY_GENERATOR  = "strategy_generator"   # STRATEGY_PARAMS in strategy_generator_ai.py
    META_CONTROLLER     = "meta_controller"       # _REGIME_MAP in meta_strategy_controller.py
    DISCOVERED_EDGES    = "discovered_edges"      # data/discovered_edges.json
    EVOLVED_STRATEGIES  = "evolved_strategies"    # data/evolved_strategies.json
    MANUAL              = "manual"                # manually registered
    UNKNOWN             = "unknown"


class LegacyStrategyType(str, Enum):
    """Structural type of the legacy strategy."""
    CODE_BASED   = "code_based"    # defined in Python code (STRATEGY_PARAMS)
    JSON_BASED   = "json_based"    # defined in JSON (discovered_edges / evolved)
    HYBRID       = "hybrid"        # both code + JSON components
    PATTERN_ONLY = "pattern_only"  # decision-tree / entry-condition only


class LegacyHealthStatus(str, Enum):
    """Operational health of a legacy strategy."""
    ACTIVE    = "active"
    DECAYING  = "decaying"
    SUSPENDED = "suspended"
    ARCHIVED  = "archived"
    UNKNOWN   = "unknown"


@dataclass
class EntryCondition:
    """A single entry condition from a discovered edge strategy."""
    feature:   str
    operator:  str   # ">", ">=", "<", "<=", "==", "!="
    threshold: float

    def evaluate(self, features: Dict[str, float]) -> Optional[bool]:
        """Evaluate against a feature dict. Returns None if feature missing."""
        val = features.get(self.feature)
        if val is None:
            return None
        ops = {
            ">":  val > self.threshold,
            ">=": val >= self.threshold,
            "<":  val < self.threshold,
            "<=": val <= self.threshold,
            "==": val == self.threshold,
            "!=": val != self.threshold,
        }
        return ops.get(self.operator, False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature":   self.feature,
            "operator":  self.operator,
            "threshold": self.threshold,
        }


@dataclass
class LegacyStrategyMetadata:
    """
    Complete metadata record for a discovered legacy strategy.
    Immutable once constructed — mutations require a new record.
    """
    strategy_id:    str
    strategy_name:  str
    source:         LegacyStrategySource
    strategy_type:  LegacyStrategyType

    # Parameters (from STRATEGY_PARAMS or JSON)
    min_rr:         float = 2.0
    max_loss_pct:   float = 0.02
    stop_loss_pct:  float = 0.02
    target_multiplier: float = 2.0

    # Classification
    base_strategy:  str = ""          # for evolved/edge variants
    category:       str = "unknown"   # composite, volatility, macro, etc.
    direction:      str = "BUY"       # BUY / SELL / NEUTRAL

    # Performance (from JSON, if available)
    precision:          Optional[float] = None   # hit rate
    support:            Optional[int]   = None   # number of observations
    sharpe_ratio:       Optional[float] = None
    oos_win_rate:       Optional[float] = None
    avg_return_r:       Optional[float] = None
    max_drawdown:       Optional[float] = None
    composite_score:    Optional[float] = None
    expectancy_r:       Optional[float] = None

    # Regime mapping
    preferred_regimes:  List[str] = field(default_factory=list)
    compatible_regimes: List[str] = field(default_factory=list)

    # Entry conditions (for JSON-based strategies)
    entry_conditions:   List[EntryCondition] = field(default_factory=list)

    # Status
    health_status:   LegacyHealthStatus = LegacyHealthStatus.UNKNOWN
    is_approved:     bool  = False
    live_trades:     int   = 0
    live_wins:       int   = 0

    # Descriptive
    description:     str   = ""
    pattern_id:      str   = ""
    tags:            List[str] = field(default_factory=list)

    # Provenance
    discovered_at:   Optional[datetime] = None
    last_tested:     Optional[datetime] = None
    source_path:     str                = ""   # file path where it was found
    raw_definition:  Dict[str, Any]     = field(default_factory=dict)

    def evaluate_entry_conditions(self, features: Dict[str, float]) -> Optional[bool]:
        """
        Returns True if all entry conditions pass, False if any fail, None if features missing.
        Always True if no conditions defined (unconditional strategy).
        """
        if not self.entry_conditions:
            return True
        results = [c.evaluate(features) for c in self.entry_conditions]
        if any(r is None for r in results):
            return None
        return all(results)  # type: ignore[arg-type]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "source":        self.source.value,
            "type":          self.strategy_type.value,
            "min_rr":        self.min_rr,
            "max_loss_pct":  self.max_loss_pct,
            "base_strategy": self.base_strategy,
            "category":      self.category,
            "direction":     self.direction,
            "precision":     self.precision,
            "support":       self.support,
            "is_approved":   self.is_approved,
            "health_status": self.health_status.value,
            "preferred_regimes": self.preferred_regimes,
            "entry_conditions": [c.to_dict() for c in self.entry_conditions],
            "description":   self.description,
        }

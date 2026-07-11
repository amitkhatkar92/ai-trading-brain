"""iios/investment/market/correlation/models.py
Core domain models for the Institutional Correlation & Intermarket Intelligence Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── Enums ──────────────────────────────────────────────────────────────────

class CorrelationRegimeType(str, Enum):
    HIGHLY_CORRELATED     = "highly_correlated"
    MODERATELY_CORRELATED = "moderately_correlated"
    WEAKLY_CORRELATED     = "weakly_correlated"
    INDEPENDENT           = "independent"
    INVERSE_CORRELATION   = "inverse_correlation"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    FLIGHT_TO_SAFETY      = "flight_to_safety"
    RISK_ON               = "risk_on"
    RISK_OFF              = "risk_off"
    UNKNOWN               = "unknown"


class CorrelationEventType(str, Enum):
    REGIME_CHANGE              = "regime_change"
    CORRELATION_SPIKE          = "correlation_spike"
    CORRELATION_BREAKDOWN      = "correlation_breakdown"
    CONTAGION_DETECTED         = "contagion_detected"
    SYSTEMIC_RISK_ELEVATED     = "systemic_risk_elevated"
    DIVERSIFICATION_COLLAPSE   = "diversification_collapse"
    FLIGHT_TO_SAFETY           = "flight_to_safety"
    RISK_ON_TRANSITION         = "risk_on_transition"
    RISK_OFF_TRANSITION        = "risk_off_transition"
    ANOMALY_DETECTED           = "anomaly_detected"
    SHOCK_PROPAGATION          = "shock_propagation"


class AssetClass(str, Enum):
    EQUITY          = "equity"
    INDEX           = "index"
    SECTOR_ETF      = "sector_etf"
    INDUSTRY        = "industry"
    BOND            = "bond"
    CURRENCY        = "currency"
    COMMODITY       = "commodity"
    PRECIOUS_METAL  = "precious_metal"
    VOLATILITY      = "volatility"
    CRYPTO          = "crypto"
    INTEREST_RATE   = "interest_rate"
    REAL_ESTATE     = "real_estate"
    UNKNOWN         = "unknown"


class CorrelationMethod(str, Enum):
    PEARSON   = "pearson"
    SPEARMAN  = "spearman"
    KENDALL   = "kendall"


class DependencyType(str, Enum):
    LEADING       = "leading"
    LAGGING       = "lagging"
    BIDIRECTIONAL = "bidirectional"
    INDEPENDENT   = "independent"


class RiskLevel(str, Enum):
    LOW         = "low"
    MODERATE    = "moderate"
    ELEVATED    = "elevated"
    HIGH        = "high"
    CRITICAL    = "critical"


class DiversificationLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD      = "good"
    FAIR      = "fair"
    POOR      = "poor"
    CRITICAL  = "critical"


class RelationshipType(str, Enum):
    POSITIVE = "positive"
    INVERSE  = "inverse"
    UNSTABLE = "unstable"
    UNKNOWN  = "unknown"


# ── Primary input types ────────────────────────────────────────────────────

@dataclass
class PriceObservation:
    """Single asset price/return observation at one time step."""
    symbol:      str
    return_pct:  float                    # percentage return (e.g. 0.01 = 1%)
    asset_class: str = AssetClass.UNKNOWN.value
    sector:      str = "unknown"
    price:       float = 0.0
    volume:      float = 0.0
    timestamp:   float = 0.0
    metadata:    Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiAssetSnapshot:
    """Collection of PriceObservation for multiple assets at one time step."""
    bar_index:    int
    timestamp:    float
    observations: List[PriceObservation]

    @property
    def total(self) -> int:
        return len(self.observations)

    @property
    def symbols(self) -> List[str]:
        return [o.symbol for o in self.observations]

    def returns(self) -> Dict[str, float]:
        return {o.symbol: o.return_pct for o in self.observations}

    def by_asset_class(self) -> Dict[str, List[PriceObservation]]:
        result: Dict[str, List[PriceObservation]] = {}
        for obs in self.observations:
            result.setdefault(obs.asset_class, []).append(obs)
        return result

    def by_sector(self) -> Dict[str, List[PriceObservation]]:
        result: Dict[str, List[PriceObservation]] = {}
        for obs in self.observations:
            result.setdefault(obs.sector, []).append(obs)
        return result

    def get(self, symbol: str) -> Optional[PriceObservation]:
        return next((o for o in self.observations if o.symbol == symbol), None)


# ── Correlation pair ───────────────────────────────────────────────────────

@dataclass
class CorrelationPair:
    symbol_a:    str
    symbol_b:    str
    correlation: float
    method:      CorrelationMethod
    window:      int
    confidence:  float = 1.0

    def reversed(self) -> "CorrelationPair":
        return CorrelationPair(
            symbol_a=self.symbol_b,
            symbol_b=self.symbol_a,
            correlation=self.correlation,
            method=self.method,
            window=self.window,
            confidence=self.confidence,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_a":    self.symbol_a,
            "symbol_b":    self.symbol_b,
            "correlation": round(self.correlation, 4),
            "method":      self.method.value,
            "window":      self.window,
            "confidence":  round(self.confidence, 4),
        }


# ── Correlation matrix ─────────────────────────────────────────────────────

@dataclass
class CorrelationMatrix:
    """Full N×N correlation matrix for a universe of assets."""
    symbols:       List[str]
    data:          Dict[str, Dict[str, float]]   # data[s1][s2] = correlation
    method:        CorrelationMethod
    window:        int
    n_observations: int
    bar_index:     int
    timestamp:     float
    confidence:    float

    def get(self, s1: str, s2: str) -> Optional[float]:
        """Return correlation between s1 and s2, or None if unknown."""
        try:
            return self.data[s1][s2]
        except KeyError:
            try:
                return self.data[s2][s1]
            except KeyError:
                return None

    def avg_correlation(self) -> float:
        """Mean of all off-diagonal absolute correlations."""
        vals = []
        syms = self.symbols
        for i, s1 in enumerate(syms):
            for s2 in syms[i + 1:]:
                v = self.get(s1, s2)
                if v is not None:
                    vals.append(v)
        return sum(vals) / len(vals) if vals else 0.0

    def avg_abs_correlation(self) -> float:
        """Mean of |correlation| for all pairs."""
        vals = []
        syms = self.symbols
        for i, s1 in enumerate(syms):
            for s2 in syms[i + 1:]:
                v = self.get(s1, s2)
                if v is not None:
                    vals.append(abs(v))
        return sum(vals) / len(vals) if vals else 0.0

    def max_pair(self) -> Optional[Tuple[str, str, float]]:
        """Pair with highest (most positive) correlation."""
        best: Optional[Tuple[str, str, float]] = None
        syms = self.symbols
        for i, s1 in enumerate(syms):
            for s2 in syms[i + 1:]:
                v = self.get(s1, s2)
                if v is not None and (best is None or v > best[2]):
                    best = (s1, s2, v)
        return best

    def min_pair(self) -> Optional[Tuple[str, str, float]]:
        """Pair with lowest (most negative) correlation."""
        worst: Optional[Tuple[str, str, float]] = None
        syms = self.symbols
        for i, s1 in enumerate(syms):
            for s2 in syms[i + 1:]:
                v = self.get(s1, s2)
                if v is not None and (worst is None or v < worst[2]):
                    worst = (s1, s2, v)
        return worst

    def highly_correlated_pairs(
        self, threshold: float = 0.70
    ) -> List[Tuple[str, str, float]]:
        result = []
        syms = self.symbols
        for i, s1 in enumerate(syms):
            for s2 in syms[i + 1:]:
                v = self.get(s1, s2)
                if v is not None and v >= threshold:
                    result.append((s1, s2, v))
        return sorted(result, key=lambda x: -x[2])

    def inversely_correlated_pairs(
        self, threshold: float = -0.70
    ) -> List[Tuple[str, str, float]]:
        result = []
        syms = self.symbols
        for i, s1 in enumerate(syms):
            for s2 in syms[i + 1:]:
                v = self.get(s1, s2)
                if v is not None and v <= threshold:
                    result.append((s1, s2, v))
        return sorted(result, key=lambda x: x[2])

    def n_pairs(self) -> int:
        n = len(self.symbols)
        return n * (n - 1) // 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbols":        self.symbols,
            "method":         self.method.value,
            "window":         self.window,
            "n_observations": self.n_observations,
            "bar_index":      self.bar_index,
            "confidence":     round(self.confidence, 4),
            "avg_correlation": round(self.avg_correlation(), 4),
            "n_pairs":        self.n_pairs(),
        }


# ── Dependency types ───────────────────────────────────────────────────────

@dataclass
class DependencyEdge:
    """Directed dependency between two assets."""
    source:          str            # leading asset
    target:          str            # lagging asset
    lag_bars:        int            # source leads target by this many bars
    correlation:     float          # cross-correlation at optimal lag
    dependency_type: DependencyType
    confidence:      float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":          self.source,
            "target":          self.target,
            "lag_bars":        self.lag_bars,
            "correlation":     round(self.correlation, 4),
            "dependency_type": self.dependency_type.value,
            "confidence":      round(self.confidence, 4),
        }


@dataclass
class DependencyGraph:
    """Graph of leading/lagging relationships between assets."""
    edges:     List[DependencyEdge]
    bar_index: int
    timestamp: float

    def leading_assets(self) -> List[str]:
        seen: Dict[str, float] = {}
        for e in self.edges:
            if e.dependency_type == DependencyType.LEADING:
                seen[e.source] = max(seen.get(e.source, 0), e.correlation)
        return sorted(seen, key=lambda s: -seen[s])

    def lagging_assets(self) -> List[str]:
        seen: Dict[str, float] = {}
        for e in self.edges:
            if e.dependency_type == DependencyType.LEADING:
                seen[e.target] = max(seen.get(e.target, 0), e.correlation)
        return sorted(seen, key=lambda s: -seen[s])

    def get_leaders_of(self, symbol: str) -> List[DependencyEdge]:
        return [e for e in self.edges if e.target == symbol
                and e.dependency_type == DependencyType.LEADING]

    def get_followers_of(self, symbol: str) -> List[DependencyEdge]:
        return [e for e in self.edges if e.source == symbol
                and e.dependency_type == DependencyType.LEADING]

    def influence_score(self, symbol: str) -> float:
        """How strongly does this asset lead others? 0-1."""
        followers = self.get_followers_of(symbol)
        if not followers:
            return 0.0
        return sum(abs(e.correlation) for e in followers) / len(followers)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_edges":       len(self.edges),
            "bar_index":     self.bar_index,
            "leading_assets": self.leading_assets(),
            "edges":         [e.to_dict() for e in self.edges],
        }


# ── Intermarket relationship ───────────────────────────────────────────────

@dataclass
class IntermarketRelationship:
    """Relationship between two asset classes or specific assets."""
    asset_a:             str
    asset_b:             str
    asset_class_a:       str
    asset_class_b:       str
    expected_type:       RelationshipType
    current_correlation: float
    historical_avg:      float
    is_typical:          bool          # behaving as expected
    anomaly_score:       float         # 0-1; 1 = highly anomalous
    description:         str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_a":             self.asset_a,
            "asset_b":             self.asset_b,
            "expected_type":       self.expected_type.value,
            "current_correlation": round(self.current_correlation, 4),
            "is_typical":          self.is_typical,
            "anomaly_score":       round(self.anomaly_score, 4),
        }


@dataclass
class IntermarketAnalysis:
    """Cross-asset and intermarket relationship analysis."""
    relationships:       List[IntermarketRelationship]
    anomalies:           List[IntermarketRelationship]    # unusual relationships
    risk_on_signals:     int                               # count of risk-on patterns
    risk_off_signals:    int                               # count of risk-off patterns
    flight_to_safety:    bool
    bar_index:           int
    timestamp:           float

    def net_regime_signal(self) -> str:
        if self.flight_to_safety:
            return "flight_to_safety"
        if self.risk_on_signals > self.risk_off_signals:
            return "risk_on"
        if self.risk_off_signals > self.risk_on_signals:
            return "risk_off"
        return "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_relationships":  len(self.relationships),
            "n_anomalies":      len(self.anomalies),
            "risk_on_signals":  self.risk_on_signals,
            "risk_off_signals": self.risk_off_signals,
            "flight_to_safety": self.flight_to_safety,
            "net_signal":       self.net_regime_signal(),
        }


# ── Risk types ─────────────────────────────────────────────────────────────

@dataclass
class ContagionPath:
    """Path through which a shock propagates."""
    source:            str
    target:            str
    path:              List[str]      # sequence of assets from source to target
    correlation_product: float        # product of correlations along path
    estimated_impact:  float          # estimated magnitude at target
    propagation_steps: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source":             self.source,
            "target":             self.target,
            "path":               self.path,
            "estimated_impact":   round(self.estimated_impact, 4),
            "propagation_steps":  self.propagation_steps,
        }


@dataclass
class SystemicRiskMetrics:
    """Systemic and contagion risk metrics."""
    risk_level:                RiskLevel
    avg_pairwise_correlation:  float      # mean of all pairwise correlations
    avg_abs_correlation:       float      # mean of |correlation|
    correlation_concentration: float      # fraction of highly-correlated pairs
    contagion_index:           float      # 0-1 contagion susceptibility
    interconnectedness:        float      # 0-1 network density
    systemic_risk_score:       float      # 0-100 composite score
    most_interconnected:       List[str]  # most systemically important assets
    n_correlated_clusters:     int        # number of highly-correlated clusters

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level":                self.risk_level.value,
            "avg_pairwise_correlation":  round(self.avg_pairwise_correlation, 4),
            "avg_abs_correlation":       round(self.avg_abs_correlation, 4),
            "correlation_concentration": round(self.correlation_concentration, 4),
            "contagion_index":           round(self.contagion_index, 4),
            "interconnectedness":        round(self.interconnectedness, 4),
            "systemic_risk_score":       round(self.systemic_risk_score, 2),
            "most_interconnected":       self.most_interconnected,
        }


# ── Diversification types ──────────────────────────────────────────────────

@dataclass
class DiversificationMetrics:
    """Portfolio diversification analysis."""
    diversification_score:  float           # 0-100 (100 = perfectly diversified)
    diversification_level:  DiversificationLevel
    effective_n_assets:     float           # Markowitz effective number
    correlation_clusters:   List[List[str]] # groups of highly-correlated assets
    redundant_pairs:        List[Tuple[str, str, float]]   # high-correlation pairs
    hedging_pairs:          List[Tuple[str, str, float]]   # inverse-correlation pairs
    portfolio_correlation:  float           # avg pairwise (assumed equal-weight)
    cluster_count:          int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diversification_score":  round(self.diversification_score, 2),
            "diversification_level":  self.diversification_level.value,
            "effective_n_assets":     round(self.effective_n_assets, 2),
            "cluster_count":          self.cluster_count,
            "n_redundant_pairs":      len(self.redundant_pairs),
            "n_hedging_pairs":        len(self.hedging_pairs),
            "portfolio_correlation":  round(self.portfolio_correlation, 4),
        }


# ── Regime types ───────────────────────────────────────────────────────────

@dataclass
class CorrelationRegimeSnapshot:
    """Current correlation regime classification."""
    regime:                CorrelationRegimeType
    confidence:            float
    duration_bars:         int
    previous_regime:       Optional[CorrelationRegimeType]
    avg_correlation:       float
    transition_probability: float
    regime_score:          float       # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime":               self.regime.value,
            "confidence":           round(self.confidence, 4),
            "duration_bars":        self.duration_bars,
            "previous_regime":      (
                self.previous_regime.value if self.previous_regime else None
            ),
            "avg_correlation":      round(self.avg_correlation, 4),
            "transition_probability": round(self.transition_probability, 4),
            "regime_score":         round(self.regime_score, 2),
        }


@dataclass
class CorrelationConfidenceScore:
    """Confidence in the correlation intelligence output."""
    data_quality:          float   # 0-1 quality of input observations
    window_fullness:       float   # 0-1 fraction of window filled
    n_assets_score:        float   # 0-1 based on number of assets
    stability_score:       float   # 0-1 consistency of correlations over time
    overall_score:         float   # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_quality":    round(self.data_quality, 4),
            "window_fullness": round(self.window_fullness, 4),
            "n_assets_score":  round(self.n_assets_score, 4),
            "stability_score": round(self.stability_score, 4),
            "overall_score":   round(self.overall_score, 2),
        }


# ── Event ─────────────────────────────────────────────────────────────────

@dataclass
class CorrelationEvent:
    """Noteworthy correlation event."""
    event_type:      CorrelationEventType
    bar_index:       int
    severity:        float                              # 0-1
    from_regime:     Optional[CorrelationRegimeType] = None
    to_regime:       Optional[CorrelationRegimeType] = None
    affected_assets: List[str] = field(default_factory=list)
    description:     str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type":      self.event_type.value,
            "bar_index":       self.bar_index,
            "severity":        round(self.severity, 4),
            "from_regime":     self.from_regime.value if self.from_regime else None,
            "to_regime":       self.to_regime.value if self.to_regime else None,
            "affected_assets": self.affected_assets,
            "description":     self.description,
        }


# ── Primary output ─────────────────────────────────────────────────────────

@dataclass
class CorrelationIntelligenceSnapshot:
    """Primary output of InstitutionalCorrelationIntelligenceEngine."""

    snapshot_id:       str
    bar_index:         int
    timestamp:         float

    # Core analysis
    correlation_matrix:  CorrelationMatrix
    regime_snapshot:     CorrelationRegimeSnapshot
    dependency_graph:    DependencyGraph
    systemic_risk:       SystemicRiskMetrics
    diversification:     DiversificationMetrics
    intermarket:         IntermarketAnalysis

    # Confidence
    confidence:          CorrelationConfidenceScore

    # Events
    active_events:       List[CorrelationEvent]
    last_event:          Optional[CorrelationEvent]

    # Cross-engine context
    market_regime:     Optional[str] = None
    volatility_regime: Optional[str] = None
    breadth_regime:    Optional[str] = None
    trend_stage:       Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "bar_index":        self.bar_index,
            "timestamp":        self.timestamp,
            "correlation_matrix": self.correlation_matrix.to_dict(),
            "regime":           self.regime_snapshot.to_dict(),
            "dependency_graph": self.dependency_graph.to_dict(),
            "systemic_risk":    self.systemic_risk.to_dict(),
            "diversification":  self.diversification.to_dict(),
            "intermarket":      self.intermarket.to_dict(),
            "confidence":       self.confidence.to_dict(),
            "active_events":    [e.to_dict() for e in self.active_events],
            "last_event":       self.last_event.to_dict() if self.last_event else None,
            "market_regime":    self.market_regime,
            "volatility_regime": self.volatility_regime,
            "breadth_regime":   self.breadth_regime,
            "trend_stage":      self.trend_stage,
        }

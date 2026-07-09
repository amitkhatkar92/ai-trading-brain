"""iios/investment/market/models/market_intelligence.py
Primary output of the Market Intelligence Engine.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import (
    BreadthCondition,
    CorrelationRegime,
    LiquidityLevel,
    MarketRegime,
    MarketStatus,
    MarketStrength,
    SentimentLevel,
    TrendDirection,
    VolatilityLevel,
)
from iios.investment.market.models.market_health import MarketHealth
from iios.investment.market.models.market_signal import MarketSignal


@dataclass
class MarketIntelligence:
    """
    Authoritative, comprehensive intelligence object produced per analysis cycle.
    Downstream engines (Technical, Options, Sector, Macro, Execution) should
    consume intelligence from here rather than re-implementing market analysis.
    """

    intelligence_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:           str              = ""
    request_id:          str              = ""

    # ── State ─────────────────────────────────────────────────────────────────
    status:              MarketStatus     = MarketStatus.UNKNOWN

    # ── Regime ────────────────────────────────────────────────────────────────
    regime:              MarketRegime     = MarketRegime.UNKNOWN
    regime_confidence:   float            = 0.0

    # ── Trend ─────────────────────────────────────────────────────────────────
    trend:               TrendDirection   = TrendDirection.UNDEFINED
    trend_strength:      MarketStrength   = MarketStrength.NEUTRAL
    trend_score:         float            = 50.0

    # ── Volatility ────────────────────────────────────────────────────────────
    volatility:          VolatilityLevel  = VolatilityLevel.MODERATE
    volatility_score:    float            = 50.0

    # ── Liquidity ─────────────────────────────────────────────────────────────
    liquidity:           LiquidityLevel   = LiquidityLevel.MODERATE
    liquidity_score:     float            = 50.0

    # ── Breadth ───────────────────────────────────────────────────────────────
    breadth:             BreadthCondition = BreadthCondition.MODERATE
    breadth_score:       float            = 50.0

    # ── Sentiment ─────────────────────────────────────────────────────────────
    sentiment:           SentimentLevel   = SentimentLevel.NEUTRAL
    sentiment_score:     float            = 50.0

    # ── Correlation ───────────────────────────────────────────────────────────
    correlation:         CorrelationRegime = CorrelationRegime.MODERATE
    correlation_score:   float             = 50.0

    # ── Health ────────────────────────────────────────────────────────────────
    health:              MarketHealth     = field(default_factory=MarketHealth)
    market_health_score: float            = 50.0
    market_quality_score: float           = 50.0

    # ── Intelligence products ─────────────────────────────────────────────────
    opportunities:       list[str]        = field(default_factory=list)
    threats:             list[str]        = field(default_factory=list)
    key_observations:    list[str]        = field(default_factory=list)
    signals:             list[MarketSignal] = field(default_factory=list)

    # ── Meta ──────────────────────────────────────────────────────────────────
    confidence:          float            = 0.0
    metadata:            dict[str, Any]   = field(default_factory=dict)
    created_at:          float            = field(default_factory=time.time)
    duration_ms:         float            = 0.0

    # ── mutation helpers ──────────────────────────────────────────────────────

    def add_signal(self, signal: MarketSignal) -> None:
        self.signals.append(signal)

    def add_opportunity(self, description: str) -> None:
        self.opportunities.append(description)

    def add_threat(self, description: str) -> None:
        self.threats.append(description)

    def add_observation(self, observation: str) -> None:
        self.key_observations.append(observation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intelligence_id":      self.intelligence_id,
            "market_id":            self.market_id,
            "request_id":           self.request_id,
            "status":               self.status.value,
            "regime":               self.regime.value,
            "regime_confidence":    self.regime_confidence,
            "trend":                self.trend.value,
            "trend_strength":       self.trend_strength.value,
            "trend_score":          self.trend_score,
            "volatility":           self.volatility.value,
            "volatility_score":     self.volatility_score,
            "liquidity":            self.liquidity.value,
            "liquidity_score":      self.liquidity_score,
            "breadth":              self.breadth.value,
            "breadth_score":        self.breadth_score,
            "sentiment":            self.sentiment.value,
            "sentiment_score":      self.sentiment_score,
            "correlation":          self.correlation.value,
            "correlation_score":    self.correlation_score,
            "health":               self.health.to_dict(),
            "market_health_score":  self.market_health_score,
            "market_quality_score": self.market_quality_score,
            "opportunities":        self.opportunities,
            "threats":              self.threats,
            "key_observations":     self.key_observations,
            "signals":              [s.to_dict() for s in self.signals],
            "confidence":           self.confidence,
            "metadata":             self.metadata,
            "created_at":           self.created_at,
            "duration_ms":          self.duration_ms,
        }

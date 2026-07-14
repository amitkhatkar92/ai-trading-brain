"""iios/investment/strategy/debate/evidence_collector.py
Collects evidence from IIOS integration points via protocol adapters.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from iios.investment.strategy.debate.debate_context import DebateContext
from iios.investment.strategy.debate.debate_constants import (
    EvidenceReliability,
    EvidenceSource,
    EvidenceWeight,
)
from iios.investment.strategy.debate.evidence_registry import Evidence, EvidenceRegistry, make_evidence
from iios.investment.strategy.debate.evidence_validator import EvidenceValidator


# ── Integration protocols ─────────────────────────────────────────────────────

@runtime_checkable
class MarketIntelligencePort(Protocol):
    def get_market_summary(self, symbol: str) -> Dict[str, Any]: ...


@runtime_checkable
class CompanyIntelligencePort(Protocol):
    def get_company_summary(self, symbol: str) -> Dict[str, Any]: ...


@runtime_checkable
class RiskIntelligencePort(Protocol):
    def get_risk_metrics(self, symbol: str, strategy: str) -> Dict[str, Any]: ...


@runtime_checkable
class LearningEnginePort(Protocol):
    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]: ...


@runtime_checkable
class KnowledgeLayerPort(Protocol):
    def query(self, topic: str, context: str) -> Dict[str, Any]: ...


# ── Collection result ─────────────────────────────────────────────────────────

@dataclass
class CollectionResult:
    session_id:      str
    collected:       int
    rejected:        int
    duration_ms:     float
    sources_queried: List[str]
    errors:          List[str]


class EvidenceCollector:
    """
    Collects evidence from registered IIOS integration adapters and
    pre-loaded context data.  Uses protocol-based duck typing so any
    compatible IIOS component works without hard coupling.
    """

    def __init__(
        self,
        market_intelligence:   Optional[MarketIntelligencePort]  = None,
        company_intelligence:  Optional[CompanyIntelligencePort] = None,
        risk_intelligence:     Optional[RiskIntelligencePort]    = None,
        learning_engine:       Optional[LearningEnginePort]      = None,
        knowledge_layer:       Optional[KnowledgeLayerPort]      = None,
        custom_collectors:     Optional[List[Callable[[DebateContext], List[Evidence]]]] = None,
    ) -> None:
        self._market     = market_intelligence
        self._company    = company_intelligence
        self._risk       = risk_intelligence
        self._learning   = learning_engine
        self._knowledge  = knowledge_layer
        self._customs    = custom_collectors or []
        self._validator  = EvidenceValidator()

    def collect(self, context: DebateContext, registry: EvidenceRegistry) -> CollectionResult:
        start      = time.monotonic()
        all_ev:    List[Evidence] = []
        queried:   List[str]      = []
        errors:    List[str]      = []

        # ── Pre-loaded evidence from context ──────────────────────────────────
        for raw in context.pre_loaded_evidence:
            try:
                ev = self._from_raw(raw, context.context_id)
                if ev:
                    all_ev.append(ev)
            except Exception as exc:
                errors.append(f"pre_loaded: {exc}")
        if context.pre_loaded_evidence:
            queried.append("pre_loaded")

        # ── Market Intelligence ───────────────────────────────────────────────
        if self._market:
            try:
                data = self._market.get_market_summary(context.symbol)
                all_ev.extend(self._parse_market_data(data, context.context_id))
                queried.append(EvidenceSource.MARKET_INTELLIGENCE.value)
            except Exception as exc:
                errors.append(f"market_intelligence: {exc}")

        # ── Company Intelligence ──────────────────────────────────────────────
        if self._company:
            try:
                data = self._company.get_company_summary(context.symbol)
                all_ev.extend(self._parse_company_data(data, context.context_id))
                queried.append(EvidenceSource.COMPANY_INTELLIGENCE.value)
            except Exception as exc:
                errors.append(f"company_intelligence: {exc}")

        # ── Risk Intelligence ─────────────────────────────────────────────────
        if self._risk:
            try:
                strategy_name = context.strategy_name if context.strategy else "unknown"
                data = self._risk.get_risk_metrics(context.symbol, strategy_name)
                all_ev.extend(self._parse_risk_data(data, context.context_id))
                queried.append(EvidenceSource.RISK_INTELLIGENCE.value)
            except Exception as exc:
                errors.append(f"risk_intelligence: {exc}")

        # ── Learning Engine ───────────────────────────────────────────────────
        if self._learning and context.strategy:
            try:
                data = self._learning.get_strategy_performance(context.strategy.strategy_id)
                all_ev.extend(self._parse_learning_data(data, context.context_id))
                queried.append(EvidenceSource.LEARNING_ENGINE.value)
            except Exception as exc:
                errors.append(f"learning_engine: {exc}")

        # ── Knowledge Layer ───────────────────────────────────────────────────
        if self._knowledge and context.opportunity:
            try:
                data = self._knowledge.query(context.symbol, "strategy_debate")
                all_ev.extend(self._parse_knowledge_data(data, context.context_id))
                queried.append(EvidenceSource.KNOWLEDGE_LAYER.value)
            except Exception as exc:
                errors.append(f"knowledge_layer: {exc}")

        # ── Custom collectors ─────────────────────────────────────────────────
        for collector in self._customs:
            try:
                custom_ev = collector(context)
                all_ev.extend(custom_ev)
                queried.append("custom")
            except Exception as exc:
                errors.append(f"custom_collector: {exc}")

        # ── Validate and register ─────────────────────────────────────────────
        valid, rejected_list = self._validator.validate_all(all_ev)
        registry.add_all(valid)

        return CollectionResult(
            session_id=context.context_id,
            collected=len(valid),
            rejected=len(rejected_list),
            duration_ms=round((time.monotonic() - start) * 1000, 2),
            sources_queried=queried,
            errors=errors,
        )

    # ── Parsers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _from_raw(raw: Dict[str, Any], session_id: str) -> Optional[Evidence]:
        """Convert a pre-loaded evidence dict to an Evidence object."""
        if not isinstance(raw, dict):
            return None
        score = float(raw.get("raw_score", 50.0))
        return make_evidence(
            session_id=session_id,
            source=EvidenceSource(raw.get("source", EvidenceSource.MARKET_INTELLIGENCE.value)),
            category=str(raw.get("category", "general")),
            title=str(raw.get("title", "Pre-loaded evidence")),
            description=str(raw.get("description", "")),
            raw_score=score,
            reliability=EvidenceReliability(raw.get("reliability", EvidenceReliability.MEDIUM.value)),
            weight=EvidenceWeight(raw.get("weight", EvidenceWeight.MEDIUM.value)),
            relevance=float(raw.get("relevance", 0.7)),
            tags=raw.get("tags", []),
            metadata=raw.get("metadata", {}),
        )

    @staticmethod
    def _parse_market_data(data: Dict, session_id: str) -> List[Evidence]:
        result = []
        regime = str(data.get("regime", "unknown"))
        # Regime evidence
        regime_score = 70.0 if "bull" in regime else (30.0 if "bear" in regime else 50.0)
        result.append(make_evidence(
            session_id=session_id,
            source=EvidenceSource.MARKET_INTELLIGENCE,
            category="market_regime",
            title=f"Market Regime: {regime}",
            description=f"Current market regime is {regime}",
            raw_score=regime_score,
            reliability=EvidenceReliability.HIGH,
            weight=EvidenceWeight.HIGH,
            relevance=0.85,
        ))
        # VIX evidence if available
        vix = data.get("vix")
        if vix is not None:
            vix_score = max(0.0, min(100.0, 100.0 - float(vix) * 2))
            result.append(make_evidence(
                session_id=session_id,
                source=EvidenceSource.MARKET_INTELLIGENCE,
                category="volatility",
                title=f"VIX Level: {vix:.1f}",
                description=f"Current VIX = {vix:.1f}. Lower VIX favours entries.",
                raw_score=vix_score,
                reliability=EvidenceReliability.HIGH,
                weight=EvidenceWeight.MEDIUM,
                relevance=0.75,
            ))
        return result

    @staticmethod
    def _parse_company_data(data: Dict, session_id: str) -> List[Evidence]:
        result = []
        sentiment = float(data.get("sentiment_score", 50.0))
        result.append(make_evidence(
            session_id=session_id,
            source=EvidenceSource.COMPANY_INTELLIGENCE,
            category="company_sentiment",
            title="Company Intelligence Sentiment",
            description=str(data.get("summary", "Company intelligence assessment")),
            raw_score=sentiment,
            reliability=EvidenceReliability.MEDIUM,
            weight=EvidenceWeight.MEDIUM,
            relevance=0.7,
        ))
        return result

    @staticmethod
    def _parse_risk_data(data: Dict, session_id: str) -> List[Evidence]:
        result = []
        risk_score = float(data.get("risk_score", 50.0))
        # Invert: high risk_score means danger (bearish for entry)
        inverted = 100.0 - risk_score
        result.append(make_evidence(
            session_id=session_id,
            source=EvidenceSource.RISK_INTELLIGENCE,
            category="risk_assessment",
            title="Risk Intelligence Assessment",
            description=str(data.get("summary", "Risk metrics assessment")),
            raw_score=inverted,
            reliability=EvidenceReliability.HIGH,
            weight=EvidenceWeight.HIGH,
            relevance=0.9,
        ))
        return result

    @staticmethod
    def _parse_learning_data(data: Dict, session_id: str) -> List[Evidence]:
        result = []
        win_rate = float(data.get("win_rate", 0.5)) * 100
        result.append(make_evidence(
            session_id=session_id,
            source=EvidenceSource.LEARNING_ENGINE,
            category="historical_performance",
            title=f"Historical Win Rate: {win_rate:.0f}%",
            description=str(data.get("summary", "Strategy learning performance data")),
            raw_score=win_rate,
            reliability=EvidenceReliability.HIGH,
            weight=EvidenceWeight.HIGH,
            relevance=0.85,
        ))
        return result

    @staticmethod
    def _parse_knowledge_data(data: Dict, session_id: str) -> List[Evidence]:
        result = []
        score = float(data.get("relevance_score", 50.0))
        result.append(make_evidence(
            session_id=session_id,
            source=EvidenceSource.KNOWLEDGE_LAYER,
            category="domain_knowledge",
            title="Knowledge Layer Insights",
            description=str(data.get("insights", "No additional insights")),
            raw_score=score,
            reliability=EvidenceReliability.MEDIUM,
            weight=EvidenceWeight.LOW,
            relevance=0.5,
        ))
        return result

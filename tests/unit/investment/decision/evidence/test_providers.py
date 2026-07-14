"""tests/unit/investment/decision/evidence/test_providers.py"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider
from iios.investment.decision.evidence.provider_registry import (
    DuplicateProviderError, ProviderRegistry, UnknownProviderError,
)
from iios.investment.decision.evidence.market_evidence import MarketEvidenceProvider
from iios.investment.decision.evidence.company_evidence import CompanyEvidenceProvider
from iios.investment.decision.evidence.strategy_evidence import StrategyEvidenceProvider
from iios.investment.decision.evidence.risk_evidence import RiskEvidenceProvider
from iios.investment.decision.evidence.knowledge_evidence import KnowledgeEvidenceProvider
from iios.investment.decision.evidence.research_evidence import ResearchEvidenceProvider


# ============================= ProviderRegistry ==========================

class TestProviderRegistry:
    def _reg(self):
        return ProviderRegistry()

    def test_register_and_get(self, stub_market_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        assert reg.get(EvidenceSourceType.MARKET) is stub_market_provider

    def test_duplicate_raises(self, stub_market_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        with pytest.raises(DuplicateProviderError):
            reg.register(stub_market_provider)

    def test_overwrite(self, stub_market_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        reg.register(stub_market_provider, overwrite=True)
        assert reg.count() == 1

    def test_get_unknown_raises(self):
        reg = self._reg()
        with pytest.raises(UnknownProviderError):
            reg.get(EvidenceSourceType.MARKET)

    def test_get_optional_returns_none(self):
        reg = self._reg()
        assert reg.get_optional(EvidenceSourceType.EXTERNAL) is None

    def test_has(self, stub_market_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        assert reg.has(EvidenceSourceType.MARKET) is True
        assert reg.has(EvidenceSourceType.COMPANY) is False

    def test_unregister(self, stub_market_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        reg.unregister(EvidenceSourceType.MARKET)
        assert not reg.has(EvidenceSourceType.MARKET)

    def test_missing_required(self):
        reg = self._reg()
        missing = reg.missing_required()
        assert EvidenceSourceType.MARKET in missing
        assert EvidenceSourceType.RISK   in missing

    def test_required_present_after_register(self, stub_market_provider, stub_risk_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        reg.register(stub_risk_provider)
        assert reg.required_providers_present() is True

    def test_to_dict(self, stub_market_provider):
        reg = self._reg()
        reg.register(stub_market_provider)
        d = reg.to_dict()
        assert d["registered_count"] == 1


# ============================= Concrete Providers ========================

_DECISION = "DEC-001"
_SUBJECT  = "TCS"
_STYPE    = "equity"


class TestMarketEvidenceProvider:
    def test_collect_empty_payload(self):
        p = MarketEvidenceProvider()
        assert p.collect(_DECISION, _SUBJECT, _STYPE, None) == []

    def test_collect_returns_items(self):
        p = MarketEvidenceProvider()
        payload = {"last_price": 3400.0, "volume": 1_000_000, "rsi_14": 62.5, "regime": "BULL"}
        items = p.collect(_DECISION, _SUBJECT, _STYPE, payload)
        assert len(items) >= 3
        keys = {i.key for i in items}
        assert "last_price" in keys

    def test_source_type(self):
        assert MarketEvidenceProvider().source_type == EvidenceSourceType.MARKET

    def test_required_items_present(self):
        p = MarketEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {"last_price": 100.0})
        required = [i for i in items if i.is_required]
        assert len(required) >= 1


class TestCompanyEvidenceProvider:
    def test_collect_empty(self):
        assert CompanyEvidenceProvider().collect(_DECISION, _SUBJECT, _STYPE, None) == []

    def test_collect_fundamentals(self):
        p = CompanyEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {"pe_ratio": 22.0, "roe": 18.5})
        assert len(items) == 2
        assert {i.key for i in items} == {"pe_ratio", "roe"}


class TestStrategyEvidenceProvider:
    def test_collect(self):
        p = StrategyEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {
            "signal_strength": 75.0, "win_rate": 0.60, "sharpe_ratio": 1.2,
        })
        assert len(items) == 3


class TestRiskEvidenceProvider:
    def test_collect(self):
        p = RiskEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {
            "risk_score": 45.0, "portfolio_risk_pct": 2.5, "var_95": 1.8,
        })
        assert len(items) == 3

    def test_required_items(self):
        p = RiskEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {
            "risk_score": 40.0, "portfolio_risk_pct": 2.0,
        })
        req = [i for i in items if i.is_required]
        assert len(req) == 2


class TestKnowledgeEvidenceProvider:
    def test_collect(self):
        p = KnowledgeEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {"news_sentiment": 68.0})
        assert len(items) == 1


class TestResearchEvidenceProvider:
    def test_collect(self):
        p = ResearchEvidenceProvider()
        items = p.collect(_DECISION, _SUBJECT, _STYPE, {"target_price": 4000.0, "analyst_rating": "BUY"})
        assert len(items) == 2

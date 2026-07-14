"""tests/unit/investment/decision/evidence/conftest.py
Shared fixtures for the Evidence Collection Engine test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidencePriority,
    EvidenceSourceType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem, make_evidence_item
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


# ------------------------------------------------------------------ helpers


def _item(
    key:          str               = "price",
    value:        Any               = 100.0,
    source_type:  EvidenceSourceType = EvidenceSourceType.MARKET,
    category:     EvidenceCategory   = EvidenceCategory.TECHNICAL,
    priority:     EvidencePriority   = EvidencePriority.MEDIUM,
    confidence:   float              = 80.0,
    freshness:    float              = 1.0,
    is_required:  bool               = False,
    decision_id:  str               = "DEC-001",
    subject_id:   str               = "TCS",
    subject_type: str               = "equity",
) -> EvidenceItem:
    return make_evidence_item(
        decision_id=decision_id,
        source_type=source_type,
        source_provider=f"{source_type.value}_provider",
        subject_id=subject_id,
        subject_type=subject_type,
        category=category,
        key=key,
        value=value,
        confidence=confidence,
        freshness_score=freshness,
        priority=priority,
        is_required=is_required,
    )


class _StubProvider(BaseEvidenceProvider):
    """Provider that returns a fixed list of items."""

    def __init__(
        self,
        src_type: EvidenceSourceType,
        items:    List[EvidenceItem],
    ) -> None:
        self._src   = src_type
        self._items = items

    @property
    def source_type(self) -> EvidenceSourceType:
        return self._src

    @property
    def provider_name(self) -> str:
        return f"StubProvider_{self._src.value}"

    def collect(
        self,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payload:      Optional[Dict[str, Any]] = None,
    ) -> List[EvidenceItem]:
        return list(self._items)


# ------------------------------------------------------------------ fixtures


@pytest.fixture()
def decision_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def subject_id() -> str:
    return "INFY"


@pytest.fixture()
def subject_type() -> str:
    return "equity"


@pytest.fixture()
def market_item(decision_id, subject_id, subject_type):
    return _item(
        key="last_price", value=1500.0,
        source_type=EvidenceSourceType.MARKET,
        priority=EvidencePriority.CRITICAL,
        is_required=True,
        decision_id=decision_id, subject_id=subject_id, subject_type=subject_type,
    )


@pytest.fixture()
def risk_item(decision_id, subject_id, subject_type):
    return _item(
        key="risk_score", value=35.0,
        source_type=EvidenceSourceType.RISK,
        priority=EvidencePriority.CRITICAL,
        is_required=True,
        decision_id=decision_id, subject_id=subject_id, subject_type=subject_type,
    )


@pytest.fixture()
def sample_items(market_item, risk_item, decision_id, subject_id, subject_type):
    extras = [
        _item("pe_ratio",    25.0,  EvidenceSourceType.COMPANY,  decision_id=decision_id, subject_id=subject_id, subject_type=subject_type),
        _item("win_rate",    0.58,  EvidenceSourceType.STRATEGY, decision_id=decision_id, subject_id=subject_id, subject_type=subject_type),
        _item("news_sentiment", 65, EvidenceSourceType.KNOWLEDGE, decision_id=decision_id, subject_id=subject_id, subject_type=subject_type),
    ]
    return [market_item, risk_item] + extras


@pytest.fixture()
def stub_market_provider(market_item):
    return _StubProvider(EvidenceSourceType.MARKET, [market_item])


@pytest.fixture()
def stub_risk_provider(risk_item):
    return _StubProvider(EvidenceSourceType.RISK, [risk_item])


@pytest.fixture()
def make_item():
    return _item


@pytest.fixture()
def StubProvider():
    return _StubProvider

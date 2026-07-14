"""tests/unit/investment/decision/reasoning/conftest.py
Shared fixtures for the Decision Reasoning Engine test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory, EvidencePriority, EvidenceSourceType, EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_snapshot import build_snapshot, EvidenceSnapshot
from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import SignalDirection


# ------------------------------------------------------------------ helpers

def _ev_item(key="price", value=100.0, src=EvidenceSourceType.MARKET,
             confidence=80.0, decision_id="D1", subject_id="TCS"):
    return make_evidence_item(
        decision_id=decision_id, source_type=src, source_provider="p",
        subject_id=subject_id, subject_type="equity",
        category=EvidenceCategory.TECHNICAL, key=key, value=value,
        confidence=confidence, freshness_score=1.0,
    )


def _snap(items, decision_id="D1", subject_id="TCS", quality=80.0):
    pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, "equity")
    pkg.add_items(items)
    pkg.seal()
    return build_snapshot(pkg, items, EvidenceValidationStatus.PASSED, quality, 1,
                          datetime.now(timezone.utc))


def _signal(
    key="price", value=100.0, direction=SignalDirection.NEUTRAL,
    src=EvidenceSourceType.MARKET, confidence=80.0,
) -> InterpretedSignal:
    import uuid
    from iios.investment.decision.evidence.evidence_constants import EvidenceCategory
    return InterpretedSignal(
        signal_id=str(uuid.uuid4()),
        evidence_id=str(uuid.uuid4()),
        trace_id=str(uuid.uuid4()),
        key=key,
        value=value,
        direction=direction,
        strength=0.8,
        interpretation=f"Signal: {key}={value}",
        source_type=src,
        category=EvidenceCategory.TECHNICAL,
        confidence=confidence,
        freshness=1.0,
        is_required=False,
    )


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
def ev_item():
    return _ev_item


@pytest.fixture()
def make_snapshot():
    return _snap


@pytest.fixture()
def make_signal():
    return _signal


@pytest.fixture()
def rich_evidence_snapshot(decision_id, subject_id):
    """A well-populated evidence snapshot with items from multiple sources."""
    items = [
        _ev_item("last_price",    1500.0, EvidenceSourceType.MARKET,    decision_id=decision_id, subject_id=subject_id),
        _ev_item("rsi_14",          62.0, EvidenceSourceType.MARKET,    decision_id=decision_id, subject_id=subject_id),
        _ev_item("risk_score",      40.0, EvidenceSourceType.RISK,      decision_id=decision_id, subject_id=subject_id),
        _ev_item("portfolio_risk_pct", 2.0, EvidenceSourceType.RISK,    decision_id=decision_id, subject_id=subject_id),
        _ev_item("pe_ratio",        22.0, EvidenceSourceType.COMPANY,   decision_id=decision_id, subject_id=subject_id),
        _ev_item("roe",             18.0, EvidenceSourceType.COMPANY,   decision_id=decision_id, subject_id=subject_id),
        _ev_item("win_rate",         0.6, EvidenceSourceType.STRATEGY,  decision_id=decision_id, subject_id=subject_id),
        _ev_item("signal_strength", 75.0, EvidenceSourceType.STRATEGY,  decision_id=decision_id, subject_id=subject_id),
        _ev_item("news_sentiment",  65.0, EvidenceSourceType.KNOWLEDGE, decision_id=decision_id, subject_id=subject_id),
    ]
    return _snap(items, decision_id=decision_id, subject_id=subject_id, quality=85.0)


@pytest.fixture()
def minimal_evidence_snapshot(decision_id, subject_id):
    """A minimal evidence snapshot with just two required items."""
    items = [
        _ev_item("last_price", 500.0, EvidenceSourceType.MARKET, decision_id=decision_id, subject_id=subject_id),
        _ev_item("risk_score",  55.0, EvidenceSourceType.RISK,   decision_id=decision_id, subject_id=subject_id),
    ]
    return _snap(items, decision_id=decision_id, subject_id=subject_id, quality=60.0)


@pytest.fixture()
def positive_signals(decision_id) -> List[InterpretedSignal]:
    return [
        _signal("win_rate",      0.65, SignalDirection.POSITIVE, EvidenceSourceType.STRATEGY),
        _signal("roe",           20.0, SignalDirection.POSITIVE, EvidenceSourceType.COMPANY),
        _signal("revenue_growth", 15.0, SignalDirection.POSITIVE, EvidenceSourceType.COMPANY),
    ]


@pytest.fixture()
def negative_signals(decision_id) -> List[InterpretedSignal]:
    return [
        _signal("risk_score", 80.0, SignalDirection.NEGATIVE, EvidenceSourceType.RISK),
        _signal("rsi_14",     75.0, SignalDirection.NEGATIVE, EvidenceSourceType.MARKET),
    ]


@pytest.fixture()
def mixed_signals(positive_signals, negative_signals):
    return positive_signals + negative_signals

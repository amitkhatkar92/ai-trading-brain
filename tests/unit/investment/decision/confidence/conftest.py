"""tests/unit/investment/decision/confidence/conftest.py
Shared fixtures for the Decision Confidence Engine test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

import pytest

from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidenceSourceType,
    EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_snapshot import (
    EvidenceSnapshot,
    build_snapshot,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.reasoning.decision_reasoning_engine import (
    DecisionReasoningEngine,
)
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


# ─── helpers ──────────────────────────────────────────────────────────────────

def _ev_item(
    key="price", value=100.0, src=EvidenceSourceType.MARKET,
    confidence=80.0, decision_id="D1", subject_id="INFY",
):
    return make_evidence_item(
        decision_id=decision_id,
        source_type=src,
        source_provider="test_provider",
        subject_id=subject_id,
        subject_type="equity",
        category=EvidenceCategory.TECHNICAL,
        key=key,
        value=value,
        confidence=confidence,
        freshness_score=1.0,
    )


def _snap(items, decision_id="D1", subject_id="INFY", quality=80.0) -> EvidenceSnapshot:
    pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, "equity")
    pkg.add_items(items)
    pkg.seal()
    return build_snapshot(
        pkg, items, EvidenceValidationStatus.PASSED, quality, 1,
        datetime.now(timezone.utc),
    )


def _build_reasoning_snap(evidence_snap: EvidenceSnapshot) -> ReasoningSnapshot:
    engine = DecisionReasoningEngine()
    engine.start()
    snap = engine.reason_sync(evidence_snap)
    engine.stop()
    return snap


# ─── basic fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def decision_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def subject_id() -> str:
    return "INFY"


@pytest.fixture()
def subject_type() -> str:
    return "equity"


# ─── evidence snapshots ───────────────────────────────────────────────────────

@pytest.fixture()
def rich_evidence_snapshot(decision_id, subject_id) -> EvidenceSnapshot:
    items = [
        _ev_item("last_price",     1500.0, EvidenceSourceType.MARKET,    confidence=90.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("rsi_14",           55.0, EvidenceSourceType.MARKET,    confidence=85.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("risk_score",       40.0, EvidenceSourceType.RISK,      confidence=88.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("portfolio_risk",    2.0, EvidenceSourceType.RISK,      confidence=88.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("pe_ratio",         22.0, EvidenceSourceType.COMPANY,   confidence=80.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("roe",              18.0, EvidenceSourceType.COMPANY,   confidence=80.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("win_rate",          0.6, EvidenceSourceType.STRATEGY,  confidence=78.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("signal_strength",  75.0, EvidenceSourceType.STRATEGY,  confidence=78.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("news_sentiment",   65.0, EvidenceSourceType.KNOWLEDGE, confidence=70.0, decision_id=decision_id, subject_id=subject_id),
    ]
    return _snap(items, decision_id=decision_id, subject_id=subject_id, quality=85.0)


@pytest.fixture()
def minimal_evidence_snapshot(decision_id, subject_id) -> EvidenceSnapshot:
    items = [
        _ev_item("last_price", 500.0, EvidenceSourceType.MARKET, confidence=80.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("risk_score",  55.0, EvidenceSourceType.RISK,   confidence=80.0, decision_id=decision_id, subject_id=subject_id),
    ]
    return _snap(items, decision_id=decision_id, subject_id=subject_id, quality=60.0)


# ─── reasoning snapshots ─────────────────────────────────────────────────────

@pytest.fixture()
def rich_reasoning_snapshot(rich_evidence_snapshot) -> ReasoningSnapshot:
    return _build_reasoning_snap(rich_evidence_snapshot)


@pytest.fixture()
def minimal_reasoning_snapshot(minimal_evidence_snapshot) -> ReasoningSnapshot:
    return _build_reasoning_snap(minimal_evidence_snapshot)


# ─── factory fixtures ─────────────────────────────────────────────────────────

@pytest.fixture()
def make_evidence_snapshot():
    return _snap


@pytest.fixture()
def make_ev_item():
    return _ev_item

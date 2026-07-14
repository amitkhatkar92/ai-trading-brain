"""tests/unit/investment/decision/explainability/conftest.py
Shared fixtures for the Decision Explainability Engine test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.decision.confidence.decision_confidence_engine import (
    DecisionConfidenceEngine,
)
from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidenceSourceType,
    EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_snapshot import (
    EvidenceSnapshot,
    build_snapshot,
)
from iios.investment.decision.reasoning.decision_reasoning_engine import (
    DecisionReasoningEngine,
)
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.decision_risk_engine import DecisionRiskEngine
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot
from iios.investment.decision.explainability.explanation_generator import ExplainabilityInput


# ─── helpers ─────────────────────────────────────────────────────────────────

def _ev_item(
    key="price", value=100.0,
    src=EvidenceSourceType.MARKET,
    confidence=80.0,
    decision_id="D1",
    subject_id="INFY",
    freshness_score: float = 1.0,
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
        freshness_score=freshness_score,
    )


def _snap(items, decision_id="D1", subject_id="INFY", quality=80.0) -> EvidenceSnapshot:
    pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, "equity")
    pkg.add_items(items)
    pkg.seal()
    return build_snapshot(
        pkg, items, EvidenceValidationStatus.PASSED, quality, 1,
        datetime.now(timezone.utc),
    )


def _build_reasoning(ev: EvidenceSnapshot) -> ReasoningSnapshot:
    engine = DecisionReasoningEngine()
    engine.start()
    snap = engine.reason_sync(ev)
    engine.stop()
    return snap


def _build_confidence(ev: EvidenceSnapshot, rs: ReasoningSnapshot) -> ConfidenceSnapshot:
    engine = DecisionConfidenceEngine()
    engine.start()
    snap = engine.estimate_sync(ev, rs)
    engine.stop()
    return snap


def _build_risk(ev: EvidenceSnapshot, rs: ReasoningSnapshot, cs: ConfidenceSnapshot) -> RiskSnapshot:
    engine = DecisionRiskEngine()
    engine.start()
    snap = engine.evaluate_sync(ev, rs, cs)
    engine.stop()
    return snap


def _full_pipeline(ev: EvidenceSnapshot):
    rs = _build_reasoning(ev)
    cs = _build_confidence(ev, rs)
    ri = _build_risk(ev, rs, cs)
    return rs, cs, ri


# ─── basic fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def decision_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def subject_id() -> str:
    return "INFY"


# ─── evidence snapshots ───────────────────────────────────────────────────────

@pytest.fixture()
def rich_evidence_snapshot(decision_id, subject_id) -> EvidenceSnapshot:
    items = [
        _ev_item("last_price",     1500.0, EvidenceSourceType.MARKET,   confidence=90.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("rsi_14",           55.0, EvidenceSourceType.MARKET,   confidence=85.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("volume",          1e6,   EvidenceSourceType.MARKET,   confidence=88.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("bid_ask_spread",   0.05, EvidenceSourceType.MARKET,   confidence=82.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("market_cap",      1e10,  EvidenceSourceType.MARKET,   confidence=88.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("pe_ratio",         22.0, EvidenceSourceType.COMPANY,  confidence=80.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("roe",              18.0, EvidenceSourceType.COMPANY,  confidence=80.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("revenue_growth",    0.1, EvidenceSourceType.COMPANY,  confidence=75.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("win_rate",          0.6, EvidenceSourceType.STRATEGY, confidence=78.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("sharpe_ratio",      1.2, EvidenceSourceType.STRATEGY, confidence=78.0, decision_id=decision_id, subject_id=subject_id),
        _ev_item("signal_strength",  75.0, EvidenceSourceType.STRATEGY, confidence=78.0, decision_id=decision_id, subject_id=subject_id),
    ]
    return _snap(items, decision_id=decision_id, subject_id=subject_id, quality=85.0)


@pytest.fixture()
def minimal_evidence_snapshot(decision_id, subject_id) -> EvidenceSnapshot:
    items = [
        _ev_item("last_price", 500.0, EvidenceSourceType.MARKET, confidence=80.0, decision_id=decision_id, subject_id=subject_id),
    ]
    return _snap(items, decision_id=decision_id, subject_id=subject_id, quality=50.0)


# ─── full pipeline snapshots ─────────────────────────────────────────────────

@pytest.fixture()
def rich_reasoning_snapshot(rich_evidence_snapshot) -> ReasoningSnapshot:
    return _build_reasoning(rich_evidence_snapshot)


@pytest.fixture()
def rich_confidence_snapshot(rich_evidence_snapshot, rich_reasoning_snapshot) -> ConfidenceSnapshot:
    return _build_confidence(rich_evidence_snapshot, rich_reasoning_snapshot)


@pytest.fixture()
def rich_risk_snapshot(
    rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
) -> RiskSnapshot:
    return _build_risk(
        rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    )


@pytest.fixture()
def minimal_reasoning_snapshot(minimal_evidence_snapshot) -> ReasoningSnapshot:
    return _build_reasoning(minimal_evidence_snapshot)


@pytest.fixture()
def minimal_confidence_snapshot(
    minimal_evidence_snapshot, minimal_reasoning_snapshot,
) -> ConfidenceSnapshot:
    return _build_confidence(minimal_evidence_snapshot, minimal_reasoning_snapshot)


@pytest.fixture()
def minimal_risk_snapshot(
    minimal_evidence_snapshot, minimal_reasoning_snapshot, minimal_confidence_snapshot,
) -> RiskSnapshot:
    return _build_risk(
        minimal_evidence_snapshot, minimal_reasoning_snapshot, minimal_confidence_snapshot,
    )


# ─── ExplainabilityInput fixtures ────────────────────────────────────────────

@pytest.fixture()
def rich_input(
    rich_evidence_snapshot,
    rich_reasoning_snapshot,
    rich_confidence_snapshot,
    rich_risk_snapshot,
) -> ExplainabilityInput:
    return ExplainabilityInput(
        evidence_snapshot   = rich_evidence_snapshot,
        reasoning_snapshot  = rich_reasoning_snapshot,
        confidence_snapshot = rich_confidence_snapshot,
        risk_snapshot       = rich_risk_snapshot,
    )


@pytest.fixture()
def minimal_input(
    minimal_evidence_snapshot,
    minimal_reasoning_snapshot,
    minimal_confidence_snapshot,
    minimal_risk_snapshot,
) -> ExplainabilityInput:
    return ExplainabilityInput(
        evidence_snapshot   = minimal_evidence_snapshot,
        reasoning_snapshot  = minimal_reasoning_snapshot,
        confidence_snapshot = minimal_confidence_snapshot,
        risk_snapshot       = minimal_risk_snapshot,
    )


# ─── factory fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def make_ev_item():
    return _ev_item


@pytest.fixture()
def make_evidence_snapshot():
    return _snap

"""tests/unit/investment/decision/committee/conftest.py
Shared fixtures for the Committee Engine test suite.
Reuses upstream engines to build real snapshots (no mocks).
"""
from __future__ import annotations

import uuid

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
from iios.investment.decision.explainability.decision_explainability_engine import (
    DecisionExplainabilityEngine,
)
from iios.investment.decision.explainability.explanation_generator import ExplainabilityInput
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.decision_reasoning_engine import (
    DecisionReasoningEngine,
)
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.decision_risk_engine import DecisionRiskEngine
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_member import (
    CommitteeMember,
    RiskIntelligenceMember,
)
from iios.investment.decision.committee.member_registry import MemberRegistry
from iios.investment.decision.committee.member_roles import MemberRole
from datetime import datetime, timezone


# ─── helpers ─────────────────────────────────────────────────────────────────

def _ev_item(
    key="price", value=100.0,
    src=EvidenceSourceType.MARKET,
    category=EvidenceCategory.TECHNICAL,
    confidence=80.0,
    decision_id="D1",
    subject_id="INFY",
    freshness_score: float = 0.9,
):
    return make_evidence_item(
        decision_id=decision_id,
        source_type=src,
        source_provider="test_provider",
        subject_id=subject_id,
        subject_type="equity",
        category=category,
        key=key,
        value=value,
        confidence=confidence,
        freshness_score=freshness_score,
    )


def _build_all(items, decision_id, subject_id):
    pkg = EvidencePackage(str(uuid.uuid4()), decision_id, subject_id, "equity")
    pkg.add_items(items)
    pkg.seal()
    ev = build_snapshot(
        pkg, items, EvidenceValidationStatus.PASSED, 80.0, 1,
        datetime.now(timezone.utc),
    )
    re_engine = DecisionReasoningEngine(); re_engine.start()
    rs = re_engine.reason_sync(ev); re_engine.stop()

    cf_engine = DecisionConfidenceEngine(); cf_engine.start()
    cs = cf_engine.estimate_sync(ev, rs); cf_engine.stop()

    rk_engine = DecisionRiskEngine(); rk_engine.start()
    ri = rk_engine.evaluate_sync(ev, rs, cs); rk_engine.stop()

    ex_engine = DecisionExplainabilityEngine(); ex_engine.start()
    snap = ex_engine.explain_sync(ev, rs, cs, ri, decision_id)
    ex_engine.stop()
    return ev, rs, cs, ri, snap


# ─── decision_id / subject_id ─────────────────────────────────────────────────

@pytest.fixture()
def decision_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def subject_id() -> str:
    return "INFY"


# ─── rich snapshots (11 evidence items) ──────────────────────────────────────

@pytest.fixture(scope="session")
def _rich_pipeline():
    did = str(uuid.uuid4())
    sid = "INFY"
    items = [
        _ev_item("last_price", 1500.0, EvidenceSourceType.MARKET,   EvidenceCategory.TECHNICAL,    90.0, did, sid),
        _ev_item("rsi_14",       55.0, EvidenceSourceType.MARKET,   EvidenceCategory.TECHNICAL,    85.0, did, sid),
        _ev_item("volume",       1e6,  EvidenceSourceType.MARKET,   EvidenceCategory.QUANTITATIVE, 88.0, did, sid),
        _ev_item("spread",      0.05,  EvidenceSourceType.MARKET,   EvidenceCategory.TECHNICAL,    82.0, did, sid),
        _ev_item("mkt_cap",     1e10,  EvidenceSourceType.MARKET,   EvidenceCategory.QUANTITATIVE, 88.0, did, sid),
        _ev_item("pe_ratio",    22.0,  EvidenceSourceType.COMPANY,  EvidenceCategory.FUNDAMENTAL,  80.0, did, sid),
        _ev_item("roe",         18.0,  EvidenceSourceType.COMPANY,  EvidenceCategory.FUNDAMENTAL,  80.0, did, sid),
        _ev_item("rev_growth",   0.1,  EvidenceSourceType.COMPANY,  EvidenceCategory.FUNDAMENTAL,  75.0, did, sid),
        _ev_item("win_rate",     0.6,  EvidenceSourceType.STRATEGY, EvidenceCategory.QUANTITATIVE, 78.0, did, sid),
        _ev_item("sharpe",       1.2,  EvidenceSourceType.STRATEGY, EvidenceCategory.QUANTITATIVE, 78.0, did, sid),
        _ev_item("signal",      75.0,  EvidenceSourceType.STRATEGY, EvidenceCategory.QUANTITATIVE, 78.0, did, sid),
    ]
    return _build_all(items, did, sid)


@pytest.fixture()
def rich_evidence_snapshot(_rich_pipeline) -> EvidenceSnapshot:
    return _rich_pipeline[0]


@pytest.fixture()
def rich_reasoning_snapshot(_rich_pipeline) -> ReasoningSnapshot:
    return _rich_pipeline[1]


@pytest.fixture()
def rich_confidence_snapshot(_rich_pipeline) -> ConfidenceSnapshot:
    return _rich_pipeline[2]


@pytest.fixture()
def rich_risk_snapshot(_rich_pipeline) -> RiskSnapshot:
    return _rich_pipeline[3]


@pytest.fixture()
def rich_explanation_snapshot(_rich_pipeline) -> ExplanationSnapshot:
    return _rich_pipeline[4]


@pytest.fixture()
def rich_context(_rich_pipeline) -> CommitteeContext:
    ev, rs, cs, ri, ex = _rich_pipeline
    return CommitteeContext(
        decision_id  = ev.subject_id + "_DEC",
        subject_id   = ev.subject_id,
        subject_type = "equity",
        evidence     = ev,
        reasoning    = rs,
        confidence   = cs,
        risk         = ri,
        explanation  = ex,
    )


# ─── minimal snapshots (1 item) ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def _minimal_pipeline():
    did = str(uuid.uuid4())
    sid = "TCS"
    items = [
        _ev_item("last_price", 500.0, EvidenceSourceType.MARKET, EvidenceCategory.TECHNICAL, 70.0, did, sid),
    ]
    return _build_all(items, did, sid)


@pytest.fixture()
def minimal_context(_minimal_pipeline) -> CommitteeContext:
    ev, rs, cs, ri, ex = _minimal_pipeline
    return CommitteeContext(
        decision_id  = ev.subject_id + "_DEC",
        subject_id   = ev.subject_id,
        subject_type = "equity",
        evidence     = ev,
        reasoning    = rs,
        confidence   = cs,
        risk         = ri,
        explanation  = ex,
    )


# ─── default registry ─────────────────────────────────────────────────────────

@pytest.fixture()
def default_registry() -> MemberRegistry:
    return MemberRegistry.default_committee()

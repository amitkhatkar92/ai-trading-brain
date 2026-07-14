"""tests/unit/investment/decision/integration/conftest.py
Shared fixtures for the Integration Engine test suite.
Reuses upstream engines to produce real snapshots.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from iios.investment.decision.confidence.decision_confidence_engine import (
    DecisionConfidenceEngine,
)
from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidenceSourceType,
    EvidenceValidationStatus,
)
from iios.investment.decision.evidence.evidence_item import make_evidence_item
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_snapshot import build_snapshot
from iios.investment.decision.explainability.decision_explainability_engine import (
    DecisionExplainabilityEngine,
)
from iios.investment.decision.reasoning.decision_reasoning_engine import (
    DecisionReasoningEngine,
)
from iios.investment.decision.risk.decision_risk_engine import DecisionRiskEngine

from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.committee_context import CommitteeContext


def _item(key, value, src, cat, conf, did, sid, freshness=0.9):
    return make_evidence_item(
        decision_id=did, source_type=src, source_provider="test",
        subject_id=sid, subject_type="equity", category=cat,
        key=key, value=value, confidence=conf, freshness_score=freshness,
    )


def _build_pipeline(items, did, sid):
    pkg = EvidencePackage(str(uuid.uuid4()), did, sid, "equity")
    pkg.add_items(items)
    pkg.seal()
    ev = build_snapshot(
        pkg, items, EvidenceValidationStatus.PASSED, 80.0, 1,
        datetime.now(timezone.utc),
    )
    re_eng = DecisionReasoningEngine(); re_eng.start()
    rs = re_eng.reason_sync(ev); re_eng.stop()
    cf_eng = DecisionConfidenceEngine(); cf_eng.start()
    cs = cf_eng.estimate_sync(ev, rs); cf_eng.stop()
    rk_eng = DecisionRiskEngine(); rk_eng.start()
    ri = rk_eng.evaluate_sync(ev, rs, cs); rk_eng.stop()
    ex_eng = DecisionExplainabilityEngine(); ex_eng.start()
    snap = ex_eng.explain_sync(ev, rs, cs, ri, did); ex_eng.stop()
    return ev, rs, cs, ri, snap


@pytest.fixture(scope="session")
def _rich_pipeline():
    did = str(uuid.uuid4())
    sid = "RELIANCE"
    items = [
        _item("last_price", 2400.0, EvidenceSourceType.MARKET,   EvidenceCategory.TECHNICAL,    90.0, did, sid),
        _item("rsi_14",       52.0, EvidenceSourceType.MARKET,   EvidenceCategory.TECHNICAL,    85.0, did, sid),
        _item("volume",        2e6, EvidenceSourceType.MARKET,   EvidenceCategory.QUANTITATIVE, 85.0, did, sid),
        _item("pe_ratio",     18.0, EvidenceSourceType.COMPANY,  EvidenceCategory.FUNDAMENTAL,  80.0, did, sid),
        _item("roe",          22.0, EvidenceSourceType.COMPANY,  EvidenceCategory.FUNDAMENTAL,  80.0, did, sid),
        _item("win_rate",      0.6, EvidenceSourceType.STRATEGY, EvidenceCategory.QUANTITATIVE, 78.0, did, sid),
        _item("sharpe",        1.3, EvidenceSourceType.STRATEGY, EvidenceCategory.QUANTITATIVE, 78.0, did, sid),
        _item("signal",       72.0, EvidenceSourceType.STRATEGY, EvidenceCategory.QUANTITATIVE, 78.0, did, sid),
    ]
    ev, rs, cs, ri, ex = _build_pipeline(items, did, sid)
    ctx = CommitteeContext(
        decision_id=did + "_DEC", subject_id=sid, subject_type="equity",
        evidence=ev, reasoning=rs, confidence=cs, risk=ri, explanation=ex,
    )
    cm = CommitteeSession(ctx.decision_id, ctx).run()
    return did, sid, ev, rs, cs, ri, ex, cm


@pytest.fixture(scope="session")
def _minimal_pipeline():
    did = str(uuid.uuid4())
    sid = "TCS"
    items = [
        _item("last_price", 3000.0, EvidenceSourceType.MARKET, EvidenceCategory.TECHNICAL, 65.0, did, sid),
    ]
    return _build_pipeline(items, did, sid)


@pytest.fixture()
def rich_all(_rich_pipeline):
    did, sid, ev, rs, cs, ri, ex, cm = _rich_pipeline
    return did, sid, ev, rs, cs, ri, ex, cm


@pytest.fixture()
def minimal_all(_minimal_pipeline):
    did, sid, ev, rs, cs, ri, ex = _minimal_pipeline[:5], _minimal_pipeline[2], *_minimal_pipeline
    return _minimal_pipeline


@pytest.fixture()
def decision_id():
    return str(uuid.uuid4())

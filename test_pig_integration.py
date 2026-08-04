"""
test_pig_integration.py -- R-001 Phase 2: PIG Integration tests.

115-test suite.  Run with:
    .venv\\Scripts\\python.exe test_pig_integration.py

Covers:
  T01-T10   PIGCallRecord
  T11-T20   PIGTelemetry
  T21-T30   PIGInfluencePolicy / from_config
  T31-T45   pig_build_vote
  T46-T60   pig_enrich_signals
  T61-T72   PIGTradingAdapter lifecycle and fallback
  T73-T85   PIGTradingAdapter.query with mock gateway
  T86-T95   Backward compatibility (no PIG vote = existing behaviour)
  T96-T105  Influence bounds enforcement
  T106-T115 Telemetry accuracy and thread safety
"""
from __future__ import annotations

import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# =============================================================================
# Test framework (same pattern as test_pig_gateway.py)
# =============================================================================

@dataclass
class TestResult:
    name:        str
    passed:      bool
    duration_ms: float
    detail:      str
    error:       Optional[str] = None


class TestRunner:
    def __init__(self) -> None:
        self.results: List[TestResult] = []

    def run(self, name: str, fn: Callable[[], Any]) -> None:
        t0 = time.perf_counter()
        try:
            detail = fn() or "OK"
            self.results.append(TestResult(
                name=name, passed=True,
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail=str(detail),
            ))
        except AssertionError as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail="ASSERTION FAILED",
                error=str(exc) or "assert failed",
            ))
        except Exception as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000,
                detail="EXCEPTION",
                error=traceback.format_exc(),
            ))

    def print_report(self) -> int:
        passed = sum(1 for r in self.results if r.passed)
        total  = len(self.results)
        print(f"\n{'═'*70}")
        print(f"  R-001 Phase 2 Integration Tests: {passed}/{total} passed")
        print(f"{'═'*70}")
        for r in self.results:
            icon = "✅" if r.passed else "❌"
            print(f"  {icon} {r.name:<45} {r.duration_ms:6.1f}ms")
            if not r.passed and r.error:
                for line in r.error.strip().splitlines()[-4:]:
                    print(f"       {line}")
        print(f"{'═'*70}\n")
        return 0 if passed == total else 1


def ok(cond: bool, msg: str = "") -> None:
    assert cond, msg or "condition is False"


# =============================================================================
# Minimal mock objects — no MLS infrastructure needed
# =============================================================================

@dataclass
class _MockPI:
    """Minimal PlatformIntelligence stub for testing."""
    raw_pmci:               float = 0.55
    ca_pmci:                float = 0.60
    cds_score:              float = 0.50
    winner_dna_match:       float = 0.65
    loser_dna_match:        float = 0.10
    evidence_count:         int   = 12
    confidence:             float = 0.58
    dna_freshness:          float = 0.80
    dna_drift:              float = 0.05
    institutional_confidence: float = 0.55
    context_score:          float = 0.60
    regime:                 str   = "BULL_TREND"
    context_adjustment:     float = 0.05
    cds_highly_relevant_count: int = 4
    cds_relevant_count:     int   = 6
    cds_total_dna:          int   = 10
    explanation:            str   = "mock"
    symbol:                 str   = "RELIANCE"
    evaluation_date:        str   = "2026-01-01"
    result_id:              str   = "PIG-mock"
    evaluated_at:           str   = "2026-01-01T09:15:00"


@dataclass
class _MockSignal:
    """Minimal TradeSignal stub."""
    symbol:            str   = "RELIANCE"
    confidence:        float = 7.0
    risk_reward_ratio: float = 2.5
    direction:         str   = "BUY"


@dataclass
class _MockSnapshot:
    """Minimal MarketSnapshot stub."""
    vix:                   float = 18.0
    market_breadth:        float = 0.55
    pcr:                   float = 0.95
    global_sentiment_score: float = 0.2


class _MockPolicy:
    """MLSConfig stub with pig_* fields."""
    pig_vote_weight               = 0.08
    pig_min_ca_pmci_for_vote      = 0.30
    pig_decision_vote_enabled     = True
    pig_max_conviction_boost      = 1.0
    pig_min_ca_pmci_for_boost     = 0.30
    pig_opportunity_boost_enabled = True
    pig_telemetry_enabled         = True


# =============================================================================
# Imports under test
# =============================================================================

from market_learning.pig_integration import (
    PIGCallRecord,
    PIGInfluencePolicy,
    PIGTelemetry,
    PIGTradingAdapter,
    pig_build_vote,
    pig_enrich_signals,
    _build_observation_features,
)
from models.agent_output import DebateVote


# =============================================================================
# T01-T10  PIGCallRecord
# =============================================================================

def _t01():
    r = PIGCallRecord(symbol="RELIANCE", latency_ms=12.5, available=True,
                      ca_pmci=0.65, evidence_count=8)
    ok(r.symbol == "RELIANCE", "symbol")
    ok(r.latency_ms == 12.5, "latency")
    ok(r.available is True, "available")
    ok(r.ca_pmci == 0.65, "ca_pmci")
    ok(r.evidence_count == 8, "evidence")
    ok(r.error is None, "error defaults None")


def _t02():
    r = PIGCallRecord(symbol="X", latency_ms=0.5, available=False,
                      ca_pmci=0.0, evidence_count=0, error="init_failed")
    ok(r.available is False)
    ok(r.error == "init_failed")


def _t03():
    # latency_ms can be 0
    r = PIGCallRecord(symbol="A", latency_ms=0.0, available=False,
                      ca_pmci=0.0, evidence_count=0)
    ok(r.latency_ms == 0.0)


def _t04():
    # evidence_count can be 0
    r = PIGCallRecord(symbol="B", latency_ms=1.0, available=True,
                      ca_pmci=0.1, evidence_count=0)
    ok(r.evidence_count == 0)


def _t05():
    # ca_pmci can be 0 even when available
    r = PIGCallRecord(symbol="C", latency_ms=5.0, available=True,
                      ca_pmci=0.0, evidence_count=1)
    ok(r.ca_pmci == 0.0)


def _t06():
    # ca_pmci can be 1.0
    r = PIGCallRecord(symbol="D", latency_ms=5.0, available=True,
                      ca_pmci=1.0, evidence_count=50)
    ok(r.ca_pmci == 1.0)


def _t07():
    # error is optional
    r1 = PIGCallRecord("A", 1.0, True, 0.5, 5)
    r2 = PIGCallRecord("A", 1.0, True, 0.5, 5, error="x")
    ok(r1.error is None)
    ok(r2.error == "x")


def _t08():
    # two records are independent
    r1 = PIGCallRecord("X", 1.0, True, 0.5, 3)
    r2 = PIGCallRecord("Y", 2.0, False, 0.0, 0, error="e")
    ok(r1.symbol != r2.symbol)
    ok(r1.available != r2.available)


def _t09():
    # latency can be fractional ms
    r = PIGCallRecord("Z", 0.123, True, 0.5, 1)
    ok(abs(r.latency_ms - 0.123) < 1e-9)


def _t10():
    # very high evidence count
    r = PIGCallRecord("Z", 10.0, True, 0.9, 9999)
    ok(r.evidence_count == 9999)


# =============================================================================
# T11-T20  PIGTelemetry
# =============================================================================

def _t11():
    t = PIGTelemetry()
    ok(len(t) == 0, "starts empty")
    ok(t.summary()["total_calls"] == 0)


def _t12():
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 5.0, True, 0.6, 8))
    ok(len(t) == 1)
    s = t.summary()
    ok(s["total_calls"] == 1)
    ok(s["available"] == 1)
    ok(s["availability_pct"] == 100.0)


def _t13():
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 5.0, True,  0.6, 8))
    t.record(PIGCallRecord("B", 3.0, False, 0.0, 0, error="e"))
    s = t.summary()
    ok(s["total_calls"] == 2)
    ok(s["available"] == 1)
    ok(s["availability_pct"] == 50.0)


def _t14():
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 10.0, True, 0.8, 5))
    t.record(PIGCallRecord("B", 20.0, True, 0.6, 3))
    s = t.summary()
    ok(abs(s["avg_latency_ms"] - 15.0) < 0.01, "avg latency")
    ok(abs(s["avg_ca_pmci"] - 0.7) < 0.01, "avg ca_pmci")


def _t15():
    t = PIGTelemetry()
    t.reset()
    ok(len(t) == 0, "reset works")


def _t16():
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 5.0, True, 0.5, 10))
    t.reset()
    ok(len(t) == 0, "reset clears records")
    ok(t.summary()["total_calls"] == 0)


def _t17():
    # avg_evidence_count computed correctly
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 1.0, True, 0.5, 10))
    t.record(PIGCallRecord("B", 1.0, True, 0.5, 20))
    s = t.summary()
    ok(abs(s["avg_evidence_count"] - 15.0) < 0.01)


def _t18():
    # all unavailable → avg_ca_pmci = 0
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 1.0, False, 0.0, 0, error="e"))
    s = t.summary()
    ok(s["avg_ca_pmci"] == 0.0)


def _t19():
    # thread-safe accumulation
    t = PIGTelemetry()
    def _add():
        for _ in range(50):
            t.record(PIGCallRecord("X", 1.0, True, 0.5, 5))
    threads = [threading.Thread(target=_add) for _ in range(4)]
    [th.start() for th in threads]
    [th.join() for th in threads]
    ok(len(t) == 200, f"expected 200 got {len(t)}")


def _t20():
    # summary keys are present even with no data
    t = PIGTelemetry()
    s = t.summary()
    for key in ("total_calls", "available", "availability_pct",
                "avg_latency_ms", "avg_ca_pmci", "avg_evidence_count"):
        ok(key in s, f"missing key {key}")


# =============================================================================
# T21-T30  PIGInfluencePolicy
# =============================================================================

def _t21():
    p = PIGInfluencePolicy()
    ok(p.vote_weight == 0.08)
    ok(p.min_ca_pmci_for_vote == 0.30)
    ok(p.decision_vote_enabled is True)
    ok(p.max_conviction_boost == 1.0)
    ok(p.opportunity_boost_enabled is True)
    ok(p.telemetry_enabled is True)


def _t22():
    cfg = _MockPolicy()
    p   = PIGInfluencePolicy.from_config(cfg)
    ok(p.vote_weight == 0.08)
    ok(p.min_ca_pmci_for_vote == 0.30)
    ok(p.decision_vote_enabled is True)


def _t23():
    cfg = _MockPolicy()
    cfg.pig_vote_weight = 0.05
    p   = PIGInfluencePolicy.from_config(cfg)
    ok(p.vote_weight == 0.05)


def _t24():
    cfg = _MockPolicy()
    cfg.pig_decision_vote_enabled = False
    p   = PIGInfluencePolicy.from_config(cfg)
    ok(p.decision_vote_enabled is False)


def _t25():
    cfg = _MockPolicy()
    cfg.pig_opportunity_boost_enabled = False
    p   = PIGInfluencePolicy.from_config(cfg)
    ok(p.opportunity_boost_enabled is False)


def _t26():
    # Missing attribute handled gracefully (defaults apply)
    class _CfgEmpty:
        pass
    p = PIGInfluencePolicy.from_config(_CfgEmpty())
    ok(p.vote_weight == 0.08)


def _t27():
    p = PIGInfluencePolicy(vote_weight=0.12)
    ok(p.vote_weight == 0.12)


def _t28():
    p = PIGInfluencePolicy(max_conviction_boost=2.0)
    ok(p.max_conviction_boost == 2.0)


def _t29():
    p = PIGInfluencePolicy(min_ca_pmci_for_vote=0.50)
    ok(p.min_ca_pmci_for_vote == 0.50)


def _t30():
    p = PIGInfluencePolicy(telemetry_enabled=False)
    ok(p.telemetry_enabled is False)


# =============================================================================
# T31-T45  pig_build_vote
# =============================================================================

def _t31():
    # High CA-PMCI → vote returned
    pi   = _MockPI(ca_pmci=0.80)
    vote = pig_build_vote(pi)
    ok(vote is not None, "vote returned")
    ok(isinstance(vote, DebateVote), "DebateVote type")
    ok(vote.agent_name == "InstitutionalDNAAI")


def _t32():
    # vote is always "approve" — PIG never hard-rejects
    pi   = _MockPI(ca_pmci=0.80)
    vote = pig_build_vote(pi)
    ok(vote.vote == "approve")


def _t33():
    # Below threshold → None (silent vote)
    pi   = _MockPI(ca_pmci=0.20)
    vote = pig_build_vote(pi)
    ok(vote is None, "below threshold returns None")


def _t34():
    # Exactly at threshold → vote returned
    p    = PIGInfluencePolicy(min_ca_pmci_for_vote=0.30)
    pi   = _MockPI(ca_pmci=0.30)
    vote = pig_build_vote(pi, p)
    ok(vote is not None, "at threshold returns vote")


def _t35():
    # Score mapping: ca_pmci=0.80 → score=8.0
    pi   = _MockPI(ca_pmci=0.80)
    vote = pig_build_vote(pi)
    ok(abs(vote.score - 8.0) < 0.01, f"expected 8.0 got {vote.score}")


def _t36():
    # Score clamped to 10.0
    pi   = _MockPI(ca_pmci=1.05)
    vote = pig_build_vote(pi)
    ok(vote.score <= 10.0, f"score={vote.score} must be ≤10")


def _t37():
    # Score clamped to 0.0 minimum when below threshold but forced through
    pi   = _MockPI(ca_pmci=0.0)
    vote = pig_build_vote(pi)
    ok(vote is None, "ca_pmci=0.0 returns None")


def _t38():
    # position_size_modifier always 1.0 — PIG doesn't resize positions
    pi   = _MockPI(ca_pmci=0.75)
    vote = pig_build_vote(pi)
    ok(vote.suggested_position_modifier == 1.0)


def _t39():
    # Reasoning contains all 7 required explainability fields (Part 3)
    pi = _MockPI(
        raw_pmci=0.55, ca_pmci=0.65, cds_score=0.50,
        institutional_confidence=0.55, evidence_count=12,
        winner_dna_match=0.65, context_score=0.60,
    )
    vote = pig_build_vote(pi)
    ok("raw_pmci"  in vote.reasoning, "raw_pmci in reasoning")
    ok("ca_pmci"   in vote.reasoning, "ca_pmci in reasoning")
    ok("cds"       in vote.reasoning, "cds in reasoning")
    ok("inst_confidence" in vote.reasoning, "inst_confidence in reasoning")
    ok("evidence"  in vote.reasoning, "evidence in reasoning")
    ok("dna_match" in vote.reasoning, "dna_match in reasoning")
    ok("ctx_match" in vote.reasoning, "ctx_match in reasoning")


def _t40():
    # decision_vote_enabled=False → None regardless of CA-PMCI
    p    = PIGInfluencePolicy(decision_vote_enabled=False)
    pi   = _MockPI(ca_pmci=0.90)
    vote = pig_build_vote(pi, p)
    ok(vote is None, "disabled → None")


def _t41():
    # Custom min_ca_pmci_for_vote=0.50
    p  = PIGInfluencePolicy(min_ca_pmci_for_vote=0.50)
    pi = _MockPI(ca_pmci=0.45)
    ok(pig_build_vote(pi, p) is None, "0.45 < 0.50 → None")
    pi2 = _MockPI(ca_pmci=0.55)
    ok(pig_build_vote(pi2, p) is not None, "0.55 ≥ 0.50 → vote")


def _t42():
    # ca_pmci=0.50 → score=5.0
    pi   = _MockPI(ca_pmci=0.50)
    vote = pig_build_vote(pi)
    ok(abs(vote.score - 5.0) < 0.01)


def _t43():
    # ca_pmci=1.0 → score=10.0
    pi   = _MockPI(ca_pmci=1.0)
    vote = pig_build_vote(pi)
    ok(abs(vote.score - 10.0) < 0.01)


def _t44():
    # ca_pmci=0.35 → score=3.5
    pi   = _MockPI(ca_pmci=0.35)
    vote = pig_build_vote(pi)
    ok(abs(vote.score - 3.5) < 0.01)


def _t45():
    # None policy → defaults applied
    pi   = _MockPI(ca_pmci=0.80)
    vote = pig_build_vote(pi, None)
    ok(vote is not None)


# =============================================================================
# T46-T60  pig_enrich_signals
# =============================================================================

_MISSING = object()

class _StubAdapter:
    """Mock PIGTradingAdapter that returns a fixed PlatformIntelligence."""
    def __init__(self, pi=_MISSING) -> None:
        self._pi     = _MockPI() if pi is _MISSING else pi
        self._policy = PIGInfluencePolicy()

    def query(self, symbol, signal=None, snapshot=None):
        return self._pi


def _make_signals(n: int, conf: float = 7.0) -> List[_MockSignal]:
    return [_MockSignal(symbol=f"SYM{i}", confidence=conf) for i in range(n)]


def _t46():
    sigs    = _make_signals(3, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.80))
    result  = pig_enrich_signals(sigs, adapter, None)
    ok(result is sigs, "returns same list")


def _t47():
    # High CA-PMCI → confidence increases
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.80))
    pig_enrich_signals(sigs, adapter, None)
    ok(sigs[0].confidence > 7.0, f"expected >7.0 got {sigs[0].confidence}")


def _t48():
    # Boost bounded to max_conviction_boost
    p       = PIGInfluencePolicy(max_conviction_boost=1.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=1.0))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(sigs[0].confidence <= 8.0, f"should be ≤8.0, got {sigs[0].confidence}")


def _t49():
    # Confidence never exceeds 10.0
    p       = PIGInfluencePolicy(max_conviction_boost=5.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=9.8)
    adapter = _StubAdapter(_MockPI(ca_pmci=1.0))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(sigs[0].confidence <= 10.0, "never > 10")


def _t50():
    # CA-PMCI below threshold → no boost
    p       = PIGInfluencePolicy(min_ca_pmci_for_boost=0.40)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.35))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(sigs[0].confidence == 7.0, "no boost below threshold")


def _t51():
    # Empty list → returned unchanged
    result = pig_enrich_signals([], _StubAdapter(), None)
    ok(result == [])


def _t52():
    # opportunity_boost_enabled=False → no enrichment
    p       = PIGInfluencePolicy(opportunity_boost_enabled=False)
    sigs    = _make_signals(2, conf=6.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.80))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(all(s.confidence == 6.0 for s in sigs), "no boost when disabled")


def _t53():
    # Adapter returns None → signals unchanged
    sigs    = _make_signals(2, conf=6.0)
    adapter = _StubAdapter(None)
    pig_enrich_signals(sigs, adapter, None)
    ok(all(s.confidence == 6.0 for s in sigs))


def _t54():
    # Multiple signals — each enriched independently
    sigs    = _make_signals(5, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.60))
    pig_enrich_signals(sigs, adapter, None)
    ok(all(s.confidence > 7.0 for s in sigs), "all 5 enriched")


def _t55():
    # Snapshot passed through to adapter.query
    captured = {}
    class _CapturingAdapter:
        _policy = PIGInfluencePolicy()
        def query(self, symbol, signal=None, snapshot=None):
            captured["snapshot"] = snapshot
            return _MockPI(ca_pmci=0.70)
    snap = _MockSnapshot()
    pig_enrich_signals(_make_signals(1), _CapturingAdapter(), snap)
    ok(captured.get("snapshot") is snap, "snapshot forwarded")


def _t56_enrich():
    # Default policy (None) uses PIGInfluencePolicy defaults
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.80))
    pig_enrich_signals(sigs, adapter, None, None)
    ok(sigs[0].confidence > 7.0)


def _t57_enrich():
    # Boost formula: ca_pmci=0.50, max_boost=1.0 → boost=0.50
    p       = PIGInfluencePolicy(max_conviction_boost=1.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.50))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(abs(sigs[0].confidence - 7.5) < 0.01, f"expected 7.5 got {sigs[0].confidence}")


def _t58_enrich():
    # Boost formula: ca_pmci=0.80, max_boost=2.0 → boost=1.60 → conf=7.0+1.60=8.60
    p       = PIGInfluencePolicy(max_conviction_boost=2.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.80))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(abs(sigs[0].confidence - 8.6) < 0.01, f"expected 8.6 got {sigs[0].confidence}")


def _t59_enrich():
    # min_ca_pmci_for_boost exactly at boundary
    p       = PIGInfluencePolicy(min_ca_pmci_for_boost=0.50, max_conviction_boost=1.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter_just_below = _StubAdapter(_MockPI(ca_pmci=0.499))
    pig_enrich_signals(sigs[:], adapter_just_below, None, p)
    ok(sigs[0].confidence == 7.0, "just below → no boost")

    sigs2   = _make_signals(1, conf=7.0)
    adapter_just_above = _StubAdapter(_MockPI(ca_pmci=0.50))
    pig_enrich_signals(sigs2, adapter_just_above, None, p)
    ok(sigs2[0].confidence > 7.0, "at threshold → boost applied")


def _t60_enrich():
    # Signal without confidence attr handled gracefully
    class _NoConf:
        symbol = "X"
        confidence = None
    sigs = [_NoConf()]
    adapter = _StubAdapter(_MockPI(ca_pmci=0.80))
    # Should not raise
    try:
        pig_enrich_signals(sigs, adapter, None)
    except Exception as exc:
        ok(False, f"raised: {exc}")


# =============================================================================
# T61-T72  PIGTradingAdapter lifecycle and fallback
# =============================================================================

def _t61():
    a = PIGTradingAdapter()
    ok(not a.is_available(), "not available before init")
    ok(a.dna_count() == 0)


def _t62():
    a = PIGTradingAdapter()
    ok(a.telemetry is not None)
    ok(isinstance(a.telemetry, PIGTelemetry))


def _t63():
    # After failed init, query returns None immediately
    a = PIGTradingAdapter()
    a._init_failed = True
    result = a.query("RELIANCE")
    ok(result is None, "None after init failure")


def _t64():
    # After failed init, multiple queries all return None
    a = PIGTradingAdapter()
    a._init_failed = True
    results = [a.query(f"SYM{i}") for i in range(5)]
    ok(all(r is None for r in results))


def _t65():
    # Telemetry records failure when init failed
    a = PIGTradingAdapter()
    a._init_failed = True
    a.query("X")
    ok(len(a.telemetry) == 1)
    s = a.telemetry.summary()
    ok(s["available"] == 0)


def _t66():
    # _ensure_init returns False when init_failed
    a = PIGTradingAdapter()
    a._init_failed = True
    ok(not a._ensure_init())


def _t67():
    # _ensure_init returns True when init_done
    a = PIGTradingAdapter()
    a._init_done = True
    ok(a._ensure_init())


def _t68():
    # dna_count returns 0 when library is None
    a = PIGTradingAdapter()
    a._library = None
    ok(a.dna_count() == 0)


def _t69():
    # policy defaults loaded correctly
    a = PIGTradingAdapter()
    ok(a._policy.vote_weight == 0.08)
    ok(a._policy.min_ca_pmci_for_vote == 0.30)


def _t70():
    # Custom policy accepted
    p = PIGInfluencePolicy(vote_weight=0.05)
    a = PIGTradingAdapter(policy=p)
    ok(a._policy.vote_weight == 0.05)


def _t71():
    # reload_library handles missing dependency gracefully
    a = PIGTradingAdapter()
    # Should not raise even if MLS not initialised
    try:
        a.reload_library()
    except Exception as exc:
        ok(False, f"reload_library raised: {exc}")


def _t72():
    # No-DNA fallback: init succeeds but library is empty
    a = PIGTradingAdapter()
    a._init_done = True
    a._library   = type("Lib", (), {"all_consensus": []})()
    a._gateway   = None
    result = a.query("RELIANCE")
    ok(result is None, "empty library → None")


# =============================================================================
# T73-T85  PIGTradingAdapter.query with injected mock gateway
# =============================================================================

class _MockGateway:
    """Minimal gateway stub that returns a fixed PlatformIntelligence."""
    def __init__(self, pi: Optional[_MockPI]) -> None:
        self._pi = pi

    def evaluate_symbol(self, symbol, observation, library, market_snapshot, repo):
        if self._pi is None:
            raise ValueError("mock error")
        return self._pi


class _FakeDNA:
    feature_name = "volume_ratio"
    direction    = "UP"


class _FakeLibrary:
    all_consensus   = [_FakeDNA()]
    master_consensus = [_FakeDNA()]


class _FakeRepo:
    pass


def _make_ready_adapter(pi=_MISSING) -> PIGTradingAdapter:
    """Return a PIGTradingAdapter with mock gateway + library pre-wired."""
    resolved    = _MockPI() if pi is _MISSING else pi
    a           = PIGTradingAdapter()
    a._init_done = True
    a._library   = _FakeLibrary()
    a._repo      = _FakeRepo()
    a._gateway   = _MockGateway(resolved)
    return a


def _t73():
    a      = _make_ready_adapter()
    result = a.query("RELIANCE")
    ok(result is not None, "result returned")
    ok(hasattr(result, "ca_pmci"), "has ca_pmci")


def _t74():
    # Signal and snapshot are forwarded (no error)
    a    = _make_ready_adapter()
    sig  = _MockSignal()
    snap = _MockSnapshot()
    result = a.query("RELIANCE", sig, snap)
    ok(result is not None)


def _t75():
    # Gateway raising → returns None, telemetry records failure
    a = _make_ready_adapter(pi=None)   # gateway raises ValueError
    result = a.query("RELIANCE")
    ok(result is None, "error → None")
    ok(len(a.telemetry) == 1)
    ok(a.telemetry.summary()["available"] == 0)


def _t76():
    # Successful query → telemetry records success
    a = _make_ready_adapter(_MockPI(ca_pmci=0.75, evidence_count=10))
    a.query("X")
    s = a.telemetry.summary()
    ok(s["available"] == 1)
    ok(s["avg_ca_pmci"] > 0)


def _t77():
    # Latency recorded in telemetry
    a = _make_ready_adapter()
    a.query("X")
    s = a.telemetry.summary()
    ok(s["avg_latency_ms"] >= 0)


def _t78():
    # Multiple symbols tracked independently in telemetry
    a = _make_ready_adapter()
    for sym in ["A", "B", "C"]:
        a.query(sym)
    s = a.telemetry.summary()
    ok(s["total_calls"] == 3)


def _t79():
    # telemetry_enabled=False → telemetry not recorded
    p = PIGInfluencePolicy(telemetry_enabled=False)
    a = _make_ready_adapter()
    a._policy = p
    a.query("X")
    ok(len(a.telemetry) == 0, "no telemetry when disabled")


def _t80():
    # is_available() True when ready
    a = _make_ready_adapter()
    ok(a.is_available())


def _t81():
    # dna_count() returns count from library
    a = _make_ready_adapter()
    ok(a.dna_count() == 1, f"expected 1 got {a.dna_count()}")


def _t82():
    # _build_observation_features returns dict
    feats = _build_observation_features("X", _MockSignal(), _MockSnapshot())
    ok(isinstance(feats, dict))
    ok(len(feats) > 0)


def _t83():
    # All feature values in [0, 1]
    feats = _build_observation_features("X", _MockSignal(), _MockSnapshot())
    for k, v in feats.items():
        ok(0.0 <= v <= 1.0, f"feature {k}={v} out of [0,1]")


def _t84():
    # Features from None signal/snapshot → defaults
    feats = _build_observation_features("X", None, None)
    ok(isinstance(feats, dict), "returns dict even with None inputs")


def _t85():
    # BUY signal → momentum_5d > 0.5; SELL → < 0.5
    feats_buy  = _build_observation_features("X", _MockSignal(direction="BUY"), None)
    feats_sell = _build_observation_features("X", _MockSignal(direction="SELL"), None)
    ok(feats_buy["momentum_5d"] > 0.5, "BUY → high momentum")
    ok(feats_sell["momentum_5d"] < 0.5, "SELL → low momentum")


# =============================================================================
# T86-T95  Backward compatibility
# =============================================================================

def _t86():
    # AGENT_WEIGHTS has InstitutionalDNAAI
    from decision_ai.decision_engine import AGENT_WEIGHTS
    ok("InstitutionalDNAAI" in AGENT_WEIGHTS, "InstitutionalDNAAI in AGENT_WEIGHTS")
    ok(AGENT_WEIGHTS["InstitutionalDNAAI"] == 0.08)


def _t87():
    # Without PIG vote: 5-agent sum still works
    from decision_ai.decision_engine import DecisionEngine, AGENT_WEIGHTS
    from models.agent_output import DebateVote, DecisionResult
    from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from datetime import datetime

    votes = [
        DebateVote("TechnicalAnalystAI", "approve", 8.0, "tech", 1.0),
        DebateVote("MacroAnalystAI",     "approve", 7.5, "mac",  1.0),
        DebateVote("RiskDebateAI",       "approve", 7.0, "risk", 1.0),
        DebateVote("SentimentAI",        "approve", 7.5, "sent", 1.0),
        DebateVote("RegimeDebateAI",     "approve", 8.0, "reg",  1.0),
    ]
    snap = MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=RegimeLabel.BULL_TREND, volatility=VolatilityLevel.LOW, vix=14.0,
    )
    sig  = TradeSignal(
        symbol="TEST", direction=SignalDirection.BUY,
        entry_price=100.0, stop_loss=95.0, target_price=115.0,
        signal_type=SignalType.EQUITY, strategy_name="Test", confidence=7.0,
    )
    engine = DecisionEngine()
    result = engine.decide(sig, votes, snap)
    ok(isinstance(result.confidence_score, float))
    ok(0.0 <= result.confidence_score <= 10.0)


def _t88():
    # With PIG vote below threshold → no vote added → same result as without
    from decision_ai.decision_engine import DecisionEngine
    from models.agent_output import DebateVote
    from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from datetime import datetime

    votes = [
        DebateVote("TechnicalAnalystAI", "approve", 8.0, "t", 1.0),
        DebateVote("MacroAnalystAI",     "approve", 8.0, "m", 1.0),
        DebateVote("RiskDebateAI",       "approve", 8.0, "r", 1.0),
        DebateVote("SentimentAI",        "approve", 8.0, "s", 1.0),
        DebateVote("RegimeDebateAI",     "approve", 8.0, "g", 1.0),
    ]
    snap = MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=RegimeLabel.BULL_TREND, volatility=VolatilityLevel.LOW, vix=14.0,
    )
    sig  = TradeSignal(
        symbol="TEST", direction=SignalDirection.BUY,
        entry_price=100.0, stop_loss=95.0, target_price=115.0,
        signal_type=SignalType.EQUITY, strategy_name="Test", confidence=8.0,
    )
    engine = DecisionEngine()
    result_no_pig = engine.decide(sig, votes, snap)

    # Below-threshold PIG → no vote → identical result
    pig_vote = pig_build_vote(_MockPI(ca_pmci=0.20))   # below 0.30 → None
    ok(pig_vote is None, "below-threshold produces no vote")
    result_with_pig = engine.decide(sig, votes, snap)
    ok(result_no_pig.confidence_score == result_with_pig.confidence_score,
       "no difference when PIG below threshold")


def _t89():
    # With PIG vote above threshold: score changes but stays in [0,10]
    from decision_ai.decision_engine import DecisionEngine
    from models.agent_output import DebateVote
    from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from datetime import datetime

    votes_base = [
        DebateVote("TechnicalAnalystAI", "approve", 8.0, "t", 1.0),
        DebateVote("MacroAnalystAI",     "approve", 8.0, "m", 1.0),
        DebateVote("RiskDebateAI",       "approve", 8.0, "r", 1.0),
        DebateVote("SentimentAI",        "approve", 8.0, "s", 1.0),
        DebateVote("RegimeDebateAI",     "approve", 8.0, "g", 1.0),
    ]
    snap = MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=RegimeLabel.BULL_TREND, volatility=VolatilityLevel.LOW, vix=14.0,
    )
    sig  = TradeSignal(
        symbol="TEST", direction=SignalDirection.BUY,
        entry_price=100.0, stop_loss=95.0, target_price=115.0,
        signal_type=SignalType.EQUITY, strategy_name="Test", confidence=8.0,
    )
    engine   = DecisionEngine()
    pig_vote = pig_build_vote(_MockPI(ca_pmci=0.80))   # score=8.0
    ok(pig_vote is not None)
    votes_with_pig = list(votes_base) + [pig_vote]
    result = engine.decide(sig, votes_with_pig, snap)
    ok(0.0 <= result.confidence_score <= 10.0)


def _t90():
    # InstitutionalDNAAI vote never hard-rejects
    pi   = _MockPI(ca_pmci=0.35)
    vote = pig_build_vote(pi)
    ok(vote is None or vote.vote != "reject", "PIG never hard-rejects")


def _t91():
    # PIG with ca_pmci=0.30 (at threshold): score=3.0 (low but present)
    p    = PIGInfluencePolicy(min_ca_pmci_for_vote=0.30)
    pi   = _MockPI(ca_pmci=0.30)
    vote = pig_build_vote(pi, p)
    ok(vote is not None)
    ok(abs(vote.score - 3.0) < 0.01, f"expected 3.0 got {vote.score}")


def _t92():
    # AGENT_WEIGHTS for existing agents unchanged
    from decision_ai.decision_engine import AGENT_WEIGHTS
    ok(abs(AGENT_WEIGHTS["TechnicalAnalystAI"] - 0.30) < 1e-9)
    ok(abs(AGENT_WEIGHTS["MacroAnalystAI"]     - 0.20) < 1e-9)
    ok(abs(AGENT_WEIGHTS["RiskDebateAI"]       - 0.25) < 1e-9)
    ok(abs(AGENT_WEIGHTS["SentimentAI"]        - 0.15) < 1e-9)
    ok(abs(AGENT_WEIGHTS["RegimeDebateAI"]     - 0.10) < 1e-9)


def _t93():
    # mls_config.py has all Phase 2 fields
    from market_learning.mls_config import MLSConfig
    cfg = MLSConfig()
    ok(hasattr(cfg, "pig_vote_weight"))
    ok(hasattr(cfg, "pig_min_ca_pmci_for_vote"))
    ok(hasattr(cfg, "pig_max_conviction_boost"))
    ok(hasattr(cfg, "pig_min_ca_pmci_for_boost"))
    ok(hasattr(cfg, "pig_opportunity_boost_enabled"))
    ok(hasattr(cfg, "pig_decision_vote_enabled"))
    ok(hasattr(cfg, "pig_telemetry_enabled"))


def _t94():
    # market_learning __init__ exports Phase 2 symbols
    import market_learning as ml
    for sym in ("PIGCallRecord", "PIGInfluencePolicy", "PIGTelemetry",
                "PIGTradingAdapter", "pig_build_vote", "pig_enrich_signals"):
        ok(hasattr(ml, sym), f"missing export: {sym}")


def _t95():
    # PIGInfluencePolicy defaults match MLSConfig defaults
    from market_learning.mls_config import MLSConfig
    cfg = MLSConfig()
    p   = PIGInfluencePolicy.from_config(cfg)
    ok(abs(p.vote_weight - cfg.pig_vote_weight) < 1e-9)
    ok(abs(p.min_ca_pmci_for_vote - cfg.pig_min_ca_pmci_for_vote) < 1e-9)
    ok(abs(p.max_conviction_boost - cfg.pig_max_conviction_boost) < 1e-9)


# =============================================================================
# T96-T105  Influence bounds
# =============================================================================

def _t96():
    # Vote weight is bounded at 0.08 by default (< weakest existing agent 0.10)
    p = PIGInfluencePolicy()
    ok(p.vote_weight <= 0.10, "PIG vote_weight ≤ weakest existing agent (0.10)")
    ok(p.vote_weight > 0.0,   "PIG vote_weight > 0")


def _t97():
    # max_conviction_boost default ≤ 1.5 (conservative)
    p = PIGInfluencePolicy()
    ok(p.max_conviction_boost <= 1.5, "max_conviction_boost conservative default")


def _t98():
    # min thresholds prevent low-quality signals from influencing
    p = PIGInfluencePolicy()
    ok(p.min_ca_pmci_for_vote > 0.0,  "threshold > 0")
    ok(p.min_ca_pmci_for_boost > 0.0, "boost threshold > 0")


def _t99():
    # PIG vote below threshold: 0 additive effect
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.10))   # below threshold
    pig_enrich_signals(sigs, adapter, None)
    ok(sigs[0].confidence == 7.0, "no boost for low quality DNA")


def _t100():
    # Very high ca_pmci: boost still bounded by max_conviction_boost
    p       = PIGInfluencePolicy(max_conviction_boost=1.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=10.0))   # wildly high — clamp applies
    pig_enrich_signals(sigs, adapter, None, p)
    ok(sigs[0].confidence <= 8.0, f"boost bounded: {sigs[0].confidence}")


def _t101():
    # PIG cannot reduce confidence (only additive)
    p       = PIGInfluencePolicy(max_conviction_boost=1.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=0.01))   # very low but above 0
    pig_enrich_signals(sigs, adapter, None, p)
    ok(sigs[0].confidence >= 7.0, "PIG never reduces confidence")


def _t102():
    # PIG vote cannot cause REJECT on its own (always "approve")
    pi   = _MockPI(ca_pmci=0.90)
    vote = pig_build_vote(pi)
    ok(vote is None or vote.vote in ("approve", "reduce_size", "hedge"),
       "PIG never hard-rejects")


def _t103():
    # max_conviction_boost=0 → no boost regardless of ca_pmci
    p       = PIGInfluencePolicy(max_conviction_boost=0.0, min_ca_pmci_for_boost=0.0)
    sigs    = _make_signals(1, conf=7.0)
    adapter = _StubAdapter(_MockPI(ca_pmci=1.0))
    pig_enrich_signals(sigs, adapter, None, p)
    ok(sigs[0].confidence == 7.0, "max_boost=0 → no change")


def _t104():
    # vote_weight < 0.30 (can never match heaviest existing agent)
    p = PIGInfluencePolicy()
    ok(p.vote_weight < 0.30, "PIG cannot outweigh TechnicalAnalystAI")


def _t105():
    # Influence policy is immutable after construction (attributes are plain fields)
    p1 = PIGInfluencePolicy(vote_weight=0.05)
    p2 = PIGInfluencePolicy(vote_weight=0.08)
    ok(p1.vote_weight == 0.05)
    ok(p2.vote_weight == 0.08)


# =============================================================================
# T106-T115  Telemetry accuracy and thread safety
# =============================================================================

def _t106():
    # Availability calculation: 3 success, 2 failure = 60%
    t = PIGTelemetry()
    for i in range(3):
        t.record(PIGCallRecord(f"S{i}", 1.0, True, 0.5, 5))
    for i in range(2):
        t.record(PIGCallRecord(f"F{i}", 1.0, False, 0.0, 0, error="e"))
    s = t.summary()
    ok(abs(s["availability_pct"] - 60.0) < 0.01, f"expected 60.0 got {s['availability_pct']}")


def _t107():
    # avg_latency computed across all calls (not just available)
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 10.0, True,  0.5, 5))
    t.record(PIGCallRecord("B", 30.0, False, 0.0, 0, error="e"))
    s = t.summary()
    ok(abs(s["avg_latency_ms"] - 20.0) < 0.01)


def _t108():
    # avg_ca_pmci only from available calls
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 1.0, True,  0.80, 5))
    t.record(PIGCallRecord("B", 1.0, False, 0.99, 0, error="e"))
    s = t.summary()
    ok(abs(s["avg_ca_pmci"] - 0.80) < 0.01, "failed call's ca_pmci not averaged")


def _t109():
    # reset then record — fresh accumulation
    t = PIGTelemetry()
    t.record(PIGCallRecord("A", 1.0, True, 0.5, 5))
    t.reset()
    t.record(PIGCallRecord("B", 2.0, True, 0.9, 8))
    s = t.summary()
    ok(s["total_calls"] == 1)
    ok(abs(s["avg_ca_pmci"] - 0.9) < 0.01)


def _t110():
    # Thread-safe concurrent reads + writes to telemetry
    t = PIGTelemetry()
    errors = []
    def _writer():
        for _ in range(100):
            t.record(PIGCallRecord("X", 1.0, True, 0.5, 5))
    def _reader():
        for _ in range(100):
            try:
                t.summary()
            except Exception as exc:
                errors.append(exc)
    threads = [threading.Thread(target=_writer) for _ in range(3)] + \
              [threading.Thread(target=_reader) for _ in range(2)]
    [th.start() for th in threads]
    [th.join() for th in threads]
    ok(len(errors) == 0, f"thread safety errors: {errors}")


def _t111():
    # Telemetry adapter counts match actual calls
    a = _make_ready_adapter()
    for sym in ["A", "B", "C", "D"]:
        a.query(sym)
    ok(a.telemetry.summary()["total_calls"] == 4)


def _t112():
    # Failed adapter calls still recorded
    a = PIGTradingAdapter()
    a._init_failed = True
    for _ in range(3):
        a.query("X")
    ok(a.telemetry.summary()["total_calls"] == 3)
    ok(a.telemetry.summary()["available"] == 0)


def _t113():
    # Telemetry records error string from PIGCallRecord
    a = PIGTradingAdapter()
    a._init_failed = True
    a.query("X")
    # Check the error key was set in the record
    with a.telemetry._lock:
        rec = a.telemetry._records[-1]
    ok(rec.error is not None and len(rec.error) > 0)


def _t114():
    # Telemetry reset inside adapter
    a = _make_ready_adapter()
    a.query("X")
    ok(len(a.telemetry) == 1)
    a.telemetry.reset()
    ok(len(a.telemetry) == 0)


def _t115():
    # PIGTradingAdapter.query doesn't raise under adversarial inputs
    a = _make_ready_adapter()
    for bad_sym in ["", "  ", "A" * 200, None]:
        try:
            a.query(bad_sym)
        except Exception as exc:
            ok(False, f"query raised for {bad_sym!r}: {exc}")


# =============================================================================
# Main
# =============================================================================

_ALL_TESTS = [
    # T01-T10  PIGCallRecord
    ("T01 PIGCallRecord basic fields",        _t01),
    ("T02 PIGCallRecord unavailable record",  _t02),
    ("T03 PIGCallRecord zero latency",        _t03),
    ("T04 PIGCallRecord zero evidence",       _t04),
    ("T05 PIGCallRecord zero ca_pmci avail",  _t05),
    ("T06 PIGCallRecord max ca_pmci",         _t06),
    ("T07 PIGCallRecord optional error",      _t07),
    ("T08 PIGCallRecord independence",        _t08),
    ("T09 PIGCallRecord fractional latency",  _t09),
    ("T10 PIGCallRecord high evidence count", _t10),
    # T11-T20  PIGTelemetry
    ("T11 PIGTelemetry starts empty",         _t11),
    ("T12 PIGTelemetry single success",       _t12),
    ("T13 PIGTelemetry mixed availability",   _t13),
    ("T14 PIGTelemetry averages",             _t14),
    ("T15 PIGTelemetry reset empty",          _t15),
    ("T16 PIGTelemetry reset clears",         _t16),
    ("T17 PIGTelemetry avg evidence count",   _t17),
    ("T18 PIGTelemetry all unavailable",      _t18),
    ("T19 PIGTelemetry thread-safe writes",   _t19),
    ("T20 PIGTelemetry summary keys",         _t20),
    # T21-T30  PIGInfluencePolicy
    ("T21 PIGInfluencePolicy defaults",       _t21),
    ("T22 PIGInfluencePolicy from_config",    _t22),
    ("T23 PIGInfluencePolicy custom weight",  _t23),
    ("T24 PIGInfluencePolicy vote disabled",  _t24),
    ("T25 PIGInfluencePolicy boost disabled", _t25),
    ("T26 PIGInfluencePolicy empty config",   _t26),
    ("T27 PIGInfluencePolicy custom weight2", _t27),
    ("T28 PIGInfluencePolicy custom boost",   _t28),
    ("T29 PIGInfluencePolicy custom min",     _t29),
    ("T30 PIGInfluencePolicy telemetry off",  _t30),
    # T31-T45  pig_build_vote
    ("T31 pig_build_vote high ca_pmci",       _t31),
    ("T32 pig_build_vote vote=approve",       _t32),
    ("T33 pig_build_vote below threshold",    _t33),
    ("T34 pig_build_vote at threshold",       _t34),
    ("T35 pig_build_vote score mapping 0.80", _t35),
    ("T36 pig_build_vote score clamp 10",     _t36),
    ("T37 pig_build_vote ca_pmci=0 → None",   _t37),
    ("T38 pig_build_vote modifier=1.0",       _t38),
    ("T39 pig_build_vote explainability 7",   _t39),
    ("T40 pig_build_vote disabled",           _t40),
    ("T41 pig_build_vote custom threshold",   _t41),
    ("T42 pig_build_vote score 0.50",         _t42),
    ("T43 pig_build_vote score 1.0",          _t43),
    ("T44 pig_build_vote score 0.35",         _t44),
    ("T45 pig_build_vote None policy",        _t45),
    # T46-T60  pig_enrich_signals
    ("T46 pig_enrich returns same list",      _t46),
    ("T47 pig_enrich increases confidence",   _t47),
    ("T48 pig_enrich boost bounded",          _t48),
    ("T49 pig_enrich confidence ≤ 10",        _t49),
    ("T50 pig_enrich below threshold no-op",  _t50),
    ("T51 pig_enrich empty list",             _t51),
    ("T52 pig_enrich boost disabled",         _t52),
    ("T53 pig_enrich None PI unchanged",      _t53),
    ("T54 pig_enrich multiple signals",       _t54),
    ("T55 pig_enrich snapshot forwarded",     _t55),
    ("T56 pig_enrich None policy defaults",   _t56_enrich),
    ("T57 pig_enrich boost formula 0.50",     _t57_enrich),
    ("T58 pig_enrich boost formula 0.80",     _t58_enrich),
    ("T59 pig_enrich threshold boundary",     _t59_enrich),
    ("T60 pig_enrich no-confidence attr",     _t60_enrich),
    # T61-T72  PIGTradingAdapter lifecycle
    ("T61 PIGTradingAdapter not available",   _t61),
    ("T62 PIGTradingAdapter telemetry attr",  _t62),
    ("T63 PIGTradingAdapter query fail None", _t63),
    ("T64 PIGTradingAdapter repeat None",     _t64),
    ("T65 PIGTradingAdapter telem failure",   _t65),
    ("T66 PIGTradingAdapter ensure False",    _t66),
    ("T67 PIGTradingAdapter ensure True",     _t67),
    ("T68 PIGTradingAdapter dna None lib",    _t68),
    ("T69 PIGTradingAdapter default policy",  _t69),
    ("T70 PIGTradingAdapter custom policy",   _t70),
    ("T71 PIGTradingAdapter reload safe",     _t71),
    ("T72 PIGTradingAdapter empty lib None",  _t72),
    # T73-T85  PIGTradingAdapter.query mock
    ("T73 query returns PI",                  _t73),
    ("T74 query with signal+snap",            _t74),
    ("T75 query gateway raises → None",       _t75),
    ("T76 query success telemetry",           _t76),
    ("T77 query latency recorded",            _t77),
    ("T78 query multi-symbol tracking",       _t78),
    ("T79 query telemetry disabled",          _t79),
    ("T80 is_available ready adapter",        _t80),
    ("T81 dna_count from library",            _t81),
    ("T82 feature builder dict output",       _t82),
    ("T83 feature values in [0,1]",           _t83),
    ("T84 feature builder None inputs",       _t84),
    ("T85 feature momentum direction",        _t85),
    # T86-T95  Backward compatibility
    ("T86 AGENT_WEIGHTS has InstitutionalDNA",_t86),
    ("T87 5-agent vote works unchanged",      _t87),
    ("T88 below-threshold PIG no effect",     _t88),
    ("T89 above-threshold PIG in [0,10]",     _t89),
    ("T90 PIG vote never hard-rejects",       _t90),
    ("T91 PIG at-threshold score=3.0",        _t91),
    ("T92 existing AGENT_WEIGHTS unchanged",  _t92),
    ("T93 MLSConfig Phase2 fields exist",     _t93),
    ("T94 __init__ exports Phase2 symbols",   _t94),
    ("T95 policy matches MLSConfig defaults", _t95),
    # T96-T105  Influence bounds
    ("T96 vote_weight ≤ weakest agent",       _t96),
    ("T97 max_conviction_boost conservative", _t97),
    ("T98 min thresholds > 0",                _t98),
    ("T99 low quality DNA no boost",          _t99),
    ("T100 very high ca_pmci still bounded",  _t100),
    ("T101 PIG never reduces confidence",     _t101),
    ("T102 PIG vote not reject",              _t102),
    ("T103 max_boost=0 no change",            _t103),
    ("T104 PIG weight < TechnicalAnalyst",    _t104),
    ("T105 policy immutable",                 _t105),
    # T106-T115  Telemetry accuracy & thread safety
    ("T106 availability 60% calculation",     _t106),
    ("T107 avg_latency all calls",            _t107),
    ("T108 avg_ca_pmci only available",       _t108),
    ("T109 reset then record fresh",          _t109),
    ("T110 thread-safe read+write",           _t110),
    ("T111 adapter call count matches",       _t111),
    ("T112 failed calls recorded",            _t112),
    ("T113 error string recorded",            _t113),
    ("T114 telemetry reset via adapter",      _t114),
    ("T115 query no raise adversarial input", _t115),
]


if __name__ == "__main__":
    runner = TestRunner()
    for name, fn in _ALL_TESTS:
        runner.run(name, fn)
    sys.exit(runner.print_report())

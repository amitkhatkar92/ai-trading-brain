"""
test_pig_gateway.py -- R-001 Phase 1: Platform Intelligence Gateway.

90-test suite.  Run with:
    .venv\\Scripts\\python.exe test_pig_gateway.py

Uses the same minimal test framework as all previous MLS phases.
No pytest dependency.  No network access.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import (
    FIIDIIData,
    MarketSnapshot,
    RegimeLabel,
    SectorFlow,
    VolatilityLevel,
)
from market_learning import (
    CAPMCIEngine,
    CDSEngine,
    CDSLibraryResult,
    ConsensusLibrary,
    ConsensusDNA,
    ConsensusLevel,
    ConsensusState,
    IDRRepository,
    InstitutionalDNA,
    MCIEngine,
    MLSConfig,
    PMCIEngine,
    PlatformConfidence,
    PlatformEvidence,
    PlatformGatewayError,
    PlatformGatewayInputError,
    PlatformGatewayStatistics,
    PlatformGatewaySymbolNotFoundError,
    PlatformIntelligence,
    PlatformIntelligenceGateway,
    PlatformRecommendationContext,
    SeparationDirection,
)
from market_learning.market_observer_models import DailyMarketSnapshot, MarketObservation, ObservationMetadata
from market_learning.dna_consensus_models import ConsensusStatistics


# =============================================================================
# Test framework
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

    def report(self) -> int:
        W = 76
        print("=" * W)
        for r in self.results:
            tag   = "[PASS]" if r.passed else "[FAIL]"
            label = r.name[:48].ljust(48)
            ms    = f"{r.duration_ms:6.1f}ms"
            short = r.detail[:60]
            print(f"  {tag} {label} {ms}  {short}")
            if not r.passed and r.error:
                for line in r.error.strip().splitlines()[-4:]:
                    print(f"          {line}")
        print("-" * W)
        passed = sum(1 for r in self.results if r.passed)
        total  = len(self.results)
        print(f"  Result:  {passed}/{total} passed, {total - passed} failed")
        print("=" * W)
        return 0 if passed == total else 1


def ok(cond: bool, detail: str = "") -> None:
    if not cond:
        raise AssertionError(detail or "condition is False")


# =============================================================================
# Fixtures
# =============================================================================

_CFG = MLSConfig(min_universe_size=1, dna_min_group_size=2)


def _market_snapshot(
    regime: RegimeLabel = RegimeLabel.BULL_TREND,
    vix: float = 14.0,
    pcr: float = 0.90,
    breadth: float = 0.65,
    fii_net: float = 1500.0,
    ts: str = "2026-08-04T09:00:00",
) -> MarketSnapshot:
    fii_buy = max(0.0, fii_net)
    fii_sell = max(0.0, -fii_net)
    fii_dii = FIIDIIData(
        date=datetime.fromisoformat(ts),
        fii_buy=fii_buy, fii_sell=fii_sell,
        dii_buy=500.0, dii_sell=0.0,
    )
    return MarketSnapshot(
        timestamp=datetime.fromisoformat(ts),
        indices={},
        regime=regime,
        vix=vix,
        pcr=pcr,
        market_breadth=breadth,
        global_sentiment_score=0.3,
        global_bias="bullish",
        fii_dii=fii_dii,
        sector_flows=[
            SectorFlow(sector_name=f"S{i}", flow_score=0.6, rank=i + 1) for i in range(4)
        ],
    )


def _adverse_snapshot() -> MarketSnapshot:
    return _market_snapshot(
        regime=RegimeLabel.VOLATILE, vix=45.0, pcr=1.5,
        breadth=0.15, fii_net=-2000.0,
    )


def _obs(
    symbol: str = "RELIANCE",
    features: Optional[Dict[str, float]] = None,
    date: str = "2026-08-04",
) -> MarketObservation:
    f = features or {"rsi": 0.75, "mom_1d": 0.70, "vol_ratio": 0.65}
    return MarketObservation(
        symbol=symbol,
        feature_timestamp=f"{date}T09:15:00",
        features=f,
        feature_count=len(f),
    )


def _cdna(
    feature: str = "rsi",
    direction: str = "WINNERS_HIGHER",
    state: str = "INSTITUTIONAL",
    score: float = 0.82,
    regime_cons: float = 0.78,
    sector_cons: float = 0.75,
    last_seen: str = "2026-08-03",
    evidence: int = 20,
) -> ConsensusDNA:
    h   = hashlib.sha256(f"{feature}::{direction}".encode()).hexdigest()[:8]
    dir_ = SeparationDirection(direction)
    st  = ConsensusState(state)
    lvl = ConsensusLevel.MASTER if st == ConsensusState.INSTITUTIONAL else ConsensusLevel.WEEKLY
    return ConsensusDNA(
        consensus_id=f"CON-{h}",
        feature_name=feature,
        direction=dir_,
        consensus_state=st,
        consensus_score=score,
        replication_frequency=0.82,
        evidence_count=evidence,
        temporal_stability=0.80,
        regime_consistency=regime_cons,
        sector_consistency=sector_cons,
        confidence_trend=0.08,
        feature_persistence=0.78,
        first_seen="2026-01-01",
        last_seen=last_seen,
        all_observations=[],
        regime_counts={"bull_trend": evidence},
        level=lvl,
    )


def _library(dna_list: Optional[List[ConsensusDNA]] = None) -> ConsensusLibrary:
    dna    = dna_list or [_cdna("rsi"), _cdna("mom_1d", "WINNERS_HIGHER"), _cdna("vol_ratio")]
    master = [c for c in dna if c.consensus_state == ConsensusState.INSTITUTIONAL]
    scores = [c.consensus_score for c in dna]
    stats  = ConsensusStatistics(
        as_of_date="2026-08-04",
        total_consensus_dna=len(dna),
        institutional_count=len(master),
        weakening_count=0,
        drifting_count=0,
        retired_count=0,
        avg_consensus_score=sum(scores) / max(1, len(scores)),
        avg_replication_freq=0.80,
        top_institutional_feature=master[0].feature_name if master else None,
    )
    h = hashlib.sha256("LIB-TEST".encode()).hexdigest()[:8]
    return ConsensusLibrary(
        library_id=f"LIB-{h}",
        as_of_date="2026-08-04",
        all_consensus=dna,
        master_consensus=master,
        drift_reports=[],
        statistics=stats,
    )


def _tmp_repo() -> IDRRepository:
    tmp = tempfile.mktemp(suffix=".db")
    return IDRRepository(db_path=Path(tmp))


def _tmp_repo_with_dna() -> IDRRepository:
    repo = _tmp_repo()
    repo.save(InstitutionalDNA(
        id="IDR-TEST-001",
        feature_name="rsi",
        direction="WINNERS_HIGHER",
        category="WINNER",
        lifecycle="INSTITUTIONAL",
        version=1,
        consensus_score=0.82,
        confidence=0.78,
        effect_size=0.60,
        regime_consistency=0.78,
        sector_consistency=0.75,
        temporal_stability=0.70,
        replication_frequency=0.82,
        evidence_count=20,
        regime_counts={"bull_trend": 20},
        last_seen="2026-08-03",
        study_id="STUDY-001",
        source="test",
        created_at="2026-08-01T09:00:00",
        updated_at="2026-08-04T09:00:00",
        is_current=True,
        metadata={},
    ))
    return repo


def _gateway() -> PlatformIntelligenceGateway:
    return PlatformIntelligenceGateway(config=_CFG)


def _full_eval():
    """Run evaluate_symbol() and return result + gateway."""
    gw  = _gateway()
    res = gw.evaluate_symbol(
        symbol="RELIANCE",
        observation=_obs(),
        library=_library(),
        market_snapshot=_market_snapshot(),
        repo=_tmp_repo_with_dna(),
    )
    return gw, res


def _meta() -> ObservationMetadata:
    return ObservationMetadata(
        run_id="MLS-OBS-20260804", trading_date="2026-08-04",
        capture_time="2026-08-04T09:14:00", universe_size=2,
        feature_count=3, snapshot_id="MLS-SNAP-20260804",
        temporal_contract_verified=True, regime="bull_trend",
        volatility="low", vix=14.0, pcr=0.90, breadth=0.65,
        global_bias="bullish", mls_config_hash="aabbccdd11223344",
    )


def _daily_snapshot(symbols: Optional[List[str]] = None) -> DailyMarketSnapshot:
    syms = symbols or ["RELIANCE", "TCS"]
    obs  = [_obs(s) for s in syms]
    return DailyMarketSnapshot(
        snapshot_id="MLS-SNAP-20260804",
        trading_date="2026-08-04",
        feature_timestamp="2026-08-04T09:15:00",
        regime="bull_trend",
        volatility="low",
        vix=14.0,
        pcr=0.90,
        breadth=0.65,
        global_bias=0.3,
        universe_size=len(syms),
        symbols=syms,
        observations=obs,
        metadata=_meta(),
        created_at="2026-08-04T09:15:00",
    )


# =============================================================================
# T01-T10: Instantiation, config, exceptions
# =============================================================================

def T01():
    gw = PlatformIntelligenceGateway()
    ok(isinstance(gw, PlatformIntelligenceGateway))
    return "PlatformIntelligenceGateway instantiated with defaults"

def T02():
    gw = PlatformIntelligenceGateway(config=_CFG)
    ok(isinstance(gw, PlatformIntelligenceGateway))
    return "PlatformIntelligenceGateway accepts custom MLSConfig"

def T03():
    mci  = MCIEngine(_CFG)
    pmci = PMCIEngine(_CFG)
    cds  = CDSEngine(_CFG)
    cap  = CAPMCIEngine(_CFG)
    gw   = PlatformIntelligenceGateway(config=_CFG, mci_engine=mci, pmci_engine=pmci, cds_engine=cds, ca_pmci_engine=cap)
    ok(isinstance(gw, PlatformIntelligenceGateway))
    return "PlatformIntelligenceGateway accepts injected engines"

def T04():
    ok(issubclass(PlatformGatewayError, Exception))
    return "PlatformGatewayError is Exception"

def T05():
    ok(issubclass(PlatformGatewayInputError, PlatformGatewayError))
    return "PlatformGatewayInputError is PlatformGatewayError"

def T06():
    ok(issubclass(PlatformGatewaySymbolNotFoundError, PlatformGatewayError))
    return "PlatformGatewaySymbolNotFoundError is PlatformGatewayError"

def T07():
    gw = _gateway()
    try:
        gw.evaluate_symbol("", _obs(), _library(), _market_snapshot(), _tmp_repo())
        ok(False, "should raise PlatformGatewayInputError for empty symbol")
    except PlatformGatewayInputError:
        pass
    return "empty symbol raises PlatformGatewayInputError"

def T08():
    gw = _gateway()
    try:
        gw.evaluate_symbol("RELIANCE", None, _library(), _market_snapshot(), _tmp_repo())
        ok(False, "should raise PlatformGatewayInputError for None observation")
    except PlatformGatewayInputError:
        pass
    return "None observation raises PlatformGatewayInputError"

def T09():
    gw = _gateway()
    try:
        gw.evaluate_symbol("RELIANCE", _obs(), None, _market_snapshot(), _tmp_repo())
        ok(False, "should raise for None library")
    except PlatformGatewayInputError:
        pass
    return "None library raises PlatformGatewayInputError"

def T10():
    ok(_CFG.pig_high_threshold == 0.70, f"expected 0.70 got {_CFG.pig_high_threshold}")
    ok(_CFG.pig_medium_threshold == 0.45, f"expected 0.45 got {_CFG.pig_medium_threshold}")
    ok(_CFG.pig_low_threshold == 0.30, f"expected 0.30 got {_CFG.pig_low_threshold}")
    return "PIG MLSConfig thresholds correct"


# =============================================================================
# T11-T20: evaluate_symbol() basic
# =============================================================================

def T11():
    _, res = _full_eval()
    ok(isinstance(res, PlatformIntelligence))
    return "evaluate_symbol() returns PlatformIntelligence"

def T12():
    _, res = _full_eval()
    ok(res.symbol == "RELIANCE", f"expected RELIANCE got {res.symbol}")
    return "PlatformIntelligence.symbol matches input"

def T13():
    _, res = _full_eval()
    ok(res.evaluation_date == "2026-08-04", f"got {res.evaluation_date}")
    return "PlatformIntelligence.evaluation_date set"

def T14():
    _, res = _full_eval()
    ok(res.result_id.startswith("PIG-"), f"got {res.result_id}")
    return "PlatformIntelligence.result_id starts with PIG-"

def T15():
    _, res = _full_eval()
    ok(0.0 <= res.raw_pmci <= 1.0, f"raw_pmci out of range: {res.raw_pmci}")
    return f"raw_pmci in [0,1]: {res.raw_pmci:.3f}"

def T16():
    _, res = _full_eval()
    ok(0.0 <= res.ca_pmci <= 1.0, f"ca_pmci out of range: {res.ca_pmci}")
    return f"ca_pmci in [0,1]: {res.ca_pmci:.3f}"

def T17():
    _, res = _full_eval()
    ok(0.0 <= res.cds_score <= 1.0, f"cds_score out of range: {res.cds_score}")
    return f"cds_score in [0,1]: {res.cds_score:.3f}"

def T18():
    _, res = _full_eval()
    ok(0.0 <= res.confidence <= 1.0, f"confidence out of range: {res.confidence}")
    return f"confidence in [0,1]: {res.confidence:.3f}"

def T19():
    _, res = _full_eval()
    ok(isinstance(res.evaluated_at, str) and len(res.evaluated_at) > 0)
    return f"evaluated_at set: {res.evaluated_at[:19]}"

def T20():
    _, res = _full_eval()
    ok(isinstance(res.pmci_result, object))
    ok(isinstance(res.ca_pmci_result, object))
    ok(isinstance(res.market_context, object))
    return "source objects (pmci_result, ca_pmci_result, market_context) attached"


# =============================================================================
# T21-T30: evaluate_symbol() output field values
# =============================================================================

def T21():
    _, res = _full_eval()
    ok(0.0 <= res.winner_dna_match <= 1.0, f"winner_dna_match={res.winner_dna_match}")
    return f"winner_dna_match in [0,1]: {res.winner_dna_match:.3f}"

def T22():
    _, res = _full_eval()
    ok(0.0 <= res.loser_dna_match <= 1.0, f"loser_dna_match={res.loser_dna_match}")
    return f"loser_dna_match in [0,1]: {res.loser_dna_match:.3f}"

def T23():
    _, res = _full_eval()
    ok(res.evidence_count >= 0, f"evidence_count={res.evidence_count}")
    return f"evidence_count >= 0: {res.evidence_count}"

def T24():
    _, res = _full_eval()
    ok(0.0 <= res.dna_freshness <= 1.0, f"dna_freshness={res.dna_freshness}")
    return f"dna_freshness in [0,1]: {res.dna_freshness:.3f}"

def T25():
    _, res = _full_eval()
    ok(0.0 <= res.dna_drift <= 1.0, f"dna_drift={res.dna_drift}")
    return f"dna_drift in [0,1]: {res.dna_drift:.3f}"

def T26():
    _, res = _full_eval()
    ok(0.0 <= res.institutional_confidence <= 1.0, f"inst_conf={res.institutional_confidence}")
    return f"institutional_confidence in [0,1]: {res.institutional_confidence:.3f}"

def T27():
    _, res = _full_eval()
    ok(0.0 <= res.context_score <= 1.0, f"context_score={res.context_score}")
    ok(len(res.regime) > 0, "regime is non-empty string")
    return f"context_score={res.context_score:.3f}, regime={res.regime}"

def T28():
    _, res = _full_eval()
    ok(res.cds_total_dna >= 0)
    ok(res.cds_highly_relevant_count >= 0)
    ok(res.cds_relevant_count >= 0)
    return f"CDS counts: total={res.cds_total_dna}, hr={res.cds_highly_relevant_count}, r={res.cds_relevant_count}"

def T29():
    _, res = _full_eval()
    ok(isinstance(res.explanation, str) and len(res.explanation) > 20)
    return "explanation non-empty string"

def T30():
    # Deterministic result_id for same (symbol, date) inputs
    gw  = _gateway()
    r1  = gw.evaluate_symbol("RELIANCE", _obs(), _library(), _market_snapshot(), _tmp_repo_with_dna())
    r2  = gw.evaluate_symbol("RELIANCE", _obs(), _library(), _market_snapshot(), _tmp_repo_with_dna())
    ok(r1.result_id == r2.result_id, f"non-deterministic: {r1.result_id} != {r2.result_id}")
    return f"result_id is deterministic: {r1.result_id}"


# =============================================================================
# T31-T40: evaluate_universe()
# =============================================================================

def T31():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(), _library(), _market_snapshot(), _tmp_repo())
    ok(isinstance(res, list))
    return f"evaluate_universe() returns list of {len(res)} results"

def T32():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    ok(len(res) == 2, f"expected 2 got {len(res)}")
    return "evaluate_universe() returns one result per symbol"

def T33():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    syms = [r.symbol for r in res]
    ok("RELIANCE" in syms and "TCS" in syms, f"got {syms}")
    return "evaluate_universe() includes all symbols"

def T34():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(), _library(), _market_snapshot(), _tmp_repo())
    ok(all(isinstance(r, PlatformIntelligence) for r in res))
    return "evaluate_universe() all results are PlatformIntelligence"

def T35():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(), _library(), _market_snapshot(), _tmp_repo())
    ok(all(0.0 <= r.raw_pmci <= 1.0 for r in res))
    ok(all(0.0 <= r.ca_pmci  <= 1.0 for r in res))
    return "evaluate_universe() all raw_pmci and ca_pmci in [0,1]"

def T36():
    # Shared context score — both symbols see the same market
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    ok(res[0].context_score == res[1].context_score,
       f"context_scores differ: {res[0].context_score} vs {res[1].context_score}")
    return "evaluate_universe() all symbols share same context_score"

def T37():
    # Shared CDS score — computed once
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    ok(res[0].cds_score == res[1].cds_score,
       f"cds_scores differ: {res[0].cds_score} vs {res[1].cds_score}")
    return "evaluate_universe() all symbols share same cds_score"

def T38():
    gw  = _gateway()
    try:
        gw.evaluate_universe(None, _library(), _market_snapshot(), _tmp_repo())
        ok(False, "should raise for None daily_snapshot")
    except PlatformGatewayInputError:
        pass
    return "evaluate_universe() raises for None daily_snapshot"

def T39():
    gw   = _gateway()
    snap = _daily_snapshot(["A", "B", "C"])
    res  = gw.evaluate_universe(snap, _library(), _market_snapshot(), _tmp_repo())
    ok(len(res) == 3)
    return "evaluate_universe() processes 3 symbols correctly"

def T40():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(), _library(), _market_snapshot(), _tmp_repo())
    ok(all(r.evaluation_date == "2026-08-04" for r in res))
    return "evaluate_universe() all results have correct evaluation_date"


# =============================================================================
# T41-T50: PlatformEvidence
# =============================================================================

def T41():
    _, res = _full_eval()
    ok(isinstance(res.evidence, list) and len(res.evidence) > 0)
    return f"evidence list has {len(res.evidence)} items"

def T42():
    _, res = _full_eval()
    ok(all(isinstance(e, PlatformEvidence) for e in res.evidence))
    return "all evidence items are PlatformEvidence"

def T43():
    _, res = _full_eval()
    sources = {e.source for e in res.evidence}
    ok("PMCI" in sources, f"PMCI not in sources: {sources}")
    ok("CA-PMCI" in sources, f"CA-PMCI not in sources: {sources}")
    ok("CDS" in sources, f"CDS not in sources: {sources}")
    ok("MCIE" in sources, f"MCIE not in sources: {sources}")
    ok("IDR" in sources, f"IDR not in sources: {sources}")
    return f"evidence covers all 5 sources: {sources}"

def T44():
    _, res = _full_eval()
    pmci_ev = [e for e in res.evidence if e.component == "raw_pmci"]
    ok(len(pmci_ev) == 1, "should have exactly 1 raw_pmci evidence item")
    ok(pmci_ev[0].value == res.raw_pmci, "evidence value matches raw_pmci")
    return "raw_pmci backed by PlatformEvidence"

def T45():
    _, res = _full_eval()
    ca_ev = [e for e in res.evidence if e.component == "ca_pmci"]
    ok(len(ca_ev) == 1, "should have exactly 1 ca_pmci evidence item")
    ok(ca_ev[0].value == res.ca_pmci, "evidence value matches ca_pmci")
    return "ca_pmci backed by PlatformEvidence"

def T46():
    _, res = _full_eval()
    cds_ev = [e for e in res.evidence if e.component == "cds_score"]
    ok(len(cds_ev) == 1, "should have exactly 1 cds_score evidence item")
    return "cds_score backed by PlatformEvidence"

def T47():
    # PlatformEvidence.to_dict / from_dict round-trip
    ev = PlatformEvidence(
        source="PMCI", component="winner_match",
        value=0.75, explanation="test evidence",
        raw={"winner_match": 0.75, "matched_count": 3},
    )
    d  = ev.to_dict()
    ev2 = PlatformEvidence.from_dict(d)
    ok(ev2.source == ev.source)
    ok(ev2.component == ev.component)
    ok(abs(ev2.value - ev.value) < 1e-9)
    ok(ev2.explanation == ev.explanation)
    return "PlatformEvidence.to_dict/from_dict round-trip"

def T48():
    _, res = _full_eval()
    ok(all(len(e.explanation) > 5 for e in res.evidence), "all evidence items have explanations")
    return "all PlatformEvidence items have non-trivial explanations"

def T49():
    _, res = _full_eval()
    idr_ev = [e for e in res.evidence if e.source == "IDR"]
    ok(len(idr_ev) >= 1, "IDR evidence missing")
    ok(idr_ev[0].value == res.institutional_confidence)
    return "institutional_confidence backed by IDR PlatformEvidence"

def T50():
    _, res = _full_eval()
    drift_ev = [e for e in res.evidence if e.component == "dna_drift"]
    ok(len(drift_ev) == 1, "dna_drift evidence missing")
    ok(drift_ev[0].value == res.dna_drift)
    return "dna_drift backed by CA-PMCI PlatformEvidence"


# =============================================================================
# T51-T60: PlatformConfidence
# =============================================================================

def T51():
    _, res = _full_eval()
    ok(isinstance(res.platform_confidence, PlatformConfidence))
    return "platform_confidence is PlatformConfidence"

def T52():
    _, res = _full_eval()
    c = res.platform_confidence
    ok(0.0 <= c.overall <= 1.0, f"overall={c.overall}")
    ok(0.0 <= c.pmci    <= 1.0, f"pmci={c.pmci}")
    ok(0.0 <= c.ca_pmci <= 1.0, f"ca_pmci={c.ca_pmci}")
    ok(0.0 <= c.context <= 1.0, f"context={c.context}")
    ok(0.0 <= c.institutional <= 1.0, f"institutional={c.institutional}")
    return "all PlatformConfidence components in [0,1]"

def T53():
    _, res = _full_eval()
    ok(res.confidence == res.platform_confidence.overall)
    return "PlatformIntelligence.confidence == platform_confidence.overall"

def T54():
    # PlatformConfidence.to_dict / from_dict round-trip
    c  = PlatformConfidence(overall=0.72, pmci=0.70, ca_pmci=0.74, context=0.80,
                             institutional=0.65, explanation="test")
    d  = c.to_dict()
    c2 = PlatformConfidence.from_dict(d)
    ok(abs(c2.overall - c.overall) < 1e-9)
    ok(abs(c2.pmci - c.pmci) < 1e-9)
    return "PlatformConfidence.to_dict/from_dict round-trip"

def T55():
    _, res = _full_eval()
    ok(len(res.platform_confidence.explanation) > 10)
    return "PlatformConfidence.explanation non-empty"

def T56():
    _, res = _full_eval()
    # Verify blended formula: 0.40*pmci + 0.35*ca + 0.15*ctx + 0.10*inst
    c = res.platform_confidence
    expected = 0.40 * c.pmci + 0.35 * c.ca_pmci + 0.15 * c.context + 0.10 * c.institutional
    ok(abs(c.overall - expected) < 1e-4, f"overall={c.overall}, formula={expected}")
    return "PlatformConfidence.overall matches blended formula"

def T57():
    _, res = _full_eval()
    ok(res.platform_confidence.pmci == res.pmci_result.confidence,
       "platform_confidence.pmci does not match PMCIResult.confidence")
    return "platform_confidence.pmci sourced from PMCIResult.confidence"

def T58():
    _, res = _full_eval()
    ok(res.platform_confidence.ca_pmci == res.ca_pmci_result.confidence,
       "platform_confidence.ca_pmci does not match CAPMCIResult.confidence")
    return "platform_confidence.ca_pmci sourced from CAPMCIResult.confidence"

def T59():
    _, res = _full_eval()
    ok(res.platform_confidence.context == res.market_context.confidence,
       "platform_confidence.context does not match MarketContext.confidence")
    return "platform_confidence.context sourced from MarketContext.confidence"

def T60():
    _, res = _full_eval()
    # Institutional confidence comes from IDR stats
    ok(0.0 <= res.platform_confidence.institutional <= 1.0)
    return "platform_confidence.institutional in [0,1]"


# =============================================================================
# T61-T67: PlatformRecommendationContext
# =============================================================================

def T61():
    _, res = _full_eval()
    ok(isinstance(res.recommendation_context, PlatformRecommendationContext))
    return "recommendation_context is PlatformRecommendationContext"

def T62():
    _, res = _full_eval()
    rc = res.recommendation_context
    ok(rc.symbol == "RELIANCE")
    ok(rc.evaluation_date == "2026-08-04")
    ok(len(rc.regime) > 0)
    return f"recommendation_context: symbol={rc.symbol}, regime={rc.regime}"

def T63():
    _, res = _full_eval()
    rc = res.recommendation_context
    ok(rc.winner_alignment in ("HIGH", "MEDIUM", "LOW"), f"bad: {rc.winner_alignment}")
    ok(rc.context_support in ("STRONG", "MODERATE", "WEAK"), f"bad: {rc.context_support}")
    ok(rc.intelligence_quality in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT"), f"bad: {rc.intelligence_quality}")
    return f"quality labels: win={rc.winner_alignment}, ctx={rc.context_support}, iq={rc.intelligence_quality}"

def T64():
    _, res = _full_eval()
    rc = res.recommendation_context
    ok(rc.raw_pmci == res.raw_pmci, "raw_pmci mismatch")
    ok(rc.ca_pmci  == res.ca_pmci,  "ca_pmci mismatch")
    ok(rc.confidence == res.confidence, "confidence mismatch")
    return "recommendation_context scores match PlatformIntelligence"

def T65():
    # PlatformRecommendationContext.to_dict/from_dict round-trip
    rc  = PlatformRecommendationContext(
        symbol="RELIANCE", evaluation_date="2026-08-04",
        regime="bull_trend", context_stability="STABLE",
        winner_alignment="HIGH", context_support="STRONG",
        intelligence_quality="HIGH",
        raw_pmci=0.72, ca_pmci=0.75, confidence=0.70,
        institutional_confidence=0.65, explanation="test",
    )
    d   = rc.to_dict()
    rc2 = PlatformRecommendationContext.from_dict(d)
    ok(rc2.symbol == rc.symbol)
    ok(rc2.winner_alignment == rc.winner_alignment)
    ok(abs(rc2.ca_pmci - rc.ca_pmci) < 1e-9)
    return "PlatformRecommendationContext.to_dict/from_dict round-trip"

def T66():
    # Adverse context reduces CA-PMCI compared to favorable context
    gw     = _gateway()
    lib    = _library()
    repo   = _tmp_repo()
    r_good = gw.evaluate_symbol("RELIANCE", _obs(), lib, _market_snapshot(), repo)
    r_bad  = gw.evaluate_symbol("RELIANCE", _obs(), lib, _adverse_snapshot(), repo)
    ok(r_bad.ca_pmci <= r_good.ca_pmci,
       f"adverse context should reduce ca_pmci: bad={r_bad.ca_pmci:.3f} > good={r_good.ca_pmci:.3f}")
    return f"adverse context reduces ca_pmci: {r_good.ca_pmci:.3f} -> {r_bad.ca_pmci:.3f}"

def T67():
    _, res = _full_eval()
    rc = res.recommendation_context
    ok(isinstance(rc.explanation, str) and len(rc.explanation) > 10)
    return "recommendation_context.explanation non-empty"


# =============================================================================
# T68-T73: statistics()
# =============================================================================

def T68():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    stats = gw.statistics(res)
    ok(isinstance(stats, PlatformGatewayStatistics))
    return "statistics() returns PlatformGatewayStatistics"

def T69():
    gw    = _gateway()
    stats = gw.statistics([])
    ok(stats.total_symbols == 0)
    ok(stats.regime == "unknown")
    return "statistics([]) returns empty statistics"

def T70():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    stats = gw.statistics(res)
    ok(stats.total_symbols == 2, f"expected 2 got {stats.total_symbols}")
    return f"statistics().total_symbols == 2"

def T71():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["A", "B", "C"]), _library(), _market_snapshot(), _tmp_repo())
    stats = gw.statistics(res)
    ok(0.0 <= stats.avg_raw_pmci  <= 1.0)
    ok(0.0 <= stats.avg_ca_pmci   <= 1.0)
    ok(0.0 <= stats.avg_confidence <= 1.0)
    ok(0.0 <= stats.avg_cds_score  <= 1.0)
    return f"statistics() averages in [0,1]"

def T72():
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE", "TCS"]), _library(), _market_snapshot(), _tmp_repo())
    stats = gw.statistics(res)
    ok(stats.top_symbol in ("RELIANCE", "TCS"), f"unexpected top: {stats.top_symbol}")
    ok(stats.top_ca_pmci >= 0.0)
    return f"statistics() top_symbol={stats.top_symbol}"

def T73():
    # to_dict on statistics
    gw  = _gateway()
    res = gw.evaluate_universe(_daily_snapshot(["RELIANCE"]), _library(), _market_snapshot(), _tmp_repo())
    stats = gw.statistics(res)
    d   = stats.to_dict()
    ok(d["total_symbols"] == 1)
    ok("avg_ca_pmci" in d)
    return "PlatformGatewayStatistics.to_dict() has expected keys"


# =============================================================================
# T74-T80: Thread safety
# =============================================================================

def T74():
    gw      = _gateway()
    lib     = _library()
    msnap   = _market_snapshot()
    repo    = _tmp_repo()
    errors  = []

    def _worker(sym):
        try:
            gw.evaluate_symbol(sym, _obs(sym), lib, msnap, repo)
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=_worker, args=(f"SYM{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ok(len(errors) == 0, f"thread errors: {errors}")
    return "5 concurrent evaluate_symbol() calls succeed without errors"

def T75():
    gw      = _gateway()
    lib     = _library()
    snap    = _daily_snapshot(["A", "B", "C", "D", "E"])
    msnap   = _market_snapshot()
    repo    = _tmp_repo()
    results = []
    errors  = []

    def _worker():
        try:
            res = gw.evaluate_universe(snap, lib, msnap, repo)
            results.append(len(res))
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=_worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ok(len(errors) == 0, f"thread errors: {errors}")
    ok(all(n == 5 for n in results), f"result counts: {results}")
    return "3 concurrent evaluate_universe() calls all return 5 results"

def T76():
    gw    = _gateway()
    lib   = _library()
    msnap = _market_snapshot()
    repo  = _tmp_repo()
    obs   = _obs()
    results = []
    errors  = []

    def _read():
        try:
            results.append(gw.evaluate_symbol("RELIANCE", obs, lib, msnap, repo))
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=_read) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ok(len(errors) == 0, f"errors: {errors}")
    ok(len(results) == 10)
    return "10 concurrent reads succeed"

def T77():
    gw     = _gateway()
    lib    = _library()
    msnap  = _market_snapshot()
    repo   = _tmp_repo_with_dna()
    errors = []

    def _eval():
        try:
            gw.evaluate_symbol("RELIANCE", _obs(), lib, msnap, repo)
        except Exception as exc:
            errors.append(str(exc))

    def _stats():
        try:
            repo.statistics()
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=(_eval if i % 2 == 0 else _stats)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ok(len(errors) == 0, f"errors: {errors}")
    return "mixed evaluate/IDR-stats concurrent calls succeed"

def T78():
    gw    = _gateway()
    lib   = _library()
    msnap = _market_snapshot()
    repo  = _tmp_repo()
    # Verify result is not mutated between calls
    r1 = gw.evaluate_symbol("RELIANCE", _obs(), lib, msnap, repo)
    r2 = gw.evaluate_symbol("RELIANCE", _obs(), lib, msnap, repo)
    ok(r1.result_id == r2.result_id, "result_id not stable across calls")
    ok(abs(r1.raw_pmci - r2.raw_pmci) < 1e-9, "raw_pmci changed between identical calls")
    return "repeated identical calls produce identical deterministic results"

def T79():
    # evaluate_symbol with a different symbol gives different result_id
    gw    = _gateway()
    lib   = _library()
    msnap = _market_snapshot()
    repo  = _tmp_repo()
    r1 = gw.evaluate_symbol("RELIANCE", _obs("RELIANCE"), lib, msnap, repo)
    r2 = gw.evaluate_symbol("TCS", _obs("TCS"), lib, msnap, repo)
    ok(r1.result_id != r2.result_id, "different symbols must give different result_ids")
    ok(r1.symbol == "RELIANCE")
    ok(r2.symbol == "TCS")
    return "different symbols produce different result_ids"

def T80():
    # statistics on 5 symbols produces correct counts
    gw    = _gateway()
    lib   = _library()
    msnap = _market_snapshot()
    repo  = _tmp_repo()
    snap  = _daily_snapshot(["A", "B", "C", "D", "E"])
    res   = gw.evaluate_universe(snap, lib, msnap, repo)
    stats = gw.statistics(res)
    ok(stats.total_symbols == 5)
    ok(stats.high_quality_count + stats.low_quality_count <= 5)
    return f"statistics on 5 symbols: high={stats.high_quality_count}, low={stats.low_quality_count}"


# =============================================================================
# T81-T86: get_context(), get_pmci(), get_cds()
# =============================================================================

def T81():
    gw  = _gateway()
    ctx = gw.get_context(_market_snapshot())
    ok(ctx is not None)
    ok(0.0 <= ctx.context_score <= 1.0)
    return f"get_context() returns MarketContext with context_score={ctx.context_score:.3f}"

def T82():
    gw   = _gateway()
    ctx  = gw.get_context(_market_snapshot())
    ok(len(ctx.regime) > 0, "regime is empty")
    ok(len(ctx.components) > 0, "no components")
    return f"get_context() regime={ctx.regime}, {len(ctx.components)} components"

def T83():
    gw      = _gateway()
    pmci_r  = gw.get_pmci(_obs(), _library())
    ok(pmci_r is not None)
    ok(0.0 <= pmci_r.pmci_score <= 1.0)
    return f"get_pmci() returns PMCIResult with pmci_score={pmci_r.pmci_score:.3f}"

def T84():
    gw      = _gateway()
    pmci_r  = gw.get_pmci(_obs(), _library(), regime="bull_trend")
    ok(pmci_r.regime == "bull_trend", f"expected bull_trend got {pmci_r.regime}")
    return "get_pmci() passes regime to PMCIEngine"

def T85():
    gw     = _gateway()
    ctx    = gw.get_context(_market_snapshot())
    cds_r  = gw.get_cds(_library(), ctx)
    ok(cds_r is not None)
    ok(isinstance(cds_r, CDSLibraryResult))
    return f"get_cds() returns CDSLibraryResult with {len(cds_r.scores)} scores"

def T86():
    gw     = _gateway()
    ctx    = gw.get_context(_market_snapshot())
    cds_r  = gw.get_cds(_library(), ctx)
    ok(0.0 <= cds_r.statistics.avg_cds <= 1.0)
    return f"get_cds() statistics.avg_cds={cds_r.statistics.avg_cds:.3f}"


# =============================================================================
# T87-T90: Explainability — every required field has evidence backing
# =============================================================================

def T87():
    _, res = _full_eval()
    components = {e.component for e in res.evidence}
    required   = {"raw_pmci", "ca_pmci", "cds_score", "winner_dna_match",
                  "loser_dna_match", "evidence_count", "context_score",
                  "dna_freshness", "dna_drift", "institutional_confidence",
                  "context_adjustment"}
    missing = required - components
    ok(len(missing) == 0, f"missing evidence for: {missing}")
    return f"all {len(required)} required fields have evidence items"

def T88():
    _, res = _full_eval()
    # Every evidence item has a non-trivial explanation
    bad = [e.component for e in res.evidence if len(e.explanation) < 10]
    ok(len(bad) == 0, f"trivial explanations for: {bad}")
    return "all evidence items have non-trivial explanations"

def T89():
    _, res = _full_eval()
    # Every evidence item has raw dict with at least one key
    bad = [e.component for e in res.evidence if not e.raw]
    ok(len(bad) == 0, f"empty raw dict for: {bad}")
    return "all evidence items have non-empty raw dict"

def T90():
    # Full to_dict() call on PlatformIntelligence succeeds and has all required keys
    _, res = _full_eval()
    d      = res.to_dict()
    for key in ("result_id", "symbol", "evaluation_date", "raw_pmci", "ca_pmci",
                "cds_score", "winner_dna_match", "loser_dna_match", "evidence_count",
                "confidence", "dna_freshness", "dna_drift", "institutional_confidence",
                "context_score", "regime", "context_adjustment", "evidence",
                "platform_confidence", "recommendation_context", "explanation"):
        ok(key in d, f"missing key in to_dict(): {key}")
    return f"PlatformIntelligence.to_dict() has all {len(d)} expected keys"


# =============================================================================
# Runner
# =============================================================================

if __name__ == "__main__":
    runner = TestRunner()
    for i, fn in enumerate([
        T01, T02, T03, T04, T05, T06, T07, T08, T09, T10,
        T11, T12, T13, T14, T15, T16, T17, T18, T19, T20,
        T21, T22, T23, T24, T25, T26, T27, T28, T29, T30,
        T31, T32, T33, T34, T35, T36, T37, T38, T39, T40,
        T41, T42, T43, T44, T45, T46, T47, T48, T49, T50,
        T51, T52, T53, T54, T55, T56, T57, T58, T59, T60,
        T61, T62, T63, T64, T65, T66, T67,
        T68, T69, T70, T71, T72, T73,
        T74, T75, T76, T77, T78, T79, T80,
        T81, T82, T83, T84, T85, T86,
        T87, T88, T89, T90,
    ], start=1):
        runner.run(f"T{i:02d} {fn.__doc__ or fn.__name__[1:]}", fn)
    sys.exit(runner.report())

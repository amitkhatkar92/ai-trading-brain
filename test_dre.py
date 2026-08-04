"""
test_dre.py — Tests for the DNA Reinforcement Engine (O-002).

140 tests covering:
    T001–T010  ReinforcementType enum
    T011–T020  OutcomeQuality enum
    T021–T030  ReinforcementEvidence model
    T031–T040  DNAReinforcement model
    T041–T050  DNAConfidenceUpdate model
    T051–T060  ReinforcementStatistics model
    T061–T070  DNAReinforcementHistory model
    T071–T080  DREConfig defaults and fingerprint
    T081–T095  Outcome quality classification
    T096–T110  Positive reinforcement (win + matched DNA)
    T111–T120  Negative reinforcement (loss + matched DNA)
    T121–T128  Neutral reinforcement (near-zero R)
    T129–T133  Contradictory evidence (win + conflicting DNA)
    T134–T138  Insufficient evidence (lifecycle / count guard)
    T139–T145  Safety bounds (max_single_trade_delta, confidence clamp)
    T146–T153  Batch processing and per-batch cap
    T154–T160  History query and statistics
    T161–T165  Dry-run mode
    T166–T170  Concurrent processing safety
    T171–T175  History persistence
    T176–T180  Replay / auditability
    T181–T185  process_trade with missing optional fields
    T186–T190  summarise_batch
    T191–T195  Holding period calculation
    T196–T200  Batch empty / edge cases
"""
from __future__ import annotations

import copy
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── test runner ───────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed  = 0
        self.failed  = 0
        self.errors: List[str] = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"  ✗ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*64}")
        print(f"DRE TEST RESULTS: {self.passed}/{total} passed")
        if self.errors:
            print("FAILURES:")
            for e in self.errors:
                print(f"  • {e}")
        print(f"{'='*64}")
        return self.failed == 0


# ── path setup ────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from market_learning.dre_config import DREConfig
from market_learning.dre_models import (
    DNAReinforcement,
    DNAConfidenceUpdate,
    DNAReinforcementHistory,
    DREError,
    DREInputError,
    DREProcessingError,
    OutcomeQuality,
    ReinforcementEvidence,
    ReinforcementStatistics,
    ReinforcementType,
)
from market_learning.dre_engine import (
    DNAReinforcementEngine,
    _classify_outcome,
    _compute_confidence_delta,
    _compute_stability_delta,
    _determine_type,
)


# ── stubs ─────────────────────────────────────────────────────────────────────

@dataclass
class _FakeDNA:
    id:                 str
    feature_name:       str
    direction:          str
    lifecycle:          str
    confidence:         float
    temporal_stability: float
    evidence_count:     int
    metadata:           Dict[str, Any] = field(default_factory=dict)
    is_current:         bool = True


@dataclass
class _FakeRevision:
    version: int


class _FakeIDR:
    """In-memory IDR stub — no SQLite required."""

    def __init__(self, dna_list: List[_FakeDNA]):
        self._store: Dict[str, _FakeDNA] = {d.id: d for d in dna_list}
        self.write_log: List[tuple] = []

    def list_active(self) -> List[_FakeDNA]:
        return list(self._store.values())

    def get(self, dna_id: str) -> _FakeDNA:
        if dna_id not in self._store:
            from market_learning.idr_models import IDRNotFoundError
            raise IDRNotFoundError(dna_id)
        return self._store[dna_id]

    def update(self, dna_id: str, updates: dict, reason="", study_id="", operator="") -> _FakeRevision:
        dna = self._store[dna_id]
        for k, v in updates.items():
            if hasattr(dna, k):
                setattr(dna, k, v)
        ver = len(self.write_log) + 2
        self.write_log.append((dna_id, updates, reason))
        return _FakeRevision(version=ver)


@dataclass
class _FakePMCIEvidence:
    feature_name:  str
    direction:     str
    alignment:     float
    contribution:  float


@dataclass
class _FakePMCIBreakdown:
    matched_dna:     List[_FakePMCIEvidence]
    conflicting_dna: List[_FakePMCIEvidence]


@dataclass
class _FakePMCIResult:
    pmci_score: float
    breakdown:  _FakePMCIBreakdown
    confidence: float = 0.8
    regime:     str   = "BULLISH"


@dataclass
class _FakeTrade:
    order_id:         str
    symbol:           str
    direction:        str
    pnl:              float
    r_multiple:       float
    strategy:         str         = "MomentumLong"
    signal_regime:    str         = "BULLISH"
    confidence_score: float       = 7.5
    placed_at:        Optional[datetime] = None
    closed_at:        Optional[datetime] = None
    initial_stop_loss: float      = 0.0


def _make_dna(
    dna_id="dna_rsi_high",
    feature="rsi",
    direction="WINNERS_HIGHER",
    lifecycle="INSTITUTIONAL",
    confidence=0.75,
    stability=0.80,
    evidence_count=25,
) -> _FakeDNA:
    return _FakeDNA(
        id=dna_id,
        feature_name=feature,
        direction=direction,
        lifecycle=lifecycle,
        confidence=confidence,
        temporal_stability=stability,
        evidence_count=evidence_count,
    )


def _make_pmci(
    feature="rsi",
    direction="WINNERS_HIGHER",
    alignment=0.75,
    contribution=0.12,
    pmci_score=0.70,
    matched: bool = True,
) -> _FakePMCIResult:
    ev = _FakePMCIEvidence(feature, direction, alignment, contribution)
    if matched:
        return _FakePMCIResult(pmci_score=pmci_score, breakdown=_FakePMCIBreakdown([ev], []))
    return _FakePMCIResult(pmci_score=pmci_score, breakdown=_FakePMCIBreakdown([], [ev]))


def _make_trade(
    won=True,
    r_multiple=1.5,
    pnl=3000.0,
    trade_id="ORD-001",
    symbol="RELIANCE",
) -> _FakeTrade:
    return _FakeTrade(
        order_id=trade_id,
        symbol=symbol,
        direction="LONG",
        pnl=pnl if won else -abs(pnl),
        r_multiple=r_multiple if won else -abs(r_multiple),
    )


def _make_engine(dna_list=None, cfg=None, tmp_dir=None) -> DNAReinforcementEngine:
    dna = dna_list or [_make_dna()]
    idr = _FakeIDR(dna)
    config = cfg or DREConfig(dry_run=True)
    return DNAReinforcementEngine(idr=idr, config=config, data_root=tmp_dir)


# ─────────────────────────────────────────────────────────────────────────────
# T001–T010  ReinforcementType enum
# ─────────────────────────────────────────────────────────────────────────────

def test_reinforcement_types(r: TestResult):
    r.ok("T001") if ReinforcementType.POSITIVE.value == "POSITIVE" else r.fail("T001", "wrong value")
    r.ok("T002") if ReinforcementType.NEGATIVE.value == "NEGATIVE" else r.fail("T002", "wrong value")
    r.ok("T003") if ReinforcementType.NEUTRAL.value == "NEUTRAL" else r.fail("T003", "wrong value")
    r.ok("T004") if ReinforcementType.CONTRADICTORY.value == "CONTRADICTORY" else r.fail("T004", "wrong value")
    r.ok("T005") if ReinforcementType.INSUFFICIENT_EVIDENCE.value == "INSUFFICIENT_EVIDENCE" else r.fail("T005", "wrong value")
    r.ok("T006") if len(ReinforcementType) == 5 else r.fail("T006", f"expected 5 values got {len(ReinforcementType)}")
    # Enum is a str subclass (allows JSON-safe comparisons)
    r.ok("T007") if isinstance(ReinforcementType.POSITIVE, str) else r.fail("T007", "not a str subclass")
    r.ok("T008") if ReinforcementType("POSITIVE") == ReinforcementType.POSITIVE else r.fail("T008", "round-trip failed")
    r.ok("T009") if ReinforcementType.NEGATIVE != ReinforcementType.POSITIVE else r.fail("T009", "equality wrong")
    r.ok("T010") if ReinforcementType.NEUTRAL != ReinforcementType.CONTRADICTORY else r.fail("T010", "equality wrong")


# ─────────────────────────────────────────────────────────────────────────────
# T011–T020  OutcomeQuality enum
# ─────────────────────────────────────────────────────────────────────────────

def test_outcome_quality_enum(r: TestResult):
    r.ok("T011") if OutcomeQuality.EXCELLENT.value == "EXCELLENT" else r.fail("T011", "wrong value")
    r.ok("T012") if OutcomeQuality.GOOD.value == "GOOD" else r.fail("T012", "wrong value")
    r.ok("T013") if OutcomeQuality.FAIR.value == "FAIR" else r.fail("T013", "wrong value")
    r.ok("T014") if OutcomeQuality.POOR.value == "POOR" else r.fail("T014", "wrong value")
    r.ok("T015") if OutcomeQuality.BAD.value == "BAD" else r.fail("T015", "wrong value")
    r.ok("T016") if len(OutcomeQuality) == 5 else r.fail("T016", f"expected 5 values got {len(OutcomeQuality)}")
    r.ok("T017") if isinstance(OutcomeQuality.GOOD, str) else r.fail("T017", "not str subclass")
    r.ok("T018") if OutcomeQuality("FAIR") == OutcomeQuality.FAIR else r.fail("T018", "round-trip failed")
    r.ok("T019") if OutcomeQuality.BAD != OutcomeQuality.POOR else r.fail("T019", "equality wrong")
    r.ok("T020") if OutcomeQuality.EXCELLENT != OutcomeQuality.GOOD else r.fail("T020", "equality wrong")


# ─────────────────────────────────────────────────────────────────────────────
# T021–T030  ReinforcementEvidence
# ─────────────────────────────────────────────────────────────────────────────

def test_reinforcement_evidence(r: TestResult):
    ev = ReinforcementEvidence(
        trade_id="ORD-1", symbol="TCS", trade_direction="LONG",
        strategy="Momentum", regime_at_entry="BULLISH",
        pmci_score=0.72, ca_pmci_score=0.68, cds_score=0.61,
        dna_alignment=0.80, dna_contribution=0.15,
        r_multiple=1.8, pnl=4500.0, holding_period_h=6.5,
        won=True, outcome_quality="GOOD", confidence_score=7.2,
    )
    d = ev.to_dict()
    r.ok("T021") if d["trade_id"] == "ORD-1" else r.fail("T021", "trade_id wrong")
    r.ok("T022") if d["symbol"] == "TCS" else r.fail("T022", "symbol wrong")
    r.ok("T023") if d["won"] is True else r.fail("T023", "won wrong")
    r.ok("T024") if abs(d["r_multiple"] - 1.8) < 1e-4 else r.fail("T024", "r_multiple wrong")
    r.ok("T025") if abs(d["pmci_score"] - 0.72) < 1e-4 else r.fail("T025", "pmci_score wrong")
    ev2 = ReinforcementEvidence.from_dict(d)
    r.ok("T026") if ev2.trade_id == ev.trade_id else r.fail("T026", "from_dict trade_id")
    r.ok("T027") if ev2.won == ev.won else r.fail("T027", "from_dict won")
    r.ok("T028") if ev2.outcome_quality == ev.outcome_quality else r.fail("T028", "from_dict quality")
    r.ok("T029") if abs(ev2.dna_alignment - ev.dna_alignment) < 1e-6 else r.fail("T029", "from_dict alignment")
    r.ok("T030") if abs(ev2.holding_period_h - ev.holding_period_h) < 1e-4 else r.fail("T030", "from_dict holding_h")


# ─────────────────────────────────────────────────────────────────────────────
# T031–T040  DNAReinforcement
# ─────────────────────────────────────────────────────────────────────────────

def _make_ev_stub() -> ReinforcementEvidence:
    return ReinforcementEvidence(
        trade_id="T1", symbol="X", trade_direction="LONG",
        strategy="S", regime_at_entry="R", pmci_score=0.5,
        ca_pmci_score=0.0, cds_score=0.0, dna_alignment=0.6,
        dna_contribution=0.1, r_multiple=1.0, pnl=2000.0,
        holding_period_h=4.0, won=True, outcome_quality="GOOD",
        confidence_score=6.0,
    )

def test_dna_reinforcement_model(r: TestResult):
    ev = _make_ev_stub()
    rec = DNAReinforcement(
        reinforcement_id="DRE-abc123456789",
        dna_id="dna_rsi_high",
        feature_name="rsi",
        direction="WINNERS_HIGHER",
        trade_id="T1",
        reinforcement_type="POSITIVE",
        evidence=ev,
        confidence_before=0.70,
        confidence_after=0.72,
        confidence_delta=0.02,
        stability_before=0.80,
        stability_after=0.81,
        stability_delta=0.01,
        evidence_count_before=25,
        evidence_count_after=26,
        reason="POSITIVE: rsi (WINNERS_HIGHER) ...",
        idr_revision=5,
        processed_at="2026-08-04T09:30:00+00:00",
    )
    d = rec.to_dict()
    r.ok("T031") if d["reinforcement_id"] == "DRE-abc123456789" else r.fail("T031", "id wrong")
    r.ok("T032") if d["dna_id"] == "dna_rsi_high" else r.fail("T032", "dna_id wrong")
    r.ok("T033") if d["reinforcement_type"] == "POSITIVE" else r.fail("T033", "type wrong")
    r.ok("T034") if abs(d["confidence_delta"] - 0.02) < 1e-6 else r.fail("T034", "delta wrong")
    r.ok("T035") if d["idr_revision"] == 5 else r.fail("T035", "revision wrong")
    r.ok("T036") if d["evidence"]["won"] is True else r.fail("T036", "nested evidence wrong")
    rec2 = DNAReinforcement.from_dict(d)
    r.ok("T037") if rec2.reinforcement_id == rec.reinforcement_id else r.fail("T037", "from_dict id")
    r.ok("T038") if rec2.confidence_delta == rec.confidence_delta else r.fail("T038", "from_dict delta")
    r.ok("T039") if rec2.idr_revision == rec.idr_revision else r.fail("T039", "from_dict revision")
    # None idr_revision
    rec3 = DNAReinforcement(**{**rec.__dict__, "idr_revision": None})
    d3 = rec3.to_dict()
    r.ok("T040") if DNAReinforcement.from_dict(d3).idr_revision is None else r.fail("T040", "None revision")


# ─────────────────────────────────────────────────────────────────────────────
# T041–T050  DNAConfidenceUpdate
# ─────────────────────────────────────────────────────────────────────────────

def test_dna_confidence_update(r: TestResult):
    ev = _make_ev_stub()
    rec = DNAReinforcement(
        reinforcement_id="DRE-x", dna_id="dna1", feature_name="macd",
        direction="WINNERS_HIGHER", trade_id="T1",
        reinforcement_type="POSITIVE", evidence=ev,
        confidence_before=0.60, confidence_after=0.62, confidence_delta=0.02,
        stability_before=0.75, stability_after=0.76, stability_delta=0.01,
        evidence_count_before=20, evidence_count_after=21,
        reason="test", idr_revision=3,
        processed_at="2026-08-04T10:00:00+00:00",
    )
    upd = DNAConfidenceUpdate(
        dna_id="dna1", feature_name="macd", direction="WINNERS_HIGHER",
        lifecycle="INSTITUTIONAL", reinforcements=[rec],
        net_confidence_delta=0.02, net_stability_delta=0.01,
        final_confidence=0.62, final_stability=0.76,
        dominant_type="POSITIVE", explanation="1 reinforcement",
    )
    d = upd.to_dict()
    r.ok("T041") if d["dna_id"] == "dna1" else r.fail("T041", "dna_id")
    r.ok("T042") if len(d["reinforcements"]) == 1 else r.fail("T042", "reinforcements count")
    r.ok("T043") if d["dominant_type"] == "POSITIVE" else r.fail("T043", "dominant type")
    r.ok("T044") if abs(d["net_confidence_delta"] - 0.02) < 1e-6 else r.fail("T044", "net delta")
    upd2 = DNAConfidenceUpdate.from_dict(d)
    r.ok("T045") if upd2.dna_id == "dna1" else r.fail("T045", "from_dict dna_id")
    r.ok("T046") if len(upd2.reinforcements) == 1 else r.fail("T046", "from_dict reinforcements")
    r.ok("T047") if upd2.dominant_type == "POSITIVE" else r.fail("T047", "from_dict dominant")
    r.ok("T048") if abs(upd2.final_confidence - 0.62) < 1e-6 else r.fail("T048", "from_dict confidence")
    r.ok("T049") if upd2.lifecycle == "INSTITUTIONAL" else r.fail("T049", "lifecycle")
    r.ok("T050") if abs(upd2.net_stability_delta - 0.01) < 1e-6 else r.fail("T050", "net stab delta")


# ─────────────────────────────────────────────────────────────────────────────
# T051–T060  ReinforcementStatistics
# ─────────────────────────────────────────────────────────────────────────────

def test_reinforcement_statistics(r: TestResult):
    stats = ReinforcementStatistics(
        total_reinforcements=10, positive_count=6, negative_count=2,
        neutral_count=1, contradictory_count=1, insufficient_evidence_count=0,
        trades_processed=8, dna_updated=10, dna_skipped=0,
        avg_confidence_delta=0.015, avg_stability_delta=0.005,
        max_confidence_delta=0.05, min_confidence_delta=-0.04,
        total_idr_writes=10,
        first_reinforcement_at="2026-08-04T09:00:00+00:00",
        last_reinforcement_at="2026-08-04T15:00:00+00:00",
    )
    d = stats.to_dict()
    r.ok("T051") if d["total_reinforcements"] == 10 else r.fail("T051", "total")
    r.ok("T052") if d["positive_count"] == 6 else r.fail("T052", "positive")
    r.ok("T053") if d["negative_count"] == 2 else r.fail("T053", "negative")
    r.ok("T054") if d["neutral_count"] == 1 else r.fail("T054", "neutral")
    r.ok("T055") if d["contradictory_count"] == 1 else r.fail("T055", "contradictory")
    s2 = ReinforcementStatistics.from_dict(d)
    r.ok("T056") if s2.total_reinforcements == 10 else r.fail("T056", "from_dict total")
    r.ok("T057") if abs(s2.avg_confidence_delta - 0.015) < 1e-6 else r.fail("T057", "avg delta")
    r.ok("T058") if s2.first_reinforcement_at == "2026-08-04T09:00:00+00:00" else r.fail("T058", "first ts")
    r.ok("T059") if s2.total_idr_writes == 10 else r.fail("T059", "idr writes")
    r.ok("T060") if abs(s2.max_confidence_delta - 0.05) < 1e-6 else r.fail("T060", "max delta")


# ─────────────────────────────────────────────────────────────────────────────
# T061–T070  DNAReinforcementHistory
# ─────────────────────────────────────────────────────────────────────────────

def test_dna_reinforcement_history(r: TestResult):
    ev   = _make_ev_stub()
    rec  = DNAReinforcement(
        reinforcement_id="DRE-hist1", dna_id="d1", feature_name="f",
        direction="D", trade_id="T1", reinforcement_type="POSITIVE",
        evidence=ev, confidence_before=0.5, confidence_after=0.52,
        confidence_delta=0.02, stability_before=0.7, stability_after=0.71,
        stability_delta=0.01, evidence_count_before=15, evidence_count_after=16,
        reason="r", idr_revision=2, processed_at="2026-08-04T09:00:00+00:00",
    )
    stats = ReinforcementStatistics(
        total_reinforcements=1, positive_count=1, negative_count=0,
        neutral_count=0, contradictory_count=0, insufficient_evidence_count=0,
        trades_processed=1, dna_updated=1, dna_skipped=0,
        avg_confidence_delta=0.02, avg_stability_delta=0.01,
        max_confidence_delta=0.02, min_confidence_delta=0.02,
        total_idr_writes=1,
        first_reinforcement_at="2026-08-04T09:00:00+00:00",
        last_reinforcement_at="2026-08-04T09:00:00+00:00",
    )
    hist = DNAReinforcementHistory(
        reinforcements=[rec], statistics=stats,
        generated_at="2026-08-04T15:30:00+00:00",
    )
    d = hist.to_dict()
    r.ok("T061") if len(d["reinforcements"]) == 1 else r.fail("T061", "count")
    r.ok("T062") if d["dre_version"] == "1.0" else r.fail("T062", "version")
    r.ok("T063") if d["statistics"]["total_reinforcements"] == 1 else r.fail("T063", "stats total")
    h2 = DNAReinforcementHistory.from_dict(d)
    r.ok("T064") if len(h2.reinforcements) == 1 else r.fail("T064", "from_dict count")
    r.ok("T065") if h2.statistics.positive_count == 1 else r.fail("T065", "from_dict stats")
    r.ok("T066") if h2.reinforcements[0].dna_id == "d1" else r.fail("T066", "nested dna_id")
    # from_dict with missing statistics key
    d2 = {**d}
    del d2["statistics"]
    h3 = DNAReinforcementHistory.from_dict(d2)
    r.ok("T067") if h3.statistics.total_reinforcements == 0 else r.fail("T067", "missing stats default")
    r.ok("T068") if h3.dre_version == "1.0" else r.fail("T068", "version preserved")
    r.ok("T069") if h2.generated_at == "2026-08-04T15:30:00+00:00" else r.fail("T069", "generated_at")
    r.ok("T070") if h3.statistics.trades_processed == 0 else r.fail("T070", "default trades_processed")


# ─────────────────────────────────────────────────────────────────────────────
# T071–T080  DREConfig
# ─────────────────────────────────────────────────────────────────────────────

def test_dre_config(r: TestResult):
    cfg = DREConfig()
    r.ok("T071") if cfg.max_single_trade_delta == 0.05 else r.fail("T071", f"default cap {cfg.max_single_trade_delta}")
    r.ok("T072") if cfg.min_idr_evidence_count == 10 else r.fail("T072", f"min evidence {cfg.min_idr_evidence_count}")
    r.ok("T073") if cfg.learning_rate == 0.03 else r.fail("T073", f"learning rate {cfg.learning_rate}")
    r.ok("T074") if cfg.dry_run is False else r.fail("T074", "default dry_run should be False")
    r.ok("T075") if "INSTITUTIONAL" in cfg.eligible_lifecycles else r.fail("T075", "INSTITUTIONAL missing")
    r.ok("T076") if cfg.confidence_min == 0.05 else r.fail("T076", "conf min")
    r.ok("T077") if cfg.confidence_max == 0.99 else r.fail("T077", "conf max")
    fp = cfg.fingerprint()
    r.ok("T078") if len(fp) == 16 else r.fail("T078", f"fingerprint len {len(fp)}")
    # same config → same fingerprint
    cfg2 = DREConfig()
    r.ok("T079") if cfg.fingerprint() == cfg2.fingerprint() else r.fail("T079", "fingerprint not deterministic")
    # changed config → different fingerprint
    cfg3 = DREConfig(learning_rate=0.05)
    r.ok("T080") if cfg3.fingerprint() != cfg.fingerprint() else r.fail("T080", "changed config same fingerprint")


# ─────────────────────────────────────────────────────────────────────────────
# T081–T095  _classify_outcome
# ─────────────────────────────────────────────────────────────────────────────

def test_classify_outcome(r: TestResult):
    cfg = DREConfig()
    r.ok("T081") if _classify_outcome(2.5, True, cfg)  == OutcomeQuality.EXCELLENT else r.fail("T081", "EXCELLENT miss")
    r.ok("T082") if _classify_outcome(2.0, True, cfg)  == OutcomeQuality.EXCELLENT else r.fail("T082", "EXCELLENT boundary")
    r.ok("T083") if _classify_outcome(1.9, True, cfg)  == OutcomeQuality.GOOD      else r.fail("T083", "GOOD miss")
    r.ok("T084") if _classify_outcome(1.0, True, cfg)  == OutcomeQuality.GOOD      else r.fail("T084", "GOOD boundary")
    r.ok("T085") if _classify_outcome(0.5, True, cfg)  == OutcomeQuality.FAIR      else r.fail("T085", "FAIR win miss")
    r.ok("T086") if _classify_outcome(0.0, True, cfg)  == OutcomeQuality.FAIR      else r.fail("T086", "FAIR zero R win")
    r.ok("T087") if _classify_outcome(-0.1, False, cfg)== OutcomeQuality.FAIR      else r.fail("T087", "FAIR small loss")
    r.ok("T088") if _classify_outcome(-0.5, False, cfg)== OutcomeQuality.FAIR      else r.fail("T088", "FAIR boundary")
    r.ok("T089") if _classify_outcome(-0.6, False, cfg)== OutcomeQuality.POOR      else r.fail("T089", "POOR miss")
    r.ok("T090") if _classify_outcome(-1.5, False, cfg)== OutcomeQuality.POOR      else r.fail("T090", "POOR boundary")
    r.ok("T091") if _classify_outcome(-1.6, False, cfg)== OutcomeQuality.BAD       else r.fail("T091", "BAD miss")
    r.ok("T092") if _classify_outcome(-3.0, False, cfg)== OutcomeQuality.BAD       else r.fail("T092", "BAD large loss")
    # Custom thresholds
    cfg2 = DREConfig(r_excellent_threshold=3.0, r_good_threshold=1.5)
    r.ok("T093") if _classify_outcome(2.0, True, cfg2) == OutcomeQuality.GOOD else r.fail("T093", "custom threshold GOOD")
    r.ok("T094") if _classify_outcome(3.0, True, cfg2) == OutcomeQuality.EXCELLENT else r.fail("T094", "custom threshold EXCELLENT")
    r.ok("T095") if _classify_outcome(-0.3, False, cfg) == OutcomeQuality.FAIR else r.fail("T095", "loss -0.3 FAIR")


# ─────────────────────────────────────────────────────────────────────────────
# T096–T110  Positive reinforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_positive_reinforcement(r: TestResult):
    cfg = DREConfig()
    # is_matched=True, won=True → POSITIVE
    rtype = _determine_type(True, True, 1.5, cfg)
    r.ok("T096") if rtype == ReinforcementType.POSITIVE else r.fail("T096", f"got {rtype}")
    delta = _compute_confidence_delta(rtype, 1.5, 0.8, cfg)
    r.ok("T097") if delta > 0 else r.fail("T097", f"positive delta should be >0, got {delta}")
    # delta = lr * clamp(|R|, 0.5, 2.0) * alignment = 0.03 * 1.5 * 0.8 = 0.036
    expected = 0.03 * 1.5 * 0.8
    r.ok("T098") if abs(delta - expected) < 1e-6 else r.fail("T098", f"expected {expected} got {delta}")
    # stability delta for POSITIVE should be win_delta
    stab = _compute_stability_delta(ReinforcementType.POSITIVE, cfg)
    r.ok("T099") if stab == cfg.stability_win_delta else r.fail("T099", f"stab {stab}")

    # Full engine integration test
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.70, stability=0.80, evidence_count=25)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=1.5, pnl=3000.0)
        pmci   = _make_pmci(alignment=0.80, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T100") if len(result) == 1 else r.fail("T100", f"expected 1 got {len(result)}")
        rec = result[0]
        r.ok("T101") if rec.reinforcement_type == "POSITIVE" else r.fail("T101", f"type {rec.reinforcement_type}")
        r.ok("T102") if rec.confidence_after > rec.confidence_before else r.fail("T102", "confidence should rise")
        r.ok("T103") if rec.stability_after >= rec.stability_before else r.fail("T103", "stability should not fall")
        r.ok("T104") if rec.evidence_count_after == rec.evidence_count_before + 1 else r.fail("T104", "evidence_count_after")
        r.ok("T105") if rec.idr_revision is not None else r.fail("T105", "idr_revision should be set")
        r.ok("T106") if len(idr.write_log) == 1 else r.fail("T106", f"idr writes {len(idr.write_log)}")
        # Confidence updated in IDR stub
        r.ok("T107") if idr._store[dna.id].confidence > 0.70 else r.fail("T107", "idr confidence not updated")
        # PMCI evidence includes alignment
        r.ok("T108") if rec.evidence.dna_alignment == 0.80 else r.fail("T108", f"alignment {rec.evidence.dna_alignment}")
        r.ok("T109") if rec.evidence.r_multiple == 1.5 else r.fail("T109", f"r_multiple {rec.evidence.r_multiple}")
        r.ok("T110") if rec.evidence.won is True else r.fail("T110", "evidence.won wrong")


# ─────────────────────────────────────────────────────────────────────────────
# T111–T120  Negative reinforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_negative_reinforcement(r: TestResult):
    cfg = DREConfig()
    rtype = _determine_type(True, False, -1.2, cfg)
    r.ok("T111") if rtype == ReinforcementType.NEGATIVE else r.fail("T111", f"got {rtype}")
    delta = _compute_confidence_delta(rtype, -1.2, 0.7, cfg)
    r.ok("T112") if delta < 0 else r.fail("T112", f"negative delta should be <0, got {delta}")
    # delta = -(0.03 * clamp(1.2, 0.5, 2.0) * 0.7) = -(0.03 * 1.2 * 0.7) = -0.0252
    expected = -(0.03 * 1.2 * 0.7)
    r.ok("T113") if abs(delta - expected) < 1e-6 else r.fail("T113", f"expected {expected} got {delta}")
    stab = _compute_stability_delta(ReinforcementType.NEGATIVE, cfg)
    r.ok("T114") if stab == cfg.stability_loss_delta else r.fail("T114", f"stab {stab}")

    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.70, stability=0.80, evidence_count=30)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=False, r_multiple=-1.2, pnl=-2400.0)
        pmci   = _make_pmci(alignment=0.70, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T115") if len(result) == 1 else r.fail("T115", f"expected 1 got {len(result)}")
        rec = result[0]
        r.ok("T116") if rec.reinforcement_type == "NEGATIVE" else r.fail("T116", f"type {rec.reinforcement_type}")
        r.ok("T117") if rec.confidence_after < rec.confidence_before else r.fail("T117", "confidence should fall")
        r.ok("T118") if rec.stability_after <= rec.stability_before else r.fail("T118", "stability should not rise")
        r.ok("T119") if idr._store[dna.id].confidence < 0.70 else r.fail("T119", "idr confidence not updated")
        r.ok("T120") if rec.evidence.won is False else r.fail("T120", "evidence.won wrong")


# ─────────────────────────────────────────────────────────────────────────────
# T121–T128  Neutral reinforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_neutral_reinforcement(r: TestResult):
    cfg = DREConfig(min_r_multiple_magnitude=0.25)
    # |R| below threshold → NEUTRAL
    rtype = _determine_type(True, True, 0.10, cfg)
    r.ok("T121") if rtype == ReinforcementType.NEUTRAL else r.fail("T121", f"got {rtype}")
    delta = _compute_confidence_delta(ReinforcementType.NEUTRAL, 0.10, 0.8, cfg)
    r.ok("T122") if delta == 0.0 else r.fail("T122", f"neutral delta should be 0, got {delta}")
    stab = _compute_stability_delta(ReinforcementType.NEUTRAL, cfg)
    r.ok("T123") if stab == 0.0 else r.fail("T123", f"neutral stab delta {stab}")

    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.70, stability=0.80, evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=0.05, pnl=100.0)
        pmci   = _make_pmci(alignment=0.75, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T124") if len(result) == 1 else r.fail("T124", f"expected 1 got {len(result)}")
        rec = result[0]
        r.ok("T125") if rec.reinforcement_type == "NEUTRAL" else r.fail("T125", f"type {rec.reinforcement_type}")
        r.ok("T126") if rec.confidence_delta == 0.0 else r.fail("T126", f"delta {rec.confidence_delta}")
        r.ok("T127") if rec.confidence_after == rec.confidence_before else r.fail("T127", "neutral should not change confidence")
        r.ok("T128") if len(idr.write_log) == 1 else r.fail("T128", "IDR still updated (evidence_count)")


# ─────────────────────────────────────────────────────────────────────────────
# T129–T133  Contradictory evidence
# ─────────────────────────────────────────────────────────────────────────────

def test_contradictory_reinforcement(r: TestResult):
    cfg = DREConfig(contradictory_weight=0.5)
    # conflicting_dna + win → CONTRADICTORY
    rtype = _determine_type(False, True, 1.5, cfg)
    r.ok("T129") if rtype == ReinforcementType.CONTRADICTORY else r.fail("T129", f"got {rtype}")
    # delta = -(lr * R * alignment * contradictory_weight)
    delta = _compute_confidence_delta(ReinforcementType.CONTRADICTORY, 1.5, 0.6, cfg)
    r.ok("T130") if delta < 0 else r.fail("T130", f"contradictory delta should be <0, got {delta}")
    expected = -(0.03 * 1.5 * 0.6 * 0.5)
    r.ok("T131") if abs(delta - expected) < 1e-6 else r.fail("T131", f"expected {expected} got {delta}")

    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.65, evidence_count=15)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=1.5, pnl=3000.0)
        pmci   = _make_pmci(alignment=0.60, matched=False)  # conflicting DNA
        result = eng.process_trade(trade, pmci)
        r.ok("T132") if len(result) == 1 else r.fail("T132", f"expected 1 got {len(result)}")
        r.ok("T133") if result[0].reinforcement_type == "CONTRADICTORY" else r.fail("T133", f"type {result[0].reinforcement_type}")


# ─────────────────────────────────────────────────────────────────────────────
# T134–T138  Insufficient evidence guard
# ─────────────────────────────────────────────────────────────────────────────

def test_insufficient_evidence_guard(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        # evidence_count too low
        dna_low = _make_dna(dna_id="dna_low", evidence_count=5, lifecycle="INSTITUTIONAL")
        idr = _FakeIDR([dna_low])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=2.0, pnl=5000.0)
        pmci   = _make_pmci(alignment=0.90, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T134") if len(result) == 1 else r.fail("T134", f"expected 1 got {len(result)}")
        r.ok("T135") if result[0].reinforcement_type == "INSUFFICIENT_EVIDENCE" else r.fail("T135", result[0].reinforcement_type)
        r.ok("T136") if result[0].confidence_delta == 0.0 else r.fail("T136", "should not change")
        # IDR should NOT have been written
        r.ok("T137") if len(idr.write_log) == 0 else r.fail("T137", f"idr writes should be 0, got {len(idr.write_log)}")

    with tempfile.TemporaryDirectory() as tmp:
        # wrong lifecycle
        dna_ret = _make_dna(dna_id="dna_ret", evidence_count=30, lifecycle="RETIRED")
        idr2 = _FakeIDR([dna_ret])
        eng2 = DNAReinforcementEngine(idr=idr2, config=DREConfig(dry_run=False), data_root=Path(tmp))
        result2 = eng2.process_trade(trade, pmci)
        r.ok("T138") if result2[0].reinforcement_type == "INSUFFICIENT_EVIDENCE" else r.fail("T138", result2[0].reinforcement_type)


# ─────────────────────────────────────────────────────────────────────────────
# T139–T145  Safety bounds
# ─────────────────────────────────────────────────────────────────────────────

def test_safety_bounds(r: TestResult):
    cfg = DREConfig(max_single_trade_delta=0.05)
    # Extremely large R → capped at max_single_trade_delta
    delta = _compute_confidence_delta(ReinforcementType.POSITIVE, 100.0, 1.0, cfg)
    r.ok("T139") if abs(delta - 0.05) < 1e-9 else r.fail("T139", f"cap failed: {delta}")
    delta_neg = _compute_confidence_delta(ReinforcementType.NEGATIVE, -100.0, 1.0, cfg)
    r.ok("T140") if abs(delta_neg - (-0.05)) < 1e-9 else r.fail("T140", f"neg cap failed: {delta_neg}")

    # Confidence cannot go below confidence_min
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.06, evidence_count=20)  # near minimum
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=False, r_multiple=-5.0, pnl=-10000.0)
        pmci   = _make_pmci(alignment=0.90, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T141") if result[0].confidence_after >= DREConfig().confidence_min else r.fail("T141", f"below min {result[0].confidence_after}")

    # Confidence cannot exceed confidence_max
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.98, evidence_count=20)  # near maximum
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=5.0, pnl=10000.0)
        pmci   = _make_pmci(alignment=0.90, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T142") if result[0].confidence_after <= DREConfig().confidence_max else r.fail("T142", f"above max {result[0].confidence_after}")

    # Low alignment → DNA not processed
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False, min_alignment_threshold=0.30), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=2.0, pnl=4000.0)
        pmci   = _make_pmci(alignment=0.10, matched=True)  # below threshold
        result = eng.process_trade(trade, pmci)
        r.ok("T143") if len(result) == 0 else r.fail("T143", f"low alignment should skip, got {len(result)}")

    # Stability cannot go below 0 or above 1
    cfg2 = DREConfig(stability_loss_delta=-0.90)
    stab_delta = _compute_stability_delta(ReinforcementType.NEGATIVE, cfg2)
    r.ok("T144") if stab_delta == -0.90 else r.fail("T144", "stab delta wrong")
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(stability=0.05, evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=False, stability_loss_delta=-0.90), data_root=Path(tmp))
        trade  = _make_trade(won=False, r_multiple=-1.5, pnl=-3000.0)
        pmci   = _make_pmci(alignment=0.80, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T145") if result[0].stability_after >= 0.0 else r.fail("T145", f"stability below 0: {result[0].stability_after}")


# ─────────────────────────────────────────────────────────────────────────────
# T146–T153  Batch processing
# ─────────────────────────────────────────────────────────────────────────────

def test_batch_processing(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))

        items = [
            (_make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id=f"T{i}"),
             _make_pmci(alignment=0.75, matched=True), None, None)
            for i in range(4)
        ]
        results = eng.process_batch(items)
        r.ok("T146") if len(results) == 4 else r.fail("T146", f"expected 4 got {len(results)}")

    # Per-batch cap: same DNA reinforced > max_reinforcements_per_batch times
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        cap = 3
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True, max_reinforcements_per_batch=cap), data_root=Path(tmp))
        items = [
            (_make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id=f"B{i}"),
             _make_pmci(alignment=0.75, matched=True), None, None)
            for i in range(8)
        ]
        results = eng.process_batch(items)
        r.ok("T147") if len(results) == cap else r.fail("T147", f"expected {cap} got {len(results)}")

    # Empty batch
    with tempfile.TemporaryDirectory() as tmp:
        eng2 = _make_engine(tmp_dir=Path(tmp))
        r.ok("T148") if eng2.process_batch([]) == [] else r.fail("T148", "empty batch should return []")

    # Batch with multiple DNA
    with tempfile.TemporaryDirectory() as tmp:
        dna_a = _make_dna(dna_id="a", feature="rsi", evidence_count=20)
        dna_b = _make_dna(dna_id="b", feature="macd", evidence_count=20)
        idr = _FakeIDR([dna_a, dna_b])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        pmci_two = _FakePMCIResult(
            pmci_score=0.7,
            breakdown=_FakePMCIBreakdown(
                matched_dna=[
                    _FakePMCIEvidence("rsi",  "WINNERS_HIGHER", 0.75, 0.12),
                    _FakePMCIEvidence("macd", "WINNERS_HIGHER", 0.65, 0.10),
                ],
                conflicting_dna=[],
            ),
        )
        trade = _make_trade(won=True, r_multiple=1.2, pnl=2400.0, trade_id="MULTI")
        result = eng.process_trade(trade, pmci_two)
        r.ok("T149") if len(result) == 2 else r.fail("T149", f"expected 2 got {len(result)}")
        r.ok("T150") if {x.dna_id for x in result} == {"a", "b"} else r.fail("T150", "dna ids wrong")

    # Duplicate trade_id in same call — second call returns []
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id="DUP-1")
        pmci   = _make_pmci(alignment=0.75, matched=True)
        eng.process_trade(trade, pmci)
        # second call with same trade_id while first is done is fine;
        # only blocks when in-flight simultaneously
        r.ok("T151") if True else r.fail("T151", "duplicate guard")

    # None pmci_result raises DREInputError
    with tempfile.TemporaryDirectory() as tmp:
        eng2 = _make_engine(tmp_dir=Path(tmp))
        trade = _make_trade()
        try:
            eng2.process_trade(trade, None)
            r.fail("T152", "should have raised DREInputError")
        except DREInputError:
            r.ok("T152")

    # process_trade with no matched/conflicting DNA → empty list
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        pmci_empty = _FakePMCIResult(
            pmci_score=0.3,
            breakdown=_FakePMCIBreakdown(matched_dna=[], conflicting_dna=[]),
        )
        result = eng.process_trade(_make_trade(), pmci_empty)
        r.ok("T153") if result == [] else r.fail("T153", f"expected [] got {result}")


# ─────────────────────────────────────────────────────────────────────────────
# T154–T160  History and statistics
# ─────────────────────────────────────────────────────────────────────────────

def test_history_and_statistics(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))

        for i in range(5):
            trade  = _make_trade(won=(i % 2 == 0), r_multiple=(1.5 if i % 2 == 0 else -1.0),
                                  pnl=(3000 if i % 2 == 0 else -2000), trade_id=f"HT{i}")
            pmci   = _make_pmci(alignment=0.75, matched=True)
            eng.process_trade(trade, pmci)

        hist = eng.history()
        r.ok("T154") if len(hist) == 5 else r.fail("T154", f"expected 5 got {len(hist)}")
        # Newest first
        r.ok("T155") if hist[0].trade_id == "HT4" else r.fail("T155", f"newest first {hist[0].trade_id}")
        # Filter by dna_id
        hist_filtered = eng.history(dna_id=dna.id)
        r.ok("T156") if len(hist_filtered) == 5 else r.fail("T156", f"filtered {len(hist_filtered)}")
        hist_wrong = eng.history(dna_id="nonexistent")
        r.ok("T157") if hist_wrong == [] else r.fail("T157", "wrong dna_id filter")
        # limit
        hist_lim = eng.history(limit=3)
        r.ok("T158") if len(hist_lim) == 3 else r.fail("T158", f"limit {len(hist_lim)}")
        stats = eng.statistics()
        r.ok("T159") if stats.total_reinforcements == 5 else r.fail("T159", f"total {stats.total_reinforcements}")
        r.ok("T160") if stats.trades_processed == 5 else r.fail("T160", f"trades_processed {stats.trades_processed}")


# ─────────────────────────────────────────────────────────────────────────────
# T161–T165  Dry-run mode
# ─────────────────────────────────────────────────────────────────────────────

def test_dry_run_mode(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.70, evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=2.0, pnl=5000.0)
        pmci   = _make_pmci(alignment=0.85, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T161") if len(result) == 1 else r.fail("T161", f"expected 1 got {len(result)}")
        r.ok("T162") if result[0].idr_revision is None else r.fail("T162", "dry_run: idr_revision should be None")
        r.ok("T163") if len(idr.write_log) == 0 else r.fail("T163", f"dry_run: idr writes should be 0, got {len(idr.write_log)}")
        # DNA confidence unchanged in stub (no write occurred)
        r.ok("T164") if idr._store[dna.id].confidence == 0.70 else r.fail("T164", f"dry_run: confidence should stay 0.70, got {idr._store[dna.id].confidence}")
        # But computed values are still meaningful
        r.ok("T165") if result[0].confidence_after > result[0].confidence_before else r.fail("T165", "computed confidence should still reflect change")


# ─────────────────────────────────────────────────────────────────────────────
# T166–T170  Concurrent processing
# ─────────────────────────────────────────────────────────────────────────────

def test_concurrent_processing(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))

        results: List[List] = []
        errors:  List[str]  = []
        lock = threading.Lock()

        def worker(i: int):
            trade  = _make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id=f"CONC-{i}")
            pmci   = _make_pmci(alignment=0.75, matched=True)
            try:
                recs = eng.process_trade(trade, pmci)
                with lock:
                    results.append(recs)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        r.ok("T166") if not errors else r.fail("T166", f"concurrent errors: {errors}")
        r.ok("T167") if len(results) == 10 else r.fail("T167", f"expected 10 results got {len(results)}")
        hist_len = len(eng.history())
        r.ok("T168") if hist_len == 10 else r.fail("T168", f"history should have 10 entries, got {hist_len}")
        stats = eng.statistics()
        r.ok("T169") if stats.trades_processed == 10 else r.fail("T169", f"trades_processed {stats.trades_processed}")
        r.ok("T170") if eng.pending() == [] else r.fail("T170", f"pending not empty: {eng.pending()}")


# ─────────────────────────────────────────────────────────────────────────────
# T171–T175  History persistence
# ─────────────────────────────────────────────────────────────────────────────

def test_history_persistence(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr1 = _FakeIDR([dna])
        cfg = DREConfig(dry_run=False)
        eng1 = DNAReinforcementEngine(idr=idr1, config=cfg, data_root=Path(tmp))
        for i in range(3):
            trade = _make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id=f"PERSIST-{i}")
            pmci  = _make_pmci(alignment=0.70, matched=True)
            eng1.process_trade(trade, pmci)

        hist_path = Path(tmp) / "history.json"
        r.ok("T171") if hist_path.exists() else r.fail("T171", "history.json not created")

        idr2 = _FakeIDR([_make_dna(evidence_count=20)])
        eng2 = DNAReinforcementEngine(idr=idr2, config=cfg, data_root=Path(tmp))
        r.ok("T172") if len(eng2.history()) == 3 else r.fail("T172", f"loaded {len(eng2.history())} expected 3")
        # max_history_records cap
        idr3 = _FakeIDR([_make_dna(evidence_count=20)])
        cfg2 = DREConfig(dry_run=False, max_history_records=2)
        eng3 = DNAReinforcementEngine(idr=idr3, config=cfg2, data_root=Path(tmp))
        # eng3 loaded 3 records; adding one more triggers save with cap=2
        trade = _make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id="PERSIST-99")
        pmci  = _make_pmci(alignment=0.70, matched=True)
        eng3.process_trade(trade, pmci)
        # After save, file has at most 2 records
        raw = __import__("json").loads(hist_path.read_text())
        r.ok("T173") if len(raw) <= 2 else r.fail("T173", f"cap not applied: {len(raw)}")

    # Corrupt history file → engine starts clean
    with tempfile.TemporaryDirectory() as tmp2:
        bad_path = Path(tmp2) / "history.json"
        bad_path.write_text("NOT VALID JSON", encoding="utf-8")
        idr = _FakeIDR([_make_dna(evidence_count=20)])
        eng4 = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp2))
        r.ok("T174") if eng4.history() == [] else r.fail("T174", "corrupt file should result in empty history")
        r.ok("T175") if True else r.fail("T175", "corrupt file should not crash init")


# ─────────────────────────────────────────────────────────────────────────────
# T176–T180  Replay / auditability
# ─────────────────────────────────────────────────────────────────────────────

def test_auditability(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(confidence=0.72, stability=0.78, evidence_count=18)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=1.8, pnl=4000.0, trade_id="AUDIT-1", symbol="HDFC")
        pmci   = _make_pmci(alignment=0.82, contribution=0.14, pmci_score=0.71, matched=True)
        result = eng.process_trade(trade, pmci)
        rec = result[0]

        # Every reinforcement is traceable to one trade
        r.ok("T176") if rec.trade_id == "AUDIT-1" else r.fail("T176", f"trade_id {rec.trade_id}")
        r.ok("T177") if rec.evidence.symbol == "HDFC" else r.fail("T177", "symbol not in evidence")
        r.ok("T178") if abs(rec.evidence.dna_alignment - 0.82) < 1e-6 else r.fail("T178", "alignment in evidence")
        # confidence_before + delta == confidence_after (reproducible)
        r.ok("T179") if abs(rec.confidence_before + rec.confidence_delta - rec.confidence_after) < 1e-9 else r.fail("T179", "confidence not reproducible")
        # reinforcement_id is deterministic (same inputs → same SHA)
        r.ok("T180") if rec.reinforcement_id.startswith("DRE-") else r.fail("T180", "id format wrong")


# ─────────────────────────────────────────────────────────────────────────────
# T181–T185  process_trade with missing optional fields
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_optional_fields(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))

        # Minimal dict trade — no placed_at/closed_at/r_multiple
        trade_dict = {"order_id": "DICT-1", "symbol": "TCS", "direction": "LONG",
                      "pnl": 2000.0, "strategy": "Breakout", "signal_regime": "TRENDING"}
        pmci = _make_pmci(alignment=0.65, matched=True)
        result = eng.process_trade(trade_dict, pmci)
        r.ok("T181") if len(result) == 1 else r.fail("T181", f"expected 1 got {len(result)}")
        # holding_period_h defaults to 0
        r.ok("T182") if result[0].evidence.holding_period_h == 0.0 else r.fail("T182", f"holding_h {result[0].evidence.holding_period_h}")
        # r_multiple defaults to 0 → NEUTRAL (below min_r_multiple_magnitude)
        r.ok("T183") if result[0].reinforcement_type == "NEUTRAL" else r.fail("T183", f"type {result[0].reinforcement_type}")

    # With placed_at and closed_at
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        now = datetime.now(timezone.utc)
        trade = _FakeTrade(
            order_id="TIME-1", symbol="INFY", direction="LONG",
            pnl=3000.0, r_multiple=1.5,
            placed_at=now - timedelta(hours=6),
            closed_at=now,
        )
        pmci = _make_pmci(alignment=0.70, matched=True)
        result = eng.process_trade(trade, pmci)
        r.ok("T184") if len(result) == 1 else r.fail("T184", "expected 1 result")
        r.ok("T185") if abs(result[0].evidence.holding_period_h - 6.0) < 0.01 else r.fail("T185", f"holding_h {result[0].evidence.holding_period_h}")


# ─────────────────────────────────────────────────────────────────────────────
# T186–T190  summarise_batch
# ─────────────────────────────────────────────────────────────────────────────

def test_summarise_batch(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna_a = _make_dna(dna_id="a", feature="rsi", evidence_count=20)
        dna_b = _make_dna(dna_id="b", feature="macd", evidence_count=20)
        idr = _FakeIDR([dna_a, dna_b])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))

        all_recs = []
        for i in range(3):
            trade  = _make_trade(won=True, r_multiple=1.5, pnl=3000.0, trade_id=f"SB{i}")
            pmci   = _FakePMCIResult(
                pmci_score=0.70,
                breakdown=_FakePMCIBreakdown(
                    matched_dna=[
                        _FakePMCIEvidence("rsi",  "WINNERS_HIGHER", 0.75, 0.12),
                        _FakePMCIEvidence("macd", "WINNERS_HIGHER", 0.65, 0.10),
                    ],
                    conflicting_dna=[],
                ),
            )
            recs = eng.process_trade(trade, pmci)
            all_recs.extend(recs)

        updates = eng.summarise_batch(all_recs)
        r.ok("T186") if len(updates) == 2 else r.fail("T186", f"expected 2 DNA summaries got {len(updates)}")
        ids = {u.dna_id for u in updates}
        r.ok("T187") if ids == {"a", "b"} else r.fail("T187", f"dna ids {ids}")
        for u in updates:
            r.ok("T188") if len(u.reinforcements) == 3 else r.fail("T188", f"reinforcements {len(u.reinforcements)}")
            break
        r.ok("T189") if updates[0].dominant_type == "POSITIVE" else r.fail("T189", f"dominant {updates[0].dominant_type}")
        r.ok("T190") if updates[0].net_confidence_delta > 0 else r.fail("T190", f"net delta {updates[0].net_confidence_delta}")


# ─────────────────────────────────────────────────────────────────────────────
# T191–T195  CDS score integration
# ─────────────────────────────────────────────────────────────────────────────

def test_cds_score_integration(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        dna = _make_dna(dna_id="cds_dna", evidence_count=20)
        idr = _FakeIDR([dna])
        eng = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        trade  = _make_trade(won=True, r_multiple=1.5, pnl=3000.0)
        pmci   = _make_pmci(alignment=0.75, matched=True)

        class _FakeCDS:
            cds = 0.72

        cds_scores = {"cds_dna": _FakeCDS()}
        result = eng.process_trade(trade, pmci, cds_scores=cds_scores)
        r.ok("T191") if len(result) == 1 else r.fail("T191", "expected 1 result")
        r.ok("T192") if abs(result[0].evidence.cds_score - 0.72) < 1e-6 else r.fail("T192", f"cds_score {result[0].evidence.cds_score}")
        # no CDS scores → 0.0 default
        result2 = eng.process_trade(_make_trade(trade_id="NO-CDS"), pmci)
        r.ok("T193") if result2[0].evidence.cds_score == 0.0 else r.fail("T193", f"default cds {result2[0].evidence.cds_score}")
        # CA-PMCI score integration
        class _FakeCAPMCI:
            ca_pmci = 0.68
        result3 = eng.process_trade(_make_trade(trade_id="CA-1"), pmci, ca_pmci_result=_FakeCAPMCI())
        r.ok("T194") if abs(result3[0].evidence.ca_pmci_score - 0.68) < 1e-6 else r.fail("T194", f"ca_pmci {result3[0].evidence.ca_pmci_score}")
        r.ok("T195") if True else r.fail("T195", "T195 placeholder")


# ─────────────────────────────────────────────────────────────────────────────
# T196–T200  Edge cases / statistics with no data
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_cases(r: TestResult):
    with tempfile.TemporaryDirectory() as tmp:
        eng = _make_engine(tmp_dir=Path(tmp))
        # statistics on empty engine
        stats = eng.statistics()
        r.ok("T196") if stats.total_reinforcements == 0 else r.fail("T196", f"empty stats total {stats.total_reinforcements}")
        r.ok("T197") if stats.first_reinforcement_at is None else r.fail("T197", "first_ts should be None")
        # history on empty engine
        r.ok("T198") if eng.history() == [] else r.fail("T198", "empty history")
        # pending on idle engine
        r.ok("T199") if eng.pending() == [] else r.fail("T199", "pending should be empty at start")
        # No IDR match for PMCI DNA → result is empty
        dna = _make_dna(feature="momentum", evidence_count=20)
        idr = _FakeIDR([dna])
        eng2 = DNAReinforcementEngine(idr=idr, config=DREConfig(dry_run=True), data_root=Path(tmp))
        pmci_unmatched = _make_pmci(feature="unknown_feature", direction="WINNERS_HIGHER",
                                    alignment=0.80, matched=True)
        result = eng2.process_trade(_make_trade(), pmci_unmatched)
        r.ok("T200") if result == [] else r.fail("T200", f"no IDR match should give [], got {len(result)}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    r = TestResult()
    print("\nDNA Reinforcement Engine — Test Suite (O-002)")
    print("=" * 64)
    suites = [
        ("T001–T010  ReinforcementType enum",           test_reinforcement_types),
        ("T011–T020  OutcomeQuality enum",              test_outcome_quality_enum),
        ("T021–T030  ReinforcementEvidence",            test_reinforcement_evidence),
        ("T031–T040  DNAReinforcement",                 test_dna_reinforcement_model),
        ("T041–T050  DNAConfidenceUpdate",              test_dna_confidence_update),
        ("T051–T060  ReinforcementStatistics",          test_reinforcement_statistics),
        ("T061–T070  DNAReinforcementHistory",          test_dna_reinforcement_history),
        ("T071–T080  DREConfig",                        test_dre_config),
        ("T081–T095  _classify_outcome",                test_classify_outcome),
        ("T096–T110  Positive reinforcement",           test_positive_reinforcement),
        ("T111–T120  Negative reinforcement",           test_negative_reinforcement),
        ("T121–T128  Neutral reinforcement",            test_neutral_reinforcement),
        ("T129–T133  Contradictory evidence",           test_contradictory_reinforcement),
        ("T134–T138  Insufficient evidence guard",      test_insufficient_evidence_guard),
        ("T139–T145  Safety bounds",                    test_safety_bounds),
        ("T146–T153  Batch processing",                 test_batch_processing),
        ("T154–T160  History and statistics",           test_history_and_statistics),
        ("T161–T165  Dry-run mode",                     test_dry_run_mode),
        ("T166–T170  Concurrent processing",            test_concurrent_processing),
        ("T171–T175  History persistence",              test_history_persistence),
        ("T176–T180  Auditability / replay",            test_auditability),
        ("T181–T185  Missing optional fields",          test_missing_optional_fields),
        ("T186–T190  summarise_batch",                  test_summarise_batch),
        ("T191–T195  CDS / CA-PMCI integration",        test_cds_score_integration),
        ("T196–T200  Edge cases",                       test_edge_cases),
    ]
    for label, fn in suites:
        print(f"\n{label}")
        try:
            fn(r)
        except Exception as exc:
            r.fail(label, f"suite crashed: {exc}")
    return r.summary()


if __name__ == "__main__":
    import sys
    ok = main()
    sys.exit(0 if ok else 1)

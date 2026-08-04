"""
test_idr_repository.py — R-013: Institutional DNA Repository.

90-test suite.  Run with:
    .venv\\Scripts\\python.exe test_idr_repository.py

Uses the same minimal test framework as all previous MLS phases.
No pytest dependency.  No network access.  In-memory SQLite for isolation.
"""
from __future__ import annotations

import sys
import sqlite3
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_learning import (
    IDRRepository,
    InstitutionalDNA,
    DNARevision,
    DNAEvidence,
    DNAHistory,
    DNAContext,
    DNARepositoryStatistics,
    IDRError,
    IDRIntegrityError,
    IDRNotFoundError,
    IDRVersionError,
    MLSConfig,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Test framework
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

def _tmp_repo() -> IDRRepository:
    """Return an IDRRepository backed by a fresh temporary file."""
    tmp = tempfile.mktemp(suffix=".db")
    return IDRRepository(db_path=Path(tmp))


def _dna(
    dna_id: str = "DNA-001",
    feature_name: str = "rsi_5d",
    direction: str = "WINNERS_HIGHER",
    category: str = "WINNER",
    lifecycle: str = "DISCOVERED",
    version: int = 1,
    consensus_score: float = 0.65,
    confidence: float = 0.72,
    effect_size: float = 0.58,
    regime_consistency: float = 0.70,
    sector_consistency: float = 0.65,
    temporal_stability: float = 0.60,
    replication_frequency: float = 0.75,
    evidence_count: int = 15,
    regime_counts: Optional[Dict[str, int]] = None,
    last_seen: Optional[str] = "2026-08-01",
    study_id: str = "STUDY-001",
    source: str = "dna_discovery_engine_v1",
    created_at: str = "2026-07-01T09:00:00+00:00",
    updated_at: str = "2026-08-01T09:00:00+00:00",
    is_current: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> InstitutionalDNA:
    return InstitutionalDNA(
        id=dna_id,
        feature_name=feature_name,
        direction=direction,
        category=category,
        lifecycle=lifecycle,
        version=version,
        consensus_score=consensus_score,
        confidence=confidence,
        effect_size=effect_size,
        regime_consistency=regime_consistency,
        sector_consistency=sector_consistency,
        temporal_stability=temporal_stability,
        replication_frequency=replication_frequency,
        evidence_count=evidence_count,
        regime_counts=regime_counts or {"BULL": 8, "BEAR": 4, "RANGE": 3},
        last_seen=last_seen,
        study_id=study_id,
        source=source,
        created_at=created_at,
        updated_at=updated_at,
        is_current=is_current,
        metadata=metadata or {},
    )


def _evidence(
    dna_id: str = "DNA-001",
    dna_version: int = 1,
    study_id: str = "STUDY-001",
    source: str = "discovery",
    sample_size: int = 50,
    effect_size: float = 0.55,
    confidence: float = 0.70,
    regime: str = "BULL",
    sector: str = "TECH",
    observation_date: str = "2026-08-01",
    p_value: Optional[float] = None,
    ci_low: Optional[float] = None,
    ci_high: Optional[float] = None,
) -> DNAEvidence:
    return DNAEvidence(
        dna_id=dna_id,
        dna_version=dna_version,
        study_id=study_id,
        source=source,
        sample_size=sample_size,
        effect_size=effect_size,
        confidence=confidence,
        regime=regime,
        sector=sector,
        observation_date=observation_date,
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
    )


def _history(
    dna_id: str = "DNA-001",
    history_date: str = "2026-08-01",
    confidence: float = 0.72,
    consensus_score: float = 0.65,
    drift: float = 0.05,
    stability: float = 0.80,
    relevance: str = "RELEVANT",
    lifecycle: str = "INSTITUTIONAL",
    version_at_time: int = 1,
) -> DNAHistory:
    return DNAHistory(
        dna_id=dna_id,
        history_date=history_date,
        confidence=confidence,
        consensus_score=consensus_score,
        drift=drift,
        stability=stability,
        relevance=relevance,
        lifecycle=lifecycle,
        version_at_time=version_at_time,
    )


def _context(
    dna_id: str = "DNA-001",
    dna_version: int = 1,
    regime: str = "BULL",
    volatility: float = 0.40,
    breadth: float = 0.65,
    sector: float = 0.70,
    liquidity: float = 0.60,
    institutional: float = 0.55,
    historical_similarity: float = 0.72,
    context_date: str = "2026-08-01",
) -> DNAContext:
    return DNAContext(
        dna_id=dna_id,
        dna_version=dna_version,
        regime=regime,
        volatility=volatility,
        breadth=breadth,
        sector=sector,
        liquidity=liquidity,
        institutional=institutional,
        historical_similarity=historical_similarity,
        context_date=context_date,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T01–T10: Instantiation and config
# ═══════════════════════════════════════════════════════════════════════════════

def T01():
    repo = _tmp_repo()
    ok(isinstance(repo, IDRRepository), "IDRRepository instantiated")
    return "IDRRepository instantiated with temp db"

def T02():
    tmp = tempfile.mktemp(suffix=".db")
    repo = IDRRepository(db_path=Path(tmp))
    ok(repo.db_path == Path(tmp))
    return f"custom db_path accepted"

def T03():
    repo = _tmp_repo()
    ok(repo.db_path.exists(), "db file exists on disk")
    return "schema created on first instantiation"

def T04():
    repo = _tmp_repo()
    ok(repo.SCHEMA_VERSION == 1, f"expected 1, got {repo.SCHEMA_VERSION}")
    return f"SCHEMA_VERSION = {repo.SCHEMA_VERSION}"

def T05():
    repo = _tmp_repo()
    try:
        repo.get("DOES-NOT-EXIST")
        ok(False, "should have raised IDRNotFoundError")
    except IDRNotFoundError:
        pass
    return "IDRNotFoundError raised for unknown DNA"

def T06():
    repo = _tmp_repo()
    repo.save(_dna())
    try:
        repo.get_version("DNA-001", 999)
        ok(False, "should have raised IDRVersionError")
    except IDRVersionError:
        pass
    return "IDRVersionError raised for unknown version"

def T07():
    ok(issubclass(IDRNotFoundError, IDRError))
    ok(issubclass(IDRVersionError, IDRError))
    ok(issubclass(IDRIntegrityError, IDRError))
    return "all IDR exceptions inherit IDRError"

def T08():
    ok(issubclass(IDRNotFoundError, IDRError))
    return "IDRNotFoundError is IDRError"

def T09():
    ok(issubclass(IDRVersionError, IDRError))
    return "IDRVersionError is IDRError"

def T10():
    cfg = MLSConfig()
    ok(hasattr(cfg, "idr_schema_version"))
    ok(hasattr(cfg, "idr_max_evidence_per_dna"))
    ok(hasattr(cfg, "idr_wal_mode"))
    ok(cfg.idr_schema_version == 1)
    ok(cfg.idr_max_evidence_per_dna == 500)
    return "MLSConfig IDR fields present with defaults"


# ═══════════════════════════════════════════════════════════════════════════════
# T11–T20: save() and InstitutionalDNA models
# ═══════════════════════════════════════════════════════════════════════════════

def T11():
    repo = _tmp_repo()
    rev = repo.save(_dna())
    ok(isinstance(rev, DNARevision))
    return "save() returns DNARevision"

def T12():
    repo = _tmp_repo()
    rev = repo.save(_dna())
    ok(rev.operation == "CREATED", f"got {rev.operation}")
    return "first save produces operation=CREATED"

def T13():
    repo = _tmp_repo()
    rev = repo.save(_dna())
    ok(rev.version == 1, f"got {rev.version}")
    return "first save produces version=1"

def T14():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="DNA-XYZ"))
    d = repo.get("DNA-XYZ")
    ok(d.id == "DNA-XYZ")
    return "InstitutionalDNA.id preserved"

def T15():
    repo = _tmp_repo()
    repo.save(_dna())
    d = repo.get("DNA-001")
    ok(d.version == 1)
    return "InstitutionalDNA.version == 1 after first save"

def T16():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="DISCOVERED"))
    d = repo.get("DNA-001")
    ok(d.lifecycle == "DISCOVERED")
    return "lifecycle=DISCOVERED preserved"

def T17():
    d = _dna()
    d2 = InstitutionalDNA.from_dict(d.to_dict())
    ok(d2.id == d.id)
    ok(d2.confidence == d.confidence)
    ok(d2.regime_counts == d.regime_counts)
    ok(d2.metadata == d.metadata)
    return "InstitutionalDNA.to_dict() / from_dict() round-trip"

def T18():
    d = _dna(metadata={"key": "value", "n": 42})
    d2 = InstitutionalDNA.from_dict(d.to_dict())
    ok(d2.metadata["key"] == "value")
    ok(d2.metadata["n"] == 42)
    return "metadata preserved in round-trip"

def T19():
    repo = _tmp_repo()
    repo.save(_dna(confidence=0.85))
    d = repo.get("DNA-001")
    ok(abs(d.confidence - 0.85) < 1e-9)
    return "save() persists to DB and get() retrieves it"

def T20():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.save(_dna(confidence=0.90))
    d = repo.get("DNA-001")
    ok(d.version == 2, f"expected version=2, got {d.version}")
    return "duplicate save creates version 2 (no overwrite)"


# ═══════════════════════════════════════════════════════════════════════════════
# T21–T30: Versioning
# ═══════════════════════════════════════════════════════════════════════════════

def T21():
    repo = _tmp_repo()
    repo.save(_dna())
    rev2 = repo.save(_dna(confidence=0.88))
    ok(rev2.version == 2)
    return "second save creates version=2"

def T22():
    repo = _tmp_repo()
    repo.save(_dna(confidence=0.70))
    repo.save(_dna(confidence=0.90))
    d = repo.get("DNA-001")
    ok(abs(d.confidence - 0.90) < 1e-9, f"get() should return latest")
    return "get() returns latest version"

def T23():
    repo = _tmp_repo()
    repo.save(_dna(confidence=0.70))
    repo.save(_dna(confidence=0.90))
    v1 = repo.get_version("DNA-001", 1)
    ok(abs(v1.confidence - 0.70) < 1e-9)
    return "get_version(1) returns version 1"

def T24():
    repo = _tmp_repo()
    repo.save(_dna(confidence=0.70))
    repo.save(_dna(confidence=0.90))
    v2 = repo.get_version("DNA-001", 2)
    ok(abs(v2.confidence - 0.90) < 1e-9)
    return "get_version(2) returns version 2"

def T25():
    repo = _tmp_repo()
    repo.save(_dna())
    try:
        repo.get_version("DNA-001", 999)
        ok(False, "expected IDRVersionError")
    except IDRVersionError:
        pass
    return "IDRVersionError raised for missing version"

def T26():
    repo = _tmp_repo()
    rev = repo.save(_dna())
    ok(rev.previous_version is None)
    return "DNARevision.previous_version is None for first version"

def T27():
    repo = _tmp_repo()
    repo.save(_dna())
    rev2 = repo.save(_dna())
    ok(rev2.previous_version == 1)
    return "DNARevision.previous_version == 1 for second version"

def T28():
    repo = _tmp_repo()
    repo.save(_dna(confidence=0.70))
    repo.save(_dna(confidence=0.90))
    v1 = repo.get_version("DNA-001", 1)
    ok(abs(v1.confidence - 0.70) < 1e-9, "v1 must remain unchanged")
    return "version 1 unchanged after version 2 is saved"

def T29():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.save(_dna())
    v1 = repo.get_version("DNA-001", 1)
    v2 = repo.get_version("DNA-001", 2)
    ok(not v1.is_current, "v1 should not be current")
    ok(v2.is_current, "v2 should be current")
    return "is_current flag: only latest version is True"

def T30():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A"))
    repo.save(_dna(dna_id="B"))
    repo.save(_dna(dna_id="A"))   # second version of A
    active = repo.list_active()
    ids = [d.id for d in active]
    ok(ids.count("A") == 1, "A should appear once")
    ok(ids.count("B") == 1, "B should appear once")
    return "list_active() returns only latest versions"


# ═══════════════════════════════════════════════════════════════════════════════
# T31–T40: update() and lifecycle transitions
# ═══════════════════════════════════════════════════════════════════════════════

def T31():
    repo = _tmp_repo()
    repo.save(_dna())
    rev = repo.update("DNA-001", {"confidence": 0.95})
    ok(rev.version == 2)
    return "update() creates new version"

def T32():
    repo = _tmp_repo()
    repo.save(_dna(confidence=0.70, effect_size=0.50))
    repo.update("DNA-001", {"confidence": 0.95})
    d = repo.get("DNA-001")
    ok(abs(d.confidence - 0.95) < 1e-9, "confidence should be updated")
    ok(abs(d.effect_size - 0.50) < 1e-9, "effect_size should be unchanged")
    return "update() changes only specified fields"

def T33():
    repo = _tmp_repo()
    repo.save(_dna(feature_name="macd_cross", study_id="S-42"))
    repo.update("DNA-001", {"confidence": 0.88})
    d = repo.get("DNA-001")
    ok(d.feature_name == "macd_cross", "feature_name preserved")
    ok(d.study_id == "S-42", "study_id preserved")
    return "update() preserves unchanged fields"

def T34():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="DISCOVERED"))
    repo.update("DNA-001", {"lifecycle": "REPLICATED"})
    d = repo.get("DNA-001")
    ok(d.lifecycle == "REPLICATED")
    return "lifecycle: DISCOVERED -> REPLICATED"

def T35():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="REPLICATED"))
    repo.update("DNA-001", {"lifecycle": "VERIFIED"})
    d = repo.get("DNA-001")
    ok(d.lifecycle == "VERIFIED")
    return "lifecycle: REPLICATED -> VERIFIED"

def T36():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="VERIFIED"))
    repo.update("DNA-001", {"lifecycle": "INSTITUTIONAL"})
    d = repo.get("DNA-001")
    ok(d.lifecycle == "INSTITUTIONAL")
    return "lifecycle: VERIFIED -> INSTITUTIONAL"

def T37():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="INSTITUTIONAL"))
    repo.update("DNA-001", {"lifecycle": "WEAKENING"})
    d = repo.get("DNA-001")
    ok(d.lifecycle == "WEAKENING")
    return "lifecycle: INSTITUTIONAL -> WEAKENING"

def T38():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="WEAKENING"))
    repo.update("DNA-001", {"lifecycle": "DRIFTING"})
    d = repo.get("DNA-001")
    ok(d.lifecycle == "DRIFTING")
    return "lifecycle: WEAKENING -> DRIFTING"

def T39():
    repo = _tmp_repo()
    repo.save(_dna(lifecycle="INSTITUTIONAL"))
    rev = repo.retire("DNA-001", reason="no longer active in current regime")
    d = repo.get("DNA-001")
    ok(d.lifecycle == "RETIRED")
    ok(rev.operation == "RETIRED")
    return "lifecycle: any -> RETIRED via retire()"

def T40():
    repo = _tmp_repo()
    repo.save(_dna())
    rev = repo.retire("DNA-001")
    ok(rev.operation == "RETIRED")
    return "retire() produces DNARevision with operation=RETIRED"


# ═══════════════════════════════════════════════════════════════════════════════
# T41–T50: history()
# ═══════════════════════════════════════════════════════════════════════════════

def T41():
    repo = _tmp_repo()
    repo.save(_dna())
    h = repo.history("DNA-001")
    ok(h == [], f"expected [], got {h}")
    return "history() returns empty list for new DNA"

def T42():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history())
    h = repo.history("DNA-001")
    ok(len(h) == 1)
    return "add_history() adds a history record"

def T43():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(history_date="2026-07-01"))
    repo.add_history("DNA-001", _history(history_date="2026-07-02"))
    repo.add_history("DNA-001", _history(history_date="2026-07-03"))
    h = repo.history("DNA-001")
    ok(len(h) == 3)
    return "history() returns all history records"

def T44():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(history_date="2026-07-10"))
    repo.add_history("DNA-001", _history(history_date="2026-07-01"))
    repo.add_history("DNA-001", _history(history_date="2026-07-05"))
    h = repo.history("DNA-001")
    dates = [x.history_date for x in h]
    ok(dates == sorted(dates), f"expected ascending, got {dates}")
    return "history() ordered ascending by date"

def T45():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(dna_id="DNA-001"))
    h = repo.history("DNA-001")
    ok(h[0].dna_id == "DNA-001")
    return "DNAHistory.dna_id matches"

def T46():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(confidence=0.88))
    h = repo.history("DNA-001")
    ok(abs(h[0].confidence - 0.88) < 1e-9)
    return "DNAHistory.confidence stored correctly"

def T47():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(consensus_score=0.72))
    h = repo.history("DNA-001")
    ok(abs(h[0].consensus_score - 0.72) < 1e-9)
    return "DNAHistory.consensus_score stored correctly"

def T48():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(drift=0.18))
    h = repo.history("DNA-001")
    ok(abs(h[0].drift - 0.18) < 1e-9)
    return "DNAHistory.drift stored correctly"

def T49():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_history("DNA-001", _history(stability=0.92))
    h = repo.history("DNA-001")
    ok(abs(h[0].stability - 0.92) < 1e-9)
    return "DNAHistory.stability stored correctly"

def T50():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.update("DNA-001", {"confidence": 0.99})   # version 2
    repo.add_history("DNA-001", _history(version_at_time=2))
    h = repo.history("DNA-001")
    ok(h[0].version_at_time == 2)
    return "DNAHistory.version_at_time matches version at addition"


# ═══════════════════════════════════════════════════════════════════════════════
# T51–T60: evidence()
# ═══════════════════════════════════════════════════════════════════════════════

def T51():
    repo = _tmp_repo()
    repo.save(_dna())
    ev = repo.evidence("DNA-001")
    ok(ev == [])
    return "evidence() returns empty list for new DNA"

def T52():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_evidence("DNA-001", _evidence())
    ev = repo.evidence("DNA-001")
    ok(len(ev) == 1)
    return "add_evidence() adds a record"

def T53():
    repo = _tmp_repo()
    repo.save(_dna())
    for i in range(3):
        repo.add_evidence("DNA-001", _evidence(observation_date=f"2026-07-{i+1:02d}"))
    ev = repo.evidence("DNA-001")
    ok(len(ev) == 3)
    return "evidence() returns all evidence records"

def T54():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="DNA-ABC"))
    repo.add_evidence("DNA-ABC", _evidence(dna_id="DNA-ABC"))
    ev = repo.evidence("DNA-ABC")
    ok(ev[0].dna_id == "DNA-ABC")
    return "DNAEvidence.dna_id matches"

def T55():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_evidence("DNA-001", _evidence(study_id="STUDY-XYZ"))
    ev = repo.evidence("DNA-001")
    ok(ev[0].study_id == "STUDY-XYZ")
    return "DNAEvidence.study_id matches"

def T56():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_evidence("DNA-001", _evidence(sample_size=150))
    ev = repo.evidence("DNA-001")
    ok(ev[0].sample_size == 150)
    return "DNAEvidence.sample_size matches"

def T57():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_evidence("DNA-001", _evidence(confidence=0.88))
    ev = repo.evidence("DNA-001")
    ok(abs(ev[0].confidence - 0.88) < 1e-9)
    return "DNAEvidence.confidence matches"

def T58():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_evidence("DNA-001", _evidence(effect_size=0.76))
    ev = repo.evidence("DNA-001")
    ok(abs(ev[0].effect_size - 0.76) < 1e-9)
    return "DNAEvidence.effect_size matches"

def T59():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_evidence("DNA-001", _evidence(regime="VOLATILE"))
    ev = repo.evidence("DNA-001")
    ok(ev[0].regime == "VOLATILE")
    return "DNAEvidence.regime matches"

def T60():
    ev = _evidence(p_value=0.04, ci_low=0.30, ci_high=0.65)
    ev2 = DNAEvidence.from_dict(ev.to_dict())
    ok(abs(ev2.p_value - 0.04) < 1e-9)
    ok(abs(ev2.ci_low - 0.30) < 1e-9)
    ok(abs(ev2.ci_high - 0.65) < 1e-9)
    ok(ev2.dna_id == ev.dna_id)
    return "DNAEvidence.to_dict() / from_dict() round-trip"


# ═══════════════════════════════════════════════════════════════════════════════
# T61–T67: add_context() and search()
# ═══════════════════════════════════════════════════════════════════════════════

def T61():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.add_context("DNA-001", _context(regime="BULL"))
    ctxs = repo.contexts("DNA-001")
    ok(len(ctxs) == 1)
    ok(ctxs[0].regime == "BULL")
    return "add_context() stores context snapshot"

def T62():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A"))
    repo.save(_dna(dna_id="B"))
    repo.save(_dna(dna_id="C"))
    results = repo.search()
    ids = {d.id for d in results}
    ok({"A", "B", "C"}.issubset(ids))
    return "search() with no filters returns all active DNA"

def T63():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A", feature_name="rsi_5d"))
    repo.save(_dna(dna_id="B", feature_name="macd_cross"))
    results = repo.search(feature_name="rsi_5d")
    ok(len(results) == 1)
    ok(results[0].id == "A")
    return "search(feature_name=) filters correctly"

def T64():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="W1", category="WINNER"))
    repo.save(_dna(dna_id="L1", category="LOSER"))
    results = repo.search(category="WINNER")
    ok(all(d.category == "WINNER" for d in results))
    ok(len(results) == 1)
    return "search(category=) filters correctly"

def T65():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A", lifecycle="INSTITUTIONAL"))
    repo.save(_dna(dna_id="B", lifecycle="DISCOVERED"))
    results = repo.search(lifecycle="INSTITUTIONAL")
    ok(len(results) == 1)
    ok(results[0].id == "A")
    return "search(lifecycle=) filters correctly"

def T66():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="HI", confidence=0.90))
    repo.save(_dna(dna_id="LO", confidence=0.40))
    results = repo.search(min_confidence=0.80)
    ids = {d.id for d in results}
    ok("HI" in ids)
    ok("LO" not in ids)
    return "search(min_confidence=) filters correctly"

def T67():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A", feature_name="rsi_5d", category="WINNER", confidence=0.85))
    repo.save(_dna(dna_id="B", feature_name="rsi_5d", category="LOSER",  confidence=0.85))
    repo.save(_dna(dna_id="C", feature_name="rsi_5d", category="WINNER", confidence=0.50))
    results = repo.search(feature_name="rsi_5d", category="WINNER", min_confidence=0.80)
    ok(len(results) == 1)
    ok(results[0].id == "A")
    return "search() with combined filters"


# ═══════════════════════════════════════════════════════════════════════════════
# T68–T73: list_active, list_retired, statistics
# ═══════════════════════════════════════════════════════════════════════════════

def T68():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A", lifecycle="INSTITUTIONAL"))
    repo.save(_dna(dna_id="B", lifecycle="DISCOVERED"))
    repo.save(_dna(dna_id="C", lifecycle="INSTITUTIONAL"))
    repo.retire("C")
    active = repo.list_active()
    ids = {d.id for d in active}
    ok("A" in ids and "B" in ids, "active should include A and B")
    ok("C" not in ids, "retired C should be excluded")
    return "list_active() excludes RETIRED DNA"

def T69():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="A", lifecycle="INSTITUTIONAL"))
    repo.save(_dna(dna_id="B", lifecycle="DISCOVERED"))
    repo.retire("A")
    retired = repo.list_retired()
    ids = {d.id for d in retired}
    ok("A" in ids)
    ok("B" not in ids)
    return "list_retired() returns only RETIRED DNA"

def T70():
    ctx = _context()
    ctx2 = DNAContext.from_dict(ctx.to_dict())
    ok(ctx2.dna_id == ctx.dna_id)
    ok(abs(ctx2.volatility - ctx.volatility) < 1e-9)
    ok(abs(ctx2.breadth - ctx.breadth) < 1e-9)
    ok(ctx2.regime == ctx.regime)
    return "DNAContext.to_dict() / from_dict() round-trip"

def T71():
    repo = _tmp_repo()
    stats = repo.statistics()
    ok(isinstance(stats, DNARepositoryStatistics))
    return "statistics() returns DNARepositoryStatistics"

def T72():
    repo = _tmp_repo()
    for i in range(5):
        repo.save(_dna(dna_id=f"DNA-{i:03d}"))
    stats = repo.statistics()
    ok(stats.total_dna == 5, f"expected 5, got {stats.total_dna}")
    return "statistics().total_dna matches saved count"

def T73():
    repo = _tmp_repo()
    for i in range(4):
        repo.save(_dna(dna_id=f"DNA-{i:03d}"))
    repo.retire("DNA-000")
    stats = repo.statistics()
    ok(stats.active_dna == 3, f"active {stats.active_dna}")
    ok(stats.retired_dna == 1, f"retired {stats.retired_dna}")
    return "statistics() active/retired counts correct"


# ═══════════════════════════════════════════════════════════════════════════════
# T74–T80: thread safety and concurrency
# ═══════════════════════════════════════════════════════════════════════════════

def T74():
    repo = _tmp_repo()
    errors = []
    def _save(i):
        try:
            repo.save(_dna(dna_id=f"THREAD-{i:03d}"))
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=_save, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    ok(len(errors) == 0, f"errors: {errors}")
    stats = repo.statistics()
    ok(stats.total_dna == 5, f"expected 5, got {stats.total_dna}")
    return "concurrent save() from 5 threads — all succeed"

def T75():
    repo = _tmp_repo()
    repo.save(_dna())
    errors = []
    def _update(i):
        try:
            repo.update("DNA-001", {"evidence_count": i})
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=_update, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    ok(len(errors) == 0, f"errors: {errors}")
    d = repo.get("DNA-001")
    ok(d.version == 6, f"5 updates -> version 6, got {d.version}")
    return "5 concurrent updates produce version=6 (no collision)"

def T76():
    repo = _tmp_repo()
    for i in range(10):
        repo.save(_dna(dna_id=f"DNA-{i:03d}"))
    errors = []
    results_box = []
    def _read(i):
        try:
            d = repo.get(f"DNA-{i:03d}")
            results_box.append(d.id)
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=_read, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    ok(len(errors) == 0, f"errors: {errors}")
    ok(len(results_box) == 10)
    return "10 concurrent reads succeed"

def T77():
    repo = _tmp_repo()
    repo.save(_dna())
    errors = []
    def _write():
        for _ in range(5):
            try:
                repo.update("DNA-001", {"confidence": 0.88})
            except Exception as e:
                errors.append(e)
    def _read():
        for _ in range(5):
            try:
                repo.get("DNA-001")
            except Exception as e:
                errors.append(e)
    threads = ([threading.Thread(target=_write) for _ in range(3)]
             + [threading.Thread(target=_read)  for _ in range(5)])
    for t in threads: t.start()
    for t in threads: t.join()
    ok(len(errors) == 0, f"errors: {errors}")
    return "concurrent reads and writes succeed"

def T78():
    repo = _tmp_repo()
    try:
        with repo._write_lock:
            conn = repo._conn()
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("SELECT 1 FROM dna")
            conn.rollback()
            conn.close()
    except Exception as e:
        ok(False, f"rollback failed: {e}")
    ok(repo.statistics().total_dna == 0)
    return "rollback leaves DB unchanged"

def T79():
    repo = _tmp_repo()
    ok(repo.verify_integrity())
    return "integrity check passes on clean DB"

def T80():
    repo = _tmp_repo()
    for i in range(5):
        repo.save(_dna(dna_id=f"D{i}"))
    stats = repo.statistics()
    ok(stats.db_size_bytes > 0, f"expected > 0, got {stats.db_size_bytes}")
    return f"statistics().db_size_bytes > 0 ({stats.db_size_bytes}B)"


# ═══════════════════════════════════════════════════════════════════════════════
# T81–T86: backup and integrity
# ═══════════════════════════════════════════════════════════════════════════════

def T81():
    repo = _tmp_repo()
    repo.save(_dna())
    backup_path = Path(tempfile.mktemp(suffix="_backup.db"))
    result = repo.backup(backup_path)
    ok(result == backup_path)
    ok(backup_path.exists())
    return "backup() creates backup file at specified path"

def T82():
    repo = _tmp_repo()
    repo.save(_dna())
    backup_path = repo.backup()   # default auto-named path
    ok(backup_path.exists())
    ok(backup_path.name.startswith("institutional_dna_backup_"))
    return "backup() with default path creates auto-named file"

def T83():
    repo = _tmp_repo()
    repo.save(_dna(dna_id="ORIG-001", confidence=0.78))
    backup_path = Path(tempfile.mktemp(suffix=".db"))
    repo.backup(backup_path)
    # Open backup and verify contents
    conn = sqlite3.connect(str(backup_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM dna WHERE id='ORIG-001' AND is_current=1").fetchone()
    conn.close()
    ok(row is not None, "backup contains DNA record")
    ok(abs(float(row["confidence"]) - 0.78) < 1e-9)
    return "backup is a valid readable SQLite database"

def T84():
    repo = _tmp_repo()
    stats = repo.statistics()
    ok(stats.schema_version == 1)
    return f"schema_version == 1 in statistics()"

def T85():
    repo = _tmp_repo()
    ok(repo.verify_integrity(), "verify_integrity() should return True")
    return "verify_integrity() returns True on healthy DB"

def T86():
    repo = _tmp_repo()
    conn = repo._conn()
    try:
        sv = conn.execute("SELECT * FROM schema_version").fetchall()
        ok(len(sv) == 1)
        ok(sv[0]["version"] == 1)
    finally:
        conn.close()
    return "schema_version table has one entry with version=1"


# ═══════════════════════════════════════════════════════════════════════════════
# T87–T90: audit trail
# ═══════════════════════════════════════════════════════════════════════════════

def T87():
    repo = _tmp_repo()
    repo.save(_dna(), study_id="STUDY-001", operator="researcher_a")
    log = repo.audit_log("DNA-001")
    ok(len(log) == 1)
    ok(log[0]["operation"] == "CREATED")
    return "save() creates audit_log entry with operation=CREATED"

def T88():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.update("DNA-001", {"confidence": 0.90}, reason="replication confirmed", study_id="S2")
    log = repo.audit_log("DNA-001")
    ok(len(log) == 2)
    ok(log[1]["operation"] == "UPDATED")
    ok(log[1]["reason"] == "replication confirmed")
    return "update() creates audit_log entry with operation=UPDATED"

def T89():
    repo = _tmp_repo()
    repo.save(_dna())
    repo.retire("DNA-001", reason="no longer active", operator="risk_manager")
    log = repo.audit_log("DNA-001")
    entry = log[-1]
    ok(entry["operation"] == "RETIRED")
    ok(entry["reason"] == "no longer active")
    ok(entry["operator"] == "risk_manager")
    return "retire() creates audit_log entry with operation=RETIRED"

def T90():
    repo = _tmp_repo()
    repo.save(_dna(), study_id="S1", operator="analyst")
    repo.update("DNA-001", {"confidence": 0.80}, reason="step1", study_id="S2")
    repo.update("DNA-001", {"confidence": 0.85}, reason="step2", study_id="S3")
    repo.retire("DNA-001", reason="end-of-life")
    log = repo.audit_log("DNA-001")
    ok(len(log) == 4, f"expected 4 entries, got {len(log)}")
    ops = [e["operation"] for e in log]
    ok(ops == ["CREATED", "UPDATED", "UPDATED", "RETIRED"])
    ok(log[0]["study_id"] == "S1")
    ok(log[0]["operator"] == "analyst")
    return "full audit trail: save->update->update->retire produces 4 entries"


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    runner = TestRunner()

    tests = [
        ("T01 IDRRepository instantiates with temp path",              T01),
        ("T02 custom db_path accepted",                                 T02),
        ("T03 schema created on first instantiation",                  T03),
        ("T04 SCHEMA_VERSION == 1",                                     T04),
        ("T05 IDRNotFoundError for unknown DNA",                        T05),
        ("T06 IDRVersionError for unknown version",                     T06),
        ("T07 all exceptions inherit IDRError",                         T07),
        ("T08 IDRNotFoundError is IDRError",                            T08),
        ("T09 IDRVersionError is IDRError",                             T09),
        ("T10 MLSConfig IDR fields present",                            T10),
        ("T11 save() returns DNARevision",                              T11),
        ("T12 first save operation=CREATED",                            T12),
        ("T13 first save version=1",                                    T13),
        ("T14 InstitutionalDNA.id preserved",                          T14),
        ("T15 InstitutionalDNA.version==1 after first save",           T15),
        ("T16 lifecycle=DISCOVERED preserved",                          T16),
        ("T17 to_dict/from_dict round-trip",                           T17),
        ("T18 metadata preserved in round-trip",                        T18),
        ("T19 save() persists and get() retrieves",                    T19),
        ("T20 duplicate save creates version 2",                        T20),
        ("T21 second save creates version=2",                           T21),
        ("T22 get() returns latest version",                            T22),
        ("T23 get_version(1) returns v1",                               T23),
        ("T24 get_version(2) returns v2",                               T24),
        ("T25 IDRVersionError for missing version",                     T25),
        ("T26 first version previous_version is None",                 T26),
        ("T27 second version previous_version==1",                     T27),
        ("T28 v1 unchanged after v2 saved",                             T28),
        ("T29 is_current flag correct",                                 T29),
        ("T30 list_active() returns only latest versions",             T30),
        ("T31 update() creates new version",                            T31),
        ("T32 update() changes specified fields only",                 T32),
        ("T33 update() preserves unchanged fields",                    T33),
        ("T34 lifecycle DISCOVERED -> REPLICATED",                       T34),
        ("T35 lifecycle REPLICATED -> VERIFIED",                         T35),
        ("T36 lifecycle VERIFIED -> INSTITUTIONAL",                      T36),
        ("T37 lifecycle INSTITUTIONAL -> WEAKENING",                     T37),
        ("T38 lifecycle WEAKENING -> DRIFTING",                         T38),
        ("T39 lifecycle any -> RETIRED",                                 T39),
        ("T40 retire() operation=RETIRED",                              T40),
        ("T41 history() empty for new DNA",                             T41),
        ("T42 add_history() adds record",                               T42),
        ("T43 history() returns all records",                           T43),
        ("T44 history() ordered ascending",                             T44),
        ("T45 DNAHistory.dna_id matches",                               T45),
        ("T46 DNAHistory.confidence stored",                            T46),
        ("T47 DNAHistory.consensus_score stored",                       T47),
        ("T48 DNAHistory.drift stored",                                 T48),
        ("T49 DNAHistory.stability stored",                             T49),
        ("T50 DNAHistory.version_at_time matches",                     T50),
        ("T51 evidence() empty for new DNA",                            T51),
        ("T52 add_evidence() adds record",                              T52),
        ("T53 evidence() returns all records",                          T53),
        ("T54 DNAEvidence.dna_id matches",                              T54),
        ("T55 DNAEvidence.study_id matches",                            T55),
        ("T56 DNAEvidence.sample_size matches",                         T56),
        ("T57 DNAEvidence.confidence matches",                          T57),
        ("T58 DNAEvidence.effect_size matches",                         T58),
        ("T59 DNAEvidence.regime matches",                              T59),
        ("T60 DNAEvidence.to_dict/from_dict round-trip",               T60),
        ("T61 add_context() stores context snapshot",                  T61),
        ("T62 search() with no filters returns all active",            T62),
        ("T63 search(feature_name=) filters correctly",                T63),
        ("T64 search(category=) filters correctly",                    T64),
        ("T65 search(lifecycle=) filters correctly",                   T65),
        ("T66 search(min_confidence=) filters correctly",              T66),
        ("T67 search() with combined filters",                         T67),
        ("T68 list_active() excludes RETIRED",                         T68),
        ("T69 list_retired() returns only RETIRED",                    T69),
        ("T70 DNAContext.to_dict/from_dict round-trip",                T70),
        ("T71 statistics() returns DNARepositoryStatistics",           T71),
        ("T72 statistics().total_dna matches count",                   T72),
        ("T73 statistics() active/retired counts",                     T73),
        ("T74 concurrent save() from 5 threads all succeed",           T74),
        ("T75 5 concurrent updates -> version=6 no collision",         T75),
        ("T76 10 concurrent reads succeed",                             T76),
        ("T77 concurrent reads+writes succeed",                        T77),
        ("T78 rollback leaves DB unchanged",                            T78),
        ("T79 integrity check passes on clean DB",                     T79),
        ("T80 statistics().db_size_bytes > 0",                         T80),
        ("T81 backup() creates file at specified path",                T81),
        ("T82 backup() auto-named default path",                       T82),
        ("T83 backup is valid readable SQLite DB",                     T83),
        ("T84 schema_version == 1 in statistics",                      T84),
        ("T85 verify_integrity() returns True",                        T85),
        ("T86 schema_version table has version=1 entry",               T86),
        ("T87 save() creates audit_log CREATED entry",                 T87),
        ("T88 update() creates audit_log UPDATED entry",               T88),
        ("T89 retire() creates audit_log RETIRED entry",               T89),
        ("T90 full audit trail 4 entries",                             T90),
    ]

    for name, fn in tests:
        runner.run(name, fn)

    sys.exit(runner.report())

"""
growth_validator/gva_collector.py
===================================
GVA-001 — Data Collector

READ-ONLY.  Never writes to any knowledge store.

Loads all evidence from JSON files, SQLite databases, and report directories.
Provides a single `collect_all()` entry point that returns a `GVAEvidence`
dataclass containing every piece of data the metrics engine needs.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .gva_config import (
    DATA, FILE_HYPOTHESIS_REG, FILE_DISCOVERED_EDGES, FILE_EDE_FEATURES,
    FILE_STRATEGY_PERF, FILE_REPLAY_SUMMARY, FILE_PAPER_DAILY, FILE_RE001A,
    STUDY_FILES, DB_IKN, DB_DNA, DB_CONTROL,
)

log = logging.getLogger(__name__)


def _js(path: Path, default: Any = None) -> Any:
    """Safe JSON load — returns default on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        log.debug("gva_collector: cannot read %s: %s", path.name, e)
        return default


def _db(path: Path) -> Optional[sqlite3.Connection]:
    """Open a read-only SQLite connection. Returns None if db missing."""
    if not path.exists():
        return None
    try:
        # open in read-only URI mode so we never accidentally write
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        # fallback: normal open
        try:
            conn = sqlite3.connect(str(path), timeout=5)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            log.warning("gva_collector: cannot open %s: %s", path.name, e)
            return None


# ── Evidence container ────────────────────────────────────────────────────────

@dataclass
class StudyRecord:
    """One completed research study."""
    study_id:     str
    title:        str
    executed_at:  str
    date_range:   Dict
    n_obs:        int
    features_before: int = 0
    features_after:  int = 0
    edges_before:    int = 0
    edges_after:     int = 0
    winner_dna_n:    int = 0
    loser_dna_n:     int = 0
    hypothesis_id:   Optional[str] = None
    validation:      Dict = field(default_factory=dict)
    extra:           Dict = field(default_factory=dict)


@dataclass
class HypothesisStats:
    total:     int = 0
    confirmed: int = 0
    rejected:  int = 0
    partial:   int = 0
    proposed:  int = 0
    by_status: Dict = field(default_factory=dict)


@dataclass
class EdgeStats:
    total:     int = 0
    active:    int = 0
    candidate: int = 0
    decaying:  int = 0
    retired:   int = 0
    active_edges: List[Dict] = field(default_factory=list)


@dataclass
class DNAStats:
    total:         int = 0
    winner:        int = 0
    loser:         int = 0
    edge_patterns: int = 0
    institutional: int = 0
    buy:           int = 0
    short:         int = 0
    evidence_records: int = 0
    created_ops:   int = 0
    updated_ops:   int = 0
    by_study:      Dict = field(default_factory=dict)


@dataclass
class IKNStats:
    total_nodes:    int = 0
    total_rels:     int = 0
    by_node_type:   Dict = field(default_factory=dict)
    by_rel_type:    Dict = field(default_factory=dict)


@dataclass
class PlatformStats:
    total_cycles:      int = 0
    cycle_errors:      int = 0
    regime_dist:       Dict = field(default_factory=dict)
    total_decisions:   int = 0
    approved:          int = 0
    rejected:          int = 0
    avg_confidence:    float = 0.0


@dataclass
class ReplayStats:
    exists:          bool = False
    days_replayed:   int = 0
    date_range:      str = ""
    win_rate:        float = 0.0
    avg_r:           float = 0.0
    profit_factor:   float = 0.0
    max_drawdown:    float = 0.0
    total_pnl:       float = 0.0
    net_pnl:         float = 0.0
    total_signals:   int = 0
    trades_executed: int = 0


@dataclass
class GVAEvidence:
    """Complete evidence bundle for GVA-001 metrics computation."""
    collected_at:      str = ""
    studies:           List[StudyRecord] = field(default_factory=list)
    hypothesis:        HypothesisStats = field(default_factory=HypothesisStats)
    edges:             EdgeStats = field(default_factory=EdgeStats)
    dna:               DNAStats = field(default_factory=DNAStats)
    ikn:               IKNStats = field(default_factory=IKNStats)
    platform:          PlatformStats = field(default_factory=PlatformStats)
    replay:            ReplayStats = field(default_factory=ReplayStats)
    feature_count:     int = 0
    feature_baseline:  int = 0   # features at start of Study 002
    labeled_features:  int = 0
    strategy_count:    int = 0
    strategy_perf:     Dict = field(default_factory=dict)
    cum_pnl:           float = 0.0
    cum_return_pct:    float = 0.0
    closed_trades:     int = 0
    open_trades:       int = 0


# ── Collector ────────────────────────────────────────────────────────────────

def _collect_studies() -> List[StudyRecord]:
    records: List[StudyRecord] = []

    for sid, path in STUDY_FILES.items():
        d = _js(path)
        if d is None:
            continue

        rec = StudyRecord(
            study_id=d.get("study_id", sid),
            title=d.get("study", sid),
            executed_at=d.get("executed_at", ""),
            date_range=d.get("date_range", {}),
            n_obs=d.get("n_observations", 0),
            hypothesis_id=d.get("hypothesis_id"),
        )

        # Feature growth
        s4 = d.get("stage4_features", {})
        rec.features_before = s4.get("feat_before", 0)
        rec.features_after  = s4.get("feat_after",  0)

        # Edge growth
        s5 = d.get("stage5_ede", {})
        rec.edges_before = s5.get("edges_before", 0)
        rec.edges_after  = s5.get("edges_after",  0)

        # Winner DNA
        w4 = d.get("stage4_winner_dna", {})
        rec.winner_dna_n = (
            w4.get("n_approved_initial", 0) or
            len(w4.get("dna_patterns", [])) or 0
        )

        # Loser DNA
        l5 = d.get("stage5_loser_dna", {})
        rec.loser_dna_n = len(l5.get("loser_dna_patterns", []))

        # Validation block (H001 or IRP002)
        rec.validation = (
            d.get("h001_validation", {}) or
            d.get("irp002_validation", {}) or {}
        )

        rec.extra = {k: v for k, v in d.items()
                     if k not in ("stage4_winner_dna", "stage5_loser_dna",
                                  "stage4_features", "stage5_ede")}

        records.append(rec)

    # Sort chronologically
    records.sort(key=lambda r: r.executed_at)
    return records


def _collect_hypotheses() -> HypothesisStats:
    reg = _js(FILE_HYPOTHESIS_REG, {})
    hyps = reg.get("hypotheses", {}) if isinstance(reg, dict) else {}
    items = list(hyps.values()) if isinstance(hyps, dict) else hyps

    stats = HypothesisStats(total=len(items))
    for h in items:
        if not isinstance(h, dict):
            continue
        s = h.get("status", "UNKNOWN").upper()
        stats.by_status[s] = stats.by_status.get(s, 0) + 1

    stats.confirmed = stats.by_status.get("CONFIRMED", 0)
    stats.rejected  = stats.by_status.get("REJECTED",  0)
    stats.partial   = stats.by_status.get("PARTIALLY_CONFIRMED", 0)
    stats.proposed  = stats.by_status.get("PROPOSED",  0)
    return stats


def _collect_edges() -> EdgeStats:
    edges = _js(FILE_DISCOVERED_EDGES, {})
    if not isinstance(edges, dict):
        return EdgeStats()

    stats = EdgeStats(total=len(edges))
    active_list = []
    for eid, e in edges.items():
        if not isinstance(e, dict):
            continue
        s = str(e.get("status", "")).upper()
        if s == "ACTIVE":
            stats.active += 1
            active_list.append(e)
        elif s == "CANDIDATE":
            stats.candidate += 1
        elif s == "DECAYING":
            stats.decaying += 1
        elif s in ("RETIRED", "DEPRECATED"):
            stats.retired += 1

    stats.active_edges = active_list
    return stats


def _collect_dna() -> DNAStats:
    stats = DNAStats()
    conn = _db(DB_DNA)
    if conn is None:
        return stats

    try:
        row = conn.execute("SELECT COUNT(*) FROM dna").fetchone()
        stats.total = row[0] if row else 0

        cats = conn.execute(
            "SELECT category, lifecycle, COUNT(*) FROM dna GROUP BY category, lifecycle"
        ).fetchall()
        for c in cats:
            cat = str(c[0] or "").lower()
            cnt = c[2]
            if cat == "winner":
                stats.winner += cnt
            elif cat == "loser":
                stats.loser += cnt
            else:
                stats.edge_patterns += cnt
            if str(c[1] or "").upper() == "INSTITUTIONAL":
                stats.institutional += cnt

        dirs = conn.execute(
            "SELECT direction, COUNT(*) FROM dna GROUP BY direction"
        ).fetchall()
        for d in dirs:
            dirn = str(d[0] or "").upper()
            if dirn == "BUY":
                stats.buy += d[1]
            elif dirn == "SHORT":
                stats.short += d[1]

        ev_row = conn.execute("SELECT COUNT(*) FROM dna_evidence").fetchone()
        stats.evidence_records = ev_row[0] if ev_row else 0

        by_study = conn.execute(
            "SELECT study_id, COUNT(*) FROM dna_evidence GROUP BY study_id"
        ).fetchall()
        stats.by_study = {r[0]: r[1] for r in by_study}

        audit = conn.execute(
            "SELECT operation, COUNT(*) FROM audit_log GROUP BY operation"
        ).fetchall()
        audit_map = {r[0]: r[1] for r in audit}
        stats.created_ops = audit_map.get("CREATED", 0)
        stats.updated_ops = audit_map.get("UPDATED", 0)

    except Exception as e:
        log.warning("DNA collect error: %s", e)
    finally:
        conn.close()

    return stats


def _collect_ikn() -> IKNStats:
    stats = IKNStats()
    conn = _db(DB_IKN)
    if conn is None:
        return stats

    try:
        row = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
        stats.total_nodes = row[0] if row else 0

        row2 = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()
        stats.total_rels = row2[0] if row2 else 0

        node_types = conn.execute(
            "SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type"
        ).fetchall()
        stats.by_node_type = {r[0]: r[1] for r in node_types}

        rel_types = conn.execute(
            "SELECT relationship_type, COUNT(*) FROM relationships GROUP BY relationship_type"
        ).fetchall()
        stats.by_rel_type = {r[0]: r[1] for r in rel_types}

    except Exception as e:
        log.warning("IKN collect error: %s", e)
    finally:
        conn.close()

    return stats


def _collect_platform() -> PlatformStats:
    stats = PlatformStats()
    conn = _db(DB_CONTROL)
    if conn is None:
        return stats

    try:
        row = conn.execute(
            "SELECT COUNT(*) total, COALESCE(SUM(had_error),0) errors FROM ct_cycles"
        ).fetchone()
        if row:
            stats.total_cycles  = row[0]
            stats.cycle_errors  = int(row[1] or 0)

        regimes = conn.execute(
            "SELECT regime, COUNT(*) FROM ct_cycles GROUP BY regime ORDER BY COUNT(*) DESC"
        ).fetchall()
        stats.regime_dist = {r[0] or "UNKNOWN": r[1] for r in regimes}

        row2 = conn.execute("SELECT COUNT(*) FROM ct_decisions").fetchone()
        stats.total_decisions = row2[0] if row2 else 0

        dists = conn.execute(
            "SELECT decision, COUNT(*) FROM ct_decisions GROUP BY decision"
        ).fetchall()
        for r in dists:
            if str(r[0] or "").upper() == "APPROVED":
                stats.approved = r[1]
            elif str(r[0] or "").upper() == "REJECTED":
                stats.rejected = r[1]

        conf_row = conn.execute("SELECT AVG(confidence) FROM ct_decisions").fetchone()
        stats.avg_confidence = float(conf_row[0] or 0.0)

    except Exception as e:
        log.warning("Platform collect error: %s", e)
    finally:
        conn.close()

    return stats


def _collect_replay() -> ReplayStats:
    d = _js(FILE_REPLAY_SUMMARY)
    if not d:
        return ReplayStats(exists=False)

    m = d.get("metrics", {})
    return ReplayStats(
        exists=True,
        days_replayed=d.get("days_replayed", 0),
        date_range=d.get("date_range", ""),
        win_rate=float(m.get("win_rate", 0) or 0),
        avg_r=float(m.get("avg_r_multiple", 0) or 0),
        profit_factor=float(m.get("profit_factor", 0) or 0),
        max_drawdown=float(m.get("max_drawdown_pct", 0) or 0),
        total_pnl=float(m.get("total_pnl", 0) or 0),
        net_pnl=float(m.get("net_pnl", 0) or 0),
        total_signals=int(m.get("total_signals", 0) or 0),
        trades_executed=int(m.get("trades_executed", 0) or 0),
    )


def collect_all() -> GVAEvidence:
    """Build complete evidence bundle. Read-only."""
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    ev = GVAEvidence(
        collected_at=datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    )

    ev.studies    = _collect_studies()
    ev.hypothesis = _collect_hypotheses()
    ev.edges      = _collect_edges()
    ev.dna        = _collect_dna()
    ev.ikn        = _collect_ikn()
    ev.platform   = _collect_platform()
    ev.replay     = _collect_replay()

    # Feature count from EDE
    ede = _js(FILE_EDE_FEATURES, [])
    if isinstance(ede, list):
        ev.feature_count = len(ede)
    elif isinstance(ede, dict):
        ev.feature_count = sum(len(v) for v in ede.values() if isinstance(v, list))

    # Baseline from study002 stage4
    for s in ev.studies:
        if "study002" in s.study_id.lower() and "a" not in s.study_id.lower():
            ev.feature_baseline = s.features_before
            ev.labeled_features = s.features_after
            break

    # Strategy performance
    sp = _js(FILE_STRATEGY_PERF, {})
    if isinstance(sp, dict):
        ev.strategy_count = len(sp)
        ev.strategy_perf  = sp

    # Cumulative P&L
    ptd = _js(FILE_PAPER_DAILY, {})
    if isinstance(ptd, dict):
        cum = ptd.get("cumulative", {})
        ev.cum_pnl        = float(cum.get("cum_pnl", 0) or 0)
        ev.cum_return_pct = float(cum.get("cum_return_pct", 0) or 0)
        ev.closed_trades  = int(cum.get("closed_trades", 0) or 0)
        ev.open_trades    = int(cum.get("open_trades", 0) or 0)

    return ev

"""
decision_tracer/dta_collector.py
===================================
DTA-001 — Decision Traceability Audit — Data Collector

READ-ONLY. Reconstructs every layer of the decision chain for a given symbol
from the control tower event log, EDE features, DNA repository, IKN graph,
and all study artefacts.

No live data calls. Traces the most recent (or specified) decision only.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

DB_CTRL  = DATA / "control_tower.db"
DB_DNA   = DATA / "mls" / "institutional_dna.db"
DB_IKN   = DATA / "ikn"  / "ikn.db"
FILE_EDE       = DATA / "ede_feature_db.json"
FILE_EDGES     = DATA / "discovered_edges.json"
FILE_STRAT_PERF= DATA / "strategy_performance.json"
FILE_HYP_REG   = DATA / "ars_hypothesis_registry.json"
FILE_REPLAY    = DATA / "replay_summary.json"

STUDY_FILES = {
    "study002":       DATA / "study002_results.json",
    "study002a":      DATA / "study002a_results.json",
    "ars_study_003":  DATA / "ars_study_003.json",
    "ars_study_h001": DATA / "ars_study_h001.json",
    "ars_study_irp002": DATA / "ars_study_irp002.json",
}


def _conn(path: Path) -> Optional[sqlite3.Connection]:
    if not path.exists():
        return None
    try:
        c = sqlite3.connect(str(path), timeout=5)
        c.row_factory = sqlite3.Row
        return c
    except Exception as e:
        log.warning("Cannot open %s: %s", path.name, e)
        return None


def _js(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


# ── Layer data containers ────────────────────────────────────────────────────

@dataclass
class MarketContext:
    cycle_id:   str = ""
    ts:         str = ""
    regime:     str = ""
    vix:        float = 0.0
    breadth:    float = 0.0
    pcr:        float = 0.0
    distortion: str = "NORMAL"
    trading_allowed: bool = True
    size_multiplier: float = 1.0
    regime_probs: Dict = field(default_factory=dict)
    strategy_mix: Dict = field(default_factory=dict)
    meta_top_strategy: str = ""


@dataclass
class FeatureSnapshot:
    symbol:         str = ""
    ts:             str = ""
    features:       Dict = field(default_factory=dict)
    forward_return: Optional[float] = None


@dataclass
class SignalRecord:
    symbol:     str = ""
    direction:  str = ""
    strategy:   str = ""
    confidence: float = 0.0
    source:     str = ""


@dataclass
class DNAMatch:
    dna_id:         int = 0
    feature_name:   str = ""
    direction:      str = ""
    category:       str = ""
    lifecycle:      str = ""
    consensus_score: float = 0.0
    confidence:     float = 0.0
    feature_value:  Optional[float] = None
    matched:        bool = False
    match_reason:   str = ""


@dataclass
class EdgeMatch:
    edge_id:    str = ""
    name:       str = ""
    status:     str = ""
    precision:  float = 0.0
    sharpe:     float = 0.0
    oos_wr:     float = 0.0
    conditions: List[Dict] = field(default_factory=list)
    all_satisfied: bool = False
    satisfied_count: int = 0
    total_count:    int = 0


@dataclass
class IKNReference:
    node_id:   str = ""
    node_type: str = ""
    name:      str = ""
    relationships: List[str] = field(default_factory=list)


@dataclass
class DecisionRecord:
    cycle_id:         str = ""
    ts:               str = ""
    symbol:           str = ""
    strategy:         str = ""
    decision:         str = ""
    confidence:       float = 0.0
    rejection_reason: str = ""
    technical_score:  float = 0.0
    risk_score:       float = 0.0
    macro_score:      float = 0.0
    regime_score:     float = 0.0
    position_modifier: float = 1.0
    regime:           str = ""
    vix:              float = 0.0


@dataclass
class RiskContext:
    risk_passed:    bool = False
    simulation_approved: bool = False
    guardian_approved: bool = False
    position_modifier: float = 1.0
    drawdown_pct:   float = 0.0
    open_positions: int = 0
    risk_reasons:   List[str] = field(default_factory=list)


@dataclass
class TraceBundle:
    """Complete decision trace for one symbol."""
    symbol:          str = ""
    audit_ts:        str = ""
    # Target decision
    decision:        Optional[DecisionRecord] = None
    # All layers
    market_ctx:      Optional[MarketContext] = None
    features:        Optional[FeatureSnapshot] = None
    signal:          Optional[SignalRecord] = None
    dna_matches:     List[DNAMatch] = field(default_factory=list)
    edge_matches:    List[EdgeMatch] = field(default_factory=list)
    ikn_refs:        List[IKNReference] = field(default_factory=list)
    risk_ctx:        Optional[RiskContext] = None
    # Historical context
    decision_history:      List[DecisionRecord] = field(default_factory=list)
    alternative_candidates: List[SignalRecord] = field(default_factory=list)
    strategy_perf:         Dict = field(default_factory=dict)
    study_references:      List[str] = field(default_factory=list)
    hypothesis_refs:       List[Dict] = field(default_factory=list)
    replay_stats:          Dict = field(default_factory=dict)
    # Comparison to previous cycle
    prev_decision:   Optional[DecisionRecord] = None
    prev_cycle_diff: Dict = field(default_factory=dict)


# ── Layer collectors ──────────────────────────────────────────────────────────

def _load_target_decision(symbol: str, target_date: Optional[str] = None) -> Optional[DecisionRecord]:
    """Find most recent (or date-specific) decision for symbol."""
    conn = _conn(DB_CTRL)
    if not conn:
        return None
    try:
        if target_date:
            row = conn.execute("""
                SELECT d.*, c.started_at, c.regime, c.vix
                FROM ct_decisions d
                JOIN ct_cycles c ON d.cycle_id = c.cycle_id
                WHERE d.symbol = ? AND DATE(c.started_at) = ?
                ORDER BY c.started_at DESC LIMIT 1
            """, (symbol, target_date)).fetchone()
        else:
            row = conn.execute("""
                SELECT d.*, c.started_at, c.regime, c.vix
                FROM ct_decisions d
                JOIN ct_cycles c ON d.cycle_id = c.cycle_id
                WHERE d.symbol = ?
                ORDER BY c.started_at DESC LIMIT 1
            """, (symbol,)).fetchone()
        if row:
            return _row_to_decision(row)
    finally:
        conn.close()
    return None


def _row_to_decision(row) -> DecisionRecord:
    return DecisionRecord(
        cycle_id=row["cycle_id"],
        ts=row["started_at"] or row["ts"],
        symbol=row["symbol"],
        strategy=row["strategy"] or "",
        decision=row["decision"] or "",
        confidence=float(row["confidence"] or 0),
        rejection_reason=row["rejection_reason"] or "",
        technical_score=float(row["technical_score"] or 0),
        risk_score=float(row["risk_score"] or 0),
        macro_score=float(row["macro_score"] or 0),
        regime_score=float(row["regime_score"] or 0),
        position_modifier=float(row["position_modifier"] or 1),
        regime=row["regime"] or "",
        vix=float(row["vix"] or 0),
    )


def _load_cycle_events(cycle_id: str) -> List[Dict]:
    conn = _conn(DB_CTRL)
    if not conn:
        return []
    try:
        rows = conn.execute("""
            SELECT ts, event_type, source_agent, payload
            FROM ct_events WHERE cycle_id = ?
            ORDER BY ts
        """, (cycle_id,)).fetchall()
        result = []
        for r in rows:
            p = r["payload"]
            if p:
                try:
                    p = json.loads(p)
                except Exception:
                    pass
            result.append({
                "ts": r["ts"],
                "event_type": r["event_type"],
                "source": r["source_agent"],
                "payload": p,
            })
        return result
    finally:
        conn.close()


def _parse_market_context(events: List[Dict], cycle_id: str, regime: str, vix: float) -> MarketContext:
    ctx = MarketContext(cycle_id=cycle_id, regime=regime, vix=vix)
    for e in events:
        et = e["event_type"]
        p  = e["payload"] or {}
        if not isinstance(p, dict):
            continue
        if et == "market.data.ready":
            ctx.breadth = float(p.get("breadth", 0))
            ctx.pcr     = float(p.get("pcr", 0))
            ctx.vix     = float(p.get("vix", vix))
            ctx.regime  = p.get("regime", regime)
            ctx.ts      = e["ts"]
        elif et == "global.distortion.detected":
            ctx.distortion       = p.get("risk_level", "NORMAL")
            ctx.trading_allowed  = bool(p.get("trading_allowed", True))
            ctx.size_multiplier  = float(p.get("size_multiplier", 1.0))
        elif et == "global.regime_probability.computed":
            ctx.regime_probs    = {
                "bull_trend": float(p.get("trend_prob", 0)),
                "range":      float(p.get("range_prob", 0)),
                "volatile":   float(p.get("volatile_prob", 0)),
                "bear":       float(p.get("bear_prob", 0)),
                "dominant":   p.get("dominant", ""),
            }
            ctx.strategy_mix = p.get("strategy_mix", {})
        elif et == "meta.learning.applied":
            ctx.meta_top_strategy = p.get("top_strategy", "")
    return ctx


def _parse_risk_context(events: List[Dict], symbol: str, modifier: float) -> RiskContext:
    ctx = RiskContext(position_modifier=modifier)
    for e in events:
        et = e["event_type"]
        p  = e["payload"] or {}
        if not isinstance(p, dict):
            continue
        if et == "risk.check.passed":
            ctx.risk_passed = True
        elif et == "risk.check.failed":
            reason = p.get("reason", p.get("message", str(p)[:100]))
            ctx.risk_reasons.append(reason)
        elif et == "simulation.complete":
            ctx.simulation_approved = p.get("approved", 0) > 0
        elif et == "risk.guardian.complete":
            ctx.guardian_approved = (p.get("decision", "") == "APPROVED")
        elif et == "risk.portfolio.updated":
            ctx.drawdown_pct   = float(p.get("drawdown_pct", 0))
            ctx.open_positions = int(p.get("open_positions", 0))
    return ctx


def _parse_alternatives(events: List[Dict], symbol: str) -> List[SignalRecord]:
    alts = []
    for e in events:
        if e["event_type"] != "opportunity.equity.found":
            continue
        p = e["payload"] or {}
        if not isinstance(p, dict):
            continue
        sym = p.get("symbol", "")
        if sym == symbol:
            continue
        alts.append(SignalRecord(
            symbol=sym,
            direction=str(p.get("direction", "")).replace("SignalDirection.", ""),
            strategy=p.get("strategy", ""),
            confidence=float(p.get("confidence", 0)),
            source=e["source"],
        ))
    # Sort by confidence
    alts.sort(key=lambda x: -x.confidence)
    return alts


def _parse_signal(events: List[Dict], symbol: str) -> Optional[SignalRecord]:
    for e in events:
        if e["event_type"] != "opportunity.equity.found":
            continue
        p = e["payload"] or {}
        if isinstance(p, dict) and p.get("symbol") == symbol:
            return SignalRecord(
                symbol=symbol,
                direction=str(p.get("direction", "")).replace("SignalDirection.", ""),
                strategy=p.get("strategy", ""),
                confidence=float(p.get("confidence", 0)),
                source=e["source"],
            )
    return None


def _load_features(symbol: str) -> Optional[FeatureSnapshot]:
    ede = _js(FILE_EDE, [])
    records = []
    if isinstance(ede, list):
        records = [r for r in ede if isinstance(r, dict) and r.get("symbol") == symbol]
    elif isinstance(ede, dict):
        for recs in ede.values():
            if isinstance(recs, list):
                records.extend(r for r in recs if isinstance(r, dict) and r.get("symbol") == symbol)

    if not records:
        return FeatureSnapshot(symbol=symbol)

    # Most recent
    records.sort(key=lambda r: r.get("date", r.get("ts", "")), reverse=True)
    r = records[0]
    return FeatureSnapshot(
        symbol=symbol,
        ts=r.get("date", r.get("ts", "")),
        features=r.get("features", {}),
        forward_return=r.get("forward_return"),
    )


def _eval_condition(cond: Dict, features: Dict) -> bool:
    """Evaluate a single edge condition against feature values."""
    feat  = cond.get("feature", "")
    op    = cond.get("operator", "")
    threshold = cond.get("threshold", 0)
    val = features.get(feat)
    if val is None:
        return False
    try:
        v = float(val)
        t = float(threshold)
        if op == "<=": return v <= t
        if op == "<":  return v < t
        if op == ">=": return v >= t
        if op == ">":  return v > t
        if op == "==": return abs(v - t) < 1e-9
    except (TypeError, ValueError):
        pass
    return False


def _match_edges(features: Dict) -> List[EdgeMatch]:
    edges = _js(FILE_EDGES, {})
    if not isinstance(edges, dict):
        return []

    matches = []
    for eid, e in edges.items():
        if not isinstance(e, dict):
            continue
        conds = e.get("entry_conditions", [])
        if isinstance(conds, str):
            try:
                conds = json.loads(conds)
            except Exception:
                conds = []

        satisfied = sum(1 for c in conds if _eval_condition(c, features))
        total     = len(conds)

        em = EdgeMatch(
            edge_id=eid,
            name=e.get("name", eid),
            status=e.get("status", ""),
            precision=float(e.get("precision", 0) or 0),
            sharpe=float(e.get("sharpe_ratio", 0) or 0),
            oos_wr=float(e.get("oos_win_rate", 0) or 0),
            conditions=conds,
            all_satisfied=(total > 0 and satisfied == total),
            satisfied_count=satisfied,
            total_count=total,
        )
        matches.append(em)

    # Sort: fully satisfied first, then by satisfaction ratio, then by status
    matches.sort(key=lambda m: (-m.all_satisfied, -(m.satisfied_count / max(m.total_count, 1))))
    return matches


def _match_dna(features: Dict, direction: str = "") -> List[DNAMatch]:
    conn = _conn(DB_DNA)
    if not conn:
        return []
    try:
        rows = conn.execute("""
            SELECT id, feature_name, direction, category, lifecycle,
                   consensus_score, confidence
            FROM dna ORDER BY confidence DESC
        """).fetchall()
    finally:
        conn.close()

    matches = []
    for r in rows:
        feat_name = r["feature_name"]
        feat_val  = features.get(feat_name)
        dna_dir   = str(r["direction"] or "").upper()

        # A DNA match means: the feature is present and the direction agrees
        # We determine "favorability" by sign: BUY DNA → feature > 0.5 (normalized)
        matched = False
        reason  = ""
        if feat_val is not None:
            fv = float(feat_val) if feat_val is not None else None
            if fv is not None:
                if dna_dir == "BUY" and direction in ("BUY", ""):
                    matched = fv > 0.3
                    reason  = f"feature={fv:.3f} > 0.3 (BUY-aligned)"
                elif dna_dir == "SHORT" and direction in ("SHORT", "SELL", ""):
                    matched = fv < 0.5
                    reason  = f"feature={fv:.3f} < 0.5 (SHORT-aligned)"
                elif direction == "" or direction not in ("BUY", "SHORT", "SELL"):
                    # Neutral: any feature presence counts
                    matched = True
                    reason  = f"feature present={fv:.3f}"

        dm = DNAMatch(
            dna_id=r["id"],
            feature_name=feat_name,
            direction=dna_dir,
            category=str(r["category"] or ""),
            lifecycle=str(r["lifecycle"] or ""),
            consensus_score=float(r["consensus_score"] or 0),
            confidence=float(r["confidence"] or 0),
            feature_value=float(feat_val) if feat_val is not None else None,
            matched=matched,
            match_reason=reason,
        )
        matches.append(dm)

    # Sort: matched first, then by confidence
    matches.sort(key=lambda m: (-m.matched, -m.confidence))
    return matches


def _load_ikn_refs(features: Dict) -> List[IKNReference]:
    conn = _conn(DB_IKN)
    if not conn:
        return []
    refs = []
    try:
        feat_names = set(features.keys())
        nodes = conn.execute("SELECT * FROM nodes").fetchall()
        for n in nodes:
            name = str(n["name"] or "")
            # Match if node name contains any feature name
            relevant = any(fn in name for fn in feat_names) or n["node_type"] in (
                "STUDY", "HYPOTHESIS", "DISCOVERY", "FINDING", "KNOWLEDGE_PACKAGE"
            )
            if not relevant:
                continue
            # Get relationships
            rels = conn.execute("""
                SELECT r.relationship_type, n2.name tgt_name, n2.node_type tgt_type
                FROM relationships r
                JOIN nodes n2 ON r.target_id = n2.node_id
                WHERE r.source_id = ?
                UNION
                SELECT r.relationship_type, n2.name src_name, n2.node_type src_type
                FROM relationships r
                JOIN nodes n2 ON r.source_id = n2.node_id
                WHERE r.target_id = ?
            """, (n["node_id"], n["node_id"])).fetchall()
            refs.append(IKNReference(
                node_id=n["node_id"],
                node_type=n["node_type"],
                name=name,
                relationships=[f"{r['relationship_type']} → [{r['tgt_type']}]{r['tgt_name']}" for r in rels],
            ))
    finally:
        conn.close()
    # Deduplicate by node_id
    seen = set()
    result = []
    for r in refs:
        if r.node_id not in seen:
            seen.add(r.node_id)
            result.append(r)
    return result[:20]


def _load_decision_history(symbol: str, exclude_cycle: str = "", limit: int = 10) -> List[DecisionRecord]:
    conn = _conn(DB_CTRL)
    if not conn:
        return []
    try:
        rows = conn.execute("""
            SELECT d.*, c.started_at, c.regime, c.vix
            FROM ct_decisions d
            JOIN ct_cycles c ON d.cycle_id = c.cycle_id
            WHERE d.symbol = ? AND d.cycle_id != ?
            ORDER BY c.started_at DESC LIMIT ?
        """, (symbol, exclude_cycle, limit)).fetchall()
        return [_row_to_decision(r) for r in rows]
    finally:
        conn.close()


def _load_study_refs(features: Dict) -> List[str]:
    """Find which studies discovered patterns related to current features."""
    refs = []
    feat_names = set(features.keys())

    for study_id, path in STUDY_FILES.items():
        d = _js(path, {})
        if not d:
            continue
        # Check if any feature from our set is referenced
        text = json.dumps(d)
        hits = [fn for fn in feat_names if fn in text]
        if hits:
            title = d.get("study", study_id)
            date  = d.get("executed_at", "")[:10]
            n_obs = d.get("n_observations", 0)
            refs.append(f"{study_id} [{date}] — '{title}' | obs={n_obs:,} | features matched: {', '.join(hits[:5])}")
    return refs


def _load_hypothesis_refs() -> List[Dict]:
    reg = _js(FILE_HYP_REG, {})
    if not isinstance(reg, dict):
        return []
    hyps = reg.get("hypotheses", {})
    result = []
    for hid, h in (hyps.items() if isinstance(hyps, dict) else []):
        if not isinstance(h, dict):
            continue
        result.append({
            "id":     hid,
            "title":  h.get("title", ""),
            "status": h.get("status", ""),
            "confidence": h.get("confidence", ""),
        })
    return result[:10]


def _prev_decision_diff(current: DecisionRecord, prev: Optional[DecisionRecord]) -> Dict:
    """What changed between the current and previous decision?"""
    if not prev:
        return {}
    diff = {}
    if prev.decision != current.decision:
        diff["decision_changed"] = f"{prev.decision} → {current.decision}"
    if abs(prev.confidence - current.confidence) > 0.05:
        diff["confidence_changed"] = f"{prev.confidence:.2f} → {current.confidence:.2f}"
    if prev.regime != current.regime:
        diff["regime_changed"] = f"{prev.regime} → {current.regime}"
    if abs(prev.vix - current.vix) > 1:
        diff["vix_changed"] = f"{prev.vix:.1f} → {current.vix:.1f}"
    if prev.strategy != current.strategy:
        diff["strategy_changed"] = f"{prev.strategy} → {current.strategy}"
    return diff


# ── Main collector ────────────────────────────────────────────────────────────

def collect_trace(symbol: str, target_date: Optional[str] = None) -> TraceBundle:
    """
    Build complete decision trace for symbol.
    target_date: 'YYYY-MM-DD' or None (most recent)
    """
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    bundle = TraceBundle(
        symbol=symbol,
        audit_ts=datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
    )

    # Find target decision
    bundle.decision = _load_target_decision(symbol, target_date)
    if not bundle.decision:
        log.info("[DTA] No decision found for %s on %s — partial trace only", symbol, target_date)
    
    cycle_id = bundle.decision.cycle_id if bundle.decision else ""

    # Load all events for this cycle
    events = _load_cycle_events(cycle_id) if cycle_id else []

    # Market context
    if bundle.decision:
        bundle.market_ctx = _parse_market_context(
            events, cycle_id, bundle.decision.regime, bundle.decision.vix
        )

    # Signal
    bundle.signal = _parse_signal(events, symbol)

    # Alternatives
    bundle.alternative_candidates = _parse_alternatives(events, symbol)[:10]

    # Feature snapshot
    bundle.features = _load_features(symbol)

    # DNA matches
    feat_dict = bundle.features.features if bundle.features else {}
    direction = bundle.signal.direction if bundle.signal else ""
    bundle.dna_matches = _match_dna(feat_dict, direction)

    # Edge matches
    bundle.edge_matches = _match_edges(feat_dict)

    # IKN references
    bundle.ikn_refs = _load_ikn_refs(feat_dict)

    # Risk context
    if bundle.decision:
        bundle.risk_ctx = _parse_risk_context(events, symbol, bundle.decision.position_modifier)

    # Decision history
    bundle.decision_history = _load_decision_history(
        symbol, exclude_cycle=cycle_id, limit=10
    )

    # Previous decision (most recent before current)
    if bundle.decision_history:
        bundle.prev_decision = bundle.decision_history[0]
        bundle.prev_cycle_diff = _prev_decision_diff(
            bundle.decision, bundle.prev_decision
        ) if bundle.decision else {}

    # Strategy performance
    sp = _js(FILE_STRAT_PERF, {})
    if bundle.decision and bundle.decision.strategy in sp:
        bundle.strategy_perf = sp[bundle.decision.strategy]

    # Study references
    bundle.study_references = _load_study_refs(feat_dict)

    # Hypothesis references
    bundle.hypothesis_refs = _load_hypothesis_refs()

    # Replay stats
    rs = _js(FILE_REPLAY, {})
    if isinstance(rs, dict):
        bundle.replay_stats = rs.get("metrics", {})

    return bundle

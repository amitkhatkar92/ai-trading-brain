"""
opportunity_engine/knowledge_fusion/knowledge_fusion_engine.py
================================================================
KLP-004 — Knowledge Fusion Engine

Fuses information from all available repository sources into a
multi-angle knowledge layer. Observational / read-only.

SAFETY CONTRACT
---------------
• broker_calls = 0, orders = 0, modifications = 0, cancellations = 0
• PAPER_TRADING state: never changed
• LIVE_TRADING_AUTHORIZED: never set
• no_lookahead = True on every output record
• Never modifies StrategyLab, RiskControl, DecisionEngine, or OrderManager

SOURCE INVENTORY (verified 2026-08-21)
---------------------------------------
SOURCE                    RECORDS   OUTCOME-LINKED   DECISION-USED
rejection_audit.db         504      YES (move 1/3/5d) NO
ct_decisions              1505      NO (decisions)    YES (was used)
ct_cycles                 5328      NO (context)      YES (market ctx)
regime_probability_history 500      NO (soft probs)   YES (MetaLearning)
KLP JSONL (local)          100      NO (outcomes=0)   NO (observational)
shadow_evidence_ledger     405      PARTIAL (C2)      NO (observational)
paper_trades.csv             0      NO (empty)        NO
"""
from __future__ import annotations

import json
import math
import sqlite3
import statistics
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .kf_models import (
    AngleResult,
    CANDIDATE, OBSERVED,
    CONTRADICTION_NONE, CONTRADICTION_MINOR, CONTRADICTION_MAJOR,
    ContradictionRecord,
    FALSE_NEGATIVE, FALSE_POSITIVE,
    KnowledgeFusionRecord,
    KnowledgeObject,
    KnowledgeValueScore,
    MultiAngleView,
    OOS_NOT_TESTED, OOS_TESTED, OOS_PASSED, OOS_FAILED,
    OUTCOME_UNKNOWN,
    RedundancyRecord,
    RelationshipCandidate,
    SelectionAnalysisRecord,
    SourceInventoryItem,
    TRUE_NEGATIVE, TRUE_POSITIVE,
    USED_AS_CONTEXT, USED_IN_DECISION, OBSERVED_ONLY, INSUFFICIENT_DATA,
)

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

_ROOT      = Path(__file__).parent.parent.parent
_DATA      = _ROOT / "data"
_KF_DIR    = _DATA / "klp" / "knowledge_fusion"
_KLP_DIR   = _DATA / "klp"

_REJECTION_DB   = _DATA / "rejection_audit.db"
_CT_DB          = _DATA / "control_tower.db"
_REGIME_HISTORY = _DATA / "regime_probability_history.json"
_SHADOW_LEDGER  = _DATA / "shadow_evidence_ledger.jsonl"
_PAPER_CSV      = _DATA / "paper_trades.csv"

# ─────────────────────────────────────────────────────────────────────────────
# Statistical helpers (stdlib only)
# ─────────────────────────────────────────────────────────────────────────────

def _pct(vals: List[float], p: float) -> Optional[float]:
    vs = [v for v in vals if v is not None]
    if not vs:
        return None
    vs.sort()
    idx = (p / 100.0) * (len(vs) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(vs) - 1)
    frac = idx - lo
    return round(vs[lo] * (1 - frac) + vs[hi] * frac, 4)


def _safe_mean(vals: List[float]) -> Optional[float]:
    vs = [v for v in vals if v is not None]
    return round(statistics.mean(vs), 4) if vs else None


def _safe_rate(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d > 0 else None


def _recency_w(date_str: str, ref: date, half_life: int = 90) -> float:
    try:
        delta = (ref - date.fromisoformat(date_str[:10])).days
        return 2.0 ** (-max(delta, 0) / half_life)
    except (ValueError, TypeError):
        return 0.5


def _ess(dates: List[str], ref: date) -> float:
    return sum(_recency_w(d, ref) for d in dates)


# ─────────────────────────────────────────────────────────────────────────────
# Sector lookup (mirrors HBE mapping)
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL_SECTOR: Dict[str, str] = {
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "BANKBARODA": "BANK", "INDUSINDBK": "BANK",
    "HDFCAMC": "FINSERVICES", "ANGELONE": "FINSERVICES", "BAJAJFINSV": "FINSERVICES",
    "BAJFINANCE": "FINSERVICES",
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "TECHM": "IT", "HCLTECH": "IT",
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "BPCL": "ENERGY",
    "ADANIGREEN": "ENERGY", "NTPC": "ENERGY", "POWERGRID": "ENERGY",
    "TATAPOWER": "ENERGY", "NHPC": "ENERGY", "COALINDIA": "ENERGY",
    "NMDC": "METALS",
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "BAJAJ-AUTO": "AUTO",
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA",
    "BIOCON": "PHARMA", "ALKEM": "PHARMA",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
    "MARICO": "FMCG", "TATACONSUM": "FMCG", "NYKAA": "FMCG",
    "TATASTEEL": "METALS", "JSWSTEEL": "METALS", "HINDALCO": "METALS",
    "PRESTIGE": "REALTY", "DLF": "REALTY",
    "BHARTIARTL": "TELECOM",
    "ASIANPAINT": "CONSUMER", "HAVELLS": "CONSUMER", "VOLTAS": "CONSUMER",
    "TITAN": "CONSUMER", "CUMMINSIND": "CONSUMER", "INOXWIND": "CONSUMER",
    "FORTIS": "HEALTHCARE", "HDFCLIFE": "INSURANCE",
    "NIFTY": "INDEX", "BANKNIFTY": "INDEX",
}


def _sector(symbol: str) -> str:
    return _SYMBOL_SECTOR.get(symbol.upper().strip(), "UNKNOWN")


# ─────────────────────────────────────────────────────────────────────────────
# Source inventory — verified against actual repository state 2026-08-21
# ─────────────────────────────────────────────────────────────────────────────

def build_source_inventory(
    data_dir: Optional[Path] = None,
) -> List[SourceInventoryItem]:
    """
    Inspect actual repository files and return the verified source inventory.

    Never fabricates availability. If a file is absent its availability = ABSENT.
    """
    d = data_dir or _DATA
    items: List[SourceInventoryItem] = []

    def _db_count(db_path: Path, table: str) -> int:
        if not db_path.exists() or db_path.stat().st_size == 0:
            return 0
        try:
            conn = sqlite3.connect(str(db_path))
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.close()
            return n
        except Exception:
            return 0

    def _jsonl_count(path: Path) -> int:
        if not path.exists():
            return 0
        return sum(1 for l in path.read_text(encoding="utf-8").splitlines() if l.strip())

    def _klp_obs_count(klp_dir: Path) -> Tuple[int, int]:
        """(obs_count, outcome_count) from all KLP files."""
        obs = out = 0
        for f in klp_dir.glob("KLP_*.jsonl"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                    et = r.get("event_type", "")
                    if et == "KNOWLEDGE_OBSERVATION":
                        obs += 1
                    elif et == "OUTCOME_UPDATE" and r.get("first_event") in (
                        "TARGET_HIT", "STOP_HIT", "OUTCOME_EXPIRED", "OUTCOME_AMBIGUOUS"
                    ):
                        out += 1
                except Exception:
                    pass
        return obs, out

    rejection_n  = _db_count(d / "rejection_audit.db",      "rejection_log")
    ct_dec_n     = _db_count(d / "control_tower.db",         "ct_decisions")
    ct_cyc_n     = _db_count(d / "control_tower.db",         "ct_cycles")
    shadow_n     = _jsonl_count(d / "shadow_evidence_ledger.jsonl")
    ke_n         = _jsonl_count(d / "knowledge_evidence_ledger.jsonl")
    rq_n         = _jsonl_count(d / "research_question_queue.jsonl")

    regime_n = 0
    if (d / "regime_probability_history.json").exists():
        try:
            regime_n = len(json.loads((d / "regime_probability_history.json").read_text()))
        except Exception:
            pass

    klp_obs_n, klp_out_n = _klp_obs_count(d / "klp") if (d / "klp").exists() else (0, 0)

    paper_n = 0
    if (d / "paper_trades.csv").exists():
        lines = (d / "paper_trades.csv").read_text().splitlines()
        paper_n = max(0, len([l for l in lines if l.strip()]) - 1)  # minus header

    def _avail(n: int) -> str:
        if n == 0:
            return "ABSENT"
        return "AVAILABLE"

    items = [
        SourceInventoryItem(
            source="REJECTION_AUDIT_DB",
            field="symbol, direction, regime, vix, decision_score, move_1d/3d/5d, max_favorable, max_adverse, rejection_outcome",
            availability=_avail(rejection_n),
            historical_depth="2024-01-01 to 2026-08-21 (synthetic + real)",
            record_count=rejection_n,
            update_frequency="DAILY",
            is_outcome_linked=True,
            currently_used_in_decisions=False,
            usage_status=OBSERVED_ONLY,
        ),
        SourceInventoryItem(
            source="CONTROL_TOWER_DECISIONS",
            field="symbol, strategy, confidence, decision, rejection_reason, technical_score, risk_score, macro_score, sentiment_score, regime_score",
            availability=_avail(ct_dec_n),
            historical_depth="2026-03-11 to present",
            record_count=ct_dec_n,
            update_frequency="REALTIME",
            is_outcome_linked=False,
            currently_used_in_decisions=True,
            usage_status=USED_IN_DECISION,
        ),
        SourceInventoryItem(
            source="CONTROL_TOWER_CYCLES",
            field="cycle_id, regime, vix, breadth, pcr, signals_generated, strategies_assigned, risk_approved, trades_executed",
            availability=_avail(ct_cyc_n),
            historical_depth="2026-03-11 to present",
            record_count=ct_cyc_n,
            update_frequency="REALTIME",
            is_outcome_linked=False,
            currently_used_in_decisions=True,
            usage_status=USED_AS_CONTEXT,
        ),
        SourceInventoryItem(
            source="REGIME_PROBABILITY_HISTORY",
            field="trend_prob, range_prob, volatile_prob, bear_prob, dominant, confidence, strategy_mix, vix, breadth, pcr",
            availability=_avail(regime_n),
            historical_depth="2026-03-13 to 2026-04-02",
            record_count=regime_n,
            update_frequency="REALTIME",
            is_outcome_linked=False,
            currently_used_in_decisions=True,
            usage_status=USED_AS_CONTEXT,
        ),
        SourceInventoryItem(
            source="KLP_OBSERVATION",
            field="symbol, direction, regime, knowledge_score, candidate_score, scanner_confidence, atr_pct, entry, target, stop",
            availability=_avail(klp_obs_n),
            historical_depth="2026-08-20 to 2026-08-21",
            record_count=klp_obs_n,
            update_frequency="DAILY",
            is_outcome_linked=False,
            currently_used_in_decisions=False,
            usage_status=OBSERVED_ONLY,
        ),
        SourceInventoryItem(
            source="KLP_OUTCOME",
            field="t1_ret_pct, t3_ret_pct, t5_ret_pct, mfe_pct, mae_pct, target_hit, stop_hit, first_event",
            availability="ABSENT" if klp_out_n == 0 else "AVAILABLE",
            historical_depth="NONE — first outcomes expected 2026-08-22",
            record_count=klp_out_n,
            update_frequency="DAILY",
            is_outcome_linked=True,
            currently_used_in_decisions=False,
            usage_status=INSUFFICIENT_DATA,
        ),
        SourceInventoryItem(
            source="SHADOW_EVIDENCE_LEDGER",
            field="symbol, direction, v3_score, c2_score, selected_final_5, t1_ret_pct, ge1, ge2",
            availability=_avail(shadow_n),
            historical_depth="historical C2 research data",
            record_count=shadow_n,
            update_frequency="DAILY",
            is_outcome_linked=True,
            currently_used_in_decisions=False,
            usage_status=OBSERVED_ONLY,
        ),
        SourceInventoryItem(
            source="KNOWLEDGE_EVIDENCE_LEDGER",
            field="classification, direction, regime, ge1, ge2, miss_reason, strategy_status",
            availability=_avail(ke_n),
            historical_depth="historical C2 research data",
            record_count=ke_n,
            update_frequency="DAILY",
            is_outcome_linked=True,
            currently_used_in_decisions=False,
            usage_status=OBSERVED_ONLY,
        ),
        SourceInventoryItem(
            source="PAPER_TRADES_CSV",
            field="symbol, direction, entry_price, stop_loss, target, strategy, confidence, rr, pnl",
            availability="ABSENT" if paper_n == 0 else "AVAILABLE",
            historical_depth="NONE — no completed paper trades yet",
            record_count=paper_n,
            update_frequency="REALTIME",
            is_outcome_linked=True,
            currently_used_in_decisions=False,
            usage_status=INSUFFICIENT_DATA,
        ),
        SourceInventoryItem(
            source="RESEARCH_QUESTION_QUEUE",
            field="research_question_id, question, direction, problem_area, minimum_sample",
            availability=_avail(rq_n),
            historical_depth="2026-08-18 to present",
            record_count=rq_n,
            update_frequency="DAILY",
            is_outcome_linked=False,
            currently_used_in_decisions=False,
            usage_status=OBSERVED_ONLY,
        ),
        SourceInventoryItem(
            source="MARKET_SNAPSHOT_REALTIME",
            field="regime, vix, pcr, breadth, global_bias, global_sentiment_score, sector_flows",
            availability="PARTIAL",
            historical_depth="NONE — not persisted historically",
            record_count=0,
            update_frequency="REALTIME",
            is_outcome_linked=False,
            currently_used_in_decisions=True,
            usage_status=USED_IN_DECISION,
        ),
        SourceInventoryItem(
            source="GLOBAL_SNAPSHOT_REALTIME",
            field="sp500_change, nasdaq_change, nikkei_change, cboe_vix, usdinr_change, crude_brent_change",
            availability="PARTIAL",
            historical_depth="NONE — not persisted historically",
            record_count=0,
            update_frequency="REALTIME",
            is_outcome_linked=False,
            currently_used_in_decisions=True,
            usage_status=USED_AS_CONTEXT,
        ),
        SourceInventoryItem(
            source="HBE_PROFILES",
            field="evidence_level, target_hit_probability, expected_move_p50, time_to_target_p50, stability",
            availability="PARTIAL",
            historical_depth="computed on demand from KLP outcomes",
            record_count=0,
            update_frequency="ON_DEMAND",
            is_outcome_linked=True,
            currently_used_in_decisions=False,
            usage_status=OBSERVED_ONLY,
        ),
    ]
    return items


# ─────────────────────────────────────────────────────────────────────────────
# Data loaders
# ─────────────────────────────────────────────────────────────────────────────

def _load_rejection_records(db_path: Path) -> List[Dict[str, Any]]:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT symbol, strategy, trade_date, direction, market_regime,
                   vix_bucket, vix, decision_score, quality_score, quality_tier,
                   rejected_reason, price_at_rejection,
                   move_1d_pct, move_3d_pct, move_5d_pct,
                   max_favorable_move, max_adverse_move,
                   rejection_outcome, is_backfill
            FROM rejection_log
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _load_ct_decisions(db_path: Path) -> List[Dict[str, Any]]:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT d.symbol, d.strategy, d.confidence, d.decision,
                   d.rejection_reason, d.technical_score, d.risk_score,
                   d.macro_score, d.sentiment_score, d.regime_score,
                   d.position_modifier, d.ts, d.cycle_id,
                   c.regime, c.vix, c.breadth, c.pcr
            FROM ct_decisions d
            LEFT JOIN ct_cycles c ON d.cycle_id = c.cycle_id
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _load_klp_observations(klp_dir: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not klp_dir.exists():
        return records
    for f in sorted(klp_dir.glob("KLP_*.jsonl")):
        trading_date = f.stem.replace("KLP_", "")
        obs_map: Dict[str, Dict] = {}
        out_map: Dict[str, Dict] = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                et = r.get("event_type", "")
                oid = r.get("obs_id", "")
                if et == "KNOWLEDGE_OBSERVATION" and oid:
                    r["_trading_date"] = trading_date
                    obs_map[oid] = r
                elif et == "OUTCOME_UPDATE" and oid:
                    out_map[oid] = r
            except Exception:
                pass
        for oid, obs in obs_map.items():
            merged = dict(obs)
            if oid in out_map:
                merged.update({f"_out_{k}": v for k, v in out_map[oid].items()})
            records.append(merged)
    return records


def _load_regime_history(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Record normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_rejection(row: Dict[str, Any]) -> KnowledgeFusionRecord:
    sym  = (row.get("symbol") or "").upper().strip()
    dirn = (row.get("direction") or "BUY").upper()
    date_str = str(row.get("trade_date") or "")[:10]
    outcome_raw = row.get("rejection_outcome")
    outcome_avail = outcome_raw in ("CORRECT_REJECTION", "FALSE_REJECTION")

    missing: List[str] = []
    for f in ("move_1d_pct", "move_3d_pct", "move_5d_pct", "max_favorable_move", "max_adverse_move"):
        if row.get(f) is None:
            missing.append(f)

    return KnowledgeFusionRecord(
        fusion_id=f"REJ_{sym}_{date_str}_{dirn}_{uuid.uuid4().hex[:6]}",
        trading_date=date_str,
        symbol=sym,
        direction=dirn,
        sector=_sector(sym),
        regime=str(row.get("market_regime") or "").upper().replace("RANGING", "RANGE") or None,
        vix=_flt(row.get("vix")),
        decision_confidence=_flt(row.get("decision_score")),
        final_decision="REJECTED",
        rejection_reason=row.get("rejected_reason"),
        outcome_available=outcome_avail,
        move_1d_pct=_flt(row.get("move_1d_pct")),
        move_3d_pct=_flt(row.get("move_3d_pct")),
        move_5d_pct=_flt(row.get("move_5d_pct")),
        max_favorable_move=_flt(row.get("max_favorable_move")),
        max_adverse_move=_flt(row.get("max_adverse_move")),
        rejection_outcome=outcome_raw,
        missing_fields=missing,
        source_ids=["REJECTION_AUDIT_DB"],
        no_lookahead=True,
    )


def _normalise_ct_decision(row: Dict[str, Any]) -> KnowledgeFusionRecord:
    sym  = (row.get("symbol") or "").upper().strip()
    date_str = str(row.get("ts") or "")[:10]

    return KnowledgeFusionRecord(
        fusion_id=f"CT_{sym}_{date_str}_{uuid.uuid4().hex[:6]}",
        trading_date=date_str,
        symbol=sym,
        direction="BUY",      # ct_decisions does not store direction — default
        sector=_sector(sym),
        regime=str(row.get("regime") or "").upper() or None,
        vix=_flt(row.get("vix")),
        pcr=_flt(row.get("pcr")),
        breadth=_flt(row.get("breadth")),
        technical_score=_flt(row.get("technical_score")),
        risk_score=_flt(row.get("risk_score")),
        macro_score=_flt(row.get("macro_score")),
        sentiment_score=_flt(row.get("sentiment_score")),
        regime_agent_score=_flt(row.get("regime_score")),
        final_decision=str(row.get("decision") or "").upper() or None,
        decision_confidence=_flt(row.get("confidence")),
        rejection_reason=row.get("rejection_reason"),
        outcome_available=False,
        missing_fields=["move_1d_pct", "move_3d_pct", "move_5d_pct"],
        source_ids=["CONTROL_TOWER_DECISIONS"],
        no_lookahead=True,
    )


def _normalise_klp(row: Dict[str, Any]) -> KnowledgeFusionRecord:
    sym  = (row.get("symbol") or "").upper().strip()
    date_str = row.get("_trading_date") or row.get("trading_date") or ""
    dirn = (row.get("direction") or "BUY").upper()
    has_outcome = row.get("_out_first_event") in (
        "TARGET_HIT", "STOP_HIT", "OUTCOME_EXPIRED", "OUTCOME_AMBIGUOUS"
    )

    return KnowledgeFusionRecord(
        fusion_id=f"KLP_{row.get('obs_id', uuid.uuid4().hex[:8])}",
        trading_date=date_str,
        symbol=sym,
        direction=dirn,
        sector=_sector(sym),
        regime=str(row.get("regime") or "").upper() or None,
        scanner_confidence=_flt(row.get("scanner_confidence")),
        candidate_score=_flt(row.get("candidate_score")),
        knowledge_score=_flt(row.get("knowledge_score")),
        atr_pct=_flt(row.get("atr_pct")),
        knowledge_rr=_flt(row.get("knowledge_RR")),
        outcome_available=has_outcome,
        move_5d_pct=_flt(row.get("_out_t5_ret_pct")),
        target_hit=row.get("_out_target_hit"),
        stop_hit=row.get("_out_stop_hit"),
        missing_fields=[f for f in ("vix", "pcr", "breadth", "technical_score") if not row.get(f)],
        source_ids=["KLP_OBSERVATION"],
        no_lookahead=True,
    )


def _flt(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Multi-angle analysis helpers
# ─────────────────────────────────────────────────────────────────────────────

def _angle_insufficient(name: str) -> AngleResult:
    return AngleResult(
        angle_name=name, sample_count=0, metrics={},
        evidence_level=7, confidence=0.0, summary="insufficient_data"
    )


def _compute_outcome_angle(
    records: List[KnowledgeFusionRecord],
    angle_name: str,
) -> AngleResult:
    """Compute statistics from outcome-linked records for one angle."""
    with_outcome = [r for r in records if r.outcome_available]
    n = len(with_outcome)
    if n == 0:
        return _angle_insufficient(angle_name)

    moves = [r.directional_move_5d for r in with_outcome if r.directional_move_5d is not None]
    fav_n  = sum(1 for m in moves if m > 0)
    tgt_n  = sum(1 for r in with_outcome if r.target_hit)
    stp_n  = sum(1 for r in with_outcome if r.stop_hit)
    false_neg_n = sum(1 for r in with_outcome
                      if r.rejection_outcome == "FALSE_REJECTION")
    corr_rej_n  = sum(1 for r in with_outcome
                      if r.rejection_outcome == "CORRECT_REJECTION")

    metrics = {
        "sample_count":         n,
        "positive_move_rate":   _safe_rate(fav_n, len(moves)) if moves else None,
        "target_hit_rate":      _safe_rate(tgt_n, n),
        "stop_hit_rate":        _safe_rate(stp_n, n),
        "false_rejection_rate": _safe_rate(false_neg_n, n),
        "correct_rejection_rate": _safe_rate(corr_rej_n, n),
        "median_move":          _pct(moves, 50),
        "p25_move":             _pct(moves, 25),
        "p75_move":             _pct(moves, 75),
        "max_favorable_p50":    _pct([r.max_favorable_move for r in with_outcome if r.max_favorable_move is not None], 50),
        "max_adverse_p50":      _pct([r.max_adverse_move for r in with_outcome if r.max_adverse_move is not None], 50),
    }

    from opportunity_engine.hbe_models import evidence_tier as _tier
    tier = _tier(n)
    confidence = round(min(tier / 6.0 * 0.8 + 0.1, 1.0), 4)

    return AngleResult(
        angle_name=angle_name,
        sample_count=n,
        metrics=metrics,
        evidence_level=max(1, 7 - tier),
        confidence=confidence,
        summary=f"{n} outcomes | move_p50={metrics['median_move']} | tgt_hit={metrics['target_hit_rate']}",
    )


def _compute_market_angle(records: List[KnowledgeFusionRecord]) -> AngleResult:
    """Market angle: regime, VIX, PCR, breadth statistics."""
    n = len(records)
    if n == 0:
        return _angle_insufficient("MARKET")

    vix_vals    = [r.vix for r in records if r.vix is not None]
    pcr_vals    = [r.pcr for r in records if r.pcr is not None]
    breadth_vals = [r.breadth for r in records if r.breadth is not None]
    regimes     = [r.regime for r in records if r.regime]

    regime_dist: Dict[str, int] = {}
    for reg in regimes:
        regime_dist[reg] = regime_dist.get(reg, 0) + 1

    metrics = {
        "sample_count":      n,
        "regime_distribution": regime_dist,
        "dominant_regime":   max(regime_dist, key=regime_dist.get) if regime_dist else None,
        "vix_median":        _pct(vix_vals, 50),
        "pcr_median":        _pct(pcr_vals, 50),
        "breadth_median":    _pct(breadth_vals, 50),
    }
    return AngleResult(
        angle_name="MARKET",
        sample_count=n,
        metrics=metrics,
        evidence_level=4 if n >= 20 else 6,
        confidence=min(n / 100, 0.8),
        summary=f"dominant_regime={metrics['dominant_regime']} vix_p50={metrics['vix_median']}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Contradiction detection
# ─────────────────────────────────────────────────────────────────────────────

def _detect_contradictions(record: KnowledgeFusionRecord) -> List[ContradictionRecord]:
    contradictions: List[ContradictionRecord] = []

    # Contradiction 1: Scanner says strong BUY but VIX is elevated (>25 = uncertain)
    if (record.knowledge_score is not None and record.knowledge_score > 0.6
            and record.vix is not None and record.vix > 25.0
            and record.direction == "BUY"):
        strength = min((record.vix - 25.0) / 20.0, 1.0)
        contradictions.append(ContradictionRecord(
            contradiction_id=f"CONT_{record.fusion_id}_VIX",
            fusion_id=record.fusion_id,
            sources=["KLP_OBSERVATION", "MARKET_SNAPSHOT"],
            contradiction_type="STRENGTH",
            details={
                "knowledge_score": record.knowledge_score,
                "vix": record.vix,
                "description": "Strong BUY signal during elevated VIX"
            },
            strength=round(strength, 4),
            historical_resolution=None,
            outcome=None,
        ))

    # Contradiction 2: BUY signal in BEAR regime
    if record.direction == "BUY" and record.regime == "BEAR":
        contradictions.append(ContradictionRecord(
            contradiction_id=f"CONT_{record.fusion_id}_REGIME",
            fusion_id=record.fusion_id,
            sources=["KLP_OBSERVATION", "REGIME"],
            contradiction_type="REGIME",
            details={
                "direction": record.direction,
                "regime": record.regime,
                "description": "BUY signal during BEAR regime"
            },
            strength=0.7,
            historical_resolution=None,
            outcome=None,
        ))

    # Contradiction 3: High technical score but low risk score
    if (record.technical_score is not None and record.risk_score is not None
            and record.technical_score > 7.0 and record.risk_score < 3.0):
        strength = min((record.technical_score - record.risk_score) / 10.0, 1.0)
        contradictions.append(ContradictionRecord(
            contradiction_id=f"CONT_{record.fusion_id}_TECH_RISK",
            fusion_id=record.fusion_id,
            sources=["TECHNICAL_AGENT", "RISK_AGENT"],
            contradiction_type="STRENGTH",
            details={
                "technical_score": record.technical_score,
                "risk_score": record.risk_score,
                "description": "High technical confidence contradicted by low risk score"
            },
            strength=round(strength, 4),
            historical_resolution=None,
            outcome=None,
        ))

    return contradictions


# ─────────────────────────────────────────────────────────────────────────────
# Redundancy detection
# ─────────────────────────────────────────────────────────────────────────────

def _detect_redundancies(records: List[KnowledgeFusionRecord]) -> List[RedundancyRecord]:
    redundancies: List[RedundancyRecord] = []

    # Check if technical_score and regime_agent_score are correlated
    # across ct_decisions records (both from debate — potentially redundant)
    tech_vals = [r.technical_score for r in records
                 if r.technical_score is not None and r.regime_agent_score is not None]
    reg_vals  = [r.regime_agent_score for r in records
                 if r.technical_score is not None and r.regime_agent_score is not None]

    if len(tech_vals) >= 10:
        corr = _pearson(tech_vals, reg_vals)
        if corr is not None and abs(corr) > 0.7:
            redundancies.append(RedundancyRecord(
                redundancy_id=f"REDUND_{uuid.uuid4().hex[:8]}",
                sources=["TECHNICAL_AGENT", "REGIME_AGENT"],
                field_names=["technical_score", "regime_agent_score"],
                correlation=round(corr, 4),
                recommendation="DEDUPLICATE",
            ))

    # candidate_score and knowledge_score are derived from the same scanner output
    cs_vals = [r.candidate_score for r in records
               if r.candidate_score is not None and r.knowledge_score is not None]
    ks_vals = [r.knowledge_score for r in records
               if r.candidate_score is not None and r.knowledge_score is not None]

    if len(cs_vals) >= 5:
        corr2 = _pearson(cs_vals, ks_vals)
        if corr2 is not None and abs(corr2) > 0.8:
            redundancies.append(RedundancyRecord(
                redundancy_id=f"REDUND_{uuid.uuid4().hex[:8]}",
                sources=["KLP_OBSERVATION"],
                field_names=["candidate_score", "knowledge_score"],
                correlation=round(corr2, 4),
                recommendation="USE_PRIMARY",
            ))

    return redundancies


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 3:
        return None
    try:
        mx, my = sum(xs) / n, sum(ys) / n
        num   = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        denom = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
        return num / denom if denom > 0 else 0.0
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Relationship discovery
# ─────────────────────────────────────────────────────────────────────────────

def _discover_relationships(
    records: List[KnowledgeFusionRecord],
    ref_date: Optional[date] = None,
) -> List[RelationshipCandidate]:
    """
    Discover feature combinations with statistically meaningful outcome patterns.
    Only relationships with outcome-linked records are computed.
    """
    ref = ref_date or date.today()
    outcome_recs = [r for r in records if r.outcome_available and r.directional_move_5d is not None]

    if not outcome_recs:
        return []

    candidates: List[RelationshipCandidate] = []

    # ── Relationship 1: regime × direction ────────────────────────────────────
    for regime in ("BULL", "BEAR", "RANGE", "VOLATILE"):
        for dirn in ("BUY", "SELL", "SHORT"):
            subset = [r for r in outcome_recs
                      if r.regime == regime and r.direction == dirn]
            if len(subset) >= 5:
                candidates.append(_make_rel(
                    features=["regime", "direction"],
                    conditions={"regime": regime, "direction": dirn},
                    subset=subset, ref=ref,
                ))

    # ── Relationship 2: sector × direction ────────────────────────────────────
    sectors = set(r.sector for r in outcome_recs if r.sector != "UNKNOWN")
    for sec in sectors:
        for dirn in ("BUY", "SELL", "SHORT"):
            subset = [r for r in outcome_recs
                      if r.sector == sec and r.direction == dirn]
            if len(subset) >= 5:
                candidates.append(_make_rel(
                    features=["sector", "direction"],
                    conditions={"sector": sec, "direction": dirn},
                    subset=subset, ref=ref,
                ))

    # ── Relationship 3: vix_bucket × direction ────────────────────────────────
    for vix_lo, vix_hi, label in [(0, 15, "LOW"), (15, 25, "MEDIUM"), (25, 40, "HIGH"), (40, 999, "EXTREME")]:
        for dirn in ("BUY", "SELL", "SHORT"):
            subset = [r for r in outcome_recs
                      if r.vix is not None
                      and vix_lo <= r.vix < vix_hi
                      and r.direction == dirn]
            if len(subset) >= 5:
                candidates.append(_make_rel(
                    features=["vix_bucket", "direction"],
                    conditions={"vix_bucket": label, "direction": dirn},
                    subset=subset, ref=ref,
                ))

    # ── Relationship 4: regime × sector × direction ───────────────────────────
    for regime in ("BULL", "BEAR", "RANGE"):
        for sec in sectors:
            for dirn in ("BUY",):
                subset = [r for r in outcome_recs
                          if r.regime == regime and r.sector == sec
                          and r.direction == dirn]
                if len(subset) >= 5:
                    candidates.append(_make_rel(
                        features=["regime", "sector", "direction"],
                        conditions={"regime": regime, "sector": sec, "direction": dirn},
                        subset=subset, ref=ref,
                    ))

    return sorted(candidates, key=lambda c: c.decision_usefulness, reverse=True)


def _make_rel(
    features: List[str],
    conditions: Dict[str, Any],
    subset: List[KnowledgeFusionRecord],
    ref: date,
) -> RelationshipCandidate:
    moves = [r.directional_move_5d for r in subset if r.directional_move_5d is not None]
    n     = len(subset)
    dates = [r.trading_date for r in subset]
    ess   = round(_ess(dates, ref), 2)
    fav_n = sum(1 for m in moves if m > 0)
    tgt_n = sum(1 for r in subset if r.target_hit)
    stp_n = sum(1 for r in subset if r.stop_hit)

    pos_rate  = _safe_rate(fav_n, len(moves)) if moves else None
    tgt_rate  = _safe_rate(tgt_n, n)
    stp_rate  = _safe_rate(stp_n, n)
    med_move  = _pct(moves, 50)
    p25       = _pct(moves, 25)
    p75       = _pct(moves, 75)

    # Stability: compare first half vs second half
    sorted_sub = sorted(subset, key=lambda r: r.trading_date)
    half = len(sorted_sub) // 2
    if half >= 3:
        h1 = [r.directional_move_5d for r in sorted_sub[:half] if r.directional_move_5d is not None]
        h2 = [r.directional_move_5d for r in sorted_sub[half:] if r.directional_move_5d is not None]
        if h1 and h2:
            mean1, mean2 = sum(h1) / len(h1), sum(h2) / len(h2)
            diff = abs(mean1 - mean2)
            stability = "stable" if diff < 1.0 else ("developing" if diff < 2.5 else "unstable")
        else:
            stability = "insufficient_data"
    else:
        stability = "insufficient_data"

    # Decision usefulness: penalise small samples and unstable
    from opportunity_engine.hbe_models import evidence_tier as _tier
    tier = _tier(n)
    stab_map = {"stable": 1.0, "developing": 0.6, "unstable": 0.2, "insufficient_data": 0.1}
    du = round((tier / 6.0) * 0.6 + stab_map.get(stability, 0.1) * 0.4, 4)

    return RelationshipCandidate(
        rel_id=f"REL_{uuid.uuid4().hex[:8]}",
        features=features,
        conditions=conditions,
        sample_count=n,
        ess=ess,
        positive_rate=pos_rate,
        target_hit_rate=tgt_rate,
        stop_hit_rate=stp_rate,
        median_move=med_move,
        p25_move=p25,
        p75_move=p75,
        median_time_to_move=None,    # not available in rejection_audit
        stability=stability,
        recency_weight=round(ess / max(n, 1), 4),
        decision_usefulness=du,
        out_of_sample_status=OOS_NOT_TESTED,
        promotion_status=CANDIDATE,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Selection analysis
# ─────────────────────────────────────────────────────────────────────────────

def _analyse_selection(records: List[KnowledgeFusionRecord]) -> List[SelectionAnalysisRecord]:
    analyses: List[SelectionAnalysisRecord] = []
    for r in records:
        selected = (r.final_decision == "APPROVED")
        dm = r.directional_move_5d
        if not r.outcome_available or dm is None:
            cls = OUTCOME_UNKNOWN
        elif selected:
            cls = TRUE_POSITIVE if dm > 0 else FALSE_POSITIVE
        else:
            if r.rejection_outcome == "FALSE_REJECTION":
                cls = FALSE_NEGATIVE
            elif r.rejection_outcome == "CORRECT_REJECTION":
                cls = TRUE_NEGATIVE
            elif dm < 0:
                cls = TRUE_NEGATIVE
            elif dm > 0:
                cls = FALSE_NEGATIVE
            else:
                cls = OUTCOME_UNKNOWN

        analyses.append(SelectionAnalysisRecord(
            analysis_id=f"SEL_{r.fusion_id}",
            trading_date=r.trading_date,
            symbol=r.symbol,
            direction=r.direction,
            selected=selected,
            outcome_available=r.outcome_available,
            move_5d_pct=r.move_5d_pct,
            directional_move=dm,
            classification=cls,
            rejection_reason=r.rejection_reason,
            no_lookahead=True,
        ))
    return analyses


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge object builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_knowledge_objects(
    relationships: List[RelationshipCandidate],
) -> List[KnowledgeObject]:
    objects: List[KnowledgeObject] = []
    now = datetime.now(timezone.utc).isoformat()
    for rel in relationships:
        if rel.sample_count < 5:
            continue
        scope = _rel_scope(rel.features)
        statement = _rel_statement(rel)
        ko = KnowledgeObject(
            knowledge_id=f"KO_{rel.rel_id}",
            knowledge_type="RELATIONSHIP",
            statement=statement,
            scope=scope,
            conditions=rel.conditions,
            supporting_sources=["REJECTION_AUDIT_DB"],
            supporting_observation_ids=[],
            sample_count=rel.sample_count,
            ess=rel.ess,
            evidence_level=max(1, 7 - min(rel.sample_count // 50, 6)),
            stability=rel.stability,
            recency=rel.recency_weight,
            confidence=min(rel.decision_usefulness + 0.1, 1.0),
            contradiction_status=CONTRADICTION_NONE,
            out_of_sample_status=OOS_NOT_TESTED,
            decision_usefulness=rel.decision_usefulness,
            created_at=now,
            updated_at=now,
            promotion_status=CANDIDATE,
        )
        # Attempt auto-promotion from CANDIDATE → OBSERVED
        ko.promote()
        objects.append(ko)
    return objects


def _rel_scope(features: List[str]) -> str:
    if "symbol" in features:
        return "SYMBOL"
    if "sector" in features:
        return "SECTOR"
    if "regime" in features:
        return "REGIME"
    return "BROAD"


def _rel_statement(rel: RelationshipCandidate) -> str:
    cond_str = " + ".join(f"{k}={v}" for k, v in rel.conditions.items())
    move_str = f"{rel.median_move:+.2f}%" if rel.median_move is not None else "unknown"
    tgt_str  = f"{rel.target_hit_rate:.1%}" if rel.target_hit_rate is not None else "unknown"
    return (f"When {cond_str}: median_move={move_str}, "
            f"target_hit_rate={tgt_str} (n={rel.sample_count})")


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge value scoring
# ─────────────────────────────────────────────────────────────────────────────

def _score_knowledge_value(ko: KnowledgeObject) -> KnowledgeValueScore:
    from opportunity_engine.hbe_models import evidence_tier as _tier
    tier = _tier(ko.sample_count)
    evidence_strength = tier / 6.0
    stab_map = {"stable": 1.0, "developing": 0.6, "unstable": 0.2, "insufficient_data": 0.0}
    stability_s  = stab_map.get(ko.stability, 0.0)
    recency_s    = ko.recency
    sample_qual  = min(ko.ess / max(ko.sample_count, 1), 1.0)
    cross_val    = 0.5          # baseline — cross-validation not yet available
    oos_map      = {OOS_NOT_TESTED: 0.0, OOS_TESTED: 0.4, OOS_PASSED: 1.0, OOS_FAILED: 0.0}
    oos_s        = oos_map.get(ko.out_of_sample_status, 0.0)
    relevance    = ko.decision_usefulness
    incremental  = 0.5          # baseline — incremental value not yet measurable

    w = KnowledgeValueScore(
        knowledge_id=ko.knowledge_id,
        evidence_strength=round(evidence_strength, 4),
        stability_score=round(stability_s, 4),
        recency_score=round(recency_s, 4),
        sample_quality=round(sample_qual, 4),
        cross_validation=round(cross_val, 4),
        out_of_sample=round(oos_s, 4),
        decision_relevance=round(relevance, 4),
        incremental_value=round(incremental, 4),
        composite_score=0.0,
    )
    w.composite_score = round(
        w.W_EVIDENCE    * w.evidence_strength +
        w.W_STABILITY   * w.stability_score   +
        w.W_RECENCY     * w.recency_score      +
        w.W_QUALITY     * w.sample_quality     +
        w.W_CROSS_VAL   * w.cross_validation   +
        w.W_OOS         * w.out_of_sample      +
        w.W_RELEVANCE   * w.decision_relevance +
        w.W_INCREMENTAL * w.incremental_value,
        4,
    )
    return w


# ─────────────────────────────────────────────────────────────────────────────
# Output writers (append-only)
# ─────────────────────────────────────────────────────────────────────────────

def _append_jsonl(path: Path, records: List[Any]) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in records:
            d = r.as_dict() if hasattr(r, "as_dict") else r
            fh.write(json.dumps(d) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeFusionEngine:
    """
    KLP-004 — Knowledge Fusion Engine.

    Usage:
        kfe = KnowledgeFusionEngine()
        result = kfe.run_fusion()

    broker_calls = 0 always.
    """

    def __init__(
        self,
        data_dir:       Optional[Path] = None,
        output_dir:     Optional[Path] = None,
        reference_date: Optional[date] = None,
    ) -> None:
        self._data_dir    = data_dir    or _DATA
        self._output_dir  = output_dir  or _KF_DIR
        self._ref_date    = reference_date or date.today()
        self.broker_calls = 0
        self.orders       = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def build_source_inventory(self) -> List[SourceInventoryItem]:
        return build_source_inventory(self._data_dir)

    def load_fusion_records(self) -> List[KnowledgeFusionRecord]:
        """
        Load and normalise all available sources into KnowledgeFusionRecord list.
        """
        records: List[KnowledgeFusionRecord] = []

        rej = _load_rejection_records(self._data_dir / "rejection_audit.db")
        for row in rej:
            records.append(_normalise_rejection(row))

        ct  = _load_ct_decisions(self._data_dir / "control_tower.db")
        for row in ct:
            records.append(_normalise_ct_decision(row))

        klp = _load_klp_observations(self._data_dir / "klp")
        for row in klp:
            records.append(_normalise_klp(row))

        return records

    def analyse_record(
        self,
        record: KnowledgeFusionRecord,
        all_records: Optional[List[KnowledgeFusionRecord]] = None,
    ) -> MultiAngleView:
        """
        Produce a 10-angle view for one fusion record.
        Uses all_records for population-level context angles.
        """
        pool = all_records or []

        angles: Dict[str, AngleResult] = {}

        # A. STOCK angle — same symbol + direction outcomes
        stock_recs = [r for r in pool
                      if r.symbol == record.symbol and r.direction == record.direction
                      and r.outcome_available]
        angles["STOCK"] = _compute_outcome_angle(stock_recs, "STOCK")

        # B. MARKET angle — same regime context
        regime_recs = [r for r in pool if r.regime and r.regime == record.regime]
        angles["MARKET"] = _compute_market_angle(regime_recs)

        # C. SECTOR angle — same sector + direction + regime
        sector_recs = [r for r in pool
                       if r.sector == record.sector and r.direction == record.direction
                       and r.outcome_available]
        angles["SECTOR"] = _compute_outcome_angle(sector_recs, "SECTOR")

        # D. VOLATILITY angle — same VIX bucket
        vix_recs = _vix_bucket_records(record.vix, pool)
        angles["VOLATILITY"] = _compute_outcome_angle(vix_recs, "VOLATILITY")

        # E. DIRECTION angle — all records with same direction + outcomes
        dir_recs = [r for r in pool
                    if r.direction == record.direction and r.outcome_available]
        angles["DIRECTION"] = _compute_outcome_angle(dir_recs, "DIRECTION")

        # F. MAGNITUDE angle — expected move vs actual distribution
        angles["MAGNITUDE"] = _magnitude_angle(record, pool)

        # G. TIME angle — T+N horizon statistics
        angles["TIME"] = _time_angle(record, pool)

        # H. RISK angle — stop probability, adverse excursion
        angles["RISK"] = _risk_angle(pool, record.direction)

        # I. SELECTION angle — selected vs rejected outcome comparison
        angles["SELECTION"] = _selection_angle(pool, record.direction)

        # J. COUNTERFACTUAL angle — what happened to rejected candidates
        angles["COUNTERFACTUAL"] = _counterfactual_angle(pool, record.direction)

        # Overall signal
        confidence_vals = [a.confidence for a in angles.values() if a.confidence > 0]
        if not confidence_vals:
            overall = "INSUFFICIENT"
        else:
            avg_conf = sum(confidence_vals) / len(confidence_vals)
            low_conf = sum(1 for c in confidence_vals if c < 0.2)
            overall = "INSUFFICIENT" if avg_conf < 0.2 else (
                "AGREE" if avg_conf > 0.6 else (
                    "DISAGREE" if low_conf > len(confidence_vals) / 2 else "MIXED"
                )
            )

        contradictions = _detect_contradictions(record)

        return MultiAngleView(
            fusion_id=record.fusion_id,
            symbol=record.symbol,
            direction=record.direction,
            trading_date=record.trading_date,
            angles=angles,
            overall_signal=overall,
            contradiction_detected=len(contradictions) > 0,
            no_lookahead=True,
        )

    def discover_relationships(
        self,
        records: Optional[List[KnowledgeFusionRecord]] = None,
    ) -> List[RelationshipCandidate]:
        pool = records if records is not None else self.load_fusion_records()
        return _discover_relationships(pool, self._ref_date)

    def detect_contradictions(
        self,
        record: KnowledgeFusionRecord,
    ) -> List[ContradictionRecord]:
        return _detect_contradictions(record)

    def detect_redundancies(
        self,
        records: List[KnowledgeFusionRecord],
    ) -> List[RedundancyRecord]:
        return _detect_redundancies(records)

    def analyse_selection(
        self,
        records: List[KnowledgeFusionRecord],
    ) -> List[SelectionAnalysisRecord]:
        return _analyse_selection(records)

    def build_knowledge_objects(
        self,
        relationships: List[RelationshipCandidate],
    ) -> List[KnowledgeObject]:
        return _build_knowledge_objects(relationships)

    def score_knowledge_value(self, ko: KnowledgeObject) -> KnowledgeValueScore:
        return _score_knowledge_value(ko)

    def run_fusion(self) -> Dict[str, Any]:
        """
        Full fusion pipeline: load → analyse → discover → contradiction → output.
        Returns a summary dict. Never raises.
        """
        try:
            return self._run_impl()
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "broker_calls": 0, "orders": 0}

    # ─────────────────────────────────────────────────────────────────────────
    # Internal implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _run_impl(self) -> Dict[str, Any]:
        # 1. Source inventory
        inventory = self.build_source_inventory()

        # 2. Load records
        records = self.load_fusion_records()

        # 3. Discover relationships
        relationships = _discover_relationships(records, self._ref_date)

        # 4. Detect redundancies
        redundancies = _detect_redundancies(records)

        # 5. Detect contradictions on all records
        contradictions: List[ContradictionRecord] = []
        for r in records:
            contradictions.extend(_detect_contradictions(r))

        # 6. Selection analysis
        selection = _analyse_selection(records)

        # 7. Build knowledge objects
        knowledge_objects = _build_knowledge_objects(relationships)

        # 8. Score knowledge value
        kv_scores = [_score_knowledge_value(ko) for ko in knowledge_objects]

        # 9. Write output files (append-only)
        _append_jsonl(self._output_dir / "source_inventory.jsonl",
                      [i.as_dict() for i in inventory])
        _append_jsonl(self._output_dir / "relationship_candidates.jsonl",  relationships)
        _append_jsonl(self._output_dir / "contradictions.jsonl",           contradictions)
        _append_jsonl(self._output_dir / "knowledge_objects.jsonl",        knowledge_objects)
        _append_jsonl(self._output_dir / "selection_analysis.jsonl",       selection)
        _append_jsonl(self._output_dir / "knowledge_value.jsonl",          kv_scores)

        # Selection summary
        sel_count = {cls: 0 for cls in (TRUE_POSITIVE, FALSE_POSITIVE, TRUE_NEGATIVE, FALSE_NEGATIVE, OUTCOME_UNKNOWN)}
        for s in selection:
            sel_count[s.classification] = sel_count.get(s.classification, 0) + 1

        return {
            "status":                "OK",
            "fusion_records":        len(records),
            "source_inventory":      len(inventory),
            "relationships_found":   len(relationships),
            "contradictions_found":  len(contradictions),
            "redundancies_found":    len(redundancies),
            "knowledge_objects":     len(knowledge_objects),
            "selection_summary":     sel_count,
            "broker_calls":          0,
            "orders":                0,
            "paper_trading":         True,
            "no_lookahead":          True,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Additional angle helpers
# ─────────────────────────────────────────────────────────────────────────────

def _vix_bucket_records(
    vix: Optional[float],
    pool: List[KnowledgeFusionRecord],
) -> List[KnowledgeFusionRecord]:
    if vix is None:
        return []
    lo = (0, 15, 25, 40)[sum(vix > t for t in (15, 25, 40))]
    hi = (15, 25, 40, 999)[sum(vix > t for t in (15, 25, 40))]
    return [r for r in pool if r.vix is not None and lo <= r.vix < hi and r.outcome_available]


def _magnitude_angle(
    record: KnowledgeFusionRecord,
    pool: List[KnowledgeFusionRecord],
) -> AngleResult:
    """Compare expected move (ATR proxy) vs actual move distribution."""
    name = "MAGNITUDE"
    outcome_recs = [r for r in pool if r.outcome_available and r.directional_move_5d is not None]
    if not outcome_recs:
        return _angle_insufficient(name)

    favs = [r.max_favorable_move for r in outcome_recs if r.max_favorable_move is not None]
    advs = [abs(r.max_adverse_move) for r in outcome_recs if r.max_adverse_move is not None]
    exp_moves = [r.directional_move_5d for r in outcome_recs if r.directional_move_5d is not None]

    metrics = {
        "sample_count":          len(outcome_recs),
        "max_favorable_p50":     _pct(favs, 50),
        "max_adverse_p50":       _pct(advs, 50),
        "expected_move_p50":     _pct(exp_moves, 50),
        "expected_move_p25":     _pct(exp_moves, 25),
        "expected_move_p75":     _pct(exp_moves, 75),
        "prob_1pct":             _safe_rate(sum(1 for m in exp_moves if m >= 1.0), len(exp_moves)),
        "prob_2pct":             _safe_rate(sum(1 for m in exp_moves if m >= 2.0), len(exp_moves)),
        "prob_5pct":             _safe_rate(sum(1 for m in exp_moves if m >= 5.0), len(exp_moves)),
        "current_atr_pct":       record.atr_pct,
    }
    n = len(outcome_recs)
    from opportunity_engine.hbe_models import evidence_tier as _tier
    conf = min(_tier(n) / 6.0 * 0.9, 0.9)
    return AngleResult(
        angle_name=name, sample_count=n, metrics=metrics,
        evidence_level=max(1, 7 - _tier(n)),
        confidence=conf,
        summary=f"exp_move_p50={metrics['expected_move_p50']} fav_p50={metrics['max_favorable_p50']}",
    )


def _time_angle(
    record: KnowledgeFusionRecord,
    pool: List[KnowledgeFusionRecord],
) -> AngleResult:
    """T+1/T+3/T+5 return distributions."""
    name = "TIME"
    outcome_recs = [r for r in pool if r.outcome_available]
    n = len(outcome_recs)
    if n < 5:
        return _angle_insufficient(name)

    m1 = [r.move_1d_pct for r in outcome_recs if r.move_1d_pct is not None]
    m3 = [r.move_3d_pct for r in outcome_recs if r.move_3d_pct is not None]
    m5 = [r.move_5d_pct for r in outcome_recs if r.move_5d_pct is not None]

    metrics = {
        "sample_count": n,
        "t1_p25": _pct(m1, 25), "t1_p50": _pct(m1, 50), "t1_p75": _pct(m1, 75),
        "t3_p25": _pct(m3, 25), "t3_p50": _pct(m3, 50), "t3_p75": _pct(m3, 75),
        "t5_p25": _pct(m5, 25), "t5_p50": _pct(m5, 50), "t5_p75": _pct(m5, 75),
    }
    from opportunity_engine.hbe_models import evidence_tier as _tier
    conf = min(_tier(n) / 6.0 * 0.8, 0.8)
    return AngleResult(
        angle_name=name, sample_count=n, metrics=metrics,
        evidence_level=max(1, 7 - _tier(n)), confidence=conf,
        summary=f"t1_p50={metrics['t1_p50']} t3_p50={metrics['t3_p50']} t5_p50={metrics['t5_p50']}",
    )


def _risk_angle(
    pool: List[KnowledgeFusionRecord],
    direction: str,
) -> AngleResult:
    """Risk angle: adverse excursion and stop probability."""
    name = "RISK"
    outcome_recs = [r for r in pool
                    if r.outcome_available and r.direction == direction
                    and r.max_adverse_move is not None]
    n = len(outcome_recs)
    if n < 5:
        return _angle_insufficient(name)

    adv = [abs(r.max_adverse_move) for r in outcome_recs]
    stp = [r.stop_hit for r in outcome_recs if r.stop_hit is not None]
    metrics = {
        "sample_count":    n,
        "adverse_p50":     _pct(adv, 50),
        "adverse_p75":     _pct(adv, 75),
        "stop_hit_rate":   _safe_rate(sum(stp), len(stp)) if stp else None,
    }
    from opportunity_engine.hbe_models import evidence_tier as _tier
    conf = min(_tier(n) / 6.0 * 0.8, 0.8)
    return AngleResult(
        angle_name=name, sample_count=n, metrics=metrics,
        evidence_level=max(1, 7 - _tier(n)), confidence=conf,
        summary=f"adverse_p50={metrics['adverse_p50']} stop_rate={metrics['stop_hit_rate']}",
    )


def _selection_angle(
    pool: List[KnowledgeFusionRecord],
    direction: str,
) -> AngleResult:
    """Compare approved vs rejected outcomes."""
    name = "SELECTION"
    approved = [r for r in pool
                if r.final_decision == "APPROVED" and r.outcome_available and r.directional_move_5d is not None]
    rejected  = [r for r in pool
                 if r.final_decision == "REJECTED" and r.outcome_available and r.directional_move_5d is not None]

    if not approved and not rejected:
        return _angle_insufficient(name)

    a_moves = [r.directional_move_5d for r in approved if r.directional_move_5d is not None]
    r_moves = [r.directional_move_5d for r in rejected  if r.directional_move_5d is not None]

    metrics = {
        "approved_count":         len(approved),
        "rejected_count":         len(rejected),
        "approved_pos_rate":      _safe_rate(sum(1 for m in a_moves if m > 0), len(a_moves)) if a_moves else None,
        "rejected_pos_rate":      _safe_rate(sum(1 for m in r_moves if m > 0), len(r_moves)) if r_moves else None,
        "approved_median_move":   _pct(a_moves, 50),
        "rejected_median_move":   _pct(r_moves, 50),
        "false_rejection_count":  sum(1 for r in rejected if r.rejection_outcome == "FALSE_REJECTION"),
        "correct_rejection_count": sum(1 for r in rejected if r.rejection_outcome == "CORRECT_REJECTION"),
    }

    n = len(approved) + len(rejected)
    from opportunity_engine.hbe_models import evidence_tier as _tier
    conf = min(_tier(n) / 6.0 * 0.8, 0.8)
    return AngleResult(
        angle_name=name, sample_count=n, metrics=metrics,
        evidence_level=max(1, 7 - _tier(n)), confidence=conf,
        summary=(
            f"approved_pos={metrics['approved_pos_rate']} "
            f"rejected_pos={metrics['rejected_pos_rate']} "
            f"false_rejections={metrics['false_rejection_count']}"
        ),
    )


def _counterfactual_angle(
    pool: List[KnowledgeFusionRecord],
    direction: str,
) -> AngleResult:
    """
    Counterfactual: what happened to candidates the system rejected?
    FALSE_REJECTION = rejected but moved favourably (missed opportunity).
    """
    name = "COUNTERFACTUAL"
    rejected = [r for r in pool
                if r.final_decision == "REJECTED"
                and r.outcome_available
                and r.direction == direction]
    n = len(rejected)
    if n < 5:
        return _angle_insufficient(name)

    false_rej = [r for r in rejected if r.rejection_outcome == "FALSE_REJECTION"]
    corr_rej  = [r for r in rejected if r.rejection_outcome == "CORRECT_REJECTION"]

    fr_moves = [r.directional_move_5d for r in false_rej if r.directional_move_5d is not None]
    cr_moves = [r.directional_move_5d for r in corr_rej  if r.directional_move_5d is not None]

    metrics = {
        "total_rejected":         n,
        "false_rejection_count":  len(false_rej),
        "correct_rejection_count": len(corr_rej),
        "false_rejection_rate":   _safe_rate(len(false_rej), n),
        "false_rej_median_move":  _pct(fr_moves, 50),
        "correct_rej_median_move": _pct(cr_moves, 50),
        "missed_opportunity_p50": _pct(fr_moves, 50),
        "missed_opportunity_p75": _pct(fr_moves, 75),
    }
    from opportunity_engine.hbe_models import evidence_tier as _tier
    conf = min(_tier(n) / 6.0 * 0.8, 0.8)
    return AngleResult(
        angle_name=name, sample_count=n, metrics=metrics,
        evidence_level=max(1, 7 - _tier(n)), confidence=conf,
        summary=(
            f"false_rejection_rate={metrics['false_rejection_rate']} "
            f"missed_move_p50={metrics['missed_opportunity_p50']}"
        ),
    )

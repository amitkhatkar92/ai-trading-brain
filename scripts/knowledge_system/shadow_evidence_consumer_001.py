"""
scripts/knowledge_system/shadow_evidence_consumer_001.py
=========================================================
Stage 1 — Shadow Evidence Consumer (KSL-001).

Reads new SHADOW_CANDIDATE records from the shadow JSONL (append-only, never
overwrites), classifies each candidate, and appends classified EvidenceRecords
to data/shadow_evidence_ledger.jsonl.

Properties:
  - restart safe: picks up from last processed byte offset
  - idempotent: deduplicated on run_id+symbol+trade_date+direction
  - append-only: never mutates existing records
  - production-isolated: no broker calls, no orders, no CandidateStore writes
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .ksl_models import (
    Classification,
    EvidenceRecord,
    KSLEventType,
    KSLState,
    MissReason,
)

ROOT = Path(__file__).resolve().parent.parent.parent

SHADOW_JSONL     = ROOT / "data" / "logs" / "final_trading_architecture_shadow_001.jsonl"
LEDGER_PATH      = ROOT / "data" / "shadow_evidence_ledger.jsonl"
KNOWLEDGE_LEDGER = ROOT / "data" / "knowledge_evidence_ledger.jsonl"
STATE_PATH       = ROOT / "data" / "ksl" / "ksl_state.json"

# Classify as RANKING_MISS / FALSE_REJECT only when move is meaningful
GE2_THRESHOLD = 2.0  # |t1_ret_pct| threshold


# ─────────────────────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────────────────────


def load_state() -> KSLState:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return KSLState.from_dict(json.load(f))
    return KSLState()


def save_state(state: KSLState) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state.to_dict(), f, indent=2)
    os.replace(tmp, STATE_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication key
# ─────────────────────────────────────────────────────────────────────────────


def _dedup_key(rec: Dict) -> str:
    return f"{rec.get('run_id','')}|{rec.get('symbol','')}|{rec.get('trade_date','')}|{rec.get('direction','')}"


def _load_existing_keys(ledger_path: Path = LEDGER_PATH) -> Set[str]:
    if not ledger_path.exists():
        return set()
    keys: Set[str] = set()
    with open(ledger_path) as f:
        for line in f:
            try:
                r = json.loads(line)
                keys.add(f"{r.get('source_run_id','')}|{r.get('symbol','')}|{r.get('trade_date','')}|{r.get('direction','')}")
            except json.JSONDecodeError:
                pass
    return keys


# ─────────────────────────────────────────────────────────────────────────────
# Classification logic
# ─────────────────────────────────────────────────────────────────────────────


def _is_direction_correct(direction: str, t1_ret_pct: float) -> bool:
    return (direction == "UP" and t1_ret_pct > 0) or (direction == "DOWN" and t1_ret_pct < 0)


def _compute_ge_flags(direction: str, t1: Optional[float]) -> Tuple[Optional[bool], Optional[bool], Optional[bool]]:
    if t1 is None:
        return None, None, None
    correct = _is_direction_correct(direction, t1)
    abs_t1 = abs(t1)
    ge1 = correct and abs_t1 >= 1.0
    ge2 = correct and abs_t1 >= GE2_THRESHOLD
    ge3 = correct and abs_t1 >= 3.0
    return ge1, ge2, ge3


def _classify(rec: Dict) -> Tuple[Classification, MissReason]:
    t1: Optional[float] = rec.get("t1_ret_pct")
    selected: bool = bool(rec.get("selected_final_5", False))
    strategy_rejected: bool = bool(rec.get("strategy_rejected", False))
    direction: str = rec.get("direction", "UP")

    # Selected by C2 Top-5
    if selected:
        return Classification.CORRECT_SELECT, MissReason.NOT_APPLICABLE

    # Outcome not yet available
    if t1 is None:
        return Classification.UNRESOLVED, MissReason.NO_DATA

    dir_correct = _is_direction_correct(direction, t1)
    is_meaningful = abs(t1) >= GE2_THRESHOLD and dir_correct

    # Strategy-rejected candidates
    if strategy_rejected:
        if is_meaningful:
            return Classification.FALSE_REJECT, MissReason.STRATEGY_REJECTION
        return Classification.CORRECT_REJECT, MissReason.STRATEGY_REJECTION

    # Not selected, not strategy-rejected → ranking miss if meaningful
    if is_meaningful:
        return Classification.RANKING_MISS, _miss_reason(rec, direction)

    # Not selected, not meaningful → not noteworthy; still record as correct
    return Classification.CORRECT_SELECT, MissReason.NOT_APPLICABLE  # effectively correct non-selection


def _miss_reason(rec: Dict, direction: str) -> MissReason:
    """Determine WHY a RANKING_MISS was missed."""
    c2_rank: Optional[int] = rec.get("c2_rank")
    gap_pct: Optional[float] = rec.get("gap_pct")

    # Adverse gap: moved favorably despite gapping the wrong way at open
    if gap_pct is not None:
        adverse = (direction == "UP" and gap_pct < 0) or (direction == "DOWN" and gap_pct > 0)
        if adverse:
            return MissReason.ADVERSE_OPEN_GAP

    # Outranked by stronger openers
    if c2_rank is not None and 6 <= c2_rank <= 10:
        return MissReason.OUTRANKED_BY_STRONGER_OPENERS

    # Low C2 score (ranks 11-20)
    if c2_rank is not None and c2_rank >= 11:
        return MissReason.LOW_C2_SCORE

    return MissReason.OUTRANKED_BY_STRONGER_OPENERS  # default for unclassified


# ─────────────────────────────────────────────────────────────────────────────
# Build EvidenceRecord from raw shadow record
# ─────────────────────────────────────────────────────────────────────────────


def _build_evidence_record(raw: Dict) -> EvidenceRecord:
    direction = raw.get("direction", "UP")
    t1 = raw.get("t1_ret_pct")
    ge1, ge2, ge3 = _compute_ge_flags(direction, t1)
    classification, miss_reason = _classify(raw)

    # knowledge_strategy_disagreement: compute if missing from old records
    ksd = raw.get("knowledge_strategy_disagreement")
    if ksd is None:
        # Derive from strategy_status + selected_final_5
        s_status = raw.get("strategy_status", "STRATEGY_UNAVAILABLE")
        selected = bool(raw.get("selected_final_5", False))
        if selected:
            ksd = "AGREE_PASS" if s_status in ("PASS", "ALIGNED", "NEUTRAL") else "KNOWLEDGE_OVERRULES_STRATEGY"
        else:
            ksd = s_status if s_status else "STRATEGY_UNAVAILABLE"

    c2_rank_raw = raw.get("c2_rank")
    c2_rank = int(c2_rank_raw) if c2_rank_raw is not None else None

    return EvidenceRecord(
        event_id=str(uuid.uuid4()),
        source_run_id=raw.get("run_id", ""),
        trade_date=raw.get("trade_date", ""),
        symbol=raw.get("symbol", ""),
        direction=direction,
        v3_score=raw.get("v3_score"),
        c2_score=raw.get("c2_score"),
        c2_rank=c2_rank,
        selected_final_5=bool(raw.get("selected_final_5", False)),
        strategy_status=raw.get("strategy_status"),
        strategy_rejected=bool(raw.get("strategy_rejected", False)),
        knowledge_strategy_disagreement=ksd,
        t1_ret_pct=t1,
        t3_ret_pct=None,   # not in shadow JSONL
        t5_ret_pct=None,   # not in shadow JSONL
        mfe_pct=raw.get("mfe_pct"),
        mae_pct=raw.get("mae_pct"),
        ge1=ge1,
        ge2=ge2,
        ge3=ge3,
        classification=classification,
        miss_reason=miss_reason,
        regime=raw.get("strategy_regime"),
        processed_at=datetime.now(timezone.utc).isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main consumer
# ─────────────────────────────────────────────────────────────────────────────


def consume_new_records(
    shadow_path: Path = SHADOW_JSONL,
    ledger_path: Path = LEDGER_PATH,
    knowledge_ledger_path: Path = KNOWLEDGE_LEDGER,
    state_path: Path = STATE_PATH,
) -> List[EvidenceRecord]:
    """
    Read new SHADOW_CANDIDATE records since last run.
    Classify them and append to the evidence ledger.
    Returns list of newly processed EvidenceRecords.
    """
    if not shadow_path.exists():
        return []

    state = load_state()
    existing_keys = _load_existing_keys()
    new_records: List[EvidenceRecord] = []

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    knowledge_ledger_path.parent.mkdir(parents=True, exist_ok=True)

    file_size = shadow_path.stat().st_size
    if file_size <= state.last_processed_byte_offset:
        return []  # No new data

    with open(shadow_path) as sf, \
         open(ledger_path, "a") as lf, \
         open(knowledge_ledger_path, "a") as kf:

        sf.seek(0)  # always seek to beginning; dedup handles duplicates
        # Skip to last processed position
        sf.read(state.last_processed_byte_offset)

        for raw_line in sf:
            try:
                raw = json.loads(raw_line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if raw.get("record_type") != "SHADOW_CANDIDATE":
                continue

            key = _dedup_key(raw)
            if key in existing_keys:
                continue  # already processed

            ev = _build_evidence_record(raw)
            ev_dict = ev.to_dict()

            lf.write(json.dumps(ev_dict) + "\n")
            kf.write(json.dumps({
                "event_type": KSLEventType.EVIDENCE.value,
                "event_id": ev.event_id,
                "trade_date": ev.trade_date,
                "symbol": ev.symbol,
                "direction": ev.direction,
                "classification": ev.classification.value,
                "miss_reason": ev.miss_reason.value,
                "t1_ret_pct": ev.t1_ret_pct,
                "ge2": ev.ge2,
                "recorded_at": ev.processed_at,
            }) + "\n")

            existing_keys.add(key)
            new_records.append(ev)

    new_offset = file_size

    # Update state
    state.last_processed_byte_offset = new_offset
    state.last_processed_at = datetime.now(timezone.utc).isoformat()
    state.total_records_ingested += len(new_records)
    save_state(state)

    return new_records


# ─────────────────────────────────────────────────────────────────────────────
# Historical audit CSV seeder (one-time bootstrap from research data)
# ─────────────────────────────────────────────────────────────────────────────


def seed_from_historical_audit_csv(
    csv_path: Optional[Path] = None,
    ledger_path: Path = LEDGER_PATH,
    knowledge_ledger_path: Path = KNOWLEDGE_LEDGER,
) -> List[EvidenceRecord]:
    """
    Seed the evidence ledger from the historical selection-quality audit CSV.
    This is a one-time bootstrap to give the pattern miner sufficient signal.
    Idempotent: records already in the ledger are skipped via dedup.
    Returns list of newly written EvidenceRecord objects.
    """
    if csv_path is None:
        csv_path = ROOT / "data" / "audit" / "daily_selection_quality_missed_movers.csv"

    if not csv_path.exists():
        return []

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    knowledge_ledger_path.parent.mkdir(parents=True, exist_ok=True)

    existing_keys = _load_existing_keys(ledger_path)
    new_records: List[EvidenceRecord] = []

    MISS_REASON_MAP = {
        "OUTRANKED_BY_STRONGER_OPENERS": MissReason.OUTRANKED_BY_STRONGER_OPENERS,
        "ADVERSE_OPEN_GAP": MissReason.ADVERSE_OPEN_GAP,
        "LOW_C2_SCORE": MissReason.LOW_C2_SCORE,
        "STRATEGY_REJECTION": MissReason.STRATEGY_REJECTION,
        "RISK_REJECTION": MissReason.RISK_REJECTION,
        "NOT_APPLICABLE": MissReason.NOT_APPLICABLE,
    }
    CLASSIF_MAP = {
        "RANKING_MISS": Classification.RANKING_MISS,
        "CORRECTLY_RANKED": Classification.CORRECT_SELECT,
        "CORRECT_SELECT": Classification.CORRECT_SELECT,
        "FALSE_REJECT": Classification.FALSE_REJECT,
        "CORRECT_REJECT": Classification.CORRECT_REJECT,
        "DISCOVERY_SUCCESS": Classification.DISCOVERY_SUCCESS,
        "DISCOVERY_MISS": Classification.DISCOVERY_MISS,
    }

    import csv
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        with open(ledger_path, "a") as lf, open(knowledge_ledger_path, "a") as kf:
            for row in reader:
                source_run_id = "AUDIT_HISTORICAL_001"
                trade_date = row.get("date", "")
                symbol = row.get("symbol", "")
                direction = row.get("direction", "UNKNOWN")

                key = f"{source_run_id}|{symbol}|{trade_date}|{direction}"
                if key in existing_keys:
                    continue

                miss_type_str = row.get("miss_type", row.get("classification", "UNRESOLVED")).upper()
                classif = CLASSIF_MAP.get(miss_type_str, Classification.UNRESOLVED)

                miss_reason_str = row.get("miss_reason", "NOT_APPLICABLE").upper()
                miss_reason = MISS_REASON_MAP.get(miss_reason_str, MissReason.NOT_APPLICABLE)
                if classif == Classification.RANKING_MISS and miss_reason == MissReason.NOT_APPLICABLE:
                    miss_reason = MissReason.OUTRANKED_BY_STRONGER_OPENERS

                try:
                    actual_move = float(row.get("actual_move", 0.0) or 0.0)
                    v3_score = float(row.get("v3_score", 0.0) or 0.0)
                    c2_score_val = row.get("c2_score")
                    c2_score = float(c2_score_val) if c2_score_val not in (None, "", "nan", "NaN") else None
                    c2_rank_val = row.get("c2_rank")
                    c2_rank = int(float(c2_rank_val)) if c2_rank_val not in (None, "", "nan", "NaN") else None
                except (TypeError, ValueError):
                    actual_move = 0.0
                    v3_score = 0.0
                    c2_score = None
                    c2_rank = None

                ge2 = bool(abs(actual_move) >= GE2_THRESHOLD)

                ev = EvidenceRecord(
                    event_id=str(uuid.uuid4()),
                    source_run_id=source_run_id,
                    trade_date=trade_date,
                    symbol=symbol,
                    direction=direction,
                    v3_score=v3_score,
                    c2_score=c2_score,
                    c2_rank=c2_rank,
                    selected_final_5=classif == Classification.CORRECT_SELECT,
                    strategy_status=None,
                    strategy_rejected=classif in (Classification.CORRECT_REJECT, Classification.FALSE_REJECT),
                    knowledge_strategy_disagreement=None,
                    t1_ret_pct=actual_move,
                    t3_ret_pct=None,
                    t5_ret_pct=None,
                    mfe_pct=None,
                    mae_pct=None,
                    ge1=bool(abs(actual_move) >= 1.0),
                    ge2=ge2,
                    ge3=bool(abs(actual_move) >= 3.0),
                    classification=classif,
                    miss_reason=miss_reason,
                    regime=row.get("regime", "UNKNOWN"),
                    processed_at=datetime.now(timezone.utc).isoformat(),
                )

                lf.write(json.dumps(ev.to_dict()) + "\n")
                kf.write(json.dumps({
                    "event_type": KSLEventType.EVIDENCE.value,
                    "evidence_id": ev.event_id,
                    "symbol": symbol,
                    "trade_date": trade_date,
                    "direction": direction,
                    "classification": ev.classification.value,
                    "miss_reason": ev.miss_reason.value,
                    "t1_ret_pct": ev.t1_ret_pct,
                    "ge2": ev.ge2,
                    "source": "historical_audit",
                    "recorded_at": ev.processed_at,
                }) + "\n")

                existing_keys.add(key)
                new_records.append(ev)

    return new_records


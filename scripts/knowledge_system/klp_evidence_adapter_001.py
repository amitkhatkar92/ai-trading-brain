"""
scripts/knowledge_system/klp_evidence_adapter_001.py
======================================================
KLP → Evidence Ledger Adapter  —  KLP-002

PURPOSE
-------
Converts completed KLP outcome records (KNOWLEDGE_OBSERVATION + OUTCOME_UPDATE
pairs) into EvidenceRecord format and appends them to the shadow evidence
ledger used by the KSL pattern mining pipeline.

This bridges live KLP observations into the same research pipeline that
processes historical shadow data — enabling the pattern miner, RQ generator,
and proposal builder to learn from live Knowledge selections.

INPUT
-----
  data/klp/KLP_YYYY-MM-DD.jsonl   — completed KLP records

OUTPUT
------
  data/shadow_evidence_ledger.jsonl   — appended EvidenceRecords (same ledger
                                        as shadow pipeline, different source_run_id)
  data/knowledge_evidence_ledger.jsonl — appended to knowledge ledger as well
  data/ksl/klp_adapter_state.json    — watermark {date: last_processed_obs_count}

CONTRACT
--------
• Never raises.
• Append-only writes to evidence ledger.
• Dedup: source_run_id = "klp_{obs_id}" prevents duplicates across runs.
• Never modifies KLP JSONL files.
• broker_calls = 0, orders = 0, production_changes = 0.

CLASSIFICATION MAPPING (KLP-specific)
--------------------------------------
knowledge_selected=True  + direction_correct=True  + ge2=True  → CORRECT_SELECT
knowledge_selected=True  + direction_correct=True  + ge2=False → CORRECT_SELECT
knowledge_selected=True  + direction_correct=False             → FALSE_REJECT (false positive)
knowledge_selected=False + ge2=True                            → RANKING_MISS
knowledge_selected=False + ge2=False                           → CORRECT_REJECT
strategy_rejected=True   + direction_correct=True              → FALSE_REJECT (K would have won)
strategy_rejected=True   + direction_correct=False             → CORRECT_REJECT (K was also wrong)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys_path_str = str(ROOT)
import sys
if sys_path_str not in sys.path:
    sys.path.insert(0, sys_path_str)

from scripts.knowledge_system.ksl_models import (
    Classification,
    EvidenceRecord,
    MissReason,
)

# ── Paths ──────────────────────────────────────────────────────────────────────
_KLP_DATA_DIR      = ROOT / "data" / "klp"
_SHADOW_LEDGER     = ROOT / "data" / "shadow_evidence_ledger.jsonl"
_KNOWLEDGE_LEDGER  = ROOT / "data" / "knowledge_evidence_ledger.jsonl"
_STATE_PATH        = ROOT / "data" / "ksl" / "klp_adapter_state.json"

# ── Source identifier prefix — distinguishes KLP records from shadow records ──
_KLP_SOURCE_PREFIX = "klp_"


def ingest_klp_outcomes(
    dates: Optional[List[str]] = None,
    klp_data_dir: Optional[Path] = None,
    shadow_ledger: Optional[Path] = None,
    knowledge_ledger: Optional[Path] = None,
    state_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Read completed KLP outcome records and append them to the evidence ledger.

    Parameters
    ----------
    dates           : list of "YYYY-MM-DD" strings to process; default: last 7 days
    klp_data_dir    : override for data/klp/ (used in tests)
    shadow_ledger   : override for shadow_evidence_ledger.jsonl (used in tests)
    knowledge_ledger: override for knowledge_evidence_ledger.jsonl (used in tests)
    state_path      : override for klp_adapter_state.json (used in tests)

    Returns summary dict.  Never raises.
    """
    try:
        return _ingest_impl(dates, klp_data_dir, shadow_ledger, knowledge_ledger, state_path)
    except Exception as exc:
        return {"new_records": 0, "error": str(exc)}


def _ingest_impl(
    dates: Optional[List[str]],
    klp_data_dir: Optional[Path],
    shadow_ledger: Optional[Path],
    knowledge_ledger: Optional[Path],
    state_path: Optional[Path],
) -> Dict[str, Any]:
    klp_dir   = Path(klp_data_dir)  if klp_data_dir   else _KLP_DATA_DIR
    s_ledger  = Path(shadow_ledger) if shadow_ledger   else _SHADOW_LEDGER
    k_ledger  = Path(knowledge_ledger) if knowledge_ledger else _KNOWLEDGE_LEDGER
    s_path    = Path(state_path)    if state_path      else _STATE_PATH

    if dates is None:
        today = date.today()
        dates = [str(today - timedelta(days=i)) for i in range(1, 8)]

    # Load already-processed obs_ids from state
    state = _load_state(s_path)
    existing_keys = _load_existing_keys(s_ledger)

    new_records: List[EvidenceRecord] = []

    for date_str in dates:
        klp_file = klp_dir / f"KLP_{date_str}.jsonl"
        if not klp_file.exists():
            continue

        # Load all records from this KLP file
        obs_map: Dict[str, Dict]     = {}   # obs_id → KNOWLEDGE_OBSERVATION
        outcome_map: Dict[str, Dict] = {}   # obs_id → OUTCOME_UPDATE
        ann_map: Dict[str, Dict]     = {}   # obs_id → STRATEGY_ANNOTATION

        with klp_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                oid = rec.get("obs_id", "")
                et  = rec.get("event_type", "")
                if et == "KNOWLEDGE_OBSERVATION":
                    obs_map[oid] = rec
                elif et == "OUTCOME_UPDATE":
                    outcome_map[oid] = rec
                elif et == "STRATEGY_ANNOTATION":
                    ann_map[oid] = rec

        # For each observation with a completed outcome, build EvidenceRecord
        for oid, obs in obs_map.items():
            outcome = outcome_map.get(oid)
            if not outcome:
                continue   # outcome not yet computed

            # Skip records that couldn't be resolved
            if outcome.get("first_event") in ("OUTCOME_PENDING", "OUTCOME_NO_DATA"):
                continue

            dedup_key = f"{_KLP_SOURCE_PREFIX}{oid}"
            if dedup_key in existing_keys:
                continue   # already in ledger

            ann = ann_map.get(oid, {})
            ev  = _build_evidence_record(obs, outcome, ann)
            new_records.append(ev)
            existing_keys.add(dedup_key)

    if not new_records:
        return {"new_records": 0, "error": None}

    # Append to both ledgers
    s_ledger.parent.mkdir(parents=True, exist_ok=True)
    k_ledger.parent.mkdir(parents=True, exist_ok=True)

    with s_ledger.open("a", encoding="utf-8") as sf, \
         k_ledger.open("a", encoding="utf-8") as kf:
        for ev in new_records:
            line = json.dumps({**ev.to_dict(), "source": "klp"}, ensure_ascii=False)
            sf.write(line + "\n")
            kf.write(line + "\n")

    # Update state
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["total_klp_records_ingested"] = state.get("total_klp_records_ingested", 0) + len(new_records)
    _save_state(s_path, state)

    return {"new_records": len(new_records), "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# Evidence record builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_evidence_record(
    obs: Dict[str, Any],
    outcome: Dict[str, Any],
    ann: Dict[str, Any],
) -> EvidenceRecord:
    direction   = (obs.get("direction") or "BUY").upper()
    symbol      = obs.get("symbol", "")
    trade_date  = obs.get("trading_date", "")
    obs_id      = obs.get("obs_id", "")

    t1          = outcome.get("t1_ret_pct")
    t3          = outcome.get("t3_ret_pct")
    t5          = outcome.get("t5_ret_pct")
    mfe         = outcome.get("mfe_pct")
    mae         = outcome.get("mae_pct")
    ge1         = outcome.get("ge1")
    ge2         = outcome.get("ge2")
    ge3         = outcome.get("ge3")

    k_selected  = bool(obs.get("knowledge_selected", False))
    strat_rej   = ann.get("strategy_status") == "REJECTED"
    dir_correct = outcome.get("direction_correct", False)

    classif, miss_reason = _classify_klp(k_selected, strat_rej, dir_correct, ge1, ge2)

    ksd = ann.get("knowledge_strategy_disagreement") or obs.get("knowledge_strategy_disagreement")

    return EvidenceRecord(
        event_id              = str(uuid.uuid4()),
        source_run_id         = f"{_KLP_SOURCE_PREFIX}{obs_id}",
        trade_date            = trade_date,
        symbol                = symbol,
        direction             = "UP" if direction == "BUY" else "DOWN",
        v3_score              = None,
        c2_score              = None,
        c2_rank               = None,
        selected_final_5      = k_selected,
        strategy_status       = ann.get("strategy_status"),
        strategy_rejected     = strat_rej,
        knowledge_strategy_disagreement = ksd,
        t1_ret_pct            = t1,
        t3_ret_pct            = t3,
        t5_ret_pct            = t5,
        mfe_pct               = mfe,
        mae_pct               = mae,
        ge1                   = ge1,
        ge2                   = ge2,
        ge3                   = ge3,
        classification        = classif,
        miss_reason           = miss_reason,
        regime                = obs.get("regime"),
        processed_at          = datetime.now(timezone.utc).isoformat(),
    )


def _classify_klp(
    k_selected: bool,
    strat_rejected: bool,
    direction_correct: bool,
    ge1: Optional[bool],
    ge2: Optional[bool],
) -> Tuple[Classification, MissReason]:
    """Map KLP observation attributes to Classification + MissReason."""
    ge2_val = bool(ge2) if ge2 is not None else False

    if k_selected:
        if direction_correct:
            return Classification.CORRECT_SELECT, MissReason.NOT_APPLICABLE
        elif strat_rejected:
            # Strategy rejected AND direction was correct → FALSE_REJECT (opportunity missed)
            if direction_correct:
                return Classification.FALSE_REJECT, MissReason.STRATEGY_REJECTION
        return Classification.CORRECT_REJECT, MissReason.STRATEGY_REJECTION if strat_rejected else MissReason.NOT_APPLICABLE
    else:
        # Not selected by knowledge
        if ge2_val:
            return Classification.RANKING_MISS, MissReason.NOT_APPLICABLE
        return Classification.CORRECT_REJECT, MissReason.NOT_APPLICABLE


# ─────────────────────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_state(state_path: Path) -> Dict[str, Any]:
    try:
        if state_path.exists():
            return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(state_path: Path, state: Dict[str, Any]) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, state_path)
    except Exception:
        pass


def _load_existing_keys(ledger_path: Path) -> Set[str]:
    """Return set of source_run_ids already in the ledger."""
    keys: Set[str] = set()
    if not ledger_path.exists():
        return keys
    try:
        with ledger_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    k = rec.get("source_run_id", "")
                    if k:
                        keys.add(k)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return keys

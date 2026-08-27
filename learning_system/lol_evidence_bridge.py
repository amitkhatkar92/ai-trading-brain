"""
learning_system/lol_evidence_bridge.py
========================================
LOL → KDA Evidence Bridge  (DTA-LIVE-003 GAP-002)

PURPOSE
-------
Reads completed LOL OUTCOME_OBSERVED records from data/lol/LOL_YYYY-MM-DD.jsonl
and appends them as EVIDENCE events to data/knowledge_evidence_ledger.jsonl so
the KDA knowledge-fusion engine can learn from live counterfactual outcomes.

HOW IT PLUGS INTO THE EXISTING KDA ARCHITECTURE
------------------------------------------------
knowledge_evidence_ledger.jsonl is consumed by:
  KnowledgeFusionEngine._load_knowledge_evidence_ledger()  (KFE angle analysis)
  scripts/knowledge_system/*.py  (KSL-001 pattern mining)

Records are written with event_type="EVIDENCE" matching the format already used
by historical_audit records so the existing readers require no modification.

OUTCOME_CLASS → CLASSIFICATION MAPPING
---------------------------------------
LOL outcome_class          Classification       MissReason
---------                  ---------------      ----------
EXECUTED_WIN               CORRECT_SELECT       NOT_APPLICABLE
TARGET_EXIT                CORRECT_SELECT       NOT_APPLICABLE
EXECUTED_LOSS              INCORRECT_SELECT     NOT_APPLICABLE
STOP_EXIT                  INCORRECT_SELECT     NOT_APPLICABLE
EARLY_EXIT                 INCORRECT_SELECT     NOT_APPLICABLE
REJECTED_INCORRECT         RANKING_MISS         STRATEGY_REJECTION
BLOCKED_INCORRECT          RANKING_MISS         RISK_REJECTION
MISSED_OPPORTUNITY         RANKING_MISS         NOT_APPLICABLE
KDA_FALSE_NEGATIVE         RANKING_MISS         NOT_APPLICABLE
REJECTED_CORRECT           CORRECT_REJECT       NOT_APPLICABLE
BLOCKED_CORRECT            CORRECT_REJECT       NOT_APPLICABLE
All others                 → skipped (ambiguous or no clean mapping)

CONTRACT
--------
• broker_calls = 0, orders = 0, PAPER_TRADING unchanged
• Append-only writes to knowledge_evidence_ledger.jsonl
• Idempotent: source_run_id = "lol_{observation_id}" prevents duplicates
• Anti-lookahead: only records with lifecycle_state == OUTCOME_OBSERVED
  and outcome_at > decision_at are ingested
• Does NOT modify knowledge_authority/, risk_guardian/, order_manager,
  or any other protected module
• Reuses existing KSL-001 Classification / EvidenceRecord / MissReason models
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── Default paths (overridable for tests) ────────────────────────────────────
_ROOT              = Path(__file__).resolve().parents[1]
_LOL_DATA_DIR      = _ROOT / "data" / "lol"
_KNOWLEDGE_LEDGER  = _ROOT / "data" / "knowledge_evidence_ledger.jsonl"
_STATE_PATH        = _ROOT / "data" / "ksl" / "lol_bridge_state.json"

# ── Dedup key prefix ─────────────────────────────────────────────────────────
_LOL_SOURCE_PREFIX = "lol_"

# ── LOL lifecycle state that indicates outcome is ready ──────────────────────
_OUTCOME_OBSERVED = "OUTCOME_OBSERVED"
_LEARNING_PROCESSED = "LEARNING_PROCESSED"  # also eligible

# ── Classification strings (mirrors ksl_models.Classification enum) ──────────
_CORRECT_SELECT   = "CORRECT_SELECT"
_INCORRECT_SELECT = "INCORRECT_SELECT"   # D13-001: executed trade that lost
_RANKING_MISS     = "RANKING_MISS"
_CORRECT_REJECT   = "CORRECT_REJECT"
_UNRESOLVED       = "UNRESOLVED"

# ── MissReason strings (mirrors ksl_models.MissReason enum) ──────────────────
_NOT_APPLICABLE      = "NOT_APPLICABLE"
_STRATEGY_REJECTION  = "STRATEGY_REJECTION"
_RISK_REJECTION      = "RISK_REJECTION"

# ── Outcome class → (classification, miss_reason) mapping ───────────────────
#
# D13-001: EXECUTED_LOSS, STOP_EXIT, EARLY_EXIT now map to INCORRECT_SELECT so
# that losses reach KEL alongside wins.  Without this, the knowledge base
# accumulates only positive evidence, creating survivorship bias.
_OUTCOME_CLASS_MAP: Dict[str, Optional[Tuple[str, str]]] = {
    # Executed and won → pipeline correctly selected the signal
    "EXECUTED_WIN":    (_CORRECT_SELECT, _NOT_APPLICABLE),
    "TARGET_EXIT":     (_CORRECT_SELECT, _NOT_APPLICABLE),
    # Executed and lost → pipeline selected incorrectly (D13-001 fix)
    "EXECUTED_LOSS":   (_INCORRECT_SELECT, _NOT_APPLICABLE),
    "STOP_EXIT":       (_INCORRECT_SELECT, _NOT_APPLICABLE),
    "EARLY_EXIT":      (_INCORRECT_SELECT, _NOT_APPLICABLE),
    # Signal was rejected / blocked; direction would have been right → missed opportunity
    "REJECTED_INCORRECT":  (_RANKING_MISS, _STRATEGY_REJECTION),
    "BLOCKED_INCORRECT":   (_RANKING_MISS, _RISK_REJECTION),
    "MISSED_OPPORTUNITY":  (_RANKING_MISS, _NOT_APPLICABLE),
    "KDA_FALSE_NEGATIVE":  (_RANKING_MISS, _NOT_APPLICABLE),
    # Signal was rejected / blocked; direction was wrong → correct rejection
    "REJECTED_CORRECT":    (_CORRECT_REJECT, _NOT_APPLICABLE),
    "BLOCKED_CORRECT":     (_CORRECT_REJECT, _NOT_APPLICABLE),
    # Ambiguous / insufficient information → skip
    "EXECUTED_FLAT":       None,
    "SHORTLISTED_NOT_EXECUTED": None,
    "KDA_FALSE_POSITIVE":  None,
    "KNOWLEDGE_AGREEMENT": None,
    "KNOWLEDGE_DISAGREEMENT": None,
    "OUTCOME_UNKNOWN":     None,
    "OUTCOME_PENDING":     None,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def ingest_lol_outcomes(
    dates:             Optional[List[str]] = None,
    lol_data_dir:      Optional[Path]      = None,
    knowledge_ledger:  Optional[Path]      = None,
    state_path:        Optional[Path]      = None,
) -> Dict[str, Any]:
    """
    Read completed LOL OUTCOME_OBSERVED records and append them to the
    knowledge evidence ledger.

    Parameters
    ----------
    dates             : list of "YYYY-MM-DD" strings to process;
                        default: today + last 7 days
    lol_data_dir      : override for data/lol/ (used in tests)
    knowledge_ledger  : override for knowledge_evidence_ledger.jsonl (used in tests)
    state_path        : override for lol_bridge_state.json (used in tests)

    Returns summary dict.  Never raises.
    """
    try:
        return _ingest_impl(dates, lol_data_dir, knowledge_ledger, state_path)
    except Exception as exc:
        log.debug("[LOL-BRIDGE] ingest_lol_outcomes error: %s", exc)
        return {"new_records": 0, "skipped": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Implementation
# ─────────────────────────────────────────────────────────────────────────────

def _ingest_impl(
    dates:            Optional[List[str]],
    lol_data_dir:     Optional[Path],
    knowledge_ledger: Optional[Path],
    state_path:       Optional[Path],
) -> Dict[str, Any]:
    lol_dir  = Path(lol_data_dir)     if lol_data_dir     else _LOL_DATA_DIR
    k_ledger = Path(knowledge_ledger) if knowledge_ledger else _KNOWLEDGE_LEDGER
    s_path   = Path(state_path)       if state_path       else _STATE_PATH

    if dates is None:
        today = date.today()
        # Today + last 7 calendar days (outcomes arrive T+1..T+5)
        dates = [str(today - timedelta(days=i)) for i in range(0, 8)]

    # Load existing source_run_ids from the knowledge ledger to dedup
    existing_keys = _load_existing_keys(k_ledger)

    new_evidence: List[Dict[str, Any]] = []
    skipped = 0

    for date_str in dates:
        lol_file = lol_dir / f"LOL_{date_str}.jsonl"
        if not lol_file.exists():
            continue

        # Build snapshot: latest record per observation_id
        # (LOL is append-only; later records supersede earlier ones for the same obs_id)
        latest_by_obs: Dict[str, Dict[str, Any]] = {}
        try:
            with lol_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    obs_id = rec.get("observation_id", "")
                    if obs_id:
                        latest_by_obs[obs_id] = rec
        except Exception as exc:
            log.debug("[LOL-BRIDGE] Error reading %s: %s", lol_file, exc)
            continue

        for obs_id, rec in latest_by_obs.items():
            # Only process records with a resolved outcome
            lifecycle_state = rec.get("lifecycle_state", "")
            if lifecycle_state not in (_OUTCOME_OBSERVED, _LEARNING_PROCESSED):
                skipped += 1
                continue

            # Anti-lookahead: STRICT — both timestamps required; outcome must be AFTER decision.
            # Missing decision_at = no temporal proof = inadmissible (not just unchecked).
            outcome_at  = rec.get("outcome_at")
            decision_at = rec.get("decision_at")
            if not outcome_at or not decision_at:
                log.info(
                    "[LOL-BRIDGE] Skipping %s: missing temporal proof "
                    "(outcome_at=%s decision_at=%s) — no_lookahead cannot be asserted.",
                    obs_id, outcome_at, decision_at,
                )
                skipped += 1
                continue
            try:
                # D-004: Parse both timestamps to UTC datetime before comparing.
                # Lexicographic string comparison fails when formats mix UTC ("Z" / "+00:00")
                # and IST ("+05:30") — e.g. "2026-08-26T15:30:00+05:30" lexicographically
                # greater than "2026-08-26T14:30:00+00:00" but actually 30 min earlier.
                from datetime import timezone as _tz
                def _to_utc(ts: str) -> datetime:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_tz.utc)
                    return dt.astimezone(_tz.utc)

                if _to_utc(outcome_at) <= _to_utc(decision_at):
                    log.warning(
                        "[LOL-BRIDGE] Skipping %s: lookahead violation — "
                        "outcome_at (%s) not after decision_at (%s).",
                        obs_id, outcome_at, decision_at,
                    )
                    skipped += 1
                    continue
            except Exception as _cmp_exc:
                log.warning(
                    "[LOL-BRIDGE] Skipping %s: timestamp comparison error: %s",
                    obs_id, _cmp_exc,
                )
                skipped += 1
                continue

            # Idempotency: skip if already in ledger
            dedup_key = f"{_LOL_SOURCE_PREFIX}{obs_id}"
            if dedup_key in existing_keys:
                skipped += 1
                continue

            # Classify outcome
            outcome_class = rec.get("outcome_class", "")
            mapping = _OUTCOME_CLASS_MAP.get(outcome_class)
            if mapping is None:
                # Ambiguous or unsupported outcome class — skip
                skipped += 1
                continue

            classification, miss_reason = mapping

            # D9-007: warn when lineage ID is missing — KEL record will have no
            # opportunity_id, making signal→decision→outcome chain untraceable.
            if not rec.get("opportunity_id"):
                log.warning(
                    "[LOL-BRIDGE] %s has no opportunity_id — evidence written "
                    "without lineage (KDA trace broken for this observation).",
                    obs_id,
                )

            # Build evidence record (event_type="EVIDENCE" for KFE compatibility)
            evidence = _build_evidence_record(rec, obs_id, classification, miss_reason)
            new_evidence.append(evidence)
            existing_keys.add(dedup_key)

    if not new_evidence:
        # Always write state so operators can confirm the bridge ran, even when
        # 0 records were eligible (all outcomes still PENDING, no bridge needed).
        state = _load_state(s_path)
        _now_iso = datetime.now(timezone.utc).isoformat()
        state["last_run"]                  = _now_iso
        state["last_run_result"]           = "NO_ELIGIBLE_OUTCOMES"
        state["last_lol_pending"]          = skipped
        state["last_lol_evidence_created"] = 0
        state["last_lol_evidence_failed"]  = 0
        _save_state(s_path, state)
        log.info(
            "[LOL-BRIDGE] Run complete: lol_pending=%d lol_outcomes_eligible=0 "
            "lol_evidence_created=0 lol_evidence_skipped=%d — state written.",
            skipped, skipped,
        )
        return {"new_records": 0, "skipped": skipped, "error": None,
                "lol_pending": skipped, "lol_evidence_created": 0,
                "lol_evidence_duplicate": 0, "lol_evidence_failed": 0}

    # Append to knowledge evidence ledger
    k_ledger.parent.mkdir(parents=True, exist_ok=True)
    try:
        with k_ledger.open("a", encoding="utf-8") as kf:
            for ev in new_evidence:
                kf.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception as exc:
        log.debug("[LOL-BRIDGE] Write error: %s", exc)
        return {"new_records": 0, "skipped": skipped, "error": str(exc)}

    # Update state
    state = _load_state(s_path)
    _now_iso = datetime.now(timezone.utc).isoformat()
    state["last_run"]                   = _now_iso
    state["last_run_result"]            = "OK"
    state["last_lol_pending"]           = skipped
    state["last_lol_evidence_created"]  = len(new_evidence)
    state["last_lol_evidence_failed"]   = 0
    state["total_lol_records_ingested"] = (
        state.get("total_lol_records_ingested", 0) + len(new_evidence)
    )
    _save_state(s_path, state)

    log.info(
        "[LOL-BRIDGE] Run complete: lol_pending=%d lol_outcomes_eligible=%d "
        "lol_evidence_created=%d lol_evidence_duplicate=%d",
        skipped, len(new_evidence) + skipped, len(new_evidence), skipped,
    )
    return {"new_records": len(new_evidence), "skipped": skipped, "error": None,
            "lol_pending": skipped, "lol_evidence_created": len(new_evidence),
            "lol_evidence_duplicate": skipped, "lol_evidence_failed": 0}


# ─────────────────────────────────────────────────────────────────────────────
# Evidence record builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_evidence_record(
    rec:            Dict[str, Any],
    obs_id:         str,
    classification: str,
    miss_reason:    str,
) -> Dict[str, Any]:
    """
    Build a knowledge-evidence-ledger record from a LOL OUTCOME_OBSERVED record.

    Uses event_type="EVIDENCE" for KFE compatibility (KnowledgeFusionEngine
    filters for this value in _load_knowledge_evidence_ledger).

    Anti-lookahead fields:
      - Only fields known at observation/decision time are included in the
        non-outcome section (symbol, direction, trading_date, regime)
      - Outcome fields (t1_ret_pct, t5_ret_pct, ge2, etc.) are only present
        because this record was computed AFTER market close using T+1..T+5 bars
        and lifecycle_state == OUTCOME_OBSERVED was verified above.

    No lookahead: no_lookahead = True is copied from the source LOL record
    (guaranteed True by the LOL module's _compute_outcome function).
    """
    direction_raw = (rec.get("direction") or "BUY").upper()
    # Normalise to UP/DOWN for compatibility with existing historical_audit records
    direction_ev  = "UP" if direction_raw not in ("SELL", "SHORT", "BEAR", "DOWN") else "DOWN"

    symbol     = (rec.get("symbol") or "").upper().strip()
    trade_date = str(rec.get("trading_date") or "")[:10]

    t1  = rec.get("t1_ret_pct")
    t3  = rec.get("t3_ret_pct")
    t5  = rec.get("t5_ret_pct")
    mfe = rec.get("mfe_pct")
    mae = rec.get("mae_pct")

    # ge1/ge2/ge3: ≥1%, ≥2%, ≥3% absolute T+5 return in predicted direction
    actual = rec.get("actual_return_pct")  # same as t5, positive = good for direction
    ge1 = (actual >= 1.0)  if actual is not None else None
    ge2 = (actual >= 2.0)  if actual is not None else None
    ge3 = (actual >= 3.0)  if actual is not None else None

    # Knowledge provenance (decision-time info)
    prov = rec.get("knowledge_provenance") or {}
    regime = (
        prov.get("regime")
        or rec.get("regime")
        or str(rec.get("kda_evidence_state") or "")  # fallback
        or None
    )
    if regime:
        regime = str(regime).upper()

    return {
        # KFE / KSL compatibility header
        "event_type":    "EVIDENCE",
        "evidence_id":   str(uuid.uuid4()),
        # Source linkage and dedup key
        "source_run_id": f"{_LOL_SOURCE_PREFIX}{obs_id}",
        "observation_id": obs_id,
        # Identity
        "symbol":        symbol,
        "trade_date":    trade_date,
        "direction":     direction_ev,
        # Outcome fields (only available after OUTCOME_OBSERVED lifecycle state)
        "classification": classification,
        "miss_reason":   miss_reason,
        "t1_ret_pct":    t1,
        "t3_ret_pct":    t3,
        "t5_ret_pct":    t5,
        "mfe_pct":       mfe,
        "mae_pct":       mae,
        "ge1":           ge1,
        "ge2":           ge2,
        "ge3":           ge3,
        # Decision-time context (no lookahead)
        "kda_decision":  rec.get("kda_decision"),
        "kda_evidence_state": rec.get("kda_evidence_state"),
        "outcome_class": rec.get("outcome_class"),
        "authorization_source": rec.get("authorization_source"),
        "regime":        regime,
        # Provenance
        "source":        "lol_live",
        # no_lookahead defaults True because the bridge verifies timestamps
        # (outcome_at > decision_at) before calling _build_evidence_record().
        # Only override to False when the source LOL record explicitly set it False.
        "no_lookahead":  bool(rec.get("no_lookahead", True)),
        "recorded_at":   datetime.now(timezone.utc).isoformat(),
        # Universal lineage ID — threads from scanner through all stores
        # D9-007: do not propagate empty lineage ID — warn instead of silently writing None
        "opportunity_id": rec.get("opportunity_id") or None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# State and dedup helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_existing_keys(ledger_path: Path) -> Set[str]:
    """Return set of source_run_ids already in the knowledge evidence ledger."""
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

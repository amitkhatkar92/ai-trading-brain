"""
hkap/hkap_idr_evidence_bridge.py
==================================
HKAP-001 -> IDR: automatic evidence-gated promotion of HKAP's own
cross-year consensus DNA (CrossYearAnalyzer output, CON-xxxxxx ids)
into the live Institutional DNA Repository.

BACKGROUND: HKAPEngine.request_live_merge() previously always raised
("Live IDR merge is not automatic... use ScientificDirector.approve_study()
with a merge study plan") -- but no such merge-study-plan flow was ever
built, so this was a permanent dead end, not a working manual gate. Per
explicit user direction (2026-09-21): a human-approval requirement is
inconsistent with every other self-learning module in this codebase
(KDA-CRE-001, RSL-001, debate-weight-refinement, regime-map-refinement,
kde_idr_evidence_bridge, etc.) -- all of them promote automatically once
evidence clears a pre-registered, computed bar. This module gives HKAP's
own consensus DNA the same treatment, reusing CrossYearAnalyzer's
already-computed, unchanged lifecycle/survival statistics -- no new
statistical logic is invented here.

Auto-promotion requires ALL of (fully computed, zero subjective input):
  1. lifecycle_label in ALLOWED_LIFECYCLE (STABLE or STRENGTHENING only --
     never EMERGING [too new], WEAKENING/DISAPPEARING/SPORADIC [degrading
     or inconclusive]).
  2. survival_score >= MIN_SURVIVAL_SCORE (0.75 -- mirrors the "STABLE"
     definition and HKAP's own Tier-1 report bar, not a new number).
  3. len(years_present) >= MIN_YEARS_PRESENT -- guards against a pattern
     "surviving" 2-for-2 years by chance looking identical to one with a
     much longer real track record.
  4. The SAME dna_id is independently reconfirmed across >= MIN_CONFIRMATIONS
     (2) separate synthesis runs, each with a years_present set that
     genuinely differs from the previous observation (a re-run over
     identical data proves nothing new).
  5. No observation's survival_score drops by more than
     DEGRADATION_TOLERANCE versus the immediately preceding observation.
When all hold, evaluate_cross_year_records_for_idr_evidence() ITSELF
calls IDRRepository.save()+add_evidence() automatically -- no human names
a dna_id. Each dna_id merges at most ONCE ever (bounds total irreversible
writes). Evidence is bounded: confidence/effect_size capped at
MAX_EVIDENCE_CONFIDENCE (0.30) so one HKAP finding can never dominate a
DNA record's aggregate confidence -- identical bound to
kde_idr_evidence_bridge.py, for consistency across the ecosystem.

request_live_merge(dna_id) remains available as a manual override/escape
hatch (mirrors kde_idr_evidence_bridge.py's own escape hatch) but is not
required, and nothing in this repo calls it automatically.

Safety contract: bounded, append-only, at-most-once-per-pattern writes.
Zero imports from execution_engine, order_manager, broker APIs,
risk_control, or knowledge_authority. Never raises from the automated path.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT              = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BRIDGE_DIR        = os.path.join(_ROOT, "data", "hkap")
_PROPOSALS_FILE    = os.path.join(_BRIDGE_DIR, "idr_evidence_proposals.jsonl")
_MERGE_LEDGER_FILE = os.path.join(_BRIDGE_DIR, "idr_evidence_merge_ledger.jsonl")

MIN_SURVIVAL_SCORE      = 0.75   # mirrors DNALifecycleLabel.STABLE's own bar
MIN_YEARS_PRESENT       = 4      # requires a real multi-year track record
ALLOWED_LIFECYCLE       = ("STABLE", "STRENGTHENING")
MIN_CONFIRMATIONS       = 2      # independent synthesis runs required before auto-merge
DEGRADATION_TOLERANCE   = 0.05   # max allowed survival_score drop vs prior observation
MAX_EVIDENCE_CONFIDENCE = 0.30   # bounded contribution -- cannot dominate a DNA record
MAX_EVIDENCE_SAMPLE     = 50     # bounded sample_size proxy

STATUS_SHADOW = "SHADOW"
STATUS_ACTIVE = "ACTIVE"


def evaluate_cross_year_records_for_idr_evidence(dna_records: List[Any]) -> List[Dict[str, Any]]:
    """
    Full VALIDATION+SYNTHESIS+PROPAGATION+GOVERNANCE pass over HKAP's own
    CrossYearAnalyzer output (List[CrossYearDNARecord]).

    Automatically merges into the real IDR store any dna_id that has just
    met all reproducibility criteria on THIS call -- no human names a
    pattern. Returns the list of proposals newly created OR newly
    auto-merged this call (empty on any error or if nothing changed).
    Never raises.
    """
    try:
        return _evaluate_impl(dna_records)
    except Exception as exc:
        log.debug("[HKAPIDREvidenceBridge] evaluate error: %s", exc)
        return []


def _evaluate_impl(dna_records: List[Any]) -> List[Dict[str, Any]]:
    proposals = _read_jsonl(_PROPOSALS_FILE)
    by_key: Dict[str, Dict[str, Any]] = {p["dna_id"]: p for p in proposals}
    changed: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for r in dna_records:
        lifecycle_label = getattr(r, "lifecycle_label", "")
        if lifecycle_label not in ALLOWED_LIFECYCLE:
            continue
        survival_score = float(getattr(r, "survival_score", 0.0))
        if survival_score < MIN_SURVIVAL_SCORE:
            continue
        years_present = sorted(getattr(r, "years_present", []) or [])
        if len(years_present) < MIN_YEARS_PRESENT:
            continue

        dna_id = getattr(r, "dna_id", "")
        if not dna_id:
            continue

        observation = {
            "recorded_at":       now_iso,
            "lifecycle_label":   lifecycle_label,
            "survival_score":    survival_score,
            "years_present":     years_present,
            "regimes_observed":  list(getattr(r, "regimes_observed", []) or []),
            "confidence_trend":  getattr(r, "confidence_trend", ""),
        }

        record = by_key.get(dna_id)
        if record is None:
            record = {
                "dna_id":       dna_id,
                "feature_name": getattr(r, "feature_name", dna_id),
                "direction":    getattr(r, "direction", ""),
                "status":       STATUS_SHADOW,
                "observations": [observation],
                "merged":       False,
                "merged_at":    None,
                "merged_by":    None,
            }
            by_key[dna_id] = record
            changed.append(record)
            continue

        if record["status"] == STATUS_ACTIVE:
            # already merged once -- keep monitoring for audit only,
            # never merges again (bounds total irreversible writes).
            record["observations"].append(observation)
            changed.append(record)
            continue

        # duplicate observation from an identical years_present set does
        # not count as an independent reproducibility confirmation.
        last = record["observations"][-1]
        if last.get("years_present") == years_present:
            continue

        record["observations"].append(observation)
        record["status"] = STATUS_SHADOW

        if _meets_auto_promotion_criteria(record["observations"]):
            if _do_live_merge(dna_id, record):
                record["status"] = STATUS_ACTIVE
                record["merged"] = True
                record["merged_at"] = now_iso
                record["merged_by"] = "auto:hkap_idr_evidence_bridge"
                _append_jsonl(_MERGE_LEDGER_FILE, [record])

        changed.append(record)

    if changed:
        _write_jsonl(_PROPOSALS_FILE, list(by_key.values()))
    return changed


def _meets_auto_promotion_criteria(observations: List[Dict[str, Any]]) -> bool:
    if len(observations) < MIN_CONFIRMATIONS:
        return False
    for obs in observations:
        if obs["survival_score"] < MIN_SURVIVAL_SCORE:
            return False
        if obs["lifecycle_label"] not in ALLOWED_LIFECYCLE:
            return False
    for prev, cur in zip(observations, observations[1:]):
        if cur["survival_score"] < prev["survival_score"] - DEGRADATION_TOLERANCE:
            return False
    years_sets = [tuple(o["years_present"]) for o in observations]
    if len(set(years_sets)) < MIN_CONFIRMATIONS:
        return False  # every observation used the identical year set -- no real confirmation
    return True


def _do_live_merge(dna_id: str, record: Dict[str, Any]) -> bool:
    try:
        from market_learning.idr_repository import IDRRepository
        from market_learning.idr_models import DNAEvidence, InstitutionalDNA, IDRNotFoundError

        latest = record["observations"][-1]
        bounded_confidence = round(min(latest["survival_score"], MAX_EVIDENCE_CONFIDENCE), 4)
        sample_size = min(len(latest["years_present"]) * 10, MAX_EVIDENCE_SAMPLE)
        now = datetime.now(timezone.utc).isoformat()
        repo = IDRRepository()

        try:
            repo.get(dna_id)
        except IDRNotFoundError:
            direction = record.get("direction", "") or ""
            category = "WINNER" if direction.upper().startswith("WINNERS") else "NEUTRAL"
            dna = InstitutionalDNA(
                id=dna_id,
                feature_name=record.get("feature_name", dna_id),
                direction=direction,
                category=category,
                lifecycle="DISCOVERED",
                version=0,
                consensus_score=bounded_confidence,
                confidence=bounded_confidence,
                effect_size=bounded_confidence,
                regime_consistency=0.0,
                sector_consistency=0.0,
                temporal_stability=bounded_confidence,
                replication_frequency=bounded_confidence,
                evidence_count=len(record["observations"]),
                regime_counts={},
                last_seen=now,
                study_id=f"HKAP-{dna_id}",
                source="hkap_idr_evidence_bridge",
                created_at=now,
                updated_at=now,
                is_current=True,
                metadata={
                    "years_present": latest["years_present"],
                    "regimes_observed": latest["regimes_observed"],
                },
            )
            repo.save(dna, study_id=f"HKAP-{dna_id}", operator="auto:hkap_idr_evidence_bridge")

        ev = DNAEvidence(
            dna_id=dna_id,
            dna_version=0,
            study_id=f"HKAP-{dna_id}",
            source="hkap_idr_evidence_bridge",
            sample_size=sample_size,
            effect_size=bounded_confidence,
            confidence=bounded_confidence,
            regime=(latest["regimes_observed"][0] if latest["regimes_observed"] else ""),
            sector="",
            observation_date=now[:10],
            metadata={
                "confirmations": len(record["observations"]),
                "lifecycle_label": latest["lifecycle_label"],
                "survival_score": latest["survival_score"],
            },
        )
        repo.add_evidence(dna_id, ev)
        return True
    except Exception as exc:
        log.debug("[HKAPIDREvidenceBridge] auto-merge failed for %s: %s", dna_id, exc)
        return False


def get_pending_proposals(dna_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read-only: SHADOW proposals not yet auto-merged into the real IDR store."""
    proposals = [p for p in _read_jsonl(_PROPOSALS_FILE) if not p.get("merged")]
    if dna_id is not None:
        proposals = [p for p in proposals if p["dna_id"] == dna_id]
    return proposals


def get_merge_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only: last n live-merge events (oldest-first)."""
    return _read_jsonl(_MERGE_LEDGER_FILE)[-n:]


def request_live_merge(dna_id: str, operator: str = "manual") -> bool:
    """
    Manual override / escape hatch -- NOT the primary path (see module
    docstring). Forces an immediate merge of the given dna_id's latest
    pending proposal, bypassing the reproducibility wait. Returns False
    if no such pending proposal exists or the write fails.
    """
    try:
        proposals = _read_jsonl(_PROPOSALS_FILE)
        match = None
        idx = None
        for i, p in enumerate(proposals):
            if p["dna_id"] == dna_id and not p.get("merged"):
                match, idx = p, i
                break
        if match is None:
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        if _do_live_merge(dna_id, match):
            match["status"] = STATUS_ACTIVE
            match["merged"] = True
            match["merged_at"] = now_iso
            match["merged_by"] = f"manual:{operator}"
            proposals[idx] = match
            _write_jsonl(_PROPOSALS_FILE, proposals)
            _append_jsonl(_MERGE_LEDGER_FILE, [match])
            return True
        return False
    except Exception as exc:
        log.debug("[HKAPIDREvidenceBridge] request_live_merge error for %s: %s", dna_id, exc)
        return False


# ── JSONL helpers ───────────────────────────────────────────────────────────

def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except Exception:
        return []


def _write_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _append_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

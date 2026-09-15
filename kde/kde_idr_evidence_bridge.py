"""
kde/kde_idr_evidence_bridge.py
================================
Self-Learning Ecosystem -- Post-roadmap Item 4: KDE Discovery -> IDR
evidence bridge.

Structural design (confirmed via schema audit before writing any code):
kde/kde_models.py's Discovery objects carry `dna_ids` -- real IDR dna_id
keys -- so IDRRepository.add_evidence(dna_id, DNAEvidence) (a REAL,
existing, well-shaped method) is the correct target, unlike the
fabricated add_observation() call PGA's Category B used to call (see
predictive_gap/pga_idr_bridge.py's docstring for that unrelated fix).

SAFETY-CRITICAL DIFFERENCE FROM EVERY OTHER BRIDGE IN THIS ECOSYSTEM:
IDRRepository is NOT a dormant/research-only sink. market_learning
.pig_gateway.PlatformIntelligenceGateway reads IDR DNA confidence/
consensus_score/evidence_count directly, and orchestrator
.master_orchestrator.py calls pig_enrich_signals()/pig_build_vote() in
the LIVE trading cycle. Writing evidence into IDR is therefore a
live-trading-decision-consequential, IRREVERSIBLE action (IDR evidence
is append-only -- there is no "remove evidence" method to undo a bad
write).

DESIGN PRINCIPLE (revised 2026-09-15 per explicit user direction): this
ecosystem exists precisely so decisions like "should this evidence go
live" are made autonomously from computed, authenticated evidence --
not by an admin manually naming which discovery/dna_id pairs to merge.
The gate is therefore not "ask a human", it is REPRODUCIBILITY ACROSS
INDEPENDENT RE-RUNS WITH GENUINELY NEW DATA -- the strongest automatic
validation signal available for this kind of cross-year discovery, and
consistent with the "never shuffled, time-ordered, minimum sample"
discipline already used by every other automated gate in this ecosystem
(RHV-001, KDA-CRE-001, RSL-001).

Auto-promotion requires ALL of (fully computed, zero subjective input):
  1. discovery.score.overall >= MIN_OVERALL_SCORE on every observation.
  2. The SAME (scheme_id, dna_id) pattern is independently re-observed
     across >= MIN_CONFIRMATIONS (2) separate KDE runs.
  3. Each re-observation's years_used set DIFFERS from the previous one
     (i.e. genuinely new underlying HKAP data, not the same deterministic
     computation re-run on identical input -- which would prove nothing).
  4. No observed score ever drops by more than DEGRADATION_TOLERANCE
     versus the immediately preceding observation (guards against
     promoting a weakening pattern).
When all 4 hold, evaluate_discoveries_for_idr_evidence() ITSELF calls
IDRRepository.add_evidence() automatically -- no human names a pair,
no separate approval call. Each (scheme_id, dna_id) pair is merged at
most ONCE ever (bounds total irreversible writes even under many future
re-runs). Evidence is always bounded: confidence/effect_size capped at
MAX_EVIDENCE_CONFIDENCE (0.30) so a single discovery can never dominate
an existing DNA record's aggregate confidence.

request_live_merge() remains available as a manual override/escape
hatch (e.g. for a human who wants to force one pair immediately) but is
no longer the primary path -- the automated path above is.

KBL stages:
  ACQUISITION  : evaluate_discoveries_for_idr_evidence() reads Discovery
               objects + the run's years_used, already produced by
               hkap_kde_bridge.py (no new computation, no download).
  VALIDATION   : score gate + cross-run reproducibility-with-new-data
               gate + non-degradation gate (all above).
  SYNTHESIS    : builds a BOUNDED DNAEvidence proposal.
  PROPAGATION  : full observation history persisted to
               data/kde/idr_evidence_proposals.jsonl (gitignored).
  GOVERNANCE   : automatic promotion when all 4 criteria hold -- the
               ONLY human-in-the-loop option is the manual override
               request_live_merge(), never required for normal
               operation.

Safety contract: bounded, append-only, at-most-once-per-pattern writes.
Zero imports from execution_engine, order_manager, broker APIs,
risk_control. Never raises from the automated path.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT              = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BRIDGE_DIR        = os.path.join(_ROOT, "data", "kde")
_PROPOSALS_FILE    = os.path.join(_BRIDGE_DIR, "idr_evidence_proposals.jsonl")
_MERGE_LEDGER_FILE = os.path.join(_BRIDGE_DIR, "idr_evidence_merge_ledger.jsonl")

MIN_OVERALL_SCORE       = 0.60   # mirrors HKAPConfig.dna_edge_threshold
MAX_EVIDENCE_CONFIDENCE = 0.30   # bounded contribution -- cannot dominate a DNA record
MAX_EVIDENCE_SAMPLE     = 50     # bounded sample_size proxy
MIN_CONFIRMATIONS       = 2      # independent re-runs required before auto-merge
DEGRADATION_TOLERANCE   = 0.05   # max allowed score drop vs prior observation

STATUS_SHADOW = "SHADOW"
STATUS_ACTIVE = "ACTIVE"
STATUS_STALE  = "STALE"


def evaluate_discoveries_for_idr_evidence(
    discoveries: List[Any],
    years_used: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Full ACQUISITION+VALIDATION+SYNTHESIS+PROPAGATION+GOVERNANCE pass.

    Automatically merges into the real IDR store any (scheme_id, dna_id)
    pattern that has just met all 4 reproducibility criteria on THIS
    call -- no human names a pair. Returns the list of proposals that
    were newly created OR newly auto-merged this call (empty list on
    any error or if nothing changed). Never raises.
    """
    try:
        return _evaluate_impl(discoveries, years_used or [])
    except Exception as exc:
        log.debug("[KDEIDREvidenceBridge] evaluate error: %s", exc)
        return []


def _evaluate_impl(discoveries: List[Any], years_used: List[int]) -> List[Dict[str, Any]]:
    proposals = _read_jsonl(_PROPOSALS_FILE)
    by_key: Dict[tuple, Dict[str, Any]] = {(p["scheme_id"], p["dna_id"]): p for p in proposals}
    changed: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for d in discoveries:
        dna_ids = list(getattr(d, "dna_ids", []) or [])
        if not dna_ids:
            continue
        score_obj = getattr(d, "score", None)
        overall = float(getattr(score_obj, "overall", 0.0)) if score_obj is not None else 0.0
        if overall < MIN_OVERALL_SCORE:
            continue

        scheme_id = getattr(d, "scheme_id", "")
        regimes = list(getattr(d, "regimes_observed", []) or [])
        regime = regimes[0] if regimes else ""
        obs_date = str(getattr(d, "generated_at", "") or now_iso)[:10]
        bounded_confidence = round(min(overall, MAX_EVIDENCE_CONFIDENCE), 4)
        bounded_effect_size = round(min(overall, MAX_EVIDENCE_CONFIDENCE), 4)
        sample_size = min(len(getattr(d, "years_observed", []) or []) * 10, MAX_EVIDENCE_SAMPLE)

        observation = {
            "recorded_at":      now_iso,
            "discovery_id":     getattr(d, "discovery_id", ""),
            "overall_score":    overall,
            "years_used":       sorted(years_used) if years_used else [],
            "confidence":       bounded_confidence,
            "effect_size":      bounded_effect_size,
            "sample_size":      sample_size,
            "regime":           regime,
            "observation_date": obs_date,
            "question":         getattr(d, "question", ""),
            "answer":           getattr(d, "answer", ""),
        }

        for dna_id in dna_ids:
            key = (scheme_id, dna_id)
            record = by_key.get(key)

            if record is None:
                record = {
                    "scheme_id":    scheme_id,
                    "dna_id":       dna_id,
                    "status":       STATUS_SHADOW,
                    "observations": [observation],
                    "merged":       False,
                    "merged_at":    None,
                    "merged_by":    None,
                }
                by_key[key] = record
                changed.append(record)
                continue

            if record["status"] == STATUS_ACTIVE:
                # already merged once -- keep monitoring for audit only,
                # never merges again (bounds total irreversible writes).
                record["observations"].append(observation)
                changed.append(record)
                continue

            # duplicate observation from the same run (identical years_used
            # as the most recent one) does not count as an independent
            # reproducibility confirmation.
            last = record["observations"][-1]
            if last.get("years_used") == observation["years_used"]:
                continue

            record["observations"].append(observation)
            record["status"] = STATUS_SHADOW

            if _meets_auto_promotion_criteria(record["observations"]):
                if _do_live_merge(dna_id, record):
                    record["status"] = STATUS_ACTIVE
                    record["merged"] = True
                    record["merged_at"] = now_iso
                    record["merged_by"] = "auto:kde_idr_evidence_bridge"
                    _append_jsonl(_MERGE_LEDGER_FILE, [record])

            changed.append(record)

    if changed:
        _write_jsonl(_PROPOSALS_FILE, list(by_key.values()))
    return changed


def _meets_auto_promotion_criteria(observations: List[Dict[str, Any]]) -> bool:
    if len(observations) < MIN_CONFIRMATIONS:
        return False
    for obs in observations:
        if obs["overall_score"] < MIN_OVERALL_SCORE:
            return False
    for prev, cur in zip(observations, observations[1:]):
        if cur["overall_score"] < prev["overall_score"] - DEGRADATION_TOLERANCE:
            return False
    years_sets = [tuple(o["years_used"]) for o in observations]
    if len(set(years_sets)) < MIN_CONFIRMATIONS:
        return False  # every observation used the identical dataset -- no real confirmation
    return True


def _do_live_merge(dna_id: str, record: Dict[str, Any]) -> bool:
    try:
        from market_learning.idr_repository import IDRRepository
        from market_learning.idr_models import DNAEvidence

        latest = record["observations"][-1]
        repo = IDRRepository()
        ev = DNAEvidence(
            dna_id=dna_id,
            dna_version=0,
            study_id=f"KDE-{latest['discovery_id']}",
            source=f"kde_idr_evidence_bridge:{record['scheme_id']}",
            sample_size=latest["sample_size"],
            effect_size=latest["effect_size"],
            confidence=latest["confidence"],
            regime=latest["regime"],
            sector="",
            observation_date=latest["observation_date"],
            metadata={
                "scheme_id": record["scheme_id"],
                "confirmations": len(record["observations"]),
                "question": latest.get("question", ""),
                "answer": latest.get("answer", ""),
            },
        )
        repo.add_evidence(dna_id, ev)
        return True
    except Exception as exc:
        log.debug("[KDEIDREvidenceBridge] auto-merge failed for %s: %s", dna_id, exc)
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


def request_live_merge(scheme_id: str, dna_id: str, operator: str = "manual") -> bool:
    """
    Manual override / escape hatch -- NOT the primary path (see module
    docstring). Forces an immediate merge of the given (scheme_id,
    dna_id) proposal's latest observation, bypassing the reproducibility
    wait. Returns False if no such pending proposal exists or the write
    fails.
    """
    try:
        proposals = _read_jsonl(_PROPOSALS_FILE)
        match = None
        idx = None
        for i, p in enumerate(proposals):
            if p["scheme_id"] == scheme_id and p["dna_id"] == dna_id and not p.get("merged"):
                match, idx = p, i
                break
        if match is None:
            return False

        if not _do_live_merge(dna_id, match):
            return False

        proposals[idx]["status"] = STATUS_ACTIVE
        proposals[idx]["merged"] = True
        proposals[idx]["merged_at"] = datetime.now(timezone.utc).isoformat()
        proposals[idx]["merged_by"] = operator
        _write_jsonl(_PROPOSALS_FILE, proposals)
        _append_jsonl(_MERGE_LEDGER_FILE, [proposals[idx]])
        return True
    except Exception as exc:
        log.debug("[KDEIDREvidenceBridge] request_live_merge error for %s/%s: %s",
                  scheme_id, dna_id, exc)
        return False


# ── jsonl helpers ──────────────────────────────────────────────────────────

def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    records: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _append_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")


def _write_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")

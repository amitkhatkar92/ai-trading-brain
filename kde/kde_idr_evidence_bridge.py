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
write, unlike RSL-001's adjustments or KDA-CRE-001's constants which
both have an explicit ROLLED_BACK transition).

Given that irreversibility, this module deliberately follows the EXACT
existing precedent already established in this codebase for this exact
class of risk: HKAPConfig.merge_to_live_idr (default False) + an
explicit, separately-invoked HKAPEngine.request_live_merge() gate. This
module:
  - fully automates PROPOSAL generation (ACQUISITION/VALIDATION/
    SYNTHESIS/PROPAGATION-to-shadow) with zero human step -- safe,
    because nothing here writes to the real IDR store yet.
  - requires an explicit, separate call to request_live_merge() to
    actually write to IDR.add_evidence() -- this is NEVER called
    automatically from any scheduler/EOD loop in this codebase. A human
    (or a future, separately-approved automation) must invoke it
    deliberately, one discovery+dna_id pair at a time.

KBL stages:
  ACQUISITION  : evaluate_discoveries_for_idr_evidence() reads Discovery
               objects already produced by hkap_kde_bridge.py (no new
               computation, no download).
  VALIDATION   : gates on discovery.score.overall >= MIN_OVERALL_SCORE
               (mirrors HKAPConfig.dna_edge_threshold=0.60's convention)
               and requires >=1 real dna_id reference. No new
               statistical machinery invented.
  SYNTHESIS    : builds a BOUNDED DNAEvidence proposal -- confidence and
               effect_size are both capped at MAX_EVIDENCE_CONFIDENCE
               (0.3) so a single KDE discovery can never dominate an
               existing DNA record's aggregate confidence, even if
               merged.
  PROPAGATION  : proposals are appended to
               data/kde/idr_evidence_proposals.jsonl (shadow-only,
               gitignored, never read by any live path).
  GOVERNANCE   : the actual live IDR write requires the explicit,
               separately-invoked request_live_merge() -- deliberately
               NOT wired into any automatic loop.

Safety contract: evaluate_discoveries_for_idr_evidence() and every
read-only accessor here NEVER write to IDR. Only request_live_merge()
does, and only when a caller explicitly names one discovery_id+dna_id
pair. Zero imports from execution_engine, order_manager, broker APIs,
risk_control. Never raises from the automated (shadow) path.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT             = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BRIDGE_DIR       = os.path.join(_ROOT, "data", "kde")
_PROPOSALS_FILE   = os.path.join(_BRIDGE_DIR, "idr_evidence_proposals.jsonl")
_MERGE_LEDGER_FILE = os.path.join(_BRIDGE_DIR, "idr_evidence_merge_ledger.jsonl")

MIN_OVERALL_SCORE       = 0.60   # mirrors HKAPConfig.dna_edge_threshold
MAX_EVIDENCE_CONFIDENCE = 0.30   # bounded contribution -- cannot dominate a DNA record
MAX_EVIDENCE_SAMPLE     = 50     # bounded sample_size proxy


def evaluate_discoveries_for_idr_evidence(discoveries: List[Any]) -> List[Dict[str, Any]]:
    """
    ACQUISITION+VALIDATION+SYNTHESIS+PROPAGATION(shadow). Never writes to
    IDR. Returns the list of newly recorded proposals (empty list on any
    error or if nothing qualifies). Never raises.
    """
    try:
        return _evaluate_impl(discoveries)
    except Exception as exc:
        log.debug("[KDEIDREvidenceBridge] evaluate error: %s", exc)
        return []


def _evaluate_impl(discoveries: List[Any]) -> List[Dict[str, Any]]:
    existing_keys = {(p["discovery_id"], p["dna_id"]) for p in _read_jsonl(_PROPOSALS_FILE)}
    new_proposals: List[Dict[str, Any]] = []

    for d in discoveries:
        dna_ids = list(getattr(d, "dna_ids", []) or [])
        if not dna_ids:
            continue
        overall = float(getattr(d.score, "overall", 0.0))
        if overall < MIN_OVERALL_SCORE:
            continue

        regimes = list(getattr(d, "regimes_observed", []) or [])
        regime = regimes[0] if regimes else ""
        obs_date = str(getattr(d, "generated_at", "") or datetime.now(timezone.utc).isoformat())[:10]
        bounded_confidence = round(min(overall, MAX_EVIDENCE_CONFIDENCE), 4)
        bounded_effect_size = round(min(overall, MAX_EVIDENCE_CONFIDENCE), 4)
        sample_size = min(len(getattr(d, "years_observed", []) or []) * 10, MAX_EVIDENCE_SAMPLE)

        for dna_id in dna_ids:
            key = (d.discovery_id, dna_id)
            if key in existing_keys:
                continue
            proposal = {
                "discovery_id":    d.discovery_id,
                "dna_id":          dna_id,
                "scheme_id":       getattr(d, "scheme_id", ""),
                "study_id":        f"KDE-{d.discovery_id}",
                "source":          f"kde_idr_evidence_bridge:{getattr(d, 'scheme_id', '')}",
                "sample_size":     sample_size,
                "effect_size":     bounded_effect_size,
                "confidence":      bounded_confidence,
                "regime":          regime,
                "sector":          "",
                "observation_date": obs_date,
                "overall_score":   overall,
                "question":        getattr(d, "question", ""),
                "answer":          getattr(d, "answer", ""),
                "years_observed":  list(getattr(d, "years_observed", []) or []),
                "recorded_at":     datetime.now(timezone.utc).isoformat(),
                "merged":          False,
            }
            new_proposals.append(proposal)
            existing_keys.add(key)

    if new_proposals:
        _append_jsonl(_PROPOSALS_FILE, new_proposals)
    return new_proposals


def get_pending_proposals(dna_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read-only: proposals not yet merged into the real IDR store."""
    proposals = [p for p in _read_jsonl(_PROPOSALS_FILE) if not p.get("merged")]
    if dna_id is not None:
        proposals = [p for p in proposals if p["dna_id"] == dna_id]
    return proposals


def get_merge_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only: last n live-merge events (oldest-first)."""
    return _read_jsonl(_MERGE_LEDGER_FILE)[-n:]


def request_live_merge(discovery_id: str, dna_id: str, operator: str = "manual") -> bool:
    """
    GOVERNANCE gate: the ONLY function in this module that writes to the
    real, live-consequential IDRRepository. Never called automatically
    by any scheduler/EOD loop in this codebase -- must be invoked
    explicitly, one discovery+dna_id pair at a time, by a human or a
    future, separately-approved automation.

    Returns True on a successful, real IDR write. False if the proposal
    doesn't exist, is already merged, or the write fails.
    """
    try:
        proposals = _read_jsonl(_PROPOSALS_FILE)
        match = None
        idx = None
        for i, p in enumerate(proposals):
            if p["discovery_id"] == discovery_id and p["dna_id"] == dna_id and not p.get("merged"):
                match, idx = p, i
                break
        if match is None:
            return False

        from market_learning.idr_repository import IDRRepository
        from market_learning.idr_models import DNAEvidence

        repo = IDRRepository()
        ev = DNAEvidence(
            dna_id=dna_id,
            dna_version=0,
            study_id=match["study_id"],
            source=match["source"],
            sample_size=match["sample_size"],
            effect_size=match["effect_size"],
            confidence=match["confidence"],
            regime=match["regime"],
            sector=match["sector"],
            observation_date=match["observation_date"],
            metadata={
                "discovery_id": discovery_id,
                "scheme_id": match.get("scheme_id", ""),
                "question": match.get("question", ""),
                "answer": match.get("answer", ""),
            },
        )
        repo.add_evidence(dna_id, ev)

        proposals[idx]["merged"] = True
        proposals[idx]["merged_at"] = datetime.now(timezone.utc).isoformat()
        proposals[idx]["merged_by"] = operator
        _write_jsonl(_PROPOSALS_FILE, proposals)
        _append_jsonl(_MERGE_LEDGER_FILE, [proposals[idx]])
        return True
    except Exception as exc:
        log.debug("[KDEIDREvidenceBridge] request_live_merge error for %s/%s: %s",
                  discovery_id, dna_id, exc)
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

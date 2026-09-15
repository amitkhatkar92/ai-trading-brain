"""
autonomous_research/ars_scheduler.py
=======================================
Self-Learning Ecosystem -- Post-roadmap Priority 1: activates the 9-agent
autonomous_research (ARS) cluster that was fully built (12 agents, 190+
tests each) but never invoked in production.

Audit finding (before writing a single line of new logic): the entire
autonomous decision chain already exists and is already tested --
ScientificDirector.daily_review()/weekly_review() already auto-generates
hypotheses for open gaps (`_generate_hypotheses_for_gaps`) and
auto-approves low-risk "Class A" study plans (SDConfig.auto_approve_
class_a=True by default), which on approval directly calls
ResearchCoordinator.run_research(plan) (see scientific_director.py's own
approve_study()). StudyPlanner.create_from_entry()/create_from_gap()
already exist to turn a prioritized RoadmapEntry/KnowledgeGap into a
StudyPlan. Nothing here invents new statistical/governance logic -- the
only real gap was that NOTHING in production ever constructed these
components together and called them. This module is pure wiring plus a
self-scheduling cadence guard, reusing 100% existing, already-tested
autonomous_research logic.

Components wired (all real, all independently already tested):
  KnowledgeProvider, HypothesisRegistry, GapDetector, RoadmapManager,
  EvidenceValidator, CrossStudySynthesizer, StudyPlanner,
  ResearchCoordinator, ScientificDirector, IDRRepository.

Post-Priority-1 addendum (Priority 2): after each real weekly review,
also calls ikn.ikn_research_bridge.sync_hypotheses_to_ikn() -- mirrors
every hypothesis (and its knowledge_gap) into IKNNetwork as real graph
data (previously an always-empty, never-populated store). Try/except
-wrapped, non-fatal, never blocks the cycle's own summary/history write.

Cadence: WEEKLY, not daily -- deep research is not a daily-trading
event (same precedent as HKAP/KDE). Self-scheduling and evidence-driven:
checks its own run-history log for the last REAL run date and skips
silently if fewer than MIN_DAYS_BETWEEN_RUNS have elapsed. No external
scheduler config needed, no human trigger required.

Safety:
  - ScientificDirector's own Class A/B safety boundary is untouched:
    only low-risk, non-META_LEARNING/CUSTOM study types auto-execute;
    everything else stays PENDING for a human (Class B) -- exactly as
    designed by this cluster's original authors, not weakened here.
  - Hypotheses created by this cluster are gap-based (subject_type left
    unset) -- they do NOT feed into KDA's get_confirmed_adjustment()
    bridge (which only reads subject_type=="SYMBOL" hypotheses). This
    cluster surfaces broader research findings for review; it does not
    silently retune any live trading signal.
  - ResearchCoordinator's repository_update stage is read-only
    (confirmed via source inspection: only .statistics()/.list_active()/
    .list_studies()/.list_edges() calls -- zero IDR writes).
  - All new output is append-only, isolated under data/ars/scheduler/.
  - Never raises.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RUN_DIR     = os.path.join(_ROOT, "data", "ars", "scheduler")
_RUN_HISTORY = os.path.join(_RUN_DIR, "run_history.jsonl")

MIN_DAYS_BETWEEN_RUNS = 7   # weekly cadence -- research is not a daily event
MAX_GAPS_TO_PLAN      = 5   # bounded per cycle, mirrors SDConfig.max_plans_per_review


def run_autonomous_research_cycle(force: bool = False) -> Dict[str, Any]:
    """
    Self-scheduling entry point. Skips (status=SKIPPED_TOO_SOON) unless
    >= MIN_DAYS_BETWEEN_RUNS have elapsed since the last real run, or
    force=True. Never raises.
    """
    try:
        return _run_impl(force)
    except Exception as exc:
        log.debug("[ARSScheduler] cycle error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl(force: bool) -> Dict[str, Any]:
    last = _last_real_run_at()
    if not force and last is not None:
        days_since = (datetime.now(timezone.utc) - last).days
        if days_since < MIN_DAYS_BETWEEN_RUNS:
            return {
                "status": "SKIPPED_TOO_SOON",
                "days_since_last_run": days_since,
                "min_days_required": MIN_DAYS_BETWEEN_RUNS,
            }

    from autonomous_research.knowledge_provider import KnowledgeProvider
    from autonomous_research.hypothesis_registry import HypothesisRegistry
    from autonomous_research.gap_detector import GapDetector
    from autonomous_research.roadmap_manager import RoadmapManager
    from autonomous_research.evidence_validator import EvidenceValidator
    from autonomous_research.cross_study_synthesizer import CrossStudySynthesizer
    from autonomous_research.study_planner import StudyPlanner
    from autonomous_research.research_coordinator import ResearchCoordinator
    from autonomous_research.rc_config import RCConfig
    from autonomous_research.scientific_director import ScientificDirector
    from autonomous_research.sd_config import SDConfig
    from market_learning.idr_repository import IDRRepository

    kp    = KnowledgeProvider()
    reg   = HypothesisRegistry(knowledge_provider=kp)
    gd    = GapDetector(knowledge_provider=kp, hypothesis_registry=reg)
    synth = CrossStudySynthesizer(knowledge_provider=kp, hypothesis_registry=reg)
    rm    = RoadmapManager(knowledge_provider=kp, hypothesis_registry=reg,
                            synthesizer=synth, gap_detector=gd)
    ev    = EvidenceValidator(knowledge_provider=kp, hypothesis_registry=reg,
                               synthesizer=synth, gap_detector=gd, roadmap_manager=rm)
    sp    = StudyPlanner(knowledge_provider=kp, hypothesis_registry=reg,
                          gap_detector=gd, roadmap_manager=rm, evidence_validator=ev)
    idr   = IDRRepository()
    rc    = ResearchCoordinator(planner=sp, hypothesis_registry=reg, evidence_validator=ev,
                                 knowledge_provider=kp, synthesizer=synth, gap_detector=gd,
                                 roadmap_manager=rm, idr=idr, config=RCConfig())
    sd    = ScientificDirector(knowledge_provider=kp, hypothesis_registry=reg, gap_detector=gd,
                                roadmap_manager=rm, evidence_validator=ev, study_planner=sp,
                                synthesizer=synth, rc=rc, idr=idr, config=SDConfig())

    # RoadmapManager.build() calls gap_detector.detect() internally if no
    # gaps are passed -- this activates BOTH GapDetector and RoadmapManager.
    roadmap = rm.build(force=True)
    top_entries = rm.top_priorities(MAX_GAPS_TO_PLAN)

    existing_gap_ids = {
        p.source_gap_id for p in sp.list_plans() if p.source_gap_id
    }
    plans_created = 0
    for entry in top_entries:
        gap_id = entry.gap.gap_id
        if gap_id in existing_gap_ids:
            continue
        try:
            sp.create_from_entry(entry)
            plans_created += 1
        except Exception as exc:
            log.debug("[ARSScheduler] plan creation failed for gap %s: %s", gap_id, exc)

    # ScientificDirector.weekly_review(): generates hypotheses for open
    # gaps + auto-approves Class A plans (which delegates them to
    # ResearchCoordinator.run_research() internally) -- fully automatic,
    # zero human step, using this cluster's own pre-existing logic.
    review = sd.weekly_review()

    try:
        from ikn.ikn_research_bridge import sync_hypotheses_to_ikn
        ikn_sync = sync_hypotheses_to_ikn()
    except Exception as exc:
        log.debug("[ARSScheduler] IKN sync skipped: %s", exc)
        ikn_sync = {"status": "ERROR", "error": str(exc)}

    summary = {
        "status":            "OK",
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "total_gaps_open":   len(roadmap.entries),
        "plans_created":     plans_created,
        "review_id":         review.review_id,
        "review_health":     review.health.value,
        "observations":      len(review.observations),
        "decisions":         len(review.decisions),
        "decision_types":    [d.decision_type.value for d in review.decisions],
        "ikn_sync":          ikn_sync,
    }
    _record_run(summary)
    return summary


def _last_real_run_at() -> Optional[datetime]:
    for rec in reversed(_read_jsonl(_RUN_HISTORY)):
        if rec.get("status") == "OK":
            try:
                return datetime.fromisoformat(rec["generated_at"])
            except (KeyError, ValueError):
                continue
    return None


def get_last_run_summary() -> Optional[Dict[str, Any]]:
    """Read-only accessor (Sandy-style): most recent run record, or None."""
    records = _read_jsonl(_RUN_HISTORY)
    return records[-1] if records else None


def get_run_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only accessor: last n run records, oldest-first."""
    return _read_jsonl(_RUN_HISTORY)[-n:]


def _record_run(summary: Dict[str, Any]) -> None:
    try:
        os.makedirs(_RUN_DIR, exist_ok=True)
        with open(_RUN_HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")
    except OSError as exc:
        log.debug("[ARSScheduler] history write skipped: %s", exc)


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

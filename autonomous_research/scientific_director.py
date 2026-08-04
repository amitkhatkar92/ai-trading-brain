"""
scientific_director.py — Apex scientific authority of IIOS.

IIOS Research Infrastructure — Phase 3C.

The Scientific Director governs science.  It never performs science.

It observes knowledge, reasons about gaps and priorities, generates
hypotheses, approves studies, delegates execution, and reviews outcomes.
It never directly invokes research pipelines, learning engines, or
trading systems.

Constitutional authority: SCIENTIFIC_DIRECTOR_CONSTITUTION.md v1.0

Observation layer  → KnowledgeProvider, GapDetector, RoadmapManager,
                     CrossStudySynthesizer, RC, MLC, IDR, PIG
Reasoning layer    → evaluate completeness, evidence quality, research value,
                     information gain, scientific risk, cost, alignment
Decision layer     → hypotheses, roadmap updates, study approvals, escalations

All decisions are fully explained and recorded in the ScientificJournal.
No free-text logs.  Structured scientific memory only.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .sd_config import SDConfig
from .sd_models import (
    DecisionClass,
    DecisionType,
    SDError,
    SDHealth,
    ScientificDecision,
    ScientificHealth,
    ScientificObservation,
    ScientificReasoning,
    ScientificRecommendation,
    ScientificReview,
    ScientificRoadmap,
    SignificanceLevel,
    UrgencyLevel,
    _now_iso,
    make_decision_id,
    make_observation_id,
    make_recommendation_id,
    make_review_id,
    ReviewType,
)
from .scientific_journal import ScientificJournal

log = logging.getLogger(__name__)

# ─── gap severity ordering ───────────────────────────────────────────────────
_SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
_SEVERITY_THRESHOLD = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _severity_val(s: str) -> int:
    return _SEVERITY_ORDER.get(s.upper(), 0)


class ScientificDirector:
    """Apex scientific authority of IIOS.

    Parameters
    ----------
    knowledge_provider : KnowledgeProvider | None
    hypothesis_registry : HypothesisRegistry | None
    gap_detector : GapDetector | None
    roadmap_manager : RoadmapManager | None
    evidence_validator : EvidenceValidator | None
    study_planner : StudyPlanner | None
    synthesizer : CrossStudySynthesizer | None
    rc : ResearchCoordinator | None
    mlc : MarketLearningCoordinator | None
    idr : IDRRepository | None
    pig : PlatformIntelligenceGateway | None
    config : SDConfig | None
    """

    def __init__(
        self,
        knowledge_provider=None,
        hypothesis_registry=None,
        gap_detector=None,
        roadmap_manager=None,
        evidence_validator=None,
        study_planner=None,
        synthesizer=None,
        rc=None,
        mlc=None,
        idr=None,
        pig=None,
        config: Optional[SDConfig] = None,
    ) -> None:
        self._kp     = knowledge_provider
        self._reg    = hypothesis_registry
        self._gd     = gap_detector
        self._rm     = roadmap_manager
        self._ev     = evidence_validator
        self._sp     = study_planner
        self._synth  = synthesizer
        self._rc     = rc
        self._mlc    = mlc
        self._idr    = idr
        self._pig    = pig
        self._config = config or SDConfig()
        self._lock   = threading.Lock()
        self._journal = ScientificJournal(
            journal_path=self._config.journal_path,
            max_entries=self._config.max_journal_entries,
            dry_run=self._config.dry_run,
        )
        self._last_review_id:   Optional[str] = None
        self._last_review_date: Optional[str] = None
        self._last_review_type: Optional[str] = None
        self._consecutive_failures:  int       = 0
        log.info(
            "[SD] Initialised. kp=%s reg=%s gd=%s rm=%s ev=%s sp=%s "
            "synth=%s rc=%s mlc=%s idr=%s pig=%s dry_run=%s",
            self._kp    is not None, self._reg   is not None,
            self._gd    is not None, self._rm    is not None,
            self._ev    is not None, self._sp    is not None,
            self._synth is not None, self._rc    is not None,
            self._mlc   is not None, self._idr   is not None,
            self._pig   is not None, self._config.dry_run,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Query API
    # ═══════════════════════════════════════════════════════════════════════

    def daily_review(self) -> ScientificReview:
        """Execute a daily scientific review cycle.

        Observes knowledge, gaps, roadmap, research, and learning state.
        Generates hypotheses for top gaps.
        Approves pending Class A study plans.
        Records everything in the journal.

        Returns
        -------
        ScientificReview
            Complete structured record of the review.
        """
        return self._run_review(ReviewType.DAILY)

    def weekly_review(self) -> ScientificReview:
        """Execute a weekly scientific review cycle.

        Includes all daily observations plus hypothesis lifecycle evaluation
        and cross-study synthesis.

        Returns
        -------
        ScientificReview
        """
        return self._run_review(ReviewType.WEEKLY)

    def monthly_review(self) -> ScientificReview:
        """Execute a monthly scientific review cycle.

        Includes all weekly observations plus IDR, PIG, and long-term
        strategic direction evaluation.

        Returns
        -------
        ScientificReview
        """
        return self._run_review(ReviewType.MONTHLY)

    def evaluate_platform(self) -> ScientificReview:
        """Evaluate overall platform health from a scientific perspective.

        Returns
        -------
        ScientificReview
        """
        return self._run_review(ReviewType.PLATFORM)

    def approve_study(self, plan_id: str) -> ScientificDecision:
        """Review and approve or escalate a specific study plan.

        Parameters
        ----------
        plan_id : str
            The plan ID to approve (must exist in StudyPlanner registry).

        Returns
        -------
        ScientificDecision
            The approval decision (Class A auto-approved, or Class B pending human).
        """
        observations: List[ScientificObservation] = []
        plan = None

        if self._sp:
            try:
                plan = self._sp.get_plan(plan_id)
                obs = self._make_obs(
                    "StudyPlanner", "plan_loaded",
                    plan_id,
                    f"Plan '{getattr(plan, 'title', plan_id)}' loaded for review.",
                    SignificanceLevel.MEDIUM,
                )
                observations.append(obs)
            except Exception as exc:
                obs = self._make_obs(
                    "StudyPlanner", "plan_not_found",
                    plan_id,
                    f"Plan {plan_id} not found: {exc}",
                    SignificanceLevel.HIGH,
                )
                observations.append(obs)
                decision = self._make_decision(
                    DecisionType.REJECT_STUDY,
                    DecisionClass.CLASS_A,
                    observations,
                    self._make_reasoning(0.0, 0.0, 0.0, 0.0, "HIGH", "LOW", 0.0,
                                         f"Plan {plan_id} could not be loaded: {exc}"),
                    f"Rejected: plan {plan_id} not found.",
                    "NONE",
                    "No study will be executed.",
                    0.9,
                    requires_human=False,
                )
                self._journal.record_decision(decision)
                return decision

        decision_class, class_reason = self._classify_study(plan)

        try:
            raw_hours = getattr(getattr(plan, "execution_estimate", None), "total_hours", 0)
            info_gain_val = float(int(raw_hours) > 0)
        except (TypeError, ValueError):
            info_gain_val = 0.5

        reasoning = self._make_reasoning(
            knowledge_completeness=0.5,
            evidence_quality=0.5,
            research_value=0.7,
            info_gain=info_gain_val,
            scientific_risk=class_reason,
            research_cost="MEDIUM",
            strategic_alignment=0.7,
            rationale=(
                f"Plan {plan_id} classified as {decision_class.value}. {class_reason}"
            ),
        )

        if decision_class == DecisionClass.CLASS_A:
            # Delegate to RC
            delegation = "ResearchCoordinator"
            if self._rc and plan and not self._config.dry_run:
                try:
                    self._rc.run_research(plan)
                except Exception as exc:
                    log.warning("[SD] RC delegation failed for plan %s: %s", plan_id, exc)
                    delegation = "ResearchCoordinator (delegation failed)"

            decision = self._make_decision(
                DecisionType.APPROVE_STUDY_CLASS_A,
                DecisionClass.CLASS_A,
                observations,
                reasoning,
                f"Approved Class A study plan {plan_id}. Delegated to ResearchCoordinator.",
                delegation,
                "ResearchCoordinator will execute 8-stage research pipeline.",
                0.85,
                requires_human=False,
            )
        else:
            # Class B — pending human approval
            decision = self._make_decision(
                DecisionType.APPROVE_STUDY_CLASS_B_PENDING,
                DecisionClass.CLASS_B,
                observations,
                reasoning,
                f"Plan {plan_id} requires human approval ({class_reason}). Awaiting confirmation.",
                "HUMAN_OPERATOR",
                "Human operator will review and either approve or reject this plan.",
                0.75,
                requires_human=True,
            )

        self._journal.record_decision(decision)
        return decision

    def reject_study(self, plan_id: str, reason: str) -> ScientificDecision:
        """Reject a study plan with a documented reason.

        Parameters
        ----------
        plan_id : str
            The plan ID to reject.
        reason : str
            Scientific justification for rejection.

        Returns
        -------
        ScientificDecision
        """
        obs = self._make_obs(
            "StudyPlanner", "plan_rejected",
            plan_id,
            f"Plan {plan_id} rejected. Reason: {reason}",
            SignificanceLevel.MEDIUM,
        )
        reasoning = self._make_reasoning(
            0.5, 0.5, 0.2, 0.1, "LOW", "LOW", 0.5,
            f"Study plan {plan_id} rejected because: {reason}",
        )
        decision = self._make_decision(
            DecisionType.REJECT_STUDY,
            DecisionClass.CLASS_A,
            [obs],
            reasoning,
            f"Rejected plan {plan_id}: {reason}",
            "NONE",
            "Plan will not be executed. It may be revised and resubmitted.",
            0.9,
            requires_human=False,
        )
        self._journal.record_decision(decision)
        return decision

    def roadmap(self) -> ScientificRoadmap:
        """Return the current scientific research roadmap.

        Returns
        -------
        ScientificRoadmap
        """
        entries = []
        if self._rm:
            try:
                entries = self._rm.list_entries()
            except Exception:
                pass

        critical = sum(1 for e in entries
                       if hasattr(e, "gap") and hasattr(e.gap, "severity")
                       and e.gap.severity.value == "CRITICAL")
        high     = sum(1 for e in entries
                       if hasattr(e, "gap") and hasattr(e.gap, "severity")
                       and e.gap.severity.value == "HIGH")
        medium   = sum(1 for e in entries
                       if hasattr(e, "gap") and hasattr(e.gap, "severity")
                       and e.gap.severity.value == "MEDIUM")
        low      = sum(1 for e in entries
                       if hasattr(e, "gap") and hasattr(e.gap, "severity")
                       and e.gap.severity.value == "LOW")

        next_e   = entries[0] if entries else None
        next_id  = getattr(getattr(next_e, "gap", None), "gap_id", None) if next_e else None
        next_tit = getattr(next_e, "recommended_study_title", None) if next_e else None
        next_sc  = float(getattr(next_e, "priority_score", 0.0)) if next_e else 0.0

        # Pending plans (plans in StudyPlanner not yet delegated)
        pending = 0
        if self._sp:
            try:
                plans = self._sp.list_plans()
                pending = len(plans)
            except Exception:
                pass

        return ScientificRoadmap(
            entries=entries,
            total_entries=len(entries),
            critical_gaps=critical,
            high_gaps=high,
            medium_gaps=medium,
            low_gaps=low,
            pending_plans=pending,
            next_priority_id=next_id,
            next_priority_title=next_tit,
            next_priority_score=next_sc,
            generated_at=_now_iso(),
        )

    def status(self) -> ScientificHealth:
        """Return the current operational health of the Scientific Director."""
        with self._lock:
            reviews = len(self._journal)
            cf      = self._consecutive_failures
            lrid    = self._last_review_id
            lrd     = self._last_review_date
            lrt     = self._last_review_type

        if reviews == 0:
            h = SDHealth.NO_DATA
        elif cf == 0:
            h = SDHealth.HEALTHY
        elif cf < 3:
            h = SDHealth.DEGRADED
        else:
            h = SDHealth.BLIND

        # hypothesis counts
        hyp_proposed = 0
        hyp_active   = 0
        if self._reg:
            try:
                stats = self._reg.statistics()
                hyp_proposed = int(stats.get("total", 0))
                hyp_active   = int(stats.get("by_status", {}).get("APPROVED", 0))
            except Exception:
                pass

        # gap counts
        gaps_open     = 0
        gaps_critical = 0
        if self._gd:
            try:
                open_gaps     = self._gd.list_open()
                gaps_open     = len(open_gaps)
                gaps_critical = sum(1 for g in open_gaps
                                    if getattr(g, "severity", None)
                                    and g.severity.value == "CRITICAL")
            except Exception:
                pass

        # pending plans
        pending_plans = 0
        if self._sp:
            try:
                pending_plans = len(self._sp.list_plans())
            except Exception:
                pass

        # knowledge completeness
        completeness = 0.0
        if self._kp:
            try:
                snap = self._kp.get_snapshot()
                completeness = self._evaluate_knowledge_completeness(snap)
            except Exception:
                pass

        # RC health
        rc_health = "UNKNOWN"
        if self._rc:
            try:
                rc_st    = self._rc.status()
                rc_health = getattr(getattr(rc_st, "health", None), "value", "UNKNOWN")
            except Exception:
                pass

        # MLC health
        mlc_health = "UNKNOWN"
        if self._mlc:
            try:
                mlc_st    = self._mlc.status()
                mlc_h     = getattr(mlc_st, "health", None)
                mlc_health = mlc_h.value if hasattr(mlc_h, "value") else str(mlc_h)
            except Exception:
                pass

        detail = (
            f"Last review: {lrd} ({lrt})." if lrd
            else "No review executed yet."
        )

        return ScientificHealth(
            health=h,
            last_review_id=lrid,
            last_review_date=lrd,
            last_review_type=lrt,
            total_reviews=reviews,
            hypotheses_proposed=hyp_proposed,
            hypotheses_active=hyp_active,
            gaps_open=gaps_open,
            gaps_critical=gaps_critical,
            studies_pending=pending_plans,
            knowledge_completeness=round(completeness, 3),
            rc_health=rc_health,
            mlc_health=mlc_health,
            consecutive_review_failures=cf,
            detail=detail,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Observation layer — READ ONLY
    # ═══════════════════════════════════════════════════════════════════════

    def _observe_knowledge(self) -> List[ScientificObservation]:
        """Observe the current knowledge state via KnowledgeProvider."""
        if not self._kp:
            return []
        obs: List[ScientificObservation] = []
        try:
            snap       = self._kp.get_snapshot()
            findings   = getattr(snap, "total_findings", 0)
            edges      = getattr(snap, "total_edges", 0)
            strategies = getattr(snap, "total_strategies", 0)
            certs      = getattr(snap, "total_certifications", 0)
            warnings   = self._kp.get_warnings()

            completeness = self._evaluate_knowledge_completeness(snap)
            comp_sig     = (
                SignificanceLevel.HIGH   if completeness < 0.3 else
                SignificanceLevel.MEDIUM if completeness < 0.6 else
                SignificanceLevel.LOW
            )
            obs.append(self._make_obs(
                "KnowledgeProvider", "knowledge_completeness",
                round(completeness, 3),
                f"Knowledge base is {'sparse' if completeness < 0.3 else 'developing' if completeness < 0.6 else 'rich'}. "
                f"findings={findings} edges={edges} strategies={strategies} certs={certs}",
                comp_sig,
            ))
            if warnings:
                obs.append(self._make_obs(
                    "KnowledgeProvider", "load_warnings",
                    len(warnings),
                    f"{len(warnings)} knowledge load warning(s) detected. "
                    "Some knowledge stores may have data quality issues.",
                    SignificanceLevel.HIGH if len(warnings) > 3 else SignificanceLevel.MEDIUM,
                ))
        except Exception as exc:
            log.debug("[SD] _observe_knowledge failed: %s", exc)
        return obs

    def _observe_gaps(self) -> List[ScientificObservation]:
        """Observe the gap landscape via GapDetector."""
        if not self._gd:
            return []
        obs: List[ScientificObservation] = []
        try:
            self._gd.detect()
            open_gaps  = self._gd.list_open()
            stats      = self._gd.statistics()
            n_open     = len(open_gaps)
            n_critical = sum(1 for g in open_gaps
                             if getattr(g, "severity", None)
                             and g.severity.value == "CRITICAL")

            sig = (
                SignificanceLevel.HIGH   if n_critical > 0 else
                SignificanceLevel.MEDIUM if n_open > 3      else
                SignificanceLevel.LOW
            )
            obs.append(self._make_obs(
                "GapDetector", "open_gaps",
                n_open,
                f"{n_open} open knowledge gap(s) detected "
                f"({n_critical} CRITICAL). "
                "Research priorities should address CRITICAL gaps first.",
                sig,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_gaps failed: %s", exc)
        return obs

    def _observe_roadmap(self) -> List[ScientificObservation]:
        """Observe the research roadmap state via RoadmapManager."""
        if not self._rm:
            return []
        obs: List[ScientificObservation] = []
        try:
            entries = self._rm.list_entries()
            top     = self._rm.top_priorities(3)
            n       = len(entries)
            obs.append(self._make_obs(
                "RoadmapManager", "roadmap_entries",
                n,
                f"Research roadmap contains {n} prioritised entries. "
                + (f"Top priority: {getattr(top[0], 'recommended_study_title', 'N/A')} "
                   f"(score={getattr(top[0], 'priority_score', 0.0):.2f})" if top else "No entries."),
                SignificanceLevel.MEDIUM if n > 0 else SignificanceLevel.HIGH,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_roadmap failed: %s", exc)
        return obs

    def _observe_research(self) -> List[ScientificObservation]:
        """Observe the ResearchCoordinator state."""
        if not self._rc:
            return []
        obs: List[ScientificObservation] = []
        try:
            st       = self._rc.status()
            rc_h     = getattr(getattr(st, "health", None), "value", "UNKNOWN")
            total    = getattr(st, "total_runs", 0)
            cf       = getattr(st, "consecutive_failures", 0)
            sig      = SignificanceLevel.HIGH if cf >= 3 else SignificanceLevel.LOW
            obs.append(self._make_obs(
                "ResearchCoordinator", "rc_health",
                rc_h,
                f"Research pipeline health={rc_h}. "
                f"total_runs={total} consecutive_failures={cf}.",
                sig,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_research failed: %s", exc)
        return obs

    def _observe_learning(self) -> List[ScientificObservation]:
        """Observe the MarketLearningCoordinator state."""
        if not self._mlc:
            return []
        obs: List[ScientificObservation] = []
        try:
            st   = self._mlc.status()
            mlc_h = getattr(st, "health", None)
            h_v   = mlc_h.value if hasattr(mlc_h, "value") else str(mlc_h)
            healthy = getattr(st, "pipeline_healthy", True)
            obs.append(self._make_obs(
                "MarketLearningCoordinator", "mlc_health",
                h_v,
                f"Market learning pipeline health={h_v}. "
                f"pipeline_healthy={healthy}.",
                SignificanceLevel.HIGH if not healthy else SignificanceLevel.LOW,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_learning failed: %s", exc)
        return obs

    def _observe_idr(self) -> List[ScientificObservation]:
        """Observe the Institutional DNA Repository."""
        if not self._idr:
            return []
        obs: List[ScientificObservation] = []
        try:
            stats      = self._idr.statistics()
            active_dna = getattr(stats, "active_count", 0)
            obs.append(self._make_obs(
                "IDRRepository", "active_dna",
                active_dna,
                f"IDR contains {active_dna} active DNA record(s). "
                "DNA represents the platform's institutional knowledge of winning patterns.",
                SignificanceLevel.INFORMATIONAL,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_idr failed: %s", exc)
        return obs

    def _observe_hypotheses(self) -> List[ScientificObservation]:
        """Observe the hypothesis registry state."""
        if not self._reg:
            return []
        obs: List[ScientificObservation] = []
        try:
            stats    = self._reg.statistics()
            total    = stats.get("total", 0)
            by_s     = stats.get("by_status", {})
            proposed = by_s.get("PROPOSED", 0)
            confirmed= by_s.get("CONFIRMED", 0)
            rejected = by_s.get("REJECTED", 0)
            obs.append(self._make_obs(
                "HypothesisRegistry", "hypothesis_counts",
                {"total": total, "proposed": proposed, "confirmed": confirmed, "rejected": rejected},
                f"Registry: {total} total, {proposed} proposed, "
                f"{confirmed} confirmed, {rejected} rejected.",
                SignificanceLevel.MEDIUM if proposed > 0 else SignificanceLevel.INFORMATIONAL,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_hypotheses failed: %s", exc)
        return obs

    def _observe_synthesis(self) -> List[ScientificObservation]:
        """Observe the cross-study synthesis state."""
        if not self._synth:
            return []
        obs: List[ScientificObservation] = []
        try:
            stats        = self._synth.statistics()
            sf           = getattr(stats, "total_synthesized_findings", 0)
            contradictions = getattr(stats, "total_contradictions", 0)
            obs.append(self._make_obs(
                "CrossStudySynthesizer", "synthesis_state",
                {"synthesized_findings": sf, "contradictions": contradictions},
                f"Synthesis: {sf} synthesised findings, {contradictions} contradiction(s).",
                SignificanceLevel.HIGH if contradictions > 0 else SignificanceLevel.INFORMATIONAL,
            ))
        except Exception as exc:
            log.debug("[SD] _observe_synthesis failed: %s", exc)
        return obs

    # ═══════════════════════════════════════════════════════════════════════
    # Reasoning layer
    # ═══════════════════════════════════════════════════════════════════════

    def _evaluate_knowledge_completeness(self, snap: Any) -> float:
        """Score current knowledge completeness as 0.0-1.0."""
        findings = getattr(snap, "total_findings", 0)
        edges    = getattr(snap, "total_edges",    0)
        certs    = getattr(snap, "total_certifications", 0)

        f_score  = min(findings / 50.0, 1.0) * 0.40
        e_score  = min(edges    / 10.0, 1.0) * 0.35
        c_score  = min(certs    /  5.0, 1.0) * 0.25
        return round(f_score + e_score + c_score, 3)

    def _evaluate_gap_urgency(self, gaps: List[Any]) -> List[Any]:
        """Filter and sort gaps by severity above the configured threshold."""
        threshold = _SEVERITY_THRESHOLD.get(
            self._config.gap_severity_threshold.upper(), 2
        )
        qualifying = [
            g for g in gaps
            if hasattr(g, "severity") and _severity_val(g.severity.value) >= threshold
        ]
        qualifying.sort(key=lambda g: _severity_val(g.severity.value), reverse=True)
        return qualifying

    def _evaluate_research_value(self, gap: Any) -> float:
        """Estimate research value (0.0-1.0) for a gap."""
        severity_score = _severity_val(getattr(getattr(gap, "severity", None), "value", "LOW")) / 4.0
        gain           = float(getattr(gap, "estimated_knowledge_gain", 0.5))
        confidence     = float(getattr(gap, "confidence", 0.5))
        return round((severity_score * 0.50 + gain * 0.30 + confidence * 0.20), 3)

    def _classify_study(self, plan: Any) -> Tuple[DecisionClass, str]:
        """Classify a StudyPlan as Class A (autonomous) or Class B (supervised)."""
        if plan is None:
            return DecisionClass.CLASS_A, "No plan provided — defaulting to Class A"

        study_type_attr = getattr(plan, "study_type", "")
        if hasattr(study_type_attr, "value"):
            study_type = str(study_type_attr.value).upper()
        else:
            study_type = str(study_type_attr).upper()

        risk_attr = getattr(plan, "risk_class", "LOW")
        if hasattr(risk_attr, "value"):
            risk_class = str(risk_attr.value).upper()
        else:
            risk_class = str(risk_attr).upper()

        if study_type in ("META_LEARNING", "CUSTOM"):
            return DecisionClass.CLASS_B, f"study_type={study_type} requires human oversight"
        if risk_class == "HIGH":
            return DecisionClass.CLASS_B, "risk_class=HIGH requires human approval"

        return DecisionClass.CLASS_A, "standard study type and risk class"

    # ═══════════════════════════════════════════════════════════════════════
    # Decision layer
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_hypotheses_for_gaps(
        self,
        gaps: List[Any],
    ) -> List[ScientificDecision]:
        """Create hypotheses for top-N actionable gaps."""
        decisions: List[ScientificDecision] = []
        if not gaps or not self._reg:
            return decisions

        limit   = self._config.max_hypotheses_per_review
        created = 0

        for gap in gaps[:limit * 2]:
            if created >= limit:
                break

            gap_id    = getattr(gap, "gap_id", "")
            gap_title = getattr(gap, "title", gap_id)
            gap_desc  = getattr(gap, "description", "")
            severity  = getattr(getattr(gap, "severity", None), "value", "MEDIUM")
            gain      = float(getattr(gap, "estimated_knowledge_gain", 0.5))

            # Skip if hypothesis already exists for this gap
            if self._reg:
                try:
                    existing = self._reg.search(gap_title)
                    if existing:
                        decisions.append(self._make_decision(
                            DecisionType.DEFER,
                            DecisionClass.CLASS_A,
                            [self._make_obs("HypothesisRegistry", "existing_hypothesis",
                                            len(existing),
                                            f"Hypothesis already exists for gap: {gap_title}",
                                            SignificanceLevel.LOW)],
                            self._make_reasoning(0.5, 0.7, 0.5, gain, "LOW", "LOW", 0.6,
                                                 f"Gap '{gap_title}' already has a hypothesis."),
                            f"Deferred: hypothesis exists for gap {gap_id}.",
                            "NONE",
                            "Existing hypothesis should be reviewed.",
                            0.9,
                            requires_human=False,
                        ))
                        continue
                except Exception:
                    pass

            # Map gap to hypothesis fields
            priority    = _GAP_SEVERITY_TO_PRIORITY.get(severity, "MEDIUM")
            classif     = _GAP_CATEGORY_TO_CLASSIFICATION.get(
                getattr(getattr(gap, "category", None), "value", ""), "EXPLORATORY"
            )

            obs = self._make_obs(
                "GapDetector", "gap_requires_hypothesis",
                gap_id,
                f"Gap '{gap_title}' (severity={severity}) has no active hypothesis. "
                f"Creating research hypothesis.",
                SignificanceLevel.HIGH if severity in ("CRITICAL", "HIGH") else SignificanceLevel.MEDIUM,
            )
            reasoning = self._make_reasoning(
                knowledge_completeness=0.4,
                evidence_quality=0.5,
                research_value=self._evaluate_research_value(gap),
                info_gain=gain,
                scientific_risk="LOW",
                research_cost="MEDIUM",
                strategic_alignment=0.7,
                rationale=(
                    f"Gap '{gap_title}' identified by GapDetector with severity={severity}. "
                    f"No existing hypothesis covers this gap. "
                    f"Creating hypothesis to initiate research pathway."
                ),
            )

            hyp_title    = f"Research gap: {gap_title}"
            hyp_question = (
                f"Can addressing the {getattr(getattr(gap, 'category', None), 'value', 'knowledge')} "
                f"gap improve IIOS scientific knowledge? Gap: {gap_desc[:120]}"
            )

            if not self._config.dry_run:
                try:
                    from .hypothesis_models import HypothesisPriority, HypothesisClassification  # noqa: PLC0415
                    self._reg.create_hypothesis(
                        title=hyp_title,
                        research_question=hyp_question,
                        description=(
                            f"Auto-generated by Scientific Director from gap {gap_id}. "
                            f"Severity: {severity}. {gap_desc}"
                        ),
                        origin="scientific_director",
                        priority=HypothesisPriority(priority),
                        classification=HypothesisClassification(classif),
                        knowledge_gap=gap_id,
                        expected_knowledge_gain=f"Estimated gain: {gain:.2f}",
                        validation_method=(
                            "EvidenceValidator quality gates followed by cross-study synthesis"
                        ),
                        created_by=self._config.created_by,
                        confidence=self._config.hypothesis_confidence_initial,
                        notes=[f"Auto-generated from gap {gap_id} during Scientific Director review."],
                    )
                    created += 1
                except Exception as exc:
                    log.warning("[SD] Hypothesis creation failed for gap %s: %s", gap_id, exc)
                    continue
            else:
                created += 1

            decision = self._make_decision(
                DecisionType.CREATE_HYPOTHESIS,
                DecisionClass.CLASS_A,
                [obs],
                reasoning,
                f"Created hypothesis '{hyp_title}' for gap {gap_id}.",
                "HypothesisRegistry",
                f"Hypothesis will be reviewed and a study plan will be created "
                f"to address gap '{gap_title}'.",
                0.80,
                requires_human=False,
            )
            decisions.append(decision)

        return decisions

    def _approve_pending_class_a_plans(self) -> List[ScientificDecision]:
        """Auto-approve Class A study plans up to the per-review limit."""
        decisions: List[ScientificDecision] = []
        if not self._sp or not self._config.auto_approve_class_a:
            return decisions

        try:
            plans = self._sp.list_plans()
        except Exception:
            return decisions

        limit   = self._config.max_plans_per_review
        approved = 0

        for plan in plans:
            if approved >= limit:
                break
            plan_id = getattr(plan, "plan_id", "")
            dec_class, reason = self._classify_study(plan)
            if dec_class == DecisionClass.CLASS_A:
                decisions.append(self.approve_study(plan_id))
                approved += 1

        return decisions

    def _check_escalations(self) -> List[ScientificDecision]:
        """Generate Class B escalation decisions for critical unresolved items."""
        decisions: List[ScientificDecision] = []

        # Check for critical gaps with no hypothesis
        if self._gd and self._reg:
            try:
                open_gaps = self._gd.list_open()
                critical  = [g for g in open_gaps
                             if getattr(getattr(g, "severity", None), "value", "") == "CRITICAL"]
                if len(critical) >= 3:
                    obs = self._make_obs(
                        "GapDetector", "critical_gap_accumulation",
                        len(critical),
                        f"{len(critical)} critical gaps are open. Human review recommended.",
                        SignificanceLevel.HIGH,
                    )
                    decisions.append(self._make_decision(
                        DecisionType.ESCALATE_HUMAN,
                        DecisionClass.CLASS_B,
                        [obs],
                        self._make_reasoning(0.2, 0.5, 0.9, 0.9, "HIGH", "MEDIUM", 0.9,
                                             "Critical gap accumulation requires human scientific oversight."),
                        f"Escalating: {len(critical)} CRITICAL gaps require human review.",
                        "HUMAN_OPERATOR",
                        "Human operator will triage critical gaps and set research priorities.",
                        0.85,
                        requires_human=True,
                    ))
            except Exception:
                pass

        # Check RC health
        if self._rc:
            try:
                st = self._rc.status()
                cf = getattr(st, "consecutive_failures", 0)
                if cf >= 5:
                    obs = self._make_obs(
                        "ResearchCoordinator", "consecutive_failures",
                        cf,
                        f"RC has {cf} consecutive pipeline failures. Research is blocked.",
                        SignificanceLevel.HIGH,
                    )
                    decisions.append(self._make_decision(
                        DecisionType.ESCALATE_HUMAN,
                        DecisionClass.CLASS_B,
                        [obs],
                        self._make_reasoning(0.3, 0.3, 0.9, 0.9, "HIGH", "HIGH", 0.9,
                                             "RC failure streak blocks all research execution."),
                        f"Escalating: RC has {cf} consecutive failures. Human investigation required.",
                        "HUMAN_OPERATOR",
                        "Human operator will diagnose and resolve RC pipeline failures.",
                        0.9,
                        requires_human=True,
                    ))
            except Exception:
                pass

        return decisions

    def _build_recommendations(
        self,
        observations: List[ScientificObservation],
    ) -> List[ScientificRecommendation]:
        """Derive recommendations from the current observation set."""
        recs: List[ScientificRecommendation] = []

        for obs in observations:
            if obs.significance in (SignificanceLevel.HIGH,) and obs.metric == "open_gaps":
                recs.append(ScientificRecommendation(
                    recommendation_id=make_recommendation_id(),
                    target="ROADMAP",
                    content=(
                        f"Address open gaps immediately. "
                        f"Current state: {obs.value} open gaps."
                    ),
                    urgency=UrgencyLevel.HIGH,
                    decision_class=DecisionClass.CLASS_A,
                    rationale=obs.interpretation,
                ))
            if obs.significance == SignificanceLevel.HIGH and "contradiction" in obs.metric:
                recs.append(ScientificRecommendation(
                    recommendation_id=make_recommendation_id(),
                    target="HUMAN_OPERATOR",
                    content=(
                        "Resolve contradictions detected in knowledge synthesis. "
                        "DIRECT contradictions require human approval."
                    ),
                    urgency=UrgencyLevel.HIGH,
                    decision_class=DecisionClass.CLASS_B,
                    rationale=obs.interpretation,
                ))
            if obs.metric == "knowledge_completeness" and isinstance(obs.value, float) and obs.value < 0.3:
                recs.append(ScientificRecommendation(
                    recommendation_id=make_recommendation_id(),
                    target="ROADMAP",
                    content=(
                        "Knowledge base is sparse. "
                        "Prioritise foundational studies to build evidence base."
                    ),
                    urgency=UrgencyLevel.MEDIUM,
                    decision_class=DecisionClass.CLASS_A,
                    rationale=obs.interpretation,
                ))

        return recs

    # ═══════════════════════════════════════════════════════════════════════
    # Internal review engine
    # ═══════════════════════════════════════════════════════════════════════

    def _run_review(self, review_type: ReviewType) -> ScientificReview:
        """Execute a complete review cycle of the given type."""
        review_id = make_review_id()
        date_str  = datetime.now().strftime("%Y-%m-%d")
        t_start   = time.monotonic()
        start_iso = _now_iso()

        log.info("[SD] Starting %s review review_id=%s", review_type.value, review_id)

        observations: List[ScientificObservation] = []
        decisions:    List[ScientificDecision]    = []
        health        = SDHealth.HEALTHY

        try:
            # ── Phase 1: Observe ────────────────────────────────────────────
            observations += self._observe_knowledge()
            observations += self._observe_gaps()
            observations += self._observe_roadmap()
            observations += self._observe_research()
            observations += self._observe_learning()
            observations += self._observe_hypotheses()

            if review_type in (ReviewType.WEEKLY, ReviewType.MONTHLY, ReviewType.PLATFORM):
                observations += self._observe_synthesis()

            if review_type in (ReviewType.MONTHLY, ReviewType.PLATFORM):
                observations += self._observe_idr()

            # ── Phase 2: Reason + Decide ────────────────────────────────────
            gaps: List[Any] = []
            if self._gd:
                try:
                    gaps = self._evaluate_gap_urgency(self._gd.list_open())
                except Exception:
                    pass

            decisions += self._generate_hypotheses_for_gaps(gaps)
            decisions += self._approve_pending_class_a_plans()
            decisions += self._check_escalations()

            # Determine health
            observed_count = len(observations)
            if observed_count == 0:
                health = SDHealth.BLIND
            elif any(o.significance == SignificanceLevel.HIGH for o in observations):
                health = SDHealth.DEGRADED
            else:
                health = SDHealth.HEALTHY

        except Exception as exc:
            log.error("[SD] Review %s failed unexpectedly: %s", review_id, exc)
            health = SDHealth.DEGRADED
            with self._lock:
                self._consecutive_failures += 1

        # ── Phase 3: Recommend ──────────────────────────────────────────────
        recommendations = self._build_recommendations(observations)

        # ── Phase 4: Compose summary ────────────────────────────────────────
        total_ms = (time.monotonic() - t_start) * 1000.0
        summary  = (
            f"{review_type.value} review completed in {total_ms:.0f}ms. "
            f"health={health.value} "
            f"observations={len(observations)} "
            f"decisions={len(decisions)} "
            f"recommendations={len(recommendations)}."
        )

        review = ScientificReview(
            review_id=review_id,
            review_type=review_type,
            date=date_str,
            observations=observations,
            decisions=decisions,
            recommendations=recommendations,
            health=health,
            summary=summary,
            duration_ms=round(total_ms, 2),
            timestamp=start_iso,
        )

        # ── Phase 5: Journal ────────────────────────────────────────────────
        self._journal.record_review(review)
        for dec in decisions:
            self._journal.record_decision(dec, review_id=review_id)

        with self._lock:
            if health == SDHealth.HEALTHY:
                self._consecutive_failures = 0
            self._last_review_id   = review_id
            self._last_review_date = date_str
            self._last_review_type = review_type.value

        log.info(
            "[SD] %s review done review_id=%s health=%s obs=%d dec=%d %.0fms",
            review_type.value, review_id, health.value,
            len(observations), len(decisions), total_ms,
        )
        return review

    # ═══════════════════════════════════════════════════════════════════════
    # Low-level helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _make_obs(
        self,
        component:      str,
        metric:         str,
        value:          Any,
        interpretation: str,
        significance:   SignificanceLevel,
    ) -> ScientificObservation:
        return ScientificObservation(
            observation_id=make_observation_id(),
            component=component,
            metric=metric,
            value=value,
            interpretation=interpretation,
            significance=significance,
            timestamp=_now_iso(),
        )

    @staticmethod
    def _make_reasoning(
        knowledge_completeness:    float,
        evidence_quality:          float,
        research_value:            float,
        info_gain:                 float,
        scientific_risk:           str,
        research_cost:             str,
        strategic_alignment:       float,
        rationale:                 str,
    ) -> ScientificReasoning:
        return ScientificReasoning(
            knowledge_completeness=round(knowledge_completeness, 3),
            evidence_quality=round(evidence_quality, 3),
            research_value=round(research_value, 3),
            expected_information_gain=round(info_gain, 3),
            scientific_risk=scientific_risk,
            research_cost=research_cost,
            strategic_alignment=round(strategic_alignment, 3),
            rationale=rationale,
        )

    @staticmethod
    def _make_decision(
        decision_type:       DecisionType,
        decision_class:      DecisionClass,
        observations:        List[ScientificObservation],
        reasoning:           ScientificReasoning,
        decision_text:       str,
        delegation_target:   str,
        expected_outcome:    str,
        confidence:          float,
        requires_human:      bool,
    ) -> ScientificDecision:
        return ScientificDecision(
            decision_id=make_decision_id(),
            decision_type=decision_type,
            decision_class=decision_class,
            observations=observations,
            reasoning=reasoning,
            decision_text=decision_text,
            delegation_target=delegation_target,
            expected_outcome=expected_outcome,
            confidence=round(confidence, 3),
            timestamp=_now_iso(),
            requires_human_approval=requires_human,
            approved_by_human=None if requires_human else True,
        )


# ─── Gap→Hypothesis mapping tables ──────────────────────────────────────────

_GAP_SEVERITY_TO_PRIORITY: Dict[str, str] = {
    "CRITICAL":  "CRITICAL",
    "HIGH":      "HIGH",
    "MEDIUM":    "MEDIUM",
    "LOW":       "LOW",
}

_GAP_CATEGORY_TO_CLASSIFICATION: Dict[str, str] = {
    "DATA_GAP":          "COVERAGE_GAP",
    "EVIDENCE_GAP":      "PERFORMANCE_GAP",
    "REGIME_GAP":        "COVERAGE_GAP",
    "SECTOR_GAP":        "COVERAGE_GAP",
    "TEMPORAL_GAP":      "TEMPORAL_GAP",
    "VALIDATION_GAP":    "PERFORMANCE_GAP",
    "CONTRADICTION_GAP": "CONTRADICTION",
    "CONFIDENCE_GAP":    "PERFORMANCE_GAP",
    "KNOWLEDGE_GAP":     "COVERAGE_GAP",
    "COVERAGE_GAP":      "COVERAGE_GAP",
}

"""
evidence_validator.py — Scientific evidence quality gate engine.

ARS Phase 2C.

Responsibilities:
    Validate research evidence, findings, hypotheses, and roadmap entries
    against configurable scientific quality standards.
    Return fully traceable EvidenceValidation records.
    Maintain session statistics.

Explicitly NOT responsible for:
    Modifying any knowledge store.
    Generating hypotheses or findings.
    Executing research.
    Changing roadmaps.
    Any write operations except appending to in-memory history.

Quality Gates (10, independent):
    G-EV-01  Sample Size           — evidence has sufficient observations
    G-EV-02  Replication           — finding corroborated by multiple studies
    G-EV-03  Temporal Coverage     — evidence spans sufficient historical period
    G-EV-04  Regime Coverage       — finding covers sufficient market regimes
    G-EV-05  Sector Coverage       — evidence represents sufficient sector diversity
    G-EV-06  Walk-Forward          — strategy/edge passes walk-forward validation
    G-EV-07  Out-of-Sample         — strategy/edge passes OOS validation
    G-EV-08  Contradiction Check   — contradictions below acceptable threshold [CRITICAL]
    G-EV-09  Certification Status  — minimum certifications passed
    G-EV-10  Evidence Freshness    — evidence is sufficiently recent

All gate thresholds are configurable via EvidenceValidatorConfig.
No threshold is hardcoded in this module.

Every EvidenceValidation record contains:
    input         → subject_type, subject_id, subject_summary
    rules         → rules_evaluated (gate_ids applied)
    evidence      → evidence_used (study/finding/cert IDs consulted)
    gate results  → gate_results (one GateResult per gate)
    score         → quality_score (formula documented in EvidenceQualityScore)
    decision      → outcome + outcome_explanation
    timestamp     → validated_at
"""
from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .cross_study_synthesizer import CrossStudySynthesizer
from .evidence_validator_models import (
    EvidenceQualityScore,
    EvidenceValidation,
    EvidenceValidatorConfig,
    EvidenceValidatorError,
    GateResult,
    GateStatus,
    ValidationOutcome,
    ValidationStatistics,
    ValidationSubjectNotFoundError,
    ValidationSummary,
)
from .gap_detector import GapDetector
from .gap_models import GapCategory
from .hypothesis_models import EvidenceType
from .hypothesis_registry import HypothesisRegistry
from .knowledge_provider import KnowledgeProvider
from .models import ResearchStudy
from .roadmap_manager import RoadmapManager
from .roadmap_models import RoadmapEntry

logger = logging.getLogger(__name__)

# ─── gate ID constants ────────────────────────────────────────────────────────

_G_SAMPLE_SIZE    = "G-EV-01"
_G_REPLICATION    = "G-EV-02"
_G_TEMPORAL       = "G-EV-03"
_G_REGIME         = "G-EV-04"
_G_SECTOR         = "G-EV-05"
_G_WALK_FORWARD   = "G-EV-06"
_G_OOS            = "G-EV-07"
_G_CONTRADICTION  = "G-EV-08"
_G_CERTIFICATION  = "G-EV-09"
_G_FRESHNESS      = "G-EV-10"

_GATE_NAMES: Dict[str, str] = {
    _G_SAMPLE_SIZE:   "Sample Size",
    _G_REPLICATION:   "Replication",
    _G_TEMPORAL:      "Temporal Coverage",
    _G_REGIME:        "Regime Coverage",
    _G_SECTOR:        "Sector Coverage",
    _G_WALK_FORWARD:  "Walk-Forward Consistency",
    _G_OOS:           "Out-of-Sample Validation",
    _G_CONTRADICTION: "Contradiction Check",
    _G_CERTIFICATION: "Certification Status",
    _G_FRESHNESS:     "Evidence Freshness",
}


def _validation_id(subject_type: str, subject_id: str) -> str:
    """Deterministic ID from subject type and ID."""
    prefix = {"finding": "F", "hypothesis": "H", "roadmap_entry": "R"}.get(
        subject_type, "X"
    )
    return f"EV-{prefix}-{hashlib.sha256(subject_id.encode()).hexdigest()[:8].upper()}"


def _safe_date_days(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-like date string, returning None on failure."""
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str.replace("Z", ""), fmt)
        except ValueError:
            continue
    return None


class EvidenceValidator:
    """
    Scientific evidence quality gate engine for IIOS.

    Applies 10 independent quality gates to findings, hypotheses, and
    roadmap entries.  Returns fully traceable EvidenceValidation records
    containing every input, rule, gate result, score, and decision.

    EvidenceValidator is read-only.  It never modifies any knowledge store,
    hypothesis, roadmap, or finding.

    Usage::

        kp = KnowledgeProvider()
        ev = EvidenceValidator(kp)

        result = ev.validate_finding(finding_id)
        print(result.outcome)                # ValidationOutcome.PASSED
        print(result.quality_score.total)    # e.g. 0.82

        for gate in result.gate_results:
            print(f"  [{gate.status.value}] {gate.name}: {gate.explanation}")
    """

    def __init__(
        self,
        knowledge_provider: KnowledgeProvider,
        hypothesis_registry: Optional[HypothesisRegistry] = None,
        synthesizer: Optional[CrossStudySynthesizer] = None,
        gap_detector: Optional[GapDetector] = None,
        roadmap_manager: Optional[RoadmapManager] = None,
        config: Optional[EvidenceValidatorConfig] = None,
    ) -> None:
        self._kp   = knowledge_provider
        self._reg  = hypothesis_registry
        self._syn  = synthesizer
        self._gd   = gap_detector
        self._rm   = roadmap_manager
        self._cfg  = config or EvidenceValidatorConfig()
        self._lock = threading.Lock()
        self._history: List[EvidenceValidation] = []

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═════════════════════════════════════════════════════════════════════════

    def validate(self, subject_id: str, subject_type: str = "finding") -> EvidenceValidation:
        """
        Validate evidence by subject type and ID.

        subject_type must be "finding" or "hypothesis".
        For roadmap entries, use validate_roadmap_entry(entry) directly.
        """
        if subject_type == "finding":
            return self.validate_finding(subject_id)
        if subject_type == "hypothesis":
            return self.validate_hypothesis(subject_id)
        raise EvidenceValidatorError(
            f"Unknown subject_type={subject_type!r}. "
            "Supported: 'finding', 'hypothesis'. "
            "Use validate_roadmap_entry(entry) for roadmap entries."
        )

    def validate_finding(self, finding_id: str) -> EvidenceValidation:
        """
        Validate the evidence quality of a single finding.

        Gates applied: all 10 (G-EV-06/07 are SKIPPED unless a matching
        edge with walk-forward/OOS metrics is found).

        Raises
        ------
        ValidationSubjectNotFoundError: if finding_id is not in KnowledgeProvider.
        """
        # ── locate finding ───────────────────────────────────────────────────
        findings = self._kp.list_findings()
        finding = next((f for f in findings if f.finding_id == finding_id), None)
        if finding is None:
            raise ValidationSubjectNotFoundError(f"Finding {finding_id!r} not found")

        study = self._kp.get_study(finding.study_id)
        n_obs = study.n_observations if study else None

        # ── replication — from CrossStudySynthesizer ─────────────────────────
        syn_finding = None
        contradictions = []
        if self._syn is not None:
            report = self._syn.synthesize()
            syn_finding = next(
                (sf for sf in report.synthesized_findings
                 if finding_id in sf.source_finding_ids),
                None,
            )
            contradictions = [
                c for c in report.contradictions
                if c.finding_a_id == finding_id or c.finding_b_id == finding_id
            ]

        if syn_finding is not None:
            n_corroborating = syn_finding.supporting_study_count
        else:
            # count studies with a matching metric finding (excluding source study)
            n_corroborating = len({
                f.study_id for f in findings
                if f.metric == finding.metric and f.study_id != finding.study_id
            })

        # ── temporal coverage ─────────────────────────────────────────────────
        temporal_days = self._compute_temporal_span([study] if study else [])

        # ── regime coverage ────────────────────────────────────────────────────
        if syn_finding and syn_finding.regime_coverage:
            regimes = [r for r in syn_finding.regime_coverage if r]
        else:
            regimes = [finding.regime] if finding.regime else []

        # ── sector coverage ────────────────────────────────────────────────────
        features = self._kp.list_features()
        sectors = list({fr.sector for fr in features if fr.sector})

        # ── walk-forward / OOS — from edges matching finding metric ──────────
        edges = [
            e for e in self._kp.list_edges()
            if e.name and finding.metric
            and finding.metric.lower()[:4] in e.name.lower()
        ]
        wf  = max((e.wf_consistency for e in edges if e.wf_consistency is not None), default=None)
        oos = max((e.oos_win_rate   for e in edges if e.oos_win_rate   is not None), default=None)

        # ── contradiction ratio ────────────────────────────────────────────────
        if syn_finding is not None:
            denom = syn_finding.supporting_study_count + syn_finding.contradicting_study_count
            contradiction_ratio = syn_finding.contradicting_study_count / max(1, denom)
        else:
            # use direct contradiction records
            metric_findings = [f for f in findings if f.metric == finding.metric]
            contradiction_ratio = len(contradictions) / max(1, len(metric_findings))

        # ── certifications ─────────────────────────────────────────────────────
        certifications = [c for c in self._kp.list_certifications() if c.passed]

        # ── freshness ──────────────────────────────────────────────────────────
        days_old: Optional[int] = None
        if study and study.executed_at:
            days_old = max(0, (datetime.now() - study.executed_at).days)

        # ── evaluate all gates ─────────────────────────────────────────────────
        gates = [
            self._gate_sample_size(n_obs),
            self._gate_replication(n_corroborating),
            self._gate_temporal_coverage(temporal_days),
            self._gate_regime_coverage(regimes),
            self._gate_sector_coverage(sectors),
            self._gate_walk_forward(wf),
            self._gate_oos(oos),
            self._gate_contradiction(contradiction_ratio),
            self._gate_certification(len(certifications)),
            self._gate_freshness(days_old),
        ]

        evidence_used = [f"finding:{finding_id}"]
        if study:
            evidence_used.append(f"study:{study.study_id}")
        if syn_finding:
            evidence_used.append(f"synthesis:{syn_finding.synthesis_id}")
        for e in edges[:3]:
            evidence_used.append(f"edge:{e.edge_id}")
        for c in certifications[:3]:
            evidence_used.append(f"cert:{c.cert_id}")

        result = self._build_validation(
            subject_type="finding",
            subject_id=finding_id,
            subject_summary=(
                f"{finding.classification.value}: {finding.metric} "
                f"— {finding.description[:60]}"
            ),
            gates=gates,
            evidence_used=evidence_used,
        )
        with self._lock:
            self._history.append(result)
        return result

    def validate_hypothesis(self, hypothesis_id: str) -> EvidenceValidation:
        """
        Validate the evidence quality supporting a scientific hypothesis.

        Requires a HypothesisRegistry to be provided at construction time.

        Raises
        ------
        EvidenceValidatorError: if no HypothesisRegistry was provided.
        ValidationSubjectNotFoundError: if hypothesis_id is not found.
        """
        if self._reg is None:
            raise EvidenceValidatorError(
                "HypothesisRegistry is required for validate_hypothesis(). "
                "Pass hypothesis_registry= at construction time."
            )
        hyp = self._reg.get(hypothesis_id)
        if hyp is None:
            raise ValidationSubjectNotFoundError(
                f"Hypothesis {hypothesis_id!r} not found in registry"
            )

        # ── supporting studies ────────────────────────────────────────────────
        study_refs = [
            e for e in hyp.supporting_evidence
            if e.evidence_type == EvidenceType.STUDY
        ]
        studies = [self._kp.get_study(e.evidence_id) for e in study_refs]
        studies = [s for s in studies if s is not None]
        max_obs: Optional[int] = max(
            (s.n_observations for s in studies if s.n_observations is not None),
            default=None,
        )

        # ── replication: number of unique supporting studies ──────────────────
        n_corroborating = len(studies)

        # ── temporal coverage ──────────────────────────────────────────────────
        temporal_days = self._compute_temporal_span(studies)

        # ── regime coverage: from findings of supporting studies ───────────────
        all_findings = [f for s in studies for f in s.findings]
        regimes = list({f.regime for f in all_findings if f.regime})

        # ── sector coverage ────────────────────────────────────────────────────
        features = self._kp.list_features()
        sectors = list({fr.sector for fr in features if fr.sector})

        # ── walk-forward / OOS: best available from all edges ─────────────────
        edges = self._kp.list_edges()
        wf  = max((e.wf_consistency for e in edges if e.wf_consistency is not None), default=None)
        oos = max((e.oos_win_rate   for e in edges if e.oos_win_rate   is not None), default=None)

        # ── contradiction: use synthesis if available, else confidence proxy ───
        contradiction_ratio: float
        if self._syn is not None:
            report = self._syn.synthesize()
            hyp_finding_ids = {
                e.evidence_id for e in hyp.supporting_evidence
                if e.evidence_type == EvidenceType.FINDING
            }
            related_contr = [
                c for c in report.contradictions
                if c.finding_a_id in hyp_finding_ids
                or c.finding_b_id in hyp_finding_ids
            ]
            total_ev = max(1, len(hyp.supporting_evidence))
            contradiction_ratio = len(related_contr) / total_ev
        else:
            # proxy: low confidence indicates contradictory / uncertain evidence
            contradiction_ratio = max(0.0, 1.0 - hyp.confidence)

        # ── certifications ─────────────────────────────────────────────────────
        certifications = [c for c in self._kp.list_certifications() if c.passed]

        # ── freshness: age of the most recent supporting study ─────────────────
        study_ages = [
            max(0, (datetime.now() - s.executed_at).days)
            for s in studies if s.executed_at
        ]
        days_old: Optional[int] = min(study_ages) if study_ages else None

        # ── evaluate all gates ─────────────────────────────────────────────────
        gates = [
            self._gate_sample_size(max_obs),
            self._gate_replication(n_corroborating),
            self._gate_temporal_coverage(temporal_days),
            self._gate_regime_coverage(regimes),
            self._gate_sector_coverage(sectors),
            self._gate_walk_forward(wf),
            self._gate_oos(oos),
            self._gate_contradiction(contradiction_ratio),
            self._gate_certification(len(certifications)),
            self._gate_freshness(days_old),
        ]

        evidence_used = [f"hypothesis:{hypothesis_id}"]
        for s in studies:
            evidence_used.append(f"study:{s.study_id}")
        for c in certifications[:3]:
            evidence_used.append(f"cert:{c.cert_id}")

        result = self._build_validation(
            subject_type="hypothesis",
            subject_id=hypothesis_id,
            subject_summary=f"{hyp.status.value}: {hyp.title[:80]}",
            gates=gates,
            evidence_used=evidence_used,
        )
        with self._lock:
            self._history.append(result)
        return result

    def validate_roadmap_entry(self, entry: RoadmapEntry) -> EvidenceValidation:
        """
        Validate the evidence quality behind a RoadmapEntry recommendation.

        G-EV-06 (Walk-Forward) and G-EV-07 (OOS) are INAPPLICABLE for roadmap
        entries since they refer to knowledge gaps rather than strategies.
        """
        gap = entry.gap

        # ── sample size: from related studies ─────────────────────────────────
        studies = [self._kp.get_study(sid) for sid in gap.related_studies]
        studies = [s for s in studies if s is not None]
        max_obs: Optional[int] = max(
            (s.n_observations for s in studies if s.n_observations is not None),
            default=None,
        )
        if max_obs is None:
            max_obs = gap.rule_parameters.get("n_observations")

        # ── replication: number of related studies ────────────────────────────
        n_corroborating = len(gap.related_studies)

        # ── temporal coverage ──────────────────────────────────────────────────
        temporal_days = self._compute_temporal_span(studies)

        # ── regime coverage ────────────────────────────────────────────────────
        if gap.category == GapCategory.REGIME_GAP:
            regimes = gap.rule_parameters.get("covered_regimes", [])
        else:
            all_findings = [f for s in studies for f in s.findings]
            regimes = list({f.regime for f in all_findings if f.regime})

        # ── sector coverage ────────────────────────────────────────────────────
        features = self._kp.list_features()
        sectors = list({fr.sector for fr in features if fr.sector})

        # ── contradiction: depends on gap category ─────────────────────────────
        if gap.category == GapCategory.CONTRADICTION_GAP:
            # Gap identifies a documented contradiction; valid if ≥2 pieces of evidence
            n_evidence = len(gap.supporting_evidence)
            contradiction_ratio = 0.0 if n_evidence >= 2 else 1.0
        else:
            if self._syn is not None:
                report = self._syn.synthesize()
                related_fids = set(gap.related_findings)
                related_contr = [
                    c for c in report.contradictions
                    if c.finding_a_id in related_fids
                    or c.finding_b_id in related_fids
                ]
                total = max(1, len(gap.related_findings)) if gap.related_findings else 1
                contradiction_ratio = len(related_contr) / total
            else:
                contradiction_ratio = 0.0

        # ── certifications ─────────────────────────────────────────────────────
        certifications = [c for c in self._kp.list_certifications() if c.passed]

        # ── freshness: gap age ──────────────────────────────────────────────────
        days_old = max(0, (datetime.now() - gap.created_at).days)

        # ── evaluate gates (WF and OOS are INAPPLICABLE) ──────────────────────
        gates = [
            self._gate_sample_size(max_obs),
            self._gate_replication(n_corroborating),
            self._gate_temporal_coverage(temporal_days),
            self._gate_regime_coverage(regimes),
            self._gate_sector_coverage(sectors),
            self._gate_inapplicable(
                _G_WALK_FORWARD, _GATE_NAMES[_G_WALK_FORWARD],
                "Not applicable to research roadmap entries",
            ),
            self._gate_inapplicable(
                _G_OOS, _GATE_NAMES[_G_OOS],
                "Not applicable to research roadmap entries",
            ),
            self._gate_contradiction(contradiction_ratio),
            self._gate_certification(len(certifications)),
            self._gate_freshness(days_old),
        ]

        evidence_used = [f"roadmap_entry:{entry.entry_id}", f"gap:{gap.gap_id}"]
        for s in studies:
            evidence_used.append(f"study:{s.study_id}")
        for c in certifications[:3]:
            evidence_used.append(f"cert:{c.cert_id}")

        result = self._build_validation(
            subject_type="roadmap_entry",
            subject_id=entry.entry_id,
            subject_summary=f"[{gap.category.value}] {entry.recommended_study_title[:80]}",
            gates=gates,
            evidence_used=evidence_used,
        )
        with self._lock:
            self._history.append(result)
        return result

    def statistics(self) -> ValidationStatistics:
        """Return aggregate statistics across all validations in this session."""
        with self._lock:
            history = list(self._history)

        by_outcome: Dict[str, int] = {}
        by_subject: Dict[str, int] = {}
        gate_fail_counts: Dict[str, int] = {}
        gate_pass_counts: Dict[str, int] = {}
        total_score = 0.0

        for v in history:
            by_outcome[v.outcome.value] = by_outcome.get(v.outcome.value, 0) + 1
            by_subject[v.subject_type]  = by_subject.get(v.subject_type,   0) + 1
            total_score += v.quality_score.total
            for g in v.gate_results:
                if g.status == GateStatus.FAILED:
                    gate_fail_counts[g.gate_id] = gate_fail_counts.get(g.gate_id, 0) + 1
                elif g.status == GateStatus.PASSED:
                    gate_pass_counts[g.gate_id] = gate_pass_counts.get(g.gate_id, 0) + 1

        n = len(history)
        avg = total_score / n if n else 0.0
        most_failed = max(gate_fail_counts, key=gate_fail_counts.get) if gate_fail_counts else None
        most_passed = max(gate_pass_counts, key=gate_pass_counts.get) if gate_pass_counts else None

        return ValidationStatistics(
            total_validations_run=n,
            by_outcome=by_outcome,
            by_subject_type=by_subject,
            avg_quality_score=round(avg, 4),
            most_failed_gate=most_failed,
            most_passed_gate=most_passed,
            built_at=datetime.now(),
        )

    def latest_results(self, n: int = 10) -> List[EvidenceValidation]:
        """Return the N most recent validation results (newest first)."""
        with self._lock:
            return list(reversed(self._history[-n:]))

    # ═════════════════════════════════════════════════════════════════════════
    # GATE EVALUATORS  (accessible for testing)
    # ═════════════════════════════════════════════════════════════════════════

    def _gate_sample_size(self, n_obs: Optional[int]) -> GateResult:
        """G-EV-01: Minimum observations for statistical significance."""
        w = self._cfg.gate_weights.get(_G_SAMPLE_SIZE, 1.0)
        if n_obs is None:
            return GateResult(
                gate_id=_G_SAMPLE_SIZE, name=_GATE_NAMES[_G_SAMPLE_SIZE],
                status=GateStatus.SKIPPED, actual_value=None,
                threshold=self._cfg.min_observations,
                explanation="Observation count not available in study metadata",
                is_critical=_G_SAMPLE_SIZE in self._cfg.critical_gates, weight=w,
            )
        passed = n_obs >= self._cfg.min_observations
        return GateResult(
            gate_id=_G_SAMPLE_SIZE, name=_GATE_NAMES[_G_SAMPLE_SIZE],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=n_obs, threshold=self._cfg.min_observations,
            explanation=(
                f"{n_obs} observations "
                f"{'≥' if passed else '<'} "
                f"{self._cfg.min_observations} required"
            ),
            is_critical=_G_SAMPLE_SIZE in self._cfg.critical_gates, weight=w,
        )

    def _gate_replication(self, n_corroborating: int) -> GateResult:
        """G-EV-02: Minimum corroborating independent studies."""
        w = self._cfg.gate_weights.get(_G_REPLICATION, 1.0)
        passed = n_corroborating >= self._cfg.min_corroborating_studies
        return GateResult(
            gate_id=_G_REPLICATION, name=_GATE_NAMES[_G_REPLICATION],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=n_corroborating,
            threshold=self._cfg.min_corroborating_studies,
            explanation=(
                f"{n_corroborating} corroborating "
                f"{'study' if n_corroborating == 1 else 'studies'} "
                f"({'≥' if passed else '<'} {self._cfg.min_corroborating_studies} required)"
            ),
            is_critical=_G_REPLICATION in self._cfg.critical_gates, weight=w,
        )

    def _gate_temporal_coverage(self, temporal_days: Optional[int]) -> GateResult:
        """G-EV-03: Minimum temporal span of evidence."""
        w = self._cfg.gate_weights.get(_G_TEMPORAL, 1.0)
        if temporal_days is None:
            return GateResult(
                gate_id=_G_TEMPORAL, name=_GATE_NAMES[_G_TEMPORAL],
                status=GateStatus.SKIPPED, actual_value=None,
                threshold=self._cfg.min_temporal_coverage_days,
                explanation="Study date range not available",
                is_critical=_G_TEMPORAL in self._cfg.critical_gates, weight=w,
            )
        passed = temporal_days >= self._cfg.min_temporal_coverage_days
        return GateResult(
            gate_id=_G_TEMPORAL, name=_GATE_NAMES[_G_TEMPORAL],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=temporal_days,
            threshold=self._cfg.min_temporal_coverage_days,
            explanation=(
                f"{temporal_days}d temporal span "
                f"({'≥' if passed else '<'} {self._cfg.min_temporal_coverage_days}d required)"
            ),
            is_critical=_G_TEMPORAL in self._cfg.critical_gates, weight=w,
        )

    def _gate_regime_coverage(self, regimes: List[str]) -> GateResult:
        """G-EV-04: Minimum distinct market regimes covered."""
        w = self._cfg.gate_weights.get(_G_REGIME, 1.0)
        n = len(set(r for r in regimes if r))
        passed = n >= self._cfg.min_regime_count
        return GateResult(
            gate_id=_G_REGIME, name=_GATE_NAMES[_G_REGIME],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=n, threshold=self._cfg.min_regime_count,
            explanation=(
                f"{n} distinct regime{'s' if n != 1 else ''} "
                f"({'≥' if passed else '<'} {self._cfg.min_regime_count} required)"
                + (f"; regimes: {sorted(set(regimes))}" if regimes else "")
            ),
            is_critical=_G_REGIME in self._cfg.critical_gates, weight=w,
        )

    def _gate_sector_coverage(self, sectors: List[str]) -> GateResult:
        """G-EV-05: Minimum distinct sectors represented."""
        w = self._cfg.gate_weights.get(_G_SECTOR, 0.5)
        n = len(set(s for s in sectors if s))
        if n == 0:
            return GateResult(
                gate_id=_G_SECTOR, name=_GATE_NAMES[_G_SECTOR],
                status=GateStatus.SKIPPED, actual_value=0,
                threshold=self._cfg.min_sector_diversity,
                explanation="Sector metadata not available in feature database",
                is_critical=_G_SECTOR in self._cfg.critical_gates, weight=w,
            )
        passed = n >= self._cfg.min_sector_diversity
        return GateResult(
            gate_id=_G_SECTOR, name=_GATE_NAMES[_G_SECTOR],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=n, threshold=self._cfg.min_sector_diversity,
            explanation=(
                f"{n} sector{'s' if n != 1 else ''} "
                f"({'≥' if passed else '<'} {self._cfg.min_sector_diversity} required)"
            ),
            is_critical=_G_SECTOR in self._cfg.critical_gates, weight=w,
        )

    def _gate_walk_forward(self, wf_consistency: Optional[float]) -> GateResult:
        """G-EV-06: Walk-forward consistency from correlated edge / strategy."""
        w = self._cfg.gate_weights.get(_G_WALK_FORWARD, 1.5)
        if wf_consistency is None:
            return GateResult(
                gate_id=_G_WALK_FORWARD, name=_GATE_NAMES[_G_WALK_FORWARD],
                status=GateStatus.SKIPPED, actual_value=None,
                threshold=self._cfg.min_walk_forward_pass_rate,
                explanation="No correlated edge with walk-forward metrics found",
                is_critical=_G_WALK_FORWARD in self._cfg.critical_gates, weight=w,
            )
        passed = wf_consistency >= self._cfg.min_walk_forward_pass_rate
        return GateResult(
            gate_id=_G_WALK_FORWARD, name=_GATE_NAMES[_G_WALK_FORWARD],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=round(wf_consistency, 4),
            threshold=self._cfg.min_walk_forward_pass_rate,
            explanation=(
                f"Walk-forward consistency {wf_consistency:.1%} "
                f"({'≥' if passed else '<'} {self._cfg.min_walk_forward_pass_rate:.1%} required)"
            ),
            is_critical=_G_WALK_FORWARD in self._cfg.critical_gates, weight=w,
        )

    def _gate_oos(self, oos_win_rate: Optional[float]) -> GateResult:
        """G-EV-07: Out-of-sample win rate from correlated edge."""
        w = self._cfg.gate_weights.get(_G_OOS, 1.0)
        if oos_win_rate is None:
            return GateResult(
                gate_id=_G_OOS, name=_GATE_NAMES[_G_OOS],
                status=GateStatus.SKIPPED, actual_value=None,
                threshold=self._cfg.min_oos_win_rate,
                explanation="No correlated edge with OOS win-rate metrics found",
                is_critical=_G_OOS in self._cfg.critical_gates, weight=w,
            )
        passed = oos_win_rate >= self._cfg.min_oos_win_rate
        return GateResult(
            gate_id=_G_OOS, name=_GATE_NAMES[_G_OOS],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=round(oos_win_rate, 4),
            threshold=self._cfg.min_oos_win_rate,
            explanation=(
                f"OOS win rate {oos_win_rate:.1%} "
                f"({'≥' if passed else '<'} {self._cfg.min_oos_win_rate:.1%} required)"
            ),
            is_critical=_G_OOS in self._cfg.critical_gates, weight=w,
        )

    def _gate_contradiction(self, contradiction_ratio: float) -> GateResult:
        """G-EV-08: Contradiction ratio gate — CRITICAL by default."""
        w = self._cfg.gate_weights.get(_G_CONTRADICTION, 2.0)
        passed = contradiction_ratio <= self._cfg.max_contradiction_ratio
        pct = f"{contradiction_ratio:.1%}"
        thr = f"{self._cfg.max_contradiction_ratio:.1%}"
        return GateResult(
            gate_id=_G_CONTRADICTION, name=_GATE_NAMES[_G_CONTRADICTION],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=round(contradiction_ratio, 4),
            threshold=self._cfg.max_contradiction_ratio,
            explanation=(
                f"Contradiction ratio {pct} "
                f"({'≤' if passed else '>'} {thr} allowed)"
            ),
            is_critical=_G_CONTRADICTION in self._cfg.critical_gates, weight=w,
        )

    def _gate_certification(self, cert_count: int) -> GateResult:
        """G-EV-09: Minimum passed certifications."""
        w = self._cfg.gate_weights.get(_G_CERTIFICATION, 1.0)
        passed = cert_count >= self._cfg.min_certification_count
        if self._cfg.min_certification_count == 0:
            passed = True  # gate trivially satisfied
        return GateResult(
            gate_id=_G_CERTIFICATION, name=_GATE_NAMES[_G_CERTIFICATION],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=cert_count,
            threshold=self._cfg.min_certification_count,
            explanation=(
                f"{cert_count} passed certification{'s' if cert_count != 1 else ''} "
                f"({'≥' if passed else '<'} {self._cfg.min_certification_count} required)"
            ),
            is_critical=_G_CERTIFICATION in self._cfg.critical_gates, weight=w,
        )

    def _gate_freshness(self, days_old: Optional[int]) -> GateResult:
        """G-EV-10: Evidence freshness (age of most recent study)."""
        w = self._cfg.gate_weights.get(_G_FRESHNESS, 1.0)
        if days_old is None:
            return GateResult(
                gate_id=_G_FRESHNESS, name=_GATE_NAMES[_G_FRESHNESS],
                status=GateStatus.SKIPPED, actual_value=None,
                threshold=self._cfg.max_evidence_staleness_days,
                explanation="Study execution date not available",
                is_critical=_G_FRESHNESS in self._cfg.critical_gates, weight=w,
            )
        passed = days_old <= self._cfg.max_evidence_staleness_days
        return GateResult(
            gate_id=_G_FRESHNESS, name=_GATE_NAMES[_G_FRESHNESS],
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            actual_value=days_old,
            threshold=self._cfg.max_evidence_staleness_days,
            explanation=(
                f"Evidence {days_old}d old "
                f"({'≤' if passed else '>'} {self._cfg.max_evidence_staleness_days}d allowed)"
            ),
            is_critical=_G_FRESHNESS in self._cfg.critical_gates, weight=w,
        )

    def _gate_inapplicable(self, gate_id: str, name: str, reason: str) -> GateResult:
        """Return an INAPPLICABLE gate result (excluded from quality score)."""
        return GateResult(
            gate_id=gate_id, name=name,
            status=GateStatus.INAPPLICABLE,
            actual_value=None, threshold=None,
            explanation=reason,
            is_critical=False,
            weight=self._cfg.gate_weights.get(gate_id, 1.0),
        )

    # ═════════════════════════════════════════════════════════════════════════
    # SCORING ENGINE
    # ═════════════════════════════════════════════════════════════════════════

    def _compute_quality_score(self, gates: List[GateResult]) -> EvidenceQualityScore:
        """
        Compute composite quality score from gate results.

        INAPPLICABLE gates are excluded entirely.
        SKIPPED gates contribute half their weight (neutral / unknown).
        PASSED gates contribute full weight.
        FAILED gates contribute zero weight.
        """
        applicable = [g for g in gates if g.status != GateStatus.INAPPLICABLE]
        total_w = sum(g.weight for g in applicable)

        earned = sum(
            g.weight if g.status == GateStatus.PASSED
            else (g.weight * 0.5 if g.status == GateStatus.SKIPPED else 0.0)
            for g in applicable
        )
        score = earned / total_w if total_w > 0.0 else 0.0
        score = min(1.0, max(0.0, score))

        gate_scores = {
            g.gate_id: round(
                g.weight / total_w if g.status == GateStatus.PASSED
                else (g.weight * 0.5 / total_w if g.status == GateStatus.SKIPPED else 0.0),
                4,
            )
            for g in applicable
        }

        return EvidenceQualityScore(
            total=round(score, 4),
            gate_scores=gate_scores,
            applicable_gates=len(applicable),
            passed_gates=sum(1 for g in applicable if g.status == GateStatus.PASSED),
            failed_gates=sum(1 for g in applicable if g.status == GateStatus.FAILED),
            skipped_gates=sum(1 for g in applicable if g.status == GateStatus.SKIPPED),
            breakdown={
                "earned_weight":    round(earned, 4),
                "total_weight":     round(total_w, 4),
                "passed_weight":    round(sum(g.weight for g in applicable if g.status == GateStatus.PASSED), 4),
                "skipped_weight":   round(sum(g.weight * 0.5 for g in applicable if g.status == GateStatus.SKIPPED), 4),
                "failed_weight":    round(sum(g.weight for g in applicable if g.status == GateStatus.FAILED), 4),
                "inapplicable_count": sum(1 for g in gates if g.status == GateStatus.INAPPLICABLE),
                "passed_threshold":         self._cfg.passed_threshold,
                "passed_with_obs_threshold": self._cfg.passed_with_obs_threshold,
            },
        )

    def _determine_outcome(
        self, score: float, gates: List[GateResult]
    ) -> Tuple[ValidationOutcome, str, List[str]]:
        """
        Determine validation outcome from quality score and gate results.

        Returns (outcome, outcome_explanation, observations).
        observations is non-empty only for PASSED_WITH_OBSERVATIONS.
        """
        critical_failures = [
            g for g in gates
            if g.is_critical and g.status == GateStatus.FAILED
        ]
        if critical_failures:
            names = ", ".join(g.name for g in critical_failures)
            return (
                ValidationOutcome.FAILED,
                f"FAILED — critical gate failure: {names}",
                [],
            )

        failed_gates = [g for g in gates if g.status == GateStatus.FAILED]

        if score >= self._cfg.passed_threshold:
            return (
                ValidationOutcome.PASSED,
                f"All quality gates passed (score={score:.0%})",
                [],
            )

        observations = [f"{g.name}: {g.explanation}" for g in failed_gates]
        skipped_gates = [g for g in gates if g.status == GateStatus.SKIPPED]
        for g in skipped_gates:
            observations.append(f"{g.name} (SKIPPED): {g.explanation}")

        if score >= self._cfg.passed_with_obs_threshold:
            return (
                ValidationOutcome.PASSED_WITH_OBSERVATIONS,
                (
                    f"Passed with {len(observations)} observation(s) "
                    f"(score={score:.0%}, threshold={self._cfg.passed_threshold:.0%})"
                ),
                observations,
            )

        return (
            ValidationOutcome.FAILED,
            (
                f"Quality score below minimum threshold "
                f"(score={score:.0%} < {self._cfg.passed_with_obs_threshold:.0%})"
            ),
            observations,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _build_validation(
        self,
        subject_type: str,
        subject_id: str,
        subject_summary: str,
        gates: List[GateResult],
        evidence_used: List[str],
    ) -> EvidenceValidation:
        quality_score = self._compute_quality_score(gates)
        outcome, explanation, observations = self._determine_outcome(quality_score.total, gates)
        return EvidenceValidation(
            validation_id=_validation_id(subject_type, subject_id),
            subject_type=subject_type,
            subject_id=subject_id,
            subject_summary=subject_summary,
            validated_at=datetime.now(),
            gate_results=gates,
            quality_score=quality_score,
            outcome=outcome,
            outcome_explanation=explanation,
            observations=observations,
            evidence_used=evidence_used,
            rules_evaluated=[g.gate_id for g in gates if g.status != GateStatus.INAPPLICABLE],
        )

    def _compute_temporal_span(self, studies: List[ResearchStudy]) -> Optional[int]:
        """Compute total temporal span in days across the provided studies."""
        starts, ends = [], []
        for s in studies:
            dt = _safe_date_days(s.date_range_start)
            if dt:
                starts.append(dt)
            dt = _safe_date_days(s.date_range_end)
            if dt:
                ends.append(dt)
        if not (starts and ends):
            return None
        return max(0, (max(ends) - min(starts)).days)

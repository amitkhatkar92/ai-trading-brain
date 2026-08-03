"""
gap_detector.py — Scientific knowledge gap detection engine.

ARS Phase 2A.

Responsibilities:
    Analyse the complete knowledge base and identify research gaps.
    Return structured, deterministic, fully traceable KnowledgeGap objects.

Explicitly NOT responsible for:
    Modifying hypotheses, studies, or any knowledge store.
    Prioritising research.
    Planning or scheduling studies.
    Executing research.
    Writing reports.

Detection rules (10, one per GapCategory):

    R-GD-01  DATA_GAP          — study n_observations < min_study_observations
    R-GD-02  EVIDENCE_GAP      — synthesized finding with < min_corroborating_studies
    R-GD-03  REGIME_GAP        — known market regime with insufficient research findings
    R-GD-04  SECTOR_GAP        — sector with sparse feature-database coverage
    R-GD-05  TEMPORAL_GAP      — newest study older than max_study_age_days
    R-GD-06  VALIDATION_GAP    — CANDIDATE edges without walk-forward validation metrics
    R-GD-07  CONTRADICTION_GAP — ContradictionRecord from CrossStudySynthesizer output
    R-GD-08  CONFIDENCE_GAP    — synthesized finding confidence < min_synthesis_confidence
    R-GD-09  KNOWLEDGE_GAP     — hypothesis open longer than max_hypothesis_open_days
    R-GD-10  COVERAGE_GAP      — FindingClassification with zero findings across all studies

All gap_ids are deterministic: sha256(category + rule_id + source_key)[:8].
Running detect() on unchanged data always produces the same gap_ids.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .cross_study_synthesizer import CrossStudySynthesizer
from .gap_models import (
    DetectionError,
    GapCategory,
    GapDetectionReport,
    GapDetectorConfig,
    GapSeverity,
    GapStatistics,
    GapStatus,
    KnowledgeGap,
)
from .hypothesis_models import EvidenceType, HypothesisPriority
from .hypothesis_registry import HypothesisRegistry
from .knowledge_provider import KnowledgeProvider
from .models import EdgeStatus, FindingClassification
from .synthesis_models import SynthesisReport

logger = logging.getLogger(__name__)

# Estimated knowledge gain per severity — documented in GapDetectorConfig docstring
_SEV_GAIN: Dict[GapSeverity, float] = {
    GapSeverity.CRITICAL: 0.90,
    GapSeverity.HIGH:     0.70,
    GapSeverity.MEDIUM:   0.50,
    GapSeverity.LOW:      0.20,
}

_PRIORITY_TO_SEV = {
    HypothesisPriority.CRITICAL:    GapSeverity.CRITICAL,
    HypothesisPriority.HIGH:        GapSeverity.HIGH,
    HypothesisPriority.MEDIUM:      GapSeverity.MEDIUM,
    HypothesisPriority.LOW:         GapSeverity.LOW,
    HypothesisPriority.EXPLORATORY: GapSeverity.LOW,
}


def _gap_id(category: GapCategory, rule_id: str, source_key: str) -> str:
    """Deterministic gap ID: same inputs always produce the same ID."""
    digest = hashlib.sha256(
        f"{category.value}:{rule_id}:{source_key}".encode()
    ).hexdigest()[:8]
    return f"G-{category.value[:4]}-{rule_id}-{digest}"


def _kg(
    *,
    category: GapCategory,
    rule_id: str,
    source_key: str,
    title: str,
    description: str,
    severity: GapSeverity,
    severity_rationale: str,
    confidence: float,
    supporting_evidence: List[str],
    related_studies: List[str],
    related_hypotheses: List[str],
    related_findings: List[str],
    recommended_action: str,
    rule_parameters: Dict[str, Any],
) -> KnowledgeGap:
    """Shared factory — reduces boilerplate in rule implementations."""
    return KnowledgeGap(
        gap_id=_gap_id(category, rule_id, source_key),
        category=category,
        title=title,
        description=description,
        severity=severity,
        severity_rationale=severity_rationale,
        confidence=confidence,
        status=GapStatus.OPEN,
        supporting_evidence=supporting_evidence,
        related_studies=related_studies,
        related_hypotheses=related_hypotheses,
        related_findings=related_findings,
        recommended_action=recommended_action,
        estimated_knowledge_gain=_SEV_GAIN[severity],
        rule_id=rule_id,
        rule_parameters=rule_parameters,
        created_at=datetime.now(),
    )


class GapDetector:
    """
    Scientific knowledge gap detection engine for IIOS.

    Consumes KnowledgeProvider, HypothesisRegistry, and CrossStudySynthesizer
    to identify research gaps.  All outputs are deterministic, traceable, and
    read-only — no store is ever modified.

    Usage::

        kp  = KnowledgeProvider()
        reg = HypothesisRegistry(knowledge_provider=kp)
        syn = CrossStudySynthesizer(knowledge_provider=kp, hypothesis_registry=reg)
        gd  = GapDetector(kp, reg, syn)

        report = gd.detect()
        for gap in gd.list_by_severity(GapSeverity.CRITICAL):
            print(gap.gap_id, gap.title)
    """

    def __init__(
        self,
        knowledge_provider: KnowledgeProvider,
        hypothesis_registry: Optional[HypothesisRegistry] = None,
        synthesizer: Optional[CrossStudySynthesizer] = None,
        config: Optional[GapDetectorConfig] = None,
    ) -> None:
        self._kp   = knowledge_provider
        self._reg  = hypothesis_registry
        self._syn  = synthesizer
        self._cfg  = config or GapDetectorConfig()
        self._lock = threading.Lock()
        self._last_report: Optional[GapDetectionReport] = None

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═════════════════════════════════════════════════════════════════════════

    def detect(self, force: bool = False) -> GapDetectionReport:
        """
        Run all 10 detection rules and return a GapDetectionReport.

        Cached after first run.  Pass force=True to re-run from scratch.
        Thread-safe.
        """
        with self._lock:
            if self._last_report is not None and not force:
                return self._last_report

            t0 = time.perf_counter()
            gaps: List[KnowledgeGap] = []
            warnings: List[str] = []

            syn_report: Optional[SynthesisReport] = None
            if self._syn is not None:
                try:
                    syn_report = self._syn.synthesize(force=force)
                except Exception as exc:
                    warnings.append(f"Synthesis unavailable: {exc}")

            gaps.extend(self._rule_data_gap(warnings))
            gaps.extend(self._rule_evidence_gap(syn_report, warnings))
            gaps.extend(self._rule_regime_gap(warnings))
            gaps.extend(self._rule_sector_gap(warnings))
            gaps.extend(self._rule_temporal_gap(warnings))
            gaps.extend(self._rule_validation_gap(warnings))
            gaps.extend(self._rule_contradiction_gap(syn_report, warnings))
            gaps.extend(self._rule_confidence_gap(syn_report, warnings))
            gaps.extend(self._rule_knowledge_gap(warnings))
            gaps.extend(self._rule_coverage_gap(warnings))

            duration_ms = (time.perf_counter() - t0) * 1000
            self._last_report = GapDetectionReport(
                report_id=f"GDR-{uuid.uuid4().hex[:8].upper()}",
                detected_at=datetime.now(),
                gaps=gaps,
                statistics=self._build_statistics(gaps, duration_ms),
                warnings=warnings,
            )
            return self._last_report

    def list_all(self) -> List[KnowledgeGap]:
        """Return all gaps from the last detection run.  Empty before first detect()."""
        if self._last_report is None:
            return []
        return list(self._last_report.gaps)

    def list_open(self) -> List[KnowledgeGap]:
        """Return gaps with status OPEN."""
        return [g for g in self.list_all() if g.status == GapStatus.OPEN]

    def list_by_category(self, category: GapCategory) -> List[KnowledgeGap]:
        """Return gaps matching a specific GapCategory."""
        return [g for g in self.list_all() if g.category == category]

    def list_by_severity(self, severity: GapSeverity) -> List[KnowledgeGap]:
        """Return gaps at a specific GapSeverity level."""
        return [g for g in self.list_all() if g.severity == severity]

    def list_by_study(self, study_id: str) -> List[KnowledgeGap]:
        """Return gaps whose related_studies list includes the given study_id."""
        return [g for g in self.list_all() if study_id in g.related_studies]

    def list_by_hypothesis(self, hypothesis_id: str) -> List[KnowledgeGap]:
        """Return gaps whose related_hypotheses list includes the given hypothesis_id."""
        return [g for g in self.list_all() if hypothesis_id in g.related_hypotheses]

    def statistics(self) -> GapStatistics:
        """Return statistics from the last detection run.  Zeros before first detect()."""
        if self._last_report is None:
            return GapStatistics(
                total_gaps=0, open_gaps=0,
                by_category={}, by_severity={},
                critical_count=0, high_count=0,
                detection_duration_ms=0.0,
                detected_at=datetime.now(),
                rules_fired={},
            )
        return self._last_report.statistics

    # ═════════════════════════════════════════════════════════════════════════
    # DETECTION RULES — deterministic, configurable, read-only
    # ═════════════════════════════════════════════════════════════════════════

    # ── R-GD-01: DATA_GAP ─────────────────────────────────────────────────────
    def _rule_data_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        rule_id  = "R-GD-01"
        threshold = self._cfg.min_study_observations
        params    = {"min_study_observations": threshold}
        result: List[KnowledgeGap] = []

        for study in self._kp.list_studies():
            n = study.n_observations
            if n is None or n >= threshold:
                continue
            ratio = n / threshold
            if ratio < 0.333:
                sev      = GapSeverity.CRITICAL
                rationale = f"n={n} is below threshold÷3 ({threshold // 3})"
            elif ratio < 0.50:
                sev      = GapSeverity.HIGH
                rationale = f"n={n} is below threshold÷2 ({threshold // 2})"
            else:
                sev      = GapSeverity.MEDIUM
                rationale = f"n={n} is below threshold ({threshold})"

            result.append(_kg(
                category=GapCategory.DATA_GAP,
                rule_id=rule_id,
                source_key=study.study_id,
                title=f"Insufficient observations in study {study.study_id}",
                description=(
                    f"Study '{study.title}' contains {n} observations, "
                    f"below the required minimum of {threshold}. "
                    f"Statistical conclusions may be unreliable."
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=1.0,
                supporting_evidence=[study.study_id, f"n_observations:{n}"],
                related_studies=[study.study_id],
                related_hypotheses=[],
                related_findings=[f.finding_id for f in study.findings],
                recommended_action=(
                    f"Re-run study {study.study_id} with a larger data window "
                    f"targeting ≥{threshold} observations."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-02: EVIDENCE_GAP ──────────────────────────────────────────────────
    def _rule_evidence_gap(
        self, syn_report: Optional[SynthesisReport], warnings: List[str]
    ) -> List[KnowledgeGap]:
        rule_id   = "R-GD-02"
        if syn_report is None:
            return []
        threshold = self._cfg.min_corroborating_studies
        params    = {"min_corroborating_studies": threshold}
        result: List[KnowledgeGap] = []

        for sf in syn_report.synthesized_findings:
            n = sf.supporting_study_count
            if n >= threshold:
                continue
            sev      = GapSeverity.HIGH if n == 0 else GapSeverity.MEDIUM
            plural   = "study" if n == 1 else "studies"
            rationale = (
                f"{n} supporting {plural} < minimum {threshold}"
            )
            result.append(_kg(
                category=GapCategory.EVIDENCE_GAP,
                rule_id=rule_id,
                source_key=sf.synthesis_id,
                title=f"Under-corroborated finding: '{sf.title}'",
                description=(
                    f"Synthesized finding '{sf.title}' "
                    f"({sf.finding_classification.value} / {sf.metric}) "
                    f"is supported by only {n} {plural}. "
                    f"Scientific credibility requires ≥{threshold}."
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=1.0,
                supporting_evidence=[sf.synthesis_id] + list(sf.source_study_ids),
                related_studies=list(sf.source_study_ids),
                related_hypotheses=list(sf.related_hypothesis_ids),
                related_findings=list(sf.source_finding_ids),
                recommended_action=(
                    f"Design a corroboration study for metric '{sf.metric}' "
                    f"to validate finding '{sf.title}'."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-03: REGIME_GAP ────────────────────────────────────────────────────
    def _rule_regime_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        rule_id   = "R-GD-03"
        known     = {r.upper() for r in self._cfg.known_regimes}
        min_count = self._cfg.min_findings_per_regime
        params    = {"known_regimes": sorted(known), "min_findings_per_regime": min_count}
        result: List[KnowledgeGap] = []

        observed_counts: Dict[str, int] = {}
        for rec in self._kp.get_regime_history():
            if rec.dominant_regime:
                ru = rec.dominant_regime.upper()
                observed_counts[ru] = observed_counts.get(ru, 0) + 1

        all_findings  = self._kp.list_findings()
        all_study_ids = [s.study_id for s in self._kp.list_studies()]

        finding_counts: Dict[str, int] = {r: 0 for r in known}
        for f in all_findings:
            r = (f.regime or "").upper()
            if r in finding_counts:
                finding_counts[r] += 1

        for regime, count in sorted(finding_counts.items()):
            if count >= min_count:
                continue
            was_observed = regime in observed_counts
            obs_n        = observed_counts.get(regime, 0)

            if count == 0 and was_observed:
                sev      = GapSeverity.HIGH
                conf     = 1.0
                rationale = (
                    f"Regime {regime}: 0 findings; "
                    f"observed {obs_n} times in live regime history"
                )
            elif count == 0:
                sev      = GapSeverity.MEDIUM
                conf     = 0.7
                rationale = f"Regime {regime}: 0 findings; not seen in regime history"
            else:
                sev      = GapSeverity.MEDIUM
                conf     = 1.0
                rationale = (
                    f"Regime {regime}: {count} finding(s) < minimum {min_count}"
                )

            obs_note = (
                f" This regime appears {obs_n} times in live market history."
                if was_observed else ""
            )
            regime_findings = [
                f.finding_id for f in all_findings
                if (f.regime or "").upper() == regime
            ]
            result.append(_kg(
                category=GapCategory.REGIME_GAP,
                rule_id=rule_id,
                source_key=regime,
                title=f"Insufficient research coverage for {regime} market regime",
                description=(
                    f"Market regime '{regime}' has only {count} research finding(s) "
                    f"(minimum {min_count}).{obs_note}"
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=conf,
                supporting_evidence=[
                    f"regime:{regime}",
                    f"finding_count:{count}",
                    f"history_observations:{obs_n}",
                ],
                related_studies=all_study_ids,
                related_hypotheses=[],
                related_findings=regime_findings,
                recommended_action=(
                    f"Design a study targeting the {regime} market regime, "
                    f"focusing on strategy performance and edge validity under "
                    f"{regime} conditions."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-04: SECTOR_GAP ────────────────────────────────────────────────────
    def _rule_sector_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        rule_id   = "R-GD-04"
        threshold = self._cfg.min_sector_observations
        params    = {"min_sector_observations": threshold}
        result: List[KnowledgeGap] = []

        sector_counts: Dict[str, int] = {}
        for feat in self._kp.list_features(limit=None):
            if feat.sector:
                sector_counts[feat.sector] = sector_counts.get(feat.sector, 0) + 1

        if not sector_counts:
            result.append(_kg(
                category=GapCategory.SECTOR_GAP,
                rule_id=rule_id,
                source_key="NO_SECTOR_DATA",
                title="No sector metadata in feature database",
                description=(
                    "Feature records contain no sector classification. "
                    "Sector-level research and performance attribution are impossible."
                ),
                severity=GapSeverity.HIGH,
                severity_rationale="Zero sector-tagged observations in feature database",
                confidence=1.0,
                supporting_evidence=["feature_records:no_sector_field"],
                related_studies=[],
                related_hypotheses=[],
                related_findings=[],
                recommended_action=(
                    "Add sector classification to the feature extraction pipeline."
                ),
                rule_parameters=params,
            ))
            return result

        for sector, count in sorted(sector_counts.items()):
            if count >= threshold:
                continue
            result.append(_kg(
                category=GapCategory.SECTOR_GAP,
                rule_id=rule_id,
                source_key=sector,
                title=f"Sparse feature coverage for sector '{sector}'",
                description=(
                    f"Sector '{sector}' has only {count} feature observation(s), "
                    f"below the required minimum of {threshold}. "
                    f"Sector-specific patterns may be statistically unreliable."
                ),
                severity=GapSeverity.MEDIUM,
                severity_rationale=(
                    f"Sector '{sector}': {count} observations < minimum {threshold}"
                ),
                confidence=1.0,
                supporting_evidence=[f"sector:{sector}", f"observation_count:{count}"],
                related_studies=[],
                related_hypotheses=[],
                related_findings=[],
                recommended_action=(
                    f"Expand data collection for sector '{sector}' "
                    f"to ≥{threshold} observations."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-05: TEMPORAL_GAP ──────────────────────────────────────────────────
    def _rule_temporal_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        rule_id   = "R-GD-05"
        threshold = self._cfg.max_study_age_days
        params    = {"max_study_age_days": threshold}
        now       = datetime.now()

        dated         = [s for s in self._kp.list_studies() if s.executed_at is not None]
        all_study_ids = [s.study_id for s in self._kp.list_studies()]

        if not dated:
            return [_kg(
                category=GapCategory.TEMPORAL_GAP,
                rule_id=rule_id,
                source_key="NO_DATED_STUDIES",
                title="No research studies with execution dates found",
                description=(
                    "The knowledge base contains no studies with a recorded "
                    "execution date.  It is impossible to assess knowledge freshness."
                ),
                severity=GapSeverity.CRITICAL,
                severity_rationale="Zero studies with executed_at recorded",
                confidence=1.0,
                supporting_evidence=["study_count_with_date:0"],
                related_studies=all_study_ids,
                related_hypotheses=[],
                related_findings=[],
                recommended_action=(
                    "Execute a research study with a valid execution date."
                ),
                rule_parameters=params,
            )]

        most_recent_dt = max(s.executed_at for s in dated)  # type: ignore[arg-type]
        age_days       = (now - most_recent_dt).days
        if age_days <= threshold:
            return []

        if age_days > 3 * threshold:
            sev      = GapSeverity.CRITICAL
            rationale = f"Age {age_days} days > 3×threshold ({3 * threshold})"
        elif age_days > 2 * threshold:
            sev      = GapSeverity.HIGH
            rationale = f"Age {age_days} days > 2×threshold ({2 * threshold})"
        else:
            sev      = GapSeverity.MEDIUM
            rationale = f"Age {age_days} days > threshold ({threshold})"

        newest = max(dated, key=lambda s: s.executed_at)  # type: ignore[arg-type]
        return [_kg(
            category=GapCategory.TEMPORAL_GAP,
            rule_id=rule_id,
            source_key=newest.study_id,
            title=f"Research knowledge is {age_days} days stale",
            description=(
                f"The most recent study ('{newest.title}', "
                f"executed {most_recent_dt.date()}) is {age_days} days old. "
                f"Maximum allowed: {threshold} days. "
                f"Strategy conclusions may not reflect current market conditions."
            ),
            severity=sev,
            severity_rationale=rationale,
            confidence=1.0,
            supporting_evidence=[newest.study_id, f"age_days:{age_days}"],
            related_studies=all_study_ids,
            related_hypotheses=[],
            related_findings=[],
            recommended_action=(
                f"Execute a new research cycle within {threshold} days of the "
                f"previous study to maintain knowledge freshness."
            ),
            rule_parameters=params,
        )]

    # ── R-GD-06: VALIDATION_GAP ────────────────────────────────────────────────
    def _rule_validation_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        """
        Groups CANDIDATE edges lacking oos_win_rate and wf_consistency by category.
        One gap per category-group.
        """
        rule_id   = "R-GD-06"
        threshold = self._cfg.max_edge_unvalidated_days
        params    = {"max_edge_unvalidated_days": threshold}
        now       = datetime.now()
        result: List[KnowledgeGap] = []

        by_category: Dict[str, list] = {}
        for edge in self._kp.list_edges():
            if edge.status != EdgeStatus.CANDIDATE:
                continue
            if edge.oos_win_rate is not None or edge.wf_consistency is not None:
                continue
            cat = edge.category or "UNCATEGORIZED"
            by_category.setdefault(cat, []).append(edge)

        for cat, edges in sorted(by_category.items()):
            ages = []
            for e in edges:
                if e.created_at is not None:
                    ages.append((now - e.created_at).days)
                elif e.last_tested is not None:
                    ages.append((now - e.last_tested).days)
            oldest_age = max(ages) if ages else None

            if oldest_age is not None and oldest_age <= threshold:
                continue

            if oldest_age is None or oldest_age > 2 * threshold:
                sev      = GapSeverity.HIGH
                rationale = (
                    f"{len(edges)} unvalidated CANDIDATE edge(s) in '{cat}'"
                    + (f"; oldest {oldest_age}d" if oldest_age else " (no age data)")
                )
            else:
                sev      = GapSeverity.MEDIUM
                rationale = (
                    f"{len(edges)} unvalidated CANDIDATE edge(s) in '{cat}'; "
                    f"oldest {oldest_age}d > threshold {threshold}d"
                )

            result.append(_kg(
                category=GapCategory.VALIDATION_GAP,
                rule_id=rule_id,
                source_key=f"CANDIDATE:{cat}",
                title=f"{len(edges)} unvalidated CANDIDATE edge(s) in '{cat}'",
                description=(
                    f"{len(edges)} edge(s) in category '{cat}' have status CANDIDATE "
                    f"but lack oos_win_rate and wf_consistency validation metrics."
                    + (f" Oldest: {oldest_age} days." if oldest_age else "")
                    + " These edges cannot be promoted to ACTIVE without evidence."
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=1.0,
                supporting_evidence=[e.edge_id for e in edges[:10]],
                related_studies=[],
                related_hypotheses=[],
                related_findings=[],
                recommended_action=(
                    f"Run walk-forward validation for all CANDIDATE edges in '{cat}'. "
                    f"Record oos_win_rate and wf_consistency before promoting to ACTIVE."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-07: CONTRADICTION_GAP ─────────────────────────────────────────────
    def _rule_contradiction_gap(
        self, syn_report: Optional[SynthesisReport], warnings: List[str]
    ) -> List[KnowledgeGap]:
        """One CONTRADICTION_GAP per ContradictionRecord from the synthesizer."""
        rule_id = "R-GD-07"
        if syn_report is None or not syn_report.contradictions:
            return []
        high_t = self._cfg.contradiction_high_threshold
        med_t  = self._cfg.contradiction_medium_threshold
        params = {
            "contradiction_high_threshold":   high_t,
            "contradiction_medium_threshold":  med_t,
        }
        result: List[KnowledgeGap] = []

        for contra in syn_report.contradictions:
            s = contra.severity
            if s > high_t:
                sev      = GapSeverity.HIGH
                rationale = f"Contradiction severity {s:.2f} > high threshold {high_t}"
            elif s > med_t:
                sev      = GapSeverity.MEDIUM
                rationale = f"Contradiction severity {s:.2f} > medium threshold {med_t}"
            else:
                sev      = GapSeverity.LOW
                rationale = f"Contradiction severity {s:.2f} ≤ medium threshold {med_t}"

            result.append(_kg(
                category=GapCategory.CONTRADICTION_GAP,
                rule_id=rule_id,
                source_key=contra.contradiction_id,
                title=f"Conflicting findings on metric '{contra.metric}'",
                description=(
                    f"Finding {contra.finding_a_id} (study {contra.study_a_id}) "
                    f"contradicts finding {contra.finding_b_id} "
                    f"(study {contra.study_b_id}) on metric '{contra.metric}'. "
                    f"Type: {contra.contradiction_type.value}. Severity: {s:.2f}."
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=1.0,
                supporting_evidence=[
                    contra.contradiction_id,
                    contra.finding_a_id,
                    contra.finding_b_id,
                ],
                related_studies=[contra.study_a_id, contra.study_b_id],
                related_hypotheses=[],
                related_findings=[contra.finding_a_id, contra.finding_b_id],
                recommended_action=(
                    f"Design a resolution study targeting metric '{contra.metric}' "
                    f"to determine which finding reflects true market behaviour."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-08: CONFIDENCE_GAP ────────────────────────────────────────────────
    def _rule_confidence_gap(
        self, syn_report: Optional[SynthesisReport], warnings: List[str]
    ) -> List[KnowledgeGap]:
        rule_id  = "R-GD-08"
        if syn_report is None:
            return []
        min_conf = self._cfg.min_synthesis_confidence
        crit_t   = self._cfg.confidence_critical_threshold
        high_t   = self._cfg.confidence_high_threshold
        params   = {
            "min_synthesis_confidence":      min_conf,
            "confidence_critical_threshold": crit_t,
            "confidence_high_threshold":     high_t,
        }
        result: List[KnowledgeGap] = []

        for sf in syn_report.synthesized_findings:
            c = sf.synthesis_confidence
            if c >= min_conf:
                continue
            if c < crit_t:
                sev      = GapSeverity.CRITICAL
                rationale = f"Confidence {c:.3f} < critical threshold {crit_t}"
            elif c < high_t:
                sev      = GapSeverity.HIGH
                rationale = f"Confidence {c:.3f} < high threshold {high_t}"
            else:
                sev      = GapSeverity.MEDIUM
                rationale = f"Confidence {c:.3f} < minimum {min_conf}"

            result.append(_kg(
                category=GapCategory.CONFIDENCE_GAP,
                rule_id=rule_id,
                source_key=sf.synthesis_id,
                title=f"Low synthesis confidence: '{sf.title}'",
                description=(
                    f"Synthesized finding '{sf.title}' has confidence {c:.3f}, "
                    f"below the minimum of {min_conf:.2f}. "
                    f"Confidence breakdown: {sf.confidence_breakdown}."
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=1.0,
                supporting_evidence=[sf.synthesis_id, f"confidence:{c:.4f}"],
                related_studies=list(sf.source_study_ids),
                related_hypotheses=list(sf.related_hypothesis_ids),
                related_findings=list(sf.source_finding_ids),
                recommended_action=(
                    f"Increase evidence quality for '{sf.metric}': add corroborating "
                    f"studies, resolve contradictions, or improve per-finding confidence."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-09: KNOWLEDGE_GAP ─────────────────────────────────────────────────
    def _rule_knowledge_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        """Fires for hypotheses open longer than max_hypothesis_open_days."""
        rule_id   = "R-GD-09"
        if self._reg is None:
            return []
        threshold = self._cfg.max_hypothesis_open_days
        params    = {"max_hypothesis_open_days": threshold}
        now       = datetime.now()
        result: List[KnowledgeGap] = []

        for hyp in self._reg.list_open():
            age = (now - hyp.created_at).days
            if age <= threshold:
                continue
            sev      = _PRIORITY_TO_SEV.get(hyp.priority, GapSeverity.MEDIUM)
            rationale = (
                f"Hypothesis {hyp.hypothesis_id} open {age} days "
                f"(>{threshold}), priority {hyp.priority.value}"
            )
            study_refs = [
                ev.evidence_id
                for ev in hyp.supporting_evidence
                if ev.evidence_type == EvidenceType.STUDY
            ]
            result.append(_kg(
                category=GapCategory.KNOWLEDGE_GAP,
                rule_id=rule_id,
                source_key=hyp.hypothesis_id,
                title=f"Stalled hypothesis: {hyp.title[:70]}",
                description=(
                    f"Hypothesis {hyp.hypothesis_id} ('{hyp.title}') has been in "
                    f"status '{hyp.status.value}' for {age} days, exceeding the "
                    f"{threshold}-day limit. "
                    f"Priority: {hyp.priority.value}. "
                    f"Classification: {hyp.classification.value}."
                ),
                severity=sev,
                severity_rationale=rationale,
                confidence=1.0,
                supporting_evidence=[
                    hyp.hypothesis_id,
                    f"age_days:{age}",
                    f"status:{hyp.status.value}",
                ],
                related_studies=study_refs,
                related_hypotheses=[hyp.hypothesis_id],
                related_findings=[],
                recommended_action=(
                    f"Escalate hypothesis {hyp.hypothesis_id} to the research queue. "
                    f"Advance '{hyp.status.value}' to the next lifecycle stage or archive."
                ),
                rule_parameters=params,
            ))
        return result

    # ── R-GD-10: COVERAGE_GAP ─────────────────────────────────────────────────
    def _rule_coverage_gap(self, warnings: List[str]) -> List[KnowledgeGap]:
        """
        Fires for each FindingClassification (excluding UNKNOWN) that has zero
        findings across all studies.  Severity: always HIGH.
        """
        rule_id       = "R-GD-10"
        params: Dict[str, Any] = {}
        covered       = {f.classification for f in self._kp.list_findings()}
        all_study_ids = [s.study_id for s in self._kp.list_studies()]
        result: List[KnowledgeGap] = []

        for cls in FindingClassification:
            if cls == FindingClassification.UNKNOWN:
                continue
            if cls in covered:
                continue
            result.append(_kg(
                category=GapCategory.COVERAGE_GAP,
                rule_id=rule_id,
                source_key=cls.value,
                title=f"No findings of classification '{cls.value}'",
                description=(
                    f"No study has produced findings of classification '{cls.value}'. "
                    f"This research area has never been systematically investigated "
                    f"across {len(all_study_ids)} available study/studies."
                ),
                severity=GapSeverity.HIGH,
                severity_rationale=(
                    f"Zero findings of type '{cls.value}' across all "
                    f"{len(all_study_ids)} studies"
                ),
                confidence=1.0,
                supporting_evidence=[
                    f"classification:{cls.value}",
                    f"studies_checked:{len(all_study_ids)}",
                ],
                related_studies=all_study_ids,
                related_hypotheses=[],
                related_findings=[],
                recommended_action=(
                    f"Design a study specifically targeting '{cls.value}' findings "
                    f"to establish baseline research coverage."
                ),
                rule_parameters=params,
            ))
        return result

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _build_statistics(
        self, gaps: List[KnowledgeGap], duration_ms: float
    ) -> GapStatistics:
        by_cat: Dict[str, int]    = {}
        by_sev: Dict[str, int]    = {}
        rules: Dict[str, int]     = {}
        for g in gaps:
            by_cat[g.category.value] = by_cat.get(g.category.value, 0) + 1
            by_sev[g.severity.value] = by_sev.get(g.severity.value, 0) + 1
            rules[g.rule_id]         = rules.get(g.rule_id, 0) + 1
        open_count = sum(1 for g in gaps if g.status == GapStatus.OPEN)
        return GapStatistics(
            total_gaps=len(gaps),
            open_gaps=open_count,
            by_category=by_cat,
            by_severity=by_sev,
            critical_count=by_sev.get(GapSeverity.CRITICAL.value, 0),
            high_count=by_sev.get(GapSeverity.HIGH.value, 0),
            detection_duration_ms=round(duration_ms, 2),
            detected_at=datetime.now(),
            rules_fired=rules,
        )

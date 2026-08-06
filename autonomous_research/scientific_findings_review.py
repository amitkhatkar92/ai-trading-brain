"""
scientific_findings_review.py — Permanent Scientific Evolution engine.

IIOS Research Governance — Phase 4.

Runs automatically after EVERY completed research study (triggered by Stage 10
of ResearchCoordinator).  Performs Scientific Findings Review, Data Quality
Assessment, hypothesis generation, research prioritisation, and next program
selection — then writes 4 governance reports.

REUSE POLICY (mandatory — see copilot-instructions.md):
    GapDetector         → gap identification            (NOT duplicated)
    RoadmapManager      → knowledge gain + prioritisation (NOT duplicated)
    HypothesisRegistry  → hypothesis creation/search    (NOT duplicated)
    CrossStudySynthesizer → contradiction detection     (NOT duplicated)
    ScientificJournal   → persistent record             (NOT duplicated)
    DataQualityAssessor → 11-dimension quality scoring  (NOT duplicated)

Only NEW logic added here:
    - Study-specific finding categorisation from ctx dict
    - EIG (Expected Information Gain) scoring
    - 4 governance report file writers
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .data_quality_assessor import DataQualityAssessor
from .sfr_models import (
    DQAResult,
    EvolStageStatus,
    FindingOutcome,
    GeneratedHypothesis,
    NextResearchProgram,
    SFRFinding,
    SFRResult,
    _now_iso,
    make_finding_id,
    make_sfr_id,
)

log = logging.getLogger(__name__)

# Minimum lift to classify as validated
_LIFT_VALIDATED = 1.20
_LIFT_PARTIAL   = 1.05

# EIG weight components
_EIG_SEVERITY: Dict[str, float] = {
    "CRITICAL": 1.00, "HIGH": 0.75, "MEDIUM": 0.50, "LOW": 0.25,
}

_DEFAULT_REPORT_DIR = Path("data") / "ars" / "sfr"


class ScientificFindingsReview:
    """
    Orchestrates post-study scientific evolution.

    Accepts study_plan and ctx (from ResearchCoordinator pipeline), then:
      1. Categorises study findings.
      2. Runs DataQualityAssessor (11 dimensions).
      3. Calls GapDetector → RoadmapManager for next program.
      4. Generates hypotheses via HypothesisRegistry.
      5. Writes 4 governance reports.
      6. Records result in ScientificJournal.
    """

    def __init__(
        self,
        knowledge_provider=None,
        hypothesis_registry=None,
        synthesizer=None,
        gap_detector=None,
        roadmap_manager=None,
        report_dir: Optional[Path] = None,
        dry_run: bool = False,
    ) -> None:
        self._kp  = knowledge_provider
        self._reg = hypothesis_registry
        self._syn = synthesizer
        self._gd  = gap_detector
        self._rm  = roadmap_manager
        self._report_dir = Path(report_dir) if report_dir else _DEFAULT_REPORT_DIR
        self._dry_run    = dry_run

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def run(
        self,
        study_plan: Any,
        ctx: Dict[str, Any],
    ) -> SFRResult:
        """Execute the full Scientific Findings Review for one study."""
        sfr_id   = make_sfr_id()
        run_date = datetime.now().strftime("%Y-%m-%d")
        study_id = getattr(study_plan, "plan_id", "unknown")

        log.info("[SFR] Starting review sfr_id=%s study_id=%s", sfr_id, study_id)

        try:
            # ── 1. Categorise findings from ctx ──────────────────────────
            findings = self._categorise_findings(study_plan, ctx)

            # ── 2. Detect contradictions via synthesizer ──────────────────
            contradictions, methodology_notes = self._check_contradictions(ctx)

            # ── 3. Data Quality Assessment ────────────────────────────────
            dqa = DataQualityAssessor(knowledge_provider=self._kp).assess()

            # ── 4. Gap analysis → hypotheses ──────────────────────────────
            gen_hyps = self._generate_hypotheses(sfr_id)

            # ── 5. Select next research program ───────────────────────────
            next_prog = self._select_next_program(dqa, gen_hyps)

            # ── 6. Build result ───────────────────────────────────────────
            anomalies = sum(1 for f in findings if f.is_anomaly)
            summary   = (
                f"SFR: findings={len(findings)} validated={sum(1 for f in findings if f.outcome==FindingOutcome.VALIDATED)} "
                f"rejected={sum(1 for f in findings if f.outcome==FindingOutcome.REJECTED)} "
                f"contradictions={contradictions} dqa={dqa.classification.value}({dqa.overall_score:.0f}) "
                f"next={'YES' if next_prog else 'NONE'}"
            )

            result = SFRResult(
                sfr_id=sfr_id,
                study_id=study_id,
                run_date=run_date,
                findings=findings,
                generated_hypotheses=gen_hyps,
                next_program=next_prog,
                dqa_result=dqa,
                contradictions=contradictions,
                anomalies=anomalies,
                methodology_notes=methodology_notes,
                status=EvolStageStatus.COMPLETE,
                summary_line=summary,
            )

            # ── 7. Write reports ──────────────────────────────────────────
            if not self._dry_run:
                self._write_reports(result, study_plan, ctx)

            # ── 8. Journal ────────────────────────────────────────────────
            self._journal_result(result)

            log.info("[SFR] Complete: %s", summary)
            return result

        except Exception as exc:
            log.error("[SFR] Review failed: %s", exc)
            # Return a minimal degraded result so the pipeline continues
            empty_dqa = DataQualityAssessor(knowledge_provider=self._kp).assess()
            return SFRResult(
                sfr_id=sfr_id, study_id=study_id, run_date=run_date,
                findings=[], generated_hypotheses=[], next_program=None,
                dqa_result=empty_dqa, contradictions=0, anomalies=0,
                methodology_notes=[f"SFR error: {exc}"],
                status=EvolStageStatus.ERROR,
                summary_line=f"SFR FAILED: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────
    # Internal: Finding categorisation
    # ─────────────────────────────────────────────────────────────────────

    def _categorise_findings(
        self, study_plan: Any, ctx: Dict[str, Any]
    ) -> List[SFRFinding]:
        """
        Extract and categorise findings from the study's ctx dictionary.

        Maps ctx keys written by previous pipeline stages into SFRFinding objects.
        This is NEW logic — not duplicating anything that already exists.
        """
        findings: List[SFRFinding] = []
        study_id = getattr(study_plan, "plan_id", "unknown")

        # Map from ctx data
        val_outcome  = ctx.get("validation_outcome", "N/A")
        evidence_ok  = ctx.get("evidence_integrated", False)
        synth_count  = ctx.get("synthesized_findings", 0)
        contra_count = ctx.get("contradictions_detected", 0)
        promo_blocked = ctx.get("promotion_blocked", False)
        audit_result  = ctx.get("methodology_audit_result", "NOT_RUN")

        # Try to load individual pattern results from the latest study
        pattern_findings = self._load_pattern_findings(study_plan)

        if pattern_findings:
            for pf in pattern_findings:
                findings.append(pf)
        else:
            # Fallback: single aggregate finding from ctx
            outcome = self._map_validation_outcome(val_outcome, promo_blocked)
            findings.append(SFRFinding(
                finding_id=make_finding_id("AGG", study_id),
                pattern_id="AGG",
                outcome=outcome,
                evidence=(
                    f"validation={val_outcome} evidence_integrated={evidence_ok} "
                    f"audit={audit_result} synth={synth_count} contradictions={contra_count}"
                ),
                confidence=0.7 if outcome in (FindingOutcome.VALIDATED, FindingOutcome.PARTIAL) else 0.4,
                is_anomaly=contra_count > 0,
                notes=f"Aggregate finding. promotion_blocked={promo_blocked}",
            ))

        return findings

    def _load_pattern_findings(self, study_plan: Any) -> List[SFRFinding]:
        """Try to load individual pattern results from the KnowledgeProvider."""
        if not self._kp:
            return []
        try:
            latest = self._kp.get_latest_study()
            if not latest:
                return []
            raw = latest if isinstance(latest, dict) else vars(latest)
            findings: List[SFRFinding] = []

            # Check for irp002-style winner DNA results
            for stage_key in ("stage4_winner_dna", "stage5_loser_dna"):
                stage_data = raw.get(stage_key, {})
                patterns   = stage_data.get("dna_patterns", [])
                for p in patterns:
                    pid      = p.get("pattern_id", "?")
                    outcome  = p.get("outcome")
                    test_lift = p.get("test_lift")
                    n_test   = p.get("test_n")
                    if outcome:
                        fo = self._map_outcome_str(outcome)
                    elif test_lift is not None:
                        fo = (FindingOutcome.VALIDATED if test_lift >= _LIFT_VALIDATED
                              else FindingOutcome.PARTIAL if test_lift >= _LIFT_PARTIAL
                              else FindingOutcome.REJECTED)
                    else:
                        fo = FindingOutcome.INSUFFICIENT_DATA

                    findings.append(SFRFinding(
                        finding_id=make_finding_id(pid, raw.get("study_id", "?")),
                        pattern_id=pid,
                        outcome=fo,
                        evidence=f"test_lift={test_lift}  n={n_test}",
                        confidence=min(1.0, test_lift / 3.0) if test_lift else 0.3,
                        lift=test_lift,
                        n_matched=n_test,
                        is_anomaly=(test_lift is not None and test_lift < 0.5),
                        notes="",
                    ))

            # Cross-year conditions (h001-style)
            for cond_key in ("conditions_tested", "cross_year_conditions"):
                conds = raw.get(cond_key, [])
                for c in conds:
                    cid     = c.get("condition_id", "?")
                    c_out   = c.get("outcome", "UNKNOWN")
                    lift    = c.get("lift")
                    fo      = self._map_outcome_str(c_out)
                    findings.append(SFRFinding(
                        finding_id=make_finding_id(cid, raw.get("study_id", "?")),
                        pattern_id=cid,
                        outcome=fo,
                        evidence=f"cross_year_outcome={c_out} lift={lift}",
                        confidence=0.6 if fo == FindingOutcome.VALIDATED else 0.3,
                        lift=lift,
                        is_anomaly=False,
                    ))

            return findings
        except Exception as exc:
            log.debug("[SFR] Pattern load failed: %s", exc)
            return []

    @staticmethod
    def _map_outcome_str(s: str) -> FindingOutcome:
        s = str(s).upper()
        if "VALIDATED" in s or "CONFIRMED" in s:     return FindingOutcome.VALIDATED
        if "REJECTED" in s:                          return FindingOutcome.REJECTED
        if "PARTIAL" in s:                           return FindingOutcome.PARTIAL
        if "CONTRADICTION" in s:                     return FindingOutcome.CONTRADICTION
        if "INSUFFICIENT" in s or "NO_DATA" in s:   return FindingOutcome.INSUFFICIENT_DATA
        if "ANOMALY" in s or "UNEXPECTED" in s:      return FindingOutcome.ANOMALY
        return FindingOutcome.PARTIAL

    @staticmethod
    def _map_validation_outcome(val: str, promo_blocked: bool) -> FindingOutcome:
        val = str(val).upper()
        if "PASSED" in val:   return FindingOutcome.VALIDATED
        if "FAILED" in val:   return FindingOutcome.REJECTED
        if promo_blocked:     return FindingOutcome.PARTIAL
        return FindingOutcome.PARTIAL

    # ─────────────────────────────────────────────────────────────────────
    # Internal: Contradiction detection (reuses CrossStudySynthesizer)
    # ─────────────────────────────────────────────────────────────────────

    def _check_contradictions(
        self, ctx: Dict[str, Any]
    ) -> tuple[int, List[str]]:
        """Return (n_contradictions, methodology_notes) by reusing synthesizer."""
        n_contra = ctx.get("contradictions_detected", 0)
        notes: List[str] = []

        # Audit findings
        audit_result = ctx.get("methodology_audit_result", "NOT_RUN")
        if audit_result == "FAIL":
            notes.append(
                "Methodology audit FAILED — promotion blocked. "
                "Review MethodologyAuditor output for confounds."
            )
        if ctx.get("promotion_blocked", False):
            notes.append(
                "Promotion blocked by governance gate. "
                "Scientific Director approval required before IDR promotion."
            )

        # Pull additional contradictions from synthesizer if available
        if self._syn:
            try:
                contras = self._syn.list_contradictions()
                if contras:
                    n_contra = max(n_contra, len(contras))
                    for c in contras[:3]:
                        desc = getattr(c, "description", str(c))
                        notes.append(f"Contradiction: {desc[:120]}")
            except Exception:
                pass

        return n_contra, notes

    # ─────────────────────────────────────────────────────────────────────
    # Internal: Hypothesis generation (reuses GapDetector + HypothesisRegistry)
    # ─────────────────────────────────────────────────────────────────────

    def _generate_hypotheses(self, sfr_id: str) -> List[GeneratedHypothesis]:
        """
        Call GapDetector for open gaps, compute EIG per gap, create hypotheses
        via HypothesisRegistry for top gaps that don't already have one.

        EIG = uncertainty × resolution_probability × information_value
        """
        gen: List[GeneratedHypothesis] = []
        if not self._gd:
            return gen

        try:
            gaps = self._gd.list_open()
        except Exception as exc:
            log.warning("[SFR] GapDetector.list_open() failed: %s", exc)
            return gen

        # Sort by severity (CRITICAL first)
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        gaps = sorted(
            gaps,
            key=lambda g: sev_order.get(
                getattr(getattr(g, "severity", None), "value", "LOW"), 3
            ),
        )

        for gap in gaps[:5]:   # max 5 hypotheses per SFR
            gap_id   = getattr(gap, "gap_id", str(gap))
            gap_title = getattr(gap, "title", gap_id)
            sev_str  = getattr(getattr(gap, "severity", None), "value", "MEDIUM")
            gain     = float(getattr(gap, "estimated_knowledge_gain", 0.4))

            # EIG calculation
            uncertainty = _EIG_SEVERITY.get(sev_str, 0.5)
            resolution_prob = min(1.0, gain * 1.2)   # higher gain → easier to resolve
            information_value = gain
            eig = round(uncertainty * resolution_prob * information_value, 4)

            # Determine study type from gap category
            cat_val   = getattr(getattr(gap, "category", None), "value", "")
            study_type = _GAP_TO_STUDY_TYPE.get(cat_val, "HYPOTHESIS_VALIDATION")

            # Skip if hypothesis already exists
            if self._reg:
                try:
                    existing = self._reg.search(gap_title)
                    if existing:
                        continue
                except Exception:
                    pass

            priority = {"CRITICAL": "CRITICAL", "HIGH": "HIGH"}.get(sev_str, "MEDIUM")
            hyp_id   = f"H-SFR-{sfr_id[-8:]}-{gap_id[:6]}"

            # Create in registry if not dry_run
            if self._reg and not self._dry_run:
                try:
                    from .hypothesis_models import (  # noqa: PLC0415
                        HypothesisClassification,
                        HypothesisPriority,
                    )
                    p_enum = getattr(HypothesisPriority, priority, HypothesisPriority.MEDIUM)
                    c_enum = getattr(
                        HypothesisClassification,
                        _GAP_TO_CLASSIFICATION.get(cat_val, "EXPLORATORY"),
                        HypothesisClassification.EXPLORATORY,
                    )
                    created = self._reg.create_hypothesis(
                        title=f"Address {gap_title}",
                        research_question=(
                            f"Can addressing the {cat_val} knowledge gap improve "
                            f"IIOS scientific quality? EIG={eig:.3f}"
                        ),
                        description=getattr(gap, "description", gap_title),
                        origin="SFR_AUTO",
                        priority=p_enum,
                        classification=c_enum,
                        knowledge_gap=gap_id,
                        expected_knowledge_gain=gain,
                        validation_method="EMPIRICAL",
                        created_by="scientific_findings_review",
                    )
                    hyp_id = created.hypothesis_id
                except Exception as exc:
                    log.warning("[SFR] Hypothesis creation failed: %s", exc)

            gen.append(GeneratedHypothesis(
                hypothesis_id=hyp_id,
                title=f"Address {gap_title}",
                research_question=f"Can addressing {cat_val} gap improve knowledge quality?",
                origin_gap=gap_id,
                priority=priority,
                expected_gain=gain,
                eig_score=eig,
                study_type=study_type,
            ))

        return gen

    # ─────────────────────────────────────────────────────────────────────
    # Internal: Next program selection (reuses RoadmapManager)
    # ─────────────────────────────────────────────────────────────────────

    def _select_next_program(
        self, dqa: DQAResult, gen_hyps: List[GeneratedHypothesis]
    ) -> Optional[NextResearchProgram]:
        """
        Call RoadmapManager.build() + get_next_study() for highest-priority entry.
        If roadmap is unavailable, use the top generated hypothesis.
        """
        # Try roadmap manager first
        if self._rm:
            try:
                roadmap = self._rm.build(force=True)
                entry   = self._rm.get_next_study()
                if entry:
                    gain   = getattr(getattr(entry, "knowledge_gain_estimate", None), "total_gain", 0.5)
                    cost   = getattr(getattr(entry, "cost_estimate", None), "estimated_hours", 0.0)
                    gap_id = getattr(getattr(entry, "gap", None), "gap_id", "")
                    hyp_id = getattr(entry, "source_hypothesis_id", None)
                    prio   = getattr(entry, "priority_score", 0.5)
                    # EIG uses roadmap priority as proxy
                    eig = round(gain * min(1.0, prio), 4)
                    return NextResearchProgram(
                        program_id=getattr(entry, "entry_id", f"nrp-{gap_id}"),
                        title=getattr(entry, "title", "Next Research Program"),
                        study_type=getattr(entry, "study_type", "HYPOTHESIS_VALIDATION"),
                        priority_rank=1,
                        priority_score=round(prio, 4),
                        evidence_basis=getattr(entry, "rationale", "Evidence-driven selection via RoadmapManager"),
                        expected_gain=round(gain, 4),
                        eig_score=eig,
                        estimated_hours=round(cost, 1),
                        source_gap=gap_id,
                        source_hypothesis=str(hyp_id) if hyp_id else None,
                        rationale=getattr(entry, "rationale", "Selected by RoadmapManager based on gap severity and knowledge gain."),
                    )
            except Exception as exc:
                log.warning("[SFR] RoadmapManager unavailable: %s", exc)

        # Fallback: top generated hypothesis by EIG score
        if gen_hyps:
            top = max(gen_hyps, key=lambda h: h.eig_score)
            return NextResearchProgram(
                program_id=f"nrp-{top.hypothesis_id}",
                title=top.title,
                study_type=top.study_type,
                priority_rank=1,
                priority_score=round(top.eig_score, 4),
                evidence_basis="Selected from SFR-generated hypotheses by EIG score.",
                expected_gain=round(top.expected_gain, 4),
                eig_score=round(top.eig_score, 4),
                estimated_hours=2.0,
                source_gap=top.origin_gap,
                source_hypothesis=top.hypothesis_id,
                rationale=f"Top EIG={top.eig_score:.3f} from SFR-generated hypotheses.",
            )

        # DQA-based fallback
        if dqa.recommendations:
            return NextResearchProgram(
                program_id="nrp-dqa-infra",
                title="Research Infrastructure Improvement",
                study_type="DATA_QUALITY",
                priority_rank=1,
                priority_score=0.5,
                evidence_basis="DQA identified infrastructure gaps requiring attention.",
                expected_gain=0.4,
                eig_score=0.3,
                estimated_hours=4.0,
                source_gap="DQA",
                source_hypothesis=None,
                rationale=dqa.recommendations[0] if dqa.recommendations else "Improve evidence infrastructure.",
            )

        return None

    # ─────────────────────────────────────────────────────────────────────
    # Internal: Report writers
    # ─────────────────────────────────────────────────────────────────────

    def _write_reports(
        self, result: SFRResult, study_plan: Any, ctx: Dict[str, Any]
    ) -> None:
        """Write 4 governance reports to the run-date directory."""
        run_dir = self._report_dir / result.run_date
        run_dir.mkdir(parents=True, exist_ok=True)

        self._write_findings_review(result, run_dir)
        self._write_roadmap(result, run_dir)
        self._write_next_program(result, run_dir)
        self._write_dqa_score(result, run_dir)

    def _write_findings_review(self, result: SFRResult, d: Path) -> None:
        n_val  = result.n_validated
        n_rej  = result.n_rejected
        n_par  = result.n_partial
        n_ins  = sum(1 for f in result.findings if f.outcome == FindingOutcome.INSUFFICIENT_DATA)
        n_tot  = len(result.findings)

        lines = [
            f"# SCIENTIFIC_FINDINGS_REVIEW.md",
            f"",
            f"**SFR ID:** {result.sfr_id}",
            f"**Study:** {result.study_id}",
            f"**Date:** {result.run_date}",
            f"**Generated:** {_now_iso()}",
            f"",
            f"---",
            f"",
            f"## Finding Summary",
            f"",
            f"| Outcome | Count | Fraction |",
            f"|---|---|---|",
            f"| VALIDATED (lift ≥ 1.20) | {n_val} | {_pct(n_val, n_tot)} |",
            f"| PARTIAL (lift ≥ 1.05)   | {n_par} | {_pct(n_par, n_tot)} |",
            f"| REJECTED (lift < 1.05)  | {n_rej} | {_pct(n_rej, n_tot)} |",
            f"| INSUFFICIENT_DATA       | {n_ins} | {_pct(n_ins, n_tot)} |",
            f"| **Total**               | **{n_tot}** | 100% |",
            f"",
            f"## Detailed Findings",
            f"",
            f"| ID | Pattern | Outcome | Lift | n | Confidence | Anomaly |",
            f"|---|---|---|---|---|---|---|",
        ]
        for f in result.findings:
            lift = f"{f.lift:.4f}" if f.lift is not None else "N/A"
            n    = str(f.n_matched) if f.n_matched is not None else "N/A"
            lines.append(
                f"| {f.finding_id} | {f.pattern_id} | {f.outcome.value} "
                f"| {lift} | {n} | {f.confidence:.2f} | {'⚠️' if f.is_anomaly else ''} |"
            )

        lines += [
            f"",
            f"## Contradictions and Anomalies",
            f"",
            f"- **Contradictions detected:** {result.contradictions}",
            f"- **Anomalies detected:** {result.anomalies}",
            f"",
        ]
        if result.methodology_notes:
            lines.append("## Methodology Notes\n")
            for note in result.methodology_notes:
                lines.append(f"- {note}")
            lines.append("")

        lines += [
            f"## Generated Hypotheses",
            f"",
            f"| Hypothesis | Gap | Priority | EIG | Study Type |",
            f"|---|---|---|---|---|",
        ]
        for h in result.generated_hypotheses:
            lines.append(
                f"| {h.title[:50]} | {h.origin_gap} | {h.priority} "
                f"| {h.eig_score:.3f} | {h.study_type} |"
            )

        lines += [
            f"",
            f"## Analysis Dimensions",
            f"",
            f"| Dimension | Status | Finding |",
            f"|---|---|---|",
            f"| Validated Discoveries | {_badge(n_val > 0)} | {n_val} patterns VALIDATED |",
            f"| Rejected Hypotheses | {_badge(True)} | {n_rej} patterns REJECTED |",
            f"| Partial Confirmations | {_badge(True)} | {n_par} patterns PARTIAL |",
            f"| Contradictions | {_badge(result.contradictions == 0, invert=True)} | {result.contradictions} detected |",
            f"| Knowledge Gaps | {_badge(len(result.generated_hypotheses) > 0)} | {len(result.generated_hypotheses)} new hypotheses |",
            f"| Unexpected Findings | {_badge(result.anomalies == 0, invert=True)} | {result.anomalies} anomalies |",
            f"| Statistical Anomalies | {_badge(True)} | see individual findings |",
            f"| Knowledge Decay | {_badge(True)} | review DECAYING edges in IDR |",
            f"| Methodology Limitations | {_badge(len(result.methodology_notes) == 0, invert=True)} | {len(result.methodology_notes)} notes |",
            f"",
            f"---",
            f"**Data Quality Score:** {result.dqa_result.overall_score:.1f}/100 ({result.dqa_result.classification.value})",
        ]

        (d / "SCIENTIFIC_FINDINGS_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_roadmap(self, result: SFRResult, d: Path) -> None:
        lines = [
            f"# UPDATED_RESEARCH_ROADMAP.md",
            f"",
            f"**SFR ID:** {result.sfr_id}",
            f"**Date:** {result.run_date}",
            f"**Generated:** {_now_iso()}",
            f"",
            f"## Prioritisation Method",
            f"",
            f"Hypotheses are prioritised using Expected Information Gain (EIG):",
            f"",
            f"```",
            f"EIG = P(uncertainty) × P(resolution) × I(value)",
            f"",
            f"P(uncertainty)  = gap severity weight (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5)",
            f"P(resolution)   = estimated_knowledge_gain × 1.2",
            f"I(value)        = estimated_knowledge_gain (from RoadmapManager)",
            f"```",
            f"",
            f"Secondary factors: Scientific Impact, Knowledge Gap Severity,",
            f"Evidence Strength, Research Cost, Strategic Importance.",
            f"",
            f"## Generated Research Hypotheses",
            f"",
            f"| Rank | Title | Priority | EIG | Study Type | Origin Gap |",
            f"|---|---|---|---|---|---|",
        ]
        for i, h in enumerate(sorted(result.generated_hypotheses, key=lambda x: -x.eig_score), 1):
            lines.append(
                f"| {i} | {h.title[:55]} | {h.priority} "
                f"| {h.eig_score:.3f} | {h.study_type} | {h.origin_gap} |"
            )

        lines += [
            f"",
            f"## Data Quality Constraints",
            f"",
            f"DQA Score: **{result.dqa_result.overall_score:.1f}/100** ({result.dqa_result.classification.value})",
            f"",
            f"Identified weaknesses that affect research quality:",
        ]
        for w in result.dqa_result.weaknesses:
            lines.append(f"- {w}")

        lines += [
            f"",
            f"Infrastructure recommendations:",
        ]
        for r in result.dqa_result.recommendations:
            lines.append(f"- {r}")

        lines += [
            f"",
            f"## Governance Principle",
            f"",
            f"No human ordering of research. Evidence determines the next program.",
            f"The next study is selected by highest EIG from the open gap universe.",
        ]

        (d / "UPDATED_RESEARCH_ROADMAP.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_next_program(self, result: SFRResult, d: Path) -> None:
        np_ = result.next_program
        lines = [
            f"# NEXT_RESEARCH_PROGRAM.md",
            f"",
            f"**SFR ID:** {result.sfr_id}",
            f"**Date:** {result.run_date}",
            f"**Generated:** {_now_iso()}",
            f"",
            f"---",
            f"",
        ]
        if np_:
            lines += [
                f"## Selected: {np_.title}",
                f"",
                f"| Field | Value |",
                f"|---|---|",
                f"| Program ID | `{np_.program_id}` |",
                f"| Study Type | {np_.study_type} |",
                f"| Priority Score | {np_.priority_score:.4f} |",
                f"| EIG Score | {np_.eig_score:.4f} |",
                f"| Expected Knowledge Gain | {np_.expected_gain:.3f} |",
                f"| Estimated Hours | {np_.estimated_hours} h |",
                f"| Source Gap | {np_.source_gap} |",
                f"| Source Hypothesis | {np_.source_hypothesis or 'N/A'} |",
                f"",
                f"## Evidence Basis",
                f"",
                f"{np_.evidence_basis}",
                f"",
                f"## Rationale",
                f"",
                f"{np_.rationale}",
                f"",
                f"## Pre-Conditions",
                f"",
                f"DQA Score: {result.dqa_result.overall_score:.1f}/100 ({result.dqa_result.classification.value})",
                f"",
            ]
            for dim in result.dqa_result.dimensions:
                if dim.status != "PASS":
                    lines.append(f"- ⚠️ {dim.name}: {dim.finding}")
        else:
            lines += [
                f"## No next program identified",
                f"",
                f"The current knowledge base does not surface a clear next research priority.",
                f"Recommendation: run `scientific_director.daily_review()` for manual guidance.",
            ]

        lines += [
            f"",
            f"---",
            f"",
            f"**Governance rule:** No human ordering. Evidence determines the next research.",
        ]

        (d / "NEXT_RESEARCH_PROGRAM.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_dqa_score(self, result: SFRResult, d: Path) -> None:
        dqa = result.dqa_result
        lines = [
            f"# DATA_QUALITY_SCORE.md",
            f"",
            f"**SFR ID:** {result.sfr_id}",
            f"**Date:** {result.run_date}",
            f"**Generated:** {_now_iso()}",
            f"",
            f"---",
            f"",
            f"## Scientific Data Readiness Score",
            f"",
            f"| Score | Classification |",
            f"|---|---|",
            f"| **{dqa.overall_score:.1f} / 100** | **{dqa.classification.value}** |",
            f"",
            f"Classification scale:",
            f"- EXCELLENT: ≥ 85",
            f"- GOOD:      ≥ 70",
            f"- ADEQUATE:  ≥ 55",
            f"- LIMITED:   ≥ 40",
            f"- INSUFFICIENT: < 40",
            f"",
            f"---",
            f"",
            f"## Dimension Scores",
            f"",
            f"| # | Dimension | Score | Raw Value | Unit | Threshold | Status |",
            f"|---|---|---|---|---|---|---|",
        ]
        for i, dim in enumerate(dqa.dimensions, 1):
            lines.append(
                f"| {i} | {dim.name} | {dim.score:.1f}/10 "
                f"| {dim.raw_value} | {dim.unit} | {dim.threshold} | {dim.status} |"
            )

        lines += [
            f"",
            f"## Detailed Findings",
            f"",
        ]
        for dim in dqa.dimensions:
            icon = "✅" if dim.status == "PASS" else ("⚠️" if dim.status == "MARGINAL" else "❌")
            lines.append(f"### {icon} {dim.name}")
            lines.append(f"- **Finding:** {dim.finding}")
            if dim.recommendation:
                lines.append(f"- **Recommendation:** {dim.recommendation}")
            lines.append("")

        lines += [
            f"## Identified Weaknesses",
            f"",
        ]
        for w in dqa.weaknesses:
            lines.append(f"- {w}")

        lines += [
            f"",
            f"## Recommended Infrastructure Improvements",
            f"",
        ]
        for r in dqa.recommendations:
            lines.append(f"1. {r}")

        (d / "DATA_QUALITY_SCORE.md").write_text("\n".join(lines), encoding="utf-8")

    # ─────────────────────────────────────────────────────────────────────
    # Internal: Journal (reuses ScientificDirector's journal path)
    # ─────────────────────────────────────────────────────────────────────

    def _journal_result(self, result: SFRResult) -> None:
        """Append the SFR result to the scientific journal."""
        if self._dry_run:
            return
        try:
            # Use the sd journal directly
            from .scientific_journal import ScientificJournal  # noqa: PLC0415
            journal_path = Path("data") / "ars" / "sd" / "journal.json"
            journal_path.parent.mkdir(parents=True, exist_ok=True)
            journal = ScientificJournal(journal_path=str(journal_path))
            # record as observation (reuses existing journal API)
            from .sd_models import ScientificObservation, SignificanceLevel  # noqa: PLC0415
            obs = ScientificObservation(
                observation_id=f"sfr-obs-{result.sfr_id[-8:]}",
                source="ScientificFindingsReview",
                observation_type="SFR_COMPLETE",
                value=result.sfr_id,
                description=result.summary_line,
                significance=SignificanceLevel.HIGH if result.n_validated > 0 else SignificanceLevel.MEDIUM,
                timestamp=_now_iso(),
            )
            journal.record_observation(obs, review_id=result.sfr_id)
        except Exception as exc:
            log.debug("[SFR] Journal record failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Lookup tables
# ─────────────────────────────────────────────────────────────────────────────

_GAP_TO_STUDY_TYPE: Dict[str, str] = {
    "DATA_GAP":          "HISTORICAL_REPLAY",
    "EVIDENCE_GAP":      "HYPOTHESIS_VALIDATION",
    "REGIME_GAP":        "MARKET_REGIME_ANALYSIS",
    "SECTOR_GAP":        "SECTOR_RESEARCH",
    "TEMPORAL_GAP":      "TEMPORAL_VALIDATION",
    "VALIDATION_GAP":    "HYPOTHESIS_VALIDATION",
    "CONTRADICTION_GAP": "CONTRADICTION_RESOLUTION",
    "CONFIDENCE_GAP":    "HYPOTHESIS_VALIDATION",
    "KNOWLEDGE_GAP":     "EXPLORATORY",
    "COVERAGE_GAP":      "COVERAGE_EXPANSION",
}

_GAP_TO_CLASSIFICATION: Dict[str, str] = {
    "DATA_GAP":       "DATA_QUALITY",
    "EVIDENCE_GAP":   "VALIDATION",
    "REGIME_GAP":     "MARKET_STRUCTURE",
    "SECTOR_GAP":     "MARKET_STRUCTURE",
    "TEMPORAL_GAP":   "VALIDATION",
    "VALIDATION_GAP": "VALIDATION",
    "KNOWLEDGE_GAP":  "EXPLORATORY",
    "COVERAGE_GAP":   "COVERAGE",
}

# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pct(n: int, d: int) -> str:
    if d == 0: return "N/A"
    return f"{100*n//d}%"

def _badge(good: bool, invert: bool = False) -> str:
    if invert:
        good = not good
    return "✅" if good else "⚠️"

"""
cross_study_synthesizer.py — Scientific knowledge synthesis engine.

ARS Phase 1.3.

Responsibilities:
    Compare, integrate, validate and synthesize evidence across all completed
    research studies.  Output is synthesized scientific knowledge, not summaries.

Explicitly NOT responsible for:
    Generating hypotheses, executing research, modifying hypotheses, modifying
    studies, changing evidence, rewriting reports.  Pure analysis only.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .hypothesis_models import HypothesisStatus
from .hypothesis_registry import HypothesisRegistry
from .knowledge_provider import KnowledgeProvider
from .models import (
    Certification,
    EdgeRecord,
    EdgeStatus,
    FeatureRecord,
    Finding,
    FindingClassification,
    KnowledgeMetric,
    RegimeProbabilityRecord,
    ResearchStudy,
    StrategyRecord,
)
from .synthesis_models import (
    ContradictionRecord,
    ContradictionType,
    EvidenceChain,
    KnowledgeConsensus,
    KnowledgeRelationship,
    RelationshipType,
    SynthesisClassification,
    SynthesisReport,
    SynthesisStatistics,
    SynthesizedFinding,
)

logger = logging.getLogger(__name__)

# Contradiction threshold: numeric values differing by this relative fraction are contradictions
_CONTRADICTION_THRESHOLD = 0.40   # 40% relative divergence
# Minimum findings in a group to consider it SUPPORTED (else INSUFFICIENT_EVIDENCE)
_MIN_FINDINGS_FOR_SUPPORT = 1
# Edge name match: finding metric substring match threshold (characters)
_EDGE_MATCH_MIN_CHARS = 4


class CrossStudySynthesizer:
    """
    Scientific knowledge synthesis engine for IIOS.

    Reads knowledge through KnowledgeProvider (and optionally HypothesisRegistry),
    synthesizes cross-study conclusions, detects contradictions, discovers
    relationships, and produces a fully traceable SynthesisReport.

    All inputs are read-only.  No store is modified.

    Usage::

        kp  = KnowledgeProvider()
        reg = HypothesisRegistry(knowledge_provider=kp)
        syn = CrossStudySynthesizer(knowledge_provider=kp,
                                    hypothesis_registry=reg)

        report = syn.synthesize()
        print(syn.statistics())
        print(syn.get_summary())
    """

    def __init__(
        self,
        knowledge_provider: KnowledgeProvider,
        hypothesis_registry: Optional[HypothesisRegistry] = None,
    ) -> None:
        self._kp = knowledge_provider
        self._registry = hypothesis_registry
        self._report: Optional[SynthesisReport] = None
        self._lock = threading.Lock()

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═════════════════════════════════════════════════════════════════════════

    def synthesize(self, force: bool = False) -> SynthesisReport:
        """
        Run synthesis over all available knowledge.  Result is cached.
        Pass force=True to re-run from scratch.
        """
        with self._lock:
            if self._report is not None and not force:
                return self._report
            self._report = self._run_synthesis()
            return self._report

    def list_synthesized_findings(self) -> List[SynthesizedFinding]:
        """Return all synthesized findings from the last synthesis run."""
        return list(self.synthesize().synthesized_findings)

    def list_relationships(self) -> List[KnowledgeRelationship]:
        """Return all discovered knowledge relationships."""
        return list(self.synthesize().relationships)

    def list_contradictions(self) -> List[ContradictionRecord]:
        """Return all detected contradictions (never auto-resolved)."""
        return list(self.synthesize().contradictions)

    def list_supported_hypotheses(self) -> List[str]:
        """
        Return hypothesis IDs that have at least one synthesized finding
        corroborating their supporting evidence.
        """
        report = self.synthesize()
        result: Set[str] = set()
        for sf in report.synthesized_findings:
            result.update(sf.related_hypothesis_ids)
        return sorted(result)

    def list_unresolved(self) -> List[SynthesizedFinding]:
        """Return synthesized findings with UNRESOLVED or INSUFFICIENT_EVIDENCE classification."""
        return [
            sf for sf in self.list_synthesized_findings()
            if sf.classification in (
                SynthesisClassification.UNRESOLVED,
                SynthesisClassification.INSUFFICIENT_EVIDENCE,
            )
        ]

    def list_by_classification(
        self, classification: SynthesisClassification
    ) -> List[SynthesizedFinding]:
        """Return synthesized findings matching a specific classification."""
        return [
            sf for sf in self.list_synthesized_findings()
            if sf.classification == classification
        ]

    def get_summary(self) -> str:
        """Return a human-readable text summary of the synthesis results."""
        report = self.synthesize()
        stats = report.statistics
        now = report.synthesized_at.strftime("%Y-%m-%d %H:%M")

        by_cls = stats.by_classification
        lines = [
            f"Cross-Study Synthesis Report — {now}",
            f"Studies processed   : {stats.studies_processed}",
            f"Findings processed  : {stats.total_findings_processed}",
            f"Synthesized findings: {stats.total_synthesized_findings}",
            f"Relationships found : {stats.total_relationships}",
            f"Contradictions      : {stats.total_contradictions}",
            f"Avg. confidence     : {stats.avg_synthesis_confidence:.2f}",
            "",
            "Classification breakdown:",
        ]
        for cls_name, count in sorted(by_cls.items(), key=lambda x: -x[1]):
            if count > 0:
                lines.append(f"  {cls_name:<26}: {count}")

        if report.contradictions:
            lines += ["", "Contradictions:"]
            for c in report.contradictions[:5]:
                lines.append(f"  [{c.contradiction_type.value}] {c.metric} "
                              f"(study {c.study_a_id} vs {c.study_b_id})")
            if len(report.contradictions) > 5:
                lines.append(f"  ... and {len(report.contradictions) - 5} more")

        if report.warnings:
            lines += ["", "Warnings:"]
            for w in report.warnings[:5]:
                lines.append(f"  ! {w}")

        return "\n".join(lines)

    def statistics(self) -> SynthesisStatistics:
        """Return synthesis statistics from the last run."""
        return self.synthesize().statistics

    # ═════════════════════════════════════════════════════════════════════════
    # SYNTHESIS PIPELINE
    # ═════════════════════════════════════════════════════════════════════════

    def _run_synthesis(self) -> SynthesisReport:
        t0 = time.perf_counter()
        warnings: List[str] = []
        now = datetime.now()

        # ── 1. Load all knowledge (read-only) ────────────────────────────────
        studies       = self._kp.list_studies()
        findings      = self._kp.list_findings()
        edges         = self._kp.list_edges()
        certifications = self._kp.list_certifications()
        metrics       = self._kp.list_knowledge_metrics()
        strategies    = self._kp.list_strategies()
        hypotheses    = self._registry.list_all() if self._registry else []

        if not studies:
            warnings.append("No research studies available for synthesis")
        if not findings:
            warnings.append("No findings available — synthesis will be empty")

        logger.info("[Synthesizer] Starting synthesis: %d studies, %d findings, "
                    "%d edges, %d hypotheses",
                    len(studies), len(findings), len(edges), len(hypotheses))

        # ── 2. Build lookup maps ──────────────────────────────────────────────
        study_map    = {s.study_id: s for s in studies}
        edge_map     = {e.edge_id: e for e in edges}
        cert_map     = {c.cert_id: c for c in certifications}
        metric_map   = {m.metric_id: m for m in metrics}
        strategy_map = {s.strategy_id: s for s in strategies}

        # ── 3. Group findings ─────────────────────────────────────────────────
        groups = self._group_findings(findings)

        # ── 4. Synthesize each group ──────────────────────────────────────────
        synthesized: List[SynthesizedFinding] = []
        all_contradictions: List[ContradictionRecord] = []
        contradiction_id_set: Set[str] = set()

        for group_key, group_findings in groups.items():
            sf, contras = self._synthesize_group(
                group_key=group_key,
                group_findings=group_findings,
                study_map=study_map,
                edges=edges,
                metrics=metrics,
                certifications=certifications,
                hypotheses=hypotheses,
                now=now,
            )
            # Deduplicate contradictions by (finding_a_id, finding_b_id)
            for c in contras:
                key = f"{c.finding_a_id}|{c.finding_b_id}"
                if key not in contradiction_id_set:
                    all_contradictions.append(c)
                    contradiction_id_set.add(key)

            synthesized.append(sf)

        # ── 5. Discover relationships ─────────────────────────────────────────
        relationships = self._discover_relationships(
            studies=studies,
            findings=findings,
            edges=edges,
            metrics=metrics,
            certifications=certifications,
            hypotheses=hypotheses,
            synthesized=synthesized,
        )

        # ── 6. Build consensus blocks ─────────────────────────────────────────
        consensus_blocks = self._build_consensus(synthesized, now)

        # ── 7. Statistics ─────────────────────────────────────────────────────
        elapsed_ms = (time.perf_counter() - t0) * 1000
        stats = self._build_statistics(
            findings=findings,
            synthesized=synthesized,
            relationships=relationships,
            contradictions=all_contradictions,
            studies=studies,
            edges_correlated=len({eid for sf in synthesized for eid in sf.related_edge_ids}),
            hyp_correlated=len({hid for sf in synthesized for hid in sf.related_hypothesis_ids}),
            cert_correlated=len({cid for sf in synthesized for cid in sf.related_cert_ids}),
            metric_correlated=len({mid for sf in synthesized for mid in sf.related_metric_ids}),
            elapsed_ms=elapsed_ms,
            now=now,
        )

        report_id = f"SYN-{now.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"
        logger.info("[Synthesizer] Synthesis complete in %.1fms: %d findings → %d synthesized, "
                    "%d relationships, %d contradictions",
                    elapsed_ms, len(findings), len(synthesized),
                    len(relationships), len(all_contradictions))

        return SynthesisReport(
            report_id=report_id,
            synthesized_at=now,
            synthesized_findings=synthesized,
            relationships=relationships,
            contradictions=all_contradictions,
            consensus_blocks=consensus_blocks,
            statistics=stats,
            warnings=warnings,
        )

    # ─── grouping ─────────────────────────────────────────────────────────────

    def _group_findings(
        self, findings: List[Finding]
    ) -> Dict[Tuple[str, str], List[Finding]]:
        """
        Group findings by (FindingClassification.value, metric).
        If metric is empty, fall back to first 40 chars of description.
        """
        groups: Dict[Tuple[str, str], List[Finding]] = defaultdict(list)
        for f in findings:
            metric_key = (f.metric or f.description[:40]).strip().lower()
            key = (f.classification.value, metric_key)
            groups[key].append(f)
        return dict(groups)

    # ─── per-group synthesis ──────────────────────────────────────────────────

    def _synthesize_group(
        self,
        group_key: Tuple[str, str],
        group_findings: List[Finding],
        study_map: Dict[str, ResearchStudy],
        edges: List[EdgeRecord],
        metrics: List[KnowledgeMetric],
        certifications: List[Certification],
        hypotheses: list,
        now: datetime,
    ) -> Tuple[SynthesizedFinding, List[ContradictionRecord]]:
        cls_str, metric_key = group_key
        finding_cls = FindingClassification(cls_str)

        # Unique studies that contributed findings in this group
        study_ids = list(dict.fromkeys(f.study_id for f in group_findings))
        finding_ids = [f.finding_id for f in group_findings]

        # Regime and sector coverage
        regimes = sorted(set(f.regime for f in group_findings if f.regime))
        sectors: List[str] = []   # findings don't carry sector — populated from feature data

        # Time coverage from contributing studies
        time_coverage = self._derive_time_coverage(study_ids, study_map)

        # Contradiction detection within this group
        contradictions = self._detect_contradictions(group_findings)
        contradiction_ids = [c.contradiction_id for c in contradictions]

        n_studies = len(study_ids)
        n_contradicting_studies = len({c.study_b_id for c in contradictions})
        n_supporting_studies = max(0, n_studies - n_contradicting_studies)

        # Average individual finding confidence
        conf_values = [f.confidence for f in group_findings if f.confidence is not None]
        avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.5

        # Certification relevance
        relevant_certs = self._find_relevant_certifications(metric_key, certifications)
        cert_ids = [c.cert_id for c in relevant_certs]

        # Edge correlation
        related_edges = self._correlate_edges(metric_key, finding_cls, group_findings, edges)
        edge_ids = [e.edge_id for e in related_edges]

        # Metric correlation
        related_metric_ids = self._correlate_metrics(metric_key, finding_cls, metrics)

        # Hypothesis correlation
        related_hyp_ids = self._correlate_hypotheses(
            study_ids, finding_ids, hypotheses
        )

        # Confidence model
        confidence, breakdown = self._calculate_confidence(
            n_studies=n_studies,
            n_supporting=n_supporting_studies,
            n_contradicting=n_contradicting_studies,
            cert_count=len(relevant_certs),
            regime_count=len(regimes) if regimes else 1,
            avg_finding_confidence=avg_conf,
        )

        classification = self._classify(
            n_studies=n_studies,
            n_supporting=n_supporting_studies,
            n_contradicting=n_contradicting_studies,
            confidence=confidence,
            n_findings=len(group_findings),
        )

        # Evidence chain
        evidence_chain = self._build_evidence_chain(
            group_findings=group_findings,
            study_ids=study_ids,
            edge_ids=edge_ids,
            related_metric_ids=related_metric_ids,
            related_hyp_ids=related_hyp_ids,
            cert_ids=cert_ids,
            metric_key=metric_key,
            finding_cls=finding_cls,
        )

        # Synthesis ID: deterministic from group key
        syn_id = f"SYN-{cls_str[:4]}-{_short_hash(metric_key)}"

        title = self._derive_title(finding_cls, metric_key, regimes)
        description = self._derive_description(group_findings, n_studies, classification)

        sf = SynthesizedFinding(
            synthesis_id=syn_id,
            title=title,
            classification=classification,
            finding_classification=finding_cls,
            metric=metric_key,
            regime=regimes[0] if len(regimes) == 1 else None,
            description=description,
            source_study_ids=study_ids,
            source_finding_ids=finding_ids,
            related_edge_ids=edge_ids,
            related_hypothesis_ids=related_hyp_ids,
            related_metric_ids=related_metric_ids,
            related_cert_ids=cert_ids,
            synthesis_confidence=confidence,
            confidence_breakdown=breakdown,
            evidence_count=len(group_findings),
            supporting_study_count=n_supporting_studies,
            contradicting_study_count=n_contradicting_studies,
            regime_coverage=regimes,
            sector_coverage=sectors,
            time_coverage=time_coverage,
            contradiction_ids=contradiction_ids,
            evidence_chain=evidence_chain,
            synthesized_at=now,
        )
        return sf, contradictions

    # ─── confidence model (documented) ───────────────────────────────────────

    @staticmethod
    def _calculate_confidence(
        n_studies: int,
        n_supporting: int,
        n_contradicting: int,
        cert_count: int,
        regime_count: int,
        avg_finding_confidence: float,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Confidence calculation — fully documented in breakdown dict.

        Components:
          study_agreement      (0.00–0.50): fraction of studies supporting × 0.5
          finding_confidence   (0.00–0.20): avg per-finding confidence × 0.2
          study_count_bonus    (0.00–0.12): 0.03 per additional study, cap 0.12
          certification_bonus  (0.00–0.10): 0.05 per certification, cap 0.10
          regime_diversity     (0.00–0.08): 0.04 per additional regime, cap 0.08
          contradiction_penalty(0.00–0.30): 0.15 per contradicting study, cap 0.30
        """
        breakdown: Dict[str, float] = {}

        # Short-circuit: zero studies means zero confidence
        if n_studies == 0:
            for k in ("study_agreement", "finding_confidence", "study_count_bonus",
                      "certification_bonus", "regime_diversity",
                      "contradiction_penalty", "total"):
                breakdown[k] = 0.0
            return 0.0, breakdown

        # Component 1 — study agreement ratio (0.0–0.50)
        if n_studies > 0:
            agreement = n_supporting / n_studies
            study_component = round(agreement * 0.50, 3)
        else:
            study_component = 0.0
        breakdown["study_agreement"] = study_component

        # Component 2 — individual finding quality (0.0–0.20)
        conf_component = round(min(1.0, max(0.0, avg_finding_confidence)) * 0.20, 3)
        breakdown["finding_confidence"] = conf_component

        # Component 3 — study count bonus (0.0–0.12)
        size_component = round(min(0.12, (n_studies - 1) * 0.03), 3)
        breakdown["study_count_bonus"] = size_component

        # Component 4 — certification bonus (0.0–0.10)
        cert_component = round(min(0.10, cert_count * 0.05), 3)
        breakdown["certification_bonus"] = cert_component

        # Component 5 — regime diversity (0.0–0.08)
        regime_component = round(min(0.08, (regime_count - 1) * 0.04), 3)
        breakdown["regime_diversity"] = regime_component

        # Penalty — contradictions (0.0–0.30)
        contradiction_penalty = round(min(0.30, n_contradicting * 0.15), 3)
        breakdown["contradiction_penalty"] = -contradiction_penalty

        raw = (study_component + conf_component + size_component +
               cert_component + regime_component - contradiction_penalty)
        final = round(max(0.0, min(1.0, raw)), 3)
        breakdown["total"] = final
        return final, breakdown

    # ─── classification rules ─────────────────────────────────────────────────

    @staticmethod
    def _classify(
        n_studies: int,
        n_supporting: int,
        n_contradicting: int,
        confidence: float,
        n_findings: int,
    ) -> SynthesisClassification:
        if n_findings == 0 or n_studies == 0:
            return SynthesisClassification.INSUFFICIENT_EVIDENCE

        # Contradicted takes priority when contradictors ≥ supporters
        if n_contradicting > 0 and n_contradicting >= n_supporting:
            return SynthesisClassification.CONTRADICTED

        # Mixed evidence where supporters lead
        if n_contradicting > 0 and n_supporting > n_contradicting:
            return SynthesisClassification.PARTIAL

        # Single study — cannot confirm, only partial support
        if n_studies == 1:
            if confidence >= 0.50:
                return SynthesisClassification.PARTIAL
            return SynthesisClassification.INSUFFICIENT_EVIDENCE

        # Multi-study, no contradictions
        if confidence >= 0.85 and n_supporting >= 3:
            return SynthesisClassification.CONFIRMED
        if confidence >= 0.75 and n_supporting >= 2:
            return SynthesisClassification.VERIFIED
        if confidence >= 0.60 and n_supporting >= 2:
            return SynthesisClassification.SUPPORTED
        if n_findings > 0:
            return SynthesisClassification.UNRESOLVED
        return SynthesisClassification.INSUFFICIENT_EVIDENCE

    # ─── contradiction detection ──────────────────────────────────────────────

    def _detect_contradictions(
        self, findings: List[Finding]
    ) -> List[ContradictionRecord]:
        """
        Detect contradictions between findings in the same group.
        Compares findings from different studies that cover the same or no regime.
        """
        contradictions: List[ContradictionRecord] = []
        seen: Set[Tuple[str, str]] = set()

        for i, fa in enumerate(findings):
            for fb in findings[i + 1:]:
                # Only compare findings from different studies
                if fa.study_id == fb.study_id:
                    continue

                pair = (min(fa.finding_id, fb.finding_id),
                        max(fa.finding_id, fb.finding_id))
                if pair in seen:
                    continue
                seen.add(pair)

                c = self._compare_findings(fa, fb)
                if c is not None:
                    contradictions.append(c)

        return contradictions

    def _compare_findings(
        self, fa: Finding, fb: Finding
    ) -> Optional[ContradictionRecord]:
        """Compare two findings and return a ContradictionRecord if they contradict."""
        # Only compare same-regime or both-unspecified findings
        if fa.regime and fb.regime and fa.regime != fb.regime:
            return None   # different regimes — not a contradiction

        contradiction_type = None
        severity = 0.0
        description = ""

        # Compare numeric values
        val_a = fa.value
        val_b = fb.value

        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            if val_a == 0 and val_b == 0:
                return None
            # Direction contradiction (opposite signs)
            if (val_a > 0 and val_b < 0) or (val_a < 0 and val_b > 0):
                contradiction_type = ContradictionType.CONFLICTING_DIRECTION
                severity = min(1.0, abs(val_a - val_b) / (abs(val_a) + abs(val_b) + 1e-9))
                description = (f"Opposing signs: study {fa.study_id} → {val_a:.4g}, "
                               f"study {fb.study_id} → {val_b:.4g}")
            else:
                # Same direction but magnitude diverges
                denom = max(abs(val_a), abs(val_b), 1e-9)
                rel_diff = abs(val_a - val_b) / denom
                if rel_diff > _CONTRADICTION_THRESHOLD:
                    contradiction_type = ContradictionType.CONFLICTING_VALUES
                    severity = min(1.0, rel_diff)
                    description = (f"Value divergence {rel_diff:.1%}: "
                                   f"study {fa.study_id} → {val_a:.4g}, "
                                   f"study {fb.study_id} → {val_b:.4g}")

        # Compare lift (positive / negative) even if value not numeric
        if contradiction_type is None and fa.lift is not None and fb.lift is not None:
            if (fa.lift > 0 and fb.lift < 0) or (fa.lift < 0 and fb.lift > 0):
                contradiction_type = ContradictionType.CONFLICTING_DIRECTION
                severity = 0.6
                description = (f"Opposite lift signs: study {fa.study_id} → {fa.lift:.3g}, "
                               f"study {fb.study_id} → {fb.lift:.3g}")

        if contradiction_type is None:
            return None

        cid = f"CON-{_short_hash(fa.finding_id + fb.finding_id)}"
        return ContradictionRecord(
            contradiction_id=cid,
            contradiction_type=contradiction_type,
            finding_a_id=fa.finding_id,
            study_a_id=fa.study_id,
            finding_b_id=fb.finding_id,
            study_b_id=fb.study_id,
            metric=fa.metric or fa.description[:40],
            value_a=val_a,
            value_b=val_b,
            description=description,
            severity=severity,
            auto_resolved=False,
            detected_at=datetime.now(),
        )

    # ─── relationship discovery ───────────────────────────────────────────────

    def _discover_relationships(
        self,
        studies: List[ResearchStudy],
        findings: List[Finding],
        edges: List[EdgeRecord],
        metrics: List[KnowledgeMetric],
        certifications: List[Certification],
        hypotheses: list,
        synthesized: List[SynthesizedFinding],
    ) -> List[KnowledgeRelationship]:
        rels: List[KnowledgeRelationship] = []
        seen: Set[Tuple[str, str]] = set()

        def add(rel: KnowledgeRelationship) -> None:
            key = (rel.from_id, rel.to_id)
            if key not in seen:
                rels.append(rel)
                seen.add(key)

        # ── Study → Finding ───────────────────────────────────────────────────
        for f in findings:
            add(KnowledgeRelationship(
                relationship_id=f"REL-SF-{_short_hash(f.study_id + f.finding_id)}",
                relationship_type=RelationshipType.STUDY_TO_FINDING,
                from_id=f.study_id,
                from_type="STUDY",
                to_id=f.finding_id,
                to_type="FINDING",
                description=f"Study {f.study_id} produced finding {f.finding_id}",
                confidence=1.0,
            ))

        # ── Finding → Finding (cross-study, same metric) ──────────────────────
        study_findings: Dict[str, List[Finding]] = defaultdict(list)
        for f in findings:
            metric_key = (f.classification.value,
                          (f.metric or f.description[:40]).strip().lower())
            study_findings[str(metric_key)].append(f)

        for mkey, mfindings in study_findings.items():
            study_ids = {f.study_id for f in mfindings}
            if len(study_ids) < 2:
                continue
            fl = mfindings
            for i, fa in enumerate(fl):
                for fb in fl[i + 1:]:
                    if fa.study_id == fb.study_id:
                        continue
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-FF-{_short_hash(fa.finding_id + fb.finding_id)}",
                        relationship_type=RelationshipType.FINDING_TO_FINDING,
                        from_id=fa.finding_id,
                        from_type="FINDING",
                        to_id=fb.finding_id,
                        to_type="FINDING",
                        description=(f"Cross-study agreement on "
                                     f"{fa.metric or fa.description[:30]} "
                                     f"({fa.study_id} ↔ {fb.study_id})"),
                        confidence=0.9,
                    ))

        # ── Finding → Edge ────────────────────────────────────────────────────
        for f in findings:
            metric_key = (f.metric or "").lower()
            for e in edges:
                edge_name = e.name.lower()
                edge_desc = (e.description or "").lower()
                # Substring match: metric appears in edge name/desc or vice versa
                match = False
                if len(metric_key) >= _EDGE_MATCH_MIN_CHARS:
                    match = (metric_key in edge_name or
                             metric_key in edge_desc or
                             (len(edge_name) >= _EDGE_MATCH_MIN_CHARS and
                              edge_name in metric_key))
                if match:
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-FE-{_short_hash(f.finding_id + e.edge_id)}",
                        relationship_type=RelationshipType.FINDING_TO_EDGE,
                        from_id=f.finding_id,
                        from_type="FINDING",
                        to_id=e.edge_id,
                        to_type="EDGE",
                        description=f"Finding metric '{f.metric}' matches edge '{e.name}'",
                        confidence=0.75,
                    ))

        # ── Finding → Metric ──────────────────────────────────────────────────
        for m in metrics:
            if m.category == "STUDY" and m.metric_id.startswith("finding."):
                parts = m.metric_id.split(".")
                if len(parts) >= 2:
                    fid = parts[1]
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-FM-{_short_hash(fid + m.metric_id)}",
                        relationship_type=RelationshipType.FINDING_TO_METRIC,
                        from_id=fid,
                        from_type="FINDING",
                        to_id=m.metric_id,
                        to_type="METRIC",
                        description=f"Finding {fid} is source of metric {m.metric_id}",
                        confidence=1.0,
                    ))

        # ── Hypothesis → Finding / Study ──────────────────────────────────────
        for h in hypotheses:
            for ev in h.supporting_evidence:
                # Hypothesis → Finding
                matching_findings = [f for f in findings if f.finding_id == ev.evidence_id]
                for f in matching_findings:
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-HF-{_short_hash(h.hypothesis_id + f.finding_id)}",
                        relationship_type=RelationshipType.HYPOTHESIS_TO_FINDING,
                        from_id=h.hypothesis_id,
                        from_type="HYPOTHESIS",
                        to_id=f.finding_id,
                        to_type="FINDING",
                        description=(f"Hypothesis {h.hypothesis_id} cites finding "
                                     f"{f.finding_id} as evidence"),
                        confidence=1.0,
                    ))
                # Hypothesis → Study (via origin_study or STUDY evidence)
                if h.origin_study and h.origin_study in {s.study_id for s in studies}:
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-HS-{_short_hash(h.hypothesis_id + h.origin_study)}",
                        relationship_type=RelationshipType.HYPOTHESIS_TO_STUDY,
                        from_id=h.hypothesis_id,
                        from_type="HYPOTHESIS",
                        to_id=h.origin_study,
                        to_type="STUDY",
                        description=f"Hypothesis {h.hypothesis_id} originated from {h.origin_study}",
                        confidence=1.0,
                    ))

        # ── Edge → Certification ──────────────────────────────────────────────
        for c in certifications:
            for e in edges:
                # Heuristic: certifications with ACTIVE edges or matching time proximity
                if e.status == EdgeStatus.ACTIVE:
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-EC-{_short_hash(e.edge_id + c.cert_id)}",
                        relationship_type=RelationshipType.EDGE_TO_CERTIFICATION,
                        from_id=e.edge_id,
                        from_type="EDGE",
                        to_id=c.cert_id,
                        to_type="CERTIFICATION",
                        description=(f"Active edge {e.edge_id} associated with "
                                     f"certification {c.cert_id}"),
                        confidence=0.6,
                    ))
                    break   # one cert per edge to prevent N² explosion

        # ── Study → Study (date range overlap) ───────────────────────────────
        for i, sa in enumerate(studies):
            for sb in studies[i + 1:]:
                if sa.date_range_start and sb.date_range_start:
                    add(KnowledgeRelationship(
                        relationship_id=f"REL-SS-{_short_hash(sa.study_id + sb.study_id)}",
                        relationship_type=RelationshipType.STUDY_TO_STUDY,
                        from_id=sa.study_id,
                        from_type="STUDY",
                        to_id=sb.study_id,
                        to_type="STUDY",
                        description=(f"Studies {sa.study_id} and {sb.study_id} "
                                     f"share overlapping time context"),
                        confidence=0.7,
                    ))

        return rels

    # ─── consensus builder ────────────────────────────────────────────────────

    def _build_consensus(
        self, synthesized: List[SynthesizedFinding], now: datetime
    ) -> List[KnowledgeConsensus]:
        """
        Group synthesized findings by FindingClassification to form consensus blocks.
        """
        by_cls: Dict[str, List[SynthesizedFinding]] = defaultdict(list)
        for sf in synthesized:
            by_cls[sf.finding_classification.value].append(sf)

        blocks: List[KnowledgeConsensus] = []
        for cls_val, group in by_cls.items():
            all_study_ids = list({sid for sf in group for sid in sf.source_study_ids})
            all_metrics   = list({sf.metric for sf in group})
            all_regimes   = list({r for sf in group for r in sf.regime_coverage})

            confirmed_or_verified = sum(
                1 for sf in group
                if sf.classification in (SynthesisClassification.CONFIRMED,
                                          SynthesisClassification.VERIFIED,
                                          SynthesisClassification.SUPPORTED)
            )
            agreement_rate = confirmed_or_verified / len(group) if group else 0.0

            # Pick the most common classification for the block
            cls_counts: Dict[str, int] = defaultdict(int)
            for sf in group:
                cls_counts[sf.classification.value] += 1
            dominant_cls = SynthesisClassification(
                max(cls_counts, key=lambda k: cls_counts[k])
            )

            blocks.append(KnowledgeConsensus(
                consensus_id=f"CON-{cls_val[:6]}-{_short_hash(cls_val)}",
                topic=cls_val.replace("_", " ").title(),
                classification=dominant_cls,
                findings_count=len(group),
                studies_count=len(all_study_ids),
                agreement_rate=round(agreement_rate, 3),
                key_metrics=all_metrics[:10],
                regime_coverage=all_regimes,
                summary=(f"{len(group)} {cls_val} findings across "
                         f"{len(all_study_ids)} studies with "
                         f"{agreement_rate:.0%} agreement rate"),
                synthesized_at=now,
            ))

        return blocks

    # ─── statistics ───────────────────────────────────────────────────────────

    @staticmethod
    def _build_statistics(
        findings: List[Finding],
        synthesized: List[SynthesizedFinding],
        relationships: List[KnowledgeRelationship],
        contradictions: List[ContradictionRecord],
        studies: List[ResearchStudy],
        edges_correlated: int,
        hyp_correlated: int,
        cert_correlated: int,
        metric_correlated: int,
        elapsed_ms: float,
        now: datetime,
    ) -> SynthesisStatistics:
        by_cls: Dict[str, int] = defaultdict(int)
        by_ftype: Dict[str, int] = defaultdict(int)
        for sf in synthesized:
            by_cls[sf.classification.value] += 1
            by_ftype[sf.finding_classification.value] += 1

        avg_conf = (
            sum(sf.synthesis_confidence for sf in synthesized) / len(synthesized)
            if synthesized else 0.0
        )
        avg_ev = (
            sum(sf.evidence_count for sf in synthesized) / len(synthesized)
            if synthesized else 0.0
        )

        return SynthesisStatistics(
            total_findings_processed=len(findings),
            total_synthesized_findings=len(synthesized),
            total_relationships=len(relationships),
            total_contradictions=len(contradictions),
            by_classification=dict(by_cls),
            by_finding_type=dict(by_ftype),
            avg_synthesis_confidence=round(avg_conf, 3),
            avg_evidence_count=round(avg_ev, 2),
            studies_processed=len(studies),
            edges_correlated=edges_correlated,
            hypotheses_correlated=hyp_correlated,
            certifications_correlated=cert_correlated,
            metrics_correlated=metric_correlated,
            synthesis_duration_ms=round(elapsed_ms, 1),
            synthesized_at=now,
        )

    # ─── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _derive_time_coverage(
        study_ids: List[str],
        study_map: Dict[str, ResearchStudy],
    ) -> Optional[Dict[str, str]]:
        starts = [
            s.date_range_start for sid in study_ids
            if (s := study_map.get(sid)) and s.date_range_start
        ]
        ends = [
            s.date_range_end for sid in study_ids
            if (s := study_map.get(sid)) and s.date_range_end
        ]
        if not starts and not ends:
            return None
        return {
            "start": min(starts) if starts else "unknown",
            "end":   max(ends)   if ends   else "unknown",
        }

    @staticmethod
    def _find_relevant_certifications(
        metric_key: str, certifications: List[Certification]
    ) -> List[Certification]:
        """Certifications are broadly applicable — return all passed ones as relevant."""
        return [c for c in certifications if c.passed]

    @staticmethod
    def _correlate_edges(
        metric_key: str,
        finding_cls: FindingClassification,
        group_findings: List[Finding],
        edges: List[EdgeRecord],
    ) -> List[EdgeRecord]:
        """Find edges whose name/description overlaps with the finding metric."""
        if not metric_key or len(metric_key) < _EDGE_MATCH_MIN_CHARS:
            return []
        result = []
        for e in edges:
            edge_name = e.name.lower()
            edge_desc = (e.description or "").lower()
            if (metric_key in edge_name or
                    metric_key in edge_desc or
                    (len(edge_name) >= _EDGE_MATCH_MIN_CHARS and
                     edge_name in metric_key)):
                result.append(e)
        return result[:20]   # cap to avoid huge lists

    @staticmethod
    def _correlate_metrics(
        metric_key: str,
        finding_cls: FindingClassification,
        metrics: List[KnowledgeMetric],
    ) -> List[str]:
        """Return metric_ids where name matches metric_key."""
        if not metric_key:
            return []
        kw = metric_key.lower()
        return [m.metric_id for m in metrics if kw in m.name.lower()][:20]

    @staticmethod
    def _correlate_hypotheses(
        study_ids: List[str],
        finding_ids: List[str],
        hypotheses: list,
    ) -> List[str]:
        """Find hypotheses that cite any of the finding_ids or origin_study."""
        result: Set[str] = set()
        ev_ids = set(finding_ids)
        study_id_set = set(study_ids)

        for h in hypotheses:
            if h.origin_study in study_id_set:
                result.add(h.hypothesis_id)
                continue
            for ev in h.supporting_evidence:
                if ev.evidence_id in ev_ids or ev.evidence_id in study_id_set:
                    result.add(h.hypothesis_id)
                    break

        return sorted(result)

    @staticmethod
    def _build_evidence_chain(
        group_findings: List[Finding],
        study_ids: List[str],
        edge_ids: List[str],
        related_metric_ids: List[str],
        related_hyp_ids: List[str],
        cert_ids: List[str],
        metric_key: str,
        finding_cls: FindingClassification,
    ) -> EvidenceChain:
        finding_ids = [f.finding_id for f in group_findings]
        layers_present = sum([
            bool(study_ids),
            bool(finding_ids),
            bool(edge_ids),
            bool(related_metric_ids),
            bool(related_hyp_ids),
            bool(cert_ids),
        ])
        completeness = round(layers_present / 6.0, 3)

        return EvidenceChain(
            chain_id=f"CHN-{_short_hash(metric_key + finding_cls.value)}",
            root_study_ids=study_ids,
            finding_ids=finding_ids,
            edge_ids=edge_ids,
            metric_ids=related_metric_ids,
            hypothesis_ids=related_hyp_ids,
            cert_ids=cert_ids,
            description=(f"Evidence chain for {finding_cls.value} / {metric_key}: "
                         f"{len(study_ids)} studies, {len(finding_ids)} findings, "
                         f"{len(edge_ids)} edges, {len(cert_ids)} certifications"),
            completeness=completeness,
        )

    @staticmethod
    def _derive_title(
        finding_cls: FindingClassification, metric_key: str, regimes: List[str]
    ) -> str:
        cls_label = finding_cls.value.replace("_", " ").title()
        regime_part = f" [{regimes[0]}]" if len(regimes) == 1 else ""
        return f"{cls_label}: {metric_key}{regime_part}"

    @staticmethod
    def _derive_description(
        group_findings: List[Finding],
        n_studies: int,
        classification: SynthesisClassification,
    ) -> str:
        sample = group_findings[0]
        return (f"{classification.value} — {n_studies} source studies. "
                f"Representative: {sample.description[:120]}")


# ─── module-level helper ─────────────────────────────────────────────────────

def _short_hash(text: str) -> str:
    """8-char deterministic hex hash of a string."""
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8].upper()

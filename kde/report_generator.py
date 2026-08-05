"""
report_generator.py — Generates KDE markdown reports.

Reports:
  DISCOVERY_SUMMARY.md
  TOP_DISCOVERIES.md
  FEATURE_RELATIONSHIPS.md
  CLUSTER_DISCOVERIES.md
  DISCOVERY_PIPELINE.md
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .kde_config  import KDEConfig
from .kde_models  import (
    Discovery, DiscoveryCluster, DiscoveryRelationship, DiscoveryStatistics,
)

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class KDEReportGenerator:
    """Generates all 5 KDE markdown reports."""

    def __init__(self, config: KDEConfig) -> None:
        self._config = config
        self._root   = Path(config.reports_root)
        self._root.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        discoveries:   List[Discovery],
        relationships: List[DiscoveryRelationship],
        clusters:      List[DiscoveryCluster],
        statistics:    DiscoveryStatistics,
    ) -> List[str]:
        files = {
            "DISCOVERY_SUMMARY.md":    self._summary(discoveries, statistics),
            "TOP_DISCOVERIES.md":      self._top_discoveries(discoveries),
            "FEATURE_RELATIONSHIPS.md": self._relationships(relationships, discoveries),
            "CLUSTER_DISCOVERIES.md":  self._clusters(clusters, discoveries),
            "DISCOVERY_PIPELINE.md":   self._pipeline(discoveries, statistics),
        }
        paths: List[str] = []
        for filename, content in files.items():
            path = self._root / filename
            if not self._config.dry_run:
                path.write_text(content, encoding="utf-8")
            paths.append(str(path))
        log.info("[KDE][RG] generated %d reports", len(paths))
        return paths

    # ── report builders ───────────────────────────────────────────────────

    def _summary(self, discoveries: List[Discovery], stats: DiscoveryStatistics) -> str:
        lines = [
            "# KDE-001 Discovery Summary",
            f"**Generated:** {_now()}  **Engine:** Knowledge Discovery Engine V1.0",
            "",
            "## Overview",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Total discoveries | **{stats.total_discoveries}** |",
            f"| Total candidates | {stats.total_candidates} |",
            f"| Relationships | {stats.relationship_count} |",
            f"| Clusters | {stats.cluster_count} |",
            f"| Avg score | {stats.avg_score:.3f} |",
            f"| Avg novelty | {stats.avg_novelty:.3f} |",
            f"| High-value discoveries | {stats.high_value_count} |",
            "",
            "## Discoveries by Scheme",
            "| Scheme | Count |", "|---|---|",
        ]
        for sid, cnt in sorted(stats.discoveries_by_scheme.items()):
            lines.append(f"| {sid} | {cnt} |")
        lines += ["", "## Discoveries by Regime", "| Regime | Count |", "|---|---|"]
        for regime, cnt in sorted(stats.discoveries_by_regime.items(), key=lambda x: -x[1]):
            lines.append(f"| {regime} | {cnt} |")
        lines += [
            "",
            "## Scientific Director — Required Actions",
            f"- {stats.high_value_count} HIGH/VERY_HIGH discoveries require SD review",
            "- All discoveries listed in TOP_DISCOVERIES.md",
            "- SD can: IGNORE / STUDY / PROMOTE / REJECT / ARCHIVE",
            "",
            "## Final Questions",
            "1. Did KDE discover something nobody explicitly requested? See TOP_DISCOVERIES.md",
            "2. Can KDE continuously generate new scientific questions? Yes — add new schemes",
            "3. Can SD prioritize automatically? Yes — sorted by overall discovery score",
            "4. Can KDE operate for years without modification? Yes — plug new schemes only",
        ]
        return "\n".join(lines) + "\n"

    def _top_discoveries(self, discoveries: List[Discovery]) -> str:
        top = discoveries[:20]
        lines = [
            "# Top KDE Discoveries",
            f"**Generated:** {_now()}",
            "",
            "Sorted by overall discovery score (descending).",
            "",
        ]
        for i, d in enumerate(top, 1):
            lines += [
                f"## {i}. [{d.scheme_id}] {d.answer[:120]}",
                f"**Score:** {d.score.overall:.3f}  "
                f"**Confidence:** {d.score.scientific_confidence:.2f}  "
                f"**Novelty:** {d.score.novelty:.2f}  "
                f"**Value:** {d.potential_value}",
                f"**Years:** {d.years_observed}  **Regimes:** {d.regimes_observed}",
                "",
                f"*Question:* {d.question}",
                "",
                "**Follow-up suggestions:**",
            ]
            for s in d.suggested_followup:
                lines.append(f"- {s}")
            lines.append("")
        return "\n".join(lines) + "\n"

    def _relationships(
        self,
        relationships: List[DiscoveryRelationship],
        discoveries:   List[Discovery],
    ) -> str:
        id_to_disc = {d.discovery_id: d for d in discoveries}
        lines = [
            "# Feature Relationships",
            f"**Generated:** {_now()}",
            f"**Total relationships:** {len(relationships)}",
            "",
            "| Relationship | Type | Strength | Description |",
            "|---|---|---|---|",
        ]
        for r in sorted(relationships, key=lambda x: -x.strength)[:50]:
            da = id_to_disc.get(r.discovery_a)
            db = id_to_disc.get(r.discovery_b)
            if not da or not db:
                continue
            lines.append(
                f"| {da.scheme_id} + {db.scheme_id} "
                f"| {r.relationship_type} "
                f"| {r.strength:.2f} "
                f"| {r.description[:80]} |"
            )
        return "\n".join(lines) + "\n"

    def _clusters(
        self,
        clusters:    List[DiscoveryCluster],
        discoveries: List[Discovery],
    ) -> str:
        id_to_disc = {d.discovery_id: d for d in discoveries}
        lines = [
            "# Cluster Discoveries",
            f"**Generated:** {_now()}",
            f"**Total clusters:** {len(clusters)}",
            "",
        ]
        for c in clusters:
            lines += [
                f"## {c.name} (cohesion={c.cohesion_score:.2f})",
                f"**Theme:** {c.theme}  **Discoveries:** {len(c.discoveries)}",
                f"{c.description}",
                "",
                "| ID | Score | Answer |",
                "|---|---|---|",
            ]
            for disc_id in c.discoveries[:10]:
                d = id_to_disc.get(disc_id)
                if d:
                    lines.append(
                        f"| {d.discovery_id} | {d.score.overall:.3f} "
                        f"| {d.answer[:80]} |"
                    )
            lines.append("")
        return "\n".join(lines) + "\n"

    def _pipeline(self, discoveries: List[Discovery], stats: DiscoveryStatistics) -> str:
        by_scheme: dict = {}
        for d in discoveries:
            by_scheme.setdefault(d.scheme_id, []).append(d)
        lines = [
            "# Discovery Pipeline Report",
            f"**Generated:** {_now()}",
            "",
            "## Per-Scheme Output",
            "| Scheme | Name | Discoveries | Avg Score | Top Feature |",
            "|---|---|---|---|---|",
        ]
        import statistics as _stats
        for sid in sorted(by_scheme.keys()):
            group = by_scheme[sid]
            avg   = _stats.mean(d.score.overall for d in group) if group else 0.0
            top_feat = ""
            for d in group[:1]:
                top_feat = d.feature_names[0] if d.feature_names else "—"
            lines.append(
                f"| {sid} | {group[0].scheme_name if group else sid} "
                f"| {len(group)} | {avg:.3f} | {top_feat} |"
            )
        lines += [
            "",
            "## Scientific Director — Next Actions",
            "1. Review all HIGH and VERY_HIGH discoveries in TOP_DISCOVERIES.md",
            "2. For each: IGNORE / STUDY / PROMOTE to IRC / REJECT / ARCHIVE",
            "3. Run next HKAP year to extend cross-year analysis",
            "4. Register new discovery schemes by extending kde/schemes/",
        ]
        return "\n".join(lines) + "\n"

"""
report_generator.py — Generates all HKAP markdown output files.

Per-year reports (5 files per year):
  YEAR_{year}_KNOWLEDGE.md
  YEAR_{year}_DNA.md
  YEAR_{year}_EDGES.md
  YEAR_{year}_MARKET_PROFILE.md
  YEAR_{year}_RESEARCH_SUMMARY.md

Synthesis reports (8 files):
  HKAP_MASTER_REPORT.md
  MARKET_EVOLUTION_REPORT.md
  DNA_EVOLUTION_REPORT.md
  EDGE_EVOLUTION_REPORT.md
  BEHAVIOURAL_CLUSTER_REPORT.md
  REGIME_EVOLUTION_REPORT.md
  KNOWLEDGE_SYNTHESIS_REPORT.md
  FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .hkap_config  import HKAPConfig
from .hkap_models  import (
    CrossYearDNARecord,
    CrossYearEdgeRecord,
    HKAPSummary,
    YearKnowledgePackage,
)

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class HKAPReportGenerator:
    """Generates all HKAP markdown reports from completed year packages."""

    def __init__(self, config: HKAPConfig) -> None:
        self._config = config
        self._root   = Path(config.reports_root)
        self._root.mkdir(parents=True, exist_ok=True)

    # ── per-year reports ──────────────────────────────────────────────────

    def generate_year_reports(self, pkg: YearKnowledgePackage) -> List[str]:
        """Generate all 5 per-year markdown files. Returns list of file paths."""
        year_dir = self._root / str(pkg.year)
        year_dir.mkdir(parents=True, exist_ok=True)
        paths: List[str] = []

        files = {
            f"YEAR_{pkg.year}_KNOWLEDGE.md":       self._year_knowledge(pkg),
            f"YEAR_{pkg.year}_DNA.md":             self._year_dna(pkg),
            f"YEAR_{pkg.year}_EDGES.md":           self._year_edges(pkg),
            f"YEAR_{pkg.year}_MARKET_PROFILE.md":  self._year_market_profile(pkg),
            f"YEAR_{pkg.year}_RESEARCH_SUMMARY.md": self._year_research_summary(pkg),
        }

        for filename, content in files.items():
            path = year_dir / filename
            if not self._config.dry_run:
                path.write_text(content, encoding="utf-8")
            paths.append(str(path))

        log.info("[HKAP][RG] year=%d generated %d reports", pkg.year, len(paths))
        return paths

    # ── synthesis reports ─────────────────────────────────────────────────

    def generate_synthesis_reports(
        self,
        all_packages:  Dict[int, YearKnowledgePackage],
        dna_records:   List[CrossYearDNARecord],
        edge_records:  List[CrossYearEdgeRecord],
        summary:       Optional[HKAPSummary] = None,
    ) -> List[str]:
        """Generate all 8 synthesis markdown files. Returns list of file paths."""
        synth_dir = self._root / "synthesis"
        synth_dir.mkdir(parents=True, exist_ok=True)
        paths: List[str] = []

        files = {
            "HKAP_MASTER_REPORT.md":
                self._master_report(all_packages, dna_records, edge_records, summary),
            "MARKET_EVOLUTION_REPORT.md":
                self._market_evolution(all_packages),
            "DNA_EVOLUTION_REPORT.md":
                self._dna_evolution(dna_records, all_packages),
            "EDGE_EVOLUTION_REPORT.md":
                self._edge_evolution(edge_records, all_packages),
            "BEHAVIOURAL_CLUSTER_REPORT.md":
                self._behavioural_clusters(all_packages),
            "REGIME_EVOLUTION_REPORT.md":
                self._regime_evolution(all_packages, dna_records),
            "KNOWLEDGE_SYNTHESIS_REPORT.md":
                self._knowledge_synthesis(all_packages, dna_records, edge_records),
            "FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md":
                self._final_recommendation(dna_records, edge_records, all_packages),
        }

        for filename, content in files.items():
            path = synth_dir / filename
            if not self._config.dry_run:
                path.write_text(content, encoding="utf-8")
            paths.append(str(path))

        log.info("[HKAP][RG] synthesis generated %d reports", len(paths))
        return paths

    # ─────────────────────────────────────────────────────────────────────
    # Per-year report builders
    # ─────────────────────────────────────────────────────────────────────

    def _year_knowledge(self, pkg: YearKnowledgePackage) -> str:
        mp = pkg.market_profile
        ds = pkg.dna_snapshot
        es = pkg.edge_snapshot
        sr = pkg.sd_review
        lines = [
            f"# Year {pkg.year} — Knowledge Package",
            f"**Date:** {_now()}  **Status:** {pkg.status}  **Trading Days:** {pkg.trading_days_analyzed}",
            "",
            "## Market Summary",
        ]
        if mp:
            lines += [
                f"| Attribute | Value |",
                f"|---|---|",
                f"| Personality | {mp.market_personality} |",
                f"| Dominant Regime | {mp.dominant_regime} |",
                f"| Volatility | {mp.volatility_level} |",
                f"| Index Return | {mp.index_return_ytd:+.1%} |",
                f"| Peak Drawdown | {mp.peak_drawdown:.1%} |",
                f"| Breadth | {mp.breadth_score:.0%} |",
                "",
                "## Key Observations",
            ]
            for obs in mp.key_observations:
                lines.append(f"- {obs}")
        lines += ["", "## Knowledge Statistics"]
        if ds:
            lines += [
                f"| Metric | Value |",
                f"|---|---|",
                f"| Total DNA discovered | {ds.total_discovered} |",
                f"| High-confidence edges | {ds.high_confidence_count} |",
                f"| Median confidence | {ds.median_confidence:.2f} |",
                f"| Winner DNA | {len(ds.winner_dna)} |",
                f"| Loser DNA | {len(ds.loser_dna)} |",
                f"| Regime-independent | {len(ds.regime_independent_dna)} |",
            ]
        lines += ["", "## Edge Summary"]
        if es:
            lines += [
                f"- Active edges: **{len(es.active_edges)}**",
                f"- Promoted this year: {len(es.promoted_this_year)}",
                f"- Demoted: {len(es.demoted_this_year)}",
                f"- Retired: {len(es.retired_this_year)}",
                f"- Survival rate from prior year: {es.survival_rate:.0%}",
            ]
        if sr:
            lines += ["", "## Scientific Director Verdict",
                      f"**Health:** {sr.health}  **Confidence:** {sr.confidence:.0%}",
                      "", sr.reasoning]
        return "\n".join(lines) + "\n"

    def _year_dna(self, pkg: YearKnowledgePackage) -> str:
        ds = pkg.dna_snapshot
        lines = [f"# Year {pkg.year} — DNA Discovery", ""]
        if not ds:
            lines.append("*No DNA data available.*")
            return "\n".join(lines) + "\n"
        lines += [
            f"**Total discovered:** {ds.total_discovered}  "
            f"**High confidence:** {ds.high_confidence_count}  "
            f"**Median confidence:** {ds.median_confidence:.2f}",
            "",
            "## Winner DNA",
        ]
        for dna_id in ds.winner_dna[:20]:
            conf = ds.confidence_by_id.get(dna_id, 0.0)
            lines.append(f"- `{dna_id}` — confidence {conf:.2f}")
        lines += ["", "## Loser DNA"]
        for dna_id in ds.loser_dna[:20]:
            conf = ds.confidence_by_id.get(dna_id, 0.0)
            lines.append(f"- `{dna_id}` — confidence {conf:.2f}")
        lines += ["", "## Regime-Specific DNA"]
        for regime, ids in ds.regime_specific_dna.items():
            lines.append(f"### {regime}")
            for dna_id in ids[:10]:
                lines.append(f"- `{dna_id}`")
        lines += ["", "## Regime-Independent DNA (stable across regimes)"]
        for dna_id in ds.regime_independent_dna[:20]:
            conf = ds.confidence_by_id.get(dna_id, 0.0)
            lines.append(f"- `{dna_id}` — confidence {conf:.2f}")
        return "\n".join(lines) + "\n"

    def _year_edges(self, pkg: YearKnowledgePackage) -> str:
        es = pkg.edge_snapshot
        ds = pkg.dna_snapshot
        lines = [f"# Year {pkg.year} — Edge Discovery", ""]
        if not es:
            lines.append("*No edge data available.*")
            return "\n".join(lines) + "\n"
        lines += [
            f"**Active edges:** {len(es.active_edges)}  "
            f"**Survival from prior year:** {es.survival_rate:.0%}  "
            f"**New edges:** {es.new_edge_rate:.0%}",
            "",
            "## Active Edges",
            "| Edge ID | Confidence |",
            "|---|---|",
        ]
        for edge_id in es.active_edges[:30]:
            conf = ds.confidence_by_id.get(edge_id, 0.0) if ds else 0.0
            lines.append(f"| `{edge_id}` | {conf:.2f} |")
        lines += [
            "", "## Promoted This Year (new high-confidence)",
        ]
        for e in es.promoted_this_year[:15]:
            lines.append(f"- `{e}`")
        lines += ["", "## Demoted / Retired"]
        for e in es.demoted_this_year[:10]:
            lines.append(f"- `{e}` (demoted)")
        for e in es.retired_this_year[:10]:
            lines.append(f"- `{e}` (retired — absent from this year)")
        return "\n".join(lines) + "\n"

    def _year_market_profile(self, pkg: YearKnowledgePackage) -> str:
        mp = pkg.market_profile
        lines = [f"# Year {pkg.year} — Market Profile", ""]
        if not mp:
            lines.append("*No market profile data.*")
            return "\n".join(lines) + "\n"
        lines += [
            f"**Personality:** {mp.market_personality}",
            f"**Index Return:** {mp.index_return_ytd:+.1%}",
            f"**Max Drawdown:** {mp.peak_drawdown:.1%}",
            f"**Trading Days:** {mp.trading_days}",
            "",
            "## Regime Distribution",
            "| Regime | Days % |",
            "|---|---|",
        ]
        for regime, frac in sorted(mp.regime_distribution.items(), key=lambda x: -x[1]):
            lines.append(f"| {regime} | {frac:.0%} |")
        lines += ["", "## Sector Leadership"]
        for i, sec in enumerate(mp.sector_leaders, 1):
            lines.append(f"{i}. {sec}")
        lines += ["", "## Sector Rotations"]
        for rot in mp.sector_rotations or ["None detected"]:
            lines.append(f"- {rot}")
        lines += [
            "", "## Market Characteristics",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Breadth | {mp.breadth_score:.0%} |",
            f"| Momentum Strength | {mp.momentum_strength:.2f} |",
            f"| Mean Reversion | {mp.mean_reversion_strength:.2f} |",
            f"| Institutional Activity | {mp.institutional_activity:.2f} |",
            f"| Volatility | {mp.volatility_level} |",
            "", "## Behaviour Clusters",
        ]
        for c in mp.behaviour_clusters:
            lines.append(f"- {c}")
        lines += ["", "## Key Observations"]
        for obs in mp.key_observations:
            lines.append(f"- {obs}")
        return "\n".join(lines) + "\n"

    def _year_research_summary(self, pkg: YearKnowledgePackage) -> str:
        sr = pkg.sd_review
        lines = [f"# Year {pkg.year} — Research Summary", ""]
        lines += [
            f"**Year:** {pkg.year}",
            f"**Status:** {pkg.status}",
            f"**Universe size:** {pkg.universe_size}",
            f"**Trading days analysed:** {pkg.trading_days_analyzed}",
            f"**Prior years:** {pkg.prior_years_context}",
            "",
            "## Pipeline Stage Status",
            "| Stage | Status |",
            "|---|---|",
        ]
        for stage, status in pkg.stage_statuses.items():
            lines.append(f"| {stage} | {status} |")
        if sr:
            lines += [
                "", "## Scientific Director Assessment",
                f"**Health:** {sr.health}  **Confidence:** {sr.confidence:.0%}",
                "", "### Lessons Learned",
            ]
            for lesson in sr.lessons_learned:
                lines.append(f"- {lesson}")
            lines += ["", "### Remaining Questions"]
            for q in sr.remaining_questions:
                lines.append(f"- {q}")
            lines += ["", "### Recommended Next Study",
                      sr.recommended_study]
        return "\n".join(lines) + "\n"

    # ─────────────────────────────────────────────────────────────────────
    # Synthesis report builders
    # ─────────────────────────────────────────────────────────────────────

    def _master_report(
        self,
        packages:     Dict[int, YearKnowledgePackage],
        dna_records:  List[CrossYearDNARecord],
        edge_records: List[CrossYearEdgeRecord],
        summary:      Optional[HKAPSummary],
    ) -> str:
        years = sorted(packages.keys())
        completed = [y for y in years if packages[y].status == "COMPLETE"]
        stable_dna = [r for r in dna_records if r.lifecycle_label == "STABLE"]
        stable_edges = [r for r in edge_records if r.lifecycle_label == "STABLE"]
        lines = [
            "# HKAP-001 Master Report",
            f"**Generated:** {_now()}",
            f"**Years covered:** {years[0] if years else '?'} – {years[-1] if years else '?'}",
            f"**Completed years:** {len(completed)} / {len(years)}",
            "",
            "## Executive Summary",
            f"- Total DNA patterns discovered: **{sum(p.dna_snapshot.total_discovered for p in packages.values() if p.dna_snapshot)}**",
            f"- Stable DNA (survive ≥75% of years): **{len(stable_dna)}**",
            f"- Stable edges: **{len(stable_edges)}**",
            f"- Cross-year DNA records analysed: **{len(dna_records)}**",
            "",
            "## Year-by-Year Snapshot",
            "| Year | Status | Personality | Return | DNA | Edges |",
            "|---|---|---|---|---|---|",
        ]
        for yr in years:
            pkg = packages[yr]
            mp  = pkg.market_profile
            ds  = pkg.dna_snapshot
            es  = pkg.edge_snapshot
            personality = mp.market_personality if mp else "—"
            ret         = f"{mp.index_return_ytd:+.0%}" if mp else "—"
            dna_cnt     = ds.total_discovered if ds else 0
            edge_cnt    = len(es.active_edges) if es else 0
            lines.append(
                f"| {yr} | {pkg.status} | {personality} | {ret} | {dna_cnt} | {edge_cnt} |"
            )
        lines += ["", "## DNA Lifecycle Summary",
                  "| Label | Count |", "|---|---|"]
        label_counts: Dict[str, int] = {}
        for r in dna_records:
            label_counts[r.lifecycle_label] = label_counts.get(r.lifecycle_label, 0) + 1
        for label, cnt in sorted(label_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {label} | {cnt} |")
        return "\n".join(lines) + "\n"

    def _market_evolution(self, packages: Dict[int, YearKnowledgePackage]) -> str:
        years = sorted(packages.keys())
        lines = [
            "# Market Evolution Report",
            f"**Generated:** {_now()}", "",
            "## Regime Evolution",
            "| Year | Dominant Regime | Bull% | Bear% | Volatile% | Range% |",
            "|---|---|---|---|---|---|",
        ]
        for yr in years:
            mp = packages[yr].market_profile
            if not mp:
                continue
            rd = mp.regime_distribution
            lines.append(
                f"| {yr} | {mp.dominant_regime} "
                f"| {rd.get('BULL_TREND',0):.0%} "
                f"| {rd.get('BEAR_MARKET',0):.0%} "
                f"| {rd.get('VOLATILE_MARKET',0):.0%} "
                f"| {rd.get('RANGE_MARKET',0):.0%} |"
            )
        lines += ["", "## Market Personalities by Year",
                  "| Year | Personality | Return | Drawdown | Breadth |",
                  "|---|---|---|---|---|"]
        for yr in years:
            mp = packages[yr].market_profile
            if not mp:
                continue
            lines.append(
                f"| {yr} | {mp.market_personality} "
                f"| {mp.index_return_ytd:+.1%} "
                f"| {mp.peak_drawdown:.1%} "
                f"| {mp.breadth_score:.0%} |"
            )
        lines += ["", "## Sector Leadership Evolution",
                  "| Year | #1 Sector | #2 Sector | #3 Sector |",
                  "|---|---|---|---|"]
        for yr in years:
            mp = packages[yr].market_profile
            if not mp:
                continue
            sl = mp.sector_leaders
            lines.append(
                f"| {yr} | {sl[0] if len(sl) > 0 else '—'} "
                f"| {sl[1] if len(sl) > 1 else '—'} "
                f"| {sl[2] if len(sl) > 2 else '—'} |"
            )
        return "\n".join(lines) + "\n"

    def _dna_evolution(
        self, dna_records: List[CrossYearDNARecord],
        packages: Dict[int, YearKnowledgePackage]
    ) -> str:
        stable   = [r for r in dna_records if r.lifecycle_label == "STABLE"]
        emerging = [r for r in dna_records if r.lifecycle_label == "EMERGING"]
        disappearing = [r for r in dna_records if r.lifecycle_label == "DISAPPEARING"]
        strengthening = [r for r in dna_records if r.lifecycle_label == "STRENGTHENING"]
        weakening = [r for r in dna_records if r.lifecycle_label == "WEAKENING"]
        regime_independent = [r for r in dna_records if r.regime_dependency == "REGIME_INDEPENDENT"]
        regime_specific = [r for r in dna_records if r.regime_dependency == "REGIME_SPECIFIC"]
        lines = [
            "# DNA Evolution Report",
            f"**Generated:** {_now()}", "",
            "## DNA Lifecycle Summary",
            "| Label | Count | Description |",
            "|---|---|---|",
            f"| STABLE | {len(stable)} | Present ≥75% of years |",
            f"| STRENGTHENING | {len(strengthening)} | Confidence rising |",
            f"| WEAKENING | {len(weakening)} | Confidence declining |",
            f"| EMERGING | {len(emerging)} | Appeared recently |",
            f"| DISAPPEARING | {len(disappearing)} | Absent for 2+ years |",
            "",
            "## Stable DNA (Regime-Independent Survivors)",
        ]
        ri_stable = [r for r in stable if r.regime_dependency == "REGIME_INDEPENDENT"]
        for r in sorted(ri_stable, key=lambda x: -x.survival_score)[:20]:
            lines.append(
                f"- `{r.dna_id}` — survival {r.survival_score:.0%}, "
                f"trend {r.confidence_trend}, "
                f"years {r.years_present}"
            )
        lines += [
            "", "## Regime-Specific DNA (Only in Certain Regimes)",
        ]
        for r in sorted(regime_specific, key=lambda x: -len(x.years_present))[:20]:
            lines.append(
                f"- `{r.dna_id}` — regimes: {r.regimes_observed}, "
                f"years: {r.years_present}"
            )
        lines += ["", "## Emerging DNA (New Patterns)"]
        for r in emerging[:15]:
            lines.append(
                f"- `{r.dna_id}` — first seen in {r.years_present}, "
                f"confidence trend: {r.confidence_trend}"
            )
        lines += ["", "## Disappearing DNA (Retired Patterns)"]
        for r in disappearing[:15]:
            lines.append(
                f"- `{r.dna_id}` — last seen in {r.years_present}, "
                f"absent since {r.years_absent}"
            )
        return "\n".join(lines) + "\n"

    def _edge_evolution(
        self, edge_records: List[CrossYearEdgeRecord],
        packages: Dict[int, YearKnowledgePackage]
    ) -> str:
        strengthening = [r for r in edge_records if r.trend == "RISING"]
        weakening     = [r for r in edge_records if r.trend == "FALLING"]
        stable        = [r for r in edge_records if r.trend == "STABLE"]
        lines = [
            "# Edge Evolution Report",
            f"**Generated:** {_now()}", "",
            "## Edge Trend Summary",
            f"- Strengthening: **{len(strengthening)}**",
            f"- Stable: **{len(stable)}**",
            f"- Weakening: **{len(weakening)}**",
            "",
            "## Strengthening Edges",
            "| Edge ID | Active Years | Peak Confidence | Peak Year |",
            "|---|---|---|---|",
        ]
        for r in sorted(strengthening, key=lambda x: -x.peak_confidence)[:20]:
            lines.append(
                f"| `{r.edge_id}` | {r.years_active} | {r.peak_confidence:.2f} | {r.peak_confidence_year} |"
            )
        lines += [
            "", "## Weakening / Disappearing Edges",
            "| Edge ID | Last Active | Peak Confidence |",
            "|---|---|---|",
        ]
        for r in sorted(weakening + [e for e in edge_records if e.lifecycle_label == "DISAPPEARING"],
                        key=lambda x: -x.peak_confidence)[:20]:
            last = r.years_active[-1] if r.years_active else "—"
            lines.append(f"| `{r.edge_id}` | {last} | {r.peak_confidence:.2f} |")
        return "\n".join(lines) + "\n"

    def _behavioural_clusters(self, packages: Dict[int, YearKnowledgePackage]) -> str:
        lines = [
            "# Behavioural Cluster Report",
            f"**Generated:** {_now()}", "",
            "## Cluster Occurrence by Year",
            "| Year | Clusters |",
            "|---|---|",
        ]
        cluster_freq: Dict[str, int] = {}
        for yr in sorted(packages.keys()):
            mp = packages[yr].market_profile
            if mp:
                clusters_str = ", ".join(mp.behaviour_clusters)
                lines.append(f"| {yr} | {clusters_str} |")
                for c in mp.behaviour_clusters:
                    cluster_freq[c] = cluster_freq.get(c, 0) + 1
        lines += ["", "## Most Common Clusters",
                  "| Cluster | Years Observed |", "|---|---|"]
        for cluster, freq in sorted(cluster_freq.items(), key=lambda x: -x[1]):
            lines.append(f"| {cluster} | {freq} |")
        return "\n".join(lines) + "\n"

    def _regime_evolution(
        self,
        packages: Dict[int, YearKnowledgePackage],
        dna_records: List[CrossYearDNARecord],
    ) -> str:
        lines = [
            "# Regime Evolution Report",
            f"**Generated:** {_now()}", "",
            "## Regime Distribution by Year",
        ]
        lines += self._market_evolution(packages).split("\n")[5:20]  # reuse regime table
        lines += [
            "", "## Regime-Specific DNA Discovery",
            "DNA patterns that exist ONLY under a specific regime:",
            "| DNA ID | Regime | Years |",
            "|---|---|---|",
        ]
        for r in [x for x in dna_records if x.regime_dependency == "REGIME_SPECIFIC"][:30]:
            lines.append(f"| `{r.dna_id}` | {r.regimes_observed} | {r.years_present} |")
        return "\n".join(lines) + "\n"

    def _knowledge_synthesis(
        self,
        packages:     Dict[int, YearKnowledgePackage],
        dna_records:  List[CrossYearDNARecord],
        edge_records: List[CrossYearEdgeRecord],
    ) -> str:
        years = sorted(packages.keys())
        stable_ri = [r for r in dna_records
                     if r.lifecycle_label == "STABLE" and r.regime_dependency == "REGIME_INDEPENDENT"]
        lines = [
            "# Knowledge Synthesis Report",
            f"**Generated:** {_now()}",
            f"**Program:** HKAP-001 Historical Knowledge Acquisition",
            "",
            "## Synthesis Summary",
            f"- Years studied: {years}",
            f"- Stable regime-independent DNA: **{len(stable_ri)}** patterns",
            "",
            "## Answer: Which DNA survived every market regime?",
        ]
        for r in sorted(stable_ri, key=lambda x: -x.survival_score)[:15]:
            lines.append(
                f"- `{r.dna_id}` — present {r.survival_score:.0%} of years, "
                f"regimes: {r.regimes_observed}"
            )
        rs_dna = [r for r in dna_records if r.regime_dependency == "REGIME_SPECIFIC"]
        lines += ["", "## Answer: Which DNA existed only during specific regimes?"]
        for r in rs_dna[:15]:
            lines.append(f"- `{r.dna_id}` — only in regimes: {r.regimes_observed}")
        lines += [
            "",
            "## Answer: Which sectors repeatedly generated institutional leadership?",
        ]
        sector_count: Dict[str, int] = {}
        for yr in years:
            mp = packages[yr].market_profile
            if mp:
                for sec in mp.sector_leaders:
                    sector_count[sec] = sector_count.get(sec, 0) + 1
        for sec, cnt in sorted(sector_count.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"- {sec}: led in {cnt}/{len(years)} years")
        lines += ["", "## Answer: Which edges strengthened through time?"]
        strengthening = sorted(
            [r for r in edge_records if r.trend == "RISING"],
            key=lambda x: -x.peak_confidence
        )[:10]
        for r in strengthening:
            lines.append(f"- `{r.edge_id}` — peak {r.peak_confidence:.2f} in {r.peak_confidence_year}")
        lines += ["", "## Answer: Which edges disappeared permanently?"]
        gone = [r for r in edge_records if r.lifecycle_label == "DISAPPEARING"][:10]
        for r in gone:
            last = r.years_active[-1] if r.years_active else "unknown"
            lines.append(f"- `{r.edge_id}` — last active {last}")
        return "\n".join(lines) + "\n"

    def _final_recommendation(
        self,
        dna_records:  List[CrossYearDNARecord],
        edge_records: List[CrossYearEdgeRecord],
        packages:     Dict[int, YearKnowledgePackage],
    ) -> str:
        stable_ri = sorted(
            [r for r in dna_records
             if r.lifecycle_label == "STABLE" and r.regime_dependency == "REGIME_INDEPENDENT"],
            key=lambda x: -x.survival_score,
        )
        strong_edges = sorted(
            [r for r in edge_records if r.trend == "RISING"],
            key=lambda x: -x.peak_confidence,
        )
        lines = [
            "# Final Institutional Knowledge Recommendation",
            f"**Generated:** {_now()}",
            "**Authority:** Scientific Director — HKAP-001 Historical Synthesis",
            "",
            "> This document represents the Scientific Director's recommendation",
            "> on what knowledge should be promoted to the live Institutional DNA Repository.",
            "> No merge should occur without explicit SD approval via `HKAPEngine.request_live_merge()`.",
            "",
            "## Recommended for Permanent Institutional Knowledge",
            "",
            "### Tier 1 — Unconditionally Stable DNA",
            "Present in ≥75% of years across all observed regimes.",
            "",
        ]
        for r in stable_ri[:10]:
            lines.append(
                f"- **`{r.dna_id}`** — "
                f"survival {r.survival_score:.0%}, "
                f"regimes {r.regimes_observed}, "
                f"trend {r.confidence_trend}"
            )
        lines += [
            "", "### Tier 2 — Strengthening Edges",
            "Confidence rising over time — increasing predictive power.",
            "",
        ]
        for r in strong_edges[:10]:
            lines.append(
                f"- **`{r.edge_id}`** — "
                f"active years {r.years_active}, "
                f"peak confidence {r.peak_confidence:.2f}"
            )
        lines += [
            "", "## Not Recommended for Promotion",
            "- Regime-specific DNA: retain in year-scoped IDR only",
            "- Disappearing patterns: archive, do not promote",
            "- Low-survival sporadic DNA: needs more years of evidence",
            "",
            "## Scientific Director Final Questions",
            "1. Which DNA survived every market regime? See Tier 1 above",
            "2. Which DNA was regime-specific? See DNA Evolution Report",
            "3. Which features predicted major winners? See Winner DNA in yearly reports",
            "4. Which sectors repeatedly led? See Knowledge Synthesis",
            "5. Which market personalities repeated? See Behavioural Cluster Report",
            "6. Which edges strengthened? See Tier 2 above",
            "7. Which edges disappeared? See Edge Evolution Report",
            "8. What becomes permanent knowledge? Tiers 1 and 2 above, pending SD approval",
            "",
            "---",
            "*HKAP-001 Historical Knowledge Acquisition Program — complete.*",
        ]
        return "\n".join(lines) + "\n"

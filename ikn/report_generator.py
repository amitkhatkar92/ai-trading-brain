"""
report_generator.py — Generates IKN-001 markdown reports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List

from .ikn_config import IKNConfig
from .ikn_models import NodeType, RelationshipType

if TYPE_CHECKING:
    from .ikn_network import IKNNetwork

_REPORT_NAMES = [
    "IKN_NETWORK_SUMMARY.md",
    "IKN_NODE_STATISTICS.md",
    "IKN_RELATIONSHIP_STATISTICS.md",
    "IKN_TRACEABILITY_REPORT.md",
]


class IKNReportGenerator:

    def __init__(self, config: IKNConfig) -> None:
        self._config = config

    def generate(self, network: "IKNNetwork") -> List[str]:
        stats    = network.statistics()
        coverage = network.coverage()
        paths: List[str] = []
        builders = [
            ("IKN_NETWORK_SUMMARY.md",        self._network_summary(stats, coverage)),
            ("IKN_NODE_STATISTICS.md",         self._node_statistics(stats, network)),
            ("IKN_RELATIONSHIP_STATISTICS.md", self._rel_statistics(stats, network)),
            ("IKN_TRACEABILITY_REPORT.md",     self._traceability(stats, coverage, network)),
        ]
        for filename, content in builders:
            out_path = str(Path(self._config.reports_root) / filename)
            paths.append(out_path)
            if not self._config.dry_run:
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                Path(out_path).write_text(content, encoding="utf-8")
        return paths

    # ── builders ──────────────────────────────────────────────────────────────

    def _network_summary(self, stats, coverage) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        node_rows = "\n".join(
            f"| {k} | {v} |" for k, v in sorted(stats.nodes_by_type.items())
        )
        rel_rows = "\n".join(
            f"| {k} | {v} |" for k, v in sorted(stats.relationships_by_type.items())
        )
        top_rows = "\n".join(
            f"| {nid} | {deg} |" for nid, deg in stats.most_connected_nodes[:10]
        )
        return (
            f"# IKN-001 Network Summary\n\n"
            f"Generated: {now}\n\n"
            f"## Overview\n\n"
            f"| Metric | Value |\n|---|---|\n"
            f"| Total Nodes | {stats.total_nodes} |\n"
            f"| Total Relationships | {stats.total_relationships} |\n"
            f"| Avg Confidence | {stats.avg_confidence:.3f} |\n"
            f"| Orphan Nodes | {stats.orphan_count} |\n"
            f"| Node Type Coverage | {coverage['node_type_coverage']:.1%} |\n"
            f"| Relationship Type Coverage | {coverage['relationship_type_coverage']:.1%} |\n"
            f"| Traceability Score | {coverage['traceability_score']:.1%} |\n\n"
            f"## Most Connected Nodes\n\n"
            f"| Node ID | Degree |\n|---|---|\n{top_rows}\n\n"
            f"## Node Type Distribution\n\n"
            f"| Type | Count |\n|---|---|\n{node_rows}\n\n"
            f"## Relationship Type Distribution\n\n"
            f"| Type | Count |\n|---|---|\n{rel_rows}\n"
        )

    def _node_statistics(self, stats, network: "IKNNetwork") -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        all_nodes = network._store.get_all_nodes()
        sections: List[str] = []
        for nt in sorted({n.node_type for n in all_nodes}):
            group = [n for n in all_nodes if n.node_type == nt]
            lines = [f"\n### {nt} ({len(group)} nodes)\n"]
            for n in group[:20]:
                deg = len(network.get_relationships(n.node_id))
                lines.append(f"- **{n.node_id}** — {n.name} ({deg} rels, v{n.version})\n")
            if len(group) > 20:
                lines.append(f"- *(and {len(group)-20} more)*\n")
            sections.extend(lines)
        return (
            f"# IKN-001 Node Statistics\n\n"
            f"Generated: {now}\n\n"
            f"Total Nodes: {stats.total_nodes}\n"
            + "".join(sections)
        )

    def _rel_statistics(self, stats, network: "IKNNetwork") -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        all_rels = network._store.get_all_relationships()
        sections: List[str] = []
        for rt, count in sorted(stats.relationships_by_type.items()):
            sample = [r for r in all_rels if r.relationship_type == rt][:3]
            sections.append(f"\n### {rt} ({count} relationships)\n")
            for r in sample:
                sections.append(
                    f"- {r.source_id} -> {r.target_id} "
                    f"(confidence={r.confidence:.2f}, v{r.version})\n"
                )
        return (
            f"# IKN-001 Relationship Statistics\n\n"
            f"Generated: {now}\n\n"
            f"Total Relationships: {stats.total_relationships}\n"
            f"Average Confidence: {stats.avg_confidence:.3f}\n"
            + "".join(sections)
        )

    def _traceability(self, stats, coverage, network: "IKNNetwork") -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        all_nodes = network._store.get_all_nodes()
        disc_nodes = [n for n in all_nodes if n.node_type == "DISCOVERY"]
        _trace_types = {"DISCOVERED_IN", "SUPPORTED_BY", "GENERATED_BY"}
        traceable   = [n for n in disc_nodes
                       if any(r.relationship_type in _trace_types
                              for r in network.get_relationships(n.node_id))]
        untraceable = [n for n in disc_nodes if n not in traceable]
        t_lines = "".join(f"- {n.node_id} ({n.name})\n" for n in traceable[:20])
        u_lines = "".join(f"- {n.node_id} ({n.name})\n" for n in untraceable[:20])
        return (
            f"# IKN-001 Traceability Report\n\n"
            f"Generated: {now}\n\n"
            f"## IKN Final Questions\n\n"
            f"1. Can every institutional fact be traced to original evidence?\n"
            f"   Score: {coverage['traceability_score']:.1%}\n\n"
            f"2. Can every DNA be explained through connected studies?\n"
            f"   DNA nodes: {stats.nodes_by_type.get('DNA', 0)}\n\n"
            f"3. Can Scientific Director navigate without reading individual files?\n"
            f"   Total relationships indexed: {stats.total_relationships}\n\n"
            f"4. Can future knowledge sources be connected without changing IKN?\n"
            f"   Yes. New sources register nodes and add relationships only.\n\n"
            f"5. Has IIOS gained a permanent institutional memory?\n"
            f"   Total nodes: {stats.total_nodes} | "
            f"Total relationships: {stats.total_relationships}\n\n"
            f"## Traceable Discoveries\n\n"
            f"{len(traceable)} / {len(disc_nodes)} discovery nodes have evidence chains.\n\n"
            f"### Traceable\n{t_lines or '(none)'}\n\n"
            f"### Untraceable\n{u_lines or '(none)'}\n"
        )

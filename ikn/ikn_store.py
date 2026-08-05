"""
ikn_store.py — Thread-safe SQLite storage backend for IKN-001.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ikn_config import IKNConfig
from .ikn_models import KnowledgeEvidence, KnowledgeNode, KnowledgeRelationship

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    node_id    TEXT PRIMARY KEY,
    node_type  TEXT NOT NULL,
    name       TEXT NOT NULL,
    metadata   TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id    TEXT PRIMARY KEY,
    source_id          TEXT NOT NULL,
    target_id          TEXT NOT NULL,
    relationship_type  TEXT NOT NULL,
    confidence         REAL NOT NULL DEFAULT 1.0,
    evidence_count     INTEGER NOT NULL DEFAULT 0,
    supporting_studies TEXT NOT NULL DEFAULT '[]',
    supporting_years   TEXT NOT NULL DEFAULT '[]',
    supporting_regimes TEXT NOT NULL DEFAULT '[]',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    version            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id     TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    description     TEXT NOT NULL,
    source          TEXT NOT NULL,
    data_points     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_rel_type   ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_ev_rel     ON evidence(relationship_id);
"""


class IKNStore:
    """
    Thread-safe SQLite storage layer.
    db_path ':memory:' is used for dry_run mode.
    """

    def __init__(self, config: IKNConfig) -> None:
        self._lock = threading.Lock()
        db_path    = ":memory:" if config.dry_run else config.db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ── nodes ─────────────────────────────────────────────────────────────────

    def add_node(self, node: KnowledgeNode) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO nodes "
                "(node_id,node_type,name,metadata,created_at,updated_at,version) "
                "VALUES (?,?,?,?,?,?,?)",
                (node.node_id, node.node_type, node.name,
                 json.dumps(node.metadata), node.created_at, node.updated_at, node.version),
            )
            self._conn.commit()

    def update_node(self, node: KnowledgeNode) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE nodes SET name=?,metadata=?,updated_at=?,version=? "
                "WHERE node_id=?",
                (node.name, json.dumps(node.metadata),
                 node.updated_at, node.version, node.node_id),
            )
            self._conn.commit()

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM nodes WHERE node_id=?", (node_id,)
            ).fetchone()
        return self._row_to_node(row) if row else None

    def get_all_nodes(self) -> List[KnowledgeNode]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM nodes ORDER BY created_at"
            ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def get_nodes_by_type(self, node_type: str) -> List[KnowledgeNode]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM nodes WHERE node_type=? ORDER BY created_at", (node_type,)
            ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def node_exists(self, node_id: str) -> bool:
        with self._lock:
            return self._conn.execute(
                "SELECT 1 FROM nodes WHERE node_id=?", (node_id,)
            ).fetchone() is not None

    # ── relationships ─────────────────────────────────────────────────────────

    def add_relationship(self, rel: KnowledgeRelationship) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO relationships "
                "(relationship_id,source_id,target_id,relationship_type,"
                " confidence,evidence_count,supporting_studies,supporting_years,"
                " supporting_regimes,created_at,updated_at,version) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (rel.relationship_id, rel.source_id, rel.target_id,
                 rel.relationship_type, rel.confidence, rel.evidence_count,
                 json.dumps(rel.supporting_studies), json.dumps(rel.supporting_years),
                 json.dumps(rel.supporting_regimes),
                 rel.created_at, rel.updated_at, rel.version),
            )
            self._conn.commit()

    def update_relationship(self, rel: KnowledgeRelationship) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE relationships SET "
                "confidence=?,evidence_count=?,supporting_studies=?,"
                "supporting_years=?,supporting_regimes=?,updated_at=?,version=? "
                "WHERE relationship_id=?",
                (rel.confidence, rel.evidence_count,
                 json.dumps(rel.supporting_studies), json.dumps(rel.supporting_years),
                 json.dumps(rel.supporting_regimes),
                 rel.updated_at, rel.version, rel.relationship_id),
            )
            self._conn.commit()

    def get_relationship(self, rel_id: str) -> Optional[KnowledgeRelationship]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM relationships WHERE relationship_id=?", (rel_id,)
            ).fetchone()
        return self._row_to_rel(row) if row else None

    def get_relationships_for_node(
        self,
        node_id:   str,
        rel_type:  Optional[str] = None,
        direction: str = "both",
    ) -> List[KnowledgeRelationship]:
        conditions: List[str] = []
        params:     List[Any] = []

        if direction == "outgoing":
            conditions.append("source_id=?")
            params.append(node_id)
        elif direction == "incoming":
            conditions.append("target_id=?")
            params.append(node_id)
        else:
            conditions.append("(source_id=? OR target_id=?)")
            params.extend([node_id, node_id])

        if rel_type:
            conditions.append("relationship_type=?")
            params.append(rel_type)

        where = " AND ".join(conditions)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM relationships WHERE {where} ORDER BY created_at",
                params,
            ).fetchall()
        return [self._row_to_rel(r) for r in rows]

    def get_all_relationships(self) -> List[KnowledgeRelationship]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM relationships ORDER BY created_at"
            ).fetchall()
        return [self._row_to_rel(r) for r in rows]

    def relationship_exists(self, rel_id: str) -> bool:
        with self._lock:
            return self._conn.execute(
                "SELECT 1 FROM relationships WHERE relationship_id=?", (rel_id,)
            ).fetchone() is not None

    # ── evidence ──────────────────────────────────────────────────────────────

    def add_evidence(self, ev: KnowledgeEvidence) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO evidence "
                "(evidence_id,relationship_id,description,source,data_points,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (ev.evidence_id, ev.relationship_id, ev.description,
                 ev.source, ev.data_points, ev.created_at),
            )
            self._conn.commit()

    def get_evidence_for_relationship(self, rel_id: str) -> List[KnowledgeEvidence]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM evidence WHERE relationship_id=? ORDER BY created_at",
                (rel_id,),
            ).fetchall()
        return [
            KnowledgeEvidence(
                evidence_id=r["evidence_id"], relationship_id=r["relationship_id"],
                description=r["description"], source=r["source"],
                data_points=r["data_points"], created_at=r["created_at"],
            )
            for r in rows
        ]

    # ── statistics ────────────────────────────────────────────────────────────

    def get_raw_statistics(self) -> Dict[str, Any]:
        with self._lock:
            total_nodes = self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            total_rels  = self._conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
            type_nodes  = self._conn.execute(
                "SELECT node_type, COUNT(*) as c FROM nodes GROUP BY node_type"
            ).fetchall()
            type_rels   = self._conn.execute(
                "SELECT relationship_type, COUNT(*) as c "
                "FROM relationships GROUP BY relationship_type"
            ).fetchall()
            avg_conf_row = self._conn.execute(
                "SELECT AVG(confidence) FROM relationships"
            ).fetchone()
            avg_conf    = avg_conf_row[0] or 0.0
            top_rows    = self._conn.execute(
                "SELECT node_id, SUM(cnt) as degree FROM ("
                "  SELECT source_id as node_id, COUNT(*) as cnt "
                "  FROM relationships GROUP BY source_id "
                "  UNION ALL "
                "  SELECT target_id as node_id, COUNT(*) as cnt "
                "  FROM relationships GROUP BY target_id"
                ") GROUP BY node_id ORDER BY degree DESC LIMIT 10"
            ).fetchall()
            orphan_count = self._conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE node_id NOT IN ("
                "  SELECT DISTINCT source_id FROM relationships "
                "  UNION SELECT DISTINCT target_id FROM relationships"
                ")"
            ).fetchone()[0]
        return {
            "total_nodes":  total_nodes,
            "total_rels":   total_rels,
            "by_node_type": {r["node_type"]: r["c"] for r in type_nodes},
            "by_rel_type":  {r["relationship_type"]: r["c"] for r in type_rels},
            "avg_conf":     round(avg_conf, 4),
            "top_nodes":    [(r["node_id"], r["degree"]) for r in top_rows],
            "orphan_count": orphan_count,
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> KnowledgeNode:
        return KnowledgeNode(
            node_id=row["node_id"], node_type=row["node_type"], name=row["name"],
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"], updated_at=row["updated_at"], version=row["version"],
        )

    @staticmethod
    def _row_to_rel(row: sqlite3.Row) -> KnowledgeRelationship:
        return KnowledgeRelationship(
            relationship_id   = row["relationship_id"],
            source_id         = row["source_id"],
            target_id         = row["target_id"],
            relationship_type = row["relationship_type"],
            confidence        = row["confidence"],
            evidence_count    = row["evidence_count"],
            supporting_studies = json.loads(row["supporting_studies"]),
            supporting_years   = json.loads(row["supporting_years"]),
            supporting_regimes = json.loads(row["supporting_regimes"]),
            created_at        = row["created_at"],
            updated_at        = row["updated_at"],
            version           = row["version"],
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

"""
idr_repository.py — Institutional DNA Repository.

R-013: Institutional DNA Repository.

Responsibilities:
    Persist every DNA record discovered by MLS phases 3–5B.
    Version every change — never overwrite.
    Maintain complete audit trail (study, operator, reason, timestamp).
    Track DNA evidence, history, and market context snapshots.
    Provide thread-safe concurrent read / serialised write access.
    Automatic WAL-mode SQLite backend with integrity verification.
    Backup support.

Explicitly NOT responsible for:
    DNA discovery.
    DNA scoring.
    Trading decisions.
    Modifying thresholds or configuration.
    Calling any MLS phase engine.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .mls_config import MLSConfig
from .idr_models import (
    DNAContext,
    DNAEvidence,
    DNAHistory,
    DNARepositoryStatistics,
    DNARevision,
    IDRError,
    IDRIntegrityError,
    IDRNotFoundError,
    IDRVersionError,
    InstitutionalDNA,
)

log = logging.getLogger(__name__)

_DEFAULT_IDR_DIR = Path(__file__).resolve().parent.parent / "data" / "mls"

# ─── schema statements (ordered — no circular deps) ───────────────────────────

_SCHEMA_STMTS: List[str] = [
    """CREATE TABLE IF NOT EXISTS schema_version (
        version     INTEGER PRIMARY KEY,
        applied_at  TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS dna (
        id                    TEXT    NOT NULL,
        version               INTEGER NOT NULL,
        feature_name          TEXT    NOT NULL,
        direction             TEXT    NOT NULL,
        category              TEXT    NOT NULL,
        lifecycle             TEXT    NOT NULL,
        consensus_score       REAL    NOT NULL DEFAULT 0.0,
        confidence            REAL    NOT NULL DEFAULT 0.0,
        effect_size           REAL    NOT NULL DEFAULT 0.0,
        regime_consistency    REAL    NOT NULL DEFAULT 0.0,
        sector_consistency    REAL    NOT NULL DEFAULT 0.0,
        temporal_stability    REAL    NOT NULL DEFAULT 0.0,
        replication_frequency REAL    NOT NULL DEFAULT 0.0,
        evidence_count        INTEGER NOT NULL DEFAULT 0,
        regime_counts         TEXT    NOT NULL DEFAULT '{}',
        last_seen             TEXT,
        study_id              TEXT    NOT NULL DEFAULT '',
        source                TEXT    NOT NULL DEFAULT '',
        created_at            TEXT    NOT NULL,
        updated_at            TEXT    NOT NULL,
        is_current            INTEGER NOT NULL DEFAULT 1,
        metadata              TEXT    NOT NULL DEFAULT '{}',
        PRIMARY KEY (id, version)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_dna_current  ON dna(id, is_current)",
    "CREATE INDEX IF NOT EXISTS idx_dna_lc       ON dna(lifecycle, is_current)",
    "CREATE INDEX IF NOT EXISTS idx_dna_feature  ON dna(feature_name, is_current)",
    "CREATE INDEX IF NOT EXISTS idx_dna_category ON dna(category, is_current)",
    """CREATE TABLE IF NOT EXISTS dna_evidence (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        dna_id           TEXT    NOT NULL,
        dna_version      INTEGER NOT NULL,
        study_id         TEXT    NOT NULL DEFAULT '',
        source           TEXT    NOT NULL DEFAULT '',
        sample_size      INTEGER NOT NULL DEFAULT 0,
        effect_size      REAL    NOT NULL DEFAULT 0.0,
        confidence       REAL    NOT NULL DEFAULT 0.0,
        regime           TEXT    NOT NULL DEFAULT '',
        sector           TEXT    NOT NULL DEFAULT '',
        p_value          REAL,
        ci_low           REAL,
        ci_high          REAL,
        observation_date TEXT    NOT NULL,
        created_at       TEXT    NOT NULL,
        metadata         TEXT    NOT NULL DEFAULT '{}'
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ev_dna ON dna_evidence(dna_id)",
    """CREATE TABLE IF NOT EXISTS dna_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        dna_id          TEXT    NOT NULL,
        history_date    TEXT    NOT NULL,
        confidence      REAL    NOT NULL DEFAULT 0.0,
        consensus_score REAL    NOT NULL DEFAULT 0.0,
        drift           REAL    NOT NULL DEFAULT 0.0,
        stability       REAL    NOT NULL DEFAULT 0.0,
        relevance       TEXT    NOT NULL DEFAULT '',
        lifecycle       TEXT    NOT NULL DEFAULT '',
        version_at_time INTEGER NOT NULL DEFAULT 1,
        created_at      TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_hist_dna  ON dna_history(dna_id)",
    "CREATE INDEX IF NOT EXISTS idx_hist_date ON dna_history(dna_id, history_date)",
    """CREATE TABLE IF NOT EXISTS dna_context (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        dna_id                TEXT    NOT NULL,
        dna_version           INTEGER NOT NULL,
        regime                TEXT    NOT NULL DEFAULT '',
        volatility            REAL    NOT NULL DEFAULT 0.0,
        breadth               REAL    NOT NULL DEFAULT 0.0,
        sector                REAL    NOT NULL DEFAULT 0.0,
        liquidity             REAL    NOT NULL DEFAULT 0.0,
        institutional         REAL    NOT NULL DEFAULT 0.0,
        historical_similarity REAL    NOT NULL DEFAULT 0.0,
        context_date          TEXT    NOT NULL,
        created_at            TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ctx_dna ON dna_context(dna_id)",
    """CREATE TABLE IF NOT EXISTS audit_log (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        operation      TEXT    NOT NULL,
        dna_id         TEXT    NOT NULL,
        version_before INTEGER,
        version_after  INTEGER,
        operator       TEXT    NOT NULL DEFAULT 'system',
        study_id       TEXT    NOT NULL DEFAULT '',
        reason         TEXT    NOT NULL DEFAULT '',
        timestamp      TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_audit_dna ON audit_log(dna_id)",
]


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ═══════════════════════════════════════════════════════════════════════════════
# IDRRepository
# ═══════════════════════════════════════════════════════════════════════════════

class IDRRepository:
    """
    Institutional DNA Repository.

    Persistent, versioned, thread-safe SQLite store for all institutional DNA
    knowledge generated by MLS.

    Every DNA update creates a new version record.  No record is ever
    overwritten.  A complete audit trail is maintained for every operation.

    Thread safety model:
        - WAL journal mode: multiple concurrent readers, one writer.
        - Python RLock: serialises Python-level writes.
        - Per-call connections: no cross-thread connection sharing.
    """

    SCHEMA_VERSION: int = 1

    def __init__(
        self,
        db_path: Optional[Path] = None,
        config: Optional[MLSConfig] = None,
    ) -> None:
        self._db_path = Path(db_path) if db_path else (_DEFAULT_IDR_DIR / "institutional_dna.db")
        self._cfg = config or MLSConfig()
        self._write_lock = threading.RLock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── connection ────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    # ── schema initialisation ─────────────────────────────────────────────────

    def _init_schema(self) -> None:
        with self._write_lock:
            conn = self._conn()
            try:
                for stmt in _SCHEMA_STMTS:
                    conn.execute(stmt)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version(version, applied_at, description) "
                    "VALUES (?, ?, ?)",
                    (self.SCHEMA_VERSION, _now(), "Initial IDR schema — R-013"),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _current_version(self, conn: sqlite3.Connection, dna_id: str) -> int:
        """Return the current (max) version number, or 0 if DNA does not exist."""
        row = conn.execute(
            "SELECT MAX(version) FROM dna WHERE id = ?", (dna_id,)
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def _clear_current_flag(self, conn: sqlite3.Connection, dna_id: str) -> None:
        conn.execute("UPDATE dna SET is_current = 0 WHERE id = ?", (dna_id,))

    def _log_audit(
        self,
        conn: sqlite3.Connection,
        operation: str,
        dna_id: str,
        version_before: Optional[int],
        version_after: int,
        operator: str,
        study_id: str,
        reason: str,
    ) -> None:
        conn.execute(
            "INSERT INTO audit_log"
            " (operation, dna_id, version_before, version_after,"
            "  operator, study_id, reason, timestamp)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (operation, dna_id, version_before, version_after,
             operator, study_id, reason, _now()),
        )

    def _row_to_dna(self, row: sqlite3.Row) -> InstitutionalDNA:
        return InstitutionalDNA(
            id=row["id"],
            feature_name=row["feature_name"],
            direction=row["direction"],
            category=row["category"],
            lifecycle=row["lifecycle"],
            version=int(row["version"]),
            consensus_score=float(row["consensus_score"]),
            confidence=float(row["confidence"]),
            effect_size=float(row["effect_size"]),
            regime_consistency=float(row["regime_consistency"]),
            sector_consistency=float(row["sector_consistency"]),
            temporal_stability=float(row["temporal_stability"]),
            replication_frequency=float(row["replication_frequency"]),
            evidence_count=int(row["evidence_count"]),
            regime_counts=json.loads(row["regime_counts"]),
            last_seen=row["last_seen"],
            study_id=row["study_id"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_current=bool(row["is_current"]),
            metadata=json.loads(row["metadata"]),
        )

    def _insert_dna_row(
        self,
        conn: sqlite3.Connection,
        dna: InstitutionalDNA,
        version: int,
        is_current: bool,
    ) -> None:
        conn.execute(
            "INSERT INTO dna"
            " (id, version, feature_name, direction, category, lifecycle,"
            "  consensus_score, confidence, effect_size,"
            "  regime_consistency, sector_consistency, temporal_stability,"
            "  replication_frequency, evidence_count, regime_counts,"
            "  last_seen, study_id, source, created_at, updated_at,"
            "  is_current, metadata)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                dna.id, version, dna.feature_name, dna.direction,
                dna.category, dna.lifecycle,
                dna.consensus_score, dna.confidence, dna.effect_size,
                dna.regime_consistency, dna.sector_consistency,
                dna.temporal_stability, dna.replication_frequency,
                dna.evidence_count,
                json.dumps(dna.regime_counts),
                dna.last_seen, dna.study_id, dna.source,
                dna.created_at, dna.updated_at,
                1 if is_current else 0,
                json.dumps(dna.metadata),
            ),
        )

    def _do_update(
        self,
        dna_id: str,
        updates: Dict[str, Any],
        operation: str,
        reason: str,
        study_id: str,
        operator: str,
    ) -> DNARevision:
        """Internal: apply updates dict → new version.  Caller sets operation string."""
        with self._write_lock:
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT * FROM dna WHERE id = ? AND is_current = 1", (dna_id,)
                ).fetchone()
                if row is None:
                    raise IDRNotFoundError(f"DNA '{dna_id}' not found in repository")
                current = self._row_to_dna(row)
                current_ver = current.version
                new_ver = current_ver + 1
                self._clear_current_flag(conn, dna_id)
                now = _now()
                updated_dict = current.to_dict()
                _IMMUTABLE = {"id", "version", "created_at", "is_current"}
                for k, v in updates.items():
                    if k not in _IMMUTABLE:
                        updated_dict[k] = v
                updated_dict["version"] = new_ver
                updated_dict["updated_at"] = now
                updated_dict["is_current"] = True
                new_dna = InstitutionalDNA.from_dict(updated_dict)
                self._insert_dna_row(conn, new_dna, new_ver, True)
                self._log_audit(conn, operation, dna_id, current_ver, new_ver,
                                operator, study_id, reason)
                conn.commit()
                return DNARevision(
                    dna_id=dna_id,
                    version=new_ver,
                    previous_version=current_ver,
                    operation=operation,
                    reason=reason,
                    study_id=study_id,
                    operator=operator,
                    timestamp=now,
                    changes=updates,
                )
            except IDRNotFoundError:
                conn.rollback()
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ── public write API ──────────────────────────────────────────────────────

    def save(
        self,
        dna: InstitutionalDNA,
        study_id: str = "",
        operator: str = "system",
    ) -> DNARevision:
        """
        Persist a DNA record.

        If the id has never been seen → creates version 1 (CREATED).
        If the id already exists → creates the next version (UPDATED).
        The previous version remains accessible via get_version().

        Thread-safe.  Atomic.  Rolls back on any failure.
        """
        with self._write_lock:
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                current_ver = self._current_version(conn, dna.id)
                new_ver = current_ver + 1
                is_new = current_ver == 0

                if is_new:
                    created_at = dna.created_at or _now()
                    operation = "CREATED"
                else:
                    orig = conn.execute(
                        "SELECT created_at FROM dna WHERE id = ? AND version = 1",
                        (dna.id,)
                    ).fetchone()
                    created_at = orig["created_at"] if orig else (dna.created_at or _now())
                    operation = "UPDATED"

                self._clear_current_flag(conn, dna.id)
                now = _now()

                to_insert = dataclasses.replace(
                    dna,
                    version=new_ver,
                    study_id=study_id or dna.study_id,
                    created_at=created_at,
                    updated_at=now,
                    is_current=True,
                )
                self._insert_dna_row(conn, to_insert, new_ver, True)
                self._log_audit(
                    conn, operation, dna.id,
                    None if is_new else current_ver,
                    new_ver, operator, study_id or dna.study_id, "",
                )
                conn.commit()
                return DNARevision(
                    dna_id=dna.id,
                    version=new_ver,
                    previous_version=None if is_new else current_ver,
                    operation=operation,
                    reason="",
                    study_id=study_id or dna.study_id,
                    operator=operator,
                    timestamp=now,
                    changes={},
                )
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def update(
        self,
        dna_id: str,
        updates: Dict[str, Any],
        reason: str = "",
        study_id: str = "",
        operator: str = "system",
    ) -> DNARevision:
        """
        Update specific fields of an existing DNA record.

        Creates a new version.  The previous version is preserved.
        Raises IDRNotFoundError if dna_id does not exist.

        Thread-safe.  Atomic.  Rolls back on any failure.
        """
        return self._do_update(dna_id, updates, "UPDATED", reason, study_id, operator)

    def retire(
        self,
        dna_id: str,
        reason: str = "",
        operator: str = "system",
    ) -> DNARevision:
        """
        Transition a DNA record to RETIRED lifecycle.

        Creates a new version with lifecycle = "RETIRED".
        The previous version is preserved.
        Raises IDRNotFoundError if dna_id does not exist.
        """
        return self._do_update(dna_id, {"lifecycle": "RETIRED"}, "RETIRED", reason, "", operator)

    def add_evidence(
        self,
        dna_id: str,
        ev: DNAEvidence,
    ) -> None:
        """
        Append a DNAEvidence record to an existing DNA.

        Evidence records are immutable — this is append-only.
        Raises IDRNotFoundError if dna_id does not exist.
        Thread-safe.
        """
        with self._write_lock:
            conn = self._conn()
            try:
                ver = self._current_version(conn, dna_id)
                if ver == 0:
                    raise IDRNotFoundError(f"DNA '{dna_id}' not found in repository")
                conn.execute(
                    "INSERT INTO dna_evidence"
                    " (dna_id, dna_version, study_id, source, sample_size,"
                    "  effect_size, confidence, regime, sector,"
                    "  p_value, ci_low, ci_high, observation_date, created_at, metadata)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        dna_id, ver,
                        ev.study_id, ev.source, ev.sample_size,
                        ev.effect_size, ev.confidence, ev.regime, ev.sector,
                        ev.p_value, ev.ci_low, ev.ci_high,
                        ev.observation_date, _now(),
                        json.dumps(ev.metadata),
                    ),
                )
                conn.commit()
            except IDRNotFoundError:
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def add_history(
        self,
        dna_id: str,
        hist: DNAHistory,
    ) -> None:
        """
        Append a DNAHistory point to an existing DNA.

        Append-only.  Raises IDRNotFoundError if dna_id does not exist.
        Thread-safe.
        """
        with self._write_lock:
            conn = self._conn()
            try:
                ver = self._current_version(conn, dna_id)
                if ver == 0:
                    raise IDRNotFoundError(f"DNA '{dna_id}' not found in repository")
                conn.execute(
                    "INSERT INTO dna_history"
                    " (dna_id, history_date, confidence, consensus_score,"
                    "  drift, stability, relevance, lifecycle, version_at_time, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        dna_id, hist.history_date,
                        hist.confidence, hist.consensus_score,
                        hist.drift, hist.stability,
                        hist.relevance, hist.lifecycle,
                        hist.version_at_time, _now(),
                    ),
                )
                conn.commit()
            except IDRNotFoundError:
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def add_context(
        self,
        dna_id: str,
        ctx: DNAContext,
    ) -> None:
        """
        Append a market-context snapshot for an existing DNA.

        Append-only.  Raises IDRNotFoundError if dna_id does not exist.
        Thread-safe.
        """
        with self._write_lock:
            conn = self._conn()
            try:
                ver = self._current_version(conn, dna_id)
                if ver == 0:
                    raise IDRNotFoundError(f"DNA '{dna_id}' not found in repository")
                conn.execute(
                    "INSERT INTO dna_context"
                    " (dna_id, dna_version, regime, volatility, breadth,"
                    "  sector, liquidity, institutional, historical_similarity,"
                    "  context_date, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        dna_id, ver,
                        ctx.regime, ctx.volatility, ctx.breadth,
                        ctx.sector, ctx.liquidity, ctx.institutional,
                        ctx.historical_similarity, ctx.context_date, _now(),
                    ),
                )
                conn.commit()
            except IDRNotFoundError:
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ── public read API ───────────────────────────────────────────────────────

    def get(self, dna_id: str) -> InstitutionalDNA:
        """
        Return the latest version of a DNA record.

        Raises IDRNotFoundError if not found.
        """
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM dna WHERE id = ? AND is_current = 1", (dna_id,)
            ).fetchone()
            if row is None:
                raise IDRNotFoundError(f"DNA '{dna_id}' not found in repository")
            return self._row_to_dna(row)
        finally:
            conn.close()

    def get_version(self, dna_id: str, version: int) -> InstitutionalDNA:
        """
        Return a specific version of a DNA record.

        Raises IDRVersionError if (dna_id, version) not found.
        """
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM dna WHERE id = ? AND version = ?",
                (dna_id, version),
            ).fetchone()
            if row is None:
                raise IDRVersionError(
                    f"DNA '{dna_id}' version {version} not found in repository"
                )
            return self._row_to_dna(row)
        finally:
            conn.close()

    def history(self, dna_id: str) -> List[DNAHistory]:
        """
        Return all DNAHistory records for a DNA id, ordered by date ascending.

        Returns empty list if no history has been recorded.
        """
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM dna_history"
                " WHERE dna_id = ? ORDER BY history_date ASC, id ASC",
                (dna_id,),
            ).fetchall()
            return [
                DNAHistory(
                    id=int(r["id"]),
                    dna_id=r["dna_id"],
                    history_date=r["history_date"],
                    confidence=float(r["confidence"]),
                    consensus_score=float(r["consensus_score"]),
                    drift=float(r["drift"]),
                    stability=float(r["stability"]),
                    relevance=r["relevance"],
                    lifecycle=r["lifecycle"],
                    version_at_time=int(r["version_at_time"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def evidence(self, dna_id: str) -> List[DNAEvidence]:
        """
        Return all DNAEvidence records for a DNA id.

        Returns empty list if no evidence has been recorded.
        """
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM dna_evidence WHERE dna_id = ? ORDER BY id ASC",
                (dna_id,),
            ).fetchall()
            return [
                DNAEvidence(
                    id=int(r["id"]),
                    dna_id=r["dna_id"],
                    dna_version=int(r["dna_version"]),
                    study_id=r["study_id"],
                    source=r["source"],
                    sample_size=int(r["sample_size"]),
                    effect_size=float(r["effect_size"]),
                    confidence=float(r["confidence"]),
                    regime=r["regime"],
                    sector=r["sector"],
                    p_value=float(r["p_value"]) if r["p_value"] is not None else None,
                    ci_low=float(r["ci_low"]) if r["ci_low"] is not None else None,
                    ci_high=float(r["ci_high"]) if r["ci_high"] is not None else None,
                    observation_date=r["observation_date"],
                    created_at=r["created_at"],
                    metadata=json.loads(r["metadata"]),
                )
                for r in rows
            ]
        finally:
            conn.close()

    def contexts(self, dna_id: str) -> List[DNAContext]:
        """
        Return all DNAContext snapshots for a DNA id.

        Returns empty list if none have been recorded.
        """
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM dna_context WHERE dna_id = ? ORDER BY id ASC",
                (dna_id,),
            ).fetchall()
            return [
                DNAContext(
                    id=int(r["id"]),
                    dna_id=r["dna_id"],
                    dna_version=int(r["dna_version"]),
                    regime=r["regime"],
                    volatility=float(r["volatility"]),
                    breadth=float(r["breadth"]),
                    sector=float(r["sector"]),
                    liquidity=float(r["liquidity"]),
                    institutional=float(r["institutional"]),
                    historical_similarity=float(r["historical_similarity"]),
                    context_date=r["context_date"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def search(
        self,
        feature_name: Optional[str] = None,
        category: Optional[str] = None,
        lifecycle: Optional[str] = None,
        min_confidence: Optional[float] = None,
        min_consensus: Optional[float] = None,
    ) -> List[InstitutionalDNA]:
        """
        Search the repository with optional filters.

        Returns only the latest (is_current=1) version of each matching DNA.
        All filters are ANDed.
        """
        conn = self._conn()
        try:
            clauses = ["is_current = 1"]
            params: List[Any] = []
            if feature_name is not None:
                clauses.append("feature_name = ?")
                params.append(feature_name)
            if category is not None:
                clauses.append("category = ?")
                params.append(category)
            if lifecycle is not None:
                clauses.append("lifecycle = ?")
                params.append(lifecycle)
            if min_confidence is not None:
                clauses.append("confidence >= ?")
                params.append(float(min_confidence))
            if min_consensus is not None:
                clauses.append("consensus_score >= ?")
                params.append(float(min_consensus))
            sql = "SELECT * FROM dna WHERE " + " AND ".join(clauses)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dna(r) for r in rows]
        finally:
            conn.close()

    def list_active(self) -> List[InstitutionalDNA]:
        """Return all active (non-RETIRED) DNA records.  Latest versions only."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM dna WHERE is_current = 1 AND lifecycle != 'RETIRED'"
            ).fetchall()
            return [self._row_to_dna(r) for r in rows]
        finally:
            conn.close()

    def list_retired(self) -> List[InstitutionalDNA]:
        """Return all RETIRED DNA records.  Latest versions only."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM dna WHERE is_current = 1 AND lifecycle = 'RETIRED'"
            ).fetchall()
            return [self._row_to_dna(r) for r in rows]
        finally:
            conn.close()

    def audit_log(self, dna_id: str) -> List[Dict[str, Any]]:
        """
        Return all audit_log entries for a DNA id.

        Each entry contains: operation, version_before, version_after,
        operator, study_id, reason, timestamp.
        """
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE dna_id = ? ORDER BY id ASC",
                (dna_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def statistics(self) -> DNARepositoryStatistics:
        """Compute and return aggregate repository statistics."""
        conn = self._conn()
        try:
            def _count(sql: str, *args: Any) -> int:
                return int(conn.execute(sql, args).fetchone()[0] or 0)

            def _avg(sql: str, *args: Any) -> float:
                v = conn.execute(sql, args).fetchone()[0]
                return float(v) if v is not None else 0.0

            total_dna   = _count("SELECT COUNT(DISTINCT id) FROM dna")
            active_dna  = _count("SELECT COUNT(*) FROM dna WHERE is_current=1 AND lifecycle!='RETIRED'")
            retired_dna = _count("SELECT COUNT(*) FROM dna WHERE is_current=1 AND lifecycle='RETIRED'")
            instit_dna  = _count("SELECT COUNT(*) FROM dna WHERE is_current=1 AND lifecycle='INSTITUTIONAL'")
            weak_dna    = _count("SELECT COUNT(*) FROM dna WHERE is_current=1 AND lifecycle='WEAKENING'")
            drift_dna   = _count("SELECT COUNT(*) FROM dna WHERE is_current=1 AND lifecycle='DRIFTING'")
            total_ev    = _count("SELECT COUNT(*) FROM dna_evidence")
            total_hist  = _count("SELECT COUNT(*) FROM dna_history")
            total_ver   = _count("SELECT COUNT(*) FROM dna")
            avg_conf    = _avg("SELECT AVG(confidence) FROM dna WHERE is_current=1")
            avg_cons    = _avg("SELECT AVG(consensus_score) FROM dna WHERE is_current=1")
            sv_row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            sv = int(sv_row[0]) if sv_row and sv_row[0] is not None else self.SCHEMA_VERSION
            lu_row = conn.execute("SELECT MAX(updated_at) FROM dna WHERE is_current=1").fetchone()
            last_updated = lu_row[0] if lu_row and lu_row[0] else _now()
            db_size = int(self._db_path.stat().st_size) if self._db_path.exists() else 0
            return DNARepositoryStatistics(
                total_dna=total_dna,
                active_dna=active_dna,
                retired_dna=retired_dna,
                institutional_dna=instit_dna,
                weakening_dna=weak_dna,
                drifting_dna=drift_dna,
                total_evidence=total_ev,
                total_history_points=total_hist,
                total_versions=total_ver,
                avg_confidence=avg_conf,
                avg_consensus_score=avg_cons,
                schema_version=sv,
                last_updated=last_updated,
                db_size_bytes=db_size,
            )
        finally:
            conn.close()

    # ── maintenance ───────────────────────────────────────────────────────────

    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create an online backup of the repository database.

        Uses SQLite's native online backup API (safe during active use).
        Returns the path of the created backup file.
        """
        if backup_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._db_path.parent / f"institutional_dna_backup_{ts}.db"
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        src = self._conn()
        try:
            dst = sqlite3.connect(str(backup_path))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        log.info("IDR backup created: %s", backup_path)
        return backup_path

    def verify_integrity(self) -> bool:
        """
        Run SQLite PRAGMA integrity_check.

        Returns True if the database passes all integrity checks.
        Raises IDRIntegrityError if a problem is detected.
        """
        conn = self._conn()
        try:
            rows = conn.execute("PRAGMA integrity_check").fetchall()
            if len(rows) == 1 and rows[0][0] == "ok":
                return True
            issues = [r[0] for r in rows]
            raise IDRIntegrityError(f"Integrity check failed: {issues}")
        finally:
            conn.close()

    @property
    def db_path(self) -> Path:
        return self._db_path

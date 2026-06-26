"""
oios/db/migrations.py
Creates OIOS schema. Safe to run multiple times (all DDL uses IF NOT EXISTS).
"""

import logging
from .connection import get_connection
from .schema import (
    PHASE_A0_DDL, PHASE_A_DDL, PHASE_B_DDL, PHASE_C_DDL, PHASE_D_DDL,
    PHASE_E0_DDL, PHASE_E1_DDL, PHASE_F_DDL,
)

log = logging.getLogger(__name__)


def _run_ddl(conn, ddl_list: list[str], label: str) -> None:
    with conn:
        for statement in ddl_list:
            conn.execute(statement)
    log.info("[OIOS] %s schema applied.", label)


def apply_phase_a0(conn=None) -> None:
    """
    Create all Phase A0 tables and indexes.
    If conn is provided, uses it (useful for test isolation with :memory: databases).
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0")
    finally:
        if _owns_conn:
            conn.close()


def apply_phase_a(conn=None) -> None:
    """
    Create all Phase A tables on top of Phase A0.
    Applies Phase A0 first (idempotent), then Phase A additions.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL, "Phase A")
    finally:
        if _owns_conn:
            conn.close()


def apply_phase_b(conn=None) -> None:
    """
    Create all Phase B tables on top of Phase A.
    Applies Phase A0 + Phase A first (idempotent), then Phase B additions.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL, "Phase A (idempotent)")
        _run_ddl(conn, PHASE_B_DDL, "Phase B")
    finally:
        if _owns_conn:
            conn.close()


def apply_phase_c(conn=None) -> None:
    """
    Create all Phase C tables on top of Phase B.
    Applies Phase A0 + A + B first (idempotent), then Phase C additions.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL, "Phase A (idempotent)")
        _run_ddl(conn, PHASE_B_DDL, "Phase B (idempotent)")
        _run_ddl(conn, PHASE_C_DDL, "Phase C")
    finally:
        if _owns_conn:
            conn.close()


def apply_phase_d(conn=None) -> None:
    """
    Create all Phase D tables on top of Phase C.
    Applies Phase A0 + A + B + C first (idempotent), then Phase D additions.

    Phase D tables:
      - archetype_outcome_distributions   (weekly recomputed by outcome_distributor)
      - opportunity_re_snapshots          (daily RE trajectory; gates D-Ready-2)
      - opportunity_daily_state_snapshot  (daily state concentration; gates D-Ready-5)
      - transition_probability_cache      (Markov priors + empirical per archetype/regime)

    Shadow mode discipline: apply_phase_d() only creates tables.
    Whether SHADOW_MODE is on/off is controlled by oios.engine.shadow_mode — not here.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL, "Phase A (idempotent)")
        _run_ddl(conn, PHASE_B_DDL, "Phase B (idempotent)")
        _run_ddl(conn, PHASE_C_DDL, "Phase C (idempotent)")
        _run_ddl(conn, PHASE_D_DDL, "Phase D")
    finally:
        if _owns_conn:
            conn.close()


def apply_phase_e0(conn=None) -> None:
    """
    Create all Phase E0 tables on top of Phase D.
    Phase E0: Knowledge Graph — daily_events, company_relationships,
    knowledge_graph_metadata, event_entity_links.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL,  "Phase A (idempotent)")
        _run_ddl(conn, PHASE_B_DDL,  "Phase B (idempotent)")
        _run_ddl(conn, PHASE_C_DDL,  "Phase C (idempotent)")
        _run_ddl(conn, PHASE_D_DDL,  "Phase D (idempotent)")
        _run_ddl(conn, PHASE_E0_DDL, "Phase E0")
    finally:
        if _owns_conn:
            conn.close()


def apply_phase_e1(conn=None) -> None:
    """
    Create all Phase E1 tables on top of Phase E0.
    Phase E1 (Shadow Mode): Cause + Propagation engines.
    Tables: opportunity_causes, cause_scores, propagation_paths,
    propagation_scores, shadow_cause_outcomes.

    Shadow mode discipline: this function only creates tables.
    E1 engines observe and record — they never modify OS, RE, TTL,
    conviction, or state transitions until E-Ready gates pass.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL,  "Phase A (idempotent)")
        _run_ddl(conn, PHASE_B_DDL,  "Phase B (idempotent)")
        _run_ddl(conn, PHASE_C_DDL,  "Phase C (idempotent)")
        _run_ddl(conn, PHASE_D_DDL,  "Phase D (idempotent)")
        _run_ddl(conn, PHASE_E0_DDL, "Phase E0 (idempotent)")
        _run_ddl(conn, PHASE_E1_DDL, "Phase E1")
    finally:
        if _owns_conn:
            conn.close()


def _add_column_if_missing(
    conn: "sqlite3.Connection",
    table: str,
    column: str,
    col_type: str,
) -> None:
    """Idempotent ALTER TABLE ADD COLUMN — no-op if column already exists."""
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        log.info("[Migration] Added column %s.%s (%s).", table, column, col_type)


def apply_phase_f(conn=None) -> None:
    """
    Create all Phase F tables on top of Phase E1.
    Phase F: Market Research Engine — read-only from A–E, research-only.

    Tables:
      - market_leaders_daily       daily top-15 winners + losers
      - market_leader_features     12-feature store per leader
      - market_leader_outcomes     multi-horizon return tracking
      - market_research_controls   control group (similar non-winners)
      - failure_attribution        candidate failure reasons

    Isolation contract: Phase F tables have NO foreign keys into A–E tables.
    Phase F services never INSERT/UPDATE/DELETE any A–E table.
    """
    _owns_conn = conn is None
    if _owns_conn:
        conn = get_connection()
    try:
        _run_ddl(conn, PHASE_A0_DDL, "Phase A0 (idempotent)")
        _run_ddl(conn, PHASE_A_DDL,  "Phase A (idempotent)")
        _run_ddl(conn, PHASE_B_DDL,  "Phase B (idempotent)")
        _run_ddl(conn, PHASE_C_DDL,  "Phase C (idempotent)")
        _run_ddl(conn, PHASE_D_DDL,  "Phase D (idempotent)")
        _run_ddl(conn, PHASE_E0_DDL, "Phase E0 (idempotent)")
        _run_ddl(conn, PHASE_E1_DDL, "Phase E1 (idempotent)")
        _run_ddl(conn, PHASE_F_DDL,  "Phase F")
        # Column migrations for existing databases (idempotent — no-op if column exists)
        with conn:
            _add_column_if_missing(conn, "market_leader_features", "updated_at", "TEXT")
    finally:
        if _owns_conn:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    apply_phase_f()
    print("Phase F schema created.")

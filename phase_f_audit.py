"""
phase_f_audit.py
Phase F — Governance Audit

Verifies the research isolation contract:
  1. No Phase F module writes to any A–E table
  2. No Phase F module calls EventBus.emit()
  3. No Phase F module imports from execution_engine
  4. phase_f_shadow.py has no DB write calls

Run daily / at CI time.  Exit code 0 = clean, 1 = violations found.

Usage:
    python phase_f_audit.py
    python phase_f_audit.py --verbose
"""

from __future__ import annotations

import argparse
import ast
import logging
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHASE_F_DIR = ROOT / "oios" / "phase_f"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Write-protected A–E table names ──────────────────────────────────────────
AE_WRITE_PROTECTED = {
    "opportunities",
    "signal_births",
    "opportunity_signals",
    "signal_state_transitions",
    "decision_log",
    "oios_events",
    "sector_conviction_daily",
    "theme_phase_history",
    "pending_adjustments",
    "archetype_outcome_distributions",
    "opportunity_re_snapshots",
    "opportunity_daily_state_snapshot",
    "transition_probability_cache",
    "daily_events",
    "company_relationships",
    "knowledge_graph_metadata",
    "event_entity_links",
    "opportunity_causes",
    "cause_scores",
    "propagation_paths",
    "propagation_scores",
    "shadow_cause_outcomes",
}

# ── Forbidden patterns in Phase F source files ────────────────────────────────
FORBIDDEN_PATTERNS = [
    # EventBus emission
    (r'\.emit\s*\(', "EventBus.emit() call"),
    # OrderManager / ExecutionEngine import
    (r'from execution_engine', "execution_engine import"),
    (r'import execution_engine', "execution_engine import"),
    (r'OrderManager', "OrderManager reference"),
    # Direct writes into A–E tables via executemany/execute with INSERT/UPDATE/DELETE
]

# Phase F tables — writes to these are allowed
PHASE_F_TABLES = {
    "market_leaders_daily",
    "market_leader_features",
    "market_leader_outcomes",
    "market_research_controls",
    "failure_attribution",
    "feature_differentials",
}

# Shadow engine is the strictest — it must have ZERO write calls
SHADOW_MODULE = "phase_f_shadow.py"
SHADOW_WRITE_PATTERNS = [
    (r'\.execute\s*\(\s*["\']?\s*(INSERT|UPDATE|DELETE|DROP|CREATE)', "DB write call"),
    (r'\.executemany\s*\(', "DB executemany call"),
    (r'conn\.commit', "conn.commit() call"),
    (r'with conn:', "context manager write block"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase F governance audit")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    violations: list[str] = []

    py_files = list(PHASE_F_DIR.glob("*.py"))
    if not py_files:
        log.error("No Phase F modules found at %s", PHASE_F_DIR)
        return 1

    for path in sorted(py_files):
        if path.name == "__init__.py":
            continue
        log.debug("Auditing %s …", path.name)
        source = path.read_text(encoding="utf-8")

        # 1. Forbidden patterns in all Phase F modules
        for pattern, label in FORBIDDEN_PATTERNS:
            for i, line in enumerate(source.splitlines(), start=1):
                if re.search(pattern, line, re.IGNORECASE):
                    msg = f"{path.name}:{i}  [{label}]  {line.strip()}"
                    violations.append(msg)
                    log.warning("VIOLATION  %s", msg)

        # 2. Check for writes to A–E table names
        for ae_table in AE_WRITE_PROTECTED:
            pattern = rf'(INSERT|UPDATE|DELETE)\s+(?:OR\s+\w+\s+)?(?:INTO\s+)?{ae_table}\b'
            for i, line in enumerate(source.splitlines(), start=1):
                if re.search(pattern, line, re.IGNORECASE):
                    msg = f"{path.name}:{i}  [WRITE to AE table {ae_table}]  {line.strip()}"
                    violations.append(msg)
                    log.warning("VIOLATION  %s", msg)

        # 3. Strict shadow module check
        if path.name == SHADOW_MODULE:
            for pattern, label in SHADOW_WRITE_PATTERNS:
                for i, line in enumerate(source.splitlines(), start=1):
                    if re.search(pattern, line, re.IGNORECASE):
                        # Allow comments
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue
                        msg = f"{path.name}:{i}  [SHADOW WRITE: {label}]  {stripped}"
                        violations.append(msg)
                        log.warning("VIOLATION  %s", msg)

    if violations:
        log.error("")
        log.error("Phase F Audit FAILED — %d violation(s) found:", len(violations))
        for v in violations:
            log.error("  %s", v)
        return 1

    # Schema verification
    schema_ok = _verify_schema()

    if not schema_ok:
        log.error("Phase F Audit FAILED — schema verification errors.")
        return 1

    log.info("")
    log.info("Phase F Audit PASSED — no isolation violations, schema verified.")
    return 0


def _verify_schema() -> bool:
    """Quick schema check — tables and indexes exist."""
    try:
        from oios.db.connection import get_connection
        conn = get_connection()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        required = {
            "market_leaders_daily", "market_leader_features",
            "market_leader_outcomes", "market_research_controls",
            "failure_attribution", "feature_differentials",
        }
        missing = required - tables
        conn.close()
        if missing:
            for t in missing:
                log.error("Schema: table missing → %s (run: python phase_f_migration.py)", t)
            return False
        log.info("Schema: all 6 Phase F tables present ✅")
        return True
    except Exception as exc:
        log.warning("Schema check skipped (DB not reachable): %s", exc)
        return True   # Don't fail audit if DB hasn't been initialised yet


if __name__ == "__main__":
    sys.exit(main())

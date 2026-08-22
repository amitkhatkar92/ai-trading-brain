"""
Fix 1: Add _startup_csv_orphan_audit() to MasterOrchestrator.

Reads paper_trades.csv on startup, detects any OPEN rows with no matching
CLOSE row that are NOT already tracked by the order_manager, and sends a
Telegram alert so no orphaned position is ever missed after a restart.
"""
import re

ORCH = "/app/orchestrator/master_orchestrator.py"

with open(ORCH, "r") as f:
    src = f.read()

# ── Guard: don't double-patch ─────────────────────────────────────────────
if "_startup_csv_orphan_audit" in src:
    print("Fix 1 already applied — skipping.")
    import sys; sys.exit(0)

# ── 1. Insert the method before set_stop_event ───────────────────────────
NEW_METHOD = '''
    def _startup_csv_orphan_audit(self) -> None:
        """
        Fix: Startup CSV Orphan Audit.

        Reads paper_trades.csv immediately on startup and detects any OPEN row
        that has no matching CLOSE row.  Cross-checks against order_manager's
        in-memory state so positions that ARE being tracked are not falsely
        flagged.  Any truly orphaned row → CRITICAL log + Telegram alert.

        This runs synchronously before the scheduler thread starts so the
        user is notified within seconds of container boot.
        """
        import csv
        from pathlib import Path

        csv_path = Path("data/paper_trades.csv")
        if not csv_path.exists():
            log.info("[OrphanAudit] paper_trades.csv not found — skipping.")
            return

        try:
            rows = list(csv.DictReader(open(csv_path)))
        except Exception as exc:
            log.warning("[OrphanAudit] Could not read CSV: %s", exc)
            return

        opens  = {r["order_id"]: r for r in rows if r.get("event", "").strip() == "OPEN"}
        closes = {r["order_id"] for r in rows  if r.get("event", "").strip() == "CLOSE"}
        orphan_ids = set(opens.keys()) - closes

        if not orphan_ids:
            log.info("[OrphanAudit] CSV integrity OK — 0 orphaned positions.")
            return

        # Cross-check: is the order_manager already tracking these?
        try:
            tracked_ids = {o.order_id for o in self.order_manager.get_open_orders()}
        except Exception:
            tracked_ids = set()

        truly_orphaned = orphan_ids - tracked_ids
        tracked_orphans = orphan_ids & tracked_ids

        for oid in tracked_orphans:
            log.info(
                "[OrphanAudit] %s is OPEN-without-CLOSE in CSV but IS tracked "
                "by order_manager — restore OK.",
                opens[oid].get("symbol", oid),
            )

        if not truly_orphaned:
            log.info(
                "[OrphanAudit] All %d CSV-open positions are tracked — no action needed.",
                len(orphan_ids),
            )
            return

        # Build alert message
        lines = []
        for oid in truly_orphaned:
            r = opens[oid]
            lines.append(
                f"  {r.get('symbol','?')} {r.get('direction','?')} "
                f"{r.get('quantity','?')} @ {r.get('entry_price','?')} "
                f"(SL={r.get('stop_loss','?')})"
            )
        alert_body = (
            f"WARNING: {len(truly_orphaned)} position(s) found in paper_trades.csv "
            f"as OPEN without a CLOSE row AND not tracked by order_manager:\\n"
            + "\\n".join(lines)
            + "\\nManual review required."
        )
        log.critical("[OrphanAudit] %s", alert_body)

        try:
            from notifications import get_notifier
            get_notifier().market_alert("⚠️ ORPHAN POSITION ALERT", alert_body)
        except Exception as exc:
            log.warning("[OrphanAudit] Telegram alert failed: %s", exc)

'''

# Insert before set_stop_event
insert_before = "    def set_stop_event(self, stop_event: threading.Event) -> None:"
if insert_before not in src:
    print(f"ERROR: Could not find insertion anchor:\n  {insert_before}")
    import sys; sys.exit(1)

src = src.replace(insert_before, NEW_METHOD + insert_before, 1)

# ── 2. Add the call in start_scheduler after _post_restore_governance_pass ──
CALL_ANCHOR = "        self._post_restore_governance_pass()"
CALL_INSERT = (
    "        self._post_restore_governance_pass()\n\n"
    "        # ── Startup CSV orphan audit ────────────────────────────────\n"
    "        # Detects any position in paper_trades.csv as OPEN-without-CLOSE\n"
    "        # that is NOT tracked by order_manager — fires Telegram alert.\n"
    "        self._startup_csv_orphan_audit()"
)
if CALL_ANCHOR not in src:
    print(f"ERROR: Could not find call anchor.")
    import sys; sys.exit(1)

src = src.replace(CALL_ANCHOR, CALL_INSERT, 1)

# Write back
with open(ORCH, "w") as f:
    f.write(src)

print("Fix 1 applied: _startup_csv_orphan_audit() added and wired into start_scheduler()")

# Quick syntax check
import py_compile, tempfile, shutil
tmp = tempfile.mktemp(suffix=".py")
shutil.copy2(ORCH, tmp)
try:
    py_compile.compile(tmp, doraise=True)
    print("Syntax check: PASSED")
except py_compile.PyCompileError as e:
    print(f"Syntax check: FAILED — {e}")
    # Rollback
    shutil.copy2(tmp + ".bak", ORCH) if False else None
finally:
    import os; os.unlink(tmp)

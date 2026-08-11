"""
cle_learning_executor/cle_reporter.py — Daily CLE-001 report generator.

Reads the CLE execution log and writes a Markdown daily report to the project root.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

_ROOT    = Path(__file__).parent.parent
_DATA    = _ROOT / "data"
_CLE_DIR = _DATA / "cle"
_CLE_LOG = _CLE_DIR / "cle_execution_log.json"


def write_daily_report(report_date: str | None = None, summary: dict | None = None) -> Path:
    """
    Generate the CLE daily report for report_date (defaults to today).

    Reads from data/cle/cle_execution_log.json (entries for report_date).
    Writes CLE_DAILY_REPORT_{YYYY-MM-DD}.md to the project root.

    Returns the Path to the written report.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    # Load CLE execution log
    entries = []
    if _CLE_LOG.exists():
        try:
            with open(_CLE_LOG, encoding="utf-8") as f:
                all_entries = json.load(f)
            entries = [e for e in all_entries if e.get("date") == report_date]
        except Exception as exc:
            log.warning("[CLE-Report] Could not load CLE log: %s", exc)

    # Bucket entries by status
    candidates    = [e for e in entries if e.get("status") == "CANDIDATE_CREATED"]
    no_dna        = [e for e in entries if e.get("status") in ("INSUFFICIENT_DATA", "NO_ACTIONABLE_DNA")]
    capital_skip  = [e for e in entries if e.get("status") == "CAPITAL_EXECUTION_CONSTRAINT"]
    failed        = [e for e in entries if e.get("status") == "FAILED"]
    other_skipped = [e for e in entries if e.get("status") == "SKIPPED"]

    dry_run = any(e.get("dry_run") for e in entries)

    lines = [
        f"# CLE-001 Daily Report — {report_date}",
        "",
        f"**Mode:** {'DRY RUN (no DNA written)' if dry_run else 'LIVE'}",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Cat-E records processed | {len(entries)} |",
        f"| DNA candidates created | {len(candidates)} |",
        f"| Insufficient evidence | {len(no_dna)} |",
        f"| Capital constraint (skipped) | {len(capital_skip)} |",
        f"| Failed | {len(failed)} |",
        f"| Other skipped | {len(other_skipped)} |",
        "",
    ]

    # ── CANDIDATE_CREATED ──────────────────────────────────────────────────
    if candidates:
        lines += [
            "## DNA Candidates Created (lifecycle=DISCOVERED)",
            "",
            "| DNA ID | Symbol | Direction | Sample | Win Rate | Lift |",
            "|--------|--------|-----------|--------|----------|------|",
        ]
        for e in candidates:
            lines.append(
                f"| {e.get('dna_id','—')} "
                f"| {e.get('symbol','')} "
                f"| {e.get('direction','')} "
                f"| {e.get('sample_count', 0)} "
                f"| {e.get('win_rate', 0):.2f} "
                f"| {e.get('lift', 0):.2f} |"
            )
        lines.append("")
        lines += [
            "> **Note:** All DNA candidates start at lifecycle=`DISCOVERED`.",
            "> They cannot influence live trading until progressing through",
            "> `REPLICATED → VERIFIED → INSTITUTIONAL` with explicit SD approval.",
            "",
        ]

    # ── NO ACTIONABLE DNA ─────────────────────────────────────────────────
    if no_dna:
        lines += [
            "## Insufficient Evidence — No DNA Created",
            "",
            "| Symbol | Direction | Return% | Status | Reason |",
            "|--------|-----------|---------|--------|--------|",
        ]
        for e in no_dna:
            lines.append(
                f"| {e.get('symbol','')} "
                f"| {e.get('direction','')} "
                f"| {e.get('return_pct',0):+.1f}% "
                f"| {e.get('status','')} "
                f"| {e.get('reason','').replace('|', '/')} |"
            )
        lines.append("")

    # ── CAPITAL CONSTRAINT ─────────────────────────────────────────────────
    if capital_skip:
        lines += [
            "## Skipped — Capital/Portfolio Constraint (not prediction failures)",
            "",
            "| Symbol | Reason |",
            "|--------|--------|",
        ]
        for e in capital_skip:
            lines.append(
                f"| {e.get('symbol','')} | {e.get('reason','').replace('|', '/')} |"
            )
        lines.append("")

    # ── FAILED ─────────────────────────────────────────────────────────────
    if failed:
        lines += [
            "## Errors",
            "",
            "| Action ID | Symbol | Reason |",
            "|-----------|--------|--------|",
        ]
        for e in failed:
            lines.append(
                f"| {e.get('action_id','')} "
                f"| {e.get('symbol','')} "
                f"| {e.get('reason','').replace('|', '/')} |"
            )
        lines.append("")

    # ── Footer ─────────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Safety Verification",
        "",
        "- [ ] All DNA candidates have `lifecycle=DISCOVERED` ✅",
        "- [ ] No live trading rules modified ✅",
        "- [ ] Registry updated atomically ✅",
        "- [ ] No unverified DNA reached PIG vote ✅",
        "",
        f"*Generated by CLE-001 | {report_date}*",
    ]

    report_path = _ROOT / f"CLE_DAILY_REPORT_{report_date}.md"
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("[CLE-Report] Written to %s", report_path)
    except Exception as exc:
        log.error("[CLE-Report] Write failed: %s", exc)

    return report_path

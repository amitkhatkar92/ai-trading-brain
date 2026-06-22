"""
oios/reporting/runner.py

EOD and weekly report runner.

Usage:
    from oios.reporting.runner import run_eod, run_weekly

    # Daily after market close
    paths = run_eod("data/market_behavior.db", "2026-06-16", "reports/")

    # Saturday weekly
    path = run_weekly("data/market_behavior.db", "2026-06-14", "reports/")

All database access is read-only (SELECT only).
No writes to the database. Reports written to files only.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database connection (read-only)
# ---------------------------------------------------------------------------

def _open_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    return conn


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _report_dir(output_root: str | Path, report_date: str) -> Path:
    d = Path(output_root) / report_date
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    log.info("Report written: %s", path)


# ---------------------------------------------------------------------------
# EOD runner — 5 reports
# ---------------------------------------------------------------------------

EOD_REPORTS = [
    ("01_data_health",    "data_health",    "generate_data_health_report"),
    ("02_oios_activity",  "oios_activity",  "generate_oios_activity_report"),
    ("03_phase_d_shadow", "phase_d_shadow", "generate_phase_d_shadow_report"),
    ("04_phase_e_shadow", "phase_e_shadow", "generate_phase_e_shadow_report"),
    ("05_readiness_gates","readiness_gates","generate_readiness_gate_summary"),
]


def run_eod(
    db_path: str | Path,
    report_date: str | None = None,
    output_root: str | Path = "reports",
) -> list[Path]:
    """
    Generate all 5 EOD reports for report_date (default: today).
    Returns list of paths to generated report files.
    Shadow mode: reads only. No DB writes.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    out_dir = _report_dir(output_root, report_date)
    conn = _open_db(str(db_path))
    generated: list[Path] = []

    try:
        for filename, module_name, fn_name in EOD_REPORTS:
            try:
                import importlib
                mod = importlib.import_module(f"oios.reporting.{module_name}")
                fn  = getattr(mod, fn_name)
                content = fn(conn, report_date)
                path = out_dir / f"{filename}.txt"
                _write(path, content)
                generated.append(path)
                print(f"  ✓  {path.name}")
            except Exception as e:
                log.error("Failed to generate %s: %s", filename, e)
                err_path = out_dir / f"{filename}.ERROR.txt"
                err_path.write_text(
                    f"REPORT GENERATION ERROR\n{filename}\n{report_date}\n\n{e}\n",
                    encoding="utf-8",
                )
                generated.append(err_path)
                print(f"  ✗  {filename}: {e}")
    finally:
        conn.close()

    # Write a manifest
    manifest_path = out_dir / "00_manifest.txt"
    manifest_lines = [
        f"OIOS EOD Report Manifest",
        f"Date: {report_date}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Reports: {len(generated)}",
        "",
    ] + [f"  {p.name}" for p in generated]
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    print(f"\nEOD reports → {out_dir}  ({len(generated)} files)")
    return generated


# ---------------------------------------------------------------------------
# Weekly runner — 1 combined report
# ---------------------------------------------------------------------------

def run_weekly(
    db_path: str | Path,
    week_end_date: str | None = None,
    output_root: str | Path = "reports",
) -> Path:
    """
    Generate the weekly report for the week ending on week_end_date.
    Default: today (intended to run on Saturday).
    Returns path to the generated report file.
    Shadow mode: reads only. No DB writes.
    """
    if week_end_date is None:
        week_end_date = date.today().isoformat()

    out_dir = _report_dir(output_root, week_end_date)
    conn = _open_db(str(db_path))

    try:
        from oios.reporting.weekly_report import generate_weekly_report
        content = generate_weekly_report(conn, week_end_date)
        path = out_dir / "06_weekly_report.txt"
        _write(path, content)
        print(f"  ✓  {path}")
        return path
    except Exception as e:
        log.error("Failed to generate weekly report: %s", e)
        err_path = out_dir / "06_weekly_report.ERROR.txt"
        err_path.write_text(
            f"WEEKLY REPORT GENERATION ERROR\n{week_end_date}\n\n{e}\n",
            encoding="utf-8",
        )
        print(f"  ✗  weekly_report: {e}")
        return err_path
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Combined: EOD + weekly on Saturdays
# ---------------------------------------------------------------------------

def run_full_eod(
    db_path: str | Path,
    report_date: str | None = None,
    output_root: str | Path = "reports",
) -> list[Path]:
    """
    Run EOD reports. If today is Saturday (weekday=5), also run weekly report.
    Returns all generated paths.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    print(f"\n{'=' * 60}")
    print(f"  OIOS EOD Reporting — {report_date}")
    print(f"{'=' * 60}")

    all_paths = run_eod(db_path, report_date, output_root)

    day_of_week = date.fromisoformat(report_date).weekday()  # 5 = Saturday
    if day_of_week == 5:
        print(f"\n  Saturday detected — running weekly report...")
        weekly_path = run_weekly(db_path, report_date, output_root)
        all_paths.append(weekly_path)

    print(f"\n  Total files: {len(all_paths)}")
    return all_paths

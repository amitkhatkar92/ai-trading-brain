"""
live_operations/report_writer.py
==================================
Shared markdown writing utilities for LOL-001 reports.
Extends oios/reporting/base.py conventions.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .lol_config import LOL_DIR

IST = timezone(timedelta(hours=5, minutes=30))

WIDTH = 72

# ── Formatting primitives ─────────────────────────────────────────────────

def hr(char: str = "=") -> str:
    return char * WIDTH


def section(title: str) -> str:
    return f"\n{title}\n{'-' * len(title)}"


def kv(label: str, value: Any, lw: int = 40) -> str:
    return f"  {label:<{lw}} {value}"


def kv_warn(label: str, value: Any, lw: int = 40) -> str:
    return f"  ⚠  {label:<{lw-3}} {value}"


def kv_fail(label: str, value: Any, lw: int = 40) -> str:
    return f"  ✗  {label:<{lw-3}} {value}"


def kv_ok(label: str, value: Any, lw: int = 40) -> str:
    return f"  ✓  {label:<{lw-3}} {value}"


def badge(status: str) -> str:
    """Return a text badge for READY/NOT_READY/BLOCKED/GO/NO-GO/PASS/FAIL."""
    mapping = {
        "READY":       "[ READY ]",
        "NOT_READY":   "[ NOT READY ]",
        "BLOCKED":     "[ BLOCKED ]",
        "GO":          "[ GO ]",
        "GO_OBS":      "[ GO WITH OBSERVATIONS ]",
        "NO_GO":       "[ NO GO ]",
        "PASS":        "[ PASS ]",
        "WARN":        "[ WARN ]",
        "FAIL":        "[ FAIL ]",
        "HEALTHY":     "[ HEALTHY ]",
        "DEGRADED":    "[ DEGRADED ]",
        "INCIDENT":    "[ INCIDENT ]",
        "CLEAR":       "[ CLEAR ]",
    }
    return mapping.get(status.upper(), f"[{status}]")


def now_ist_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def report_header(title: str, report_date: str, subtitle: str = "") -> str:
    lines = [
        hr(),
        f"  {title}",
        f"  Date: {report_date}",
        f"  Generated: {now_ist_str()}",
    ]
    if subtitle:
        lines.append(f"  {subtitle}")
    lines.append(hr())
    return "\n".join(lines)


# ── File I/O ──────────────────────────────────────────────────────────────

def get_report_dir(report_date: str) -> Path:
    d = LOL_DIR / report_date
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_report(filename: str, content: str, report_date: str) -> Path:
    path = get_report_dir(report_date) / filename
    path.write_text(content, encoding="utf-8")
    return path


def append_report(filename: str, content: str, report_date: str) -> Path:
    path = get_report_dir(report_date) / filename
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)
    return path

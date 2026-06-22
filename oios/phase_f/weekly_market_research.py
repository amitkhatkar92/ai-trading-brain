"""
oios/phase_f/weekly_market_research.py
Phase F Step F5.1 — Weekly Research Report Generator

Produces a plain-text / Markdown research report for a given week ending date.

Report sections:
  1. Winners — top common features among WINNER rows
  2. Losers  — top common features among LOSER rows
  3. Controls — why similar stocks failed (failure attribution summary)
  4. Persistence — outcome class breakdown at 1D/3D/5D/10D/20D horizons

ISOLATION CONTRACT
------------------
Reads only: market_leaders_daily, market_leader_features,
            market_leader_outcomes, market_research_controls,
            failure_attribution
Writes: nothing (report is returned as a string; caller decides where to send)
"""

from __future__ import annotations

import logging
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# Top N features to report per section
TOP_N_FEATURES = 5

# Persistence threshold for reporting
HORIZON_WIN_THRESHOLD = 0.0   # return > 0 counted as "positive"


def generate_weekly_report(week_ending: str, conn: sqlite3.Connection) -> str:
    """
    Generate and return the weekly research report as a Markdown string.

    Parameters
    ----------
    week_ending : str
        ISO-8601 YYYY-MM-DD (typically Friday).
    conn : sqlite3.Connection
        OIOS DB connection.

    Returns
    -------
    str
        Full Markdown report.
    """
    week_start = _date_minus_n(week_ending, 6)

    winners  = _get_leaders("WINNER", week_start, week_ending, conn)
    losers   = _get_leaders("LOSER",  week_start, week_ending, conn)

    lines = [
        f"# Market Research Report",
        f"**Week:** {week_start} → {week_ending}",
        f"**Generated:** {_now_ts()}",
        "",
    ]

    lines += _section_leaders("Winners", winners, conn)
    lines += _section_leaders("Losers",  losers,  conn)
    lines += _section_controls(week_start, week_ending, conn)
    lines += _section_persistence(week_start, week_ending, conn)

    report = "\n".join(lines)
    log.info("[WeeklyResearch] Report generated for week ending %s (%d chars)",
             week_ending, len(report))
    return report


# ── Section builders ──────────────────────────────────────────────────────────

def _section_leaders(title: str, leaders: list[dict], conn: sqlite3.Connection) -> list[str]:
    lines = [f"## {title}", ""]
    if not leaders:
        lines += [f"*No {title.lower()} data for this week.*", ""]
        return lines

    leader_type = leaders[0]["leader_type"]
    sectors = Counter(l["sector"] for l in leaders)
    lines.append(f"**Total captured:** {len(leaders)} across {len(sectors)} sectors")
    lines.append("")

    # Common features
    lines.append("### Top Common Features")
    lines.append("")
    features = _aggregate_features(leaders, conn)
    if features:
        lines.append("| Feature | Avg Value | Pct Present |")
        lines.append("|---|---|---|")
        for feat, avg, pct in features[:TOP_N_FEATURES]:
            lines.append(f"| {feat} | {avg:.2f} | {pct:.0%} |")
    else:
        lines.append("*Feature data not yet available.*")
    lines.append("")

    # Sector distribution
    lines.append("### Sector Concentration")
    lines.append("")
    for sec, cnt in sectors.most_common(5):
        pct = cnt / len(leaders) * 100
        lines.append(f"- **{sec}**: {cnt} stocks ({pct:.0f}%)")
    lines.append("")

    return lines


def _section_controls(week_start: str, week_ending: str, conn: sqlite3.Connection) -> list[str]:
    lines = ["## Controls — Why Similar Stocks Failed", ""]

    # Top failure reasons across the week
    rows = conn.execute("""
        SELECT candidate_reason, COUNT(*) as cnt, AVG(confidence) as avg_conf
        FROM failure_attribution
        WHERE trade_date BETWEEN ? AND ?
        GROUP BY candidate_reason
        ORDER BY cnt DESC, avg_conf DESC
        LIMIT 10
    """, (week_start, week_ending)).fetchall()

    if not rows:
        lines.append("*No failure attribution data for this week.*")
        lines.append("")
        return lines

    lines.append("| Reason | Occurrences | Avg Confidence |")
    lines.append("|---|---|---|")
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]:.2f} |")
    lines.append("")

    # Top stocks with most failures
    sym_rows = conn.execute("""
        SELECT symbol, COUNT(*) as fail_count, GROUP_CONCAT(DISTINCT candidate_reason) as reasons
        FROM failure_attribution
        WHERE trade_date BETWEEN ? AND ?
        GROUP BY symbol
        ORDER BY fail_count DESC
        LIMIT 5
    """, (week_start, week_ending)).fetchall()

    if sym_rows:
        lines.append("### Stocks with Most Failure Signals")
        lines.append("")
        for r in sym_rows:
            lines.append(f"- **{r[0]}**: {r[1]} signals → {r[2]}")
        lines.append("")

    return lines


def _section_persistence(week_start: str, week_ending: str, conn: sqlite3.Connection) -> list[str]:
    lines = ["## Persistence — Return Horizons", ""]

    horizons = [("1D", "return_1d"), ("3D", "return_3d"), ("5D", "return_5d"),
                ("10D", "return_10d"), ("20D", "return_20d")]

    for leader_type in ("WINNER", "LOSER"):
        lines.append(f"### {leader_type.title()}s")
        lines.append("")

        # Outcome class distribution
        oc_rows = conn.execute("""
            SELECT mlo.outcome_class, COUNT(*) as cnt
            FROM market_leaders_daily mld
            JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
            WHERE mld.trade_date BETWEEN ? AND ?
              AND mld.leader_type = ?
              AND mlo.outcome_class != 'UNKNOWN'
            GROUP BY mlo.outcome_class
            ORDER BY cnt DESC
        """, (week_start, week_ending, leader_type)).fetchall()

        if oc_rows:
            total = sum(r[1] for r in oc_rows)
            for r in oc_rows:
                lines.append(f"- **{r[0]}**: {r[1]} ({r[1]/total:.0%})")
        else:
            lines.append("*Outcome classification pending.*")
        lines.append("")

        # Positive return rates by horizon
        lines.append("| Horizon | Avg Return | % Positive |")
        lines.append("|---|---|---|")
        for label, col in horizons:
            row = conn.execute(f"""
                SELECT AVG(mlo.{col}),
                       SUM(CASE WHEN mlo.{col} > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
                FROM market_leaders_daily mld
                JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
                WHERE mld.trade_date BETWEEN ? AND ?
                  AND mld.leader_type = ?
                  AND mlo.{col} IS NOT NULL
            """, (week_start, week_ending, leader_type)).fetchone()
            if row and row[0] is not None:
                lines.append(f"| {label} | {row[0]:.2f}% | {row[1]:.0%} |")
            else:
                lines.append(f"| {label} | — | — |")
        lines.append("")

    return lines


# ── Aggregation ───────────────────────────────────────────────────────────────

def _aggregate_features(
    leaders: list[dict], conn: sqlite3.Connection
) -> list[tuple[str, float, float]]:
    """
    Returns list of (feature_name, avg_value, pct_present) sorted by pct_present desc.
    """
    leader_ids = [l["leader_id"] for l in leaders]
    if not leader_ids:
        return []

    placeholders = ",".join("?" * len(leader_ids))
    rows = conn.execute(f"""
        SELECT feature_name, feature_value
        FROM market_leader_features
        WHERE leader_id IN ({placeholders})
          AND feature_value IS NOT NULL
    """, leader_ids).fetchall()

    sums:  dict[str, float] = defaultdict(float)
    counts: dict[str, int]  = defaultdict(int)
    for r in rows:
        sums[r[0]]   += r[1]
        counts[r[0]] += 1

    n = len(leaders)
    result = []
    for feat in sums:
        avg  = sums[feat] / counts[feat]
        pct  = counts[feat] / n
        result.append((feat, avg, pct))

    result.sort(key=lambda x: x[2], reverse=True)
    return result


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_leaders(
    leader_type: str, week_start: str, week_ending: str, conn: sqlite3.Connection
) -> list[dict]:
    rows = conn.execute("""
        SELECT leader_id, symbol, sector, day_return_pct, leader_type
        FROM market_leaders_daily
        WHERE leader_type = ? AND trade_date BETWEEN ? AND ?
        ORDER BY trade_date, rank_position
    """, (leader_type, week_start, week_ending)).fetchall()
    return [dict(r) for r in rows]


def _date_minus_n(date_str: str, n: int) -> str:
    d = date.fromisoformat(date_str) - timedelta(days=n)
    return d.isoformat()


def _now_ts() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

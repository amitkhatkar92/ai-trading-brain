"""
Improvement Backlog Tracker
============================
Persistent store of every issue auto-detected by the EOD Retrospective.
Think of it as a self-maintained bug/improvement tracker that the AI populates
and the human reviews — closing the daily feedback loop.

Schema (data/improvement_backlog.json)
───────────────────────────────────────
[
  {
    "id":           1,
    "date_found":   "2026-04-10",
    "area":         "Latency",
    "description":  "OpportunityEngine DEGRADED 2/5 cycles",
    "impact":       "high",        # high / medium / low
    "status":       "open",        # open / in_progress / fixed
    "date_fixed":   null,
    "fix_commit":   null
  },
  ...
]

Impact scoring
──────────────
  high   → directly affects signal approval rate or P&L
  medium → affects cycle reliability or logging quality
  low    → minor UX or cosmetic

Status lifecycle
────────────────
  open        → detected, not yet addressed
  in_progress → being worked on this session
  fixed       → code change deployed
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_BACKLOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "improvement_backlog.json",
)

# Impact hierarchy for sorting
_IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}

# ── Known area labels ─────────────────────────────────────────────────────────
AREA_LATENCY    = "Latency"
AREA_FUNNEL     = "Signal Funnel"
AREA_TRADES     = "Trade Quality"
AREA_ODM        = "Opportunity Density"
AREA_STRATEGY   = "Strategy Selection"
AREA_EXECUTION  = "Execution"
AREA_RISK       = "Risk Management"
AREA_DATA       = "Data Feed"


class ImprovementBacklog:
    """
    Read/write the persistent improvement backlog.

    Usage::
        bl = ImprovementBacklog()
        bl.add("Latency", "OpportunityEngine slow 2/5 cycles", impact="high")
        bl.mark_fixed(item_id=3, commit="abc1234")
        print(bl.format_report())
    """

    def __init__(self) -> None:
        self._items: List[dict] = []
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def add(
        self,
        area:        str,
        description: str,
        impact:      str = "medium",
        date_found:  Optional[str] = None,
    ) -> Optional[int]:
        """
        Add a new issue — only if an identical (area + description) open item
        doesn't already exist, to prevent daily duplicates.

        Returns the item id, or None if the item was a duplicate.
        """
        dsc_lower = description.lower()
        for item in self._items:
            if (item["area"] == area
                    and item["status"] in ("open", "in_progress")
                    and item["description"].lower() == dsc_lower):
                return None   # already tracked

        new_id = max((i["id"] for i in self._items), default=0) + 1
        self._items.append({
            "id":          new_id,
            "date_found":  date_found or date.today().isoformat(),
            "area":        area,
            "description": description,
            "impact":      impact,
            "status":      "open",
            "date_fixed":  None,
            "fix_commit":  None,
        })
        self._save()
        log.info("[Backlog] New item #%d: [%s] %s", new_id, impact.upper(), description[:80])
        return new_id

    def mark_fixed(self, item_id: int, commit: Optional[str] = None) -> bool:
        """Mark an item as fixed."""
        for item in self._items:
            if item["id"] == item_id:
                item["status"]     = "fixed"
                item["date_fixed"] = date.today().isoformat()
                item["fix_commit"] = commit or ""
                self._save()
                log.info("[Backlog] Item #%d marked FIXED.", item_id)
                return True
        return False

    def mark_in_progress(self, item_id: int) -> bool:
        for item in self._items:
            if item["id"] == item_id:
                item["status"] = "in_progress"
                self._save()
                return True
        return False

    def get_open(self) -> List[dict]:
        """Return open items sorted by impact then date."""
        open_items = [i for i in self._items if i["status"] in ("open", "in_progress")]
        return sorted(open_items,
                      key=lambda i: (_IMPACT_ORDER.get(i["impact"], 9), i["date_found"]))

    def get_fixed_count(self) -> int:
        return sum(1 for i in self._items if i["status"] == "fixed")

    def get_all(self) -> List[dict]:
        return list(self._items)

    def format_report(self) -> str:
        """Plain-text backlog report for logs or /backlog command."""
        open_items = self.get_open()
        fixed_n    = self.get_fixed_count()

        sep  = "═" * 56
        sep2 = "─" * 56
        lines = [
            sep,
            "  🗂️  IMPROVEMENT BACKLOG",
            f"  Open: {len(open_items)}  |  Fixed: {fixed_n}  |  Total: {len(self._items)}",
            sep,
        ]

        if not open_items:
            lines.append("  ✅ No open issues — system is clean!")
        else:
            for item in open_items:
                icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(item["impact"], "⚪")
                status_tag = " [IN PROGRESS]" if item["status"] == "in_progress" else ""
                lines.append(
                    f"  #{item['id']:>3}  {icon} [{item['area']}]{status_tag}"
                )
                lines.append(f"       {item['description'][:72]}")
                lines.append(f"       Found: {item['date_found']}")
                lines.append(sep2)

        return "\n".join(lines)

    def format_telegram(self) -> str:
        """Telegram HTML backlog summary."""
        open_items = self.get_open()
        fixed_n    = self.get_fixed_count()

        def _h(t: str) -> str:
            return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        lines = [
            f"<b>🗂️ Improvement Backlog</b>",
            f"Open: <b>{len(open_items)}</b>  |  Fixed: {fixed_n}  |  Total: {len(self._items)}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if not open_items:
            lines.append("✅ <b>No open issues</b>")
        else:
            high   = [i for i in open_items if i["impact"] == "high"]
            medium = [i for i in open_items if i["impact"] == "medium"]
            low    = [i for i in open_items if i["impact"] == "low"]

            for group, icon, label in (
                (high,   "🔴", "HIGH IMPACT"),
                (medium, "🟡", "MEDIUM"),
                (low,    "⚪", "LOW"),
            ):
                if not group:
                    continue
                lines.append(f"\n{icon} <b>{label}</b>")
                for item in group:
                    status_tag = " <i>[in progress]</i>" if item["status"] == "in_progress" else ""
                    lines.append(
                        f"  <b>#{item['id']}</b> [{_h(item['area'])}]{status_tag}\n"
                        f"  {_h(item['description'][:90])}"
                        f"\n  <i>Found {item['date_found']}</i>"
                    )

        return "\n".join(lines)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(_BACKLOG_PATH):
            return
        try:
            with open(_BACKLOG_PATH, "r", encoding="utf-8") as f:
                self._items = json.load(f)
            log.info("[Backlog] Loaded %d items (%d open).",
                     len(self._items), len(self.get_open()))
        except Exception as exc:
            log.warning("[Backlog] Could not load: %s", exc)

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(_BACKLOG_PATH), exist_ok=True)
            with open(_BACKLOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._items, f, indent=2, default=str)
        except Exception as exc:
            log.warning("[Backlog] Could not save: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────
_instance: Optional[ImprovementBacklog] = None


def get_backlog() -> ImprovementBacklog:
    global _instance
    if _instance is None:
        _instance = ImprovementBacklog()
    return _instance


# ── Auto-populate from EOD flag strings ───────────────────────────────────────

_FLAG_RULES: List[dict] = [
    # (substring in flag, area, impact)
    {"key": "DEGRADED",           "area": AREA_LATENCY,  "impact": "high"},
    {"key": "STAGNANT",           "area": AREA_ODM,      "impact": "high"},
    {"key": "Single-symbol",      "area": AREA_STRATEGY, "impact": "high"},
    {"key": "MC stability",       "area": AREA_FUNNEL,   "impact": "medium"},
    {"key": "Re-entry DROPPED",   "area": AREA_EXECUTION,"impact": "medium"},
    {"key": "Negative P&L",       "area": AREA_TRADES,   "impact": "high"},
    {"key": "Survival rate",      "area": AREA_FUNNEL,   "impact": "medium"},
    {"key": "backtest",           "area": AREA_FUNNEL,   "impact": "medium"},
    {"key": "stale",              "area": AREA_DATA,     "impact": "low"},
]


def populate_from_flags(flags: List[str]) -> List[int]:
    """
    Given a list of auto-detected flag strings (from EOD Retrospective),
    add any new ones to the backlog.

    Returns list of new item ids added.
    """
    bl = get_backlog()
    added = []
    for flag in flags:
        area   = "General"
        impact = "low"
        for rule in _FLAG_RULES:
            if rule["key"].lower() in flag.lower():
                area   = rule["area"]
                impact = rule["impact"]
                break
        item_id = bl.add(area, flag, impact=impact)
        if item_id is not None:
            added.append(item_id)
    return added

"""
EOD Retrospective Engine
=========================
Runs at 15:35 IST every trading day.  Parses today's log file, trade journal,
and system state to produce a structured daily analysis report — the same
analysis that would otherwise require manual inspection.

Report covers:
  1. Cycle health overview (HEALTHY / DEGRADED counts, worst layer)
  2. Signal pipeline funnel (generated → backtest → MC → debate → executed)
  3. Trade outcomes (open / closed, P&L)
  4. ODM state (tier, consecutive EXPAND, stagnant flag)
  5. Market context (regime, VIX)
  6. Auto-detected flags (bottlenecks, concentration, threshold violations)
  7. Tomorrow watch (what to keep an eye on)

Output:
  • Saved to  data/eod_<YYYY-MM-DD>.txt
  • Sent via Telegram (HTML format)
  • Returned as plain text for /eod command
"""

from __future__ import annotations

import csv
import inspect
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── [RuntimeFingerprint] ─────────────────────────────────────────────────────
log.info(
    "[RuntimeFingerprint] module=%s build=SESSION_C_PATCHSET_V1 pid=%d file=%s",
    __name__, os.getpid(), os.path.abspath(__file__),
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR        = os.path.join(_ROOT, "logs")
_DATA_DIR       = os.path.join(_ROOT, "data")
_ODM_STATE      = os.path.join(_DATA_DIR, "odm_state.json")
_TRADES_CSV     = os.path.join(_DATA_DIR, "paper_trades.csv")
_DAILY_JSON     = os.path.join(_DATA_DIR, "paper_trading_daily.json")

# ── Regex patterns for log mining ─────────────────────────────────────────────
_RE_CYCLE_HEALTH  = re.compile(
    r"\[SystemMonitor\] (HEALTHY ✅|DEGRADED ⚠️) \| Cycle #(\d+) \| Total=([\d.]+)ms"
    r"(?: \| Slowest=(\S+))?"
)
_RE_BACKTEST_REJECT = re.compile(
    r"\[BacktestingAI\] (\S+) rejected \| score=(\d+)/6 below threshold ([\d.]+)"
)
_RE_MC_REJECT = re.compile(
    r"(Stability|Survival rate|MC profit|Worst-case) ([\d.]+\S*) < "
    r"(?:threshold|limit) ([\d.]+\S*)"
)
_RE_DECISION_WSCORE   = re.compile(r"Weighted Score:\s*([\d.]+)")
_RE_DECISION_APPROVED = re.compile(
    r"(?:FULL TRADE|PARTIAL TRADE).*?Position Size"
)
_RE_DECISION_REJECTED = re.compile(
    r"REJECTED.*?Position Size"
)
# Phase 5 — structured debate decision line emitted by DecisionEngine
_RE_DEBATE_DECISION = re.compile(
    r"\[DebateDecision\]\s+symbol=(\S+)\s+score=([\d.]+)\s+decision=(APPROVED|REJECTED)"
    r"\s+strategy=(\S+)\s+rr=([\d.]+)"
)
_RE_ODM_CYCLE = re.compile(
    r"\[ODM\] Cycle recorded: signals=(\d+).*?approved=(\d+).*?tier=(\w+)"
)
_RE_REGIME = re.compile(
    r"regime[=:\s]+(bull_trend|range_market|bear_market|volatile|neutral)", re.IGNORECASE
)
_VALID_REGIMES = {"bull_trend", "bear_market", "range_market", "volatile", "neutral"}
_RE_VIX    = re.compile(r"(?:VIX|vix)[=:\s]+([\d.]+)")
_RE_STAGNANT = re.compile(r"\[ODM\].*?STAGNANT.*?(\d+) consecutive")
_RE_LAYER_CRIT = re.compile(
    r"\[SystemMonitor\] CRITICAL latency: (\S+) took ([\d.]+)ms"
)
_RE_REENTRY_DROPPED = re.compile(
    r"\[OrderManager\].*?Re-entry DROPPED.*?(\S+) price ([\d.]+).*?drifted ([\d.]+)%"
)
_RE_EXECUTED = re.compile(
    r"(?:\[OrderManager\]|\[Execution\]).*?(?:LIMIT|MARKET) (?:order )?(?:placed|executed)"
    r".*?([A-Z]{4,10})",
    re.IGNORECASE,
)

# ── Lines we care about (fast pre-filter before regex) ────────────────────────
_KEYWORDS = (
    "SystemMonitor",
    "BacktestingAI",
    "Stability ", "Survival rate", "MC profit", "Worst-case",
    "DecisionEngine", "[Decision]",
    "[ODM]",
    "CRITICAL latency",
    "Re-entry DROPPED",
    "LIMIT order placed", "MARKET order",
)


# ─────────────────────────────────────────────────────────────────────────────
class EODRetrospective:
    """
    Collects and analyses today's trading session data.

    Usage::
        retro = EODRetrospective()
        report_text, telegram_html = retro.run()
    """

    def __init__(self) -> None:
        self._today = datetime.now().strftime("%Y-%m-%d")

    # ─────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────

    def run(self) -> Tuple[str, str]:
        """
        Run the full retrospective.

        Returns
        -------
        (plain_text, telegram_html) — both contain the same content.
        """
        log.info("[EOD-Retro] Starting daily retrospective for %s …", self._today)
        lines = self._read_log()

        cycles     = self._parse_cycles(lines)
        bt_rejects = self._parse_backtest_rejects(lines)
        mc_rejects = self._parse_mc_rejects(lines)
        decisions  = self._parse_decisions(lines)
        odm_cycles = self._parse_odm(lines)
        re_drops   = self._parse_reentry_drops(lines)
        regime, vix = self._parse_context(lines)
        stagnant_n = self._parse_stagnant(lines)
        trades     = self._read_trades()
        odm_state  = self._read_odm_state()
        daily_json = self._read_daily_json()
        trend      = self._compute_trend()

        plain, html = self._build_report(
            cycles, bt_rejects, mc_rejects, decisions, odm_cycles,
            re_drops, stagnant_n, regime, vix, trades, odm_state,
            daily_json, trend,
        )

        self._save(plain)

        # ── Auto-populate improvement backlog from detected flags ─────
        try:
            from learning_system.improvement_backlog import populate_from_flags
            _flags_section = self._extract_flags_from_plain(plain)
            new_ids = populate_from_flags(_flags_section)
            if new_ids:
                log.info("[EOD-Retro] %d new item(s) added to backlog: %s",
                         len(new_ids), new_ids)
        except Exception as _bl_exc:
            log.debug("[EOD-Retro] Backlog update skipped: %s", _bl_exc)

        log.info("[EOD-Retro] Report saved → data/eod_retro_%s.txt", self._today)
        return plain, html

    @staticmethod
    def _extract_flags_from_plain(plain: str) -> List[str]:
        """Extract the numbered flag lines from the plain-text report."""
        flags = []
        in_flags = False
        for line in plain.splitlines():
            if "AUTO-DETECTED FLAGS" in line:
                in_flags = True
                continue
            if in_flags:
                stripped = line.strip()
                if stripped and stripped[0].isdigit() and ". " in stripped:
                    flags.append(stripped.split(". ", 1)[1])
                elif stripped.startswith("═") or stripped.startswith("─"):
                    break
        return flags

    # ─────────────────────────────────────────────────────────────────
    # Log parsing
    # ─────────────────────────────────────────────────────────────────

    def _read_log(self) -> List[str]:
        """Return lines from today's log file (empty list if not found)."""
        for candidate in [
            os.path.join(_LOG_DIR, f"{self._today}.log"),
            os.path.join(_LOG_DIR, f"trading_{self._today}.log"),
            os.path.join(_LOG_DIR, "trading.log"),
        ]:
            if os.path.exists(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8", errors="replace") as f:
                        return f.readlines()
                except Exception as exc:
                    log.warning("[EOD-Retro] Could not read log %s: %s", candidate, exc)
        # Also try Docker container log written to data/
        alt = os.path.join(_DATA_DIR, f"{self._today}.log")
        if os.path.exists(alt):
            try:
                with open(alt, "r", encoding="utf-8", errors="replace") as f:
                    return f.readlines()
            except Exception:
                pass
        log.warning("[EOD-Retro] No log file found for %s — metrics will be empty.", self._today)
        return []

    def _parse_cycles(self, lines: List[str]) -> List[dict]:
        """Parse HEALTHY/DEGRADED cycle summaries."""
        cycles = []
        for line in lines:
            if "SystemMonitor" not in line:
                continue
            m = _RE_CYCLE_HEALTH.search(line)
            if m:
                cycles.append({
                    "status":   "HEALTHY" if "HEALTHY" in m.group(1) else "DEGRADED",
                    "cycle":    int(m.group(2)),
                    "total_ms": float(m.group(3)),
                    "slowest":  m.group(4) or "",
                })
        return cycles

    def _parse_backtest_rejects(self, lines: List[str]) -> List[dict]:
        rejects = []
        for line in lines:
            if "BacktestingAI" not in line:
                continue
            m = _RE_BACKTEST_REJECT.search(line)
            if m:
                rejects.append({
                    "strategy":  m.group(1),
                    "score":     int(m.group(2)),
                    "threshold": float(m.group(3)),
                })
        return rejects

    def _parse_mc_rejects(self, lines: List[str]) -> List[dict]:
        rejects = []
        for line in lines:
            if "Stability" not in line and "Survival rate" not in line \
               and "MC profit" not in line and "Worst-case" not in line:
                continue
            m = _RE_MC_REJECT.search(line)
            if m:
                rejects.append({
                    "reason":    m.group(1),
                    "value":     m.group(2),
                    "threshold": m.group(3),
                })
        return rejects

    def _parse_decisions(self, lines: List[str]) -> List[dict]:
        """
        Parse DecisionEngine scorecard lines from the trading log.

        Preferred source: [DebateDecision] structured lines (Phase 5).
        Fallback:
          "  Weighted Score: X.XX / 10"
          "  Decision : ✅ FULL TRADE    | Position Size: 100%"
          "  Decision : ⚡ PARTIAL TRADE | Position Size:  50%"
          "  Decision : ❌ REJECTED      | Position Size:   0%"
        """
        decisions: List[dict] = []
        _pending_score: Optional[float] = None
        _wscore_lines  = 0
        _outcome_lines = 0
        _debate_decision_lines = 0
        for line in lines:
            # ── Phase 5: prefer structured [DebateDecision] line ──────────────
            m_dd = _RE_DEBATE_DECISION.search(line)
            if m_dd:
                _debate_decision_lines += 1
                decisions.append({
                    "score":    float(m_dd.group(2)),
                    "outcome":  m_dd.group(3),    # "APPROVED" or "REJECTED"
                    "symbol":   m_dd.group(1),
                    "strategy": m_dd.group(4),
                    "rr":       float(m_dd.group(5)),
                    "source":   "DebateDecision",
                })
                continue
            # ── Fallback: legacy scorecard format ────────────────────────────
            m_ws = _RE_DECISION_WSCORE.search(line)
            if m_ws:
                _pending_score = float(m_ws.group(1))
                _wscore_lines += 1
                continue
            if _RE_DECISION_APPROVED.search(line):
                _outcome_lines += 1
                decisions.append({"score": _pending_score or 0.0, "outcome": "APPROVED", "source": "legacy"})
                _pending_score = None
            elif _RE_DECISION_REJECTED.search(line):
                _outcome_lines += 1
                decisions.append({"score": _pending_score or 0.0, "outcome": "REJECTED", "source": "legacy"})
                _pending_score = None
        # ── [DebateParserValidation] ───────────────────────────────────────
        _approved = sum(1 for d in decisions if d["outcome"] == "APPROVED")
        _rejected = sum(1 for d in decisions if d["outcome"] == "REJECTED")
        log.info(
            "[DebateParserValidation] weighted_score_lines=%d  outcome_lines=%d"
            "  debate_decision_lines=%d  approved=%d  rejected=%d"
            "  source=%s",
            _wscore_lines, _outcome_lines,
            _debate_decision_lines, _approved, _rejected,
            "DebateDecision" if _debate_decision_lines > 0 else "legacy_scorecard",
        )
        # ── [DebateConsistencyAudit] ──────────────────────────────────────
        if _debate_decision_lines > 0 and _wscore_lines > 0:
            # Both sources found in same log — cross-check counts
            log.warning(
                "[DebateConsistencyAudit] BOTH sources found: "
                "debate_decision_lines=%d  wscore_lines=%d  "
                "Preferring DebateDecision (structured). Legacy lines ignored.",
                _debate_decision_lines, _wscore_lines,
            )
        elif _debate_decision_lines == 0 and _wscore_lines == 0:
            log.warning(
                "[DebateConsistencyAudit] NO debate data found in log "
                "(both DebateDecision=0 and wscore_lines=0). "
                "Log file may be empty or debate cycle did not run.",
            )
        else:
            log.info(
                "[DebateConsistencyAudit] source=%s  total_debates=%d  "
                "approved=%d  rejected=%d  consistency=OK",
                "DebateDecision" if _debate_decision_lines > 0 else "legacy",
                _debate_decision_lines + _wscore_lines,
                _approved, _rejected,
            )
        return decisions

    def _parse_odm(self, lines: List[str]) -> List[dict]:
        cycles = []
        for line in lines:
            if "[ODM]" not in line:
                continue
            m = _RE_ODM_CYCLE.search(line)
            if m:
                cycles.append({
                    "signals":  int(m.group(1)),
                    "approved": int(m.group(2)),
                    "tier":     m.group(3),
                })
        return cycles

    def _parse_reentry_drops(self, lines: List[str]) -> List[dict]:
        drops = []
        for line in lines:
            if "Re-entry DROPPED" not in line:
                continue
            m = _RE_REENTRY_DROPPED.search(line)
            if m:
                drops.append({
                    "symbol":    m.group(1),
                    "price":     float(m.group(2)),
                    "drift_pct": float(m.group(3)),
                })
        return drops

    def _parse_stagnant(self, lines: List[str]) -> int:
        """Return the highest consecutive EXPAND count logged today."""
        best = 0
        for line in lines:
            if "STAGNANT" not in line:
                continue
            m = _RE_STAGNANT.search(line)
            if m:
                best = max(best, int(m.group(1)))
        return best

    def _parse_context(self, lines: List[str]) -> Tuple[str, float]:
        """Extract most recent regime and VIX from logs."""
        regime = "unknown"
        vix    = 0.0
        _match_line:    str = ""
        _match_pattern: str = ""
        _vix_line:      str = ""
        for line in reversed(lines):
            if not regime or regime == "unknown":
                m = _RE_REGIME.search(line)
                if m and m.group(1) not in ("unknown", "None"):
                    regime          = m.group(1)
                    _match_pattern  = m.group(0)
                    _match_line     = line.strip()[:120]
            if vix == 0.0:
                m = _RE_VIX.search(line)
                if m:
                    vix       = float(m.group(1))
                    _vix_line = line.strip()[:80]
            if regime != "unknown" and vix > 0.0:
                break
        # ── [RegimeParserValidation] / [RegimeParseFailure] ───────────────────────
        # Confirms exactly which log line produced the regime value.
        # If regime="unknown" or regime not in whitelist → emit [RegimeParseFailure]
        if regime == "unknown" or regime not in _VALID_REGIMES:
            log.warning(
                "[RegimeParseFailure] result_regime=%r  valid_regimes=%s"
                "  fallback_used=True  total_log_lines_scanned=%d"
                "  regex_pattern=%r  matched_pattern=%r  matched_line=%r",
                regime, sorted(_VALID_REGIMES), len(lines),
                _RE_REGIME.pattern,
                _match_pattern if _match_pattern else "(no_match)",
                _match_line    if _match_line    else "(no_match)",
            )
        else:
            log.info(
                "[RegimeParserValidation] result_regime=%r  result_vix=%.1f"
                "  fallback_used=False  total_log_lines_scanned=%d"
                "  regex_pattern=%r"
                "  matched_regime_pattern=%r"
                "  matched_line_preview=%r"
                "  matched_vix_line_preview=%r",
                regime, vix,
                len(lines),
                _RE_REGIME.pattern,
                _match_pattern if _match_pattern else "(no_match)",
                _match_line    if _match_line    else "(no_match)",
                _vix_line      if _vix_line      else "(no_match)",
            )
        return regime, vix

    # ─────────────────────────────────────────────────────────────────
    # External state readers
    # ─────────────────────────────────────────────────────────────────

    def _read_trades(self) -> List[dict]:
        """Read today's rows from paper_trades.csv."""
        if not os.path.exists(_TRADES_CSV):
            return []
        try:
            with open(_TRADES_CSV, newline="", encoding="utf-8") as f:
                return [r for r in csv.DictReader(f)
                        if r.get("timestamp", "").startswith(self._today)]
        except Exception as exc:
            log.warning("[EOD-Retro] Could not read trades CSV: %s", exc)
            return []

    def _read_odm_state(self) -> dict:
        if not os.path.exists(_ODM_STATE):
            return {}
        try:
            with open(_ODM_STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _read_daily_json(self) -> dict:
        if not os.path.exists(_DAILY_JSON):
            return {}
        try:
            with open(_DAILY_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # ─────────────────────────────────────────────────────────────────
    # Week-over-week trend
    # ─────────────────────────────────────────────────────────────────

    def _compute_trend(self) -> dict:
        """
        Read the last 5 saved daily JSON files and compute direction
        for key profitability metrics.

        Returns dict with keys:
          days_available, pnl_trend, approval_rate_trend,
          healthy_rate_trend, rows (last 5 rows for table)
        """
        import glob as _glob
        pattern = os.path.join(_DATA_DIR, "eod_retro_*.txt")
        files = sorted(_glob.glob(pattern))[-5:]   # last 5 plain reports

        # We can't parse our own plain text reliably — use paper_trading_daily.json
        # history if available, otherwise use daily_json snapshots.
        # Simpler approach: read the daily_json for each day by scanning the data dir.
        daily_pattern = os.path.join(_DATA_DIR, "paper_trading_daily_*.json")
        daily_files = sorted(_glob.glob(daily_pattern))

        # Also accept the single rolling file (paper_trading_daily.json) as day 0 reference
        rows = []
        for fp in daily_files[-5:]:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    d = json.load(f)
                rows.append({
                    "date":     d.get("date", "?"),
                    "pnl":      d.get("today", {}).get("net_pnl", 0.0),
                    "trades":   d.get("today", {}).get("trades", 0),
                    "wins":     d.get("today", {}).get("wins", 0),
                })
            except Exception:
                pass

        if len(rows) < 2:
            return {"days_available": len(rows), "rows": rows,
                    "pnl_trend": "insufficient data"}

        pnls = [r["pnl"] for r in rows]
        recent_avg  = sum(pnls[-2:]) / 2
        earlier_avg = sum(pnls[:-2]) / max(len(pnls) - 2, 1)
        if recent_avg > earlier_avg + 500:
            pnl_dir = "📈 improving"
        elif recent_avg < earlier_avg - 500:
            pnl_dir = "📉 declining"
        else:
            pnl_dir = "➡️ stable"

        total_trades = sum(r["trades"] for r in rows)
        total_wins   = sum(r["wins"]   for r in rows)
        week_wr = (total_wins / total_trades * 100) if total_trades else 0

        return {
            "days_available": len(rows),
            "rows":           rows,
            "pnl_trend":      pnl_dir,
            "week_win_rate":  round(week_wr, 1),
            "week_total_pnl": round(sum(pnls), 2),
        }

    # ─────────────────────────────────────────────────────────────────
    # Report builder
    # ─────────────────────────────────────────────────────────────────

    def _build_report(
        self,
        cycles:     List[dict],
        bt_rj:      List[dict],
        mc_rj:      List[dict],
        decisions:  List[dict],
        odm_cy:     List[dict],
        re_drops:   List[dict],
        stagnant_n: int,
        regime:     str,
        vix:        float,
        trades:     List[dict],
        odm_state:  dict,
        daily_json: dict,
        trend:      dict,
    ) -> Tuple[str, str]:

        today_label = datetime.now().strftime("%d %b %Y")

        # ── Cycle summary ──────────────────────────────────────────────
        healthy_n  = sum(1 for c in cycles if c["status"] == "HEALTHY")
        degraded_n = len(cycles) - healthy_n
        total_ms_list = [c["total_ms"] for c in cycles]
        fastest_ms = min(total_ms_list, default=0)
        slowest_ms = max(total_ms_list, default=0)
        slowest_layers: Dict[str, int] = defaultdict(int)
        for c in cycles:
            if c["slowest"] and c["status"] == "DEGRADED":
                slowest_layers[c["slowest"].split("(")[0]] += 1

        # ── Signal funnel ──────────────────────────────────────────────
        total_signals  = sum(c["signals"]  for c in odm_cy) if odm_cy else 0
        total_approved = sum(c["approved"] for c in odm_cy) if odm_cy else 0
        total_bt_rj    = len(bt_rj)
        total_mc_rj    = len(mc_rj)
        approved_dec   = sum(1 for d in decisions if d["outcome"] == "APPROVED")
        rejected_dec   = sum(1 for d in decisions if d["outcome"] == "REJECTED")

        # MC rejection breakdown
        mc_reasons: Dict[str, int] = defaultdict(int)
        mc_values: Dict[str, List[float]] = defaultdict(list)
        for r in mc_rj:
            mc_reasons[r["reason"]] += 1
            try:
                mc_values[r["reason"]].append(float(r["value"].rstrip("%R")))
            except Exception:
                pass

        # ── Trades ────────────────────────────────────────────────────
        # Build open/closed from today's rows.
        # order_manager writes event="CLOSE" (not "CLOSED"), so we accept both.
        # Deduplicate open positions by order_id: keep only the latest OPEN row
        # per order (guards against duplicate journal writes after restart).
        _CLOSE_EVENTS = {"CLOSE", "CLOSED", "CANCELLED"}
        _OPEN_EVENTS  = {"OPEN", "REENTRY_OPEN"}
        _open_by_oid: Dict[str, dict] = {}
        _closed_oids: set = set()
        for _t in trades:
            _oid = _t.get("order_id", "").strip()
            _ev  = _t.get("event", "").strip().upper()
            if _ev in _CLOSE_EVENTS:
                _closed_oids.add(_oid)
                _open_by_oid.pop(_oid, None)
            elif _ev in _OPEN_EVENTS and _oid not in _closed_oids:
                _open_by_oid[_oid] = _t
        open_trades   = list(_open_by_oid.values())
        closed_trades = [t for t in trades if t.get("event", "").strip().upper() in _CLOSE_EVENTS]
        today_pnl = daily_json.get("today", {}).get("net_pnl", 0.0)
        today_wins = daily_json.get("today", {}).get("wins", 0)
        today_losses = daily_json.get("today", {}).get("losses", 0)

        # ── Research Integrity — classify by architecture generation ──────────
        # Trades before PREPARED_UNIVERSE_ACTIVATION_DATE = LEGACY_STATIC.
        # Trades on/after = PREPARED_UNIVERSE_V1.
        # Classification uses timestamp field from the CSV row.
        try:
            from config import PREPARED_UNIVERSE_ACTIVATION_DATE as _act_date
        except Exception:
            _act_date = "2026-05-22"

        def _classify_generation(row: dict) -> str:
            ts = row.get("timestamp", "") or ""
            date_part = ts[:10]   # "YYYY-MM-DD"
            if date_part and date_part >= _act_date:
                return "PREPARED_UNIVERSE_V1"
            return "LEGACY_STATIC"

        _legacy_closed   = [t for t in closed_trades if _classify_generation(t) == "LEGACY_STATIC"]
        _prepared_closed = [t for t in closed_trades if _classify_generation(t) == "PREPARED_UNIVERSE_V1"]
        _legacy_pnl   = sum(float(t.get("pnl", 0.0) or 0.0) for t in _legacy_closed)
        _prepared_pnl = sum(float(t.get("pnl", 0.0) or 0.0) for t in _prepared_closed)

        # Patch 19/20/22/26: dynamic weight, contamination, clean state, generation tag
        try:
            from learning_system.research_integrity import (
                compute_legacy_weight,
                emit_contamination_telemetry,
                emit_clean_research_state,
                get_system_prepared_trade_count,
                is_clean_research_ready,
                MIN_CLEAN_PREPARED_TRADES,
            )
            _sys_prepared   = get_system_prepared_trade_count()
            _dyn_lw         = compute_legacy_weight(_sys_prepared)
            _clean_ready    = is_clean_research_ready()
            _contamination  = emit_contamination_telemetry(
                legacy_count   = len(_legacy_closed),
                prepared_count = _sys_prepared,
                source         = "EODRetrospective",
            )
            _crs            = emit_clean_research_state(source="EODRetrospective")
        except Exception as _ri_exc:
            log.debug("[ResearchIntegrity] EOD helpers skipped: %s", _ri_exc)
            _sys_prepared  = len(_prepared_closed)
            _dyn_lw        = 0.25
            _clean_ready   = False
            _contamination = {
                "legacy_trade_count": len(_legacy_closed),
                "prepared_trade_count": _sys_prepared,
                "effective_legacy_weight": _dyn_lw,
                "legacy_weighted_pct": 0.0,
                "prepared_weighted_pct": 0.0,
            }
            _crs = {
                "prepared_trade_count": _sys_prepared,
                "required": 100,
                "ready": _clean_ready,
                "adaptive_mutation_blocked": True,
            }

        log.info(
            "[ResearchIntegrity] EOD  activation_date=%s  "
            "legacy_trades=%d  legacy_pnl=%.2f  "
            "prepared_trades=%d  prepared_pnl=%.2f  "
            "dynamic_legacy_weight=%.4f  prepared_weight=1.00",
            _act_date,
            len(_legacy_closed),   _legacy_pnl,
            len(_prepared_closed), _prepared_pnl,
            _dyn_lw,
        )

        # Patch 26: [TelemetryGeneration] — forensic traceability of primary generation
        try:
            from config import USE_PREPARED_UNIVERSE as _use_prep_eod
            _primary_gen = "PREPARED_UNIVERSE_V1" if _use_prep_eod else "LEGACY_STATIC"
        except Exception:
            _primary_gen = "PREPARED_UNIVERSE_V1"

        _total_wt = (
            len(_legacy_closed) * _dyn_lw +
            _sys_prepared * 1.0
        )
        _legacy_wpct_telemetry = (
            round(len(_legacy_closed) * _dyn_lw / _total_wt * 100, 1)
            if _total_wt > 0 else 0.0
        )

        log.info(
            "[TelemetryGeneration] primary_generation=%s  "
            "legacy_weighted_pct=%.1f",
            _primary_gen, _legacy_wpct_telemetry,
        )

        # Symbols traded
        symbols: Dict[str, int] = defaultdict(int)
        for t in trades:
            s = t.get("symbol", "")
            if s:
                symbols[s] += 1

        # ── ODM ───────────────────────────────────────────────────────
        odm_tier       = odm_state.get("current_tier", "unknown")
        odm_density    = odm_state.get("density_pct",  0.0)
        consec_expand  = odm_state.get("consecutive_expand", stagnant_n) or stagnant_n
        odm_stagnant   = consec_expand >= 3

        # ── Flags (auto-detected issues) ──────────────────────────────
        flags: List[str] = []

        if degraded_n > 0:
            worst_layer = (max(slowest_layers, key=slowest_layers.get)
                          if slowest_layers else "unknown")
            flags.append(
                f"⚡ {degraded_n}/{len(cycles)} cycles DEGRADED "
                f"(slowest: {worst_layer}) — check latency"
            )

        if odm_stagnant:
            flags.append(
                f"🔍 ODM STAGNANT — {consec_expand} consecutive EXPAND cycles "
                f"(density {odm_density:.1f}%) — universe fully expanded, "
                f"few setups passing filters"
            )

        # MC stability rejections with values
        if "Stability" in mc_reasons:
            vals = mc_values["Stability"]
            avg_val = sum(vals) / len(vals) if vals else 0
            flags.append(
                f"📉 MC stability rejected {mc_reasons['Stability']} signal(s) "
                f"(avg score {avg_val:.2f}) — "
                f"{"within adaptive range, regime-specific threshold applied" if avg_val >= 0.38 else "genuinely poor edge"}"
            )

        if len(symbols) == 1:
            sym = next(iter(symbols))
            flags.append(
                f"⚠️  Single-symbol concentration — only {sym} seen all day. "
                f"Universe may be too narrow for current regime."
            )

        if re_drops:
            _drop_parts = [f"{d['symbol']} {d['drift_pct']:.1f}%" for d in re_drops[:3]]
            flags.append(
                f"↩️  {len(re_drops)} stale re-entry slot(s) dropped "
                f"(price drifted >1.5%): {', '.join(_drop_parts)}"
            )

        if today_pnl < -5000:
            flags.append(
                f"💸 Negative P&L today: ₹{today_pnl:,.0f} — review trade quality"
            )

        # ── Tomorrow watch ────────────────────────────────────────────
        watch: List[str] = []
        if odm_stagnant:
            watch.append("ODM still in EXPAND — consider if additional stocks or "
                         "looser scan criteria would help")
        if regime in ("range_market",):
            watch.append(
                f"Market in {regime} (VIX {vix:.1f}) — expect similar density; "
                f"mean-reversion setups most likely"
            )
        if degraded_n > 1:
            watch.append("Multiple DEGRADED cycles today — monitor latency at open")

        if not watch:
            watch.append("No specific concerns — continue standard monitoring")

        # ── Per-strategy breakdown for Strategy Intelligence section ─────
        strat_pnl:    Dict[str, float] = defaultdict(float)
        strat_trades: Dict[str, int]   = defaultdict(int)
        strat_wins:   Dict[str, int]   = defaultdict(int)
        for _ct in closed_trades:
            _s = (_ct.get("strategy", "") or "").strip() or "unknown"
            _p = float(_ct.get("pnl", 0.0) or 0.0)
            strat_pnl[_s]    += _p
            strat_trades[_s] += 1
            if _p > 0:
                strat_wins[_s] += 1

        # ── Governance violations (pre-open / late-entry) ─────────────
        gov_violations = self._parse_governance_violations(trades)

        # ── Assemble plain text ────────────────────────────────────────
        sep  = "─" * 52
        sep2 = "═" * 52

        lines_plain = [
            sep2,
            f"  📊 DAILY RETROSPECTIVE — {today_label}",
            sep2,
        ]

        # ──────────────────────────────────────────────────────────────
        # SECTION 1 — STRATEGY INTELLIGENCE
        # Real edge quality: what did each strategy actually produce today?
        # ──────────────────────────────────────────────────────────────
        pnl_str = f"₹{today_pnl:+,.0f}" if today_pnl != 0.0 else "—"
        lines_plain += [
            "🧠 SECTION 1 — STRATEGY INTELLIGENCE",
            f"  Closed trades : {len(closed_trades)}  |  Open: {len(open_trades)}",
            f"  Day P&L       : {pnl_str}  (W:{today_wins}  L:{today_losses})",
        ]
        if strat_trades:
            lines_plain.append("  Per-strategy breakdown:")
            for _sn in sorted(strat_trades):
                _n  = strat_trades[_sn]
                _pw = strat_wins[_sn]
                _wr = int(_pw / _n * 100) if _n else 0
                _pp = strat_pnl[_sn]
                lines_plain.append(
                    f"    {_sn:<38}  {_n:>2} trades  "
                    f"{_pw}W {_n - _pw}L  {_wr}%WR  ₹{_pp:+,.0f}"
                )
        else:
            lines_plain.append("  No closed trades recorded today.")
        lines_plain.append(sep)

        # ──────────────────────────────────────────────────────────────
        # SECTION 1b — RESEARCH INTEGRITY
        # Architecture generation split: DO NOT merge LEGACY_STATIC and
        # PREPARED_UNIVERSE_V1 performance for adaptive intelligence use.
        # ──────────────────────────────────────────────────────────────
        lines_plain += [
            "🔬 SECTION 1b — RESEARCH INTEGRITY (Architecture Generation)",
            f"  Activation date : {_act_date}  (PREPARED_UNIVERSE_V1 epoch start)",
        ]
        if _legacy_closed:
            _lw  = sum(1 for t in _legacy_closed if float(t.get("pnl", 0.0) or 0.0) > 0)
            _lwr = int(_lw / len(_legacy_closed) * 100) if _legacy_closed else 0
            lines_plain.append(
                f"  LEGACY_STATIC   : {len(_legacy_closed)} trades  "
                f"{_lw}W {len(_legacy_closed)-_lw}L  {_lwr}%WR  "
                f"₹{_legacy_pnl:+,.0f}  [research_weight=0.25 — DO NOT use for strategy governance]"
            )
        else:
            lines_plain.append("  LEGACY_STATIC   : 0 trades today  ✅ epoch boundary crossed")
        if _prepared_closed:
            _pw2 = sum(1 for t in _prepared_closed if float(t.get("pnl", 0.0) or 0.0) > 0)
            _pwr = int(_pw2 / len(_prepared_closed) * 100) if _prepared_closed else 0
            lines_plain.append(
                f"  PREPARED_V1     : {len(_prepared_closed)} trades  "
                f"{_pw2}W {len(_prepared_closed)-_pw2}L  {_pwr}%WR  "
                f"₹{_prepared_pnl:+,.0f}  [research_weight=1.00 — valid for governance]"
            )
        else:
            lines_plain.append("  PREPARED_V1     : 0 trades yet — accumulating clean sample")

        # Patch 19/20/22/26: dynamic weight, contamination, clean state
        lines_plain += [
            f"  Dynamic legacy weight : {_dyn_lw:.4f}  "
            f"(decays 0.25→0.10 as prepared_trades grow)",
            f"  Architecture telemetry :",
            f"    LEGACY_STATIC      : trades={len(_legacy_closed)}"
            f"  weighted={len(_legacy_closed) * _dyn_lw:.2f}",
            f"    PREPARED_UNIVERSE_V1: trades={_sys_prepared}"
            f"  weighted={_sys_prepared * 1.0:.2f}",
            f"  Research contamination : "
            f"legacy_weighted_pct={_contamination['legacy_weighted_pct']:.1f}%  "
            f"prepared_weighted_pct={_contamination['prepared_weighted_pct']:.1f}%",
            f"  Clean research gate   : "
            f"prepared={_crs['prepared_trade_count']}  required={_crs['required']}  "
            f"ready={'✅ YES' if _crs['ready'] else '⏳ NO'}  "
            f"adaptive_mutation_blocked={'NO' if _crs['ready'] else 'YES — FROZEN'}",
            f"  Primary generation    : {_primary_gen}",
        ]

        # ──────────────────────────────────────────────────────────────
        # SECTION 2 — OPERATIONAL RELIABILITY
        # System stability: cycle health, signal funnel, ODM.
        # ──────────────────────────────────────────────────────────────
        lines_plain += [
            "🔄 SECTION 2 — OPERATIONAL RELIABILITY",
            f"  Cycles     : {len(cycles)}  ✅ {healthy_n}  ⚠️ {degraded_n}",
        ]
        if total_ms_list:
            lines_plain.append(
                f"  Latency    : fastest {fastest_ms:.0f}ms  |  slowest {slowest_ms:.0f}ms"
            )
        if slowest_layers:
            layers_str = ", ".join(f"{k}×{v}" for k, v in slowest_layers.items())
            lines_plain.append(f"  Slow layers: {layers_str}")
        lines_plain += [
            f"  Signals    : {total_signals} generated  →  {total_bt_rj} BT-rejected"
            f"  →  {total_mc_rj} MC-rejected",
            f"  Debate     : ✅ {approved_dec} approved  ❌ {rejected_dec} rejected",
            f"  ODM tier   : {odm_tier}  density {odm_density:.1f}%",
        ]
        if odm_stagnant:
            lines_plain.append(
                f"  ⚠️  ODM stagnant: {consec_expand} consecutive EXPAND cycles"
            )
        if mc_reasons:
            mc_summary = ", ".join(f"{k}:{v}" for k, v in mc_reasons.items())
            lines_plain.append(f"  MC reasons : {mc_summary}")
        if degraded_n > 0 and slowest_layers:
            worst_layer = max(slowest_layers, key=slowest_layers.get)
            lines_plain.append(
                f"  ⚡ {degraded_n} DEGRADED — slowest: {worst_layer}"
            )
        lines_plain.append(sep)

        # ──────────────────────────────────────────────────────────────
        # SECTION 3 — GOVERNANCE VIOLATIONS
        # Execution-window compliance: pre-open and late-entry breaches.
        # ──────────────────────────────────────────────────────────────
        lines_plain.append("⚖️  SECTION 3 — GOVERNANCE VIOLATIONS")
        if gov_violations:
            lines_plain.append(
                f"  ⚠️  {len(gov_violations)} violation(s) detected today:"
            )
            for _v in gov_violations:
                lines_plain.append(f"    • {_v}")
            lines_plain.append(
                "  ACTION: Review entry timing. Window is 09:45–14:30."
            )
        else:
            lines_plain.append("  ✅ All entries within approved window (09:45–14:30).")
        lines_plain.append(sep)

        # ──────────────────────────────────────────────────────────────
        # SECTION 4 — CONCENTRATION RISK
        # Symbol diversity and exposure structure.
        # ──────────────────────────────────────────────────────────────
        lines_plain.append("🔎 SECTION 4 — CONCENTRATION RISK")
        if symbols:
            lines_plain += [
                f"  Symbols seen : {len(symbols)}  ({', '.join(symbols.keys())})",
            ]
        else:
            lines_plain.append("  No symbols traded today.")
        if len(symbols) == 1:
            sym1 = next(iter(symbols))
            lines_plain.append(
                f"  ⚠️  Single-symbol concentration: only {sym1} today."
                f"  Universe may be too narrow for current regime."
            )
        if re_drops:
            _drop_parts = [f"{d['symbol']} {d['drift_pct']:.1f}%" for d in re_drops[:3]]
            lines_plain.append(
                f"  ↩️  {len(re_drops)} stale re-entry slot(s) dropped"
                f"  (drifted >1.5%): {', '.join(_drop_parts)}"
            )
        if today_pnl < -5000:
            lines_plain.append(
                f"  💸 Negative P&L today: ₹{today_pnl:,.0f}"
            )
        lines_plain.append(sep)

        # ──────────────────────────────────────────────────────────────
        # SECTION 5 — MARKET REGIME CONTEXT
        # Regime, VIX, tomorrow watch, weekly trend.
        # ──────────────────────────────────────────────────────────────
        lines_plain += [
            "🌐 SECTION 5 — MARKET REGIME CONTEXT",
            f"  Regime : {regime}  |  VIX: {vix:.1f}",
            "",
            "  🔭 Tomorrow Watch",
        ]
        for item in watch:
            lines_plain.append(f"    • {item}")

        lines_plain += [sep2, "  Ask Copilot: 'what did we learn today?' for analysis", sep2]

        # ── Assemble Telegram HTML ─────────────────────────────────────
        def _h(t: str) -> str:
            return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html_lines = [
            f"<b>📊 DAILY RETROSPECTIVE — {today_label}</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            # ── S1: Strategy Intelligence ──────────────────────────────
            "<b>🧠 Strategy Intelligence</b>",
            f"  Closed: {len(closed_trades)}  Open: {len(open_trades)}"
            f"  |  P&amp;L: <b>{_h(pnl_str)}</b>  (W:{today_wins} L:{today_losses})",
        ]
        if strat_trades:
            for _sn in sorted(strat_trades):
                _n  = strat_trades[_sn]
                _wr = int(strat_wins[_sn] / _n * 100) if _n else 0
                _pp = strat_pnl[_sn]
                html_lines.append(
                    f"  <code>{_h(_sn):<36}  {_n:>2}tr  {_wr}%WR  ₹{_pp:+,.0f}</code>"
                )
        else:
            html_lines.append("  <i>No closed trades recorded today.</i>")

        html_lines += [
            "",
            # ── S2: Operational Reliability ────────────────────────────
            "<b>🔄 Operational Reliability</b>",
            f"  Cycles: {len(cycles)}  ✅ {healthy_n}  ⚠️ {degraded_n}",
        ]
        if total_ms_list:
            html_lines.append(f"  Latency: {fastest_ms:.0f}–{slowest_ms:.0f}ms")
        html_lines += [
            f"  Signals: {total_signals} → BT-rj {total_bt_rj} → MC-rj {total_mc_rj}",
            f"  Debate: ✅ {approved_dec}  ❌ {rejected_dec}",
            f"  ODM: <b>{_h(odm_tier)}</b>  {odm_density:.1f}%",
        ]
        if odm_stagnant:
            html_lines.append(f"  ⚠️ ODM stagnant: {consec_expand} EXPAND cycles")

        html_lines += [
            "",
            # ── S3: Governance Violations ──────────────────────────────
            "<b>⚖️ Governance Violations</b>",
        ]
        if gov_violations:
            html_lines.append(
                f"  ⚠️ <b>{len(gov_violations)} violation(s)</b> detected:"
            )
            for _v in gov_violations:
                html_lines.append(f"  • {_h(_v)}")
            html_lines.append(
                "  <i>Window: 09:45–14:30. Review entry timing.</i>"
            )
        else:
            html_lines.append("  ✅ All entries within approved window.")

        html_lines += [
            "",
            # ── S4: Concentration Risk ─────────────────────────────────
            "<b>🔎 Concentration Risk</b>",
        ]
        if symbols:
            html_lines.append(
                f"  Symbols: <code>{_h(', '.join(symbols.keys()))}</code>"
            )
            if len(symbols) == 1:
                html_lines.append(
                    f"  ⚠️ Single-symbol concentration today."
                )
        else:
            html_lines.append("  No symbols traded today.")
        if re_drops:
            html_lines.append(
                f"  ↩️ {len(re_drops)} re-entry slot(s) dropped (price drift)"
            )

        html_lines += [
            "",
            # ── S5: Market Regime Context ──────────────────────────────
            "<b>🌐 Market Regime Context</b>",
            f"  Regime: <code>{_h(regime)}</code>  VIX: {vix:.1f}",
            "",
            "<b>🔭 Tomorrow Watch</b>",
        ]
        for item in watch:
            html_lines.append(f"  • {_h(item)}")

        # ── Week-over-week trend (HTML) ────────────────────────────────
        if trend.get("days_available", 0) >= 2:
            html_lines += [
                "",
                "<b>📈 Weekly Trend</b>",
                f"  P&amp;L direction : {_h(trend.get('pnl_trend', '—'))}",
                f"  5-day win rate : {trend.get('week_win_rate', 0):.1f}%",
                f"  5-day net P&amp;L : ₹{trend.get('week_total_pnl', 0):+,.0f}",
            ]
            for r in trend.get("rows", []):
                wr_str = (f"{r['wins']}/{r['trades']}" if r['trades'] else "—")
                html_lines.append(
                    f"  <code>{r['date']}  ₹{r['pnl']:+7,.0f}  W/L:{wr_str}</code>"
                )

        html_lines += [
            "",
            "<i>💬 Ask Copilot: \"what did we learn today?\" to get improvement suggestions</i>",
        ]

        html = "\n".join(html_lines)

        # ── Week-over-week trend (plain text) ─────────────────────────
        if trend.get("days_available", 0) >= 2:
            lines_plain += [
                "📈 WEEKLY TREND",
                f"  P&L direction  : {trend.get('pnl_trend', '—')}",
                f"  5-day win rate : {trend.get('week_win_rate', 0):.1f}%",
                f"  5-day net P&L  : ₹{trend.get('week_total_pnl', 0):+,.0f}",
            ]
            for r in trend.get("rows", []):
                wr_str = (f"{r['wins']}/{r['trades']}" if r['trades'] else "—")
                lines_plain.append(f"  {r['date']}  ₹{r['pnl']:+7,.0f}  W/L:{wr_str}")
            lines_plain.append(sep2)

        plain = "\n".join(lines_plain)

        return plain, html

    # ─────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_governance_violations(trades: List[dict]) -> List[str]:
        """
        Detect trades opened outside the approved 09:45–14:30 execution window
        by inspecting the timestamp column of CSV rows with OPEN/REENTRY_OPEN events.
        Returns a list of human-readable violation strings, empty list if clean.
        """
        violations: List[str] = []
        _WINDOW_OPEN  = "09:45"
        _WINDOW_CLOSE = "14:30"
        for _t in trades:
            _ev = (_t.get("event", "") or "").strip().upper()
            if _ev not in ("OPEN", "REENTRY_OPEN"):
                continue
            _ts = (_t.get("timestamp", "") or "").strip()
            if not _ts:
                continue
            try:
                _dt = datetime.fromisoformat(_ts)
                _t_str = _dt.strftime("%H:%M")
                _sym   = _t.get("symbol",   "?")
                _strat = _t.get("strategy", "?")
                if _t_str < _WINDOW_OPEN:
                    violations.append(
                        f"Pre-open entry: {_sym} ({_strat}) at {_t_str}"
                        f"  [window opens 09:45]"
                    )
                elif _t_str > _WINDOW_CLOSE:
                    violations.append(
                        f"Late entry: {_sym} ({_strat}) at {_t_str}"
                        f"  [window closes 14:30]"
                    )
            except Exception:
                continue
        return violations

    def _save(self, plain: str) -> None:
        """Save to data/eod_retro_YYYY-MM-DD.txt (separate from self-eval report)."""
        try:
            os.makedirs(_DATA_DIR, exist_ok=True)
            path = os.path.join(_DATA_DIR, f"eod_retro_{self._today}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(plain)
            # Mirror to data/logs/ for consistency
            log_dir = os.path.join(_DATA_DIR, "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, f"eod_retro_{self._today}.txt"),
                      "w", encoding="utf-8") as f:
                f.write(plain)
        except Exception as exc:
            log.warning("[EOD-Retro] Could not save report: %s", exc)


# ── Convenience function ──────────────────────────────────────────────────────

def run_eod_retrospective() -> Tuple[str, str]:
    """
    Generate and return today's EOD retrospective.
    Returns (plain_text, telegram_html).
    """
    return EODRetrospective().run()

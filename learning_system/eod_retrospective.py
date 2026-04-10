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
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

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
_RE_DECISION_SCORE = re.compile(
    r"\[Decision(?:Engine)?\].*?score=([\d.]+).*?(APPROVED|REJECTED)"
)
_RE_ODM_CYCLE = re.compile(
    r"\[ODM\] Cycle recorded: signals=(\d+).*?approved=(\d+).*?tier=(\w+)"
)
_RE_REGIME = re.compile(r"regime[=:\s]+([\w_]+)", re.IGNORECASE)
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
        decisions = []
        for line in lines:
            if "Decision" not in line:
                continue
            m = _RE_DECISION_SCORE.search(line)
            if m:
                decisions.append({
                    "score":    float(m.group(1)),
                    "outcome":  m.group(2),
                })
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
        for line in reversed(lines):
            if not regime or regime == "unknown":
                m = _RE_REGIME.search(line)
                if m and m.group(1) not in ("unknown", "None"):
                    regime = m.group(1)
            if vix == 0.0:
                m = _RE_VIX.search(line)
                if m:
                    vix = float(m.group(1))
            if regime != "unknown" and vix > 0.0:
                break
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
        open_trades   = [t for t in trades if t.get("event", "").upper() != "CLOSED"]
        closed_trades = [t for t in trades if t.get("event", "").upper() == "CLOSED"]
        today_pnl = daily_json.get("today", {}).get("net_pnl", 0.0)
        today_wins = daily_json.get("today", {}).get("wins", 0)
        today_losses = daily_json.get("today", {}).get("losses", 0)

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
            flags.append(
                f"↩️  {len(re_drops)} stale re-entry slot(s) dropped "
                f"(price drifted >1.5%): "
                f"{', '.join(d['symbol'] + f\" {d['drift_pct']:.1f}%\" for d in re_drops[:3])}"
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

        # ── Assemble plain text ────────────────────────────────────────
        sep  = "─" * 52
        sep2 = "═" * 52

        lines_plain = [
            sep2,
            f"  📊 DAILY RETROSPECTIVE — {today_label}",
            sep2,
        ]

        # Section 1: Cycles
        lines_plain += [
            "🔄 CYCLE HEALTH",
            f"  Cycles run : {len(cycles)}  |  ✅ HEALTHY: {healthy_n}  |  ⚠️ DEGRADED: {degraded_n}",
        ]
        if total_ms_list:
            lines_plain.append(
                f"  Latency    : fastest {fastest_ms:.0f}ms  |  slowest {slowest_ms:.0f}ms"
            )
        if slowest_layers:
            layers_str = ", ".join(f"{k}×{v}" for k, v in slowest_layers.items())
            lines_plain.append(f"  Slow layers: {layers_str}")

        lines_plain.append(sep)

        # Section 2: Signal funnel
        lines_plain += [
            "📡 SIGNAL PIPELINE",
            f"  Generated  : {total_signals}  (across {len(odm_cy)} cycles)",
            f"  Backtest   : rejected {total_bt_rj}",
        ]
        if mc_reasons:
            mc_summary = ", ".join(f"{k}: {v}" for k, v in mc_reasons.items())
            lines_plain.append(f"  MC/Resil.  : rejected {total_mc_rj}  ({mc_summary})")
        else:
            lines_plain.append(f"  MC/Resil.  : rejected {total_mc_rj}")
        lines_plain += [
            f"  Debate     : {approved_dec} approved, {rejected_dec} rejected",
            sep,
        ]

        # Section 3: Trades
        pnl_str = f"₹{today_pnl:+,.0f}" if today_pnl != 0.0 else "—"
        lines_plain += [
            "🎯 TRADES TODAY",
            f"  Open   : {len(open_trades)}  |  Closed: {len(closed_trades)}",
            f"  P&L    : {pnl_str}  (W:{today_wins} L:{today_losses})",
        ]
        if symbols:
            lines_plain.append(f"  Symbols: {', '.join(symbols.keys())}")
        lines_plain.append(sep)

        # Section 4: ODM
        lines_plain += [
            "📊 OPPORTUNITY DENSITY",
            f"  Tier   : {odm_tier}  |  Density: {odm_density:.1f}%",
        ]
        if odm_stagnant:
            lines_plain.append(
                f"  ⚠️  STAGNANT: {consec_expand} consecutive EXPAND cycles"
            )
        lines_plain.append(sep)

        # Section 5: Context
        lines_plain += [
            "🌐 MARKET CONTEXT",
            f"  Regime : {regime}  |  VIX: {vix:.1f}",
            sep,
        ]

        # Section 6: Flags
        if flags:
            lines_plain.append("⚠️  AUTO-DETECTED FLAGS")
            for i, f_text in enumerate(flags, 1):
                lines_plain.append(f"  {i}. {f_text}")
            lines_plain.append(sep)
        else:
            lines_plain += ["✅ No issues detected today", sep]

        # Section 7: Tomorrow watch
        lines_plain.append("🔭 TOMORROW WATCH")
        for item in watch:
            lines_plain.append(f"  • {item}")
        lines_plain += [sep2, "  Ask Copilot: 'what did we learn today?' for analysis", sep2]

        # ── Assemble Telegram HTML ─────────────────────────────────────
        def _h(t: str) -> str:
            return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html_lines = [
            f"<b>📊 DAILY RETROSPECTIVE — {today_label}</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "<b>🔄 Cycle Health</b>",
            f"  Cycles: {len(cycles)}  |  ✅ {healthy_n}  |  ⚠️ {degraded_n}",
        ]
        if total_ms_list:
            html_lines.append(
                f"  Latency: {fastest_ms:.0f}ms – {slowest_ms:.0f}ms"
            )
        html_lines += [
            "",
            "<b>📡 Signal Pipeline</b>",
            f"  Generated → {total_signals}",
            f"  Backtest rejected → {total_bt_rj}",
            f"  MC/Resilience rejected → {total_mc_rj}",
            f"  Debate: ✅ {approved_dec}  ❌ {rejected_dec}",
            "",
            "<b>🎯 Trades</b>",
            f"  Open: {len(open_trades)}  Closed: {len(closed_trades)}",
            f"  P&amp;L: <b>{_h(pnl_str)}</b>  (W:{today_wins} L:{today_losses})",
        ]
        if symbols:
            html_lines.append(
                f"  Symbols: <code>{_h(', '.join(symbols.keys()))}</code>"
            )
        html_lines += [
            "",
            "<b>📊 Opportunity Density</b>",
            f"  Tier: <b>{_h(odm_tier)}</b>  Density: {odm_density:.1f}%",
        ]
        if odm_stagnant:
            html_lines.append(
                f"  ⚠️ STAGNANT: {consec_expand} consecutive EXPAND cycles"
            )
        html_lines += [
            "",
            "<b>🌐 Market</b>",
            f"  Regime: <code>{_h(regime)}</code>  VIX: {vix:.1f}",
            "",
        ]
        if flags:
            html_lines.append("<b>⚠️ Auto-Detected Flags</b>")
            for i, f_text in enumerate(flags, 1):
                html_lines.append(f"  {i}. {_h(f_text)}")
            html_lines.append("")
        else:
            html_lines += ["✅ <b>No issues detected today</b>", ""]

        html_lines.append("<b>🔭 Tomorrow Watch</b>")
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

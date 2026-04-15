"""
Trade Analytics Layer — Performance Measurement Engine
=======================================================
Tracks every closed trade outcome and produces quantified evidence that the
adaptive exit/extension logic is improving (or hurting) system expectancy.

4 Blocks:
  Block 1 — Trade-level log       (symbol, entry, exit, R, duration, exit reason)
  Block 2 — Exit reason breakdown (SL / TARGET / TIME_STALE / EARLY_LOSS / EXTENSION)
  Block 3 — Adaptive logic impact (savings per feature, extension success rate)
  Block 4 — Daily performance     (expectancy, win rate, net R, profit factor)

Additional metrics beyond user request:
  • Profit Factor
  • Best / Worst trade
  • Win/Loss streaks
  • Avg duration: winners vs losers
  • Strategy breakdown (expectancy per strategy)
  • R-distribution buckets

Persistence:
  data/trade_analytics_YYYY-MM-DD.json — appended after each trade close,
  reloaded on startup so restarts within the same trading day preserve all data.

Calling convention:
  analytics = TradeAnalytics()
  analytics.record_closed_trade(
      order, ltp, action, adaptive_reason, was_extended, r_at_extension
  )
  analytics.mark_extension(oid, r_multiple)   # called when extension fires
  print(analytics.daily_report())             # plain text
  print(analytics.telegram_report())          # HTML — send via notifier
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR  = os.path.join(_ROOT, "data")

# Baseline: assume a full SL hit = −1.0R (definition of 1 unit of risk)
_BASELINE_SL_R = -1.0


# ─────────────────────────────────────────────────────────────────────────────
# Per-trade record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClosedTradeRecord:
    """One entry per closed trade — the atomic unit of the analytics layer."""
    symbol:           str
    strategy:         str
    direction:        str          # BUY | SELL
    entry_price:      float
    exit_price:       float
    stop_loss:        float        # stop at time of close (may have been trailed)
    target:           float
    r_multiple:       float        # realised R-multiple at exit
    duration_minutes: float        # minutes from placed_at to close
    exit_reason:      str          # SL / TARGET / TIME_STALE / EARLY_LOSS / EXTENSION / EMERGENCY
    was_extended:     bool         # trade went through profit extension
    r_at_extension:   float        # R when extension was triggered (0 if not extended)
    timestamp:        str          # ISO close timestamp


# ─────────────────────────────────────────────────────────────────────────────
# Main analytics engine
# ─────────────────────────────────────────────────────────────────────────────

class TradeAnalytics:
    """
    Accumulates trade outcomes during a trading session and computes all
    four analytics blocks on demand.

    Thread safety: the TradeMonitor worker is single-threaded, so no lock needed.
    """

    def __init__(self) -> None:
        self._date:   str                       = datetime.now().strftime("%Y-%m-%d")
        self._trades: List[ClosedTradeRecord]   = []
        # Pending extension R-level: oid → R when extension was triggered
        self._pending_extension_r: Dict[str, float] = {}
        self._load()
        log.info("[TradeAnalytics] Initialised (date=%s, loaded=%d trades).",
                 self._date, len(self._trades))

    # ─────────────────────────────────────────────────────────────────
    # Public API — called by TradeMonitor
    # ─────────────────────────────────────────────────────────────────

    def mark_extension(self, oid: str, r_at_extension: float) -> None:
        """
        Call this when _evaluate() fires the extension intercept so we can
        record the R baseline for later impact calculation.
        """
        self._pending_extension_r[oid] = r_at_extension

    def record_closed_trade(
        self,
        order,                          # OrderRecord
        ltp: float,                     # exit price
        action: str,                    # close_sl | close_target | adaptive_exit | …
        adaptive_reason: Optional[str], # TIME_STALE | EARLY_LOSS | None
        was_extended: bool,             # True if _extended[oid] was set
        *,
        close_time: Optional[datetime] = None,
    ) -> None:
        """
        Called from TradeMonitor._act() for every trade close.
        """
        entry   = order.entry_price
        sl      = order.stop_loss
        target  = getattr(order, "target",   0.0) or 0.0
        risk    = abs(entry - sl) if sl else 0.0
        is_long = order.direction == "BUY"

        # Realised R-multiple
        if risk > 0:
            r_multiple = ((ltp - entry) / risk) if is_long else ((entry - ltp) / risk)
        else:
            r_multiple = 0.0
        r_multiple = round(r_multiple, 3)

        # Duration
        placed_at = (getattr(order, "placed_at",  None)
                     or getattr(order, "created_at", None))
        now = close_time or datetime.now()
        duration_minutes = (
            round((now - placed_at).total_seconds() / 60, 1)
            if placed_at else 0.0
        )

        # Exit reason label
        exit_reason = self._classify_exit(action, adaptive_reason, was_extended)

        # R when extension was triggered
        r_at_ext = self._pending_extension_r.pop(order.order_id, 0.0)

        rec = ClosedTradeRecord(
            symbol           = order.symbol,
            strategy         = getattr(order, "strategy", "unknown") or "unknown",
            direction        = order.direction,
            entry_price      = round(entry, 2),
            exit_price       = round(ltp, 2),
            stop_loss        = round(sl, 2) if sl else 0.0,
            target           = round(target, 2),
            r_multiple       = r_multiple,
            duration_minutes = duration_minutes,
            exit_reason      = exit_reason,
            was_extended     = was_extended,
            r_at_extension   = round(r_at_ext, 3),
            timestamp        = now.isoformat(),
        )
        self._trades.append(rec)
        self._save()
        log.info(
            "[TradeAnalytics] Trade recorded: %s %s  exit=%s  r=%.2fR  "
            "dur=%.0fmin  reason=%s  extended=%s",
            rec.symbol, rec.direction, exit_reason,
            r_multiple, duration_minutes, exit_reason, was_extended,
        )

    # ─────────────────────────────────────────────────────────────────
    # Report generation
    # ─────────────────────────────────────────────────────────────────

    def daily_report(self) -> str:
        """Plain-text daily performance report covering all 4 blocks."""
        if not self._trades:
            return f"[TradeAnalytics] No trades recorded for {self._date}."

        b1 = self._block1_trade_log()
        b2 = self._block2_exit_breakdown()
        b3 = self._block3_adaptive_impact()
        b4 = self._block4_daily_summary()
        verdict = self._verdict(b4)

        sep = "═" * 56
        return "\n".join([
            sep,
            f"  📊 AI PERFORMANCE REPORT — {self._date}",
            sep,
            b1, "",
            b2, "",
            b3, "",
            b4, "",
            verdict,
            sep,
        ])

    def telegram_report(self) -> str:
        """HTML-formatted Telegram message (compatible with parse_mode=HTML)."""
        if not self._trades:
            return f"<b>📊 Performance Report {self._date}</b>\nNo trades recorded today."

        b2 = self._block2_exit_breakdown_tg()
        b3 = self._block3_adaptive_impact_tg()
        b4 = self._block4_daily_summary_tg()
        verdict = self._verdict_tg(self._compute_summary())

        return "\n".join([
            f"<b>📊 AI PERFORMANCE REPORT — {self._date}</b>",
            "",
            b4,
            "",
            b2,
            "",
            b3,
            "",
            verdict,
        ])

    # ─────────────────────────────────────────────────────────────────
    # Block 1 — Trade-level log
    # ─────────────────────────────────────────────────────────────────

    def _block1_trade_log(self) -> str:
        lines = ["── Block 1: Trade Log ──────────────────────────────────────"]
        hdr = f"{'SYMBOL':<12} {'DIR':<5} {'ENTRY':>8} {'EXIT':>8} {'R':>6} {'DUR':>6} {'REASON':<12}"
        lines.append(hdr)
        lines.append("─" * 60)
        for t in sorted(self._trades, key=lambda x: x.timestamp):
            ext_mark = "⚡" if t.was_extended else " "
            lines.append(
                f"{t.symbol:<12} {t.direction:<5} {t.entry_price:>8.2f} "
                f"{t.exit_price:>8.2f} {t.r_multiple:>+6.2f}R "
                f"{t.duration_minutes:>5.0f}m {ext_mark}{t.exit_reason:<12}"
            )
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    # Block 2 — Exit reason breakdown
    # ─────────────────────────────────────────────────────────────────

    def _block2_exit_breakdown(self) -> str:
        counts = self._exit_counts()
        total  = sum(counts.values())
        lines  = ["── Block 2: Exit Reason Breakdown ─────────────────────────"]
        order  = ["SL", "TARGET", "TIME_STALE", "EARLY_LOSS", "EXTENSION", "EMERGENCY"]
        for k in order:
            n = counts.get(k, 0)
            pct = n / total * 100 if total else 0
            lines.append(f"  {k:<14} {n:>3}  ({pct:4.0f}%)")
        # any other reason not in standard set
        for k, n in counts.items():
            if k not in order:
                pct = n / total * 100 if total else 0
                lines.append(f"  {k:<14} {n:>3}  ({pct:4.0f}%)")
        return "\n".join(lines)

    def _block2_exit_breakdown_tg(self) -> str:
        counts = self._exit_counts()
        total  = sum(counts.values())
        lines  = ["<b>📤 Exit Breakdown</b>"]
        icons  = {"SL": "🔴", "TARGET": "🟢", "TIME_STALE": "⏱", "EARLY_LOSS": "📉",
                  "EXTENSION": "⚡", "EMERGENCY": "🚨"}
        for k in ["SL", "TARGET", "TIME_STALE", "EARLY_LOSS", "EXTENSION"]:
            n   = counts.get(k, 0)
            pct = n / total * 100 if total else 0
            ico = icons.get(k, "•")
            lines.append(f"{ico} {k}: <b>{n}</b>  ({pct:.0f}%)")
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    # Block 3 — Adaptive logic impact
    # ─────────────────────────────────────────────────────────────────

    def _block3_adaptive_impact(self) -> str:
        early  = self._early_loss_impact()
        time_e = self._time_exit_impact()
        ext    = self._extension_impact()

        lines = ["── Block 3: Adaptive Logic Impact ─────────────────────────"]

        # A — Early Loss
        if early["count"] > 0:
            lines.append(
                f"  A. Early Loss (n={early['count']})\n"
                f"     Baseline SL    = {_BASELINE_SL_R:+.1f}R\n"
                f"     Avg exit R     = {early['avg_r']:+.2f}R\n"
                f"     Saving/trade   = {early['saving_per_trade']:+.2f}R\n"
                f"     Total saved    = {early['total_saved']:+.2f}R  ✅"
            )
        else:
            lines.append("  A. Early Loss: no trades.")

        # B — Time Exit
        if time_e["count"] > 0:
            lines.append(
                f"  B. Time Exit (n={time_e['count']})\n"
                f"     Stale trades removed  = {time_e['count']}\n"
                f"     Capital time freed    = {time_e['hours_freed']:.1f} hours\n"
                f"     Avg R at stale exit   = {time_e['avg_r']:+.2f}R"
            )
        else:
            lines.append("  B. Time Exit: no stale trades removed.")

        # C — Extension
        if ext["total"] > 0:
            rate = ext["successful"] / ext["total"] * 100
            lines.append(
                f"  C. Extension (n={ext['total']})\n"
                f"     Success rate          = {rate:.0f}%  "
                f"({'✅' if rate >= 50 else '⚠️'})\n"
                f"     Successful = {ext['successful']}  |  Failed = {ext['failed']}\n"
                f"     Avg gain (successful) = {ext['avg_gain']:+.2f}R\n"
                f"     Avg loss  (failed)    = {ext['avg_fail']:+.2f}R\n"
                f"     Net extension R       = {ext['net_r']:+.2f}R"
            )
        else:
            lines.append("  C. Extension: no extended trades.")

        return "\n".join(lines)

    def _block3_adaptive_impact_tg(self) -> str:
        early  = self._early_loss_impact()
        time_e = self._time_exit_impact()
        ext    = self._extension_impact()

        lines = ["<b>🤖 Adaptive Logic Impact</b>"]

        if early["count"] > 0:
            lines.append(
                f"📉 Early Loss (n={early['count']}): "
                f"saved {early['total_saved']:+.2f}R total "
                f"({early['saving_per_trade']:+.2f}R/trade)"
            )

        if time_e["count"] > 0:
            lines.append(
                f"⏱ Time Exit (n={time_e['count']}): "
                f"{time_e['hours_freed']:.1f}h freed"
            )

        if ext["total"] > 0:
            rate = ext["successful"] / ext["total"] * 100
            lines.append(
                f"⚡ Extension (n={ext['total']}): "
                f"<b>{rate:.0f}%</b> success rate · "
                f"net {ext['net_r']:+.2f}R"
            )

        if len(lines) == 1:
            lines.append("No adaptive features triggered today.")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    # Block 4 — Daily performance summary
    # ─────────────────────────────────────────────────────────────────

    def _block4_daily_summary(self) -> str:
        s = self._compute_summary()
        lines = [
            "── Block 4: Daily Performance Summary ─────────────────────",
            f"  Trades      : {s['total']}",
            f"  Wins        : {s['wins']}   |   Losses : {s['losses']}",
            f"  Win Rate    : {s['win_rate']:.1f}%",
            "",
            f"  Avg Win     : +{s['avg_win']:.2f}R",
            f"  Avg Loss    :  {s['avg_loss']:.2f}R",
            f"  Expectancy  : {s['expectancy']:+.3f}R per trade  "
            f"({'✅' if s['expectancy'] > 0 else '❌'})",
            "",
            f"  Net R       : {s['net_r']:+.2f}R",
            f"  Profit Factor: {s['profit_factor']:.2f}",
            "",
            f"  Best trade  : {s['best_r']:+.2f}R  ({s['best_sym']})",
            f"  Worst trade : {s['worst_r']:+.2f}R  ({s['worst_sym']})",
            f"  Max Win streak  : {s['max_win_streak']}",
            f"  Max Loss streak : {s['max_loss_streak']}",
            f"  Avg duration — winners : {s['avg_dur_win']:.0f} min",
            f"  Avg duration — losers  : {s['avg_dur_loss']:.0f} min",
        ]

        # R-Distribution
        buckets = s["r_buckets"]
        lines += [
            "",
            "  R-Distribution:",
            f"    < -1.0R : {buckets['below_m1']}",
            f"    -1R–0R  : {buckets['m1_to_0']}",
            f"     0R–1R  : {buckets['p0_to_1']}",
            f"     1R–2R  : {buckets['p1_to_2']}",
            f"     2R–3R  : {buckets['p2_to_3']}",
            f"    > +3R   : {buckets['above_p3']}",
        ]

        # Per-strategy
        strat = s["strategy_breakdown"]
        if strat:
            lines.append("\n  Strategy Breakdown:")
            for name, st in sorted(strat.items(), key=lambda x: -x[1]["expectancy"]):
                lines.append(
                    f"    {name:<22} WR={st['win_rate']:.0f}%  "
                    f"Exp={st['expectancy']:+.2f}R  (n={st['n']})"
                )

        return "\n".join(lines)

    def _block4_daily_summary_tg(self) -> str:
        s = self._compute_summary()
        ok = s["expectancy"] > 0
        lines = [
            f"<b>📈 Daily Summary</b>",
            f"Trades: <b>{s['total']}</b>  |  Win Rate: <b>{s['win_rate']:.1f}%</b>",
            f"Net P&amp;L: <b>{s['net_r']:+.2f}R</b>  |  Profit Factor: <b>{s['profit_factor']:.2f}</b>",
            "",
            f"Avg Win: <b>+{s['avg_win']:.2f}R</b>  |  Avg Loss: <b>{s['avg_loss']:.2f}R</b>",
            f"Expectancy: <b>{s['expectancy']:+.3f}R/trade</b>",
        ]
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    # Verdict
    # ─────────────────────────────────────────────────────────────────

    def _verdict(self, block4_text: str) -> str:
        s = self._compute_summary()
        v = self._verdict_line(s)
        return f"── VERDICT ─────────────────────────────────────────────────\n  {v}"

    def _verdict_tg(self, s: dict) -> str:
        v = self._verdict_line(s)
        return f"<b>🏁 VERDICT</b>\n{v}"

    def _verdict_line(self, s: dict) -> str:
        exp = s["expectancy"]
        wr  = s["win_rate"]
        tot = s["total"]
        if tot < 3:
            return "⏳ Insufficient data — need ≥3 trades for reliable verdict."
        if exp > 0.3 and wr >= 50:
            return f"✅ System improving expectancy ({exp:+.3f}R/trade, WR={wr:.0f}%)"
        if exp > 0:
            return f"⚠️  Marginally positive ({exp:+.3f}R/trade) — monitor closely."
        return f"❌ Negative expectancy ({exp:+.3f}R/trade) — review thresholds."

    # ─────────────────────────────────────────────────────────────────
    # Metric computation helpers
    # ─────────────────────────────────────────────────────────────────

    def _exit_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for t in self._trades:
            counts[t.exit_reason] += 1
        return dict(counts)

    def _early_loss_impact(self) -> dict:
        early = [t for t in self._trades if t.exit_reason == "EARLY_LOSS"]
        if not early:
            return {"count": 0, "avg_r": 0.0, "saving_per_trade": 0.0, "total_saved": 0.0}
        avg_r = statistics.mean(t.r_multiple for t in early)
        saving_per = avg_r - _BASELINE_SL_R   # e.g. -0.6 - (-1.0) = +0.4
        return {
            "count":            len(early),
            "avg_r":            round(avg_r, 3),
            "saving_per_trade": round(saving_per, 3),
            "total_saved":      round(saving_per * len(early), 3),
        }

    def _time_exit_impact(self) -> dict:
        stale = [t for t in self._trades if t.exit_reason == "TIME_STALE"]
        if not stale:
            return {"count": 0, "hours_freed": 0.0, "avg_r": 0.0}
        return {
            "count":       len(stale),
            "hours_freed": round(sum(t.duration_minutes for t in stale) / 60, 1),
            "avg_r":       round(statistics.mean(t.r_multiple for t in stale), 3),
        }

    def _extension_impact(self) -> dict:
        exts = [t for t in self._trades if t.was_extended]
        if not exts:
            return {"total": 0, "successful": 0, "failed": 0,
                    "avg_gain": 0.0, "avg_fail": 0.0, "net_r": 0.0}

        # Successful = exit R > R at time of extension (genuinely extended the gain)
        successful = [t for t in exts if t.r_multiple > t.r_at_extension]
        failed     = [t for t in exts if t.r_multiple <= t.r_at_extension]

        avg_gain = (statistics.mean(t.r_multiple - t.r_at_extension for t in successful)
                    if successful else 0.0)
        avg_fail = (statistics.mean(t.r_multiple - t.r_at_extension for t in failed)
                    if failed else 0.0)
        net_r    = sum(t.r_multiple - t.r_at_extension for t in exts)

        return {
            "total":      len(exts),
            "successful": len(successful),
            "failed":     len(failed),
            "avg_gain":   round(avg_gain, 3),
            "avg_fail":   round(avg_fail, 3),
            "net_r":      round(net_r, 3),
        }

    def _compute_summary(self) -> dict:
        trades = self._trades
        if not trades:
            return {
                "total": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0, "expectancy": 0.0,
                "net_r": 0.0, "profit_factor": 0.0,
                "best_r": 0.0, "best_sym": "-", "worst_r": 0.0, "worst_sym": "-",
                "max_win_streak": 0, "max_loss_streak": 0,
                "avg_dur_win": 0.0, "avg_dur_loss": 0.0,
                "r_buckets": {"below_m1":0,"m1_to_0":0,"p0_to_1":0,
                              "p1_to_2":0,"p2_to_3":0,"above_p3":0},
                "strategy_breakdown": {},
            }

        rs    = [t.r_multiple for t in trades]
        wins  = [t for t in trades if t.r_multiple > 0]
        losses= [t for t in trades if t.r_multiple <= 0]

        total       = len(trades)
        n_wins      = len(wins)
        n_losses    = len(losses)
        win_rate    = n_wins / total * 100
        avg_win_r   = statistics.mean(t.r_multiple for t in wins)  if wins   else 0.0
        avg_loss_r  = statistics.mean(t.r_multiple for t in losses) if losses else 0.0  # negative
        net_r       = sum(rs)
        sum_pos     = sum(r for r in rs if r > 0)
        sum_neg     = abs(sum(r for r in rs if r < 0))
        pf          = round(sum_pos / sum_neg, 2) if sum_neg > 0 else (99.0 if sum_pos > 0 else 0.0)
        expectancy  = (win_rate/100 * avg_win_r) + ((1 - win_rate/100) * avg_loss_r)

        best  = max(trades, key=lambda t: t.r_multiple)
        worst = min(trades, key=lambda t: t.r_multiple)

        # Streaks
        max_ws = max_ls = cur_ws = cur_ls = 0
        for t in trades:
            if t.r_multiple > 0:
                cur_ws += 1; cur_ls = 0
            else:
                cur_ls += 1; cur_ws = 0
            max_ws = max(max_ws, cur_ws)
            max_ls = max(max_ls, cur_ls)

        # Avg duration
        avg_dur_win  = statistics.mean(t.duration_minutes for t in wins)  if wins   else 0.0
        avg_dur_loss = statistics.mean(t.duration_minutes for t in losses) if losses else 0.0

        # R buckets
        def _bucket(r):
            if r < -1.0:        return "below_m1"
            elif r < 0.0:       return "m1_to_0"
            elif r < 1.0:       return "p0_to_1"
            elif r < 2.0:       return "p1_to_2"
            elif r < 3.0:       return "p2_to_3"
            else:               return "above_p3"
        buckets: Dict[str, int] = defaultdict(int)
        for t in trades:
            buckets[_bucket(t.r_multiple)] += 1

        # Strategy breakdown
        strat_groups: Dict[str, List[ClosedTradeRecord]] = defaultdict(list)
        for t in trades:
            strat_groups[t.strategy].append(t)
        strat_breakdown = {}
        for name, grp in strat_groups.items():
            w  = [t for t in grp if t.r_multiple > 0]
            l  = [t for t in grp if t.r_multiple <= 0]
            wr = len(w) / len(grp) * 100
            aw = statistics.mean(t.r_multiple for t in w) if w else 0.0
            al = statistics.mean(t.r_multiple for t in l) if l else 0.0
            exp = (wr/100 * aw) + ((1 - wr/100) * al)
            strat_breakdown[name] = {
                "n": len(grp), "win_rate": round(wr,1),
                "avg_win": round(aw,3), "avg_loss": round(al,3),
                "expectancy": round(exp, 3),
            }

        return {
            "total":             total,
            "wins":              n_wins,
            "losses":            n_losses,
            "win_rate":          round(win_rate, 2),
            "avg_win":           round(avg_win_r, 3),
            "avg_loss":          round(avg_loss_r, 3),
            "expectancy":        round(expectancy, 4),
            "net_r":             round(net_r, 3),
            "profit_factor":     pf,
            "best_r":            round(best.r_multiple, 2),
            "best_sym":          best.symbol,
            "worst_r":           round(worst.r_multiple, 2),
            "worst_sym":         worst.symbol,
            "max_win_streak":    max_ws,
            "max_loss_streak":   max_ls,
            "avg_dur_win":       round(avg_dur_win, 1),
            "avg_dur_loss":      round(avg_dur_loss, 1),
            "r_buckets":         {k: buckets.get(k, 0) for k in
                                  ["below_m1","m1_to_0","p0_to_1","p1_to_2","p2_to_3","above_p3"]},
            "strategy_breakdown": strat_breakdown,
        }

    # ─────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────

    def _filepath(self) -> str:
        return os.path.join(_DATA_DIR, f"trade_analytics_{self._date}.json")

    def _save(self) -> None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        try:
            with open(self._filepath(), "w", encoding="utf-8") as f:
                json.dump([asdict(t) for t in self._trades], f, indent=2)
        except Exception as exc:
            log.warning("[TradeAnalytics] Save failed: %s", exc)

    def _load(self) -> None:
        fp = self._filepath()
        if not os.path.exists(fp):
            return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                rows = json.load(f)
            self._trades = [ClosedTradeRecord(**r) for r in rows]
        except Exception as exc:
            log.warning("[TradeAnalytics] Load failed: %s", exc)
            self._trades = []

    # ─────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_exit(action: str, adaptive_reason: Optional[str],
                        was_extended: bool) -> str:
        """Map trade-monitor action → human exit label."""
        if was_extended:
            return "EXTENSION"       # any close on an extended trade → EXTENSION
        if action == "close_sl":
            return "SL"
        if action == "close_target":
            return "TARGET"
        if action == "adaptive_exit":
            return (adaptive_reason or "ADAPTIVE").upper()
        if action == "close_emergency":
            return "EMERGENCY"
        if action == "close_eod":
            return "EOD_CLOSE"
        return action.upper().replace("CLOSE_", "")

    # ─────────────────────────────────────────────────────────────────
    # Accessors
    # ─────────────────────────────────────────────────────────────────

    def get_trades(self) -> List[ClosedTradeRecord]:
        return list(self._trades)

    def trade_count(self) -> int:
        return len(self._trades)

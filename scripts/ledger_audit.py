"""
Historical Ledger Audit — Strategy Bias Check
Reads paper_trades.csv with the corrected 15-column header and produces
a complete picture of each strategy's real performance history.
"""
import csv, os, sys
from datetime import datetime
from collections import defaultdict

BASELINE_DATE = "2026-04-27"  # Ledger B start
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "paper_trades.csv")

_SKIP_REASONS = {
    "SYSTEM_CLEANUP", "REPLACEMENT",
    "emergency_close", "close_emergency",
}

def load_trades():
    if not os.path.exists(CSV_PATH):
        print("paper_trades.csv not found"); sys.exit(1)

    opens = {}   # order_id -> open row
    trades = []  # completed trade dicts

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            event = row.get("event", "").strip().upper()
            oid   = row.get("order_id", "").strip()
            if not oid:
                continue
            if event in ("OPEN", "REENTRY_OPEN"):
                opens[oid] = row
            elif event in ("CLOSE", "CANCELLED"):
                open_row = opens.pop(oid, None)
                strategy  = row.get("strategy", "") or (open_row.get("strategy","") if open_row else "")
                reason    = row.get("reason", "").strip()
                ts        = row.get("timestamp", "")
                date_str  = ts[:10]
                try:
                    pnl   = float(row.get("pnl", 0) or 0)
                    entry = float(row.get("entry_price", 0) or 0)
                    sl    = float(row.get("stop_loss", 0) or 0)
                    qty   = int(float(row.get("quantity", 1) or 1))
                    exit_ = float(row.get("exit_price", 0) or 0)
                    r_risk = abs(entry - sl) if sl else 1.0
                    r_mult = pnl / (r_risk * qty) if (r_risk * qty) else 0.0
                except (ValueError, TypeError):
                    pnl = exit_ = r_mult = 0.0

                trades.append({
                    "oid": oid, "date": date_str, "strategy": strategy,
                    "symbol": row.get("symbol",""), "direction": row.get("direction",""),
                    "pnl": pnl, "r_mult": r_mult, "reason": reason,
                    "ledger": "B" if date_str >= BASELINE_DATE else "A",
                    "excluded": reason in _SKIP_REASONS,
                })
    return trades, opens

def audit(trades, open_positions=None):
    print("=" * 80)
    print("  HISTORICAL LEDGER AUDIT — Strategy Bias Check")
    print(f"  Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    # ── Full trade table ──────────────────────────────────────────────────────
    print("\nALL CLOSED TRADES (chronological):\n")
    print(f"  {'Date':10}  {'Sym':12}  {'Dir':5}  {'Strategy':25}  {'PnL':>12}  {'R':>7}  {'Reason':30}  {'Ledger':6}  {'Eval?':6}")
    print("  " + "-"*115)
    for t in trades:
        flag = "SKIP" if t["excluded"] else "EVAL"
        pnl_s = f"₹{t['pnl']:+,.0f}"
        r_s   = f"{t['r_mult']:+.2f}R"
        print(f"  {t['date']}  {t['symbol']:12}  {t['direction']:5}  {t['strategy']:25}  {pnl_s:>12}  {r_s:>7}  {t['reason']:30}  {t['ledger']:6}  {flag}")

    # ── Per-strategy breakdown ────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  PER-STRATEGY BREAKDOWN (Ledger B official only — excludes SKIP reasons)\n")

    by_strat = defaultdict(lambda: {"wins":0,"losses":0,"draws":0,"pnl":0.0,"r_list":[],"dates":[]})
    for t in trades:
        if t["ledger"] != "B" or t["excluded"]:
            continue
        s = by_strat[t["strategy"]]
        s["pnl"]    += t["pnl"]
        s["r_list"].append(t["r_mult"])
        s["dates"].append(t["date"])
        if t["pnl"] > 0:   s["wins"]   += 1
        elif t["pnl"] < 0: s["losses"] += 1
        else:               s["draws"]  += 1

    if not by_strat:
        print("  No official Ledger B evaluable trades found.")
    else:
        print(f"  {'Strategy':30}  {'Trades':>6}  {'WR%':>6}  {'Net PnL':>12}  {'AvgR':>7}  {'Bias?'}")
        print("  " + "-"*85)
        for strat, s in sorted(by_strat.items()):
            n = s["wins"] + s["losses"] + s["draws"]
            wr = 100 * s["wins"] / n if n else 0
            avg_r = sum(s["r_list"]) / len(s["r_list"]) if s["r_list"] else 0
            pnl_s = f"₹{s['pnl']:+,.0f}"
            # Bias check: always-0 R means pnl never recorded properly
            all_zero_r = all(r == 0.0 for r in s["r_list"])
            bias = "⚠️  ALL R=0 (CSV bug?)" if all_zero_r and n > 0 else ("✅ OK" if n > 0 else "—")
            print(f"  {strat:30}  {n:>6}  {wr:>6.1f}  {pnl_s:>12}  {avg_r:>+7.2f}R  {bias}")

    # ── SESSION_EXPIRED sub-audit ─────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  SESSION_EXPIRED TRADES — learning inclusion check\n")
    se_trades = [t for t in trades if "SESSION_EXPIRED" in t["reason"]]
    if not se_trades:
        print("  No SESSION_EXPIRED trades found.")
    else:
        print(f"  {'Date':10}  {'Sym':12}  {'Strategy':25}  {'PnL':>12}  {'R':>7}  {'Reason':30}  {'Action':20}")
        print("  " + "-"*100)
        for t in se_trades:
            action = "INCLUDE (real pnl)" if t["pnl"] != 0 else "SKIP (zero pnl)"
            pnl_s = f"₹{t['pnl']:+,.0f}"
            r_s   = f"{t['r_mult']:+.2f}R"
            print(f"  {t['date']}  {t['symbol']:12}  {t['strategy']:25}  {pnl_s:>12}  {r_s:>7}  {t['reason']:30}  {action}")

    # ── EdgeDiscovery strategies ──────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  EDGE DISCOVERY STRATEGIES — any real trade history?\n")
    edg_trades = [t for t in trades if t["strategy"].startswith("EDG_")]
    if not edg_trades:
        print("  No EdgeDiscovery trades in journal yet (expected at this stage).")
    else:
        by_edg = defaultdict(lambda: {"n":0,"pnl":0.0})
        for t in edg_trades:
            by_edg[t["strategy"]]["n"]   += 1
            by_edg[t["strategy"]]["pnl"] += t["pnl"]
        for strat, s in sorted(by_edg.items()):
            print(f"  {strat:40}  trades={s['n']}  pnl=₹{s['pnl']:+,.0f}")

    print("\n" + "=" * 80)
    print("  OPEN POSITIONS (no CLOSE row yet)\n")
    if not open_positions:
        print("  None.")
    else:
        for oid, r in open_positions.items():
            print(f"  {r.get('timestamp','')[:16]}  {r.get('symbol',''):12}  {r.get('direction',''):5}  {r.get('strategy',''):25}  entry={r.get('entry_price','')}  oid={oid}")

    print("\n" + "=" * 80)
    print("  Audit complete.")
    print("=" * 80)

if __name__ == "__main__":
    trades, open_positions = load_trades()
    audit(trades, open_positions)

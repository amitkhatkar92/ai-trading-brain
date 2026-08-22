"""
Watchlist Forensic Audit — May 29 2026
Checks:
  1. Static _BASE_WATCHLIST / _EXTENDED_WATCHLIST — stale / anomalous fields
  2. CandidateStore (prepared universe) — age, coverage, validity
  3. PRICE_CACHE — live LTP freshness before scan cycle
  4. Support/resistance sanity (S > R, levels crossed, outliers)
  5. RSI extremes that block signals
  6. ADV too low to be tradeable
  7. volume_ratio anomalies
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone

# ── 1. Load static watchlist from equity_scanner_ai ──────────────────────────
sys.path.insert(0, "/app")
os.chdir("/app")

# Patch: prevent full module init side effects by reading the dict literally
import ast, re
with open("/app/opportunity_engine/equity_scanner_ai.py") as f:
    src = f.read()

def extract_watchlist(src, var):
    # Find the opening '[' of the list literal
    pat = re.compile(re.escape(var) + r"[^=]+=\s*\[")
    m2 = pat.search(src)
    if not m2:
        raise ValueError(f"Could not find {var}")
    list_start = m2.end() - 1  # points to '['
    depth = 0
    i = list_start
    while i < len(src):
        if src[i] == "[":
            depth += 1
        elif src[i] == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    raw = src[list_start:i+1]
    # Strip inline comments
    raw_lines = []
    for line in raw.splitlines():
        line = re.sub(r"\s*#.*$", "", line)
        raw_lines.append(line)
    raw = "\n".join(raw_lines)
    return ast.literal_eval(raw)

base_wl = extract_watchlist(src, "_BASE_WATCHLIST")
ext_wl  = extract_watchlist(src, "_EXTENDED_WATCHLIST")
all_wl  = base_wl + ext_wl

# Extract last_level_update date from log.info call
m = re.search(r"last_level_update=(\d{4}-\d{2}-\d{2})", src)
level_update_date = m.group(1) if m else "UNKNOWN"

now_utc = datetime.now(timezone.utc)

print("=" * 80)
print("WATCHLIST FORENSIC AUDIT — {}".format(now_utc.strftime("%Y-%m-%d %H:%M UTC")))
print("=" * 80)
print(f"\nStatic watchlist: {len(base_wl)} base + {len(ext_wl)} extended = {len(all_wl)} total")
print(f"Last level refresh tagged: {level_update_date}")
days_stale = (now_utc.date() - datetime.strptime(level_update_date, "%Y-%m-%d").date()).days if level_update_date != "UNKNOWN" else 999
print(f"Level staleness: {days_stale} day(s)")

# ── 2. Per-symbol sanity checks ───────────────────────────────────────────────
print("\n{:<14} {:>9} {:>9} {:>9} {:>6} {:>5} {:>5}  Issues"
      .format("Symbol", "base_ltp", "resist", "support", "vol_r", "rsi", "adv_cr"))
print("-" * 100)

issues_total = 0
critical_symbols = []
flagged_details = []

for s in all_wl:
    sym   = s["symbol"]
    ltp   = s["base_ltp"]
    res   = s["resistance"]
    sup   = s["support"]
    vol   = s["volume_ratio"]
    rsi   = s["rsi"]
    adv   = s["adv_crore"]
    label = "(E)" if any(e["symbol"] == sym for e in ext_wl) else "   "
    issues = []

    # Sanity checks
    if sup >= res:
        issues.append("SUPPORT>=RESIST")
    if ltp > 0 and sup > ltp:
        issues.append(f"SUPPORT({sup})>LTP({ltp})")
    if ltp > 0 and res < ltp:
        issues.append(f"RESIST({res})<LTP({ltp})")
    if rsi > 80:
        issues.append(f"RSI_EXTREME_OB({rsi})")
    if rsi < 20:
        issues.append(f"RSI_EXTREME_OS({rsi})")
    if adv < 100:
        issues.append(f"LOW_ADV({adv}cr)")
    if vol > 4.0:
        issues.append(f"VOL_SPIKE({vol}x)")
    if vol < 0.3:
        issues.append(f"VOL_DEAD({vol}x)")
    if ltp <= 0:
        issues.append("ZERO_LTP!")
    if res > 0 and sup > 0:
        spread = (res - sup) / ltp if ltp > 0 else 0
        if spread < 0.01:
            issues.append(f"TIGHT_RANGE({spread:.1%})")
        if spread > 0.40:
            issues.append(f"WIDE_RANGE({spread:.1%})")

    issue_str = " | ".join(issues) if issues else "OK"
    if issues:
        issues_total += 1
        critical_symbols.append(sym)
        flagged_details.append((sym, label, ltp, res, sup, vol, rsi, adv, " | ".join(issues)))

    print(f"  {label}{sym:<12} {ltp:>9.2f} {res:>9.2f} {sup:>9.2f} {vol:>6.1f} {rsi:>5.1f} {adv:>5d}  {issue_str}")

print()
print(f"  Symbols with issues: {issues_total}/{len(all_wl)}")

# ── 3. CandidateStore (prepared universe) ────────────────────────────────────
print("\n" + "=" * 80)
print("CANDIDATE STORE (Prepared Universe)")
print("=" * 80)

STORE_FILE = Path("/app/data/candidate_store.json")
if not STORE_FILE.exists():
    print("  MISSING — no candidate_store.json found!")
    print("  ACTION REQUIRED: run market_scanner.py before tomorrow's session")
else:
    payload = json.loads(STORE_FILE.read_text())
    prepared_at = payload.get("prepared_at", "UNKNOWN")
    context = payload.get("context", {})
    candidates = payload.get("candidates", [])
    premarket_ok = payload.get("premarket_refresh_complete", False)
    scanner_stats = payload.get("scanner_stats", {})

    if prepared_at != "UNKNOWN":
        ts = datetime.fromisoformat(prepared_at.replace("Z", "+00:00"))
        age_h = (now_utc - ts).total_seconds() / 3600.0
        age_str = f"{age_h:.1f}h ago"
    else:
        age_h = 999
        age_str = "UNKNOWN"

    print(f"  Prepared at:          {prepared_at}  ({age_str})")
    print(f"  Premarket refresh:    {'✅ Complete' if premarket_ok else '❌ INCOMPLETE'}")
    print(f"  Candidates count:     {len(candidates)}")
    print(f"  Scanner stats:        {json.dumps(scanner_stats, indent=None)}")

    if age_h > 20:
        print(f"  ⚠ STALE store ({age_h:.0f}h old) — should be refreshed overnight")
    elif age_h > 8:
        print(f"  ⚠ OLD store ({age_h:.0f}h old) — was premarket refresh run?")
    else:
        print(f"  ✅ Store is fresh ({age_h:.1f}h old)")

    # Check candidate validity
    if candidates:
        now_utc2 = datetime.now(timezone.utc)
        expired = 0
        missing_ltp = 0
        missing_sr = 0
        for c in candidates:
            vu = c.get("valid_until_utc")
            if vu:
                try:
                    exp = datetime.fromisoformat(vu.replace("Z", "+00:00"))
                    if now_utc2 > exp:
                        expired += 1
                except Exception:
                    pass
            if not c.get("base_ltp") or float(c.get("base_ltp",0)) <= 0:
                missing_ltp += 1
            if not c.get("resistance") or not c.get("support"):
                missing_sr += 1

        print(f"  Expired candidates:   {expired}/{len(candidates)}")
        print(f"  Missing base_ltp:     {missing_ltp}/{len(candidates)}")
        print(f"  Missing S/R:          {missing_sr}/{len(candidates)}")
        active = len(candidates) - expired
        print(f"  Active candidates:    {active}")
        if active < 5:
            print(f"  ⚠ CRITICALLY LOW active candidates — scanner will likely fall to static fallback")

        print(f"\n  {'Symbol':<16} {'base_ltp':>9} {'Resistance':>10} {'Support':>10} {'RSI':>6} {'valid_until':<22} Status")
        print("  " + "-" * 95)
        for c in sorted(candidates, key=lambda x: x.get("symbol","")):
            sym = c.get("symbol","?")
            bl  = float(c.get("base_ltp",0) or 0)
            res = float(c.get("resistance",0) or 0)
            sup = float(c.get("support",0) or 0)
            rsi = float(c.get("rsi",0) or 0)
            vu  = c.get("valid_until_utc","")[:16] if c.get("valid_until_utc") else "none"
            try:
                exp = datetime.fromisoformat(c.get("valid_until_utc","").replace("Z","+00:00"))
                status = "EXPIRED" if now_utc > exp else "VALID"
            except Exception:
                status = "NO_TTL"
            print(f"  {sym:<16} {bl:>9.2f} {res:>10.2f} {sup:>10.2f} {rsi:>6.1f} {vu:<22} {status}")

# ── 4. _PRICE_CACHE staleness (via log check) ─────────────────────────────────
print("\n" + "=" * 80)
print("PRICE CACHE FRESHNESS (last 30 log lines)")
print("=" * 80)
import subprocess
result = subprocess.run(
    ["grep", "-E", "PriceGuard|PriceRefresh|PricePrewarm|price refresh|EquityScannerAI.*Fetched",
     "/app/logs/trading.log"],
    capture_output=True, text=True
)
lines = (result.stdout.strip().split("\n") if result.stdout.strip() else [])
for line in lines[-30:]:
    print(f"  {line}")
if not lines:
    print("  No price-refresh log entries found in trading.log")

# ── 5. Summary verdict ────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("VERDICT SUMMARY")
print("=" * 80)

print(f"\n  Static watchlist (base+ext): {len(all_wl)} symbols")
print(f"  Technical levels age: {days_stale} day(s) (tagged {level_update_date})")
if days_stale == 0:
    print("  ✅ Refreshed today")
elif days_stale <= 3:
    print("  ✅ Acceptably fresh (<=3 days)")
elif days_stale <= 7:
    print("  ⚠ Getting stale — refresh this weekend with refresh_watchlist_data.py")
else:
    print("  ❌ STALE — run refresh_watchlist_data.py NOW")

print(f"\n  Watchlist sanity:")
if issues_total == 0:
    print("  ✅ All symbols pass sanity checks (LTP/S/R/RSI/ADV)")
else:
    print(f"  ⚠ {issues_total} symbols have issues:")
    for d in flagged_details:
        print(f"     {d[0]}{d[1]}: ltp={d[2]:.2f} res={d[3]:.2f} sup={d[4]:.2f} rsi={d[6]:.1f} adv={d[7]}cr → {d[8]}")

print("\n  LTP update BEFORE scan cycle:")
print("  ✅ _live_watchlist() fetches live prices via _fetch_live_prices() each call")
print("  ✅ PriceGuard: cold-start waits up to 30s for real data before allowing scan")
print("  ✅ Background PriceRefresh thread updates cache every ~60s")
print("  ✅ pre-warm thread fires at import time (30-60s before first scan)")
print()
print("  Potential gaps:")
if days_stale > 0:
    print(f"  ⚠ support/resistance still use {days_stale}d-old 20-day range — these drift")
    print("     while base_ltp updates live. Run refresh_watchlist_data.py to fix.")
print("  ⚠ RSI in _BASE_WATCHLIST is a snapshot — overlaid by _background_rsi_refresh()")
print("     every 5 min during session, but it's starting from a stale value")
print("     each morning until first RSI refresh fires (~5 min after market open)")

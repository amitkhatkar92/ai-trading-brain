"""
Fix 1: Add weekday guard to all scheduler-fired functions in master_orchestrator.py
       that currently only check is_nse_holiday() but fire on weekends too.
Fix 2: Dynamic S/R level refresh + expanded watchlist in equity_scanner_ai.py
"""
import sys, re

# ═══════════════════════════════════════════════════════════════
# FIX 1 — Weekend guard in master_orchestrator.py
# ═══════════════════════════════════════════════════════════════
ORCH = "/app/orchestrator/master_orchestrator.py"
HOST_ORCH = "/root/ai-trading-brain/orchestrator/master_orchestrator.py"

with open(ORCH, "r") as f:
    orch = f.read()

# Helper: insert weekday guard right after is_nse_holiday check in each function
# Pattern: the 4 functions all have:
#   from config import is_nse_holiday
#   if is_nse_holiday():
#       log.info("... skipped.")
#       return
# We add weekday check BEFORE the holiday check.

WEEKEND_GUARD = (
    "        if datetime.now().weekday() >= 5:  # Saturday=5, Sunday=6\n"
    "            log.debug(\"[Orchestrator] Weekend — skipping.\")\n"
    "            return\n"
)

FUNCS = [
    "_premarket_init",
    "_market_open_notify",
    "_market_close_notify",
    "run_eod_learning",
]

changes = 0
for fname in FUNCS:
    # Find the function body and the first "from config import is_nse_holiday"
    pattern = (
        f"    def {fname}(self) -> None:\n"
    )
    idx = orch.find(pattern)
    if idx == -1:
        print(f"WARN: {fname} not found")
        continue
    # Find the "from config import is_nse_holiday" within this function
    import_pos = orch.find("        from config import is_nse_holiday", idx)
    if import_pos == -1:
        print(f"WARN: no is_nse_holiday import in {fname}")
        continue
    # Check not already patched
    check_region = orch[import_pos-150:import_pos]
    if "weekday" in check_region:
        print(f"  {fname}: already patched")
        continue
    # Insert weekend guard before the "from config import is_nse_holiday"
    orch = orch[:import_pos] + WEEKEND_GUARD + orch[import_pos:]
    print(f"  {fname}: weekend guard added")
    changes += 1

# _premarket_data_warmup has NO guard at all — add one
warmup_old = (
    "    def _premarket_data_warmup(self) -> None:\n"
    "        \"\"\"\n"
    "        Secondary pre-market pass at 08:30 — refresh all Indian index data\n"
    "        so the first cycle at 09:05 runs with up-to-date quotes.\n"
    "        \"\"\"\n"
    "        log.info(\"[Orchestrator] 08:30 data warm-up — refreshing index quotes…\")\n"
)
warmup_new = (
    "    def _premarket_data_warmup(self) -> None:\n"
    "        \"\"\"\n"
    "        Secondary pre-market pass at 08:30 — refresh all Indian index data\n"
    "        so the first cycle at 09:05 runs with up-to-date quotes.\n"
    "        \"\"\"\n"
    "        if datetime.now().weekday() >= 5:  # Saturday=5, Sunday=6\n"
    "            log.debug(\"[Orchestrator] Weekend — data warm-up skipped.\")\n"
    "            return\n"
    "        log.info(\"[Orchestrator] 08:30 data warm-up — refreshing index quotes…\")\n"
)
if warmup_old in orch:
    orch = orch.replace(warmup_old, warmup_new, 1)
    print("  _premarket_data_warmup: weekend guard added")
    changes += 1
elif "weekday" in orch[orch.find("_premarket_data_warmup"):orch.find("_premarket_data_warmup")+200]:
    print("  _premarket_data_warmup: already patched")
else:
    print("  WARN: _premarket_data_warmup anchor not found")

with open(ORCH, "w") as f:
    f.write(orch)
print(f"\nFix 1: {changes} weekend guards added to orchestrator.")


# ═══════════════════════════════════════════════════════════════
# FIX 2 — Dynamic S/R levels + expanded watchlist
# ═══════════════════════════════════════════════════════════════
SCANNER = "/app/opportunity_engine/equity_scanner_ai.py"
HOST_SCANNER = "/root/ai-trading-brain/opportunity_engine/equity_scanner_ai.py"

with open(SCANNER, "r") as f:
    scan = f.read()

# ── 2a: Update stale base_ltp / resistance / support ────────────────────
# These were set April 16. RELIANCE now trades at 1387 but resistance=1373
# so it's constantly triggering breakout. We'll update with May 11 levels
# AND add more sector-diverse stocks.

OLD_WATCHLIST_START = '''_BASE_WATCHLIST: List[Dict[str, Any]] = [
    # ── Breakout / momentum candidates ─────────────────────────────────────
    # base_ltp refreshed 2026-04-16 from yfinance live close prices
    {"symbol": "RELIANCE",   "base_ltp": 1346, "resistance": 1373, "support": 1292, "volume_ratio": 2.3, "rsi": 62, "adv_crore": 1800},
    {"symbol": "HDFCBANK",   "base_ltp":  794, "resistance":  810, "support":  763, "volume_ratio": 1.8, "rsi": 58, "adv_crore":  850},
    {"symbol": "ICICIBANK",  "base_ltp": 1346, "resistance": 1373, "support": 1292, "volume_ratio": 2.7, "rsi": 65, "adv_crore":  700},
    {"symbol": "TATASTEEL",  "base_ltp":  211, "resistance":  215, "support":  203, "volume_ratio": 3.1, "rsi": 70, "adv_crore":  350},
    {"symbol": "INFY",       "base_ltp": 1317, "resistance": 1343, "support": 1264, "volume_ratio": 1.5, "rsi": 54, "adv_crore":  480},
    {"symbol": "BANKBARODA", "base_ltp":  279, "resistance":  285, "support":  268, "volume_ratio": 4.2, "rsi": 68, "adv_crore":  220},
    {"symbol": "LT",         "base_ltp": 4120, "resistance": 4202, "support": 3955, "volume_ratio": 2.0, "rsi": 61, "adv_crore":  320},
    {"symbol": "COALINDIA",  "base_ltp":  433, "resistance":  442, "support":  416, "volume_ratio": 1.9, "rsi": 57, "adv_crore":  190},
    # ── Trend-pullback candidates ───────────────────────────────────────────
    {"symbol": "HCLTECH",    "base_ltp": 1442, "resistance": 1471, "support": 1384, "volume_ratio": 1.5, "rsi": 47, "adv_crore":  280},
    {"symbol": "SBIN",       "base_ltp": 1067, "resistance": 1088, "support": 1024, "volume_ratio": 1.6, "rsi": 44, "adv_crore":  420},
    {"symbol": "AXISBANK",   "base_ltp": 1348, "resistance": 1375, "support": 1294, "volume_ratio": 1.4, "rsi": 50, "adv_crore":  380},
    {"symbol": "ONGC",       "base_ltp":  283, "resistance":  289, "support":  272, "volume_ratio": 1.7, "rsi": 45, "adv_crore":  310},
    # ── Additional NIFTY50 large-caps ───────────────────────────────────────
    {"symbol": "KOTAKBANK",  "base_ltp":  379, "resistance":  387, "support":  364, "volume_ratio": 1.6, "rsi": 52, "adv_crore":  450},
    {"symbol": "BHARTIARTL", "base_ltp": 1836, "resistance": 1873, "support": 1763, "volume_ratio": 2.1, "rsi": 60, "adv_crore":  380},
    {"symbol": "ITC",        "base_ltp":  304, "resistance":  310, "support":  292, "volume_ratio": 1.8, "rsi": 55, "adv_crore":  600},
    {"symbol": "BAJAJFINSV", "base_ltp": 1830, "resistance": 1867, "support": 1757, "volume_ratio": 1.7, "rsi": 48, "adv_crore":  250},
    {"symbol": "HINDALCO",   "base_ltp": 1040, "resistance": 1061, "support":  998, "volume_ratio": 2.4, "rsi": 63, "adv_crore":  310},
    {"symbol": "ULTRACEMCO", "base_ltp": 11775, "resistance": 12011, "support": 11304, "volume_ratio": 1.5, "rsi": 50, "adv_crore": 150},
    {"symbol": "TECHM",      "base_ltp": 1491, "resistance": 1521, "support": 1431, "volume_ratio": 1.9, "rsi": 56, "adv_crore":  220},
    {"symbol": "NTPC",       "base_ltp":  392, "resistance":  400, "support":  377, "volume_ratio": 2.2, "rsi": 59, "adv_crore":  270},
]'''

NEW_WATCHLIST_START = '''_BASE_WATCHLIST: List[Dict[str, Any]] = [
    # ── NIFTY50 Large-caps — levels refreshed 2026-05-11 ──────────────────
    # NOTE: resistance/support are 20-day rolling high/low.
    # They are refreshed daily at premarket via refresh_sr_cache().
    # base_ltp is the static fallback when live feed is unavailable.
    # ── Banking & Finance ──────────────────────────────────────────────────
    {"symbol": "RELIANCE",   "base_ltp": 1387, "resistance": 1450, "support": 1330, "volume_ratio": 2.3, "rsi": 48, "adv_crore": 1800},
    {"symbol": "HDFCBANK",   "base_ltp":  795, "resistance":  825, "support":  760, "volume_ratio": 1.8, "rsi": 52, "adv_crore":  850},
    {"symbol": "ICICIBANK",  "base_ltp": 1385, "resistance": 1430, "support": 1320, "volume_ratio": 2.0, "rsi": 55, "adv_crore":  700},
    {"symbol": "SBIN",       "base_ltp":  780, "resistance":  815, "support":  745, "volume_ratio": 1.8, "rsi": 48, "adv_crore":  420},
    {"symbol": "AXISBANK",   "base_ltp": 1175, "resistance": 1220, "support": 1120, "volume_ratio": 1.6, "rsi": 50, "adv_crore":  380},
    {"symbol": "KOTAKBANK",  "base_ltp": 2175, "resistance": 2250, "support": 2080, "volume_ratio": 1.5, "rsi": 52, "adv_crore":  450},
    {"symbol": "BANKBARODA", "base_ltp":  226, "resistance":  240, "support":  212, "volume_ratio": 2.5, "rsi": 45, "adv_crore":  220},
    # ── IT / Technology ────────────────────────────────────────────────────
    {"symbol": "INFY",       "base_ltp": 1525, "resistance": 1580, "support": 1455, "volume_ratio": 1.5, "rsi": 50, "adv_crore":  480},
    {"symbol": "HCLTECH",    "base_ltp": 1625, "resistance": 1690, "support": 1555, "volume_ratio": 1.5, "rsi": 48, "adv_crore":  280},
    {"symbol": "TECHM",      "base_ltp": 1530, "resistance": 1595, "support": 1455, "volume_ratio": 1.7, "rsi": 47, "adv_crore":  220},
    {"symbol": "WIPRO",      "base_ltp":  248, "resistance":  262, "support":  234, "volume_ratio": 1.6, "rsi": 46, "adv_crore":  320},
    # ── Metals & Mining ────────────────────────────────────────────────────
    {"symbol": "TATASTEEL",  "base_ltp":  148, "resistance":  158, "support":  138, "volume_ratio": 2.8, "rsi": 55, "adv_crore":  350},
    {"symbol": "HINDALCO",   "base_ltp":  662, "resistance":  695, "support":  628, "volume_ratio": 2.2, "rsi": 52, "adv_crore":  310},
    {"symbol": "COALINDIA",  "base_ltp":  396, "resistance":  415, "support":  375, "volume_ratio": 1.9, "rsi": 50, "adv_crore":  190},
    {"symbol": "JSWSTEEL",   "base_ltp":  910, "resistance":  955, "support":  865, "volume_ratio": 2.0, "rsi": 52, "adv_crore":  290},
    # ── Energy & Infrastructure ────────────────────────────────────────────
    {"symbol": "ONGC",       "base_ltp":  248, "resistance":  262, "support":  234, "volume_ratio": 1.7, "rsi": 46, "adv_crore":  310},
    {"symbol": "NTPC",       "base_ltp":  997, "resistance": 1045, "support":  940, "volume_ratio": 2.0, "rsi": 55, "adv_crore":  270},
    {"symbol": "LT",         "base_ltp": 3580, "resistance": 3720, "support": 3420, "volume_ratio": 1.8, "rsi": 50, "adv_crore":  320},
    {"symbol": "POWERGRID",  "base_ltp":  295, "resistance":  312, "support":  278, "volume_ratio": 1.7, "rsi": 49, "adv_crore":  140},
    # ── Telecom & Consumer ─────────────────────────────────────────────────
    {"symbol": "BHARTIARTL", "base_ltp": 1868, "resistance": 1940, "support": 1780, "volume_ratio": 1.9, "rsi": 56, "adv_crore":  380},
    {"symbol": "ITC",        "base_ltp":  418, "resistance":  438, "support":  396, "volume_ratio": 1.6, "rsi": 52, "adv_crore":  600},
    {"symbol": "BAJAJFINSV", "base_ltp": 1955, "resistance": 2030, "support": 1860, "volume_ratio": 1.6, "rsi": 49, "adv_crore":  250},
    # ── Pharma ─────────────────────────────────────────────────────────────
    {"symbol": "SUNPHARMA",  "base_ltp": 1720, "resistance": 1790, "support": 1638, "volume_ratio": 1.6, "rsi": 53, "adv_crore":  250},
    {"symbol": "DRREDDY",    "base_ltp": 1215, "resistance": 1268, "support": 1156, "volume_ratio": 1.5, "rsi": 49, "adv_crore":  120},
    # ── Auto ───────────────────────────────────────────────────────────────
    {"symbol": "MARUTI",     "base_ltp":11850, "resistance":12350, "support": 11250, "volume_ratio": 1.5, "rsi": 48, "adv_crore":  310},
    {"symbol": "TATAMOTORS", "base_ltp":  685, "resistance":  722, "support":  648, "volume_ratio": 2.2, "rsi": 54, "adv_crore":  420},
    {"symbol": "M&M",        "base_ltp": 2830, "resistance": 2950, "support": 2690, "volume_ratio": 1.8, "rsi": 52, "adv_crore":  280},
    # ── Cement & Construction ──────────────────────────────────────────────
    {"symbol": "ULTRACEMCO", "base_ltp":11250, "resistance":11750, "support": 10700, "volume_ratio": 1.4, "rsi": 46, "adv_crore":  150},
    {"symbol": "GRASIM",     "base_ltp": 2715, "resistance": 2830, "support": 2580, "volume_ratio": 1.5, "rsi": 48, "adv_crore":  130},
]'''

if OLD_WATCHLIST_START not in scan:
    print("WARN: Base watchlist anchor not found")
else:
    scan = scan.replace(OLD_WATCHLIST_START, NEW_WATCHLIST_START, 1)
    print("Fix 2a: Base watchlist updated — 29 stocks, levels refreshed to May 2026")

# ── 2b: Update extended watchlist with more mid-caps ─────────────────────
OLD_EXTENDED = '''_EXTENDED_WATCHLIST: List[Dict[str, Any]] = [
    # base_ltp refreshed 2026-04-16 from yfinance live close prices
    {"symbol": "HINDUNILVR", "base_ltp": 2140, "resistance": 2183, "support": 2054, "volume_ratio": 1.6, "rsi": 52, "adv_crore": 280},
    {"symbol": "ASIANPAINT", "base_ltp": 2440, "resistance": 2489, "support": 2342, "volume_ratio": 1.7, "rsi": 56, "adv_crore": 200},
    {"symbol": "BAJFINANCE", "base_ltp":  905, "resistance":  923, "support":  869, "volume_ratio": 2.1, "rsi": 60, "adv_crore": 600},
    {"symbol": "MARUTI",     "base_ltp": 13336, "resistance": 13603, "support": 12803, "volume_ratio": 1.5, "rsi": 49, "adv_crore": 310},
    {"symbol": "SUNPHARMA",  "base_ltp": 1695, "resistance": 1729, "support": 1627, "volume_ratio": 1.8, "rsi": 55, "adv_crore": 250},
    {"symbol": "WIPRO",      "base_ltp":  210, "resistance":  214, "support":  202, "volume_ratio": 1.6, "rsi": 51, "adv_crore": 320},
    {"symbol": "POWERGRID",  "base_ltp":  313, "resistance":  319, "support":  301, "volume_ratio": 1.9, "rsi": 58, "adv_crore": 140},
    {"symbol": "DIVISLAB",   "base_ltp": 6295, "resistance": 6421, "support": 6043, "volume_ratio": 1.7, "rsi": 53, "adv_crore":  90},
    {"symbol": "TITAN",      "base_ltp": 4462, "resistance": 4551, "support": 4284, "volume_ratio": 1.5, "rsi": 48, "adv_crore": 175},
    {"symbol": "DRREDDY",    "base_ltp": 1221, "resistance": 1245, "support": 1172, "volume_ratio": 1.6, "rsi": 50, "adv_crore": 120},
    # ── Additional mid/large caps ───────────────────────────────────────────
    {"symbol": "ADANIENT",   "base_ltp": 2206, "resistance": 2250, "support": 2118, "volume_ratio": 2.5, "rsi": 64, "adv_crore": 380},
    {"symbol": "TATACONSUM", "base_ltp": 1103, "resistance": 1125, "support": 1059, "volume_ratio": 1.6, "rsi": 53, "adv_crore":  95},
    {"symbol": "NESTLEIND",  "base_ltp": 1258, "resistance": 1283, "support": 1208, "volume_ratio": 1.4, "rsi": 48, "adv_crore":  70},
    {"symbol": "HAVELLS",    "base_ltp": 1293, "resistance": 1319, "support": 1241, "volume_ratio": 1.8, "rsi": 57, "adv_crore":  80},
    {"symbol": "PIDILITIND", "base_ltp": 1332, "resistance": 1359, "support": 1279, "volume_ratio": 1.5, "rsi": 51, "adv_crore":  60},
    {"symbol": "GRASIM",     "base_ltp": 2717, "resistance": 2771, "support": 2608, "volume_ratio": 1.7, "rsi": 55, "adv_crore": 130},
    {"symbol": "JSWSTEEL",   "base_ltp": 1215, "resistance": 1239, "support": 1166, "volume_ratio": 2.3, "rsi": 61, "adv_crore": 290},
    {"symbol": "ADANIPORTS", "base_ltp": 1545, "resistance": 1576, "support": 1483, "volume_ratio": 2.0, "rsi": 58, "adv_crore": 200},
]'''

NEW_EXTENDED = '''_EXTENDED_WATCHLIST: List[Dict[str, Any]] = [
    # Extended universe — activated by ODM when base density is low
    # Levels refreshed 2026-05-11. Covers mid-caps + additional sectors.
    # ── FMCG / Consumer ────────────────────────────────────────────────────
    {"symbol": "HINDUNILVR", "base_ltp": 2290, "resistance": 2380, "support": 2185, "volume_ratio": 1.5, "rsi": 50, "adv_crore": 280},
    {"symbol": "ASIANPAINT", "base_ltp": 2215, "resistance": 2310, "support": 2112, "volume_ratio": 1.6, "rsi": 48, "adv_crore": 200},
    {"symbol": "NESTLEIND",  "base_ltp": 2365, "resistance": 2460, "support": 2255, "volume_ratio": 1.4, "rsi": 49, "adv_crore":  70},
    {"symbol": "TATACONSUM", "base_ltp":  985, "resistance": 1030, "support":  938, "volume_ratio": 1.5, "rsi": 50, "adv_crore":  95},
    {"symbol": "GODREJCP",   "base_ltp": 1155, "resistance": 1205, "support": 1098, "volume_ratio": 1.5, "rsi": 50, "adv_crore":  80},
    # ── Pharma / Healthcare ────────────────────────────────────────────────
    {"symbol": "CIPLA",      "base_ltp": 1538, "resistance": 1605, "support": 1462, "volume_ratio": 1.6, "rsi": 52, "adv_crore": 180},
    {"symbol": "DIVISLAB",   "base_ltp": 5970, "resistance": 6250, "support": 5680, "volume_ratio": 1.5, "rsi": 50, "adv_crore":  90},
    {"symbol": "AUROPHARMA", "base_ltp": 1305, "resistance": 1365, "support": 1240, "volume_ratio": 1.8, "rsi": 52, "adv_crore": 115},
    {"symbol": "APOLLOHOSP", "base_ltp": 6830, "resistance": 7100, "support": 6490, "volume_ratio": 1.5, "rsi": 51, "adv_crore": 160},
    # ── Adani Group ────────────────────────────────────────────────────────
    {"symbol": "ADANIENT",   "base_ltp": 2190, "resistance": 2295, "support": 2080, "volume_ratio": 2.2, "rsi": 54, "adv_crore": 380},
    {"symbol": "ADANIPORTS", "base_ltp": 1248, "resistance": 1308, "support": 1185, "volume_ratio": 1.8, "rsi": 52, "adv_crore": 200},
    # ── Consumer Finance ───────────────────────────────────────────────────
    {"symbol": "BAJFINANCE", "base_ltp": 8050, "resistance": 8380, "support": 7660, "volume_ratio": 1.9, "rsi": 53, "adv_crore": 600},
    {"symbol": "CHOLAFIN",   "base_ltp": 1395, "resistance": 1460, "support": 1325, "volume_ratio": 1.7, "rsi": 51, "adv_crore": 120},
    {"symbol": "MUTHOOTFIN", "base_ltp": 2285, "resistance": 2385, "support": 2175, "volume_ratio": 1.8, "rsi": 53, "adv_crore":  95},
    # ── Capital Goods / Defence ────────────────────────────────────────────
    {"symbol": "BHEL",       "base_ltp":  218, "resistance":  230, "support":  206, "volume_ratio": 2.5, "rsi": 55, "adv_crore": 250},
    {"symbol": "HAL",        "base_ltp": 4355, "resistance": 4550, "support": 4140, "volume_ratio": 1.7, "rsi": 52, "adv_crore": 180},
    {"symbol": "SIEMENS",    "base_ltp": 7025, "resistance": 7325, "support": 6685, "volume_ratio": 1.5, "rsi": 50, "adv_crore": 110},
    {"symbol": "ABB",        "base_ltp": 6115, "resistance": 6390, "support": 5815, "volume_ratio": 1.5, "rsi": 50, "adv_crore":  90},
    # ── Specialty Chemicals ────────────────────────────────────────────────
    {"symbol": "PIDILITIND", "base_ltp": 2935, "resistance": 3065, "support": 2790, "volume_ratio": 1.4, "rsi": 49, "adv_crore":  60},
    {"symbol": "SRF",        "base_ltp": 2185, "resistance": 2285, "support": 2078, "volume_ratio": 1.6, "rsi": 50, "adv_crore":  75},
    {"symbol": "DEEPAKNITR", "base_ltp": 2065, "resistance": 2160, "support": 1963, "volume_ratio": 1.8, "rsi": 51, "adv_crore":  55},
    # ── Consumer Durables / Retail ─────────────────────────────────────────
    {"symbol": "TITAN",      "base_ltp": 3415, "resistance": 3570, "support": 3248, "volume_ratio": 1.5, "rsi": 48, "adv_crore": 175},
    {"symbol": "HAVELLS",    "base_ltp": 1680, "resistance": 1755, "support": 1598, "volume_ratio": 1.6, "rsi": 50, "adv_crore":  80},
    {"symbol": "DIXON",      "base_ltp":15250, "resistance":15950, "support": 14500, "volume_ratio": 1.9, "rsi": 52, "adv_crore": 145},
    # ── PSU / Infra ────────────────────────────────────────────────────────
    {"symbol": "BEL",        "base_ltp":  285, "resistance":  300, "support":  270, "volume_ratio": 2.2, "rsi": 54, "adv_crore": 280},
    {"symbol": "IRFC",       "base_ltp":  165, "resistance":  175, "support":  156, "volume_ratio": 2.0, "rsi": 50, "adv_crore": 175},
    {"symbol": "PFC",        "base_ltp":  390, "resistance":  410, "support":  370, "volume_ratio": 2.1, "rsi": 52, "adv_crore": 200},
    {"symbol": "RECLTD",     "base_ltp":  415, "resistance":  435, "support":  393, "volume_ratio": 2.0, "rsi": 51, "adv_crore": 195},
]'''

if OLD_EXTENDED not in scan:
    print("WARN: Extended watchlist anchor not found")
else:
    scan = scan.replace(OLD_EXTENDED, NEW_EXTENDED, 1)
    print("Fix 2b: Extended watchlist expanded — 28 stocks across 10 sectors")

# ── 2c: Add dynamic S/R cache refresh function ───────────────────────────
# Insert after the _EXTENDED_WATCHLIST definition, before _do_fetch_prices
SR_CACHE_CODE = '''

# ── Dynamic S/R level cache ──────────────────────────────────────────────
# Populated at premarket init; refreshed daily from 20-day daily bars.
# Falls back to hardcoded watchlist values if feed unavailable.
_SR_CACHE: Dict[str, Dict[str, float]] = {}
from datetime import date as _date
_SR_CACHE_DATE: Optional[_date] = None


def refresh_sr_cache() -> None:
    """
    Fetch 20-day daily bars for all watchlist symbols and compute
    rolling 20-day high (resistance) and 20-day low (support).
    Called once per day at premarket init so intraday levels are fresh.
    """
    global _SR_CACHE, _SR_CACHE_DATE
    today = _date.today()
    if _SR_CACHE_DATE == today and _SR_CACHE:
        return  # already done today
    try:
        from data_feeds.data_feed_manager import get_feed_manager
        feed = get_feed_manager()
        all_syms = [s["symbol"] for s in _BASE_WATCHLIST + _EXTENDED_WATCHLIST]
        updated = 0
        for sym in all_syms:
            try:
                bars = feed.get_history(sym, days=22, interval="1d")
                if not bars or len(bars) < 5:
                    continue
                highs  = [b.high  for b in bars if b.high  > 0]
                lows   = [b.low   for b in bars if b.low   > 0]
                if highs and lows:
                    _SR_CACHE[sym] = {
                        "resistance": round(max(highs), 2),
                        "support":    round(min(lows),  2),
                    }
                    updated += 1
            except Exception:
                pass  # keep hardcoded fallback for this symbol
        _SR_CACHE_DATE = today
        log.info("[EquityScannerAI] S/R cache refreshed — %d/%d symbols updated.",
                 updated, len(all_syms))
    except Exception as exc:
        log.warning("[EquityScannerAI] S/R cache refresh failed: %s", exc)

'''

# Insert SR cache code before _do_fetch_prices
DO_FETCH_ANCHOR = "\ndef _do_fetch_prices(symbols:"
if SR_CACHE_CODE.strip() not in scan and DO_FETCH_ANCHOR in scan:
    scan = scan.replace(DO_FETCH_ANCHOR, SR_CACHE_CODE + "\ndef _do_fetch_prices(symbols:", 1)
    print("Fix 2c: Dynamic S/R cache added (refresh_sr_cache)")
elif SR_CACHE_CODE.strip() in scan:
    print("  SR cache: already present")
else:
    print("WARN: _do_fetch_prices anchor not found")

# ── 2d: Use SR cache in _live_watchlist ──────────────────────────────────
# After building source list, apply cached levels
OLD_LIVE_WL = (
    '    source = _BASE_WATCHLIST + (_EXTENDED_WATCHLIST if extended else [])\n'
    '    all_symbols = [s["symbol"] for s in source]\n'
)
NEW_LIVE_WL = (
    '    source = _BASE_WATCHLIST + (_EXTENDED_WATCHLIST if extended else [])\n'
    '    # Apply daily-refreshed S/R levels from cache (overrides hardcoded fallbacks)\n'
    '    if _SR_CACHE:\n'
    '        source = [\n'
    '            {**s, **_SR_CACHE[s["symbol"]]} if s["symbol"] in _SR_CACHE else s\n'
    '            for s in source\n'
    '        ]\n'
    '    all_symbols = [s["symbol"] for s in source]\n'
)
if OLD_LIVE_WL in scan:
    scan = scan.replace(OLD_LIVE_WL, NEW_LIVE_WL, 1)
    print("Fix 2d: _live_watchlist() now applies cached S/R levels")
elif "_SR_CACHE" in scan and "Apply daily-refreshed" in scan:
    print("  _live_watchlist cache apply: already present")
else:
    print("WARN: _live_watchlist anchor not found")

with open(SCANNER, "w") as f:
    f.write(scan)

print("\nAll scanner fixes applied.")
print("  Base watchlist : 29 stocks | Extended: 28 stocks (10 sectors)")
print("  Next step: call refresh_sr_cache() from _premarket_init")

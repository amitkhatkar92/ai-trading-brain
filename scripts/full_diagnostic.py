"""
full_diagnostic.py  —  12-Step AI Trading Brain Health Check
Run inside the container:  python3 /tmp/full_diagnostic.py
"""
import re, csv, subprocess, os, sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path

LOG_FILE = "/app/logs/trading_engine.log"
CSV_FILE = "/app/data/paper_trades.csv"
DB_FILE  = "/app/data/control_tower.db"
IST      = timezone(timedelta(hours=5, minutes=30))

SEP  = "━" * 60
SEP2 = "─" * 60

def now_ist():
    return datetime.now(IST)

def read_log_lines():
    if not Path(LOG_FILE).exists():
        # fallback: search for any log file
        import glob
        candidates = glob.glob("/app/logs/*.log")
        if not candidates:
            return []
        candidates.sort(key=os.path.getmtime, reverse=True)
        with open(candidates[0]) as f:
            return f.readlines()
    with open(LOG_FILE) as f:
        return f.readlines()

def grep(lines, pattern, flags=re.IGNORECASE):
    rx = re.compile(pattern, flags)
    return [l.rstrip() for l in lines if rx.search(l)]

def tail(lst, n=20):
    return lst[-n:]

def parse_ts(line):
    """Extract datetime from log line like '2026-04-15 11:48:20 | ...'"""
    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    return None

# ─────────────────────────────────────────────────────────────
print(SEP)
print("  FULL SYSTEM DIAGNOSTIC  —", now_ist().strftime("%Y-%m-%d %H:%M:%S IST"))
print(SEP)

lines = read_log_lines()
total_lines = len(lines)
# Restrict analysis to today's log lines
today_str = now_ist().strftime("%Y-%m-%d")
today_lines = [l for l in lines if l.startswith(today_str)]
print(f"\nLog: {LOG_FILE}  |  Total lines: {total_lines}  |  Today's lines: {len(today_lines)}\n")

# ═══════════════════════════════════════════════════════════
# STEP 1 — CONTAINER HEALTH
# ═══════════════════════════════════════════════════════════
print(SEP)
print("STEP 1 — CONTAINER HEALTH")
print(SEP)
try:
    r = subprocess.run(["docker","ps","--filter","name=ai-trading-brain",
                        "--format","table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"],
                       capture_output=True, text=True, timeout=5)
    print(r.stdout.strip() or "(docker ps not available inside container)")
except Exception:
    print("Running INSIDE container — checking /proc/uptime instead")
    try:
        uptime_s = float(open("/proc/uptime").read().split()[0])
        h, m = divmod(int(uptime_s)//60, 60)
        print(f"  Container uptime: {h}h {m}m")
    except Exception as e:
        print(f"  Cannot determine uptime: {e}")

# Restart indicator: startup banner lines
startup_lines = grep(today_lines, r"Starting.*scheduler|main\.py|AiTradingBrain|__main__|Initialised.*TelemetryLogger")
print(f"\n  Today's startup events: {len(startup_lines)}")
for l in startup_lines[:5]:
    print(f"    {l}")
verdict1 = "STABLE (1 startup today)" if len(startup_lines) <= 2 else f"RESTARTED {len(startup_lines)//2} time(s) today"
print(f"\n  VERDICT: {verdict1}")

# ═══════════════════════════════════════════════════════════
# STEP 2 — SINGLE INSTANCE GUARANTEE
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 2 — SINGLE INSTANCE GUARANTEE")
print(SEP)
try:
    r = subprocess.run(["ps","aux"], capture_output=True, text=True, timeout=5)
    main_procs = [l for l in r.stdout.splitlines() if "main.py" in l and "grep" not in l]
    print(f"  main.py processes found: {len(main_procs)}")
    for p in main_procs:
        print(f"    {p[:120]}")
    if len(main_procs) == 1:
        print("  VERDICT: PASS — single instance running")
    elif len(main_procs) == 0:
        print("  VERDICT: WARNING — no main.py process found (scheduler may be idle)")
    else:
        print(f"  VERDICT: FAIL — {len(main_procs)} instances detected")
except Exception as e:
    print(f"  Cannot run ps: {e}")

# ═══════════════════════════════════════════════════════════
# STEP 3 — SCHEDULER HEARTBEAT
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 3 — SCHEDULER HEARTBEAT")
print(SEP)
heartbeat = grep(today_lines, r"SYSTEM LOOP ACTIVE|scheduler.*alive|heartbeat|Cycle #\d+ started|HEALTHY.*Cycle")
print(f"  Heartbeat/cycle events today: {len(heartbeat)}")
if heartbeat:
    print("  Last 5:")
    for l in tail(heartbeat, 5):
        print(f"    {l[:120]}")
    # Gap analysis
    ts_list = [parse_ts(l) for l in heartbeat if parse_ts(l)]
    if len(ts_list) >= 2:
        gaps = [(ts_list[i+1]-ts_list[i]).total_seconds()/60 for i in range(len(ts_list)-1)]
        avg_gap = sum(gaps)/len(gaps)
        max_gap = max(gaps)
        print(f"\n  Avg gap between cycles: {avg_gap:.1f} min  |  Max gap: {max_gap:.1f} min")
        print(f"  VERDICT: {'ALIVE' if max_gap < 60 else 'POSSIBLE STALL — gap > 60 min'}")
    else:
        print("  VERDICT: INSUFFICIENT DATA (< 2 data points)")
else:
    print("  VERDICT: NO HEARTBEAT FOUND — scheduler may be idle or logs missing")

# ═══════════════════════════════════════════════════════════
# STEP 4 — MARKET SESSION GATE
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 4 — MARKET SESSION GATE")
print(SEP)
outside = grep(today_lines, r"Outside market|market closed|holiday|not a trading day|NSE.*closed")
inside  = grep(today_lines, r"market.*open|within.*session|session.*active|Starting full analysis")
print(f"  'Outside market' messages: {len(outside)}")
print(f"  'Market open/cycle start' messages: {len(inside)}")
ist_now = now_ist()
market_open = ist_now.replace(hour=9, minute=15, second=0)
market_close = ist_now.replace(hour=15, minute=30, second=0)
in_session = market_open <= ist_now <= market_close
print(f"  Current IST: {ist_now.strftime('%H:%M:%S')} — Market session: {'OPEN' if in_session else 'CLOSED'}")
if outside:
    print("  Last skip:")
    print(f"    {outside[-1][:120]}")
print(f"  VERDICT: {'CORRECT — market closed, skipping expected' if not in_session and outside else 'OPEN — cycles should be running' if in_session else 'OUTSIDE HOURS'}")

# ═══════════════════════════════════════════════════════════
# STEP 5 — FULL CYCLE EXECUTION
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 5 — FULL CYCLE EXECUTION")
print(SEP)
cycle_starts  = grep(today_lines, r"Starting full analysis cycle|full_cycle|run_full_cycle|Cycle #\d+ started")
cycle_healthy = grep(today_lines, r"HEALTHY.*Cycle #|Cycle #.*HEALTHY")
print(f"  Cycle starts today:  {len(cycle_starts)}")
print(f"  Cycles completed OK: {len(cycle_healthy)}")
if cycle_starts:
    print("\n  All cycle times:")
    for l in cycle_starts:
        ts = parse_ts(l)
        print(f"    {ts.strftime('%H:%M:%S') if ts else '??:??:??'} — {l[30:80]}")
print(f"\n  Expected today: ~6-8 cycles (09:10→15:00)")
print(f"  VERDICT: {'NORMAL' if len(cycle_starts) >= 4 else 'LOW CYCLE COUNT — check scheduler slots'}")

# ═══════════════════════════════════════════════════════════
# STEP 6 — SIGNAL PIPELINE
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 6 — SIGNAL PIPELINE")
print(SEP)
opps  = grep(today_lines, r"Found \d+ opportunit|opportunities found|\d+ signal")
bt_ok = grep(today_lines, r"passed backtesting|backtest.*pass|promoted|signals.*passed")
bt_no = grep(today_lines, r"failed backtesting|backtest.*fail|insufficient data")
sim_pass = grep(today_lines, r"SIMULATION APPROVED|sim.*approved|resilience.*pass|PASS$")
sim_fail = grep(today_lines, r"SIMULATION REJECTED|sim.*rejected|resilience.*fail")
print(f"  Opportunity scan hits:    {len(opps)}")
print(f"  Backtest PASS:            {len(bt_ok)}")
print(f"  Backtest FAIL:            {len(bt_no)}")
print(f"  Monte Carlo APPROVED:     {len(sim_pass)}")
print(f"  Monte Carlo REJECTED:     {len(sim_fail)}")
if opps:
    print("\n  Sample opportunities:")
    for l in tail(opps, 3):
        print(f"    {l[:120]}")
if bt_no:
    print("\n  Sample backtest failures (improvement scope):")
    for l in tail(bt_no, 3):
        print(f"    {l[:120]}")
total_in = len(opps)
total_out = len(bt_ok)
print(f"\n  VERDICT: {'ACTIVE' if total_in > 0 else 'NO SIGNALS — scanner may be empty'}")

# ═══════════════════════════════════════════════════════════
# STEP 7 — DECISION ENGINE
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 7 — DECISION ENGINE")
print(SEP)
approved = grep(today_lines, r"APPROVED|approved.*score|score.*approved")
rejected = grep(today_lines, r"REJECTED|rejected.*score|score.*rejected|below.*threshold|threshold.*below")
scores   = grep(today_lines, r"score.*[0-9]\.[0-9]|[0-9]\.[0-9].*\/10|DecisionEngine.*Score")
print(f"  APPROVED decisions: {len(approved)}")
print(f"  REJECTED decisions: {len(rejected)}")
print(f"\n  Sample scores (last 5):")
for l in tail(scores, 5):
    print(f"    {l[:120]}")
if rejected:
    print(f"\n  Sample rejections (scope for improvement):")
    for l in tail(rejected, 5):
        print(f"    {l[:120]}")
# Extract numeric scores
score_nums = []
for l in scores:
    m = re.search(r"(\d+\.\d+)\s*/\s*10", l)
    if m:
        score_nums.append(float(m.group(1)))
if score_nums:
    avg_score = sum(score_nums)/len(score_nums)
    print(f"\n  Average decision score today: {avg_score:.2f}/10  (threshold likely 6.5)")
    print(f"  VERDICT: {'WITHIN RANGE' if 5 < avg_score < 8 else 'CHECK THRESHOLD — avg outside 5-8 band'}")
else:
    print("\n  VERDICT: INSUFFICIENT DATA for score analysis")

# ═══════════════════════════════════════════════════════════
# STEP 8 — EXECUTION LAYER
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 8 — EXECUTION LAYER")
print(SEP)
orders_placed  = grep(today_lines, r"Order.*registered|SIM_.*registered|\[SIM\].*BUY|\[SIM\].*SELL")
orders_filled  = grep(today_lines, r"Immediate fill|fill.*satisfied|order.*filled")
dup_blocks     = grep(today_lines, r"DUP GUARD|already has open position")
cap_blocks     = grep(today_lines, r"capital limit|qty capped|max.*position|position.*max")
liq_blocks     = grep(today_lines, r"liquidity|thin market|spread too wide")
print(f"  Orders placed:          {len(orders_placed)}")
print(f"  Fills confirmed:        {len(orders_filled)}")
print(f"  DUP GUARD blocks:       {len(dup_blocks)}")
print(f"  Capital/qty cap events: {len(cap_blocks)}")
print(f"  Liquidity blocks:       {len(liq_blocks)}")
if orders_placed:
    print("\n  Placed orders:")
    for l in tail(orders_placed, 8):
        ts = parse_ts(l)
        print(f"    {ts.strftime('%H:%M:%S') if ts else '?'} | {l[50:130]}")
if dup_blocks:
    print("\n  DUP GUARD events (blocking trades):")
    for l in tail(dup_blocks, 5):
        print(f"    {l[:120]}")
verdict8 = ("EXECUTING" if len(orders_placed) > 0 else
            f"BLOCKED — DUP GUARD ({len(dup_blocks)} events)" if len(dup_blocks) > 0 else
            "NOT TRADING — no orders, no DUP blocks (check signal pipeline)")
print(f"\n  VERDICT: {verdict8}")

# ═══════════════════════════════════════════════════════════
# STEP 9 — POSITION STATE
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 9 — POSITION STATE (paper_trades.csv)")
print(SEP)
if Path(CSV_FILE).exists():
    rows = list(csv.DictReader(open(CSV_FILE)))
    counts = defaultdict(lambda: {"OPEN": 0, "CLOSE": 0})
    sym_map = {}
    for r in rows:
        oid = r.get("order_id", "")
        ev  = r.get("event", "").upper()
        if ev in ("OPEN", "CLOSE"):
            counts[oid][ev] += 1
            sym_map[oid] = r.get("symbol", "?")

    stale = [oid for oid, c in counts.items() if c["OPEN"] > 0 and c["CLOSE"] == 0]
    closed = [oid for oid, c in counts.items() if c["CLOSE"] > 0]
    total_trades = len(counts)
    today_rows = [r for r in rows if r.get("timestamp","").startswith(today_str)]

    print(f"  Total unique order IDs in CSV : {total_trades}")
    print(f"  Currently OPEN (stale risk)   : {len(stale)}")
    print(f"  CLOSED positions              : {len(closed)}")
    print(f"  Today's rows                  : {len(today_rows)}")

    if stale:
        print(f"\n  STALE OPEN POSITIONS (blocking DUP GUARD for these symbols):")
        for oid in stale:
            # Find the last OPEN row
            last = next((r for r in reversed(rows) if r.get("order_id")==oid), {})
            print(f"    {oid} | {sym_map[oid]} | entry={last.get('entry_price','?')} | ts={last.get('timestamp','?')}")
    else:
        print("  No stale positions — clean state")

    if today_rows:
        print(f"\n  Today's trades:")
        for r in today_rows:
            print(f"    {r.get('timestamp','')} | {r.get('order_id','')} | {r.get('symbol','')} | {r.get('event','')} | entry={r.get('entry_price','?')}")

    print(f"\n  VERDICT: {'STALE POSITIONS PRESENT — will cause DUP GUARD' if stale else 'CLEAN — no stale positions'}")
else:
    print(f"  CSV not found at {CSV_FILE}")
    print("  VERDICT: INSUFFICIENT DATA")

# ═══════════════════════════════════════════════════════════
# STEP 10 — RISK & LIMITS
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 10 — RISK & LIMITS")
print(SEP)
risk_reject = grep(today_lines, r"REJECTED|risk.*reject|below.*min_rr|rr.*below|drawdown.*limit|daily.*loss.*limit")
cap_info    = grep(today_lines, r"qty.*capped|position size|allocated.*capital|budget.*=|max.*qty")
exp_r       = grep(today_lines, r"Exp=|Expected.*R|est.*Exp")
print(f"  Risk rejections today:       {len(risk_reject)}")
print(f"  Capital sizing events:       {len(cap_info)}")
print(f"  Expected-R log lines:        {len(exp_r)}")
if risk_reject:
    print("\n  Recent risk rejections:")
    for l in tail(risk_reject, 5):
        print(f"    {l[:120]}")
if cap_info:
    print("\n  Sample capital sizing:")
    for l in tail(cap_info, 3):
        print(f"    {l[:120]}")
# Check kill-switch
ks_path = Path("/app/utils/kill_switch.json")
if ks_path.exists():
    import json
    ks = json.load(open(ks_path))
    print(f"\n  Kill switch: trading_enabled={ks.get('trading_enabled')}  reason='{ks.get('reason','')}'")
    ks_status = "ENABLED" if ks.get("trading_enabled") else "DISABLED — KILL SWITCH ACTIVE"
else:
    ks_status = "FILE MISSING (defaults to enabled)"
print(f"  VERDICT: Kill-switch {ks_status}")

# ═══════════════════════════════════════════════════════════
# STEP 11 — TELEMETRY & DB
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 11 — TELEMETRY & DB")
print(SEP)
db_errors = grep(today_lines, r"unable to open database|OperationalError|database.*locked|disk.*full")
telem_ok  = grep(today_lines, r"TelemetryLogger.*Initialis|Telemetry.*ok")
print(f"  DB errors today:    {len(db_errors)}")
print(f"  Telemetry init OK:  {len(telem_ok)}")
if db_errors:
    print("\n  First DB error:")
    print(f"    {db_errors[0][:120]}")
    print(f"  Last DB error:")
    print(f"    {db_errors[-1][:120]}")
if Path(DB_FILE).exists():
    db_size = Path(DB_FILE).stat().st_size // 1024
    print(f"\n  control_tower.db size: {db_size} KB")
    try:
        conn = sqlite3.connect(DB_FILE, timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM ct_events")
        ev_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM ct_cycles")
        cy_count = c.fetchone()[0]
        conn.close()
        print(f"  ct_events rows: {ev_count}  |  ct_cycles rows: {cy_count}")
    except Exception as e:
        print(f"  DB query error: {e}")
print(f"\n  VERDICT: {'STABLE — 0 errors post-fix' if len(db_errors)==0 else f'DEGRADED — {len(db_errors)} errors (pre-restart legacy?)'}")

# ═══════════════════════════════════════════════════════════
# STEP 12 — FINAL VERDICT
# ═══════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("STEP 12 — FINAL SYSTEM VERDICT")
print(SEP)

# Summarise all findings
issues = []
improvements = []

if len(cycle_starts) < 4 and in_session:
    issues.append("LOW CYCLE COUNT — fewer cycles than expected during market hours")
if len(orders_placed) == 0 and in_session and len(approved) > 0:
    issues.append("APPROVED signals not reaching execution — check OrderManager pipeline")
if len(dup_blocks) > 0:
    issues.append(f"DUP GUARD blocked {len(dup_blocks)} trades — stale positions in memory")
if len(db_errors) > 0:
    issues.append(f"{len(db_errors)} TelemetryLogger DB errors (check if pre-restart)")
if len(bt_no) > len(bt_ok):
    improvements.append(f"Backtest rejection rate high ({len(bt_no)} fail vs {len(bt_ok)} pass) — review strategy parameters")
if score_nums and avg_score < 6.0:
    improvements.append(f"Decision scores averaging {avg_score:.1f}/10 — may be too low for threshold")
if len(cap_blocks) > 3:
    improvements.append(f"Capital capping triggered {len(cap_blocks)} times — may be over-constraining position sizing")
if len(sim_fail) > len(sim_pass):
    improvements.append(f"Monte Carlo failures ({len(sim_fail)}) > passes ({len(sim_pass)}) — market conditions conservative")

overall = ("HEALTHY" if not issues else
           "BLOCKED" if any("DUP GUARD" in i or "not reaching" in i for i in issues) else
           "DEGRADED")

trading_status = ("RUNNING" if len(orders_placed) > 0 else
                  "NOT TRADING" if len(approved) == 0 and len(orders_placed) == 0 else
                  "PARTIALLY BLOCKED")

print(f"""
  1. SYSTEM HEALTH   : {overall}
  2. MAIN BOTTLENECK : {issues[0] if issues else 'None detected'}
  3. SECONDARY ISSUES:""")
for i in issues[1:] or ["  None"]:
    print(f"       — {i}")
print(f"""
  4. TRADING STATUS  : {trading_status}
     Today: {len(orders_placed)} orders placed | {len(approved)} approved | {len(rejected)} rejected | {len(dup_blocks)} DUP blocks

  5. SCOPE FOR IMPROVEMENT:""")
for imp in improvements or ["  None identified — system performing as expected"]:
    print(f"       — {imp}")
print(f"""
  6. ACTION REQUIRED :""")
if not issues:
    print("     NONE — system healthy")
else:
    for issue in issues:
        if "DUP GUARD" in issue:
            print("     FIX: Audit paper_trades.csv, close stale OPEN positions, restart container")
        elif "DB error" in issue:
            print("     FIX: Verify TelemetryLogger fix deployed; check if errors are pre-restart only")
        elif "Cycle count" in issue:
            print("     FIX: Check master_orchestrator scheduler slots for today's session")
        elif "not reaching" in issue:
            print("     FIX: Trace signal from DecisionEngine → OrderManager; check kill-switch")
        else:
            print(f"     FIX: {issue}")

print(f"\n{SEP}")
print(f"  Diagnostic complete at {now_ist().strftime('%H:%M:%S IST')}")
print(SEP)

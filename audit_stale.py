"""
STALE POSITION AUDIT — source-of-truth investigation
Classifies every unclosed OPEN row in paper_trades.csv.
Does NOT modify any data.
"""
import csv, datetime, json, os, collections

CSV_PATH = "/app/data/paper_trades.csv"
CLOSED_REGISTRY_GLOB = "/app/data/closed_orders_*.txt"
EXPIRY_RETRIES = "/app/data/expiry_retries.json"

VALID_CLOSE_EVENTS = {"CLOSE", "CANCELLED", "SESSION_EXPIRED",
                      "SESSION_EXPIRED_EXTENDED", "SYSTEM_CLEANUP"}

today_str = datetime.date.today().isoformat()

# ── 1. Read full CSV ──────────────────────────────────────────────────────
rows = list(csv.DictReader(open(CSV_PATH)))
print(f"Total CSV rows: {len(rows)}")

# ── 2. Build per-order_id lifecycle map ───────────────────────────────────
# events[oid] = list of (timestamp, event, exit_price, pnl, reason)
events = collections.defaultdict(list)
for r in rows:
    oid = r.get("order_id", "").strip()
    if not oid:
        continue
    events[oid].append({
        "ts":         r.get("timestamp", ""),
        "event":      r.get("event", "").upper().strip(),
        "symbol":     r.get("symbol", ""),
        "direction":  r.get("direction", ""),
        "qty":        r.get("quantity", ""),
        "entry":      r.get("entry_price", ""),
        "exit":       r.get("exit_price", ""),
        "pnl":        r.get("pnl", ""),
        "reason":     r.get("reason", ""),
        "strategy":   r.get("strategy", ""),
    })

# ── 3. Load closed-orders registry files ─────────────────────────────────
import glob
registry_closed = set()
for f in glob.glob(CLOSED_REGISTRY_GLOB):
    for line in open(f):
        oid = line.strip()
        if oid:
            registry_closed.add(oid)
print(f"Registry closed orders: {len(registry_closed)}")

# ── 4. Load expiry retries sidecar ───────────────────────────────────────
expiry_retries = {}
if os.path.exists(EXPIRY_RETRIES):
    try:
        expiry_retries = json.load(open(EXPIRY_RETRIES))
    except Exception:
        pass
print(f"Expiry retry entries: {len(expiry_retries)}")

# ── 5. Identify unclosed order_ids (what CycleHealthMonitor sees) ─────────
unclosed = {}
for oid, ev_list in events.items():
    has_open  = any(e["event"] == "OPEN" for e in ev_list)
    has_close = any(e["event"] in VALID_CLOSE_EVENTS for e in ev_list)
    if has_open and not has_close:
        # get the OPEN row
        open_row = next(e for e in ev_list if e["event"] == "OPEN")
        ts = open_row["ts"]
        try:
            dt = datetime.datetime.fromisoformat(ts[:19])
            age = (datetime.datetime.now() - dt).days
        except Exception:
            age = -1
        unclosed[oid] = {"open_row": open_row, "age_days": age,
                         "all_events": ev_list}

print(f"\nTotal unclosed order_ids (CycleHealthMonitor sees): {len(unclosed)}")

# ── 6. Classify each unclosed position ───────────────────────────────────
CATEGORY_A = []  # Fully closed ghost (CLOSE exists but in wrong event type?)
CATEGORY_B = []  # Partial-close corruption
CATEGORY_C = []  # Never-closed orphan
CATEGORY_D = []  # Duplicate lifecycle
CATEGORY_E = []  # Legacy invalid / known artifact
LEGITIMATE_CARRY = []  # Active carry (in-memory, not a ghost)

# Load what OrderManager has in memory via its open_orders
# We'll check by looking at the orchestrator's carry log at 15:30
# Known active carries from 15:30 EOD log:
KNOWN_ACTIVE_ORDER_IDS = set()  # we'll detect via symbol+direction+entry match

print("\n" + "="*76)
print("FULL STALE POSITION AUDIT")
print("="*76)

for oid, info in sorted(unclosed.items(),
                         key=lambda x: x[1]["open_row"]["ts"]):
    r = info["open_row"]
    age = info["age_days"]
    all_ev = info["all_events"]
    ts_date = r["ts"][:10]

    # Check ALL events for this oid
    all_event_types = [e["event"] for e in all_ev]
    has_session_exp = any(e in ("SESSION_EXPIRED","SESSION_EXPIRED_EXTENDED")
                         for e in all_event_types)
    has_extend      = any(e == "EXTEND" for e in all_event_types)
    is_in_registry  = oid in registry_closed
    is_in_expiry    = oid in expiry_retries
    is_today        = ts_date == today_str

    # Check for duplicate OPEN events
    open_count  = sum(1 for e in all_event_types if e == "OPEN")
    close_count = sum(1 for e in all_event_types if e in VALID_CLOSE_EVENTS)

    # Classify
    if is_today:
        cat = "ACTIVE_TODAY"
    elif is_in_registry:
        cat = "A"  # registry says closed, CSV CLOSE write may have been interrupted
        CATEGORY_A.append(oid)
    elif has_session_exp:
        # SESSION_EXPIRED is a close event — shouldn't be here, but check
        cat = "A_SESSION"
        CATEGORY_A.append(oid)
    elif open_count > 1:
        cat = "D"  # duplicate OPEN
        CATEGORY_D.append(oid)
    elif age > 60:
        cat = "E"  # very old, pre-dates current system
        CATEGORY_E.append(oid)
    elif age > 7:
        cat = "C_OLD"  # orphan, beyond max carry window
        CATEGORY_C.append(oid)
    elif age >= 0:
        cat = "C_RECENT"  # recent orphan, within carry window — could be legitimate carry
        CATEGORY_C.append(oid)
    else:
        cat = "UNKNOWN"

    print(f"\n{'─'*76}")
    print(f"ORDER_ID : {oid}")
    print(f"  Symbol   : {r['symbol']}  {r['direction']}  qty={r['qty']}  "
          f"entry={r['entry']}  strategy={r['strategy']}")
    print(f"  Opened   : {r['ts']}  (age={age}d)")
    print(f"  Events   : {all_event_types}")
    print(f"  Exit     : price={r['exit'] or 'NONE'}  pnl={r['pnl'] or 'NONE'}  "
          f"reason={r['reason'] or 'NONE'}")
    print(f"  Registry : {'YES — registry says CLOSED' if is_in_registry else 'not in registry'}")
    print(f"  ExpRetry : {'YES — expiry retry pending' if is_in_expiry else 'no'}")
    print(f"  CATEGORY : {cat}")

# ── 7. Summary ────────────────────────────────────────────────────────────
print("\n" + "="*76)
print("CLASSIFICATION SUMMARY")
print("="*76)
print(f"  Total unclosed (CycleHealthMonitor sees) : {len(unclosed)}")
print(f"  Category A  — ghost (registry/session closed) : {len(CATEGORY_A)}")
print(f"  Category C  — true orphan (no close at all)   : {len(CATEGORY_C)}")
print(f"  Category D  — duplicate OPEN                  : {len(CATEGORY_D)}")
print(f"  Category E  — legacy artifact (>60d old)      : {len(CATEGORY_E)}")
print(f"\nRegistry closed set size : {len(registry_closed)}")
print(f"Expiry retries pending   : {len(expiry_retries)}")

# ── 8. Accounting integrity check ─────────────────────────────────────────
print("\n" + "="*76)
print("ACCOUNTING INTEGRITY CHECK")
print("="*76)
total_realized = 0.0
orphan_exposure = 0.0
for r in rows:
    ev = r.get("event","").upper()
    if ev in ("CLOSE","SESSION_EXPIRED","SESSION_EXPIRED_EXTENDED"):
        try:
            total_realized += float(r.get("pnl","0") or 0)
        except Exception:
            pass

# Orphan exposure (unclosed with no pnl)
for oid, info in unclosed.items():
    r = info["open_row"]
    try:
        entry = float(r["entry"])
        qty   = int(float(r["qty"]))
        orphan_exposure += entry * qty
    except Exception:
        pass

print(f"  Total realized P&L in CSV (all time) : ₹{total_realized:+,.0f}")
print(f"  Notional exposure of unclosed orphans : ₹{orphan_exposure:,.0f}")
print(f"  (Note: orphan P&L is neither booked nor written — accounting gap)")

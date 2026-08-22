"""smoke_test_reports.py — verify all 6 report generators work."""
import os, sqlite3, uuid
os.environ["OIOS_DB_PATH"] = ":memory:"
from oios.db.migrations import apply_phase_e1
from oios.db.calendar import populate_trading_calendar_with_names
from datetime import date, timedelta

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON;")
apply_phase_e1(conn=conn)
populate_trading_calendar_with_names(conn, "2025-01-01", "2027-12-31")

# Seed OHLCV
sym = "HAL.NS"
for i in range(25):
    d = (date(2026, 5, 15) + timedelta(days=i)).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO ohlcv_daily "
        "(symbol,trade_date,open,high,low,close,volume,adjusted_close,data_source) "
        "VALUES (?,?,100,102,99,101,100000,NULL,'TEST')",
        (sym, d),
    )

# Seed event
from oios.engine.event_ingestion import ingest_event
ingest_event(conn, symbol=sym, event_type="ORDER_WIN",
             event_date="2026-06-15", direction="POSITIVE",
             magnitude="HIGH", headline="HAL wins order", source="BSE", confidence=0.9)

# Seed signal_birth + opportunity
sid, oid = str(uuid.uuid4()), str(uuid.uuid4())
conn.execute(
    "INSERT INTO signal_births "
    "(signal_id,symbol,archetype_id,archetype_version,signal_type,"
    "detected_at,birth_price,base_score,regime_at_birth,"
    "expected_ttl_days,expected_move_direction,current_state,expected_move_pct)"
    " VALUES (?,?,?,1,'1A','2026-06-10',100.0,7.0,'TRENDING_UP',18,'LONG','ACTIVE',8.0)",
    (sid, sym, "DNA_1A_MOMENTUM_CONT"),
)
conn.execute(
    "INSERT INTO opportunities "
    "(opportunity_id,symbol,direction,sector,created_at,first_signal_id,"
    "regime_at_birth,birth_ttl_days,effective_ttl_days,discovered_expires_at,"
    "current_state,conviction_score,confirming_count,age_trading_days)"
    " VALUES (?,?,?,?,?,?,?,18,18,'2026-06-28','ACTIVE',7.5,3,4)",
    (oid, sym, "LONG", "DEFENCE", "2026-06-10", sid, "TRENDING_UP"),
)
conn.execute(
    "INSERT OR IGNORE INTO opportunity_signals "
    "(opportunity_id,signal_id,signal_type,signal_direction,evidence_weight,added_at)"
    " VALUES (?,?,'1A','CONFIRMING',1.0,'2026-06-10')",
    (oid, sid),
)
conn.execute(
    "INSERT INTO sector_conviction_daily "
    "(record_date,sector,sector_conviction_score,stocks_with_data,stocks_total)"
    " VALUES ('2026-06-16','DEFENCE',7.5,5,10)",
)
conn.commit()

from oios.engine.cause_intelligence import compute_cause_score
compute_cause_score(conn, oid, "2026-06-16")
from oios.engine.shadow_scorer import record_shadow_score
record_shadow_score(conn, oid, "2026-06-16", live_os=7.5)
conn.commit()

# ── Run all reports ──────────────────────────────────────────────────────
DATE = "2026-06-16"
from oios.reporting.data_health import generate_data_health_report
from oios.reporting.oios_activity import generate_oios_activity_report
from oios.reporting.phase_d_shadow import generate_phase_d_shadow_report
from oios.reporting.phase_e_shadow import generate_phase_e_shadow_report
from oios.reporting.readiness_gates import generate_readiness_gate_summary
from oios.reporting.weekly_report import generate_weekly_report

print("\n--- Smoke Test: OIOS Report Generators ---\n")
all_ok = True
for name, fn in [
    ("data_health",    generate_data_health_report),
    ("oios_activity",  generate_oios_activity_report),
    ("phase_d_shadow", generate_phase_d_shadow_report),
    ("phase_e_shadow", generate_phase_e_shadow_report),
    ("readiness_gates",generate_readiness_gate_summary),
]:
    try:
        out = fn(conn, DATE)
        n = len(out.splitlines())
        assert n > 10, f"too short ({n} lines)"
        print(f"  OK  {name:<22}  {n} lines")
    except Exception as e:
        import traceback
        print(f"  FAIL {name}: {e}")
        traceback.print_exc()
        all_ok = False

try:
    out = generate_weekly_report(conn, DATE)
    n = len(out.splitlines())
    assert n > 10
    print(f"  OK  weekly_report         {n} lines")
except Exception as e:
    import traceback
    print(f"  FAIL weekly_report: {e}")
    traceback.print_exc()
    all_ok = False

conn.close()
print("\nAll OK." if all_ok else "\nSome failures.")

"""Phase A Forensic Audit script — run directly."""
import sqlite3, os, sys, ast, re
from pathlib import Path

os.environ["OIOS_DB_PATH"] = ":memory:"

# ── Setup ──────────────────────────────────────────────────────────────────
from oios.db.migrations import apply_phase_a
from oios.db.calendar import populate_trading_calendar_with_names

c = sqlite3.connect(":memory:")
c.row_factory = sqlite3.Row
c.execute("PRAGMA foreign_keys=ON;")
apply_phase_a(conn=c)
populate_trading_calendar_with_names(c, "2026-01-01", "2026-12-31", {})

PASS = "PASS"
FAIL = "FAIL"
findings = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    findings.append((name, status, detail))
    marker = "✓" if condition else "✗"
    print(f"  {marker} {name}: {status}" + (f" — {detail}" if detail else ""))

# ===========================================================================
# AUDIT A-1: Schema compliance
# ===========================================================================
print("\n=== AUDIT A-1: Schema Compliance ===")

for tbl in ["universe_stocks", "ohlcv_daily", "bhav_daily", "bulk_block_deals"]:
    cols = {r["name"]: dict(r) for r in c.execute(f"PRAGMA table_info({tbl})").fetchall()}
    print(f"\n  Table: {tbl}")
    for name, info in cols.items():
        print(f"    {name:35} {info['type']:15} notnull={info['notnull']} dflt={info['dflt_value']}")

# universe_stocks required columns
us_cols = {r["name"] for r in c.execute("PRAGMA table_info(universe_stocks)").fetchall()}
for col in ["symbol","company_name","sector","sector_purity_score","is_active","added_date","removed_date","removal_reason"]:
    check(f"A1.us.{col}_exists", col in us_cols)

# ohlcv_daily required columns
od_cols = {r["name"] for r in c.execute("PRAGMA table_info(ohlcv_daily)").fetchall()}
for col in ["symbol","trade_date","open","high","low","close","volume","adjusted_close","data_source","fetched_at"]:
    check(f"A1.od.{col}_exists", col in od_cols)

# PK uniqueness on ohlcv_daily
pk_info = c.execute("PRAGMA table_info(ohlcv_daily)").fetchall()
pk_cols = [r["name"] for r in pk_info if r["pk"] > 0]
check("A1.od.pk_is_symbol_date", set(pk_cols) == {"symbol", "trade_date"}, str(pk_cols))

# bhav_daily
bd_cols = {r["name"] for r in c.execute("PRAGMA table_info(bhav_daily)").fetchall()}
for col in ["symbol","trade_date","series","traded_quantity","deliverable_qty","delivery_pct","data_source"]:
    check(f"A1.bd.{col}_exists", col in bd_cols)
bd_pk = [r["name"] for r in c.execute("PRAGMA table_info(bhav_daily)").fetchall() if r["pk"] > 0]
check("A1.bd.pk_is_symbol_date", set(bd_pk) == {"symbol", "trade_date"}, str(bd_pk))

# bulk_block_deals
bb_cols = {r["name"] for r in c.execute("PRAGMA table_info(bulk_block_deals)").fetchall()}
for col in ["deal_id","trade_date","symbol","deal_type","client_name","buy_sell","quantity","price","sector","data_source"]:
    check(f"A1.bb.{col}_exists", col in bb_cols)

# Indexes
print("\n  Indexes:")
idx_rows = c.execute(
    "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND tbl_name IN "
    "('universe_stocks','ohlcv_daily','bhav_daily','bulk_block_deals')"
).fetchall()
for r in idx_rows:
    print(f"    [{r['tbl_name']}] {r['name']}")
check("A1.ohlcv_has_symbol_date_idx", any("ohlcv" in r["name"] for r in idx_rows))
check("A1.bhav_has_symbol_date_idx",  any("bhav" in r["name"] for r in idx_rows))
check("A1.bbd_has_sector_idx",        any("sector" in r["name"] for r in idx_rows))

# ===========================================================================
# AUDIT A-2: Universe integrity
# ===========================================================================
print("\n=== AUDIT A-2: Universe Integrity ===")

from oios.seeds.universe_230 import UNIVERSE_230
from collections import Counter

syms = [x[0] for x in UNIVERSE_230]
total = len(UNIVERSE_230)
unique = len(set(syms))
dups = [s for s in set(syms) if syms.count(s) > 1]
sects = Counter(x[2] for x in UNIVERSE_230)

check("A2.total_exactly_230", total == 230, f"actual={total}")
check("A2.no_duplicates", len(dups) == 0, f"dups={dups}")
check("A2.all_sectors_present", len(sects) == 12, f"sectors={len(sects)}")
check("A2.all_have_ns_suffix", all(s.endswith(".NS") for s in syms), 
      str([s for s in syms if not s.endswith(".NS")]))
check("A2.all_have_sector", all(x[2] for x in UNIVERSE_230))
check("A2.all_have_company_name", all(x[1].strip() for x in UNIVERSE_230))

# Exact counts per sector
print(f"\n  Sector counts: {dict(sects)}")
print(f"  Total: {total}  Unique: {unique}  Expected: 230")

# ===========================================================================
# AUDIT A-3: Sector purity
# ===========================================================================
print("\n=== AUDIT A-3: Sector Purity ===")

purities = [x[3] for x in UNIVERSE_230]
check("A3.no_zeros",     all(p > 0 for p in purities), str([p for p in purities if p <= 0]))
check("A3.no_negatives", all(p > 0 for p in purities))
check("A3.max_le_1",     all(p <= 1.0 for p in purities), str([p for p in purities if p > 1.0]))
check("A3.min_gt_0",     min(purities) > 0, f"min={min(purities)}")
print(f"  Range: {min(purities)} – {max(purities)}")

# ===========================================================================
# AUDIT A-4: Scanner purity (static analysis)
# ===========================================================================
print("\n=== AUDIT A-4: Scanner Purity ===")

scanner_path = Path("oios/scanners/layer_1a.py")
scanner_src  = scanner_path.read_text(encoding="utf-8")

# These patterns are illegal in a pure scanner
write_patterns = [
    (r"conn\.execute\s*\(\s*[\"']INSERT",      "Direct INSERT"),
    (r"conn\.execute\s*\(\s*[\"']UPDATE",      "Direct UPDATE"),
    (r"conn\.execute\s*\(\s*[\"']DELETE",      "Direct DELETE"),
    (r"from.*repository.*import",              "Repository import"),
    (r"import.*repository",                    "Repository import"),
    (r"R\.create_",                             "Repository write call"),
    (r"R\.append_",                             "Repository write call"),
    (r"R\.upsert_",                             "Repository write call"),
    (r"R\.add_opportunity",                     "Repository write call"),
    (r"R\.log_decision",                        "Repository write call"),
    (r"R\.emit_event",                          "Repository write call"),
    (r"conn\.executemany",                      "Direct executemany"),
]
# Allowed: conn.execute for READ only (SELECT)
# Check: any conn.execute that is NOT a SELECT
import re
# Extract all conn.execute calls
execute_calls = re.findall(r"conn\.execute\s*\([^\)]*\)", scanner_src)
execute_calls_multiline = re.findall(r'conn\.execute\s*\(\s*"""[\s\S]*?"""', scanner_src)
all_executes = execute_calls + execute_calls_multiline

write_violations = []
for ec in all_executes:
    ec_stripped = ec.strip()
    if re.search(r'INSERT|UPDATE|DELETE', ec_stripped, re.IGNORECASE):
        write_violations.append(ec_stripped[:80])

check("A4.no_direct_db_writes_in_scanner", len(write_violations) == 0,
      str(write_violations))

# Check for repository imports
repo_imports = re.findall(r"^(?:from|import).*repositor.*$", scanner_src, re.MULTILINE)
check("A4.no_repository_imports", len(repo_imports) == 0, str(repo_imports))

# Confirm READ access is allowed (SELECT for price data)
select_calls = [ec for ec in all_executes if re.search(r'SELECT', ec, re.IGNORECASE)]
print(f"  SELECT calls in scanner (allowed): {len(select_calls)}")

# ===========================================================================
# AUDIT A-5: Opportunity service boundary
# ===========================================================================
print("\n=== AUDIT A-5: Service Boundary ===")

# Search for direct DB writes outside service + signal_writer
oios_root = Path("oios")
violations = []

for py_file in oios_root.rglob("*.py"):
    rel = py_file.relative_to(oios_root)
    # Service and repository are allowed to write; signal_writer too
    allowed_writers = {
        "db/repository.py",
        "domain/opportunity_service.py",
        "scanners/signal_writer.py",
        "db/universe.py",
        "data/ohlcv_fetcher.py",
        "data/bhav_fetcher.py",
        "data/bulk_block_fetcher.py",
        "db/calendar.py",
        "db/migrations.py",
    }
    rel_str = str(rel).replace("\\", "/")
    if rel_str in allowed_writers:
        continue

    src = py_file.read_text(encoding="utf-8")
    # Check for opportunity/signal_birth creation outside allowed writers
    opp_creates = re.findall(r"create_opportunity|INSERT INTO opportunities|INSERT INTO signal_births", src)
    if opp_creates:
        violations.append(f"{rel_str}: {opp_creates}")

check("A5.no_rogue_opportunity_creators", len(violations) == 0, str(violations))

# Confirm signal_writer is the only caller of attach_or_create_opportunity
callers = []
for py_file in oios_root.rglob("*.py"):
    src = py_file.read_text(encoding="utf-8")
    if "attach_or_create_opportunity" in src:
        rel_str = str(py_file.relative_to(oios_root)).replace("\\", "/")
        callers.append(rel_str)

check("A5.service_called_only_from_signal_writer",
      all(c in {"domain/opportunity_service.py", "scanners/signal_writer.py"} for c in callers),
      str(callers))

# ===========================================================================
# AUDIT A-6: OHLCV integrity
# ===========================================================================
print("\n=== AUDIT A-6: OHLCV Integrity ===")

from oios.data.ohlcv_fetcher import upsert_ohlcv_rows, get_latest_date

rows_1 = [("TEST.NS","2026-06-01",100.0,105.0,99.0,102.0,1e6,102.0,"TEST")]
with c:
    n1 = upsert_ohlcv_rows(c, rows_1)
with c:
    n2 = upsert_ohlcv_rows(c, rows_1)   # exact duplicate

check("A6.duplicate_insert_ignored", n2 == 0, f"second insert returned rowcount={n2}")
check("A6.first_insert_accepted",    n1 == 1)

# Adjusted close stored separately from close
cols_od = {r["name"] for r in c.execute("PRAGMA table_info(ohlcv_daily)").fetchall()}
check("A6.adjusted_close_column_exists", "adjusted_close" in cols_od)
check("A6.close_column_exists",          "close" in cols_od)

# Gap detection function exists and is importable
from oios.data.ohlcv_fetcher import find_gaps
check("A6.gap_detection_importable", True)

# ===========================================================================
# AUDIT A-7: Opportunity merge rule boundary
# ===========================================================================
print("\n=== AUDIT A-7: Merge Rule Boundary ===")

service_src = Path("oios/domain/opportunity_service.py").read_text(encoding="utf-8")

# MAS spec: age < effective_ttl × 0.75  (strictly less than, not <=)
# The within_merge_window() method in models.py must use strict <
models_src = Path("oios/domain/models.py").read_text(encoding="utf-8")
merge_fn = re.search(r"def within_merge_window.*?(?=\n    def |\nclass |\Z)", models_src, re.DOTALL)
if merge_fn:
    fn_text = merge_fn.group()
    print(f"  within_merge_window() body:\n{fn_text}")
    # Check it uses < not <=
    uses_strict_lt = bool(re.search(r"age_trading_days\s*<\s*self\.effective_ttl", fn_text))
    uses_lte       = bool(re.search(r"age_trading_days\s*<=\s*self\.effective_ttl", fn_text))
    check("A7.merge_window_uses_strict_lt", uses_strict_lt and not uses_lte,
          f"strict_lt={uses_strict_lt} lte={uses_lte}")
else:
    check("A7.merge_window_fn_found", False, "within_merge_window not found in models.py")

# Check the multiplier is exactly 0.75
check("A7.multiplier_is_0_75",
      "0.75" in models_src and "within_merge_window" in models_src)

# ===========================================================================
# AUDIT A-8: Event integrity (THESIS_INVALIDATED_WITH_POSITION)
# ===========================================================================
print("\n=== AUDIT A-8: Event Integrity ===")

sm_src = Path("oios/domain/state_machine.py").read_text(encoding="utf-8")

# Count multiline-safe: events.append(_event(\n    EventType.THESIS_INVALIDATED...
thesis_appends = re.findall(
    r"events\.append\s*\(\s*_event\s*\(\s*\n?\s*EventType\.THESIS_INVALIDATED_WITH_POSITION",
    sm_src,
)
check("A8.thesis_event_appended_exactly_once_in_code",
      len(thesis_appends) == 1, f"found {len(thesis_appends)} append(s)")

# Verify it is guarded by position_exists check
guard_pattern = re.search(
    r"if\s+opp\.position_exists.*?THESIS_INVALIDATED_WITH_POSITION",
    sm_src, re.DOTALL
)
check("A8.thesis_event_guarded_by_position_exists",
      guard_pattern is not None)

# Verify THESIS event fires BEFORE transition record WITHIN try_invalidate
# Extract the body of try_invalidate
try_inv_match = re.search(
    r"def try_invalidate[\s\S]*?(?=\ndef [a-z]|\Z)",
    sm_src,
)
if try_inv_match:
    inv_body = try_inv_match.group(0)
    thesis_in_fn   = inv_body.find("THESIS_INVALIDATED_WITH_POSITION")
    transition_in_fn = inv_body.find("transitions.append")
    check("A8.thesis_event_emitted_before_transition_record",
          0 < thesis_in_fn < transition_in_fn,
          f"thesis@{thesis_in_fn} transition@{transition_in_fn}")
else:
    check("A8.thesis_event_emitted_before_transition_record", False,
          "try_invalidate function not found")

# ===========================================================================
# AUDIT A-9: Architecture freeze compliance
# ===========================================================================
print("\n=== AUDIT A-9: Freeze Compliance ===")

oios_root_path = Path("oios")
forbidden_patterns = [
    ("TODO redesign",   r"TODO\s+redesign"),
    ("FIXME",           r"FIXME"),
    ("HACK:",           r"HACK\s*:"),
    ("TEMP:",           r"TEMP\s*:"),
    ("WORKAROUND",      r"WORKAROUND"),
    ("EXPERIMENTAL",    r"EXPERIMENTAL"),
    ("XXX:",            r"XXX\s*:"),
]
freeze_violations = []
for py_file in oios_root_path.rglob("*.py"):
    src = py_file.read_text(encoding="utf-8")
    for label, pattern in forbidden_patterns:
        if re.search(pattern, src, re.IGNORECASE):
            freeze_violations.append(f"{py_file.name}: {label}")

check("A9.no_freeze_violations", len(freeze_violations) == 0, str(freeze_violations))

# ===========================================================================
# AUDIT A-10: Buildability check
# ===========================================================================
print("\n=== AUDIT A-10: Buildability ===")

# Phase B needs: sector_conviction_daily and theme_phase_history tables (not yet created)
# Verify that apply_phase_a does NOT create them (they must not exist yet)
existing_tables = {r[0] for r in c.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()}
check("A10.phase_b_tables_not_yet_created",
      "sector_conviction_daily" not in existing_tables and "theme_phase_history" not in existing_tables)

# Verify that apply_phase_a is additive (does not alter A0 tables)
a0_tables = {
    "opportunities","signal_births","opportunity_signals",
    "signal_state_transitions","decision_log","oios_events","trading_calendar",
    "stock_sector_map","archetype_versions"
}
check("A10.all_a0_tables_still_present", a0_tables.issubset(existing_tables),
      str(a0_tables - existing_tables))

# Verify Layer 1B can be added without touching Layer 1A code
# (structural: signal_births already has signal_type column accepting "1B")
sb_type_col = c.execute("PRAGMA table_info(signal_births)").fetchall()
type_col_check = [r for r in sb_type_col if r["name"] == "signal_type"]
if type_col_check:
    constraint_sql = c.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='signal_births'"
    ).fetchone()[0]
    has_1b_in_check = "1B" in (constraint_sql or "")
    check("A10.signal_births_accepts_1B_type", has_1b_in_check, constraint_sql[:120] if constraint_sql else "")

# ===========================================================================
# Summary
# ===========================================================================
print("\n" + "="*60)
print("PHASE A FORENSIC AUDIT — SUMMARY")
print("="*60)
total_checks = len(findings)
passed = sum(1 for _, s, _ in findings if s == PASS)
failed = sum(1 for _, s, _ in findings if s == FAIL)
print(f"  Total checks: {total_checks}")
print(f"  PASS:  {passed}")
print(f"  FAIL:  {failed}")
print()
if failed > 0:
    print("FINDINGS (FAIL):")
    for name, status, detail in findings:
        if status == FAIL:
            print(f"  [FAIL] {name}")
            if detail:
                print(f"         {detail}")
else:
    print("  All checks passed.")

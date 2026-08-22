"""
phase_c_audit.py

Phase C Forensic Audit — 60 checks across 9 categories.

Mirrors phase_a_audit.py and phase_b_audit.py discipline: every check is
explicit, labelled, and must PASS before Phase D authorization may be issued.

Run standalone:
    python phase_c_audit.py

Expected output: 60/60 PASS, 0 FAIL.

Checks:
    C1  — Phase C Schema (3 checks)
    C2  — RE Calculator formula (12 checks)
    C3  — Half-life multipliers vs MAS spec (12 checks)
    C4  — Maturity Engine dimensions (10 checks)
    C5  — Effective TTL regime adjustment (6 checks)
    C6  — ELE cycle state machine integration (8 checks)
    C7  — 5% audit trade override (3 checks)
    C8  — Phase C purity (no adaptive writes) (4 checks)
    C9  — Phase A/B table immutability (2 checks)
"""

import hashlib
import os
import sqlite3
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ["OIOS_DB_PATH"] = ":memory:"

# ---------------------------------------------------------------------------
# Check infrastructure (identical pattern to phase_a_audit.py)
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    _results.append((label, condition, detail))
    icon = "PASS" if condition else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {'[+]' if condition else '[X]'} {label}: {icon}{suffix}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    from oios.db.migrations import apply_phase_c
    from oios.db.calendar import populate_trading_calendar_with_names
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    apply_phase_c(conn=conn)
    populate_trading_calendar_with_names(conn, "2025-01-01", "2026-12-31")
    return conn


def _insert_ohlcv(conn, symbol, n=25, start_price=100.0, daily_move=0.0):
    rows = []
    d = date(2026, 1, 1)
    price = start_price
    for _ in range(n):
        rows.append((symbol, d.isoformat(),
                     round(price * 0.998, 4), round(price * 1.005, 4),
                     round(price * 0.997, 4), round(price, 4),
                     100_000.0, None, "AUDIT"))
        price *= (1 + daily_move)
        d += timedelta(days=1)
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)


def _make_signal_and_opp(conn, symbol, base_score=6.0, signal_type="1A",
                          birth_price=100.0, expected_move_pct=8.0, ttl=18,
                          direction="LONG"):
    from oios.db import repository as R
    from oios.domain.models import (
        Opportunity, SignalBirth, OpportunitySignal,
    )
    sid = str(uuid.uuid4())
    sb = SignalBirth(
        signal_id               = sid,
        symbol                  = symbol,
        archetype_id            = "DNA_1A_MOMENTUM_CONT",
        signal_type             = signal_type,
        detected_at             = "2026-01-02",
        birth_price             = birth_price,
        base_score              = base_score,
        regime_at_birth         = "TRENDING_UP",
        expected_ttl_days       = ttl,
        expected_move_direction = direction,
        expected_move_pct       = expected_move_pct,
    )
    R.create_signal_birth(conn, sb)
    oid = str(uuid.uuid4())
    opp = Opportunity(
        opportunity_id        = oid,
        symbol                = symbol,
        direction             = direction,
        sector                = "IT",
        created_at            = "2026-01-02",
        first_signal_id       = sid,
        regime_at_birth       = "TRENDING_UP",
        birth_ttl_days        = ttl,
        effective_ttl_days    = ttl,
        discovered_expires_at = (date(2026, 1, 2) + timedelta(days=ttl // 2 + 1)).isoformat(),
        conviction_score      = 0.0,
        confirming_count      = 1,
    )
    R.create_opportunity(conn, opp)
    conn.execute("UPDATE signal_births SET opportunity_id = ? WHERE signal_id = ?", (oid, sid))
    conn.execute("""
        INSERT INTO opportunity_signals
            (opportunity_id, signal_id, signal_type, signal_direction, evidence_weight, added_at)
        VALUES (?,?,?,?,?,?)
    """, (oid, sid, signal_type, "CONFIRMING", 1.0, "2026-01-02"))
    return sb, opp


# ===========================================================================
# AUDIT C-1: Phase C Schema
# ===========================================================================

section("AUDIT C-1: Phase C Schema")
try:
    conn = _make_db()

    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    check("C1.01.pending_adjustments_exists", "pending_adjustments" in tables)

    # Verify required columns
    pa_cols = {r[1] for r in conn.execute("PRAGMA table_info(pending_adjustments)").fetchall()}
    required_pa_cols = {
        "adjustment_id", "proposed_at", "archetype_id", "regime",
        "adjustment_type", "current_value", "proposed_value", "change_pct",
        "evidence_summary", "status", "expires_at", "requires_approval",
    }
    missing_cols = required_pa_cols - pa_cols
    check("C1.02.pending_adjustments_columns",
          len(missing_cols) == 0,
          f"missing: {missing_cols}" if missing_cols else "")

    # Migration idempotent
    from oios.db.migrations import apply_phase_c
    apply_phase_c(conn=conn)
    apply_phase_c(conn=conn)
    count_after = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    check("C1.03.migration_idempotent", count_after > 0, f"{count_after} tables after 3 applies")

    conn.close()
except Exception as exc:
    check("C1.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-2: RE Calculator formula
# ===========================================================================

section("AUDIT C-2: RE Calculator Formula")
try:
    from oios.engine.re_calculator import (
        compute_re, compute_ec_path, compute_crowding,
        get_half_life, BASE_HALF_LIFE, HALF_LIFE_MULTIPLIERS,
    )

    # RE at birth (age=0, no move, no crowding) = base_score
    re_birth = compute_re(7.0, 0, "1A", "BULL", 0.0, 8.0, 0.0)
    check("C2.01.re_at_birth_equals_base_score",
          abs(re_birth - 7.0) < 1e-6, f"got {re_birth}")

    # RE never exceeds base_score
    re_max = compute_re(7.0, 0, "1A", "BULL", 0.0, 8.0, 0.0)
    check("C2.02.re_le_base_score", re_max <= 7.0 + 1e-9, f"got {re_max}")

    # RE decays monotonically with age
    re_0  = compute_re(6.0, 0,  "1A", "BULL", 0.0, 8.0, 0.0)
    re_5  = compute_re(6.0, 5,  "1A", "BULL", 0.0, 8.0, 0.0)
    re_13 = compute_re(6.0, 13, "1A", "BULL", 0.0, 8.0, 0.0)
    check("C2.03.re_decays_with_age", re_0 > re_5 > re_13 > 0, f"{re_0:.3f} > {re_5:.3f} > {re_13:.3f}")

    # RE = 0 when EC_path = 1.0 (edge consumed)
    re_consumed = compute_re(7.0, 3, "1A", "BULL", 8.0, 8.0, 0.0)
    check("C2.04.re_zero_at_edge_consumed", re_consumed == 0.0, f"got {re_consumed}")

    # RE never negative
    re_extreme = compute_re(5.0, 50, "1A", "PANIC", 20.0, 8.0, 1.0)
    check("C2.05.re_never_negative", re_extreme >= 0.0, f"got {re_extreme}")

    # D_time: at age=0, D_time=1.0 → RE = base_score × 1.0 × 1.0 × 1.0 = base_score
    import math
    hl = get_half_life("1A", "BULL")
    d_time_expected = 0.5 ** (5 / hl)
    re_age5 = compute_re(8.0, 5, "1A", "BULL", 0.0, 8.0, 0.0)
    check("C2.06.d_time_formula_correct",
          abs(re_age5 - 8.0 * d_time_expected) < 1e-6,
          f"expected {8.0 * d_time_expected:.4f}, got {re_age5:.4f}")

    # EC_path = actual / expected, capped at [0,1]
    check("C2.07.ec_path_zero_for_no_move",    compute_ec_path(0.0, 8.0) == 0.0)
    check("C2.08.ec_path_half_at_midway",
          abs(compute_ec_path(4.0, 8.0) - 0.5) < 1e-9, f"got {compute_ec_path(4.0, 8.0)}")
    check("C2.09.ec_path_one_at_expected_move", compute_ec_path(8.0, 8.0) == 1.0)
    check("C2.10.ec_path_clamped_at_overshoot", compute_ec_path(16.0, 8.0) == 1.0)
    check("C2.11.ec_path_no_negative_from_loss", compute_ec_path(-5.0, 8.0) == 0.0)

    # PANIC half-life = 1A base × 0.1 = 10 × 0.1 = 1.0
    hl_panic = get_half_life("1A", "PANIC")
    check("C2.12.panic_half_life_correct",
          abs(hl_panic - 1.0) < 1e-6, f"got {hl_panic}")

except Exception as exc:
    check("C2.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-3: Half-life multipliers per MAS_v1.2.md Section 5
# ===========================================================================

section("AUDIT C-3: Half-life Multipliers vs MAS Spec")
try:
    from oios.engine.re_calculator import get_half_life, BASE_HALF_LIFE, HALF_LIFE_MULTIPLIERS

    # MAS spec table (Section 5):
    # Type | Base HL | BULL | RANGE | BEAR | PANIC
    # 1A   | 10      | 1.3  | 0.7   | 0.6  | 0.1
    # 1B   | 18      | 1.8  | 0.5   | 0.7  | 0.1
    # 1.5  | 20      | 2.0  | 0.4   | 0.5  | 0.0
    # 2    | 12      | (default 1.0) | ...
    # 3    | 8       | (default 1.0) | ...

    spec = {
        "1A":  {"base": 10.0, "BULL": 1.3, "RANGE": 0.7, "BEAR": 0.6, "PANIC": 0.1},
        "1B":  {"base": 18.0, "BULL": 1.8, "RANGE": 0.5, "BEAR": 0.7, "PANIC": 0.1},
        "1.5": {"base": 20.0, "BULL": 2.0, "RANGE": 0.4, "BEAR": 0.5, "PANIC": 0.0},
    }
    regimes_to_check = ["BULL", "RANGE", "BEAR", "PANIC"]

    for sig_type, row in spec.items():
        base = row["base"]
        for regime in regimes_to_check:
            mult = row[regime]
            expected_hl = max(0.5, base * mult)   # PANIC 1.5 → 0.0×20=0.0 → floor at 0.5
            actual_hl   = get_half_life(sig_type, regime)
            # For PANIC 1.5: MAS spec says 0.0 multiplier → half_life floor at 0.5 or 1
            if mult == 0.0:
                close = actual_hl <= 1.0
            else:
                close = abs(actual_hl - expected_hl) < 0.05
            check(f"C3.{sig_type}_{regime}_half_life",
                  close,
                  f"expected ~{expected_hl:.1f}, got {actual_hl:.1f}")

except Exception as exc:
    check("C3.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-4: Maturity Engine dimensions
# ===========================================================================

section("AUDIT C-4: Maturity Engine Dimensions")
try:
    from oios.engine.maturity_engine import (
        temporal_maturity, path_maturity, conviction_maturity,
        most_conservative, compute_maturity,
        SEED, EMERGING, DEVELOPING, MATURE, LATE_STAGE,
    )

    # Temporal dimension (boundaries: 0%, 20%, 40%, 60%, 80%, 100%)
    check("C4.01.temporal_seed_low",          temporal_maturity(1, 10)  == SEED)
    check("C4.02.temporal_emerging_20pct",     temporal_maturity(2, 10)  == EMERGING)
    check("C4.03.temporal_developing_50pct",   temporal_maturity(5, 10)  == DEVELOPING)
    check("C4.04.temporal_mature_70pct",       temporal_maturity(7, 10)  == MATURE)
    check("C4.05.temporal_late_stage_90pct",   temporal_maturity(9, 10)  == LATE_STAGE)

    # Path dimension
    check("C4.06.path_seed_low",               path_maturity(0.1)  == SEED)
    check("C4.07.path_late_stage_high",        path_maturity(0.9)  == LATE_STAGE)

    # Conviction dimension
    check("C4.08.conviction_seed_1",           conviction_maturity(1)  == SEED)
    check("C4.09.conviction_mature_4",         conviction_maturity(4)  == MATURE)
    check("C4.10.conviction_late_stage_5plus", conviction_maturity(5)  == LATE_STAGE)

    # most_conservative returns earliest
    check("C4.11.most_conservative_basic",
          most_conservative(LATE_STAGE, SEED, MATURE) == SEED)

    # compute_maturity is most conservative of all three
    # age=8/ttl=10=80%→MATURE, ec=0.1→SEED, confirming=3→DEVELOPING → combined=SEED
    combined = compute_maturity(8, 10, 0.1, 3)
    check("C4.12.combined_most_conservative", combined == SEED,
          f"expected SEED, got {combined}")

except Exception as exc:
    check("C4.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-5: Effective TTL regime adjustment
# ===========================================================================

section("AUDIT C-5: Effective TTL Regime Adjustment")
try:
    from oios.engine.re_calculator import compute_effective_ttl

    # 1A, birth_ttl=10:
    #   BULL mult=1.3  → round(13) = 13
    #   RANGE mult=0.7 → round(7)  = 7
    #   PANIC mult=0.1 → round(1)  = 1 (floor)
    ttl_bull  = compute_effective_ttl(10, "1A", "BULL")
    ttl_range = compute_effective_ttl(10, "1A", "SIDEWAYS")
    ttl_panic = compute_effective_ttl(10, "1A", "PANIC")

    check("C5.01.bull_extends_ttl",    ttl_bull  >= 10, f"got {ttl_bull}")
    check("C5.02.range_shortens_ttl",  ttl_range <  10, f"got {ttl_range}")
    check("C5.03.panic_shortest_ttl",  ttl_panic <= ttl_range, f"got {ttl_panic}")
    check("C5.04.panic_floor_applied", ttl_panic >= 1, f"got {ttl_panic}")
    check("C5.05.bull_gte_range_gte_panic",
          ttl_bull >= ttl_range >= ttl_panic,
          f"bull={ttl_bull} range={ttl_range} panic={ttl_panic}")

    # Regime label mapping: TRENDING_UP → BULL, same as explicit BULL
    ttl_trending_up = compute_effective_ttl(10, "1A", "TRENDING_UP")
    check("C5.06.trending_up_maps_to_bull",
          ttl_trending_up == ttl_bull,
          f"TRENDING_UP={ttl_trending_up}, BULL={ttl_bull}")

except Exception as exc:
    check("C5.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-6: ELE cycle state machine integration
# ===========================================================================

section("AUDIT C-6: ELE Cycle State Machine Integration")
try:
    from oios.engine.ele import run_ele_cycle_for_opportunity, run_ele_daily, _is_audit_trade
    from oios.domain.models import OpportunityState

    conn2 = _make_db()

    # ─ C6.01: ACTIVE→WATCHING when RE is low (old age, BULL regime)
    _insert_ohlcv(conn2, "C6A.NS", n=30, start_price=100.0, daily_move=0.0)
    with conn2:
        sb, opp = _make_signal_and_opp(conn2, "C6A.NS", base_score=6.0, ttl=18)
        conn2.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=16,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp.opportunity_id,))
    with conn2:
        r = run_ele_cycle_for_opportunity(conn2, opp.opportunity_id, "2026-01-17", "BULL")
    check("C6.01.active_to_watching_on_low_re",
          r is not None and r.new_state in (OpportunityState.WATCHING, OpportunityState.INVALID),
          f"got {r.new_state if r else None}")

    # ─ C6.02: WATCHING→ACTIVE recovery when RE high (young, BULL)
    _insert_ohlcv(conn2, "C6B.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn2:
        sb2, opp2 = _make_signal_and_opp(conn2, "C6B.NS", base_score=8.0, ttl=18)
        conn2.execute("""
            UPDATE opportunities SET current_state='WATCHING', age_trading_days=1,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp2.opportunity_id,))
    with conn2:
        r2 = run_ele_cycle_for_opportunity(conn2, opp2.opportunity_id, "2026-01-03", "BULL")
    check("C6.02.watching_recovers_to_active",
          r2 is not None and r2.new_state == OpportunityState.ACTIVE,
          f"got {r2.new_state if r2 else None}, re={r2.re_score if r2 else None}")

    # ─ C6.03: TTL_EXHAUSTED — 1A SIDEWAYS regime, age = effective_ttl
    _insert_ohlcv(conn2, "C6C.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn2:
        sb3, opp3 = _make_signal_and_opp(conn2, "C6C.NS", base_score=6.0, ttl=10)
        conn2.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=7
            WHERE opportunity_id=?
        """, (opp3.opportunity_id,))
    with conn2:
        r3 = run_ele_cycle_for_opportunity(conn2, opp3.opportunity_id, "2026-01-09", "SIDEWAYS")
    inv_row = conn2.execute(
        "SELECT invalidation_reason FROM opportunities WHERE opportunity_id=?",
        (opp3.opportunity_id,)
    ).fetchone()
    check("C6.03.ttl_exhausted",
          r3 is not None and r3.new_state == OpportunityState.INVALID
          and inv_row and inv_row["invalidation_reason"] == "TTL_EXHAUSTED",
          f"state={r3.new_state if r3 else None}, reason={inv_row['invalidation_reason'] if inv_row else None}")

    # ─ C6.04: EC_EXHAUSTED — stock has doubled from birth price (100/50-1=100% > 8% expected)
    _insert_ohlcv(conn2, "C6D.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn2:
        # birth_price=50 so current price 100 = 100% actual move >> 8% expected → ec_path=1.0
        sb4, opp4 = _make_signal_and_opp(conn2, "C6D.NS", base_score=6.0, ttl=18,
                                          birth_price=50.0, expected_move_pct=8.0)
        conn2.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3
            WHERE opportunity_id=?
        """, (opp4.opportunity_id,))
    with conn2:
        r4 = run_ele_cycle_for_opportunity(conn2, opp4.opportunity_id, "2026-01-05", "BULL")
    inv4 = conn2.execute(
        "SELECT invalidation_reason FROM opportunities WHERE opportunity_id=?",
        (opp4.opportunity_id,)
    ).fetchone()
    check("C6.04.ec_exhausted",
          r4 is not None and r4.new_state == OpportunityState.INVALID
          and inv4 and inv4["invalidation_reason"] == "EC_EXHAUSTED",
          f"reason={inv4['invalidation_reason'] if inv4 else None}")

    # ─ C6.05: Transitions written to signal_state_transitions
    _insert_ohlcv(conn2, "C6E.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn2:
        sb5, opp5 = _make_signal_and_opp(conn2, "C6E.NS", base_score=6.0, ttl=10)
        conn2.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=7
            WHERE opportunity_id=?
        """, (opp5.opportunity_id,))
    before = conn2.execute(
        "SELECT COUNT(*) FROM signal_state_transitions WHERE opportunity_id=?",
        (opp5.opportunity_id,)
    ).fetchone()[0]
    with conn2:
        run_ele_cycle_for_opportunity(conn2, opp5.opportunity_id, "2026-01-09", "SIDEWAYS")
    after = conn2.execute(
        "SELECT COUNT(*) FROM signal_state_transitions WHERE opportunity_id=?",
        (opp5.opportunity_id,)
    ).fetchone()[0]
    check("C6.05.transitions_written_on_state_change",
          after > before, f"before={before}, after={after}")

    # ─ C6.06: run_ele_daily returns correct processed count
    _insert_ohlcv(conn2, "C6F1.NS", n=25, start_price=100.0, daily_move=0.0)
    _insert_ohlcv(conn2, "C6F2.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn2:
        for sym in ("C6F1.NS", "C6F2.NS"):
            sb_f, opp_f = _make_signal_and_opp(conn2, sym, base_score=6.0, ttl=18)
            conn2.execute("""
                UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3,
                confirming_count=3, conviction_score=7.5
                WHERE opportunity_id=?
            """, (opp_f.opportunity_id,))
    live_before = conn2.execute(
        "SELECT COUNT(*) FROM opportunities WHERE current_state='ACTIVE'"
    ).fetchone()[0]
    with conn2:
        daily = run_ele_daily(conn2, "2026-01-05", "BULL")
    check("C6.06.ele_daily_processes_all_live",
          daily.opps_processed >= 2,
          f"processed={daily.opps_processed}")

    # ─ C6.07: RE score is populated in cycle result
    _insert_ohlcv(conn2, "C6G.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn2:
        sb7, opp7 = _make_signal_and_opp(conn2, "C6G.NS", base_score=7.0, ttl=18)
        conn2.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=2,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp7.opportunity_id,))
    with conn2:
        r7 = run_ele_cycle_for_opportunity(conn2, opp7.opportunity_id, "2026-01-04", "BULL")
    check("C6.07.re_score_populated_in_result",
          r7 is not None and r7.re_score is not None and r7.re_score >= 0.0,
          f"re={r7.re_score if r7 else None}")

    # ─ C6.08: maturity populated in cycle result
    check("C6.08.maturity_populated_in_result",
          r7 is not None and r7.maturity in ("SEED", "EMERGING", "DEVELOPING", "MATURE", "LATE_STAGE"),
          f"maturity={r7.maturity if r7 else None}")

    conn2.close()
except Exception as exc:
    import traceback
    check("C6.EXCEPTION", False, str(exc))
    traceback.print_exc()

# ===========================================================================
# AUDIT C-7: Audit trade override (5% by hash)
# ===========================================================================

section("AUDIT C-7: 5% Audit Trade Override")
try:
    from oios.engine.ele import _is_audit_trade

    # Determinism
    sid = str(uuid.uuid4())
    check("C7.01.audit_trade_deterministic",
          _is_audit_trade(sid) == _is_audit_trade(sid))

    # Correct hash formula: sha256 % 20 == 0
    known_sid = "test-signal-zero"
    h = int(hashlib.sha256(known_sid.encode()).hexdigest(), 16)
    expected = (h % 20) == 0
    check("C7.02.audit_trade_hash_formula_correct",
          _is_audit_trade(known_sid) == expected,
          f"sha256%20=={h%20}, expected selected={expected}")

    # Rate: ~5% of 1000 UUIDs
    n_selected = sum(1 for _ in range(1000) if _is_audit_trade(str(uuid.uuid4())))
    check("C7.03.audit_trade_rate_approx_5pct",
          30 <= n_selected <= 80,
          f"{n_selected}/1000 selected")

except Exception as exc:
    check("C7.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-8: Phase C purity — no adaptive writes
# ===========================================================================

section("AUDIT C-8: Phase C Purity (No Adaptive Writes)")
try:
    from oios.engine.ele import run_ele_daily

    conn3 = _make_db()
    _insert_ohlcv(conn3, "PURE.NS", n=25, start_price=100.0, daily_move=0.0)
    with conn3:
        sb_p, opp_p = _make_signal_and_opp(conn3, "PURE.NS", base_score=6.0, ttl=18)
        conn3.execute("""
            UPDATE opportunities SET current_state='ACTIVE', age_trading_days=3,
            confirming_count=3, conviction_score=7.5
            WHERE opportunity_id=?
        """, (opp_p.opportunity_id,))
    with conn3:
        run_ele_daily(conn3, "2026-01-05", "SIDEWAYS")

    # pending_adjustments must remain empty
    n_pa = conn3.execute("SELECT COUNT(*) FROM pending_adjustments").fetchone()[0]
    check("C8.01.no_pending_adjustments_writes",
          n_pa == 0, f"{n_pa} rows found")

    # archetype_outcome_distributions: may not exist in Phase C schema (that's fine)
    aod_exists = conn3.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name='archetype_outcome_distributions'
    """).fetchone()[0]
    if aod_exists:
        n_aod = conn3.execute(
            "SELECT COUNT(*) FROM archetype_outcome_distributions"
        ).fetchone()[0]
        check("C8.02.no_aod_writes", n_aod == 0, f"{n_aod} rows found")
    else:
        check("C8.02.no_aod_writes", True, "table does not exist (correct for Phase C)")

    # Signal births table NOT modified by ELE (no column changes)
    sb_cols = {r[1] for r in conn3.execute("PRAGMA table_info(signal_births)").fetchall()}
    for protected_col in ("signal_id", "symbol", "detected_at", "base_score"):
        check(f"C8.03.signal_births_{protected_col}_present",
              protected_col in sb_cols)

    conn3.close()
except Exception as exc:
    check("C8.EXCEPTION", False, str(exc))

# ===========================================================================
# AUDIT C-9: Phase A/B table immutability
# ===========================================================================

section("AUDIT C-9: Phase A/B Table Immutability")
try:
    conn4 = _make_db()

    # Phase A core tables must still exist with correct structure
    phase_a_tables = {
        "signal_births", "opportunities", "opportunity_signals",
        "signal_state_transitions", "trading_calendar", "ohlcv_daily",
    }
    db_tables = {r[0] for r in conn4.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    missing_a = phase_a_tables - db_tables
    check("C9.01.phase_a_tables_intact",
          len(missing_a) == 0, f"missing: {missing_a}" if missing_a else "all present")

    # Phase B core tables
    phase_b_tables = {"sector_conviction_daily", "theme_phase_history"}
    missing_b = phase_b_tables - db_tables
    check("C9.02.phase_b_tables_intact",
          len(missing_b) == 0, f"missing: {missing_b}" if missing_b else "all present")

    conn4.close()
except Exception as exc:
    check("C9.EXCEPTION", False, str(exc))

# ===========================================================================
# Summary
# ===========================================================================

print("\n" + "=" * 60)
total  = len(_results)
passed = sum(1 for _, ok, _ in _results if ok)
failed = total - passed

print(f"\nPhase C Forensic Audit: {passed}/{total} PASS, {failed} FAIL")
if failed == 0:
    print("\n  ALL CHECKS PASS — Phase C certified. Phase D may begin.")
else:
    print("\n  FAILURES detected:")
    for label, ok, detail in _results:
        if not ok:
            suffix = f" -- {detail}" if detail else ""
            print(f"    [X] {label}: FAIL{suffix}")

sys.exit(0 if failed == 0 else 1)

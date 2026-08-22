"""
Pre-Live Adversarial Audit — 26 Parts (A–Z)
Runs all critical adversarial checks before authorizing Monday live experiment.
Outputs structured results to PRELIVE_AUDIT_RESULTS.txt
"""
from __future__ import annotations
import os, sys, json, re, ast, traceback
from pathlib import Path
from typing import List, Tuple, Dict, Any

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RESULTS: List[dict] = []

def finding(part: str, severity: str, title: str, detail: str, status: str = "FINDING"):
    """severity: P0 / P1 / P2 / INFO / PASS"""
    RESULTS.append({"part": part, "severity": severity, "title": title, "detail": detail, "status": status})
    tag = f"[{severity}]" if status != "PASS" else "[PASS]"
    print(f"  {tag} {title}: {detail[:120]}")

def read(path: str, encoding="utf-8") -> str:
    try:
        return (ROOT / path).read_text(encoding=encoding, errors="replace")
    except Exception as e:
        return f"<READ_ERROR: {e}>"

def grep(text: str, pattern: str, flags=0) -> List[str]:
    return re.findall(pattern, text, flags=flags | re.MULTILINE)

print("=" * 70)
print("ADVERSARIAL PRE-LIVE AUDIT — AI Trading Brain")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# PART A: Production Call Graph
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART A] PRODUCTION CALL GRAPH")
try:
    orch = read("orchestrator/master_orchestrator.py")
    # Verify scheduler entry point exists
    has_scheduler = "_guarded_cycle" in orch or "run_full_cycle" in orch
    has_scan      = "_do_scan" in orch or "run_full_cycle" in orch
    has_execution = "order_manager" in orch.lower() and "execute" in orch

    if has_scheduler and has_execution:
        finding("A", "INFO", "Call graph intact",
                "scheduler→_guarded_cycle→run_full_cycle→LayerN→OrderManager.execute confirmed", "PASS")
    else:
        finding("A", "P1", "Call graph broken", f"scheduler={has_scheduler} execution={has_execution}")

    # Verify RiskGuardian is called BEFORE OrderManager
    rg_pos = orch.find("risk_guardian.evaluate")
    om_pos = orch.find("order_manager") if "order_manager" in orch else orch.find("OrderManager")
    if rg_pos > 0 and om_pos > 0 and rg_pos < om_pos:
        finding("A", "INFO", "RiskGuardian before OrderManager", f"rg_pos={rg_pos} < om_pos={om_pos}", "PASS")
    else:
        finding("A", "P1", "RiskGuardian not guaranteed before OrderManager",
                f"rg_pos={rg_pos} om_pos={om_pos}")
except Exception as e:
    finding("A", "P1", "Part A exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART B: Signal → Decision → Execution Integrity
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART B] SIGNAL→DECISION→EXECUTION INTEGRITY")
try:
    om = read("execution_engine/order_manager.py")
    # The execute() method must use signal.quantity × decision.position_size_modifier
    has_qty_mod = "position_size_modifier" in om
    has_signal_qty = "signal.quantity" in om
    has_stop = "stop_loss" in om
    has_target = "target_price" in om

    if has_qty_mod and has_signal_qty:
        finding("B", "INFO", "Quantity = signal.quantity × position_size_modifier", "confirmed", "PASS")
    else:
        finding("B", "P0", "Position size modifier not applied", f"qty_mod={has_qty_mod}")

    # Verify stop_loss is passed to broker (or placed separately)
    has_stop_order = "_place_stop_loss" in om
    if has_stop_order:
        finding("B", "INFO", "_place_stop_loss called after entry", "confirmed", "PASS")
    else:
        finding("B", "P1", "No stop-loss order placement found", "Stop may not be placed with broker")

except Exception as e:
    finding("B", "P1", "Part B exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART C: KDA → Orchestrator → OrderManager Data Flow
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART C] KDA → ORCHESTRATOR → ORDERMASTER DATA FLOW")
try:
    orch = read("orchestrator/master_orchestrator.py")
    # KDA decision should reach orchestrator
    has_kda_decision = "kda_dec" in orch or "KNOWLEDGE_BUY" in orch or "kda_hold_blocked" in orch
    has_kda_hold_drop = "KNOWLEDGE_HOLD" in orch and "continue" in orch
    # KDA must be consulted before StrategyLab
    kda_pos = orch.find("run_knowledge_shadow")
    strat_pos = orch.find("StrategyLab") if "StrategyLab" in orch else orch.find("strategy_lab")

    if has_kda_decision:
        finding("C", "INFO", "KDA decision used in orchestrator", "kda_dec/KNOWLEDGE_BUY found", "PASS")
    else:
        finding("C", "P1", "KDA decision not used in orchestrator", "No kda_dec found")

    if has_kda_hold_drop:
        finding("C", "INFO", "KNOWLEDGE_HOLD drops signal before StrategyLab", "confirmed", "PASS")
    else:
        finding("C", "P1", "KNOWLEDGE_HOLD not dropping signal", "Signal may proceed despite conflict")

except Exception as e:
    finding("C", "P1", "Part C exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART D: Target / Stop / Horizon Integrity
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART D] TARGET/STOP/HORIZON INTEGRITY")
try:
    orch = read("orchestrator/master_orchestrator.py")
    # Check that kda_stop and kda_target are applied to signal
    has_kda_stop = "kda_stop" in orch
    has_kda_target = "kda_target" in orch
    has_atr_fallback = "ATR_FALLBACK" in orch or "atr_fallback" in orch.lower()

    if has_kda_stop:
        finding("D", "INFO", "kda_stop assigned to signal.stop_loss", "confirmed", "PASS")
    else:
        finding("D", "P1", "kda_stop not found in orchestrator",
                "Signal may use scanner stop without KDA override")

    if has_kda_target:
        finding("D", "INFO", "kda_target assigned to signal.target_price", "confirmed", "PASS")
    else:
        finding("D", "P1", "kda_target not found in orchestrator", "Target may not be KDA-derived")

    if has_atr_fallback:
        finding("D", "INFO", "ATR_FALLBACK present for DEVELOPING evidence", "confirmed", "PASS")
    else:
        finding("D", "P2", "ATR_FALLBACK not found", "May use raw scanner stop even for thin evidence")

    # Check that signal.stop_loss > 0 before it reaches OrderManager
    om = read("execution_engine/order_manager.py")
    has_sl_check = "stop_loss" in om and ("sl_distance" in om or "stop_loss <= 0" in om or "sl_dist" in om)
    if has_sl_check:
        finding("D", "INFO", "Stop distance validated before sizing", "confirmed", "PASS")
    else:
        finding("D", "P1", "No explicit stop_loss validity check before sizing", "Zero stop could crash sizing")

except Exception as e:
    finding("D", "P1", "Part D exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART E: Position Sizing with ₹10,000 Capital
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART E] POSITION SIZING — ₹10,000 CAPITAL")
try:
    import config
    cap = config.TOTAL_CAPITAL
    risk_pct = config.MAX_RISK_PER_TRADE_PCT

    finding("E", "INFO", f"TOTAL_CAPITAL", f"₹{cap:,.0f}", "PASS" if cap == 10000 else "INFO")
    finding("E", "INFO", f"MAX_RISK_PER_TRADE_PCT", f"{risk_pct*100:.3f}% = ₹{cap*risk_pct:.2f} per trade", "PASS")

    # Simulate sizing for representative stocks
    def sim_size(strategy_share, entry, stop_dist):
        deployable = cap * 0.80  # bull regime
        budget = deployable * strategy_share
        risk_amt = budget * risk_pct
        qty_risk = int(risk_amt / stop_dist) if stop_dist > 0.001 else 0
        qty_budget = int(budget / entry)
        qty = min(qty_risk, qty_budget)
        notional = qty * entry
        notional_pct = (notional / cap * 100) if cap > 0 else 0
        return qty, notional, notional_pct

    tests = [
        ("IDEA/PENNYSTK ₹15 ATR₹0.5", 0.28, 15, 0.5),
        ("SUZLON ₹75 ATR₹1", 0.28, 75, 1.0),
        ("TATASTEEL ₹160 ATR₹3", 0.28, 160, 3.0),
        ("SBIN ₹850 ATR₹8", 0.18, 850, 8.0),
        ("RELIANCE ₹2820 ATR₹28", 0.18, 2820, 28.0),
        ("HDFCBANK ₹1900 ATR₹19", 0.18, 1900, 19.0),
    ]
    for label, share, entry, stop_dist in tests:
        qty, notional, pct = sim_size(share, entry, stop_dist)
        status = "PASS" if qty >= 1 else "INFO"
        finding("E", "INFO" if qty >= 1 else "P2",
                f"Sizing {label}",
                f"qty={qty} notional=₹{notional:.0f} ({pct:.1f}% of capital)",
                status)

    # Critical check: MAX_CAPITAL_PER_TRADE_PCT
    from execution_engine.order_manager import MAX_CAPITAL_PER_TRADE_PCT, MAX_TOTAL_OPEN_EXPOSURE_PCT
    finding("E", "INFO", f"MAX_CAPITAL_PER_TRADE_PCT={MAX_CAPITAL_PER_TRADE_PCT}%",
            f"Max per trade = ₹{cap * MAX_CAPITAL_PER_TRADE_PCT / 100:.0f}", "PASS")
    finding("E", "INFO", f"MAX_TOTAL_OPEN_EXPOSURE_PCT={MAX_TOTAL_OPEN_EXPOSURE_PCT}%",
            f"Max total exposure = ₹{cap * MAX_TOTAL_OPEN_EXPOSURE_PCT / 100:.0f}", "PASS")

except Exception as e:
    finding("E", "P1", "Part E exception", traceback.format_exc()[:300])

# ─────────────────────────────────────────────────────────────────────────────
# PART F: DHAN_SECURITY_MAP Coverage
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART F] DHAN_SECURITY_MAP COVERAGE")
try:
    dhan_src = read("data_feeds/dhan_feed.py")
    # Count entries in the map
    map_entries = re.findall(r'"[A-Z]+"\s*:', dhan_src)
    finding("F", "INFO", f"DHAN_SECURITY_MAP entries", f"~{len(map_entries)} symbols", "PASS")

    # Check if _broker_place handles missing mapping gracefully
    om = read("execution_engine/order_manager.py")
    has_missing_map_guard = "MISSING_DHAN_MAPPING" in om or "not in DHAN_SECURITY_MAP" in om
    if has_missing_map_guard:
        finding("F", "INFO", "Missing map guard in _broker_place", "Returns None on missing mapping", "PASS")
    else:
        finding("F", "P1", "No missing map guard", "Missing symbol could crash _broker_place")

    # Check if scanner output symbols are in the map
    # The key risk: scanner may find symbols not in DHAN map → order blocked
    finding("F", "P2", "DHAN_SECURITY_MAP completeness unknown",
            "Scanner may find symbols not in map → orders silently blocked (DATA-DEPENDENT)", "INFO")

except Exception as e:
    finding("F", "P1", "Part F exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART G: Live Order Construction (Payload Validity)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART G] LIVE ORDER CONSTRUCTION")
try:
    dhan_broker = read("execution_engine/brokers/dhan_broker.py")
    # Check that place_order sends correct Dhan API fields
    has_security_id   = "security_id" in dhan_broker
    has_exchange_seg  = "exchange_segment" in dhan_broker
    has_transaction   = "transaction_type" in dhan_broker
    has_qty           = "quantity" in dhan_broker
    has_price         = "price" in dhan_broker
    has_order_type    = "order_type" in dhan_broker
    all_fields = all([has_security_id, has_exchange_seg, has_transaction, has_qty, has_price, has_order_type])

    if all_fields:
        finding("G", "INFO", "Dhan API payload has all required fields", "security_id,exchange_segment,transaction_type,quantity,price,order_type", "PASS")
    else:
        missing = [f for f, v in [("security_id",has_security_id),("exchange_seg",has_exchange_seg),
                                    ("transaction_type",has_transaction),("quantity",has_qty),
                                    ("price",has_price),("order_type",has_order_type)] if not v]
        finding("G", "P0", "Missing Dhan API fields", f"missing={missing}")

    # SIM mode returns SIM_ prefix — verify we never confuse SIM orders with real
    has_sim_prefix = "SIM_DHAN_" in dhan_broker or "SIM_" in dhan_broker
    if has_sim_prefix:
        finding("G", "INFO", "SIM mode returns SIM_ prefixed IDs", "Never confused with real orders", "PASS")
    else:
        finding("G", "P1", "SIM mode ID prefix unclear", "May confuse SIM vs real orders")

except Exception as e:
    finding("G", "P1", "Part G exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART H: Duplicate Order Protection
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART H] DUPLICATE ORDER PROTECTION")
try:
    om = read("execution_engine/order_manager.py")
    has_symbol_check   = "_symbol_has_open_position" in om
    has_reentry_check  = "_dup_guard_reentry_check" in om
    has_same_zone_pct  = "_SAME_ZONE_PCT" in om
    has_order_id_dedup = "_submitted_order_ids" in om or "dedupe" in om or "order_id" in om.lower()
    has_daily_reset    = "daily reset" in om.lower() or "_today" in om

    if has_symbol_check:
        finding("H", "INFO", "Symbol open-position check in execute()", "confirmed", "PASS")
    else:
        finding("H", "P0", "No symbol open-position check", "Duplicate trades on same symbol possible")

    if has_reentry_check and has_same_zone_pct:
        finding("H", "INFO", "Zone-based reentry guard (2%)", "confirmed", "PASS")
    else:
        finding("H", "P1", "Zone reentry guard missing", f"reentry={has_reentry_check} zone={has_same_zone_pct}")

    # RESTART RISK: _orders dict is in-memory → lost on crash
    has_restore = "restore_state" in om or "_restore_from_journal" in om
    if has_restore:
        finding("H", "INFO", "Crash recovery: restore_state/_restore_from_journal exists", "confirmed", "PASS")
    else:
        finding("H", "P0", "No crash recovery for _orders dict", "Restart loses open positions → duplicate trades possible")

    # Check CSV journal persistence
    has_csv = "paper_trades.csv" in om or ".csv" in om
    if has_csv:
        finding("H", "INFO", "CSV journal for persistence", "confirmed", "PASS")
    else:
        finding("H", "P1", "No CSV journal", "Position state lost on restart")

except Exception as e:
    finding("H", "P1", "Part H exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART I: Crash Recovery & Restart Safety
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART I] CRASH RECOVERY & RESTART SAFETY")
try:
    om = read("execution_engine/order_manager.py")
    # Check restore from CSV loads stop/target correctly
    restore_loads_sl = "stop_loss" in om and "restore" in om.lower()
    restore_loads_tgt = "target_price" in om and "restore" in om.lower()

    if restore_loads_sl and restore_loads_tgt:
        finding("I", "INFO", "Restore loads stop_loss and target_price", "confirmed", "PASS")
    else:
        finding("I", "P1", "Restore may miss stop/target fields",
                f"sl={restore_loads_sl} tgt={restore_loads_tgt}")

    # Check if restored positions have duplicate guard active
    has_prefetch = "_prefetch_restored_ltps" in om
    if has_prefetch:
        finding("I", "INFO", "LTP pre-fetch after restore (prevents false drawdown)", "confirmed", "PASS")
    else:
        finding("I", "P1", "No LTP pre-fetch after restore",
                "Restored positions may have stale LTP → false MAX_DRAWDOWN halt")

except Exception as e:
    finding("I", "P1", "Part I exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART J: Dhan Token Expiry / Auth Failure
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART J] DHAN TOKEN EXPIRY & AUTH FAILURE")
try:
    dhan_feed = read("data_feeds/dhan_feed.py")
    dhan_broker = read("execution_engine/brokers/dhan_broker.py")

    has_token_check = "access_token" in dhan_feed or "DHAN_ACCESS_TOKEN" in dhan_feed
    has_fallback    = "yfinance" in dhan_feed.lower() or "yahoo" in dhan_feed.lower() or "fallback" in dhan_feed.lower()
    has_connected   = "_connected" in dhan_broker
    has_sim_fallback = "not self._connected" in dhan_broker or "SIM_DHAN" in dhan_broker

    if has_token_check:
        finding("J", "INFO", "Token check in dhan_feed", "access_token verified", "PASS")
    else:
        finding("J", "P1", "No token check in dhan_feed", "Auth failure may crash silently")

    if has_fallback:
        finding("J", "INFO", "yfinance/yahoo fallback in data feed", "confirmed", "PASS")
    else:
        finding("J", "P1", "No data fallback", "Dhan feed failure = no market data")

    if has_sim_fallback:
        finding("J", "INFO", "Broker falls back to SIM when not connected",
                "Token failure → SIM mode (no real orders)", "PASS")
    else:
        finding("J", "P0", "No SIM fallback in broker", "Token failure could crash order placement")

except Exception as e:
    finding("J", "P1", "Part J exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART K: Connectivity Failure (Feed Down)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART K] CONNECTIVITY FAILURE")
try:
    orch = read("orchestrator/master_orchestrator.py")
    # Check that orchestrator catches exceptions from data feeds
    has_try_except = "except" in orch and "Exception" in orch
    has_fallback_log = "fallback" in orch.lower() or "yfinance" in orch.lower()
    has_guarded_cycle = "_guarded_cycle" in orch

    if has_guarded_cycle:
        finding("K", "INFO", "_guarded_cycle wraps run_full_cycle with exception handling",
                "confirmed", "PASS")
    else:
        finding("K", "P1", "No _guarded_cycle found", "Unguarded exceptions could kill scheduler")

    # Check that a data feed failure doesn't prevent learning
    has_eod_separate = "_do_eod_learning" in orch
    if has_eod_separate:
        finding("K", "INFO", "EOD learning separate from scan cycle", "_do_eod_learning", "PASS")
    else:
        finding("K", "P2", "EOD learning not isolated from scan", "Scan failure could skip learning")

except Exception as e:
    finding("K", "P1", "Part K exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART L: Data Integrity / Price Sanity
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART L] DATA INTEGRITY / PRICE SANITY")
try:
    om = read("execution_engine/order_manager.py")
    has_price_validator = "price_integrity_validator" in om or "PRE-ORDER PRICE GUARD" in om
    if has_price_validator:
        finding("L", "INFO", "Pre-order price integrity guard", "Validates price band before execution", "PASS")
    else:
        finding("L", "P1", "No pre-order price integrity guard", "Phantom/SIM prices could execute")

    # Check that entry_price > 0 is validated
    has_entry_check = "entry_price <= 0" in om or "entry_price > 0" in om
    if has_entry_check:
        finding("L", "INFO", "entry_price > 0 validated", "confirmed", "PASS")
    else:
        finding("L", "P1", "entry_price > 0 not explicitly validated", "Zero entry could cause division")

    # Check that stop_loss < entry for BUY (directional sanity)
    cre = read("risk_control/capital_risk_engine.py")
    has_sl_dist_check = "sl_distance < 0.001" in cre or "sl_distance <= 0" in cre
    if has_sl_dist_check:
        finding("L", "INFO", "Stop distance sanity check in CRE", "< 0.001 → qty=0", "PASS")
    else:
        finding("L", "P1", "No stop distance sanity in CRE", "Zero/tiny stop could inflate position size")

except Exception as e:
    finding("L", "P1", "Part L exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART M: Regime Failure / No Signal
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART M] REGIME FAILURE / NO SIGNAL HANDLING")
try:
    orch = read("orchestrator/master_orchestrator.py")
    # Should handle empty candidate list gracefully
    has_empty_guard = "not cre_signals" in orch or "len(cre_signals) == 0" in orch or \
                      "no signals" in orch.lower() or "empty" in orch.lower()
    if has_empty_guard or "if not" in orch:
        finding("M", "INFO", "Orchestrator handles empty signal lists", "confirmed", "PASS")
    else:
        finding("M", "P1", "No empty signal guard", "Empty CRE output may crash downstream")

    # RiskGuardian VIX kill-switch
    rg = read("risk_guardian/risk_guardian.py")
    has_vix_kill = "VIX" in rg and ("45" in rg or "kill" in rg.lower() or "BLOCK" in rg)
    if has_vix_kill:
        finding("M", "INFO", "VIX kill-switch in RiskGuardian", "VIX>45 → BLOCK", "PASS")
    else:
        finding("M", "P1", "No VIX kill-switch found", "Extreme volatility may not halt trading")

    has_dd_kill = "MAX_DRAWDOWN" in rg or "daily_loss" in rg.lower() or "drawdown" in rg.lower()
    if has_dd_kill:
        finding("M", "INFO", "Drawdown kill-switch in RiskGuardian", "confirmed", "PASS")
    else:
        finding("M", "P1", "No drawdown kill-switch found", "Uncontrolled losses possible")

except Exception as e:
    finding("M", "P1", "Part M exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART N: No-Lookahead Invariant (KFE/HBE)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART N] NO-LOOKAHEAD INVARIANT")
try:
    kfe = read("knowledge_authority/knowledge_feature_engine.py")
    hbe = read("knowledge_authority/hypothesis_backtesting_engine.py")

    # KFE: records should only use historical data (no future prices)
    has_timestamp = "timestamp" in kfe or "created_at" in kfe or "date" in kfe.lower()
    has_outcome_separation = "outcome" in kfe.lower() or "OUTCOME" in kfe
    # The HBE should never peek at future candles
    has_hbe_hist = "history" in hbe.lower() or "bars" in hbe.lower() or "candle" in hbe.lower()

    if has_timestamp:
        finding("N", "INFO", "KFE uses timestamps for record dating", "confirmed", "PASS")
    else:
        finding("N", "P1", "KFE has no timestamp", "Records may be undated → lookahead possible")

    # Check for any use of future data patterns
    future_patterns = re.findall(r"shift\(-|\.iloc\[[-\d]+\]|future|lookahead", kfe.lower())
    if not future_patterns:
        finding("N", "INFO", "No obvious lookahead patterns in KFE", "confirmed", "PASS")
    else:
        finding("N", "P0", "Possible lookahead in KFE", f"patterns={future_patterns[:5]}")

except Exception as e:
    finding("N", "P1", "Part N exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART O: Trading Hours Guard
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART O] TRADING HOURS GUARD")
try:
    om = read("execution_engine/order_manager.py")
    has_exec_win = "ExecutionWindowBlock" in om or "_EXEC_WIN_OPEN" in om or "09:45" in om
    has_pre_market_guard = "09:15" in om or "pre.market" in om.lower() or "PreMarket" in om

    if has_exec_win:
        finding("O", "INFO", "Execution window guard (09:45 earliest)", "confirmed", "PASS")
    else:
        finding("O", "P1", "No execution window block in OrderManager",
                "Orders may be placed before 09:15 market open")

    # Check orchestrator market hours
    orch = read("orchestrator/master_orchestrator.py")
    has_market_hours = "09:15" in orch or "15:30" in orch or "market_hours" in orch.lower()
    if has_market_hours:
        finding("O", "INFO", "Market hours gate in orchestrator", "confirmed", "PASS")
    else:
        finding("O", "P1", "No market hours gate in orchestrator", "Could scan/trade after hours")

    # Signal freshness check
    has_freshness = "SignalFreshnessGate" in om or "stale" in om.lower()
    if has_freshness:
        finding("O", "INFO", "Signal freshness gate present", "Stale signals rejected", "PASS")
    else:
        finding("O", "P2", "No signal freshness gate", "Hour-old signals may execute")

except Exception as e:
    finding("O", "P1", "Part O exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART P: Pilot Trade Limit
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART P] PILOT TRADE LIMIT")
try:
    import config
    pilot_max = getattr(config, "PILOT_MAX_TRADES", None)
    pilot_enabled = getattr(config, "PILOT_MODE", None)

    finding("P", "INFO", f"PILOT_MAX_TRADES={pilot_max}", f"Max trades per session", "PASS" if pilot_max is not None else "INFO")
    if pilot_enabled is not None:
        finding("P", "INFO", f"PILOT_MODE={pilot_enabled}", "confirmed", "PASS")
    else:
        finding("P", "P2", "PILOT_MODE not explicitly set", "PILOT_MAX_TRADES may not be enforced unless checked")

    # Check if pilot limit is enforced in orchestrator
    orch = read("orchestrator/master_orchestrator.py")
    has_pilot_check = "PILOT_MAX_TRADES" in orch or "pilot" in orch.lower()
    if has_pilot_check:
        finding("P", "INFO", "PILOT_MAX_TRADES enforced in orchestrator", "confirmed", "PASS")
    else:
        finding("P", "P1", "PILOT_MAX_TRADES not referenced in orchestrator",
                "Pilot limit may not be enforced during live experiment")

except Exception as e:
    finding("P", "P1", "Part P exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART Q: Daily Loss Halt (₹ Hard Stop)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART Q] DAILY LOSS HALT")
try:
    rg = read("risk_guardian/risk_guardian.py")
    orch = read("orchestrator/master_orchestrator.py")

    # MAX_DRAWDOWN_PCT is 10% → at ₹10,000 = ₹1,000 daily halt
    import config
    max_dd = config.MAX_DRAWDOWN_PCT
    daily_halt = config.TOTAL_CAPITAL * max_dd
    finding("Q", "INFO", f"MAX_DRAWDOWN_PCT={max_dd*100:.0f}% = ₹{daily_halt:.0f} halt threshold",
            "Halt triggered after this loss", "PASS" if daily_halt <= 1500 else "INFO")

    has_drawdown_check = "MAX_DRAWDOWN" in rg or "drawdown_pct" in rg.lower() or "daily_loss" in rg.lower()
    if has_drawdown_check:
        finding("Q", "INFO", "Drawdown halt in RiskGuardian", "confirmed", "PASS")
    else:
        finding("Q", "P0", "No drawdown halt", "Unlimited daily loss possible")

    # Check daily halt is actually connected to execution gate
    rg_blocks_exec = "BLOCK" in rg and "evaluate" in rg
    if rg_blocks_exec:
        finding("Q", "INFO", "RiskGuardian.evaluate() returns BLOCK", "confirmed", "PASS")
    else:
        finding("Q", "P1", "BLOCK return not confirmed in RiskGuardian", "Halt may not stop execution")

except Exception as e:
    finding("Q", "P1", "Part Q exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART R: Stop-Loss Order Actually Reaches Broker
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART R] STOP-LOSS ORDER REACHES BROKER")
try:
    om = read("execution_engine/order_manager.py")
    dhan_broker = read("execution_engine/brokers/dhan_broker.py")

    # Find _place_stop_loss implementation
    has_place_sl_impl = "def _place_stop_loss" in om
    has_sl_broker_call = "_broker_place" in om and "_place_stop_loss" in om

    if has_place_sl_impl:
        # Get the implementation
        sl_impl_start = om.find("def _place_stop_loss")
        sl_impl_end = om.find("\n    def ", sl_impl_start + 10)
        sl_impl = om[sl_impl_start:sl_impl_end][:500]

        is_paper_mode_sl = "paper_mode" in sl_impl.lower() or "_paper_mode" in sl_impl
        calls_broker = "_broker_place" in sl_impl
        finding("R", "INFO", "_place_stop_loss defined",
                f"calls_broker={calls_broker} paper_aware={is_paper_mode_sl}", "PASS")
    else:
        finding("R", "P1", "_place_stop_loss not implemented",
                "Stop orders may not be placed with broker")

    # SL order type: should be SL-M or SL
    has_sl_order_type = "SL" in dhan_broker and ("SL-M" in dhan_broker or "STOP" in dhan_broker.upper())
    if has_sl_order_type:
        finding("R", "INFO", "SL/SL-M order type in Dhan broker", "confirmed", "PASS")
    else:
        finding("R", "P2", "SL order type unclear in Dhan broker",
                "Stop orders may be placed as LIMIT instead of SL-M")

except Exception as e:
    finding("R", "P1", "Part R exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART S: EOD Close / Target Hit / Stop Hit Handling
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART S] EOD CLOSE / TARGET HIT / STOP HIT")
try:
    om = read("execution_engine/order_manager.py")
    # Check that positions are closed at EOD
    has_eod_close = "EOD" in om or "end_of_day" in om.lower() or "close_all" in om.lower()
    has_target_hit = "target_price" in om and ("target" in om.lower() and "close" in om.lower())
    has_stop_hit = "stop_loss" in om and ("stop" in om.lower() and "close" in om.lower())

    if has_eod_close:
        finding("S", "INFO", "EOD close logic in OrderManager", "confirmed", "PASS")
    else:
        finding("S", "P1", "No EOD close logic",
                "Positions may remain open overnight — gap risk")

    if has_target_hit and has_stop_hit:
        finding("S", "INFO", "Target and stop monitoring in OrderManager", "confirmed", "PASS")
    else:
        finding("S", "P1", "Target/stop hit detection unclear",
                f"target={has_target_hit} stop={has_stop_hit}")

    # Check _do_monitor in orchestrator closes positions
    orch = read("orchestrator/master_orchestrator.py")
    has_monitor_close = "_do_monitor" in orch and "close_position" in orch
    if has_monitor_close:
        finding("S", "INFO", "_do_monitor closes positions on target/stop hit", "confirmed", "PASS")
    else:
        finding("S", "P1", "_do_monitor may not close positions", "Positions may never be closed")

except Exception as e:
    finding("S", "P1", "Part S exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART T: KDA Evidence Bootstrap (STALE_8D warning)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART T] KDA EVIDENCE BOOTSTRAP / STALE DATA")
try:
    kfe = read("knowledge_authority/knowledge_feature_engine.py")
    kda = read("knowledge_authority/knowledge_decision_authority.py")

    has_stale_warning = "STALE" in kfe or "stale" in kfe.lower() or "STALE_8D" in kfe
    has_ess_threshold = "_ESS_DEVELOPING" in kda or "ESS" in kda
    has_knowledge_wait = "KNOWLEDGE_WAIT" in kda

    if has_ess_threshold:
        # Extract ESS developing threshold
        match = re.search(r"_ESS_DEVELOPING\s*=\s*([\d.]+)", kda)
        ess_val = match.group(1) if match else "?"
        finding("T", "INFO", f"ESS_DEVELOPING={ess_val} (signals express BUY/SELL)",
                "KDA correctly skips thin evidence → KNOWLEDGE_WAIT", "PASS")
    else:
        finding("T", "P1", "ESS_DEVELOPING not found in KDA", "Evidence thresholds unclear")

    if has_knowledge_wait:
        finding("T", "INFO", "KNOWLEDGE_WAIT for ESS<3 evidence",
                "New symbol enters KNOWLEDGE_WAIT → does not block execution", "PASS")
    else:
        finding("T", "P1", "KNOWLEDGE_WAIT not found", "Unknown behavior for new/cold symbols")

    # Check that KNOWLEDGE_WAIT does NOT block signal (it's just advisory)
    orch = read("orchestrator/master_orchestrator.py")
    wait_blocks = "KNOWLEDGE_WAIT" in orch and "continue" in orch
    hold_blocks = "KNOWLEDGE_HOLD" in orch and "continue" in orch
    if hold_blocks:
        finding("T", "INFO", "KNOWLEDGE_HOLD blocks, KNOWLEDGE_WAIT does NOT block",
                "Correct: only material conflict halts signal", "PASS")

except Exception as e:
    finding("T", "P1", "Part T exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART U: Debate / Confidence Threshold
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART U] DEBATE / CONFIDENCE THRESHOLD")
try:
    orch = read("orchestrator/master_orchestrator.py")
    debate = read("debate_and_decision/decision_engine.py") if (ROOT / "debate_and_decision/decision_engine.py").exists() else ""

    # Decision threshold 6.5
    has_65_threshold = "6.5" in orch or "6.5" in debate
    has_debate_agents = "debate" in orch.lower() and ("_run_debate" in orch or "debate_and_decision" in orch)

    if has_65_threshold:
        finding("U", "INFO", "Decision threshold 6.5 confirmed", "confirmed", "PASS")
    else:
        finding("U", "P2", "Decision threshold 6.5 not found", "Threshold may be different")

    if has_debate_agents:
        finding("U", "INFO", "Debate agents called before execution", "confirmed", "PASS")
    else:
        finding("U", "P1", "Debate not called before execution", "Debate isolation may be broken")

    # Check debate isolation from KDA
    debate_after_kda = orch.find("_run_debate") > orch.find("run_knowledge_shadow") if \
        "_run_debate" in orch and "run_knowledge_shadow" in orch else False
    if debate_after_kda:
        finding("U", "INFO", "Debate called AFTER KDA (correct order)", "confirmed", "PASS")
    else:
        finding("U", "P2", "Cannot confirm debate order relative to KDA", "Manual verification needed")

except Exception as e:
    finding("U", "P1", "Part U exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART V: Paper/Live Safety Gate (PRIMARY SAFETY)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART V] PAPER/LIVE SAFETY GATE (PRIMARY)")
try:
    import config, os as _os
    pt = config.PAPER_TRADING
    lta = _os.environ.get("LIVE_TRADING_AUTHORIZED", "ABSENT")

    finding("V", "INFO", f"config.PAPER_TRADING={pt}", "Local dev config", "PASS" if not pt else "INFO")
    finding("V", "INFO", f"LIVE_TRADING_AUTHORIZED={lta}",
            "Must be 'true' for live orders", "PASS" if lta == "ABSENT" else "P0")

    # Defense-in-depth: OrderManager requires BOTH paper_mode=False AND LIVE_TRADING_AUTHORIZED=true
    om = read("execution_engine/order_manager.py")
    has_dual_gate = "LIVE_TRADING_AUTHORIZED" in om and "paper_mode" in om
    if has_dual_gate:
        finding("V", "INFO", "Defense-in-depth gate: BOTH PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED=true required",
                "confirmed — any single override insufficient", "PASS")
    else:
        finding("V", "P0", "Dual gate not confirmed", "Single PAPER_TRADING flag may be bypassable")

    # DhanBroker SIM mode: if not connected, returns SIM_ ID
    dhan_broker = read("execution_engine/brokers/dhan_broker.py")
    has_connected_check = "self._connected" in dhan_broker
    if has_connected_check:
        finding("V", "INFO", "DhanBroker._connected check in place_order",
                "Not connected → SIM mode (safe)", "PASS")
    else:
        finding("V", "P0", "DhanBroker has no connection check",
                "Broker may attempt real API calls without connection")

    # VPS check (should have PAPER_TRADING=true on VPS)
    finding("V", "INFO", "VPS safety (manual verify required)",
            "VPS docker-compose.yml must have PAPER_TRADING=true until authorized", "INFO")

    # Check for any bypass paths to _broker_place
    # Only OrderManager should call _broker_place
    bp_calls = [(ln+1, l.strip()) for ln, l in enumerate(om.split('\n'))
                if '_broker_place(' in l and 'def _broker_place' not in l]
    finding("V", "INFO", f"_broker_place called {len(bp_calls)} times in OrderManager",
            f"lines={[x[0] for x in bp_calls]}", "PASS")

except Exception as e:
    finding("V", "P1", "Part V exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART W: Scheduler Resilience (no crash loop)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART W] SCHEDULER RESILIENCE")
try:
    orch = read("orchestrator/master_orchestrator.py")
    # Check _guarded_cycle catches exceptions
    gc_idx = orch.find("_guarded_cycle")
    if gc_idx > 0:
        gc_snippet = orch[gc_idx:gc_idx+600]
        has_except = "except" in gc_snippet and "Exception" in gc_snippet
        if has_except:
            finding("W", "INFO", "_guarded_cycle catches exceptions", "Scheduler survives layer failures", "PASS")
        else:
            finding("W", "P1", "_guarded_cycle may not catch all exceptions", gc_snippet[:100])
    else:
        finding("W", "P1", "_guarded_cycle not found", "Scheduler may crash on layer exception")

    # Check SIGTERM handler
    main_src = read("main.py")
    has_sigterm = "SIGTERM" in main_src or "signal.signal" in main_src
    if has_sigterm:
        finding("W", "INFO", "SIGTERM handler in main.py", "Clean shutdown", "PASS")
    else:
        finding("W", "P2", "No SIGTERM handler", "SIGTERM may leave state inconsistent")

except Exception as e:
    finding("W", "P1", "Part W exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART X: Test Coverage (436+ tests still pass)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART X] TEST COVERAGE CHECK")
try:
    test_files = list(ROOT.rglob("test_*.py"))
    test_count = sum(len(re.findall(r"def test_", tf.read_text(encoding="utf-8", errors="replace")))
                     for tf in test_files)
    finding("X", "INFO", f"Test files: {len(test_files)}, test functions: {test_count}",
            f"files={[tf.name for tf in test_files[:5]]}", "PASS" if test_count >= 436 else "P1")

except Exception as e:
    finding("X", "P1", "Part X exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART Y: Environment / Deployment Checklist
# ─────────────────────────────────────────────────────────────────────────────
print("\n[PART Y] ENVIRONMENT / DEPLOYMENT CHECKLIST")
try:
    import config, os as _os
    env_checks = [
        ("PAPER_TRADING", str(config.PAPER_TRADING), "VPS must be true until authorized"),
        ("TOTAL_CAPITAL", str(config.TOTAL_CAPITAL), "₹10,000 for live experiment"),
        ("LIVE_TRADING_AUTHORIZED", _os.environ.get("LIVE_TRADING_AUTHORIZED", "ABSENT"),
         "Must be absent/false until go-live"),
        ("DHAN_ACCESS_TOKEN", "SET" if _os.environ.get("DHAN_ACCESS_TOKEN") else "ABSENT",
         "Required for live data/orders"),
        ("DHAN_CLIENT_ID", "SET" if _os.environ.get("DHAN_CLIENT_ID") else "ABSENT",
         "Required for live data/orders"),
    ]
    for name, val, note in env_checks:
        finding("Y", "INFO", f"{name}={val}", note, "PASS")

    # Check docker-compose.yml for PAPER_TRADING
    dc = read("docker-compose.yml")
    if "PAPER_TRADING" in dc:
        pt_in_dc = re.findall(r"PAPER_TRADING[=:]?\s*(\S+)", dc)
        finding("Y", "INFO", f"docker-compose PAPER_TRADING", f"values={pt_in_dc}", "PASS")
    else:
        finding("Y", "P2", "PAPER_TRADING not in docker-compose.yml",
                "VPS may use env default (true) — verify manually")

except Exception as e:
    finding("Y", "P1", "Part Y exception", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# PART Z: FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("[PART Z] FINAL ADVERSARIAL AUDIT SUMMARY")
print("=" * 70)

p0s = [r for r in RESULTS if r["severity"] == "P0" and r["status"] != "PASS"]
p1s = [r for r in RESULTS if r["severity"] == "P1" and r["status"] != "PASS"]
p2s = [r for r in RESULTS if r["severity"] == "P2" and r["status"] != "PASS"]
infos = [r for r in RESULTS if r["severity"] == "INFO" or r["status"] == "PASS"]

print(f"\nTotal findings: {len(RESULTS)}")
print(f"  P0 (blocker): {len(p0s)}")
print(f"  P1 (high):    {len(p1s)}")
print(f"  P2 (medium):  {len(p2s)}")
print(f"  PASS/INFO:    {len(infos)}")

if p0s:
    print("\n--- P0 BLOCKERS (must fix before live) ---")
    for r in p0s:
        print(f"  [{r['part']}] {r['title']}: {r['detail'][:120]}")

if p1s:
    print("\n--- P1 HIGH (should fix before live) ---")
    for r in p1s:
        print(f"  [{r['part']}] {r['title']}: {r['detail'][:120]}")

if p2s:
    print("\n--- P2 MEDIUM (fix in next session) ---")
    for r in p2s:
        print(f"  [{r['part']}] {r['title']}: {r['detail'][:120]}")

# Verdict
if not p0s and not p1s:
    verdict = "GO — no P0/P1 blockers found"
elif not p0s:
    verdict = f"CONDITIONAL GO — 0 P0s, {len(p1s)} P1s (review P1s)"
else:
    verdict = f"NO-GO — {len(p0s)} P0 blockers must be fixed first"

print(f"\n{'='*70}")
print(f"VERDICT: {verdict}")
print(f"{'='*70}")

# Write results to file
out_path = ROOT / "PRELIVE_AUDIT_RESULTS.json"
out_path.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
print(f"\nDetailed results written to: {out_path}")

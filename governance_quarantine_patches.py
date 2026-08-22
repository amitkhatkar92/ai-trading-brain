"""
governance_quarantine_patches.py
Run INSIDE the Docker container: python3 /tmp/governance_quarantine_patches.py

REFINEMENT 1 — EARLY ENTRY GOVERNANCE
  order_manager.py: Replace observe-only [ExecutionWindowAudit] with blocking
  [ExecutionWindowBlock] that rejects pre-09:45 orders (returns None).

REFINEMENT 2 — CORPORATE ACTION QUARANTINE
  trade_monitor.py:      Set governance_state=CORPORATE_ACTION_REVIEW,
                         write to data/ca_quarantine.json,
                         emit [CorporateActionQuarantine].
  learning_engine.py:    Skip CORPORATE_ACTION_REVIEW trades from SHM / strategy
                         buckets.
  master_orchestrator.py: Load quarantine registry; skip from perf_tracker,
                           performance_evaluator, and meta_learning loops.
"""
import sys
import ast

PATCHES = []

# ─────────────────────────────────────────────────────────────────────────────
# REFINEMENT 1  —  ExecutionWindowBlock  (order_manager.py)
# ─────────────────────────────────────────────────────────────────────────────
PATCHES.append(dict(
    label="R1-exec-window-block",
    path="/app/execution_engine/order_manager.py",
    old='''\
            if _now < _exec_win_open:
                _mins_early = int((_exec_win_open - _now).total_seconds() / 60)
                import logging as _log_ewa
                _log_ewa.getLogger(__name__).warning(
                    "[ExecutionWindowAudit] symbol=%s strategy=%s "
                    "order_time=%s window_opens=09:45 minutes_early=%d "
                    "window_check=ABSENT_IN_EXECUTION_LAYER "
                    "root_cause=first_opportunity_scan_fires_run_full_cycle_no_early_guard "
                    "governance_check=LEARNING_LAYER_ONLY",
                    signal.symbol,
                    getattr(signal, 'strategy_name', '?'),
                    _now.strftime('%H:%M:%S'),
                    _mins_early,
                )
            # end ExecutionWindowAudit''',
    new='''\
            if _now < _exec_win_open:
                _mins_early = int((_exec_win_open - _now).total_seconds() / 60)
                _sched_src = getattr(signal, 'source', 'scheduler_slot')
                log.warning(
                    "[ExecutionWindowBlock] symbol=%s strategy=%s "
                    "attempt_time=%s allowed_window=09:45-14:30 "
                    "minutes_early=%d scheduler_source=%s "
                    "action=ORDER_REJECTED",
                    signal.symbol,
                    getattr(signal, 'strategy_name', '?'),
                    _now.strftime('%H:%M:%S'),
                    _mins_early,
                    _sched_src,
                )
                return None
            # end ExecutionWindowBlock''',
))

# ─────────────────────────────────────────────────────────────────────────────
# REFINEMENT 2a  —  CorporateActionQuarantine marker  (trade_monitor.py)
# ─────────────────────────────────────────────────────────────────────────────
PATCHES.append(dict(
    label="R2a-ca-quarantine-marker",
    path="/app/trade_monitoring/trade_monitor.py",
    old='''\
                        )
                        # end CorporateActionAudit
                        self._dg_update_stale(order.order_id, symbol, baseline)''',
    new='''\
                        )
                        # end CorporateActionAudit
                        # CorporateActionQuarantine: mark position and persist to registry
                        order.governance_state = "CORPORATE_ACTION_REVIEW"
                        _caq_oid = order.order_id if order else '?'
                        log.warning(
                            "[CorporateActionQuarantine] symbol=%s oid=%s "
                            "entry_price=%.2f market_price=%.2f deviation_pct=%.1f "
                            "reason=LTPGuard_price_freeze_no_independent_confirmation "
                            "learning_excluded=YES shm_excluded=YES winrate_excluded=YES "
                            "governance_state=CORPORATE_ACTION_REVIEW",
                            symbol, _caq_oid,
                            _ca_entry, candidate, deviation * 100,
                        )
                        try:
                            import os as _caq_os, json as _caq_json
                            _caq_path = _caq_os.path.join(
                                _caq_os.path.dirname(
                                    _caq_os.path.dirname(_caq_os.path.abspath(__file__))
                                ),
                                "data", "ca_quarantine.json",
                            )
                            _caq_data = {}
                            if _caq_os.path.exists(_caq_path):
                                with open(_caq_path, "r", encoding="utf-8") as _caq_r:
                                    _caq_data = _caq_json.load(_caq_r)
                            _caq_data[_caq_oid] = {
                                "symbol": symbol,
                                "reason": "LTPGuard_deviation",
                                "deviation_pct": round(deviation * 100, 1),
                                "timestamp": datetime.now().isoformat(),
                            }
                            with open(_caq_path, "w", encoding="utf-8") as _caq_w:
                                _caq_json.dump(_caq_data, _caq_w, indent=2)
                        except Exception as _caq_exc:
                            log.debug(
                                "[CorporateActionQuarantine] registry write failed: %s",
                                _caq_exc,
                            )
                        # end CorporateActionQuarantine
                        self._dg_update_stale(order.order_id, symbol, baseline)''',
))

# ─────────────────────────────────────────────────────────────────────────────
# REFINEMENT 2b  —  SHM / strategy-bucket skip  (learning_engine.py)
# ─────────────────────────────────────────────────────────────────────────────
PATCHES.append(dict(
    label="R2b-learning-engine-skip",
    path="/app/learning_system/learning_engine.py",
    old='''\
        for trade in closed_trades:
            pnl_pct = (
                trade.pnl / (trade.entry_price * trade.quantity)
                if trade.entry_price and trade.quantity else 0.0
            )
            strategy_buckets[trade.strategy].append(pnl_pct)''',
    new='''\
        for trade in closed_trades:
            # CorporateActionQuarantine: skip phantom-P&L positions from SHM / strategy stats
            if getattr(trade, 'governance_state', 'ACTIVE') == 'CORPORATE_ACTION_REVIEW':
                log.warning(
                    "[CorporateActionQuarantine] symbol=%s excluded from SHM/strategy-learning "
                    "— governance_state=CORPORATE_ACTION_REVIEW phantom_pnl_risk=YES",
                    getattr(trade, 'symbol', '?'),
                )
                continue
            pnl_pct = (
                trade.pnl / (trade.entry_price * trade.quantity)
                if trade.entry_price and trade.quantity else 0.0
            )
            strategy_buckets[trade.strategy].append(pnl_pct)''',
))

# ─────────────────────────────────────────────────────────────────────────────
# REFINEMENT 2c  —  EOD perf-tracker quarantine load + skip  (master_orchestrator.py)
# ─────────────────────────────────────────────────────────────────────────────
PATCHES.append(dict(
    label="R2c-orchestrator-perf-skip",
    path="/app/orchestrator/master_orchestrator.py",
    old='''\
        for trade in trades:
            # OrderRecord uses .strategy; fall back to .strategy_name for compat
            strategy   = getattr(trade, "strategy", None) or getattr(trade, "strategy_name", "unknown")
            regime     = getattr(trade, "signal_regime", None) or getattr(trade, "regime", "unknown")''',
    new='''\
        # CorporateActionQuarantine: load registry to exclude phantom-P&L positions
        _ca_quarantine_oids: set = set()
        try:
            import json as _caq_json
            _caq_path = "data/ca_quarantine.json"
            if os.path.exists(_caq_path):
                with open(_caq_path, "r", encoding="utf-8") as _caq_r:
                    _ca_quarantine_oids = set(_caq_json.load(_caq_r).keys())
                if _ca_quarantine_oids:
                    log.info(
                        "[CorporateActionQuarantine] registry loaded — %d quarantined oid(s): %s",
                        len(_ca_quarantine_oids), list(_ca_quarantine_oids),
                    )
        except Exception as _caq_exc:
            log.debug("[CorporateActionQuarantine] registry load failed: %s", _caq_exc)

        for trade in trades:
            # CorporateActionQuarantine: skip phantom-P&L positions from all EOD learning
            _t_oid = getattr(trade, 'order_id', '')
            _t_gov = getattr(trade, 'governance_state', 'ACTIVE')
            if _t_gov == 'CORPORATE_ACTION_REVIEW' or _t_oid in _ca_quarantine_oids:
                log.warning(
                    "[CorporateActionQuarantine] symbol=%s oid=%s excluded from "
                    "EOD perf/win-rate — phantom_pnl_risk=YES",
                    getattr(trade, 'symbol', '?'), _t_oid,
                )
                continue
            # OrderRecord uses .strategy; fall back to .strategy_name for compat
            strategy   = getattr(trade, "strategy", None) or getattr(trade, "strategy_name", "unknown")
            regime     = getattr(trade, "signal_regime", None) or getattr(trade, "regime", "unknown")''',
))

# ─────────────────────────────────────────────────────────────────────────────
# REFINEMENT 2d  —  meta-learning loop skip  (master_orchestrator.py)
# ─────────────────────────────────────────────────────────────────────────────
PATCHES.append(dict(
    label="R2d-orchestrator-metalearning-skip",
    path="/app/orchestrator/master_orchestrator.py",
    old='''\
        # ── Meta-Learning Feedback ─────────────────────────────────────
        log.info("── Layer 13: Meta-Learning Feedback ──")
        for trade in trades:
            self.meta_learning.record_result(
                strategy   = getattr(trade, "strategy", None) or getattr(trade, "strategy_name", "unknown"),
                snapshot   = None,    # uses cached last_snapshot
                r_multiple = getattr(trade, "r_multiple",    0.0),
                return_pct = getattr(trade, "pnl",           0.0) / 1_000_000 * 100,
                won        = getattr(trade, "pnl",           0.0) > 0,
            )''',
    new='''\
        # ── Meta-Learning Feedback ─────────────────────────────────────
        log.info("── Layer 13: Meta-Learning Feedback ──")
        for trade in trades:
            # CorporateActionQuarantine: skip phantom-P&L from meta-learning
            _t_oid_ml = getattr(trade, 'order_id', '')
            _t_gov_ml = getattr(trade, 'governance_state', 'ACTIVE')
            if _t_gov_ml == 'CORPORATE_ACTION_REVIEW' or _t_oid_ml in _ca_quarantine_oids:
                log.debug(
                    "[CorporateActionQuarantine] symbol=%s excluded from meta-learning",
                    getattr(trade, 'symbol', '?'),
                )
                continue
            self.meta_learning.record_result(
                strategy   = getattr(trade, "strategy", None) or getattr(trade, "strategy_name", "unknown"),
                snapshot   = None,    # uses cached last_snapshot
                r_multiple = getattr(trade, "r_multiple",    0.0),
                return_pct = getattr(trade, "pnl",           0.0) / 1_000_000 * 100,
                won        = getattr(trade, "pnl",           0.0) > 0,
            )''',
))

# ─────────────────────────────────────────────────────────────────────────────
# Apply patches
# ─────────────────────────────────────────────────────────────────────────────
results = {}

for p in PATCHES:
    label = p["label"]
    path  = p["path"]
    old   = p["old"]
    new   = p["new"]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        if old not in src:
            results[label] = "SKIP (already applied or old string not found)"
            continue
        count = src.count(old)
        if count > 1:
            results[label] = f"AMBIGUOUS — old string found {count} times"
            continue
        src2 = src.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src2)
        results[label] = "OK"
    except Exception as exc:
        results[label] = f"ERROR: {exc}"

# Syntax check all patched files
checked = {}
for path in set(p["path"] for p in PATCHES):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        ast.parse(src)
        checked[path] = "SYNTAX OK"
    except SyntaxError as se:
        checked[path] = f"SYNTAX ERROR: {se}"

# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=== REFINEMENT 1: ExecutionWindowBlock ===")
print(f"  {results.get('R1-exec-window-block', '?'):6s}  R1-exec-window-block")

print()
print("=== REFINEMENT 2: CorporateActionQuarantine ===")
for k in ("R2a-ca-quarantine-marker", "R2b-learning-engine-skip",
          "R2c-orchestrator-perf-skip", "R2d-orchestrator-metalearning-skip"):
    print(f"  {results.get(k, '?'):6s}  {k}")

print()
print("=== SYNTAX CHECKS ===")
for path, status in sorted(checked.items()):
    print(f"  {status}: {path}")

all_ok = all(v in ("OK", "SYNTAX OK") or v.startswith("SKIP")
             for v in list(results.values()) + list(checked.values()))
print()
print("=" * 60)
print("RESULT:", "ALL OK" if all_ok else "SOME FAILURES — review above")
sys.exit(0 if all_ok else 1)

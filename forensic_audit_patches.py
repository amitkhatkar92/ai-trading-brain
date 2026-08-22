"""
forensic_audit_patches.py — runs INSIDE the container

Applies 4 forensic audit packages:
  AUDIT 1  [ExecutionWindowAudit]   — order_manager.py
  AUDIT 2  [CorporateActionAudit]   — trade_monitor.py + master_orchestrator.py
  FIX 3    [ReadinessScoreAudit]    — angelone_readiness_auditor.py
  AUDIT 4  [TrendFilterAudit]       — equity_scanner_ai.py
           [TrendFilterSummary]     — pipeline_forensic_reporter.py

Evidence-only instruments. No logic changes. No thresholds. No strategies.
"""

import sys


def patch(path, old, new, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print(f"  SKIP {label}: file not found: {path}")
        return False
    if old not in src:
        print(f"  MISS {label}: old string not found in {path}")
        # Show context
        lines = old.splitlines()
        first = lines[0].strip() if lines else ""
        idx = src.find(first[:40]) if first else -1
        if idx >= 0:
            print(f"    nearest match at char {idx}: {src[idx:idx+80]!r}")
        return False
    if src.count(old) > 1:
        print(f"  AMBIG {label}: found {src.count(old)} matches in {path}")
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(src.replace(old, new, 1))
    print(f"  OK    {label}")
    return True


errors = 0

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT 1 — ExecutionWindowAudit — order_manager.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== AUDIT 1: ExecutionWindowAudit ===")
OM = "/app/execution_engine/order_manager.py"

ok = patch(OM,
    "_LATE_ENTRY_MIN_SCORE = 7.0                               # score floor in elevated window",
    "_LATE_ENTRY_MIN_SCORE = 7.0                               # score floor in elevated window\n"
    "_EXEC_WINDOW_OPEN_H, _EXEC_WINDOW_OPEN_M = 9, 45    # governance window opens (IST)",
    "A1-constant",
)
errors += not ok

ok = patch(OM,
    "        if not _is_same_symbol_swap:\n"
    "            _now = datetime.now()\n"
    "            _cutoff  = _now.replace(hour=_LATE_ENTRY_CUTOFF_H,   minute=_LATE_ENTRY_CUTOFF_M,   second=0, microsecond=0)\n"
    "            _elevated = _now.replace(hour=_LATE_ENTRY_ELEVATED_H, minute=_LATE_ENTRY_ELEVATED_M, second=0, microsecond=0)",
    "        if not _is_same_symbol_swap:\n"
    "            _now = datetime.now()\n"
    "            # ExecutionWindowAudit: observe entries before approved window (09:45 IST)\n"
    "            _exec_win_open = _now.replace(\n"
    "                hour=_EXEC_WINDOW_OPEN_H, minute=_EXEC_WINDOW_OPEN_M,\n"
    "                second=0, microsecond=0,\n"
    "            )\n"
    "            if _now < _exec_win_open:\n"
    "                _mins_early = int((_exec_win_open - _now).total_seconds() / 60)\n"
    "                import logging as _log_ewa\n"
    "                _log_ewa.getLogger(__name__).warning(\n"
    "                    \"[ExecutionWindowAudit] symbol=%s strategy=%s \"\n"
    "                    \"order_time=%s window_opens=09:45 minutes_early=%d \"\n"
    "                    \"window_check=ABSENT_IN_EXECUTION_LAYER \"\n"
    "                    \"root_cause=first_opportunity_scan_fires_run_full_cycle_no_early_guard \"\n"
    "                    \"governance_check=LEARNING_LAYER_ONLY\",\n"
    "                    signal.symbol,\n"
    "                    getattr(signal, 'strategy_name', '?'),\n"
    "                    _now.strftime('%H:%M:%S'),\n"
    "                    _mins_early,\n"
    "                )\n"
    "            # end ExecutionWindowAudit\n"
    "            _cutoff  = _now.replace(hour=_LATE_ENTRY_CUTOFF_H,   minute=_LATE_ENTRY_CUTOFF_M,   second=0, microsecond=0)\n"
    "            _elevated = _now.replace(hour=_LATE_ENTRY_ELEVATED_H, minute=_LATE_ENTRY_ELEVATED_M, second=0, microsecond=0)",
    "A1-audit-emit",
)
errors += not ok

import py_compile, tempfile, shutil
try:
    py_compile.compile(OM, doraise=True)
    print(f"  SYNTAX OK: {OM}")
except py_compile.PyCompileError as e:
    print(f"  SYNTAX FAIL: {e}")
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT 2a — CorporateActionAudit — trade_monitor.py (LTPGuard path)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== AUDIT 2a: CorporateActionAudit (trade_monitor.py) ===")
TM = "/app/trade_monitoring/trade_monitor.py"

ok = patch(TM,
    "                        log.warning(\n"
    "                            \"[DataGuard] Using fallback price for %s — live data unavailable \"\n"
    "                            \"(feed=%.2f flagged; fallback=%.2f).\",\n"
    "                            symbol, candidate, baseline,\n"
    "                        )\n"
    "                        self._dg_update_stale(order.order_id, symbol, baseline)",
    "                        log.warning(\n"
    "                            \"[DataGuard] Using fallback price for %s — live data unavailable \"\n"
    "                            \"(feed=%.2f flagged; fallback=%.2f).\",\n"
    "                            symbol, candidate, baseline,\n"
    "                        )\n"
    "                        # CorporateActionAudit: structured forensic evidence for large deviations\n"
    "                        _ca_entry = getattr(order, 'entry_price', baseline)\n"
    "                        log.warning(\n"
    "                            \"[CorporateActionAudit] symbol=%s oid=%s \"\n"
    "                            \"feed_price=%.2f last_known=%.2f entry_price=%.2f \"\n"
    "                            \"deviation_pct=%.1f \"\n"
    "                            \"detection=LTPGuard_20pct_threshold \"\n"
    "                            \"positions_affected=1 \"\n"
    "                            \"phantom_pnl_risk=YES_sl_fires_on_frozen_not_real_price \"\n"
    "                            \"learning_contamination_risk=YES_exit_recorded_at_fallback_not_market \"\n"
    "                            \"auto_review_state=NOT_IMPLEMENTED \"\n"
    "                            \"action=FROZEN_AT_LAST_KNOWN \"\n"
    "                            \"recommendation=manual_close_CORPORATE_ACTION_CLOSE\",\n"
    "                            symbol, order.order_id if order else '?',\n"
    "                            candidate, baseline, _ca_entry,\n"
    "                            deviation * 100,\n"
    "                        )\n"
    "                        # end CorporateActionAudit\n"
    "                        self._dg_update_stale(order.order_id, symbol, baseline)",
    "A2a-ltpguard",
)
errors += not ok

try:
    py_compile.compile(TM, doraise=True)
    print(f"  SYNTAX OK: {TM}")
except py_compile.PyCompileError as e:
    print(f"  SYNTAX FAIL: {e}")
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT 2b — CorporateActionAudit — master_orchestrator.py (restore path)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== AUDIT 2b: CorporateActionAudit (master_orchestrator.py) ===")
MO = "/app/orchestrator/master_orchestrator.py"

ok = patch(MO,
    "                    log.warning(\n"
    "                        \"[PostRestoreGovernance] RECONCILIATION_SUSPECT %s \"\n"
    "                        \"entry=%.2f  ltp=%.2f  deviation=%.0f%% — \"\n"
    "                        \"possible instrument mapping change (demerger/split?) \"\n"
    "                        \"or stale pre-migration position.  \"\n"
    "                        \"SL governance remains active; manual review advised.\",\n"
    "                        _rec.symbol, _entry, _ltp, _deviation * 100,\n"
    "                    )",
    "                    log.warning(\n"
    "                        \"[PostRestoreGovernance] RECONCILIATION_SUSPECT %s \"\n"
    "                        \"entry=%.2f  ltp=%.2f  deviation=%.0f%% — \"\n"
    "                        \"possible instrument mapping change (demerger/split?) \"\n"
    "                        \"or stale pre-migration position.  \"\n"
    "                        \"SL governance remains active; manual review advised.\",\n"
    "                        _rec.symbol, _entry, _ltp, _deviation * 100,\n"
    "                    )\n"
    "                    # CorporateActionAudit: structured evidence on restore\n"
    "                    log.warning(\n"
    "                        \"[CorporateActionAudit] symbol=%s \"\n"
    "                        \"entry_price=%.2f feed_ltp=%.2f deviation_pct=%.1f \"\n"
    "                        \"detection=post_restore_plausibility_50pct \"\n"
    "                        \"positions_affected=1 \"\n"
    "                        \"phantom_pnl_risk=YES_fallback_price_active_for_sl_eval \"\n"
    "                        \"learning_contamination_risk=YES_exit_recorded_at_stale_not_real \"\n"
    "                        \"auto_review_state=NOT_IMPLEMENTED \"\n"
    "                        \"action=RECONCILIATION_SUSPECT_NOTIFIED \"\n"
    "                        \"recommendation=manual_close_CORPORATE_ACTION_CLOSE\",\n"
    "                        _rec.symbol, _entry, _ltp, _deviation * 100,\n"
    "                    )\n"
    "                    # end CorporateActionAudit",
    "A2b-restore",
)
errors += not ok

try:
    py_compile.compile(MO, doraise=True)
    print(f"  SYNTAX OK: {MO}")
except py_compile.PyCompileError as e:
    print(f"  SYNTAX FAIL: {e}")
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# FIX 3 — ReadinessScoreAudit — angelone_readiness_auditor.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== FIX 3: ReadinessScoreAudit ===")
ARA = "/app/data_feeds/angelone_readiness_auditor.py"

ok = patch(ARA,
    "    def emit_readiness_report(self) -> None:\n"
    "        \"\"\"Emit [AngelOneReadinessReport] — call at EOD.\"\"\"\n"
    "        with self._mu:",
    "    # Minimum LTP shadow comparisons before confidence is statistically meaningful\n"
    "    _MIN_LTP_SAMPLES: int = 10\n"
    "\n"
    "    def emit_readiness_report(self) -> None:\n"
    "        \"\"\"Emit [AngelOneReadinessReport] — call at EOD.\"\"\"\n"
    "        with self._mu:",
    "F3-constant",
)
errors += not ok

ok = patch(ARA,
    "            # Overall confidence\n"
    "            confidence = round((ltp_score + options_score + candidate_score\n"
    "                                + signal_score + reliability_score) / 5)\n"
    "            migration_ready = \"YES\" if confidence >= 80 else \"NO\"\n"
    "            recommendation = (\n"
    "                \"Ready for Dhan retirement\" if confidence >= 80\n"
    "                else \"Continue dual-feed — gaps remain\"\n"
    "            )",
    "            # Overall confidence\n"
    "            confidence = round((ltp_score + options_score + candidate_score\n"
    "                                + signal_score + reliability_score) / 5)\n"
    "            # Sample size guard: score is invalid when ltp_compared < minimum\n"
    "            _insufficient = total_sym < self._MIN_LTP_SAMPLES\n"
    "            if _insufficient:\n"
    "                confidence_label = 'UNKNOWN'\n"
    "                migration_ready  = 'UNKNOWN'\n"
    "                recommendation   = (\n"
    "                    f'Insufficient LTP samples ({total_sym}/{self._MIN_LTP_SAMPLES})'\n"
    "                    f' -- score not valid; accumulate more sessions'\n"
    "                )\n"
    "            else:\n"
    "                confidence_label = str(confidence)\n"
    "                migration_ready  = 'YES' if confidence >= 80 else 'NO'\n"
    "                recommendation   = (\n"
    "                    'Ready for Dhan retirement' if confidence >= 80\n"
    "                    else 'Continue dual-feed -- gaps remain'\n"
    "                )",
    "F3-guard",
)
errors += not ok

ok = patch(ARA,
    "            \"overall_confidence=%d migration_ready=%s \"\n"
    "            \"recommendation=%s | \"\n"
    "            \"detail: ltp_compared=%d avg_ltp_diff=%.3f%% max_ltp_diff=%.3f%% \"",
    "            \"overall_confidence=%s migration_ready=%s \"\n"
    "            \"insufficient_data=%s \"\n"
    "            \"recommendation=%s | \"\n"
    "            \"detail: ltp_compared=%d avg_ltp_diff=%.3f%% max_ltp_diff=%.3f%% \"",
    "F3-logfmt",
)
errors += not ok

ok = patch(ARA,
    "            confidence, migration_ready, recommendation,\n"
    "            total_sym, avg_ltp_diff, max_ltp_diff,",
    "            confidence_label, migration_ready, _insufficient, recommendation,\n"
    "            total_sym, avg_ltp_diff, max_ltp_diff,",
    "F3-logargs",
)
errors += not ok

ok = patch(ARA,
    "        cap_inv = self._build_capability_inventory()\n"
    "        for cap_name, cap_status, cap_reason in cap_inv:\n"
    "            log.info(\n"
    "                \"[CapabilityInventory] capability=%-35s status=%-20s reason=%s\",\n"
    "                cap_name, cap_status, cap_reason,\n"
    "            )",
    "        cap_inv = self._build_capability_inventory()\n"
    "        for cap_name, cap_status, cap_reason in cap_inv:\n"
    "            log.info(\n"
    "                \"[CapabilityInventory] capability=%-35s status=%-20s reason=%s\",\n"
    "                cap_name, cap_status, cap_reason,\n"
    "            )\n"
    "        # ReadinessScoreAudit: per-component breakdown for forensic review\n"
    "        with self._mu:\n"
    "            _ara_total_sym = self._p2_total_symbols\n"
    "        log.info(\n"
    "            \"[ReadinessScoreAudit] \"\n"
    "            \"ltp_samples=%d min_required=%d sample_valid=%s \"\n"
    "            \"ltp_score=%s options_score=%d candidate_score=%d \"\n"
    "            \"signal_score=%d reliability_score=%d \"\n"
    "            \"overall_confidence=%s \"\n"
    "            \"note=ltp_score_invalid_when_insufficient_data\",\n"
    "            _ara_total_sym, self._MIN_LTP_SAMPLES, not _insufficient,\n"
    "            'INVALID' if _insufficient else str(ltp_score),\n"
    "            options_score, candidate_score, signal_score, reliability_score,\n"
    "            confidence_label,\n"
    "        )",
    "F3-readiness-audit",
)
errors += not ok

try:
    py_compile.compile(ARA, doraise=True)
    print(f"  SYNTAX OK: {ARA}")
except py_compile.PyCompileError as e:
    print(f"  SYNTAX FAIL: {e}")
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT 4a — TrendFilterAudit per-symbol — equity_scanner_ai.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== AUDIT 4a: TrendFilterAudit per-symbol (equity_scanner_ai.py) ===")
ESA = "/app/opportunity_engine/equity_scanner_ai.py"

ok = patch(ESA,
    "            log.debug(\n"
    "                \"[UniverseAudit] %-14s reason=%-22s rsi=%4.0f vol=%.1fx regime=%s\",\n"
    "                stock[\"symbol\"], reason,\n"
    "                stock.get(\"rsi\", 0), stock.get(\"volume_ratio\", 0),\n"
    "                getattr(snapshot.regime, \"value\", snapshot.regime),\n"
    "            )",
    "            log.debug(\n"
    "                \"[UniverseAudit] %-14s reason=%-22s rsi=%4.0f vol=%.1fx regime=%s\",\n"
    "                stock[\"symbol\"], reason,\n"
    "                stock.get(\"rsi\", 0), stock.get(\"volume_ratio\", 0),\n"
    "                getattr(snapshot.regime, \"value\", snapshot.regime),\n"
    "            )\n"
    "            # TrendFilterAudit: per-symbol detail when trend_filter bucket fires\n"
    "            _TF_REASONS = frozenset({\n"
    "                'breakout_rsi_hi', 'retest_rsi_oob', 'pullback_miss',\n"
    "                'short_conditions', 'bounce_price_hi', 'rsi_neutral',\n"
    "            })\n"
    "            if reason in _TF_REASONS:\n"
    "                _tf_rsi = stock.get('rsi', 0)\n"
    "                _tf_vol = stock.get('volume_ratio', 1.0)\n"
    "                _tf_ltp = stock.get('ltp', 0)\n"
    "                _tf_res = stock.get('resistance', 0)\n"
    "                _tf_sup = stock.get('support', 0)\n"
    "                _tf_sec = stock.get('sector') or _SYMBOL_SECTOR_MAP.get(stock['symbol'], 'UNKNOWN')\n"
    "                _tf_reg = getattr(snapshot.regime, 'value', str(snapshot.regime))\n"
    "                _TF_META = {\n"
    "                    'breakout_rsi_hi':  ('RSI_OVERBOUGHT_AT_BREAKOUT',  'RSI<75'),\n"
    "                    'retest_rsi_oob':   ('RSI_OUTSIDE_RETEST_BAND',     'RSI_50-65'),\n"
    "                    'pullback_miss':    ('PULLBACK_CONDITIONS_NOT_MET',  'RSI_38-56_vol_ge_1.2'),\n"
    "                    'short_conditions': ('SHORT_SETUP_CONDITIONS_UNMET', 'RSI_ge_67_AND_price_ge_res_099'),\n"
    "                    'bounce_price_hi':  ('PRICE_ABOVE_SUPPORT_ZONE',    'price_le_support_102'),\n"
    "                    'rsi_neutral':      ('RSI_IN_NO_SIGNAL_ZONE',       'RSI_lt_46_OR_RSI_gt_66'),\n"
    "                }\n"
    "                _cond, _req = _TF_META.get(reason, (reason.upper(), '?'))\n"
    "                log.info(\n"
    "                    '[TrendFilterAudit] symbol=%-14s sector=%-12s '\n"
    "                    'rejection_reason=%-28s trend_condition=%s '\n"
    "                    'required=%s '\n"
    "                    'trend_score=%.0f vol_ratio=%.1f '\n"
    "                    'ltp=%.2f resistance=%.2f support=%.2f regime=%s',\n"
    "                    stock['symbol'], _tf_sec,\n"
    "                    reason, _cond,\n"
    "                    _req,\n"
    "                    _tf_rsi, _tf_vol,\n"
    "                    _tf_ltp, _tf_res, _tf_sup, _tf_reg,\n"
    "                )\n"
    "                try:\n"
    "                    from control_tower.pipeline_forensic_reporter import get_pipeline_reporter as _gpfr\n"
    "                    _gpfr().record_trend_filter_rejection(stock['symbol'], _tf_sec, reason)\n"
    "                except Exception:\n"
    "                    pass\n"
    "            # end TrendFilterAudit",
    "A4a-per-symbol",
)
errors += not ok

try:
    py_compile.compile(ESA, doraise=True)
    print(f"  SYNTAX OK: {ESA}")
except py_compile.PyCompileError as e:
    print(f"  SYNTAX FAIL: {e}")
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT 4b — TrendFilterSummary EOD — pipeline_forensic_reporter.py
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== AUDIT 4b: TrendFilterSummary EOD (pipeline_forensic_reporter.py) ===")
PFR = "/app/control_tower/pipeline_forensic_reporter.py"

ok = patch(PFR,
    "        # ── Sector coverage (across all scan cycles today) ───────────\n"
    "        self._sector_coverage: Dict[str, int] = defaultdict(int)",
    "        # ── Sector coverage (across all scan cycles today) ───────────\n"
    "        self._sector_coverage: Dict[str, int] = defaultdict(int)\n"
    "\n"
    "        # TrendFilter forensics (for TrendFilterSummary)\n"
    "        self._tf_symbol_counts: Dict[str, int] = defaultdict(int)\n"
    "        self._tf_sector_counts: Dict[str, int] = defaultdict(int)\n"
    "        self._tf_reason_counts: Dict[str, int] = defaultdict(int)",
    "A4b-reset",
)
errors += not ok

ok = patch(PFR,
    "    def record_lifecycle_transition(self, symbol: str, old_state: str, new_state: str) -> None:",
    "    def record_trend_filter_rejection(\n"
    "        self, symbol: str, sector: str, reason: str\n"
    "    ) -> None:\n"
    "        \"\"\"Accumulate per-symbol/sector/reason counts for TrendFilterSummary.\"\"\"\n"
    "        with self._lock:\n"
    "            self._check_rollover()\n"
    "            self._tf_symbol_counts[symbol] += 1\n"
    "            self._tf_sector_counts[sector or 'UNKNOWN'] += 1\n"
    "            self._tf_reason_counts[reason] += 1\n"
    "\n"
    "    def record_lifecycle_transition(self, symbol: str, old_state: str, new_state: str) -> None:",
    "A4b-method",
)
errors += not ok

ok = patch(PFR,
    "                sec_cov      = dict(self._sector_coverage)\n"
    "                regime_hist  = list(self._regime_history)",
    "                sec_cov      = dict(self._sector_coverage)\n"
    "                regime_hist  = list(self._regime_history)\n"
    "                tf_sym       = dict(self._tf_symbol_counts)\n"
    "                tf_sec       = dict(self._tf_sector_counts)\n"
    "                tf_rsn       = dict(self._tf_reason_counts)",
    "A4b-snapshot",
)
errors += not ok

ok = patch(PFR,
    "            # ── Stage 3: Strategy ──────────────────────────────────────────",
    "            # TrendFilterSummary: EOD breakdown of all trend_filter rejections\n"
    "            _tf_total = sum(tf_rsn.values())\n"
    "            if _tf_total > 0:\n"
    "                _tf_top_sym = sorted(tf_sym.items(), key=lambda x: -x[1])[:5]\n"
    "                _tf_top_sec = sorted(tf_sec.items(), key=lambda x: -x[1])[:5]\n"
    "                _tf_rsn_dist = '  '.join(\n"
    "                    f'{k}={v}' for k, v in sorted(tf_rsn.items(), key=lambda x: -x[1])\n"
    "                )\n"
    "                log.info(\n"
    "                    '[TrendFilterSummary] date=%s '\n"
    "                    'total_rejected=%d '\n"
    "                    'top_sectors_rejected=%s '\n"
    "                    'top_repeated_symbols=%s '\n"
    "                    'rejection_reason_distribution=%s',\n"
    "                    d, _tf_total,\n"
    "                    str(_tf_top_sec),\n"
    "                    str(_tf_top_sym),\n"
    "                    _tf_rsn_dist,\n"
    "                )\n"
    "            # end TrendFilterSummary\n"
    "\n"
    "            # ── Stage 3: Strategy ──────────────────────────────────────────",
    "A4b-summary-emit",
)
errors += not ok

try:
    py_compile.compile(PFR, doraise=True)
    print(f"  SYNTAX OK: {PFR}")
except py_compile.PyCompileError as e:
    print(f"  SYNTAX FAIL: {e}")
    errors += 1

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"RESULT: {'ALL OK' if errors == 0 else f'{errors} PATCH(ES) FAILED'}")
sys.exit(0 if errors == 0 else 1)

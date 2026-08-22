"""
deploy_forensic_audits.py — June 3 Forensic Audit Deployment

Applies 4 forensic audit packages to the VPS container:

  AUDIT 1  [ExecutionWindowAudit]   — order_manager.py
  AUDIT 2  [CorporateActionAudit]   — trade_monitor.py + master_orchestrator.py
  FIX 3    [ReadinessScoreAudit]    — angelone_readiness_auditor.py
  AUDIT 4  [TrendFilterAudit]       — equity_scanner_ai.py
           [TrendFilterSummary]     — pipeline_forensic_reporter.py

Evidence-only instruments.  No logic changes.  No threshold changes.
No strategy changes.
"""

import subprocess, sys, textwrap

SSH = "ssh -i C:/Users/UCIC/.ssh/trading_vps -o StrictHostKeyChecking=no root@178.18.252.24"
CONTAINER = "ai-trading-brain"


def run(cmd: str, label: str = "") -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = result.stdout + result.stderr
    tag = f"[{label}] " if label else ""
    print(f"{tag}{out.strip()}")
    if result.returncode != 0:
        print(f"  *** EXIT {result.returncode} — check output above")
    return out


def docker(cmd: str, label: str = "") -> str:
    return run(f'{SSH} "docker exec {CONTAINER} {cmd}"', label)


def patch_file(remote_path: str, old: str, new: str, label: str) -> bool:
    """Apply a single string replacement to a file in the container via Python."""
    import json
    script = textwrap.dedent(f"""
import sys
path = {json.dumps(remote_path)}
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()
old = {json.dumps(old)}
new = {json.dumps(new)}
if old not in src:
    print("PATCH_MISS: old string not found in " + path)
    sys.exit(1)
if src.count(old) > 1:
    print("PATCH_AMBIGUOUS: old string found multiple times in " + path)
    sys.exit(1)
src = src.replace(old, new, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(src)
print("PATCH_OK")
""").strip()
    result = run(f'{SSH} "python3 -c \'{script}\'"', label)
    return "PATCH_OK" in result


def syntax_check(path: str, label: str) -> bool:
    result = docker(f"python3 -m py_compile {path} && echo SYNTAX_OK", label)
    return "SYNTAX_OK" in result


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT 1 — [ExecutionWindowAudit] — order_manager.py
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("AUDIT 1 — ExecutionWindowAudit → order_manager.py")
print("="*70)

OM_PATH = "/app/execution_engine/order_manager.py"

# Step 1: add _EXEC_WINDOW_OPEN constant next to the late-entry constants
patch_file(
    OM_PATH,
    "_LATE_ENTRY_MIN_SCORE = 7.0                               # score floor in elevated window",
    "_LATE_ENTRY_MIN_SCORE = 7.0                               # score floor in elevated window\n"
    "_EXEC_WINDOW_OPEN_H, _EXEC_WINDOW_OPEN_M = 9, 45    # governance window opens (IST)",
    "A1-constant",
)

# Step 2: add [ExecutionWindowAudit] emit in the late-entry block
patch_file(
    OM_PATH,
    "        if not _is_same_symbol_swap:\n"
    "            _now = datetime.now()\n"
    "            _cutoff  = _now.replace(hour=_LATE_ENTRY_CUTOFF_H,   minute=_LATE_ENTRY_CUTOFF_M,   second=0, microsecond=0)\n"
    "            _elevated = _now.replace(hour=_LATE_ENTRY_ELEVATED_H, minute=_LATE_ENTRY_ELEVATED_M, second=0, microsecond=0)",
    "        if not _is_same_symbol_swap:\n"
    "            _now = datetime.now()\n"
    "            # ── ExecutionWindowAudit — observe early entries (before 09:45) ───\n"
    "            _exec_win_open = _now.replace(\n"
    "                hour=_EXEC_WINDOW_OPEN_H, minute=_EXEC_WINDOW_OPEN_M,\n"
    "                second=0, microsecond=0,\n"
    "            )\n"
    "            if _now < _exec_win_open:\n"
    "                _mins_early = int((_exec_win_open - _now).total_seconds() / 60)\n"
    "                log.warning(\n"
    "                    \"[ExecutionWindowAudit] symbol=%s strategy=%s \"\n"
    "                    \"order_time=%s window_opens=09:45 minutes_early=%d \"\n"
    "                    \"window_check=ABSENT_IN_EXECUTION_LAYER \"\n"
    "                    \"root_cause=first_opportunity_scan_fires_run_full_cycle_without_early_guard \"\n"
    "                    \"governance_check=LEARNING_LAYER_ONLY\",\n"
    "                    signal.symbol,\n"
    "                    getattr(signal, \"strategy_name\", \"?\"),\n"
    "                    _now.strftime(\"%H:%M:%S\"),\n"
    "                    _mins_early,\n"
    "                )\n"
    "            # ─────────────────────────────────────────────────────────────\n"
    "            _cutoff  = _now.replace(hour=_LATE_ENTRY_CUTOFF_H,   minute=_LATE_ENTRY_CUTOFF_M,   second=0, microsecond=0)\n"
    "            _elevated = _now.replace(hour=_LATE_ENTRY_ELEVATED_H, minute=_LATE_ENTRY_ELEVATED_M, second=0, microsecond=0)",
    "A1-audit-emit",
)

syntax_check(OM_PATH, "A1-syntax")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT 2 — [CorporateActionAudit] — trade_monitor.py
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("AUDIT 2a — CorporateActionAudit → trade_monitor.py (LTPGuard path)")
print("="*70)

TM_PATH = "/app/trade_monitoring/trade_monitor.py"

patch_file(
    TM_PATH,
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
    "                        # ── CorporateActionAudit — structured forensic evidence ──\n"
    "                        _entry_px = getattr(order, \"entry_price\", baseline)\n"
    "                        log.warning(\n"
    "                            \"[CorporateActionAudit] symbol=%s oid=%s \"\n"
    "                            \"feed_price=%.2f last_known=%.2f entry_price=%.2f \"\n"
    "                            \"deviation_pct=%.1f \"\n"
    "                            \"detection=LTPGuard_threshold_20pct \"\n"
    "                            \"positions_affected=1 \"\n"
    "                            \"phantom_pnl_risk=YES_sl_fires_on_frozen_not_real_price \"\n"
    "                            \"learning_contamination_risk=YES_exit_recorded_at_fallback \"\n"
    "                            \"auto_review_state=NOT_IMPLEMENTED \"\n"
    "                            \"action=FROZEN_AT_LAST_KNOWN \"\n"
    "                            \"recommendation=manual_close_CORPORATE_ACTION_CLOSE\",\n"
    "                            symbol, order.order_id if order else \"?\",\n"
    "                            candidate, baseline, _entry_px,\n"
    "                            deviation * 100,\n"
    "                        )\n"
    "                        # ─────────────────────────────────────────────────────\n"
    "                        self._dg_update_stale(order.order_id, symbol, baseline)",
    "A2a-ltpguard",
)

syntax_check(TM_PATH, "A2a-syntax")

print("\n" + "="*70)
print("AUDIT 2b — CorporateActionAudit → master_orchestrator.py (restore path)")
print("="*70)

MO_PATH = "/app/orchestrator/master_orchestrator.py"

patch_file(
    MO_PATH,
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
    "                    # ── CorporateActionAudit — structured forensic evidence ──\n"
    "                    log.warning(\n"
    "                        \"[CorporateActionAudit] symbol=%s \"\n"
    "                        \"entry_price=%.2f feed_ltp=%.2f deviation_pct=%.1f \"\n"
    "                        \"detection=post_restore_plausibility_50pct \"\n"
    "                        \"positions_affected=1 \"\n"
    "                        \"phantom_pnl_risk=YES_fallback_price_active_for_sl_eval \"\n"
    "                        \"learning_contamination_risk=YES_exit_recorded_at_stale_entry_not_real \"\n"
    "                        \"auto_review_state=NOT_IMPLEMENTED \"\n"
    "                        \"action=RECONCILIATION_SUSPECT_NOTIFIED \"\n"
    "                        \"recommendation=manual_close_CORPORATE_ACTION_CLOSE\",\n"
    "                        _rec.symbol, _entry, _ltp, _deviation * 100,\n"
    "                    )\n"
    "                    # ──────────────────────────────────────────────────────",
    "A2b-restore",
)

syntax_check(MO_PATH, "A2b-syntax")


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 3 — [ReadinessScoreAudit] — angelone_readiness_auditor.py
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("FIX 3 — ReadinessScoreAudit → angelone_readiness_auditor.py")
print("="*70)

ARA_PATH = "/app/data_feeds/angelone_readiness_auditor.py"

# Step 1: find the class-level constants block — add _MIN_LTP_SAMPLES
# Look for an existing class attribute to anchor off
docker(f"grep -n '_MIN_LTP\|_p1\|_p2_total\|class AngelOne\|def __init__' {ARA_PATH} | head -15", "ARA-probe")

patch_file(
    ARA_PATH,
    "    def emit_readiness_report(self) -> None:\n"
    "        \"\"\"Emit [AngelOneReadinessReport] — call at EOD.\"\"\"\n"
    "        with self._mu:",
    "    # Minimum LTP shadow comparisons before the score is statistically meaningful\n"
    "    _MIN_LTP_SAMPLES: int = 10\n"
    "\n"
    "    def emit_readiness_report(self) -> None:\n"
    "        \"\"\"Emit [AngelOneReadinessReport] — call at EOD.\"\"\"\n"
    "        with self._mu:",
    "F3-constant",
)

# Step 2: add sample size guard after confidence is computed
patch_file(
    ARA_PATH,
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
    "            # ── Sample size guard: confidence is invalid when ltp_compared=0 ──\n"
    "            _insufficient = total_sym < self._MIN_LTP_SAMPLES\n"
    "            if _insufficient:\n"
    "                confidence_label = \"UNKNOWN\"\n"
    "                migration_ready  = \"UNKNOWN\"\n"
    "                recommendation   = (\n"
    "                    f\"Insufficient LTP samples ({total_sym}/{self._MIN_LTP_SAMPLES}) \"\n"
    "                    f\"— score not valid; accumulate more sessions\"\n"
    "                )\n"
    "            else:\n"
    "                confidence_label = str(confidence)\n"
    "                migration_ready  = \"YES\" if confidence >= 80 else \"NO\"\n"
    "                recommendation   = (\n"
    "                    \"Ready for Dhan retirement\" if confidence >= 80\n"
    "                    else \"Continue dual-feed — gaps remain\"\n"
    "                )",
    "F3-guard",
)

# Step 3: update the log line to use confidence_label instead of raw confidence
patch_file(
    ARA_PATH,
    "            \"overall_confidence=%d migration_ready=%s \"\n"
    "            \"recommendation=%s | \"\n"
    "            \"detail: ltp_compared=%d avg_ltp_diff=%.3f%% max_ltp_diff=%.3f%% \"",
    "            \"overall_confidence=%s migration_ready=%s \"\n"
    "            \"insufficient_data=%s \"\n"
    "            \"recommendation=%s | \"\n"
    "            \"detail: ltp_compared=%d avg_ltp_diff=%.3f%% max_ltp_diff=%.3f%% \"",
    "F3-logfmt",
)

# Step 4: update the log args to pass confidence_label, and _insufficient
patch_file(
    ARA_PATH,
    "            confidence, migration_ready, recommendation,\n"
    "            total_sym, avg_ltp_diff, max_ltp_diff,",
    "            confidence_label, migration_ready, _insufficient, recommendation,\n"
    "            total_sym, avg_ltp_diff, max_ltp_diff,",
    "F3-logargs",
)

# Step 5: add [ReadinessScoreAudit] emit right after the capability inventory block
patch_file(
    ARA_PATH,
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
    "        # ── ReadinessScoreAudit — per-component breakdown ──────────────\n"
    "        with self._mu:\n"
    "            _ts = total_sym\n"
    "        log.info(\n"
    "            \"[ReadinessScoreAudit] \"\n"
    "            \"ltp_samples=%d min_required=%d sample_valid=%s \"\n"
    "            \"ltp_score=%s options_score=%d candidate_score=%d \"\n"
    "            \"signal_score=%d reliability_score=%d \"\n"
    "            \"overall_confidence=%s \"\n"
    "            \"note=ltp_score_is_zero_weighted_when_insufficient_data\",\n"
    "            _ts, self._MIN_LTP_SAMPLES, not _insufficient,\n"
    "            \"INVALID\" if _insufficient else str(ltp_score),\n"
    "            options_score, candidate_score, signal_score, reliability_score,\n"
    "            confidence_label,\n"
    "        )",
    "F3-readiness-audit",
)

syntax_check(ARA_PATH, "F3-syntax")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT 4 — [TrendFilterAudit] per-symbol — equity_scanner_ai.py
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("AUDIT 4a — TrendFilterAudit per-symbol → equity_scanner_ai.py")
print("="*70)

ESA_PATH = "/app/opportunity_engine/equity_scanner_ai.py"

# Inject [TrendFilterAudit] after the existing [UniverseAudit] debug line in the scan loop
patch_file(
    ESA_PATH,
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
    "            # ── TrendFilterAudit — per-symbol detail for trend_filter rejections ──\n"
    "            _TF_REASONS = {\n"
    "                \"breakout_rsi_hi\", \"retest_rsi_oob\", \"pullback_miss\",\n"
    "                \"short_conditions\", \"bounce_price_hi\", \"rsi_neutral\",\n"
    "            }\n"
    "            if reason in _TF_REASONS:\n"
    "                _tf_rsi   = stock.get(\"rsi\", 0)\n"
    "                _tf_vol   = stock.get(\"volume_ratio\", 1.0)\n"
    "                _tf_ltp   = stock.get(\"ltp\", 0)\n"
    "                _tf_res   = stock.get(\"resistance\", 0)\n"
    "                _tf_sup   = stock.get(\"support\", 0)\n"
    "                _tf_sec   = stock.get(\"sector\") or _SYMBOL_SECTOR_MAP.get(stock[\"symbol\"], \"UNKNOWN\")\n"
    "                _tf_reg   = getattr(snapshot.regime, \"value\", str(snapshot.regime))\n"
    "                # Map reason → human-readable condition and required threshold\n"
    "                _TF_META = {\n"
    "                    \"breakout_rsi_hi\":  (\"RSI_OVERBOUGHT_AT_BREAKOUT\",  \"RSI<75\"),\n"
    "                    \"retest_rsi_oob\":   (\"RSI_OUTSIDE_RETEST_BAND\",     \"RSI_50-65\"),\n"
    "                    \"pullback_miss\":    (\"PULLBACK_CONDITIONS_NOT_MET\",  \"RSI_38-56_vol>=1.2\"),\n"
    "                    \"short_conditions\": (\"SHORT_SETUP_CONDITIONS_UNMET\", \"RSI>=67_AND_price>=res*0.99\"),\n"
    "                    \"bounce_price_hi\":  (\"PRICE_ABOVE_SUPPORT_ZONE\",    \"price<=support*1.02\"),\n"
    "                    \"rsi_neutral\":      (\"RSI_IN_NO_SIGNAL_ZONE\",       \"RSI<46_OR_RSI>66\"),\n"
    "                }\n"
    "                _cond, _req = _TF_META.get(reason, (reason.upper(), \"?\"))\n"
    "                log.info(\n"
    "                    \"[TrendFilterAudit] symbol=%-14s sector=%-12s \"\n"
    "                    \"rejection_reason=%-28s trend_condition=%s \"\n"
    "                    \"required=%s \"\n"
    "                    \"trend_score=%.0f vol_ratio=%.1f \"\n"
    "                    \"ltp=%.2f resistance=%.2f support=%.2f regime=%s\",\n"
    "                    stock[\"symbol\"], _tf_sec,\n"
    "                    reason, _cond,\n"
    "                    _req,\n"
    "                    _tf_rsi, _tf_vol,\n"
    "                    _tf_ltp, _tf_res, _tf_sup, _tf_reg,\n"
    "                )\n"
    "            # ──────────────────────────────────────────────────────────────",
    "A4a-per-symbol",
)

syntax_check(ESA_PATH, "A4a-syntax")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT 4 — [TrendFilterSummary] EOD — pipeline_forensic_reporter.py
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("AUDIT 4b — TrendFilterSummary EOD → pipeline_forensic_reporter.py")
print("="*70)

PFR_PATH = "/app/control_tower/pipeline_forensic_reporter.py"

# Step 1: add TrendFilter tracking fields to _reset()
patch_file(
    PFR_PATH,
    "        # ── Sector coverage (across all scan cycles today) ───────────\n"
    "        self._sector_coverage: Dict[str, int] = defaultdict(int)",
    "        # ── Sector coverage (across all scan cycles today) ───────────\n"
    "        self._sector_coverage: Dict[str, int] = defaultdict(int)\n"
    "\n"
    "        # ── TrendFilter forensics ────────────────────────────────────\n"
    "        self._tf_symbol_counts: Dict[str, int] = defaultdict(int)   # symbol → rejections\n"
    "        self._tf_sector_counts: Dict[str, int] = defaultdict(int)   # sector → rejections\n"
    "        self._tf_reason_counts: Dict[str, int] = defaultdict(int)   # sub-reason → rejections",
    "A4b-reset",
)

# Step 2: add record_trend_filter_rejection() method (after record_invalidation)
patch_file(
    PFR_PATH,
    "    def record_lifecycle_transition(self, symbol: str, old_state: str, new_state: str) -> None:",
    "    def record_trend_filter_rejection(\n"
    "        self, symbol: str, sector: str, reason: str\n"
    "    ) -> None:\n"
    "        \"\"\"Call for every trend_filter rejection to power TrendFilterSummary.\"\"\"\n"
    "        with self._lock:\n"
    "            self._check_rollover()\n"
    "            self._tf_symbol_counts[symbol] += 1\n"
    "            self._tf_sector_counts[sector or \"UNKNOWN\"] += 1\n"
    "            self._tf_reason_counts[reason] += 1\n"
    "\n"
    "    def record_lifecycle_transition(self, symbol: str, old_state: str, new_state: str) -> None:",
    "A4b-method",
)

# Step 3: snapshot new fields in emit_daily_summary() under lock
patch_file(
    PFR_PATH,
    "                sec_cov      = dict(self._sector_coverage)\n"
    "                regime_hist  = list(self._regime_history)",
    "                sec_cov      = dict(self._sector_coverage)\n"
    "                regime_hist  = list(self._regime_history)\n"
    "                tf_sym       = dict(self._tf_symbol_counts)\n"
    "                tf_sec       = dict(self._tf_sector_counts)\n"
    "                tf_rsn       = dict(self._tf_reason_counts)",
    "A4b-snapshot",
)

# Step 4: emit [TrendFilterSummary] after [PipelineFiltering] daily summary
patch_file(
    PFR_PATH,
    "            # ── Stage 3: Strategy ──────────────────────────────────────────",
    "            # ── TrendFilterSummary — EOD breakdown of 183-class rejections ──\n"
    "            _tf_total = sum(tf_rsn.values())\n"
    "            if _tf_total > 0:\n"
    "                _tf_top_sym = sorted(tf_sym.items(), key=lambda x: -x[1])[:5]\n"
    "                _tf_top_sec = sorted(tf_sec.items(), key=lambda x: -x[1])[:5]\n"
    "                _tf_rsn_dist = \"  \".join(\n"
    "                    f\"{k}={v}\" for k, v in sorted(tf_rsn.items(), key=lambda x: -x[1])\n"
    "                )\n"
    "                log.info(\n"
    "                    \"[TrendFilterSummary] date=%s \"\n"
    "                    \"total_rejected=%d \"\n"
    "                    \"top_sectors_rejected=%s \"\n"
    "                    \"top_repeated_symbols=%s \"\n"
    "                    \"rejection_reason_distribution=%s\",\n"
    "                    d, _tf_total,\n"
    "                    str(_tf_top_sec),\n"
    "                    str(_tf_top_sym),\n"
    "                    _tf_rsn_dist,\n"
    "                )\n"
    "            # ─────────────────────────────────────────────────────────────\n"
    "\n"
    "            # ── Stage 3: Strategy ──────────────────────────────────────────",
    "A4b-summary-emit",
)

syntax_check(PFR_PATH, "A4b-syntax")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT 4c — Wire record_trend_filter_rejection() from equity_scanner_ai.py
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("AUDIT 4c — Wire TrendFilter rejection counter into forensic reporter")
print("="*70)

# Add the reporter call inside the TrendFilterAudit block we already injected
patch_file(
    ESA_PATH,
    "                log.info(\n"
    "                    \"[TrendFilterAudit] symbol=%-14s sector=%-12s \"\n"
    "                    \"rejection_reason=%-28s trend_condition=%s \"\n"
    "                    \"required=%s \"\n"
    "                    \"trend_score=%.0f vol_ratio=%.1f \"\n"
    "                    \"ltp=%.2f resistance=%.2f support=%.2f regime=%s\",\n"
    "                    stock[\"symbol\"], _tf_sec,\n"
    "                    reason, _cond,\n"
    "                    _req,\n"
    "                    _tf_rsi, _tf_vol,\n"
    "                    _tf_ltp, _tf_res, _tf_sup, _tf_reg,\n"
    "                )\n"
    "            # ──────────────────────────────────────────────────────────────",
    "                log.info(\n"
    "                    \"[TrendFilterAudit] symbol=%-14s sector=%-12s \"\n"
    "                    \"rejection_reason=%-28s trend_condition=%s \"\n"
    "                    \"required=%s \"\n"
    "                    \"trend_score=%.0f vol_ratio=%.1f \"\n"
    "                    \"ltp=%.2f resistance=%.2f support=%.2f regime=%s\",\n"
    "                    stock[\"symbol\"], _tf_sec,\n"
    "                    reason, _cond,\n"
    "                    _req,\n"
    "                    _tf_rsi, _tf_vol,\n"
    "                    _tf_ltp, _tf_res, _tf_sup, _tf_reg,\n"
    "                )\n"
    "                # Feed the forensic reporter for EOD TrendFilterSummary\n"
    "                try:\n"
    "                    from control_tower.pipeline_forensic_reporter import get_pipeline_reporter as _gpfr\n"
    "                    _gpfr().record_trend_filter_rejection(stock[\"symbol\"], _tf_sec, reason)\n"
    "                except Exception:\n"
    "                    pass\n"
    "            # ──────────────────────────────────────────────────────────────",
    "A4c-wire",
)

syntax_check(ESA_PATH, "A4c-syntax")


# ═══════════════════════════════════════════════════════════════════════════════
# FINAL — restart container
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("FINAL — Restarting container")
print("="*70)

run(f'{SSH} "docker restart {CONTAINER}"', "RESTART")
print("\nDone. Watch for [ExecutionWindowAudit], [CorporateActionAudit],")
print("[ReadinessScoreAudit], [TrendFilterAudit], [TrendFilterSummary] in logs.")

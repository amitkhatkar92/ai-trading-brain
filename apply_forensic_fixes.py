"""
Patch script: Apply all 7 forensic refinement fixes.
Run inside container: python3 /app/apply_forensic_fixes.py
"""
import re, sys, shutil, os

def patch_file(path, old, new, label):
    with open(path) as f:
        src = f.read()
    if old not in src:
        print(f"  MISS [{label}] — pattern not found in {path}")
        return False
    cnt = src.count(old)
    if cnt > 1:
        print(f"  WARN [{label}] — {cnt} occurrences of pattern in {path}")
    src2 = src.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(src2)
    print(f"  OK   [{label}]")
    return True

results = []

# ─── FIX 1: EveningScanSchedulerAudit — master_orchestrator.py ───────────────
MO = "/app/orchestrator/master_orchestrator.py"

results.append(patch_file(MO,
    '    def _run_post_market_scan(self) -> None:\n'
    '        """\n'
    '        Phase D — Post-market deep scan.  Scheduled at 16:45 IST.\n'
    '        Runs ~20 min, writes prepared candidates to data/daily_candidates.json.\n'
    '        Skipped on NSE holidays; skipped if SCANNER_SHADOW_MODE=True until\n'
    '        shadow validation is complete.\n'
    '        """\n'
    '        try:\n'
    '            from config import is_nse_holiday\n'
    '            if is_nse_holiday():\n'
    '                log.info("[Orchestrator] NSE HOLIDAY — post-market scan skipped.")\n'
    '                return\n'
    '            log.info("[Orchestrator] 16:45 IST — starting Phase D post-market scanner.")\n'
    '            from opportunity_engine.market_scanner import run_scan\n'
    '            success = run_scan()\n'
    '            if success:\n'
    '                log.info("[Orchestrator] Phase D scanner complete — candidate store updated.")\n'
    '            else:\n'
    '                log.warning("[Orchestrator] Phase D scanner returned failure — static fallback active tomorrow.")\n'
    '        except Exception as exc:\n'
    '            log.error("[Orchestrator] Phase D scanner crashed: %s", exc, exc_info=True)\n',

    '    def _run_post_market_scan(self, trigger_source: str = "SCHEDULER") -> None:\n'
    '        """\n'
    '        Phase D — Post-market deep scan.  Scheduled at 16:45 IST.\n'
    '        Runs ~20 min, writes prepared candidates to data/daily_candidates.json.\n'
    '        Skipped on NSE holidays; skipped if SCANNER_SHADOW_MODE=True until\n'
    '        shadow validation is complete.\n'
    '        """\n'
    '        try:\n'
    '            from config import is_nse_holiday\n'
    '            if is_nse_holiday():\n'
    '                log.info("[Orchestrator] NSE HOLIDAY — post-market scan skipped.")\n'
    '                return\n'
    '            _scheduler_fired = trigger_source == "SCHEDULER"\n'
    '            log.info(\n'
    '                "[EveningScanSchedulerAudit] scheduled_time=%s actual_time=%s "\n'
    '                "trigger_source=%s scheduler_registered=True scheduler_fired=%s "\n'
    '                "fallback_scan_used=%s",\n'
    '                SCHEDULE["post_market_scan"],\n'
    '                datetime.now().strftime("%H:%M"),\n'
    '                trigger_source,\n'
    '                _scheduler_fired,\n'
    '                not _scheduler_fired,\n'
    '            )\n'
    '            log.info("[Orchestrator] 16:45 IST — starting Phase D post-market scanner.")\n'
    '            from opportunity_engine.market_scanner import run_scan\n'
    '            success = run_scan()\n'
    '            if success:\n'
    '                log.info("[Orchestrator] Phase D scanner complete — candidate store updated.")\n'
    '            else:\n'
    '                log.warning("[Orchestrator] Phase D scanner returned failure — static fallback active tomorrow.")\n'
    '        except Exception as exc:\n'
    '            log.error("[Orchestrator] Phase D scanner crashed: %s", exc, exc_info=True)\n',
    "Fix1-method-sig",
))

results.append(patch_file(MO,
    '            if _needs_scan:\n'
    '                import threading as _threading\n'
    '                _t = _threading.Thread(\n'
    '                    target=self._run_post_market_scan,\n'
    '                    daemon=True, name="PremarketPhaseD",\n'
    '                )',

    '            if _needs_scan:\n'
    '                import threading as _threading\n'
    '                _t = _threading.Thread(\n'
    '                    target=lambda: self._run_post_market_scan(trigger_source="STARTUP_STALE_DETECTION"),\n'
    '                    daemon=True, name="PremarketPhaseD",\n'
    '                )',
    "Fix1-startup-trigger",
))

# ─── FIX 7: UniverseHealthReport appended to _run_post_market_scan ────────────
results.append(patch_file(MO,
    '            if success:\n'
    '                log.info("[Orchestrator] Phase D scanner complete — candidate store updated.")\n'
    '            else:\n'
    '                log.warning("[Orchestrator] Phase D scanner returned failure — static fallback active tomorrow.")\n'
    '        except Exception as exc:\n'
    '            log.error("[Orchestrator] Phase D scanner crashed: %s", exc, exc_info=True)\n',

    '            if success:\n'
    '                log.info("[Orchestrator] Phase D scanner complete — candidate store updated.")\n'
    '            else:\n'
    '                log.warning("[Orchestrator] Phase D scanner returned failure — static fallback active tomorrow.")\n'
    '            # Fix 7 — UniverseHealthReport scorecard\n'
    '            try:\n'
    '                import json as _uj\n'
    '                from pathlib import Path as _UP\n'
    '                _up = _UP("data/daily_candidates.json")\n'
    '                if _up.exists():\n'
    '                    _ud = _uj.loads(_up.read_text())\n'
    '                    _uss  = _ud.get("scanner_stats", {})\n'
    '                    _ucov = _uss.get("coverage_pct", 0.0)\n'
    '                    _ucands = len(_ud.get("candidates", []))\n'
    '                    _scan_health    = "GOOD" if _ucov >= 70 else "WARN" if _ucov >= 50 else "FAIL"\n'
    '                    _fresh_health   = "GOOD" if success else "FAIL"\n'
    '                    _refiner_status = _ud.get("premarket_refresh_complete", None)\n'
    '                    _refiner_health = "GOOD" if _refiner_status else "PENDING"\n'
    '                    _stale_pct      = round((1.0 - _ucov / 100.0) * 100, 1) if _ucov else 0.0\n'
    '                    _overall        = "GOOD" if _scan_health == "GOOD" and _fresh_health == "GOOD" else "WARN"\n'
    '                    log.info(\n'
    '                        "[UniverseHealthReport] scan_health=%s refiner_health=%s "\n'
    '                        "freshness_health=%s coverage_pct=%.1f stale_pct=%.1f "\n'
    '                        "candidates=%d overall_health=%s trigger_source=%s",\n'
    '                        _scan_health, _refiner_health, _fresh_health,\n'
    '                        _ucov, _stale_pct, _ucands, _overall, trigger_source,\n'
    '                    )\n'
    '            except Exception as _uhr_e:\n'
    '                log.debug("[UniverseHealthReport] failed: %s", _uhr_e)\n'
    '        except Exception as exc:\n'
    '            log.error("[Orchestrator] Phase D scanner crashed: %s", exc, exc_info=True)\n',
    "Fix7-universe-health-report",
))

# ─── FIX 2 + 4: PremarketRefiner — premarket_refiner.py ─────────────────────
PR = "/app/opportunity_engine/premarket_refiner.py"

results.append(patch_file(PR,
    'def _get_sector_bias() -> Dict[str, float]:\n'
    '    """Get sector bias from GlobalDataAI. Returns {} on any failure."""\n'
    '    try:\n'
    '        from global_intelligence.global_data_ai import GlobalDataAI\n'
    '        gd = GlobalDataAI()\n'
    '        snap = gd.fetch()  # uses cache if already fetched this cycle\n'
    '        return gd.get_sector_regime_bias()\n'
    '    except Exception as exc:\n'
    '        log.debug("[PremarketRefiner] Sector bias unavailable: %s", exc)\n'
    '        return {}',

    'def _get_sector_bias() -> tuple:\n'
    '    """Get sector bias from GlobalDataAI. Returns (bias_dict, available) tuple."""\n'
    '    try:\n'
    '        from global_intelligence.global_data_ai import GlobalDataAI\n'
    '        gd = GlobalDataAI()\n'
    '        gd.fetch()  # uses cache if already fetched this cycle\n'
    '        return gd.get_sector_regime_bias(), True\n'
    '    except Exception as exc:\n'
    '        log.debug("[PremarketRefiner] Sector bias unavailable: %s", exc)\n'
    '        return {}, False',
    "Fix2-sector-bias-tuple",
))

# Update the call site — _get_sector_bias() is called once in run_premarket_refinement
results.append(patch_file(PR,
    '    # ── Load sector bias from GlobalDataAI ────────────────────────────────────\n'
    '    sector_bias = _get_sector_bias()\n',

    '    # ── Load sector bias from GlobalDataAI ────────────────────────────────────\n'
    '    sector_bias, _bias_avail = _get_sector_bias()\n',
    "Fix2-callsite-unpack",
))

# Add sector_adj_count tracking and rank_changes in the loop
results.append(patch_file(PR,
    '    refined: List[Dict[str, Any]] = []\n'
    '    expired_count  = 0\n'
    '    adjusted_count = 0\n',

    '    refined: List[Dict[str, Any]] = []\n'
    '    expired_count  = 0\n'
    '    adjusted_count = 0\n'
    '    sector_adj_count = 0\n'
    '    rank_changes     = 0\n',
    "Fix2-add-counters",
))

# In the candidate loop, track sector_adj_count and rank_changes
results.append(patch_file(PR,
    '        # 3. Sector bias overlay (Phase F)\n'
    '        adj = sector_bias.get(sector, 0.0)\n'
    '        if adj != 0.0:\n'
    '            # Apply the sector adjustment to volume_ratio (≈ setup attractiveness proxy)\n'
    '            c["volume_ratio"] = round(\n'
    '                max(0.1, min(8.0, c.get("volume_ratio", 1.0) * (1.0 + adj))), 2\n'
    '            )\n'
    '            c["overnight_adjustment"] = round(adj, 3)\n',

    '        # 3. Sector bias overlay (Phase F)\n'
    '        adj = sector_bias.get(sector, 0.0)\n'
    '        _cand_changed = False\n'
    '        if adj != 0.0:\n'
    '            # Apply the sector adjustment to volume_ratio (≈ setup attractiveness proxy)\n'
    '            c["volume_ratio"] = round(\n'
    '                max(0.1, min(8.0, c.get("volume_ratio", 1.0) * (1.0 + adj))), 2\n'
    '            )\n'
    '            c["overnight_adjustment"] = round(adj, 3)\n'
    '            sector_adj_count += 1\n'
    '            _cand_changed = True\n',
    "Fix2-sector-adj-count",
))

# Also track changes from gap/decay
results.append(patch_file(PR,
    '        # 2. Overnight gap adjustment\n'
    '        gap_pct = gap_map.get(sym, 0.0)\n'
    '        if abs(gap_pct) > 0.001:\n'
    '            adjusted_count += 1\n',

    '        # 2. Overnight gap adjustment\n'
    '        gap_pct = gap_map.get(sym, 0.0)\n'
    '        if abs(gap_pct) > 0.001:\n'
    '            adjusted_count += 1\n'
    '            _cand_changed = True\n',
    "Fix2-gap-change-track",
))

# Unfortunately the decay block is before _cand_changed is set. Need to track decay separately.
# Actually _cand_changed is set AFTER gap block (not before). Let me restructure...
# The loop order is: 1. decay, 2. gap, 3. sector bias, 4. valid_until, 5. expiry check
# I need to track changes from all three sources.
# Let me add _cand_changed initialization before step 1 (decay) instead.

results.append(patch_file(PR,
    '        sym    = c.get("symbol", "?")\n'
    '        sector = c.get("sector", "UNKNOWN")\n'
    '\n'
    '        # 1. Conviction decay based on consecutive days in list\n'
    '        streak = streak_counts.get(sym, 1)\n'
    '        if streak > 1:\n',

    '        sym    = c.get("symbol", "?")\n'
    '        sector = c.get("sector", "UNKNOWN")\n'
    '        _cand_changed = False\n'
    '\n'
    '        # 1. Conviction decay based on consecutive days in list\n'
    '        streak = streak_counts.get(sym, 1)\n'
    '        if streak > 1:\n',
    "Fix2-cand-changed-init",
))

# Now remove the extra _cand_changed = False that was inserted inside gap block
# since we moved it to before step 1. But wait, I inserted _cand_changed = False
# in the gap block too. Let me handle this by removing the duplicate...
# Actually looking at my patch above for "Fix2-sector-adj-count", I added:
#   _cand_changed = False
# before `if adj != 0.0:`. But that's in step 3 (sector bias), not step 2 (gap).
# And in "Fix2-gap-change-track" I added `_cand_changed = True` inside the gap block.
# Now in "Fix2-cand-changed-init" I added `_cand_changed = False` before step 1.
# The one added in step 3 (sector bias) section will now be a redundant reset.
# I need to remove the `_cand_changed = False` that's in the sector bias section.

results.append(patch_file(PR,
    '        adj = sector_bias.get(sector, 0.0)\n'
    '        _cand_changed = False\n'
    '        if adj != 0.0:\n',

    '        adj = sector_bias.get(sector, 0.0)\n'
    '        if adj != 0.0:\n',
    "Fix2-remove-dup-init",
))

# Add decay change tracking
results.append(patch_file(PR,
    '        if streak > 1:\n'
    '            decay_days  = streak - 1\n'
    '            # Drift RSI toward 50 (decay of edge)\n'
    '            rsi = c.get("rsi", 50.0)\n'
    '            rsi = rsi + (50.0 - rsi) * (DECAY_RSI_DRIFT / 100.0) * decay_days\n'
    '            c["rsi"] = round(max(0.0, min(100.0, rsi)), 1)\n'
    '            # Decay volume_ratio\n'
    '            vol = c.get("volume_ratio", 1.0)\n'
    '            c["volume_ratio"] = round(max(0.1, vol * (DECAY_VOL_FACTOR ** decay_days)), 2)\n',

    '        if streak > 1:\n'
    '            decay_days  = streak - 1\n'
    '            # Drift RSI toward 50 (decay of edge)\n'
    '            rsi = c.get("rsi", 50.0)\n'
    '            rsi = rsi + (50.0 - rsi) * (DECAY_RSI_DRIFT / 100.0) * decay_days\n'
    '            c["rsi"] = round(max(0.0, min(100.0, rsi)), 1)\n'
    '            # Decay volume_ratio\n'
    '            vol = c.get("volume_ratio", 1.0)\n'
    '            c["volume_ratio"] = round(max(0.1, vol * (DECAY_VOL_FACTOR ** decay_days)), 2)\n'
    '            _cand_changed = True\n',
    "Fix2-decay-change-track",
))

# After the loop, add rank_changes increment (append before refined.append(c))
results.append(patch_file(PR,
    '        # 5. Drop candidates whose valid_until_utc is already past\n'
    '        if _is_expired(valid_until_utc):\n'
    '            expired_count += 1\n'
    '            log.debug("[PremarketRefiner] %s valid_until=%s already expired — dropped.", sym, valid_until_utc)\n'
    '            continue\n'
    '\n'
    '        refined.append(c)\n',

    '        # 5. Drop candidates whose valid_until_utc is already past\n'
    '        if _is_expired(valid_until_utc):\n'
    '            expired_count += 1\n'
    '            log.debug("[PremarketRefiner] %s valid_until=%s already expired — dropped.", sym, valid_until_utc)\n'
    '            continue\n'
    '\n'
    '        if _cand_changed:\n'
    '            rank_changes += 1\n'
    '        refined.append(c)\n',
    "Fix2-rank-changes-count",
))

# Add effectiveness + noop audit AFTER the existing log.info/success lines
results.append(patch_file(PR,
    '    # ── Write back to candidate store ────────────────────────────────────────\n'
    '    complete = (len(refined) + expired_count) >= len(candidates)\n'
    '    success  = CandidateStore.update_premarket(refined, complete=complete)\n'
    '\n'
    '    duration = time.monotonic() - start\n'
    '    if success:\n'
    '        log.info("[PremarketRefiner] Complete in %.1fs. premarket_refresh_complete=%s",\n'
    '                 duration, complete)\n'
    '    else:\n'
    '        log.error("[PremarketRefiner] Failed to write updated candidates.")\n',

    '    # ── Write back to candidate store ────────────────────────────────────────\n'
    '    complete = (len(refined) + expired_count) >= len(candidates)\n'
    '    success  = CandidateStore.update_premarket(refined, complete=complete)\n'
    '\n'
    '    duration = time.monotonic() - start\n'
    '    if success:\n'
    '        log.info("[PremarketRefiner] Complete in %.1fs. premarket_refresh_complete=%s",\n'
    '                 duration, complete)\n'
    '    else:\n'
    '        log.error("[PremarketRefiner] Failed to write updated candidates.")\n'
    '\n'
    '    # Fix 2 — PremarketRefinerEffectiveness telemetry\n'
    '    log.info(\n'
    '        "[PremarketRefinerEffectiveness] input_candidates=%d output_candidates=%d "\n'
    '        "rank_changes=%d additions=0 removals=%d sector_adjustments=%d "\n'
    '        "gap_adjustments=%d runtime_ms=%.0f sector_bias_available=%s",\n'
    '        len(candidates), len(refined),\n'
    '        rank_changes, expired_count, sector_adj_count,\n'
    '        adjusted_count, duration * 1000, _bias_avail,\n'
    '    )\n'
    '\n'
    '    # Fix 4 — RefinerNoOpAudit: emit when no real changes applied\n'
    '    _noop_reasons = []\n'
    '    if not _bias_avail:\n'
    '        _noop_reasons.append("SECTOR_BIAS_UNAVAILABLE")\n'
    '    if not gap_map:\n'
    '        _noop_reasons.append("NO_GAP_DATA")\n'
    '    if not _noop_reasons and rank_changes == 0:\n'
    '        _noop_reasons.append("NO_REFINEMENT_REQUIRED")\n'
    '    if rank_changes == 0 and _noop_reasons:\n'
    '        log.info(\n'
    '            "[RefinerNoOpAudit] candidate_count=%d changes_detected=%d reason=%s",\n'
    '            len(candidates), rank_changes, ",".join(_noop_reasons),\n'
    '        )\n',
    "Fix2+4-effectiveness+noop",
))

# ─── FIX 3: Scanner stats persistence — market_scanner.py ────────────────────
MS = "/app/opportunity_engine/market_scanner.py"

results.append(patch_file(MS,
    '    scanner_stats = {\n'
    '        "symbols_attempted":  attempted,\n'
    '        "symbols_successful": len(processed),\n'
    '        "symbols_failed":     failed_count,\n'
    '        "coverage_pct":       round(coverage, 1),\n'
    '        "scan_duration_min":  round((time.monotonic() - scan_start) / 60.0, 2),\n'
    '        "candidates_before_sector_cap": len(processed),\n'
    '        "candidates_after_sector_cap":  len(candidates),\n'
    '    }\n',

    '    scanner_stats = {\n'
    '        "symbols_attempted":  attempted,\n'
    '        "symbols_successful": len(processed),\n'
    '        "symbols_failed":     failed_count,\n'
    '        "coverage_pct":       round(coverage, 1),\n'
    '        "scan_duration_min":  round((time.monotonic() - scan_start) / 60.0, 2),\n'
    '        "candidates_before_sector_cap": len(processed),\n'
    '        "candidates_after_sector_cap":  _before_floor,\n'
    '        "candidates_written":           len(candidates),\n'
    '        "sector_cap_removed":           len(processed) - _before_floor,\n'
    '        "score_floor_removed":          _before_floor - len(candidates),\n'
    '    }\n',
    "Fix3-scanner-stats",
))

# Emit ScannerStatsPersistenceAudit after CandidateStore.write returns
results.append(patch_file(MS,
    '    _total_sec = time.monotonic() - scan_start\n'
    '    if success:\n'
    '        log.info(\n'
    '            "[ScannerRun] Complete. candidates=%d coverage=%.1f%% duration=%.1fmin",\n'
    '            len(candidates), coverage, _total_sec / 60.0,\n'
    '        )\n',

    '    _total_sec = time.monotonic() - scan_start\n'
    '    if success:\n'
    '        log.info(\n'
    '            "[ScannerRun] Complete. candidates=%d coverage=%.1f%% duration=%.1fmin",\n'
    '            len(candidates), coverage, _total_sec / 60.0,\n'
    '        )\n'
    '        # Fix 3 — ScannerStatsPersistenceAudit\n'
    '        log.info(\n'
    '            "[ScannerStatsPersistenceAudit] candidates_written=%d sector_cap_removed=%d "\n'
    '            "score_floor_removed=%d after_sector_cap=%d coverage_pct=%.1f",\n'
    '            len(candidates),\n'
    '            len(processed) - _before_floor,\n'
    '            _before_floor - len(candidates),\n'
    '            _before_floor,\n'
    '            coverage,\n'
    '        )\n',
    "Fix3-persistence-audit",
))

# ─── FIX 5: ExecutionFreshnessSummary — equity_scanner_ai.py ─────────────────
ES = "/app/opportunity_engine/equity_scanner_ai.py"

results.append(patch_file(ES,
    '        # Patch 1 — update stats for health heartbeat\n'
    '        _LAST_PREPARED_STATS = {\n'
    '            "prepared_count":    len(rows),\n'
    '            "expired_count":     expired_count,\n'
    '            "invalidated_count": _invalidated_count,   # V2\n'
    '            "fallback_used":     False,\n'
    '            "reason":            "OK",\n'
    '            "fallback_sessions":  0,\n'
    '        }\n'
    '        return rows\n',

    '        # Patch 1 — update stats for health heartbeat\n'
    '        _LAST_PREPARED_STATS = {\n'
    '            "prepared_count":    len(rows),\n'
    '            "expired_count":     expired_count,\n'
    '            "invalidated_count": _invalidated_count,   # V2\n'
    '            "fallback_used":     False,\n'
    '            "reason":            "OK",\n'
    '            "fallback_sessions":  0,\n'
    '        }\n'
    '\n'
    '        # Fix 5 — ExecutionFreshnessSummary\n'
    '        try:\n'
    '            from datetime import datetime as _dtt, timezone as _tz\n'
    '            _now_utc = _dtt.now(_tz.utc)\n'
    '            _ages_min = []\n'
    '            for _fr in rows:\n'
    '                _pa = _fr.get("prepared_at")\n'
    '                if _pa:\n'
    '                    try:\n'
    '                        _pt = _dtt.fromisoformat(_pa.replace("Z", "+00:00"))\n'
    '                        _ages_min.append((_now_utc - _pt).total_seconds() / 60.0)\n'
    '                    except Exception:\n'
    '                        pass\n'
    '            _oldest = round(max(_ages_min), 1) if _ages_min else None\n'
    '            _avg    = round(sum(_ages_min) / len(_ages_min), 1) if _ages_min else None\n'
    '            log.info(\n'
    '                "[ExecutionFreshnessSummary] fresh=%d expired=%d ttl_rejected=%d "\n'
    '                "invalidated=%d oldest_candidate_minutes=%s avg_candidate_age_minutes=%s",\n'
    '                len(rows), expired_count, expired_count, _invalidated_count,\n'
    '                _oldest if _oldest is not None else "N/A",\n'
    '                _avg if _avg is not None else "N/A",\n'
    '            )\n'
    '        except Exception as _efs_e:\n'
    '            log.debug("[ExecutionFreshnessSummary] failed: %s", _efs_e)\n'
    '\n'
    '        return rows\n',
    "Fix5-freshness-summary",
))

# ─── FIX 6: DeltaRefreshShadowSummary — delta_refresh_shadow.py ──────────────
DS = "/app/opportunity_engine/delta_refresh_shadow.py"

results.append(patch_file(DS,
    '    # Ranking stability\n'
    '    log.info(\n'
    '        "[RankingStability] cycle=%s candidate_rank_flip_count=%d "\n'
    '        "top5_stability=%.0f%% top10_churn_rate=%.1f%% "\n'
    '        "rerank_noise_score=%.1f",\n'
    '        cycle_label,\n'
    '        top5_flip_count,\n'
    '        top5_stability,\n'
    '        top10_churn * 100.0,\n'
    '        oscillation_risk,\n'
    '    )\n',

    '    # Ranking stability\n'
    '    log.info(\n'
    '        "[RankingStability] cycle=%s candidate_rank_flip_count=%d "\n'
    '        "top5_stability=%.0f%% top10_churn_rate=%.1f%% "\n'
    '        "rerank_noise_score=%.1f",\n'
    '        cycle_label,\n'
    '        top5_flip_count,\n'
    '        top5_stability,\n'
    '        top10_churn * 100.0,\n'
    '        oscillation_risk,\n'
    '    )\n'
    '\n'
    '    # Fix 6 — DeltaRefreshShadowSummary consolidated one-liner\n'
    '    log.info(\n'
    '        "[DeltaRefreshShadowSummary] cycle=%s rank_flip_count=%d "\n'
    '        "top5_stability=%.0f%% top10_churn=%.1f%% avg_rsi_delta=%.2f "\n'
    '        "stale_candidate_count=%d false_stale_count=%d runtime_ms=%.1f",\n'
    '        cycle_label,\n'
    '        top5_flip_count,\n'
    '        top5_stability,\n'
    '        top10_churn * 100.0,\n'
    '        avg_rsi_delta,\n'
    '        len(stale_syms),\n'
    '        len(hypothetical_invalidations),\n'
    '        runtime_ms,\n'
    '    )\n',
    "Fix6-shadow-summary",
))

# ── Summary ──
ok = sum(1 for r in results if r)
fail = sum(1 for r in results if not r)
print(f"\nPatches applied: {ok} OK, {fail} FAILED")
if fail:
    sys.exit(1)

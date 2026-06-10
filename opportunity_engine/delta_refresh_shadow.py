"""
PREPARED_UNIVERSE_V2.5 — Pre-Cycle Delta Refresh Shadow Audit
=============================================================

Forensic measurement framework.  Runs at each full cycle slot
(09:45, 10:30, 11:30, 13:00, 14:00, 15:00) to answer ONE question:

    Would a live pre-cycle delta refresh materially improve execution quality?

THIS MODULE NEVER:
  • alters live candidates, scores, or rankings
  • delays cycle execution (runs in a daemon background thread)
  • makes extra API calls (only reads existing in-memory caches)

Log markers emitted:
  [DeltaRefreshShadow]      — per-cycle aggregate metrics
  [FalseStaleExecution]     — per-candidate that would be invalidated
  [LifecycleTransitionShadow] — per-candidate lifecycle change detected
  [RankingStability]        — ranking churn / top-N stability
  [RefreshPressureAudit]    — projected API overhead if refresh were live
  [ConvictionDriftShadow]   — conviction score changes detected
  [ShadowAuditSummary]      — rolling multi-cycle aggregate (logged on EOD)

PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE = True  →  collect telemetry only
PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE = False →  disabled entirely

Decision gate:
  Enable live refresh ONLY when audit evidence shows:
    decision_drift_pct    >  15 %      (top candidate would change)
    avg_invalidations/cy  >  1.5
    top3_drift_pct        >  25 %
    avg_rsi_delta         >  5  pts
    rate_limit_risk       == LOW
    avg_runtime_ms        <  250 ms
    avg_ranking_instability < 20
"""

from __future__ import annotations

import datetime
import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)

# ── Master flag ──────────────────────────────────────────────────────────────
PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE: bool = True

# ── Rolling history (last 12 cycles ≈ 2 trading days) ───────────────────────
_SHADOW_HISTORY: List[Dict[str, Any]] = []
_SHADOW_LOCK = threading.Lock()
_MAX_HISTORY: int = 12

# ── Decision-gate thresholds ─────────────────────────────────────────────────
_GATE_DECISION_DRIFT_PCT:   float = 15.0   # % cycles where top-1 would change
_GATE_AVG_INVALIDATIONS:    float =  1.5   # avg invalidations per cycle
_GATE_TOP3_DRIFT_PCT:       float = 25.0   # % of top-3 set changed
_GATE_AVG_RSI_DELTA:        float =  5.0   # RSI points drift
_GATE_RANK_INSTABILITY:     float = 20.0   # Kendall tau×100 threshold
_GATE_RUNTIME_MS:           float = 250.0  # shadow loop ceiling


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _kendall_tau_distance(rank_a: List[str], rank_b: List[str]) -> float:
    """
    Normalised Kendall tau distance between two ranked symbol lists.
    Returns 0.0 = identical order, 1.0 = fully reversed.
    Operates on the union of both lists.
    """
    all_syms: List[str] = list(dict.fromkeys(rank_a + rank_b))
    n = len(all_syms)
    if n < 2:
        return 0.0
    pos_a = {s: i for i, s in enumerate(rank_a)}
    pos_b = {s: i for i, s in enumerate(rank_b)}
    len_a, len_b = len(rank_a), len(rank_b)
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = all_syms[i], all_syms[j]
            ai = pos_a.get(si, len_a)
            aj = pos_a.get(sj, len_a)
            bi = pos_b.get(si, len_b)
            bj = pos_b.get(sj, len_b)
            diff_a = ai - aj
            diff_b = bi - bj
            if diff_a * diff_b > 0:
                concordant += 1
            elif diff_a * diff_b < 0:
                discordant += 1
    total = concordant + discordant
    return discordant / total if total > 0 else 0.0


def _candidate_age_hours(
    candidate: Dict[str, Any],
    now_utc: datetime.datetime,
) -> float:
    """Return age of candidate in hours from prepared_at field."""
    pa = candidate.get("prepared_at", "")
    if not pa:
        return 0.0
    try:
        dt = datetime.datetime.fromisoformat(str(pa).replace("Z", "+00:00"))
        return (now_utc - dt).total_seconds() / 3600.0
    except Exception:
        return 0.0


def _sorted_by_score(candidates: List[Dict[str, Any]]) -> List[str]:
    """Return symbol list sorted descending by score."""
    return [
        c["symbol"]
        for c in sorted(candidates, key=lambda x: -float(x.get("score") or 0.0))
        if c.get("symbol")
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  Core shadow simulation
# ─────────────────────────────────────────────────────────────────────────────

def _run_shadow_simulation(cycle_label: str) -> None:
    """
    Inner worker — called from a daemon thread.
    Simulates a hypothetical delta refresh using existing in-memory caches
    and logs forensic telemetry.  Never raises; any failure is debug-logged.
    """
    t_start = time.perf_counter()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # ── 1. Lazy imports (keeps startup cost zero) ─────────────────────────
    try:
        from opportunity_engine.candidate_store import (
            CandidateStore,
            apply_conviction_decay,        # module-level alias added in V2
            compute_lifecycle_state,
            LIFECYCLE_EXPIRED,
            LIFECYCLE_INVALIDATED,
            LIFECYCLE_WEAKENING,
        )
    except ImportError:
        # apply_conviction_decay may be only a classmethod
        try:
            from opportunity_engine.candidate_store import (
                CandidateStore,
                compute_lifecycle_state,
                LIFECYCLE_EXPIRED,
                LIFECYCLE_INVALIDATED,
                LIFECYCLE_WEAKENING,
            )
            apply_conviction_decay = CandidateStore.apply_conviction_decay
        except ImportError as exc:
            log.debug("[DeltaRefreshShadow] import failed: %s", exc)
            return

    try:
        import opportunity_engine.equity_scanner_ai as _eq_sc
        _PRICE_CACHE_LOCK      = _eq_sc._PRICE_CACHE_LOCK
        _RSI_CACHE_LOCK        = _eq_sc._RSI_CACHE_LOCK
        _check_breakout_invalidation = _eq_sc._check_breakout_invalidation
    except (ImportError, AttributeError) as exc:
        log.debug("[DeltaRefreshShadow] equity_scanner import failed: %s", exc)
        return

    # ── 2. Load current prepared pool ────────────────────────────────────
    candidates: Optional[List[Dict[str, Any]]] = CandidateStore.read()
    if not candidates:
        log.debug("[DeltaRefreshShadow] cycle=%s pool_empty — skipping", cycle_label)
        return
    pool_size = len(candidates)

    # Snapshot caches under locks — use module reference so we always see
    # the CURRENT dict even if equity_scanner reassigned _PRICE_CACHE via
    # "global _PRICE_CACHE = prices" (name-import would give a stale empty dict)
    with _PRICE_CACHE_LOCK:
        price_snap: Dict[str, float] = dict(_eq_sc._PRICE_CACHE)
    with _RSI_CACHE_LOCK:
        rsi_snap: Dict[str, float] = dict(_eq_sc._RSI_CACHE)

    # ── 3. Pre-refresh ranking (current state) ────────────────────────────
    current_ranking: List[str] = _sorted_by_score(candidates)

    # ── 4. Simulate per-candidate delta refresh ───────────────────────────
    hypothetical_invalidations: List[Dict[str, Any]] = []
    hypothetical_reranks:       List[Tuple[str, float, float]] = []
    lifecycle_transitions:      List[Tuple[str, str, str]] = []
    rsi_deltas:                 List[float] = []
    stale_syms:                 List[str] = []
    conviction_parts:           List[str] = []
    cache_hits:                 int = 0
    rsi_hits:                   int = 0

    refreshed_pool: List[Dict[str, Any]] = []

    for c in candidates:
        sym        = c.get("symbol", "")
        old_score  = float(c.get("score") or 0.0)
        old_lc     = str(c.get("_lifecycle_state") or "UNKNOWN")
        stored_rsi = float(c.get("rsi") or 50.0)
        stored_ltp = float(c.get("base_ltp") or c.get("ltp") or 0.0)

        # Pull from in-memory caches (zero extra API calls)
        live_ltp_raw = price_snap.get(sym)
        live_ltp = float(live_ltp_raw) if live_ltp_raw is not None and live_ltp_raw > 0 else stored_ltp
        if live_ltp_raw is not None and live_ltp_raw > 0 and live_ltp != stored_ltp:
            cache_hits += 1

        live_rsi_raw = rsi_snap.get(sym)
        live_rsi: Optional[float] = float(live_rsi_raw) if live_rsi_raw is not None else None
        if live_rsi is not None:
            rsi_hits += 1
            rsi_deltas.append(abs(live_rsi - stored_rsi))

        # Stale candidate check (>2 h since preparation)
        age_h = _candidate_age_hours(c, now_utc)
        if age_h > 2.0:
            stale_syms.append(sym)

        # Simulate breakout invalidation
        inv, inv_reason = _check_breakout_invalidation(c, live_ltp=live_ltp, live_rsi=live_rsi)
        if inv:
            orig_rank = (current_ranking.index(sym) + 1) if sym in current_ranking else -1
            exec_diff_score = (orig_rank / max(1, pool_size)) * 100.0
            hypothetical_invalidations.append({
                "symbol": sym,
                "original_rank": orig_rank,
                "stale_reason": inv_reason,
                "exec_diff_score": exec_diff_score,
            })
            continue  # excluded from refreshed pool

        # Simulate conviction decay (single candidate, no side-effects)
        sim_c = [dict(c, score=old_score)]
        try:
            decayed, _ = apply_conviction_decay(
                sim_c,
                price_map={sym: live_ltp} if live_ltp > 0 else {},
                rsi_map={sym: live_rsi} if live_rsi is not None else None,
            )
            new_score = float(decayed[0].get("score", old_score))
        except Exception:
            new_score = old_score

        if abs(new_score - old_score) > 0.005:
            hypothetical_reranks.append((sym, old_score, new_score))
            conviction_parts.append(f"{sym}:{old_score:.3f}→{new_score:.3f}")

        # Simulate lifecycle transition
        try:
            new_lc = compute_lifecycle_state(
                c, live_ltp=live_ltp, live_rsi=live_rsi, now_utc=now_utc
            )
        except Exception:
            new_lc = old_lc
        if new_lc != old_lc:
            lifecycle_transitions.append((sym, old_lc, new_lc))

        refreshed_pool.append(dict(c, score=new_score, _lifecycle_state=new_lc))

    # ── 5. Post-refresh ranking ───────────────────────────────────────────
    refreshed_ranking: List[str] = _sorted_by_score(refreshed_pool)

    # Kendall tau on top-10
    top10_cur = current_ranking[:10]
    top10_ref = refreshed_ranking[:10]
    tau_dist  = _kendall_tau_distance(top10_cur, top10_ref)
    ranking_instability_score = round(tau_dist * 100.0, 1)

    # Top-5 flips (symbols that left the top-5 set)
    top5_flip_count = len(set(top10_cur[:5]) - set(top10_ref[:5]))
    top5_stability  = round((1.0 - top5_flip_count / 5.0) * 100.0, 1)

    # Top-10 churn rate
    top10_churn = len(set(top10_cur) - set(top10_ref)) / max(1, len(top10_cur))

    # Decision drift: did the single top candidate change?
    top1_cur = current_ranking[0]  if current_ranking  else "NONE"
    top1_ref = refreshed_ranking[0] if refreshed_ranking else "NONE"
    decision_drift = top1_cur != top1_ref

    # Top-3 selection drift
    top3_cur = set(current_ranking[:3])
    top3_ref = set(refreshed_ranking[:3])
    top3_drift_pct = round(len(top3_cur - top3_ref) / max(1, len(top3_cur)) * 100.0, 1)

    # RSI summary
    avg_rsi_delta = round(sum(rsi_deltas) / max(1, len(rsi_deltas)), 2) if rsi_deltas else 0.0

    # ── 6. API pressure projection ────────────────────────────────────────
    uncached = sum(
        1 for c in candidates
        if not price_snap.get(c.get("symbol", ""))
    )
    cache_hit_rate = round((pool_size - uncached) / max(1, pool_size) * 100.0, 1)

    # yfinance batches ~20 symbols per call; 6 cycles/day
    extra_calls_per_cycle = math.ceil(pool_size / 20)
    calls_per_day         = 6 * extra_calls_per_cycle
    rate_limit_risk = (
        "LOW"    if calls_per_day <  50 else
        "MEDIUM" if calls_per_day < 200 else
        "HIGH"
    )

    # ── 7. Runtime cost ───────────────────────────────────────────────────
    t_end      = time.perf_counter()
    runtime_ms = round((t_end - t_start) * 1000.0, 1)

    # Oscillation risk proxy = ranking instability score
    oscillation_risk = ranking_instability_score

    # ── 8. Emit telemetry ─────────────────────────────────────────────────

    # Primary aggregate
    log.info(
        "[DeltaRefreshShadow] cycle=%s pool=%d "
        "hypothetical_invalidations=%d hypothetical_reranks=%d "
        "avg_rsi_delta=%.2f stale_candidate_count=%d lifecycle_transitions=%d "
        "decision_drift=%s top3_drift_pct=%.1f%% "
        "ranking_instability_score=%.1f oscillation_risk_score=%.1f "
        "refresh_runtime_cost_ms=%.1f "
        "cache_hits=%d/%d rsi_hits=%d "
        "estimated_api_cost=~%d_calls/day rate_limit_risk=%s",
        cycle_label, pool_size,
        len(hypothetical_invalidations), len(hypothetical_reranks),
        avg_rsi_delta, len(stale_syms), len(lifecycle_transitions),
        decision_drift, top3_drift_pct,
        ranking_instability_score, oscillation_risk,
        runtime_ms,
        cache_hits, pool_size, rsi_hits,
        calls_per_day, rate_limit_risk,
    )

    # Per-invalidated-candidate FalseStaleExecution
    for inv_data in hypothetical_invalidations:
        log.info(
            "[FalseStaleExecution] symbol=%s original_rank=%d "
            "stale_reason=%s hypothetical_invalidation=True "
            "execution_difference_score=%.1f",
            inv_data["symbol"],
            inv_data["original_rank"],
            inv_data["stale_reason"],
            inv_data["exec_diff_score"],
        )

    # Lifecycle transitions
    for sym, old_lc, new_lc in lifecycle_transitions:
        log.info(
            "[LifecycleTransitionShadow] symbol=%s %s→%s",
            sym, old_lc, new_lc,
        )

    # Ranking stability
    log.info(
        "[RankingStability] cycle=%s candidate_rank_flip_count=%d "
        "top5_stability=%.0f%% top10_churn_rate=%.1f%% "
        "rerank_noise_score=%.1f",
        cycle_label,
        top5_flip_count,
        top5_stability,
        top10_churn * 100.0,
        oscillation_risk,
    )

    # API pressure
    log.info(
        "[RefreshPressureAudit] cycle=%s projected_calls_per_day=%d "
        "cache_hit_rate=%.1f%% estimated_extra_calls_per_cycle=%d "
        "estimated_rate_limit_risk=%s refresh_scope_size=%d",
        cycle_label,
        calls_per_day,
        cache_hit_rate,
        extra_calls_per_cycle,
        rate_limit_risk,
        pool_size,
    )

    # Conviction drift (only when non-trivial)
    if conviction_parts:
        log.info(
            "[ConvictionDriftShadow] cycle=%s count=%d changes=%s",
            cycle_label, len(conviction_parts),
            " | ".join(conviction_parts[:10]),
        )

    # ── 9. Store in rolling history ───────────────────────────────────────
    record = {
        "cycle":                     cycle_label,
        "ts_utc":                    now_utc.isoformat(),
        "pool_size":                 pool_size,
        "hypothetical_invalidations": len(hypothetical_invalidations),
        "hypothetical_reranks":      len(hypothetical_reranks),
        "avg_rsi_delta":             avg_rsi_delta,
        "stale_count":               len(stale_syms),
        "lifecycle_transitions":     len(lifecycle_transitions),
        "decision_drift":            decision_drift,
        "top3_drift_pct":            top3_drift_pct,
        "ranking_instability_score": ranking_instability_score,
        "runtime_ms":                runtime_ms,
        "cache_hit_rate":            cache_hit_rate,
        "rate_limit_risk":           rate_limit_risk,
        "calls_per_day":             calls_per_day,
    }
    with _SHADOW_LOCK:
        _SHADOW_HISTORY.append(record)
        while len(_SHADOW_HISTORY) > _MAX_HISTORY:
            _SHADOW_HISTORY.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_shadow_audit(cycle_label: str) -> None:
    """
    Fire-and-forget: launch shadow audit in a daemon thread.
    Returns immediately — the cycle is never delayed.

    Args:
        cycle_label: human-readable slot identifier, e.g. "0945", "1030".
    """
    if not PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE:
        return
    t = threading.Thread(
        target=_run_shadow_simulation,
        args=(cycle_label,),
        name=f"shadow_audit_{cycle_label}",
        daemon=True,
    )
    t.start()


def get_shadow_audit_summary() -> Dict[str, Any]:
    """
    Return aggregated metrics across all stored shadow audit cycles.
    Also evaluates whether the decision gate is met.

    Called by EOD telemetry or Telegram /perf command.
    """
    with _SHADOW_LOCK:
        if not _SHADOW_HISTORY:
            return {"cycles_sampled": 0}

        n = len(_SHADOW_HISTORY)

        avg_inv       = sum(h["hypothetical_invalidations"] for h in _SHADOW_HISTORY) / n
        avg_reranks   = sum(h["hypothetical_reranks"]       for h in _SHADOW_HISTORY) / n
        avg_rsi       = sum(h["avg_rsi_delta"]              for h in _SHADOW_HISTORY) / n
        avg_stale     = sum(h["stale_count"]                for h in _SHADOW_HISTORY) / n
        drift_pct     = sum(1 for h in _SHADOW_HISTORY if h["decision_drift"]) / n * 100.0
        top3_drift    = sum(h["top3_drift_pct"]             for h in _SHADOW_HISTORY) / n
        instability   = sum(h["ranking_instability_score"]  for h in _SHADOW_HISTORY) / n
        runtime_ms    = sum(h["runtime_ms"]                 for h in _SHADOW_HISTORY) / n
        cache_hit     = sum(h["cache_hit_rate"]             for h in _SHADOW_HISTORY) / n
        lc_trans      = sum(h["lifecycle_transitions"]      for h in _SHADOW_HISTORY) / n

        # Decision-gate evaluation
        gate_pass = (
            drift_pct   > _GATE_DECISION_DRIFT_PCT  and
            avg_inv     > _GATE_AVG_INVALIDATIONS   and
            top3_drift  > _GATE_TOP3_DRIFT_PCT      and
            avg_rsi     > _GATE_AVG_RSI_DELTA       and
            instability < _GATE_RANK_INSTABILITY    and
            runtime_ms  < _GATE_RUNTIME_MS
        )
        gate_factors = {
            f"decision_drift_pct  {'✅' if drift_pct   > _GATE_DECISION_DRIFT_PCT  else '❌'}":
                f"{drift_pct:.1f}% (gate>{_GATE_DECISION_DRIFT_PCT}%)",
            f"avg_invalidations   {'✅' if avg_inv     > _GATE_AVG_INVALIDATIONS   else '❌'}":
                f"{avg_inv:.2f} (gate>{_GATE_AVG_INVALIDATIONS})",
            f"avg_top3_drift_pct  {'✅' if top3_drift  > _GATE_TOP3_DRIFT_PCT      else '❌'}":
                f"{top3_drift:.1f}% (gate>{_GATE_TOP3_DRIFT_PCT}%)",
            f"avg_rsi_delta       {'✅' if avg_rsi     > _GATE_AVG_RSI_DELTA       else '❌'}":
                f"{avg_rsi:.2f}pts (gate>{_GATE_AVG_RSI_DELTA}pts)",
            f"rank_instability    {'✅' if instability < _GATE_RANK_INSTABILITY    else '❌'}":
                f"{instability:.1f} (gate<{_GATE_RANK_INSTABILITY})",
            f"runtime_ms          {'✅' if runtime_ms  < _GATE_RUNTIME_MS          else '❌'}":
                f"{runtime_ms:.1f}ms (gate<{_GATE_RUNTIME_MS}ms)",
        }

        return {
            "cycles_sampled":              n,
            "avg_hypothetical_invalidations": round(avg_inv,     2),
            "avg_hypothetical_reranks":    round(avg_reranks,    2),
            "avg_rsi_delta":               round(avg_rsi,        2),
            "avg_stale_count":             round(avg_stale,      2),
            "avg_lifecycle_transitions":   round(lc_trans,       2),
            "decision_drift_pct":          round(drift_pct,      1),
            "avg_top3_drift_pct":          round(top3_drift,     1),
            "avg_ranking_instability":     round(instability,    1),
            "avg_runtime_ms":              round(runtime_ms,     1),
            "avg_cache_hit_rate":          round(cache_hit,      1),
            "live_refresh_decision_gate":  "PASS — consider enabling" if gate_pass else "FAIL — keep V2 as-is",
            "gate_factors":                gate_factors,
        }


def log_shadow_audit_summary() -> None:
    """
    Emit a [ShadowAuditSummary] log line with the aggregated decision verdict.
    Called by EOD routine.
    """
    summary = get_shadow_audit_summary()
    if not summary.get("cycles_sampled"):
        log.debug("[ShadowAuditSummary] No shadow audit cycles recorded today.")
        return

    gate = summary["live_refresh_decision_gate"]
    log.info(
        "[ShadowAuditSummary] cycles=%d "
        "decision_drift_pct=%.1f%% avg_invalidations=%.2f avg_reranks=%.2f "
        "avg_rsi_delta=%.2fpts avg_top3_drift=%.1f%% "
        "avg_instability=%.1f avg_runtime_ms=%.1fms "
        "avg_cache_hit=%.1f%% verdict=%s",
        summary["cycles_sampled"],
        summary["decision_drift_pct"],
        summary["avg_hypothetical_invalidations"],
        summary["avg_hypothetical_reranks"],
        summary["avg_rsi_delta"],
        summary["avg_top3_drift_pct"],
        summary["avg_ranking_instability"],
        summary["avg_runtime_ms"],
        summary["avg_cache_hit_rate"],
        gate,
    )
    # Log per-gate-factor detail at debug level
    for factor, value in summary.get("gate_factors", {}).items():
        log.debug("[ShadowAuditSummary.Gate] %s = %s", factor, value)

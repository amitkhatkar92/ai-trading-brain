"""
opportunity_engine/klp_evaluator.py
=====================================
Knowledge-Led Path (KLP) Evaluator  —  KLP-001

PURPOSE
-------
Independently evaluates every scan-qualified signal BEFORE StrategyLab
to build a research-only parallel decision layer.

For each trading cycle the evaluator:
  1. Receives all signals from EquityScannerAI.scan()
  2. Computes KNOWLEDGE_RESEARCH_SCORE_v1 per signal (no look-ahead)
  3. Ranks signals by that score across the full cycle
  4. Marks the top-5 as "knowledge_selected"
  5. Writes KNOWLEDGE_OBSERVATION records (append-only JSONL)

After StrategyLab completes, the orchestrator calls annotate_strategy_outcome():
  6. Determines per-symbol strategy approval / rejection
  7. Computes structural strategy context (regime-based, via final_c2_selector)
  8. Computes KLP-vs-Strategy disagreement label
  9. Writes STRATEGY_ANNOTATION records (append-only JSONL)

OUTPUT
------
  data/klp/KLP_YYYY-MM-DD.jsonl   — two event types per signal per cycle:
    event_type = "KNOWLEDGE_OBSERVATION"  — written before StrategyLab
    event_type = "STRATEGY_ANNOTATION"   — written after  StrategyLab

CONTRACT
--------
• Never raises — all public methods swallow every exception.
• Never modifies any TradeSignal or any shared pipeline object.
• No broker calls, no orders, no CandidateStore writes.
• All score components use only scan-time data — no future price data.
• Dedup: one KNOWLEDGE_OBSERVATION per symbol per trading day per session.
• Files are append-only and created on first write.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from utils import get_logger

log = get_logger(__name__)

# ── Output directory (overridable for tests via KLPEvaluator(data_dir=...)) ──
_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "klp"

# ── Score component weights (must sum to 1.0) ────────────────────────────────
_W_CANDIDATE_SCORE = 0.40
_W_CONFIDENCE      = 0.25
_W_EXPECTED_MOVE   = 0.15
_W_RISK_REWARD     = 0.10
_W_REGIME_ALIGN    = 0.10

# ── Knowledge selection: top-N candidates per cycle ──────────────────────────
KNOWLEDGE_TOP_N = 5

# ── Regime alignment lookup (scanner regime_label → direction → alignment score) ─
_REGIME_ALIGN_TABLE: Dict[str, Dict[str, float]] = {
    "bull_trend":    {"BUY": 1.0, "SELL": 0.2, "SHORT": 0.2, "HEDGE": 0.5, "EXIT": 0.5},
    "bull_market":   {"BUY": 0.9, "SELL": 0.3, "SHORT": 0.3, "HEDGE": 0.5, "EXIT": 0.5},
    "range_market":  {"BUY": 0.7, "SELL": 0.7, "SHORT": 0.7, "HEDGE": 0.6, "EXIT": 0.6},
    "bear_market":   {"BUY": 0.2, "SELL": 0.9, "SHORT": 0.9, "HEDGE": 0.7, "EXIT": 0.7},
    "volatile":      {"BUY": 0.4, "SELL": 0.4, "SHORT": 0.4, "HEDGE": 0.8, "EXIT": 0.8},
}

# ── Scanner regime label → evaluate_strategy_context() regime argument ────────
_REGIME_TO_CTX: Dict[str, str] = {
    "bull_trend":   "BULL",
    "bull_market":  "BULL",
    "range_market": "RANGE",
    "bear_market":  "BEAR",
    "volatile":     "VOLATILE",
}

# ── Disagreement labels ───────────────────────────────────────────────────────
AGREE_PASS                  = "AGREE_PASS"
AGREE_REJECT                = "AGREE_REJECT"
KNOWLEDGE_OVERRULES         = "KNOWLEDGE_OVERRULES"
STRATEGY_OVERRULES          = "STRATEGY_OVERRULES"
STRUCTURAL_OVERRIDE         = "STRUCTURAL_OVERRIDE"

# ── Module-level lock (protects singleton creation only) ─────────────────────
_SINGLETON_LOCK = threading.Lock()
_EVALUATOR_INSTANCE: Optional["KLPEvaluator"] = None


def get_klp_evaluator() -> "KLPEvaluator":
    """Return the session-scoped singleton KLPEvaluator."""
    global _EVALUATOR_INSTANCE
    with _SINGLETON_LOCK:
        if _EVALUATOR_INSTANCE is None:
            _EVALUATOR_INSTANCE = KLPEvaluator()
    return _EVALUATOR_INSTANCE


class KLPEvaluator:
    """
    Session-scoped Knowledge-Led Path evaluator.

    Create a fresh instance in tests by passing data_dir to the constructor.
    Use get_klp_evaluator() in production for the process-scoped singleton.

    Usage (in orchestrator):
        evaluator = get_klp_evaluator()
        evaluator.evaluate_and_record(signals, snapshot)               # before StrategyLab
        evaluator.annotate_strategy_outcome(signals, approved, ...)    # after StrategyLab
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir    = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
        self._seen_obs: Set[str]              = set()   # "<symbol>|<date>" dedup keys
        self._session_obs: Dict[str, Dict[str, Any]] = {}  # obs_id → record (for annotation)
        self._obs_lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate_and_record(
        self,
        signals: List[Any],
        snapshot: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        Score, rank, and write KNOWLEDGE_OBSERVATION records for all signals.

        Called BEFORE StrategyLab.  Never raises.

        Returns the list of observation dicts (for diagnostics/testing — the
        trading pipeline does NOT consume this return value).
        """
        try:
            return self._evaluate_impl(signals, snapshot)
        except Exception as _exc:
            log.warning("[KLP-001] evaluate_and_record error: %s", _exc)
            return []

    def annotate_strategy_outcome(
        self,
        original_signals: List[Any],
        approved_symbols: Set[str],
        rejected_reasons: Optional[Dict[str, str]] = None,
        snapshot: Any = None,
    ) -> None:
        """
        Write STRATEGY_ANNOTATION records for all original signals.

        Called AFTER StrategyLab.  Never raises.

        Parameters
        ----------
        original_signals : signals from EquityScannerAI.scan() (pre-StrategyLab)
        approved_symbols : set of symbol strings that passed StrategyLab
        rejected_reasons : optional {symbol: rejection_reason_str} mapping
        snapshot         : MarketSnapshot (used for structural strategy context)
        """
        try:
            self._annotate_impl(
                original_signals,
                approved_symbols,
                rejected_reasons or {},
                snapshot,
            )
        except Exception as _exc:
            log.warning("[KLP-001] annotate_strategy_outcome error: %s", _exc)

    def get_today_stats(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Return counts from today's KLP file (for health file integration).
        Returns a zeroed dict on any error.  Never raises.
        """
        try:
            return self._stats_impl(date_str)
        except Exception as _exc:
            log.warning("[KLP-001] get_today_stats error: %s", _exc)
            return {"klp_observations": 0, "klp_annotations": 0, "klp_selected": 0,
                    "klp_overrules": 0, "klp_file": None}

    # ─────────────────────────────────────────────────────────────────────────
    # Evaluation implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _evaluate_impl(self, signals: List[Any], snapshot: Any) -> List[Dict[str, Any]]:
        now_utc  = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%Y-%m-%d")

        # Score all signals
        scored: List[tuple] = []   # (score, sig)
        for sig in signals:
            score = compute_knowledge_score(sig)
            scored.append((score, sig))

        # Rank descending by knowledge score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Determine top-N selection set
        selected_symbols: Set[str] = set()
        for rank_idx, (_, sig) in enumerate(scored):
            if rank_idx < KNOWLEDGE_TOP_N:
                sym = _sym(sig)
                if sym:
                    selected_symbols.add(sym)

        # Build and emit observation records
        records: List[Dict[str, Any]] = []
        for rank_idx, (score, sig) in enumerate(scored):
            sym = _sym(sig)
            dedup_key = f"{sym}|{date_str}"
            with self._obs_lock:
                if dedup_key in self._seen_obs:
                    continue
                self._seen_obs.add(dedup_key)

            rec = _build_obs_record(
                sig           = sig,
                score         = score,
                rank          = rank_idx + 1,
                selected      = (sym in selected_symbols),
                now_utc       = now_utc,
                date_str      = date_str,
                total_signals = len(scored),
            )
            with self._obs_lock:
                self._session_obs[rec["obs_id"]] = rec
            records.append(rec)

        if records:
            self._write(records)
        return records

    # ─────────────────────────────────────────────────────────────────────────
    # Annotation implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _annotate_impl(
        self,
        original_signals: List[Any],
        approved_symbols: Set[str],
        rejected_reasons: Dict[str, str],
        snapshot: Any,
    ) -> None:
        now_utc  = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%Y-%m-%d")

        annotations: List[Dict[str, Any]] = []
        for sig in original_signals:
            sym           = _sym(sig)
            obs_id        = _make_obs_id(sym, date_str, sig)
            strat_approved = sym in approved_symbols
            strategy_status = "PASS" if strat_approved else "REJECTED"
            rej_reason = None if strat_approved else rejected_reasons.get(sym, "STRATEGY_REJECTED")

            # Structural (regime-based) strategy context — frozen C2 logic
            structural_status, structural_name, structural_reason = (
                _evaluate_structural(sig, snapshot)
            )

            # Was this signal knowledge-selected in this session?
            with self._obs_lock:
                matching_obs    = self._session_obs.get(obs_id, {})
            knowledge_selected  = bool(matching_obs.get("knowledge_selected", False))

            disagreement = _compute_disagreement(
                knowledge_selected = knowledge_selected,
                strategy_approved  = strat_approved,
                structural_status  = structural_status,
            )

            annotations.append({
                "obs_id":                         obs_id,
                "event_type":                     "STRATEGY_ANNOTATION",
                "ts_utc":                         now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "trading_date":                   date_str,
                "symbol":                         sym,
                "strategy_name":                  str(getattr(sig, "strategy_name", "unassigned") or "unassigned"),
                "strategy_status":                strategy_status,
                "strategy_rejection_reason":      rej_reason,
                "structural_strategy_status":     structural_status,
                "structural_strategy_name":       structural_name,
                "structural_strategy_reason":     structural_reason,
                "knowledge_selected":             knowledge_selected,
                "knowledge_strategy_disagreement": disagreement,
                "knowledge_execution_status":     "NOT_EXECUTED" if not strat_approved else "STRATEGY_APPROVED",
                "observation_type":               "KNOWLEDGE_ONLY_OBSERVATION" if (knowledge_selected and not strat_approved) else "STRATEGY_PASSED_OBSERVATION" if strat_approved else "KNOWLEDGE_OBSERVED",
                "no_lookahead":                   True,
            })

        if annotations:
            self._write(annotations)

    # ─────────────────────────────────────────────────────────────────────────
    # Stats for health file
    # ─────────────────────────────────────────────────────────────────────────

    def _stats_impl(self, date_str: Optional[str]) -> Dict[str, Any]:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        klp_file = self._data_dir / f"KLP_{date_str}.jsonl"
        obs = ann = selected = overrules = 0
        if klp_file.exists():
            with klp_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    et = rec.get("event_type", "")
                    if et == "KNOWLEDGE_OBSERVATION":
                        obs += 1
                        if rec.get("knowledge_selected"):
                            selected += 1
                    elif et == "STRATEGY_ANNOTATION":
                        ann += 1
                        if rec.get("knowledge_strategy_disagreement") == KNOWLEDGE_OVERRULES:
                            overrules += 1
        return {
            "klp_observations":  obs,
            "klp_annotations":   ann,
            "klp_selected":      selected,
            "klp_overrules":     overrules,
            "klp_file":          str(klp_file) if klp_file.exists() else None,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # File I/O
    # ─────────────────────────────────────────────────────────────────────────

    def _write(self, records: List[Dict[str, Any]]) -> None:
        """Append records to today's KLP JSONL.  Never raises."""
        try:
            now_utc  = datetime.now(timezone.utc)
            date_str = now_utc.strftime("%Y-%m-%d")
            self._data_dir.mkdir(parents=True, exist_ok=True)
            out_path = self._data_dir / f"KLP_{date_str}.jsonl"
            with out_path.open("a", encoding="utf-8") as fh:
                for rec in records:
                    fh.write(json.dumps(rec, ensure_ascii=False))
                    fh.write("\n")
        except Exception as _exc:
            log.warning("[KLP-001] _write error: %s", _exc)


# ─────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE_RESEARCH_SCORE_v1 formula  (module-level, testable independently)
# ─────────────────────────────────────────────────────────────────────────────

def compute_knowledge_score(sig: Any) -> float:
    """
    Compute KNOWLEDGE_RESEARCH_SCORE_v1 in [0.0, 1.0].

    Component weights (sum = 1.0):
      _W_CANDIDATE_SCORE (0.40) — scanner composite score (_obs_candidate_score)
      _W_CONFIDENCE      (0.25) — scanner confidence (0–10) normalised to [0–1]
      _W_EXPECTED_MOVE   (0.15) — expected_move_pct capped at 8 %
      _W_RISK_REWARD     (0.10) — RR piecewise quality function
      _W_REGIME_ALIGN    (0.10) — regime × direction compatibility

    All inputs read from TradeSignal fields — NO future price data.
    Returns float in [0.0, 1.0].
    """
    score = 0.0

    # Component 1: Scanner candidate score (0–1)
    c_score = getattr(sig, "_obs_candidate_score", None)
    if c_score is not None:
        try:
            score += _W_CANDIDATE_SCORE * min(float(c_score), 1.0)
        except (TypeError, ValueError):
            pass

    # Component 2: Scanner confidence (0–10 → 0–1)
    try:
        conf = float(getattr(sig, "confidence", 0.0) or 0.0)
        score += _W_CONFIDENCE * min(conf / 10.0, 1.0)
    except (TypeError, ValueError):
        pass

    # Component 3: Expected move pct (0–8 % → 0–1)
    emp = getattr(sig, "expected_move_pct", None)
    if emp is not None:
        try:
            emp_f = float(emp)
            if emp_f > 0:
                score += _W_EXPECTED_MOVE * min(emp_f / 8.0, 1.0)
        except (TypeError, ValueError):
            pass

    # Component 4: Risk-reward quality (piecewise)
    try:
        entry  = float(getattr(sig, "entry_price",  0.0) or 0.0)
        stop   = float(getattr(sig, "stop_loss",    0.0) or 0.0)
        target = float(getattr(sig, "target_price", 0.0) or 0.0)
        rr = 0.0
        if entry and stop and target and entry != stop:
            rr = abs(target - entry) / abs(entry - stop)
        rr_qual = (
            1.00 if rr >= 3.0 else
            0.85 if rr >= 2.5 else
            0.70 if rr >= 2.0 else
            0.50 if rr >= 1.5 else
            0.20 if rr > 0   else 0.0
        )
        score += _W_RISK_REWARD * rr_qual
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    # Component 5: Regime × direction alignment
    # Only contributes when regime is known; unknown regime = 0 contribution.
    try:
        regime    = str(getattr(sig, "_obs_regime", None) or "").lower().strip()
        direction = getattr(sig, "direction", None)
        dir_str   = (
            getattr(direction, "value", str(direction))
            if direction is not None else ""
        ).upper().strip()
        if regime and dir_str:
            align = _REGIME_ALIGN_TABLE.get(regime, {}).get(dir_str, 0.5)
            score += _W_REGIME_ALIGN * align
        # else: no regime/direction data → 0 contribution
    except (TypeError, AttributeError):
        pass  # no contribution when alignment cannot be computed

    return round(min(max(score, 0.0), 1.0), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sym(sig: Any) -> str:
    return (getattr(sig, "symbol", None) or "UNKNOWN").strip()


def _make_obs_id(symbol: str, date_str: str, sig: Any) -> str:
    """
    Generate a stable obs_id for this signal.
    Keyed on symbol + date + entry_price (rounded to 5 paise).
    """
    entry_raw = float(getattr(sig, "entry_price", 0.0) or 0.0)
    entry_key = round(entry_raw * 20) / 20.0
    return f"{symbol}_{date_str}_{entry_key:.2f}_klp"


def _build_obs_record(
    sig: Any,
    score: float,
    rank: int,
    selected: bool,
    now_utc: datetime,
    date_str: str,
    total_signals: int,
) -> Dict[str, Any]:
    sym = _sym(sig)
    direction_obj = getattr(sig, "direction", None)
    dir_str = (
        getattr(direction_obj, "value", str(direction_obj))
        if direction_obj is not None else "UNKNOWN"
    ).upper()

    entry  = float(getattr(sig, "entry_price",  0.0) or 0.0)
    stop   = float(getattr(sig, "stop_loss",    0.0) or 0.0)
    target = float(getattr(sig, "target_price", 0.0) or 0.0)
    atr    = float(getattr(sig, "atr",          0.0) or 0.0)

    rr: Optional[float] = None
    if entry and stop and target and entry != stop:
        try:
            rr = round(abs(target - entry) / abs(entry - stop), 4)
        except ZeroDivisionError:
            pass

    atr_pct: Optional[float] = None
    if atr and entry and entry > 0:
        atr_pct = round(atr / entry * 100, 4)

    return {
        "obs_id":                       _make_obs_id(sym, date_str, sig),
        "opportunity_id":               getattr(sig, "opportunity_id", None),
        "event_type":                   "KNOWLEDGE_OBSERVATION",
        "ts_utc":                       now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trading_date":                 date_str,
        "symbol":                       sym,
        "direction":                    dir_str,
        # ── Knowledge scoring ────────────────────────────────────────────────
        "knowledge_score":              score,
        "knowledge_score_version":      "KNOWLEDGE_RESEARCH_SCORE_v1",
        "knowledge_rank":               rank,
        "knowledge_selected":           selected,
        "knowledge_selection_rule":     f"TOP_{KNOWLEDGE_TOP_N}_BY_KNOWLEDGE_SCORE",
        "total_signals_this_cycle":     total_signals,
        # ── Target / SL / RR (READ from TradeSignal — no new formula) ────────
        "reference_entry":              entry,
        "knowledge_stop_loss":          stop,
        "knowledge_target":             target,
        "knowledge_RR":                 rr,
        "knowledge_risk_points":        round(abs(entry - stop), 4)   if entry and stop   else None,
        "knowledge_reward_points":      round(abs(target - entry), 4) if entry and target else None,
        "knowledge_expected_return":    getattr(sig, "expected_move_pct", None),
        "atr":                          atr,
        "atr_pct":                      atr_pct,
        "stop_method":                  "ATR_1.5x_FROM_ENTRY",
        "target_method":                "REUSE_SCANNER_STOP_TARGET",
        "calculation_version":          "KLP_001_v1",
        "target_method_version":        "ATR_1.5x_RR_scanner_v1",
        "stop_method_version":          "ATR_1.5x_v1",
        # ── Scanner context ──────────────────────────────────────────────────
        "candidate_score":              getattr(sig, "_obs_candidate_score", None),
        "scanner_confidence":           float(getattr(sig, "confidence", 0.0) or 0.0),
        "scanner_strategy":             str(getattr(sig, "strategy_name", "unassigned") or "unassigned"),
        "regime":                       str(getattr(sig, "_obs_regime", None) or ""),
        # ── Strategy fields — populated by STRATEGY_ANNOTATION ───────────────
        "strategy_status":              None,
        "strategy_rejection_reason":    None,
        "knowledge_strategy_disagreement": None,
        # ── Execution / outcome fields — populated post-market ───────────────
        "knowledge_execution_status":   None,
        "selected":                     None,
        "actual_return_pct":            None,
        "target_hit":                   None,
        "stop_hit":                     None,
        "mfe_pct":                      None,
        "mae_pct":                      None,
        "t1_ret_pct":                   None,
        "t3_ret_pct":                   None,
        "t5_ret_pct":                   None,
        "virtual_outcome":              "KNOWLEDGE_ONLY_OBSERVATION",
        "no_lookahead":                 True,
    }


def _evaluate_structural(sig: Any, snapshot: Any) -> tuple:
    """
    Evaluate structural (regime-based) strategy context via final_c2_selector.
    Returns (status_str, name_str, reason_str).  Never raises.
    """
    try:
        from opportunity_engine.final_c2_selector import evaluate_strategy_context
        direction_obj = getattr(sig, "direction", None)
        dir_str = (
            getattr(direction_obj, "value", str(direction_obj))
            if direction_obj is not None else "BUY"
        ).upper()
        # Map scanner direction to evaluate_strategy_context convention
        ctx_direction = "UP" if dir_str == "BUY" else "DOWN"

        # Map scanner regime label to strategy context regime
        regime_obj = getattr(snapshot, "regime", None) if snapshot else None
        regime_raw = (
            getattr(regime_obj, "value", str(regime_obj))
            if regime_obj is not None else ""
        ).lower()
        ctx_regime = _REGIME_TO_CTX.get(regime_raw, "RANGE")

        result = evaluate_strategy_context(ctx_direction, ctx_regime)
        # result is a 3-tuple: (status, name, reason)
        if isinstance(result, (list, tuple)) and len(result) == 3:
            return str(result[0]), str(result[1]), str(result[2])
        return str(result), "UNKNOWN", "UNKNOWN"
    except Exception:
        return "CONTEXT_UNAVAILABLE", "NONE", "CONTEXT_UNAVAILABLE"


def _compute_disagreement(
    knowledge_selected: bool,
    strategy_approved: bool,
    structural_status: str,
) -> str:
    """
    Compute the KLP-vs-Strategy disagreement label.

    AGREE_PASS           — both knowledge selects AND strategy approves
    AGREE_REJECT         — knowledge doesn't select AND strategy rejects
    KNOWLEDGE_OVERRULES  — knowledge selects but strategy rejects
    STRATEGY_OVERRULES   — knowledge doesn't select but strategy approves
    STRUCTURAL_OVERRIDE  — knowledge selects, strategy rejects, structural context says REJECT
    """
    if knowledge_selected and strategy_approved:
        return AGREE_PASS
    if knowledge_selected and not strategy_approved:
        if structural_status in ("REJECT", "CONTRADICTED"):
            return STRUCTURAL_OVERRIDE
        return KNOWLEDGE_OVERRULES
    if not knowledge_selected and strategy_approved:
        return STRATEGY_OVERRULES
    return AGREE_REJECT

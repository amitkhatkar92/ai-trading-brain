"""
learning_system/learning_observation_ledger.py
================================================
LOL — Learning Observation Ledger

Unified, persistent, restart-safe lifecycle tracker for every signal
observation from scanner through to learning outcome.

PROBLEM SOLVED
--------------
Prior to this module there was no single authoritative record of:
  • which signals were observed
  • which decision was made (KDA / StrategyLab / rejected)
  • which signals were executed vs rejected vs missed
  • whether a rejection was correct
  • what the counterfactual outcome was

Each component (KLP JSONL, KDA ledger, rejection_audit.db) held a partial
view.  After a container restart the cross-links between those views were
not explicitly reconstructable.

SOLUTION
--------
Append-only JSONL ledger per trading date:

  data/lol/LOL_YYYY-MM-DD.jsonl

Every lifecycle transition appends a new line with the same observation_id.
The canonical state of each observation is the LAST record with that ID.
This makes the ledger idempotent: re-processing the same event is safe.

LIFECYCLE STATES
----------------
  OBSERVED            — scanner produced signal; KLP observation recorded
  DECISION_RECORDED   — StrategyLab + KDA evaluated the signal
  EXECUTED            — order submitted to broker
  REJECTED            — rejected by StrategyLab, KDA HOLD, risk, or debate
  BLOCKED             — risk guardian or circuit-breaker blocked the order
  OUTCOME_PENDING     — T+1 or later data required; not yet available
  OUTCOME_OBSERVED    — T+1..T+5 price data collected; outcome classified
  LEARNING_PROCESSED  — outcome fed back to learning system

OUTCOME CLASSES (16)
--------------------
  1.  EXECUTED_WIN
  2.  EXECUTED_LOSS
  3.  EXECUTED_FLAT
  4.  EARLY_EXIT
  5.  STOP_EXIT
  6.  TARGET_EXIT
  7.  REJECTED_CORRECT       — rejected; price moved against the signal
  8.  REJECTED_INCORRECT     — rejected; price moved in predicted direction
  9.  BLOCKED_CORRECT        — blocked; price moved against the signal
  10. BLOCKED_INCORRECT      — blocked; price moved in predicted direction
  11. SHORTLISTED_NOT_EXECUTED
  12. MISSED_OPPORTUNITY     — not in candidate list; price moved ≥ threshold
  13. KDA_FALSE_POSITIVE     — KDA said BUY/SELL; move did not materialise
  14. KDA_FALSE_NEGATIVE     — KDA said HOLD; missed a real move
  15. KNOWLEDGE_AGREEMENT    — KDA and StrategyLab agreed; outcome consistent
  16. KNOWLEDGE_DISAGREEMENT — KDA and StrategyLab disagreed; compared

AUTHORITY INVARIANTS (never violated)
--------------------------------------
  broker_calls      = 0
  orders            = 0
  execution_authority = False
  PAPER_TRADING state never read or modified here
  production decision path never modified (read-only access to signals)

RESTART SAFETY
--------------
  On __init__, the ledger loads all OUTCOME_PENDING records from the last
  LOOKBACK_DAYS date files.  No in-memory state is required to survive a
  restart; the JSONL files are the single source of truth.

ANTI-LOOKAHEAD RULE
-------------------
  Counterfactual outcomes are computed ONLY from bars with
  bar.date > observation.decision_timestamp.date().
  The original decision record is NEVER modified.

USAGE (from orchestrator — all wrapped in try/except)
------
  lol = get_lol()

  # At KLP-001 evaluation time (before StrategyLab):
  lol.record_observations(signals, trading_date)

  # After KDA + StrategyLab merge:
  lol.update_decisions(signals, enriched_signals, kda_results, trading_date)

  # At EOD (alongside KLP-002):
  lol.fill_pending_outcomes(lookback_days=7)
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from utils import get_logger

log = get_logger(__name__)

# ── Storage ───────────────────────────────────────────────────────────────────
_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "lol"
_LOOKBACK_DAYS    = 10    # days to scan for pending outcomes on startup
_OUTCOME_HORIZON  = 5     # T+1..T+5 bars for counterfactual
_MISSED_MOVE_PCT  = 1.5   # abs move ≥ this → MISSED_OPPORTUNITY

# ── Lifecycle state constants ─────────────────────────────────────────────────
OBSERVED           = "OBSERVED"
DECISION_RECORDED  = "DECISION_RECORDED"
EXECUTED           = "EXECUTED"
REJECTED           = "REJECTED"
BLOCKED            = "BLOCKED"
OUTCOME_PENDING    = "OUTCOME_PENDING"
OUTCOME_OBSERVED   = "OUTCOME_OBSERVED"
LEARNING_PROCESSED = "LEARNING_PROCESSED"

_LIFECYCLE_STATES = {
    OBSERVED, DECISION_RECORDED, EXECUTED, REJECTED,
    BLOCKED, OUTCOME_PENDING, OUTCOME_OBSERVED, LEARNING_PROCESSED,
}

# ── Outcome class constants ───────────────────────────────────────────────────
EXECUTED_WIN           = "EXECUTED_WIN"
EXECUTED_LOSS          = "EXECUTED_LOSS"
EXECUTED_FLAT          = "EXECUTED_FLAT"
EARLY_EXIT             = "EARLY_EXIT"
STOP_EXIT              = "STOP_EXIT"
TARGET_EXIT            = "TARGET_EXIT"
REJECTED_CORRECT       = "REJECTED_CORRECT"
REJECTED_INCORRECT     = "REJECTED_INCORRECT"
BLOCKED_CORRECT        = "BLOCKED_CORRECT"
BLOCKED_INCORRECT      = "BLOCKED_INCORRECT"
SHORTLISTED_NOT_EXECUTED = "SHORTLISTED_NOT_EXECUTED"
MISSED_OPPORTUNITY     = "MISSED_OPPORTUNITY"

# ── KDA error sentinel constants (not lifecycle states) ───────────────────────
# These appear in the kda_decision field to distinguish error conditions
# from genuine knowledge-evaluation outcomes.
KDA_NOT_REACHED    = "KDA_NOT_REACHED"    # outer KDA block never ran (pipeline crashed before KDA)
KDA_PIPELINE_ERROR = "KDA_PIPELINE_ERROR" # KDA ran but returned status=KNOWLEDGE_PIPELINE_ERROR
KDA_FALSE_POSITIVE     = "KDA_FALSE_POSITIVE"
KDA_FALSE_NEGATIVE     = "KDA_FALSE_NEGATIVE"
KNOWLEDGE_AGREEMENT    = "KNOWLEDGE_AGREEMENT"
KNOWLEDGE_DISAGREEMENT = "KNOWLEDGE_DISAGREEMENT"

OUTCOME_UNKNOWN  = "UNKNOWN"
OUTCOME_PENDING_CLASS = "PENDING"

_ALL_OUTCOME_CLASSES = {
    EXECUTED_WIN, EXECUTED_LOSS, EXECUTED_FLAT, EARLY_EXIT, STOP_EXIT,
    TARGET_EXIT, REJECTED_CORRECT, REJECTED_INCORRECT, BLOCKED_CORRECT,
    BLOCKED_INCORRECT, SHORTLISTED_NOT_EXECUTED, MISSED_OPPORTUNITY,
    KDA_FALSE_POSITIVE, KDA_FALSE_NEGATIVE, KNOWLEDGE_AGREEMENT,
    KNOWLEDGE_DISAGREEMENT, OUTCOME_UNKNOWN, OUTCOME_PENDING_CLASS,
}

# ── NSE symbol helpers ────────────────────────────────────────────────────────
_INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "NIFTY50", "NIFTYBANK"}
_GLOBAL_SYMBOL_MAP = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK",
                      "NIFTY50": "^NSEI", "NIFTYBANK": "^NSEBANK"}


def _yf_ticker(symbol: str) -> str:
    s = symbol.upper().strip()
    return _GLOBAL_SYMBOL_MAP.get(s, s if s.endswith(".NS") else f"{s}.NS")


def _make_obs_id(symbol: str, trading_date: str, entry_price: float) -> str:
    """Stable observation ID: deterministic per signal. Same symbol+date+entry → same ID."""
    raw = f"{symbol}|{trading_date}|{entry_price:.4f}"
    import hashlib
    return "LOL_" + hashlib.sha1(raw.encode()).hexdigest()[:16]


# ── Observation record schema ─────────────────────────────────────────────────

def _empty_record(
    obs_id:        str,
    symbol:        str,
    direction:     str,
    trading_date:  str,
    observed_at:   str,
    entry_price:   float,
    stop_loss:     float,
    target_price:  float,
) -> Dict[str, Any]:
    return {
        # identity
        "observation_id":       obs_id,
        "opportunity_id":       None,   # universal lineage key (UUID from scanner)
        "symbol":               symbol,
        "direction":            direction,
        "trading_date":         trading_date,
        # event taxonomy
        "event_type":           "OBSERVED",  # matches lifecycle_state on creation
        # timestamps
        "observed_at":          observed_at,
        "decision_at":          None,
        "execution_at":         None,
        "outcome_at":           None,
        # prices
        "entry_price":          entry_price,
        "stop_loss":            stop_loss,
        "target_price":         target_price,
        "rr_ratio":             None,
        # lifecycle
        "lifecycle_state":      OBSERVED,
        # decision
        "klp_score":            None,
        "klp_selected":         None,
        "klp_rank":             None,
        "strategy_decision":    None,
        "strategy_name":        None,
        "strategy_rejection_reason": None,
        "kda_decision":         None,
        "kda_evidence_state":   None,
        "authorization_source": None,
        # execution
        "executed":             False,
        "order_id":             None,
        # outcome (filled at EOD T+1..T+5)
        "outcome_class":        OUTCOME_PENDING_CLASS,
        "actual_return_pct":    None,
        "target_hit":           None,
        "stop_hit":             None,
        "mfe_pct":              None,
        "mae_pct":              None,
        "t1_ret_pct":           None,
        "t3_ret_pct":           None,
        "t5_ret_pct":           None,
        "outcome_first_event":  None,
        # knowledge provenance
        "knowledge_provenance": {},
        # integrity
        "no_lookahead":         True,
        "outcome_fill_horizon": _OUTCOME_HORIZON,
        "lol_version":          "1",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Core ledger class
# ─────────────────────────────────────────────────────────────────────────────

class LearningObservationLedger:
    """
    Unified, persistent, restart-safe lifecycle ledger.
    Thread-safe.  All methods swallow exceptions — never raises.
    broker_calls = 0, orders = 0, execution_authority = False.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file_locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        # In-memory dedup for this session (keyed by obs_id)
        # Prevents double-writing OUTCOME_OBSERVED for the same obs_id.
        self._outcome_written: Set[str] = set()
        # Pending observations: obs_id → record dict.  Populated at startup and
        # updated as new decisions / outcomes are appended.
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._load_pending_on_startup()
        log.info(
            "[LOL] Initialised. data_dir=%s pending_observations=%d",
            self._dir, len(self._pending),
        )

    # ── Public API: intraday ──────────────────────────────────────────────────

    def record_observations(
        self,
        signals:       List[Any],
        trading_date:  Optional[str] = None,
    ) -> int:
        """
        Record OBSERVED lifecycle entry for each scanner signal.
        Called once per cycle BEFORE StrategyLab.
        Returns count of new observations recorded.  Never raises.
        """
        try:
            return self._record_observations_impl(signals, trading_date)
        except Exception as exc:
            log.debug("[LOL] record_observations error: %s", exc)
            return 0

    def update_decisions(
        self,
        original_signals:  List[Any],
        enriched_signals:  List[Any],
        kda_results:       Dict[str, Any],
        trading_date:      Optional[str] = None,
    ) -> int:
        """
        Update lifecycle to DECISION_RECORDED, REJECTED, or BLOCKED for each
        signal after StrategyLab + KDA merge.
        Returns count of records updated.  Never raises.
        """
        try:
            return self._update_decisions_impl(
                original_signals, enriched_signals, kda_results, trading_date
            )
        except Exception as exc:
            log.debug("[LOL] update_decisions error: %s", exc)
            return 0

    def record_execution(
        self,
        obs_id:    str,
        order_id:  str,
        executed_at: Optional[str] = None,
    ) -> bool:
        """
        Advance lifecycle to EXECUTED for a signal that was placed.
        Called after OrderManager confirms placement.  Never raises.
        """
        try:
            rec = self._pending.get(obs_id)
            if rec is None:
                return False
            rec = dict(rec)
            rec["lifecycle_state"] = EXECUTED
            rec["event_type"]      = EXECUTED
            rec["executed"]        = True
            rec["order_id"]        = order_id
            rec["execution_at"]    = executed_at or datetime.now(timezone.utc).isoformat()
            self._append(rec)
            self._pending[obs_id] = rec
            return True
        except Exception as exc:
            log.debug("[LOL] record_execution error: %s", exc)
            return False

    def update_cre_blocking(
        self,
        signals:       List[Any],
        block_reason:  str,
        trading_date:  Optional[str] = None,
    ) -> int:
        """
        Record signals blocked by CapitalRiskEngine (e.g. QTY_ZERO) as BLOCKED.
        These are signals that passed StrategyLab but could not be sized.
        The block_reason is stored so CRE blocks are distinguishable from
        RiskGuardian blocks.  Outcome fill will classify them as
        BLOCKED_CORRECT / BLOCKED_INCORRECT at T+1+.
        Never raises.
        """
        try:
            return self._update_cre_blocking_impl(signals, block_reason, trading_date)
        except Exception as exc:
            log.debug("[LOL] update_cre_blocking error: %s", exc)
            return 0

    # ── Public API: EOD outcome fill ─────────────────────────────────────────

    def fill_pending_outcomes(
        self,
        lookback_days: int = 7,
        _ohlcv_fetcher=None,
    ) -> Dict[str, Any]:
        """
        Fill outcome fields for all OUTCOME_PENDING observations.
        Computes counterfactual returns from T+1..T+5 daily bars.
        ANTI-LOOKAHEAD: uses only bars AFTER decision_timestamp.
        Called once at EOD.  Never raises.
        Returns summary: {processed, skipped_pending, skipped_no_data, errors}.
        """
        try:
            return self._fill_outcomes_impl(lookback_days, _ohlcv_fetcher)
        except Exception as exc:
            log.debug("[LOL] fill_pending_outcomes error: %s", exc)
            return {"processed": 0, "error": str(exc)}

    # ── Public API: query ─────────────────────────────────────────────────────

    def get_pending(self) -> List[Dict[str, Any]]:
        """Return all records currently in OUTCOME_PENDING state."""
        return [r for r in self._pending.values()
                if r.get("lifecycle_state") == OUTCOME_PENDING]

    def load_day(self, trading_date: str) -> List[Dict[str, Any]]:
        """Load all records for a given trading date.  Never raises."""
        try:
            path = self._dir / f"LOL_{trading_date}.jsonl"
            if not path.exists():
                return []
            records: Dict[str, Dict] = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    obs_id = rec.get("observation_id")
                    if obs_id:
                        records[obs_id] = rec  # latest wins
                except Exception:
                    pass
            return list(records.values())
        except Exception:
            return []

    def get_stats(self, trading_date: Optional[str] = None) -> Dict[str, Any]:
        """Return summary statistics for a trading date (default: today)."""
        td = trading_date or date.today().isoformat()
        records = self.load_day(td)
        by_state: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        for r in records:
            s = r.get("lifecycle_state", "UNKNOWN")
            o = r.get("outcome_class", "UNKNOWN")
            by_state[s]   = by_state.get(s, 0)   + 1
            by_outcome[o] = by_outcome.get(o, 0) + 1
        return {
            "trading_date":  td,
            "total":         len(records),
            "by_state":      by_state,
            "by_outcome":    by_outcome,
            "pending_count": by_state.get(OUTCOME_PENDING, 0),
        }

    # ── Internal: startup loading ────────────────────────────────────────────

    def _load_pending_on_startup(self) -> None:
        """Scan the last LOOKBACK_DAYS of files and collect OUTCOME_PENDING records."""
        today = date.today()
        for delta in range(_LOOKBACK_DAYS):
            d = (today - timedelta(days=delta)).isoformat()
            path = self._dir / f"LOL_{d}.jsonl"
            if not path.exists():
                continue
            seen: Dict[str, Dict] = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    obs_id = rec.get("observation_id")
                    if obs_id:
                        seen[obs_id] = rec  # latest wins
                except Exception:
                    pass
            for obs_id, rec in seen.items():
                if rec.get("lifecycle_state") not in (
                    OUTCOME_OBSERVED, LEARNING_PROCESSED
                ):
                    self._pending[obs_id] = rec
                else:
                    # D8-003: restore dedup set from disk so EOD after restart
                    # does not write duplicate OUTCOME_OBSERVED records
                    self._outcome_written.add(obs_id)

    # ── Internal: record observations ────────────────────────────────────────

    def _record_observations_impl(
        self,
        signals:      List[Any],
        trading_date: Optional[str],
    ) -> int:
        td  = trading_date or date.today().isoformat()
        now = datetime.now(timezone.utc).isoformat()
        written = 0
        for sig in signals:
            try:
                symbol  = str(getattr(sig, "symbol", ""))
                entry   = float(getattr(sig, "entry_price",   0.0) or 0.0)
                stop    = float(getattr(sig, "stop_loss",     0.0) or 0.0)
                target  = float(getattr(sig, "target_price",  0.0) or 0.0)
                conf    = float(getattr(sig, "confidence",    0.0) or 0.0)
                rr      = float(getattr(sig, "risk_reward_ratio", 0.0) or 0.0)
                dir_raw = getattr(sig, "direction", "BUY")
                direction = (
                    dir_raw.value.upper() if hasattr(dir_raw, "value")
                    else str(dir_raw).upper()
                )
                obs_id = _make_obs_id(symbol, td, entry)
                # Idempotent: skip if already OBSERVED for this session
                if obs_id in self._pending:
                    continue
                rec = _empty_record(
                    obs_id=obs_id, symbol=symbol, direction=direction,
                    trading_date=td, observed_at=now,
                    entry_price=entry, stop_loss=stop, target_price=target,
                )
                # Propagate universal opportunity lineage ID from scanner
                rec["opportunity_id"] = str(getattr(sig, "opportunity_id", "") or "")
                rec["klp_score"]  = float(getattr(sig, "_obs_candidate_score", conf) or conf)
                rec["rr_ratio"]   = rr
                rec["knowledge_provenance"] = {
                    "confidence":    conf,
                    "strategy_name": str(getattr(sig, "strategy_name", "") or ""),
                    "regime":        str(getattr(sig, "regime", "") or ""),
                    "scanner_source": "EQUITY_SCANNER",
                }
                self._append(rec)
                self._pending[obs_id] = rec
                written += 1
            except Exception as exc:
                log.debug("[LOL] Signal record error: %s", exc)
        return written

    # ── Internal: update decisions ────────────────────────────────────────────

    def _update_decisions_impl(
        self,
        original_signals: List[Any],
        enriched_signals:  List[Any],
        kda_results:       Dict[str, Any],
        trading_date:      Optional[str],
    ) -> int:
        td  = trading_date or date.today().isoformat()
        now = datetime.now(timezone.utc).isoformat()
        enriched_syms = {str(getattr(s, "symbol", "")) for s in enriched_signals}
        updated = 0
        for sig in original_signals:
            try:
                symbol  = str(getattr(sig, "symbol", ""))
                entry   = float(getattr(sig, "entry_price", 0.0) or 0.0)
                obs_id  = _make_obs_id(symbol, td, entry)
                rec     = dict(self._pending.get(obs_id) or {})
                if not rec:
                    continue
                kda_r   = kda_results.get(symbol, {})
                # Distinguish error states from genuine insufficient-evidence
                _kda_status = kda_r.get("status") if kda_r else None
                if _kda_status == "KNOWLEDGE_PIPELINE_ERROR":
                    kda_dec = KDA_PIPELINE_ERROR
                    kda_ev  = "PIPELINE_ERROR"
                elif not kda_r:
                    # Empty dict = outer KDA block never reached this symbol
                    kda_dec = KDA_NOT_REACHED
                    kda_ev  = "NOT_REACHED"
                else:
                    kda_dec = kda_r.get("kda_decision") or "KNOWLEDGE_INSUFFICIENT_EVIDENCE"
                    kda_ev  = kda_r.get("evidence_state") or "NO_EVIDENCE"
                auth_src = (
                    "BOTH"         if symbol in enriched_syms and kda_r.get("kda_decision") in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
                    else "STRATEGY_LAB" if symbol in enriched_syms
                    else "KDA"     if kda_r.get("kda_decision") in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
                    else "NONE"
                )
                strategy_name = str(getattr(sig, "strategy_name", "") or "")
                strategy_rej  = None
                new_state     = DECISION_RECORDED
                if symbol not in enriched_syms and auth_src == "NONE":
                    new_state = REJECTED
                    strategy_rej = "STRATEGY_REJECTED"
                    if kda_dec == "KNOWLEDGE_HOLD":
                        new_state = BLOCKED
                        strategy_rej = "KDA_HOLD"
                else:
                    # signal entered the production path (DECISION_RECORDED = awaiting execution gating)
                    new_state = OUTCOME_PENDING
                rec["lifecycle_state"]           = new_state
                rec["event_type"]                = new_state  # mirrors lifecycle_state
                rec["decision_at"]               = now
                rec["strategy_decision"]         = "PASS" if symbol in enriched_syms else "REJECT"
                rec["strategy_name"]             = strategy_name
                rec["strategy_rejection_reason"] = strategy_rej
                rec["kda_decision"]              = kda_dec
                rec["kda_evidence_state"]        = kda_ev
                rec["authorization_source"]      = auth_src
                rec["klp_selected"]              = bool(getattr(sig, "knowledge_selected", False))
                rec["klp_rank"]                  = getattr(sig, "knowledge_rank", None)
                self._append(rec)
                self._pending[obs_id] = rec
                updated += 1
            except Exception as exc:
                log.debug("[LOL] update_decisions error for signal: %s", exc)
        return updated

    def _update_cre_blocking_impl(
        self,
        signals:      List[Any],
        block_reason: str,
        trading_date: Optional[str],
    ) -> int:
        td  = trading_date or date.today().isoformat()
        now = datetime.now(timezone.utc).isoformat()
        updated = 0
        for sig in signals:
            try:
                symbol = str(getattr(sig, "symbol", ""))
                entry  = float(getattr(sig, "entry_price", 0.0) or 0.0)
                obs_id = _make_obs_id(symbol, td, entry)
                rec    = dict(self._pending.get(obs_id) or {})
                if not rec:
                    continue
                rec["lifecycle_state"]           = BLOCKED
                rec["event_type"]                = BLOCKED
                rec["decision_at"]               = now
                rec["block_reason"]              = block_reason
                rec["strategy_decision"]         = "PASS"
                rec["strategy_rejection_reason"] = None
                rec["authorization_source"]      = "NONE"
                # Preserve KDA state already recorded (or mark as not-reached)
                if not rec.get("kda_decision"):
                    rec["kda_decision"]      = KDA_NOT_REACHED
                    rec["kda_evidence_state"] = "NOT_REACHED"
                self._append(rec)
                self._pending[obs_id] = rec
                updated += 1
            except Exception as exc:
                log.debug("[LOL] CRE blocking update error: %s", exc)
        return updated

    # ── Internal: outcome fill ────────────────────────────────────────────────

    def _fill_outcomes_impl(
        self,
        lookback_days: int,
        _ohlcv_fetcher,
    ) -> Dict[str, Any]:
        fetcher = _ohlcv_fetcher or _fetch_ohlcv
        today   = date.today()
        result  = {"processed": 0, "skipped_pending": 0, "skipped_no_data": 0, "errors": 0}
        # Load pending from files for lookback window
        pending_to_fill: List[Dict[str, Any]] = []
        for delta in range(lookback_days):
            d = (today - timedelta(days=delta)).isoformat()
            for rec in self.load_day(d):
                state = rec.get("lifecycle_state")
                if state in (OUTCOME_PENDING, REJECTED, BLOCKED, DECISION_RECORDED):
                    obs_id = rec.get("observation_id")
                    if obs_id and obs_id not in self._outcome_written:
                        pending_to_fill.append(rec)
        for rec in pending_to_fill:
            obs_id       = rec["observation_id"]
            symbol       = rec.get("symbol", "")
            decision_date = rec.get("trading_date") or rec.get("observed_at", "")[:10]
            entry         = rec.get("entry_price", 0.0) or 0.0
            stop          = rec.get("stop_loss",   0.0) or 0.0
            target        = rec.get("target_price", 0.0) or 0.0
            direction     = rec.get("direction", "BUY")
            # Anti-lookahead: need T+1 to be in the past
            try:
                t1 = date.fromisoformat(decision_date) + timedelta(days=1)
            except Exception:
                result["errors"] += 1
                continue
            if t1 > today:
                result["skipped_pending"] += 1
                continue
            try:
                bars = fetcher(symbol, decision_date, _OUTCOME_HORIZON)
            except Exception:
                result["skipped_no_data"] += 1
                continue
            if not bars:
                result["skipped_no_data"] += 1
                continue
            # Compute outcome
            outcome = _compute_outcome(
                bars=bars,
                entry=entry,
                stop=stop,
                target=target,
                direction=direction,
                decision_state=rec.get("lifecycle_state", OUTCOME_PENDING),
                kda_decision=rec.get("kda_decision"),
                strategy_decision=rec.get("strategy_decision"),
                authorization_source=rec.get("authorization_source", "NONE"),
            )
            updated = dict(rec)
            updated.update(outcome)
            updated["lifecycle_state"] = OUTCOME_OBSERVED
            updated["event_type"]      = OUTCOME_OBSERVED
            # outcome_at = actual market bar date (first bar used = T+1 after decision)
            # processed_at = wall-clock time this EOD job ran (for audit/latency tracking)
            _outcome_bar_date = bars[0].get("date") if bars else None
            if _outcome_bar_date:
                updated["outcome_at"]    = str(_outcome_bar_date) + "T15:30:00+05:30"
            else:
                updated["outcome_at"]    = datetime.now(timezone.utc).isoformat()
            updated["processed_at"]  = datetime.now(timezone.utc).isoformat()
            # D-022: verify temporal order before asserting no_lookahead=True.
            # Outcome must be strictly after decision. If comparison fails, mark False.
            try:
                from datetime import timezone as _tz
                def _to_utc(ts: str) -> datetime:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_tz.utc)
                    return dt.astimezone(_tz.utc)
                _decision_at = updated.get("decision_at", "")
                _outcome_at  = updated.get("outcome_at",  "")
                updated["no_lookahead"] = (
                    bool(_decision_at) and bool(_outcome_at)
                    and _to_utc(_outcome_at) > _to_utc(_decision_at)
                )
            except Exception:
                updated["no_lookahead"] = False  # uncertain → fail closed
            self._append(updated)
            self._pending.pop(obs_id, None)
            self._outcome_written.add(obs_id)
            result["processed"] += 1
        return result

    # ── Internal: file I/O ────────────────────────────────────────────────────

    def _file_lock(self, date_str: str) -> threading.Lock:
        with self._global_lock:
            if date_str not in self._file_locks:
                self._file_locks[date_str] = threading.Lock()
            return self._file_locks[date_str]

    def _append(self, record: Dict[str, Any]) -> None:
        td   = record.get("trading_date") or date.today().isoformat()
        path = self._dir / f"LOL_{td}.jsonl"
        lock = self._file_lock(td)
        with lock:
            try:
                line = json.dumps(record, default=str) + "\n"
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.flush()
                    os.fsync(fh.fileno())  # D-021: ensure outcome records survive OS crash
            except Exception as exc:
                log.debug("[LOL] Append error: %s", exc)


# ── Outcome computation ───────────────────────────────────────────────────────

def _compute_outcome(
    bars:               List[Dict[str, Any]],
    entry:              float,
    stop:               float,
    target:             float,
    direction:          str,
    decision_state:     str,
    kda_decision:       Optional[str],
    strategy_decision:  Optional[str],
    authorization_source: str,
) -> Dict[str, Any]:
    """
    Compute theoretical outcome from OHLCV bars.
    bars[0] must be T+1 (first bar AFTER decision date).
    Anti-lookahead: only bars in the list are used.
    """
    is_buy   = direction.upper() not in ("SELL", "SHORT", "BEAR")
    t1_close = bars[0]["close"] if bars else None
    t3_close = bars[2]["close"] if len(bars) >= 3 else None
    t5_close = bars[4]["close"] if len(bars) >= 5 else None

    def pct(price: Optional[float]) -> Optional[float]:
        if price is None or not entry:
            return None
        raw = (price - entry) / entry * 100.0
        return round(raw if is_buy else -raw, 4)

    t1_ret = pct(t1_close)
    t3_ret = pct(t3_close)
    t5_ret = pct(t5_close)

    # Path-dependent MFE/MAE and first event
    mfe = 0.0
    mae = 0.0
    target_hit = False
    stop_hit   = False
    first_event = "OUTCOME_EXPIRED"
    for bar in bars:
        hi = bar["high"]
        lo = bar["low"]
        if is_buy:
            bar_mfe = (hi - entry) / entry * 100.0
            bar_mae = (entry - lo) / entry * 100.0
            if not stop_hit and not target_hit:
                if lo <= stop < hi:
                    stop_hit   = True
                    first_event = "STOP_HIT"
                if hi >= target > lo:
                    target_hit  = True
                    first_event = "TARGET_HIT"
                if lo <= stop and hi >= target:
                    first_event = "OUTCOME_AMBIGUOUS"
                    stop_hit = target_hit = True
        else:
            bar_mfe = (entry - lo) / entry * 100.0
            bar_mae = (hi - entry) / entry * 100.0
            if not stop_hit and not target_hit:
                if hi >= stop > lo:
                    stop_hit   = True
                    first_event = "STOP_HIT"
                if lo <= target < hi:
                    target_hit  = True
                    first_event = "TARGET_HIT"
                if hi >= stop and lo <= target:
                    first_event = "OUTCOME_AMBIGUOUS"
                    stop_hit = target_hit = True
        mfe = max(mfe, bar_mfe)
        mae = max(mae, bar_mae)

    # Classify outcome class
    oc = _classify_outcome(
        target_hit=target_hit, stop_hit=stop_hit,
        t5_ret=t5_ret, first_event=first_event,
        decision_state=decision_state,
        kda_decision=kda_decision,
        strategy_decision=strategy_decision,
        authorization_source=authorization_source,
        is_buy=is_buy,
    )
    return {
        "actual_return_pct":   t5_ret,
        "t1_ret_pct":          t1_ret,
        "t3_ret_pct":          t3_ret,
        "t5_ret_pct":          t5_ret,
        "target_hit":          target_hit,
        "stop_hit":            stop_hit,
        "mfe_pct":             round(mfe, 4),
        "mae_pct":             round(mae, 4),
        "outcome_first_event": first_event,
        "outcome_class":       oc,
    }


def _classify_outcome(
    target_hit:          bool,
    stop_hit:            bool,
    t5_ret:              Optional[float],
    first_event:         str,
    decision_state:      str,
    kda_decision:        Optional[str],
    strategy_decision:   Optional[str],
    authorization_source: str,
    is_buy:              bool,
) -> str:
    """Classify one of 16 outcome classes.  No exceptions raised."""
    move_positive = (t5_ret is not None and t5_ret > 0)
    move_negative = (t5_ret is not None and t5_ret < 0)
    is_significant = (t5_ret is not None and abs(t5_ret) >= _MISSED_MOVE_PCT)

    # Executed outcomes
    if decision_state in (EXECUTED, OUTCOME_PENDING) and authorization_source not in ("NONE", ""):
        if first_event == "TARGET_HIT":
            return TARGET_EXIT
        if first_event == "STOP_HIT":
            return STOP_EXIT
        if target_hit and stop_hit:
            return EXECUTED_FLAT
        if t5_ret is not None:
            if t5_ret > 0.3:
                return EXECUTED_WIN
            if t5_ret < -0.3:
                return EXECUTED_LOSS
            return EXECUTED_FLAT
        return OUTCOME_UNKNOWN

    # Rejected / blocked outcomes
    if decision_state in (REJECTED, BLOCKED):
        moved_in_predicted  = (is_buy and move_positive) or (not is_buy and move_negative)
        moved_against        = (is_buy and move_negative) or (not is_buy and move_positive)
        is_correct_rejection = moved_against and is_significant
        is_wrong_rejection   = moved_in_predicted and is_significant

        if decision_state == BLOCKED:
            if is_correct_rejection:
                return BLOCKED_CORRECT
            if is_wrong_rejection:
                return BLOCKED_INCORRECT
        else:
            # REJECTED
            if is_correct_rejection:
                return REJECTED_CORRECT
            if is_wrong_rejection:
                return REJECTED_INCORRECT

        # KDA-specific disagreement analysis
        kda = kda_decision or ""
        strat = strategy_decision or ""
        if "KNOWLEDGE_BUY" in kda or "KNOWLEDGE_SELL" in kda:
            # KDA said go, strategy said no
            if moved_in_predicted and is_significant:
                return KDA_FALSE_NEGATIVE  # should have listened to KDA
        if "KNOWLEDGE_HOLD" in kda:
            # KDA blocked it
            if moved_against and is_significant:
                return KDA_FALSE_NEGATIVE  # KDA was wrong to hold
        if strat == "PASS" and kda in ("KNOWLEDGE_HOLD",):
            if moved_in_predicted:
                return KNOWLEDGE_DISAGREEMENT

        return OUTCOME_UNKNOWN

    # Not selected at all (discovery only)
    if not is_significant:
        return OUTCOME_UNKNOWN
    return MISSED_OPPORTUNITY if (
        (is_buy and move_positive) or (not is_buy and move_negative)
    ) else OUTCOME_UNKNOWN


# ── OHLCV fetcher ─────────────────────────────────────────────────────────────

def _fetch_ohlcv(symbol: str, decision_date: str, horizon: int = 5) -> List[Dict[str, Any]]:
    """Fetch T+1..T+horizon daily bars. No bars on or before decision_date."""
    try:
        import yfinance as yf
        from datetime import timedelta
        d0    = date.fromisoformat(decision_date)
        start = (d0 + timedelta(days=1)).isoformat()
        end   = (d0 + timedelta(days=horizon + 10)).isoformat()
        ticker = _yf_ticker(symbol)
        df = yf.download(ticker, start=start, end=end, progress=False,
                         auto_adjust=True, timeout=8)
        if df is None or df.empty:
            return []
        bars = []
        for idx, row in df.iterrows():
            bar_date = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
            if bar_date <= decision_date:
                continue  # strict anti-lookahead
            bars.append({
                "date":  bar_date,
                "open":  float(row["Open"]),
                "high":  float(row["High"]),
                "low":   float(row["Low"]),
                "close": float(row["Close"]),
            })
        return bars[:horizon]
    except Exception:
        return []


# ── Singleton ─────────────────────────────────────────────────────────────────
_LOL_INSTANCE: Optional[LearningObservationLedger] = None
_LOL_LOCK = threading.Lock()


def get_lol(data_dir: Optional[Path] = None) -> LearningObservationLedger:
    """Return the singleton LOL instance. Thread-safe."""
    global _LOL_INSTANCE
    if _LOL_INSTANCE is None:
        with _LOL_LOCK:
            if _LOL_INSTANCE is None:
                _LOL_INSTANCE = LearningObservationLedger(data_dir)
    return _LOL_INSTANCE

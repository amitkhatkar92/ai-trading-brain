"""
Options Opportunity Observation Journal
=======================================

Append-only JSONL record of every options opportunity observed through the pipeline.

State lifecycle (v2 — full lifecycle):
  DISCOVERED                → Signal discovered; pre-quality-gate market context captured
  CONTEXT_ENRICHED          → Full market context (OI, PCR, bid/ask, IV provenance) attached
  SHORTLISTED               → Passed all quality gate checks (C1–C6)
  REJECTED                  → Failed a quality gate check (rejection_check + rejection_reason captured)
  APPROVED                  → Approved by options risk engine (Layer C)
  BLOCKED                   → Blocked by risk engine or execution engine (reason captured)
  EXECUTED                  → Order placed by OptionsOrderManager (Layer D)
  NOT_EXECUTED              → Passed all gates but no execution slot (dedup/idle)
  EXPIRED                   → Signal expired without execution
  OUTCOME_OBSERVED          → Position closed; actual P&L recorded
  COUNTERFACTUAL_MONITORING → Rejected/non-executed; monitoring hypothetical outcome
  COUNTERFACTUAL_OUTCOME    → Monitoring complete; hypothetical P&L computed
  REJECTION_CORRECT         → False rejection analysis: rejection was correct
  REJECTION_INCORRECT       → False rejection analysis: rejection was wrong (missed opportunity)
  MISSED_OPPORTUNITY        → System failed to generate a signal for a profitable situation

Design principles:
  1. EVERY discovered opportunity gets a record at DISCOVERED state — not just executed trades.
  2. opportunity_id links ALL state records for the same opportunity across its full lifecycle.
  3. Rejection reasons are captured at the specific check level (C1, C2, ..., C6).
  4. IV and greek provenance are explicitly tagged (LIVE_MARKET / MODEL_ESTIMATE / DERIVED).
  5. Full market context captured at DISCOVERED time: OI, volume, bid/ask, PCR, spot, regime.
  6. Counterfactual: rejected signals monitored so false-rejection analysis is possible.
  7. Append-only: no record is ever modified. State transitions produce new records.
  8. All writes are wrapped in try/except — this journal must never block execution.
  9. This is an OPTIONS-SPECIFIC system, independent of the equity KDA/KLP path.

File: data/options_observations.jsonl (append-only JSONL, one JSON object per line)
Singleton: get_options_observation_journal()
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

OBSERVATIONS_PATH = "data/options_observations.jsonl"

# ── Observation state constants ────────────────────────────────────────────
OBS_DISCOVERED                = "DISCOVERED"
OBS_CONTEXT_ENRICHED          = "CONTEXT_ENRICHED"
OBS_SHORTLISTED               = "SHORTLISTED"
OBS_REJECTED                  = "REJECTED"
OBS_APPROVED                  = "APPROVED"
OBS_BLOCKED                   = "BLOCKED"
OBS_EXECUTED                  = "EXECUTED"
OBS_NOT_EXECUTED              = "NOT_EXECUTED"
OBS_EXPIRED                   = "EXPIRED"
OBS_OUTCOME_OBSERVED          = "OUTCOME_OBSERVED"
OBS_COUNTERFACTUAL_MONITORING = "COUNTERFACTUAL_MONITORING"
OBS_COUNTERFACTUAL_OUTCOME    = "COUNTERFACTUAL_OUTCOME"
OBS_REJECTION_CORRECT         = "REJECTION_CORRECT"
OBS_REJECTION_INCORRECT       = "REJECTION_INCORRECT"
OBS_MISSED_OPPORTUNITY        = "MISSED_OPPORTUNITY"

_VALID_STATES = frozenset({
    OBS_DISCOVERED,
    OBS_CONTEXT_ENRICHED,
    OBS_SHORTLISTED,
    OBS_REJECTED,
    OBS_APPROVED,
    OBS_BLOCKED,
    OBS_EXECUTED,
    OBS_NOT_EXECUTED,
    OBS_EXPIRED,
    OBS_OUTCOME_OBSERVED,
    OBS_COUNTERFACTUAL_MONITORING,
    OBS_COUNTERFACTUAL_OUTCOME,
    OBS_REJECTION_CORRECT,
    OBS_REJECTION_INCORRECT,
    OBS_MISSED_OPPORTUNITY,
})

# ── IV and greek provenance tags ───────────────────────────────────────────
IV_SOURCE_LIVE_MARKET   = "LIVE_MARKET"    # yfinance actual chain IV
IV_SOURCE_MODEL_ESTIMATE = "MODEL_ESTIMATE"  # AngelOne: IV=0.16 BS seed
IV_SOURCE_DERIVED       = "DERIVED"        # computed from price history
IV_SOURCE_UNAVAILABLE   = "UNAVAILABLE"    # no IV data available

GREEK_SOURCE_LIVE_MARKET   = "LIVE_MARKET"
GREEK_SOURCE_MODEL_ESTIMATE = "MODEL_ESTIMATE"  # computed from seeded IV

# ── Data source tags ──────────────────────────────────────────────────────
DATA_SOURCE_ANGEL_ONE = "ANGEL_ONE"
DATA_SOURCE_YFINANCE  = "YFINANCE"
DATA_SOURCE_SYNTHETIC = "SYNTHETIC"


@dataclass
class OptionsOpportunityObservation:
    """
    Snapshot of one options opportunity at a specific point in its lifecycle.

    Each state transition writes a NEW record to the journal (immutable/append-only).

    CRITICAL: `opportunity_id` is the stable lifecycle identifier.  It is
    generated ONCE at the DISCOVERED state (by OptionsOpportunityRegistry)
    and must be propagated to ALL subsequent observation records for the
    same opportunity.

    `obs_id` remains for internal seq/dedup purposes only.
    """
    obs_id:        str         # "OOO-{YYYYMMDDHHMMSS}-{seq:04d}-{SYMBOL}-{STRATEGY}"
    symbol:        str
    strategy_name: str
    observed_at:   str         # ISO 8601 datetime string
    state:         str         # one of the OBS_* constants above

    # ── Stable lifecycle identity ──────────────────────────────────────
    opportunity_id: Optional[str] = None   # set at DISCOVERED; propagated to all records

    # ── Signal characteristics at observation time ─────────────────────
    confidence:    float = 0.0
    direction:     str   = ""
    dte:           int   = 0
    iv_rank:       float = 0.0
    chain_quality: float = 0.0
    regime:        str   = ""
    vix:           float = 0.0

    # ── Data provenance ────────────────────────────────────────────────
    data_source:  str = ""   # DATA_SOURCE_* constant
    iv_source:    str = ""   # IV_SOURCE_* constant
    greek_source: str = ""   # GREEK_SOURCE_* constant

    # ── Full market context at discovery time ──────────────────────────
    spot_price:           float = 0.0   # underlying spot
    atm_iv:               float = 0.0   # chain ATM IV (0 if model estimate)
    total_ce_oi:          int   = 0     # total call open interest
    total_pe_oi:          int   = 0     # total put open interest
    pcr:                  float = 0.0   # put-call OI ratio
    atm_bid_ask_spread:   float = 0.0   # ATM bid-ask spread as % of mid
    time_of_day:          str   = ""    # PRE_MARKET / OPENING / NORMAL / CLOSING
    events_today:         List[str] = field(default_factory=list)   # "EXPIRY", "RBI_POLICY", etc.

    # ── Per-leg market context ─────────────────────────────────────────
    # Each entry: {strike, option_type, premium, bid, ask, iv, delta,
    #              gamma, theta, vega, open_interest, volume, iv_source}
    legs_context: List[Dict] = field(default_factory=list)

    # ── Quality gate evidence ──────────────────────────────────────────
    # Populated for SHORTLISTED/REJECTED states
    quality_checks_passed: List[str]     = field(default_factory=list)
    rejection_check:       Optional[str] = None   # "C1" | "C2" | "C3" | "C4" | "C5" | "C6"
    rejection_reason:      Optional[str] = None   # human-readable reason string

    # ── Risk engine evidence (Layer C) ────────────────────────────────
    risk_approved:         Optional[bool] = None
    risk_rejection_reason: Optional[str]  = None
    risk_gate_failed:      Optional[str]  = None  # exact gate: "CAPITAL"/"VIX"/"LOSS_STREAK"/"PER_TRADE"

    # ── Execution linkage ─────────────────────────────────────────────
    order_id: Optional[str] = None   # set when state == EXECUTED

    # ── Outcome fields (OUTCOME_OBSERVED state) ───────────────────────
    actual_pnl:           Optional[float] = None
    expected_pnl:         Optional[float] = None
    actual_exit_price:    Optional[float] = None
    actual_entry_price:   Optional[float] = None
    expected_entry_price: Optional[float] = None
    hold_days:            Optional[int]   = None
    exit_reason:          Optional[str]   = None
    outcome_correctness:  Optional[str]   = None

    # ── Knowledge observer state at time of this observation ──────────
    knowledge_state: str            = "DEVELOPING"
    knowledge_score: Optional[float] = None

    # ── Counterfactual tracking (for REJECTED / non-executed signals) ─
    counterfactual_checked: bool          = False
    counterfactual_notes:   Optional[str] = None
    counterfactual_pnl:     Optional[float] = None   # hypothetical P&L if executed
    counterfactual_horizon_days: Optional[int] = None


class OptionsObservationJournal:
    """
    Append-only JSONL journal of options opportunity observations.

    Thread-safe; each write is an independent file append.
    Failures are logged at DEBUG level and never propagate to callers.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq  = 0
        try:
            os.makedirs(os.path.dirname(OBSERVATIONS_PATH), exist_ok=True)
        except Exception:
            pass

    # ── Public API ─────────────────────────────────────────────────────

    def make_obs_id(self, symbol: str, strategy: str) -> str:
        """
        Generate a unique observation ID.
        Format: OOO-{YYYYMMDDHHMMSS}-{seq:04d}-{SYMBOL}-{STRATEGY}
        """
        with self._lock:
            self._seq += 1
            seq = self._seq
        dt_str    = datetime.now().strftime("%Y%m%d%H%M%S")
        sym_clean = (symbol or "UNK").replace(".", "_").upper()[:12]
        strat_clean = (strategy or "UNK").replace(" ", "_").upper()[:20]
        return f"OOO-{dt_str}-{seq:04d}-{sym_clean}-{strat_clean}"

    def record(self, obs: OptionsOpportunityObservation) -> None:
        """
        Append one observation to the JSONL file.
        Silently ignores invalid states and I/O failures.
        """
        if obs.state not in _VALID_STATES:
            log.debug(
                "[OptionsObservationJournal] Invalid state '%s' for obs %s — skipped.",
                obs.state, obs.obs_id,
            )
            return
        try:
            row  = asdict(obs)
            line = json.dumps(row, default=str) + "\n"
            with self._lock:
                with open(OBSERVATIONS_PATH, "a", encoding="utf-8") as fh:
                    fh.write(line)
        except Exception as exc:
            log.debug(
                "[OptionsObservationJournal] Write failed for obs %s: %s",
                obs.obs_id, exc,
            )

    def read_all(self) -> List[Dict]:
        """
        Read all observations from the journal.
        Returns a list of dicts (parsed JSON lines).
        Empty list on any error.
        """
        if not os.path.exists(OBSERVATIONS_PATH):
            return []
        rows: List[Dict] = []
        try:
            with open(OBSERVATIONS_PATH, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            pass
        except Exception as exc:
            log.debug("[OptionsObservationJournal] read_all failed: %s", exc)
        return rows

    def read_by_order_id(self, order_id: str) -> List[Dict]:
        """Return all observations linked to a specific execution order_id."""
        return [r for r in self.read_all() if r.get("order_id") == order_id]

    def read_by_symbol_strategy(self, symbol: str, strategy: str) -> List[Dict]:
        """Return all observations for a specific symbol + strategy combination."""
        return [
            r for r in self.read_all()
            if r.get("symbol") == symbol and r.get("strategy_name") == strategy
        ]

    def read_by_opportunity_id(self, opportunity_id: str) -> List[Dict]:
        """Return all records that share the same opportunity_id (full lifecycle)."""
        return [r for r in self.read_all()
                if r.get("opportunity_id") == opportunity_id]

    def read_outcomes(self) -> List[Dict]:
        """Return all OUTCOME_OBSERVED records."""
        return [r for r in self.read_all()
                if r.get("state") == OBS_OUTCOME_OBSERVED]

    def read_since_date(self, date_str: str) -> List[Dict]:
        """Return all observations on or after the given YYYY-MM-DD date string."""
        return [r for r in self.read_all()
                if r.get("observed_at", "") >= date_str]


# ── Module-level singleton ─────────────────────────────────────────────────

_JOURNAL_INSTANCE: Optional[OptionsObservationJournal] = None
_JOURNAL_LOCK     = threading.Lock()


def get_options_observation_journal() -> OptionsObservationJournal:
    """Return the process-wide OptionsObservationJournal singleton."""
    global _JOURNAL_INSTANCE
    with _JOURNAL_LOCK:
        if _JOURNAL_INSTANCE is None:
            _JOURNAL_INSTANCE = OptionsObservationJournal()
    return _JOURNAL_INSTANCE

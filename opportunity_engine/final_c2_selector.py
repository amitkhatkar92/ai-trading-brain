"""
opportunity_engine/final_c2_selector.py
========================================
Final C2 Selection Module — Frozen Architecture

Single source of truth for the 20→5 selection validated in:
  POST_OPEN_SELECTION_RESEARCH_001 (OOS UP dir_acc=0.615, lift=1.71×)
  FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001

Architecture:
  V3 20 UP + 20 DOWN  →  T+1 open observed
  →  C2 score = direction-signed gap magnitude
  →  Top 5 per direction (by C2 desc)
  →  Strategy evaluated as CONTEXT (not a gate)

Key principle: Knowledge/C2 is primary selector.
Strategy provides evidence. It does not veto Knowledge selections.

SAFETY INVARIANTS (permanent):
  - Zero broker calls
  - Zero orders
  - Zero CandidateStore writes
  - No ExecutionEngine, RiskControl, or DecisionEngine access
  - Strategy evaluation is read-only context
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Architecture constants (frozen — change only with new validated research)
# ─────────────────────────────────────────────────────────────────────────────

C2_TOP_N         = 5   # top-N per direction (validated OOS)
V3_POOL_SIZE     = 20  # pool candidates per direction from V3
MODULE_VERSION   = "FINAL_C2_SELECTOR_v1"

# ── Disagreement labels ────────────────────────────────────────────────────
# AGREE_PASS               Knowledge selects, Strategy also passes
# KNOWLEDGE_OVERRULES_STRATEGY  Knowledge selects, Strategy would reject
# STRATEGY_SUPPORTS_KNOWLEDGE   Strategy has an active aligned position/signal
# STRATEGY_UNAVAILABLE     Strategy cannot evaluate (no regime data / no match)
# NO_STRATEGY_MATCH        No applicable strategy for this direction/regime

AGREE_PASS                    = "AGREE_PASS"
KNOWLEDGE_OVERRULES_STRATEGY  = "KNOWLEDGE_OVERRULES_STRATEGY"
STRATEGY_SUPPORTS_KNOWLEDGE   = "STRATEGY_SUPPORTS_KNOWLEDGE"
STRATEGY_UNAVAILABLE          = "STRATEGY_UNAVAILABLE"
NO_STRATEGY_MATCH             = "NO_STRATEGY_MATCH"

# ── Strategy evaluation rules (from STRATEGY_RECONSTRUCTION_VALIDATION_001) ─
# D2: BEAR  + UP       → REJECT
# D3: VOLATILE + UP    → REJECT
# DOWN: no SELL strategies exist → ALIGNED/NEUTRAL/CONTRADICTED only

_REJECT_REASON_D2   = "D2_BEAR_EQUITY_BUY"
_REJECT_REASON_D3   = "D3_VOLATILE_EQUITY_BUY"
_PASS_REASON        = "PASS_ALL_RULES"
_UNAVAIL_REASON     = "STRATEGY_UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class C2Candidate:
    """A single candidate from the V3 20-pool with C2 scoring applied."""
    # Identity
    symbol:    str
    direction: str      # "UP" or "DOWN"

    # V3 discovery
    v3_score:  float
    v3_rank:   int      # 1-based rank within V3 pool
    pool_size: int      # total V3 pool size (usually 20)

    # T0 data
    previous_close: Optional[float] = None

    # T+1 data (post-open — populated after open)
    opening_price: Optional[float] = None
    gap_pct:       Optional[float] = None  # (T1_open/T0_close - 1) × 100

    # C2 scoring
    c2_score:      Optional[float] = None  # +gap_pct for UP, -gap_pct for DOWN
    c2_rank:       Optional[int]   = None  # 1-based rank within direction pool
    selected_top5: bool            = False

    # Strategy as context (non-veto)
    strategy_status:  str = STRATEGY_UNAVAILABLE
    strategy_name:    str = "NONE"
    strategy_reason:  str = _UNAVAIL_REASON
    strategy_regime:  str = "UNAVAILABLE"

    # Knowledge/Strategy relationship
    knowledge_strategy_disagreement: str = STRATEGY_UNAVAILABLE

    # Metadata
    v3_model_version: str = "V3_FINAL"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class C2SelectionResult:
    """Complete result of a C2 selection day."""
    trade_date:          str
    t1_date:             Optional[str]
    selection_timestamp: str
    architecture_version: str = MODULE_VERSION

    # Complete pools (all 20 per direction, with c2_rank assigned)
    up_pool:   List[C2Candidate] = field(default_factory=list)
    down_pool: List[C2Candidate] = field(default_factory=list)

    # Regime
    regime: str = "UNAVAILABLE"

    # Summary counts
    @property
    def up_top5(self) -> List[C2Candidate]:
        return [c for c in self.up_pool if c.selected_top5]

    @property
    def down_top5(self) -> List[C2Candidate]:
        return [c for c in self.down_pool if c.selected_top5]

    @property
    def strategy_agree_up(self) -> int:
        return sum(1 for c in self.up_top5 if c.knowledge_strategy_disagreement == AGREE_PASS)

    @property
    def strategy_overrule_up(self) -> int:
        return sum(1 for c in self.up_top5
                   if c.knowledge_strategy_disagreement == KNOWLEDGE_OVERRULES_STRATEGY)

    def model_b_up(self) -> List[C2Candidate]:
        """Model B counterfactual: which UP top-5 would survive a strategy gate."""
        return [c for c in self.up_top5 if c.strategy_status == "PASS"]

    def model_b_down(self) -> List[C2Candidate]:
        """Model B counterfactual: all DOWN top-5 (no SELL gate exists)."""
        return list(self.down_top5)


# ─────────────────────────────────────────────────────────────────────────────
# Pure functions
# ─────────────────────────────────────────────────────────────────────────────

def compute_c2_score(
    previous_close: float,
    opening_price: float,
    direction: str,
) -> Optional[float]:
    """
    C2 = direction-signed gap magnitude (post-open only).

    Formula (frozen — FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001):
      gap_pct = (T1_open / T0_close - 1) × 100
      UP:   c2_score = +gap_pct   (reward largest positive opening gap)
      DOWN: c2_score = -gap_pct   (reward largest negative opening gap)

    Information: T+1 open only. Never uses T+1 close/high/low.
    Returns None if inputs are invalid.
    """
    if previous_close is None or opening_price is None:
        return None
    if previous_close <= 0 or opening_price <= 0:
        return None
    gap_pct = (opening_price / previous_close - 1.0) * 100.0
    return round(gap_pct if direction == "UP" else -gap_pct, 6)


def compute_gap_pct(previous_close: float, opening_price: float) -> Optional[float]:
    """Raw gap: (T1_open / T0_close - 1) × 100. Positive = gap up."""
    if not previous_close or not opening_price or previous_close <= 0 or opening_price <= 0:
        return None
    return round((opening_price / previous_close - 1.0) * 100.0, 6)


def evaluate_strategy_context(
    direction: str,
    regime: Optional[str],
) -> Tuple[str, str, str]:
    """
    Evaluate strategy rules as READ-ONLY context.

    Returns (status, name, reason) where:
      UP   + BEAR     → ("REJECT", "ALL_BUY_STRATEGIES", "D2_BEAR_EQUITY_BUY")
      UP   + VOLATILE → ("REJECT", "ALL_BUY_STRATEGIES", "D3_VOLATILE_EQUITY_BUY")
      UP   + BULL/RANGE → ("PASS", strategy_name, "PASS_ALL_RULES")
      DOWN + any      → ("ALIGNED"/"NEUTRAL"/"CONTRADICTED", "NONE", reason)
      unknown regime  → ("STRATEGY_UNAVAILABLE", "NONE", "STRATEGY_UNAVAILABLE")

    IMPORTANT: "REJECT" means the Strategy rule WOULD reject.
    It does NOT automatically remove the Knowledge-selected candidate.
    The disagreement is RECORDED as KNOWLEDGE_OVERRULES_STRATEGY.
    """
    if not regime or regime in ("UNAVAILABLE", "UNKNOWN", None):
        return (STRATEGY_UNAVAILABLE, "NONE", _UNAVAIL_REASON)

    if direction == "UP":
        if regime == "BEAR":
            return ("REJECT", "ALL_BUY_STRATEGIES", _REJECT_REASON_D2)
        if regime == "VOLATILE":
            return ("REJECT", "ALL_BUY_STRATEGIES", _REJECT_REASON_D3)
        if regime == "BULL":
            return ("PASS", "Trend_Pullback", _PASS_REASON)
        return ("PASS", "Mean_Reversion_or_Trend_Pullback", _PASS_REASON)

    else:  # DOWN
        # No SELL strategies in the evolved library
        if regime == "BEAR":
            return ("ALIGNED", "NONE", "DOWN_BEAR_ALIGNED")
        if regime == "BULL":
            return ("CONTRADICTED", "NONE", "DOWN_BULL_CONTRADICTED")
        return ("NEUTRAL", "NONE", "DOWN_RANGE_NEUTRAL")


def compute_disagreement(
    strategy_status: str,
    direction: str,
    selected_top5: bool = True,
) -> str:
    """
    Describe the relationship between C2 selection and Strategy evaluation.

    ``selected_top5=True``  (candidate IS in the C2 top-5):
        Returns a K/S relationship label:
          AGREE_PASS                   — K selects; S also passes
          KNOWLEDGE_OVERRULES_STRATEGY — K selects; S would reject or macro is adverse
          STRATEGY_SUPPORTS_KNOWLEDGE  — K selects; macro context is aligned (DOWN+BEAR)
          STRATEGY_UNAVAILABLE         — no regime data; S cannot evaluate

    ``selected_top5=False`` (candidate is NOT in the C2 top-5):
        Strategy is evaluated INDEPENDENTLY of C2 rank.
        Returns the raw strategy verdict so non-selected candidates carry
        full strategy information for analytics:
          "PASS" / "REJECT" / "ALIGNED" / "CONTRADICTED" / "NEUTRAL"
          or STRATEGY_UNAVAILABLE when regime data is missing.

    ``NO_STRATEGY_MATCH`` is returned ONLY when there is genuinely no
    applicable strategy rule for this direction/regime combination.
    It is NEVER returned solely because a candidate was not selected by C2.
    """
    if strategy_status == STRATEGY_UNAVAILABLE:
        return STRATEGY_UNAVAILABLE

    if selected_top5:
        # C2 selected this candidate — describe the K/S relationship.
        if direction == "UP":
            if strategy_status == "PASS":
                return AGREE_PASS
            if strategy_status == "REJECT":
                return KNOWLEDGE_OVERRULES_STRATEGY
        else:  # DOWN — no SELL gate; only contextual labels
            if strategy_status == "ALIGNED":
                return STRATEGY_SUPPORTS_KNOWLEDGE
            if strategy_status == "CONTRADICTED":
                # Macro context is adverse; K still selects
                return KNOWLEDGE_OVERRULES_STRATEGY
            if strategy_status == "NEUTRAL":
                return AGREE_PASS
        return STRATEGY_UNAVAILABLE

    # C2 did NOT select this candidate.
    # Strategy was evaluated independently of C2 rank.
    # Carry the raw strategy verdict so it remains informative for analytics.
    if strategy_status in ("PASS", "REJECT", "ALIGNED", "CONTRADICTED", "NEUTRAL"):
        return strategy_status
    return NO_STRATEGY_MATCH  # genuinely no applicable rule


# ─────────────────────────────────────────────────────────────────────────────
# Main selection function
# ─────────────────────────────────────────────────────────────────────────────

def select_c2_top5(
    up_pool: List[Dict[str, Any]],
    down_pool: List[Dict[str, Any]],
    opening_prices: Dict[str, float],
    regime: str = "UNAVAILABLE",
    trade_date: str = "",
    t1_date: Optional[str] = None,
    n: int = C2_TOP_N,
) -> C2SelectionResult:
    """
    Apply C2 selection to the V3 20+20 pool.

    Args:
      up_pool:        List of V3 UP pool dicts (must have 'symbol', 'v3_up_score',
                      'previous_close'; v3_rank will be inferred from position).
      down_pool:      List of V3 DOWN pool dicts.
      opening_prices: {symbol: open_price} from T+1 data.
      regime:         Market regime (BULL/BEAR/RANGE/VOLATILE/UNAVAILABLE).
      trade_date:     The T close date (YYYY-MM-DD).
      t1_date:        The T+1 opening date (YYYY-MM-DD).
      n:              How many candidates to select (default: 5).

    Returns:
      C2SelectionResult with ALL 20+20 candidates ranked.
      Top-5 have selected_top5=True.
      Strategy evaluated as non-veto context on every candidate.
      knowledge_strategy_disagreement recorded on every candidate.

    Selection is deterministic:
      Ties broken by v3_rank (lower V3 rank = higher V3 score = wins tie).
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    def _process(pool: List[Dict], direction: str) -> List[C2Candidate]:
        score_key = "v3_up_score" if direction == "UP" else "v3_down_score"
        candidates: List[C2Candidate] = []

        for v3_rank, raw in enumerate(pool, start=1):
            sym        = raw.get("symbol", "")
            prev_close = raw.get("previous_close") or raw.get("close")
            opening    = opening_prices.get(sym)
            v3_score   = float(raw.get(score_key) or raw.get("v3_score") or 0.0)

            gap_pct = compute_gap_pct(prev_close, opening) if (prev_close and opening) else None
            c2_score = compute_c2_score(prev_close, opening, direction) if (prev_close and opening) else None

            strat_status, strat_name, strat_reason = evaluate_strategy_context(direction, regime)

            cand = C2Candidate(
                symbol          = sym,
                direction       = direction,
                v3_score        = v3_score,
                v3_rank         = v3_rank,
                pool_size       = len(pool),
                previous_close  = prev_close,
                opening_price   = opening,
                gap_pct         = gap_pct,
                c2_score        = c2_score,
                strategy_status = strat_status,
                strategy_name   = strat_name,
                strategy_reason = strat_reason,
                strategy_regime = regime,
            )
            candidates.append(cand)

        # Rank by c2_score descending; break ties by v3_rank ascending
        valid   = [c for c in candidates if c.c2_score is not None]
        no_data = [c for c in candidates if c.c2_score is None]

        valid.sort(key=lambda c: (-c.c2_score, c.v3_rank))

        for c2_rank, cand in enumerate(valid, start=1):
            cand.c2_rank        = c2_rank
            cand.selected_top5  = c2_rank <= n
            cand.knowledge_strategy_disagreement = compute_disagreement(
                cand.strategy_status, direction, selected_top5=cand.selected_top5
            )

        for cand in no_data:
            cand.c2_rank        = None
            cand.selected_top5  = False
            # strategy_status was computed independently; carry it through
            cand.knowledge_strategy_disagreement = compute_disagreement(
                cand.strategy_status, direction, selected_top5=False
            )

        return valid + no_data

    up_ranked   = _process(up_pool,   "UP")
    down_ranked = _process(down_pool, "DOWN")

    return C2SelectionResult(
        trade_date           = trade_date,
        t1_date              = t1_date,
        selection_timestamp  = now_utc,
        up_pool              = up_ranked,
        down_pool            = down_ranked,
        regime               = regime,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def candidates_to_records(result: C2SelectionResult) -> List[Dict[str, Any]]:
    """Flatten C2SelectionResult to a list of dicts suitable for JSONL/CSV."""
    records = []
    for cand in result.up_pool + result.down_pool:
        rec = cand.as_dict()
        rec["trade_date"]          = result.trade_date
        rec["t1_date"]             = result.t1_date
        rec["selection_timestamp"] = result.selection_timestamp
        rec["architecture_version"] = result.architecture_version
        rec["regime"]              = result.regime
        records.append(rec)
    return records

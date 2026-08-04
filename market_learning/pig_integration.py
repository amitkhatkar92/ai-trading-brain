"""
pig_integration.py — R-001 Phase 2: PIG Integration into Trading Platform.

Wires the Platform Intelligence Gateway (PIG) into the live trading pipeline
at two injection points:

  1. Opportunity Engine  — enriches TradeSignal.confidence for ranking.
                           No signal direction, entry, stop, or target changed.
  2. Decision Engine     — adds InstitutionalDNAAI as a bounded extra vote.
                           Decision Engine retains final authority.

Design principles
-----------------
* PIG is additional evidence, NOT a signal generator.
* All PIG calls are fallback-safe: None returned on any failure.
* Influence is bounded by PIGInfluencePolicy.
* Every call emits a [PIGTelemetry] log line for observability.
* When PIG is unavailable, pipeline continues identically to current behaviour.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# =============================================================================
# Telemetry
# =============================================================================

@dataclass
class PIGCallRecord:
    """One query attempt — used to populate PIGTelemetry."""
    symbol:         str
    latency_ms:     float
    available:      bool
    ca_pmci:        float
    evidence_count: int
    error:          Optional[str] = None


class PIGTelemetry:
    """Thread-safe accumulator for per-cycle PIG call telemetry."""

    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._records: List[PIGCallRecord] = []

    def record(self, r: PIGCallRecord) -> None:
        with self._lock:
            self._records.append(r)
        if r.available:
            log.info(
                "[PIGTelemetry] symbol=%s latency=%.0fms ca_pmci=%.3f evidence=%d",
                r.symbol, r.latency_ms, r.ca_pmci, r.evidence_count,
            )
        else:
            log.info(
                "[PIGTelemetry] symbol=%s latency=%.0fms available=False error=%s",
                r.symbol, r.latency_ms, r.error or "none",
            )

    def summary(self) -> Dict[str, Any]:
        """Return aggregate stats over all recorded calls."""
        with self._lock:
            n = len(self._records)
            if not n:
                return {
                    "total_calls": 0, "available": 0, "availability_pct": 0.0,
                    "avg_latency_ms": 0.0, "avg_ca_pmci": 0.0, "avg_evidence_count": 0.0,
                }
            avail = [r for r in self._records if r.available]
            return {
                "total_calls":        n,
                "available":          len(avail),
                "availability_pct":   round(100 * len(avail) / n, 1),
                "avg_latency_ms":     round(sum(r.latency_ms for r in self._records) / n, 1),
                "avg_ca_pmci":        round(sum(r.ca_pmci for r in avail) / len(avail), 4) if avail else 0.0,
                "avg_evidence_count": round(sum(r.evidence_count for r in avail) / len(avail), 1) if avail else 0.0,
            }

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)


# =============================================================================
# Influence Policy
# =============================================================================

@dataclass
class PIGInfluencePolicy:
    """
    Configurable bounds for PIG's contribution to the trading pipeline.

    All defaults are conservative.  PIG influence grows as DNA data accumulates
    and track record is established.  All fields can be overridden via MLSConfig.
    """
    # DecisionEngine: vote weight for InstitutionalDNAAI
    vote_weight:           float = 0.08
    # Minimum CA-PMCI to cast a non-silent vote; below this PIG returns None
    min_ca_pmci_for_vote:  float = 0.30
    # Feature flag: inject PIG vote into DecisionEngine
    decision_vote_enabled: bool  = True

    # Opportunity Engine: max additive boost to TradeSignal.confidence (0-10 scale)
    max_conviction_boost:         float = 1.0
    # Minimum CA-PMCI to apply opportunity boost; below this no enrichment
    min_ca_pmci_for_boost:        float = 0.30
    # Feature flag: enrich Opportunity Engine signals
    opportunity_boost_enabled:    bool  = True

    # Telemetry feature flag
    telemetry_enabled: bool = True

    @classmethod
    def from_config(cls, cfg: Any) -> "PIGInfluencePolicy":
        """Build from MLSConfig instance using pig_* fields."""
        return cls(
            vote_weight=getattr(cfg, "pig_vote_weight", 0.08),
            min_ca_pmci_for_vote=getattr(cfg, "pig_min_ca_pmci_for_vote", 0.30),
            decision_vote_enabled=getattr(cfg, "pig_decision_vote_enabled", True),
            max_conviction_boost=getattr(cfg, "pig_max_conviction_boost", 1.0),
            min_ca_pmci_for_boost=getattr(cfg, "pig_min_ca_pmci_for_boost", 0.30),
            opportunity_boost_enabled=getattr(cfg, "pig_opportunity_boost_enabled", True),
            telemetry_enabled=getattr(cfg, "pig_telemetry_enabled", True),
        )


# =============================================================================
# Vote builder — Part 2 (Decision Engine integration)
# =============================================================================

def pig_build_vote(
    pi:     Any,   # PlatformIntelligence
    policy: Optional[PIGInfluencePolicy] = None,
) -> Optional[Any]:   # DebateVote | None
    """
    Convert PlatformIntelligence into a DebateVote for 'InstitutionalDNAAI'.

    Returns None when CA-PMCI < policy.min_ca_pmci_for_vote.
    This preserves backward-compatible behaviour: when PIG has no opinion,
    the 5 existing agent weights sum to 1.0 unchanged.

    Score mapping: CA-PMCI is [0,1]; DecisionEngine scores are [0,10].
      CA-PMCI < threshold  → None (silent — no vote cast)
      CA-PMCI >= threshold → score = min(10.0, ca_pmci * 10.0)

    The vote is always "approve" — PIG never issues hard rejects.
    Its contribution is bounded by InstitutionalDNAAI's weight in AGENT_WEIGHTS.

    Part 3 explainability: reasoning string records all 7 required fields.
    """
    from models.agent_output import DebateVote

    if policy is None:
        policy = PIGInfluencePolicy()

    if not policy.decision_vote_enabled:
        return None

    ca_pmci  = float(getattr(pi, "ca_pmci", 0.0))
    raw_pmci = float(getattr(pi, "raw_pmci", 0.0))
    cds      = float(getattr(pi, "cds_score", 0.0))
    inst_c   = float(getattr(pi, "institutional_confidence", 0.0))
    ev_count = int(getattr(pi, "evidence_count", 0))
    dna_match = float(getattr(pi, "winner_dna_match", 0.0))
    ctx_match = float(getattr(pi, "context_score", 0.0))

    if ca_pmci < policy.min_ca_pmci_for_vote:
        return None   # insufficient conviction — stay silent

    score = min(10.0, max(0.0, ca_pmci * 10.0))

    reasoning = (
        f"[InstitutionalDNA] raw_pmci={raw_pmci:.3f} ca_pmci={ca_pmci:.3f} "
        f"cds={cds:.3f} inst_confidence={inst_c:.3f} "
        f"evidence={ev_count} dna_match={dna_match:.3f} ctx_match={ctx_match:.3f}"
    )

    return DebateVote(
        agent_name="InstitutionalDNAAI",
        vote="approve",
        score=round(score, 2),
        reasoning=reasoning,
        suggested_position_modifier=1.0,   # PIG never changes position sizing
    )


# =============================================================================
# Opportunity enrichment — Part 1 (Opportunity Engine integration)
# =============================================================================

def pig_enrich_signals(
    signals:  List[Any],   # List[TradeSignal]
    adapter:  "PIGTradingAdapter",
    snapshot: Any,          # MarketSnapshot
    policy:   Optional[PIGInfluencePolicy] = None,
) -> List[Any]:
    """
    Enrich TradeSignal.confidence scores using PlatformIntelligence.

    Only confidence (ranking score) is modified.  Signal direction, entry,
    stop-loss, and target are never touched.  Returns the same list.

    Boost formula: boost = min(max_boost, ca_pmci * max_boost)
    The boost is additive on the 0–10 confidence scale, capped at 10.

    If PIG is unavailable, signals are returned unchanged.
    """
    if not signals:
        return signals
    if policy is None:
        policy = PIGInfluencePolicy()
    if not policy.opportunity_boost_enabled:
        return signals

    enriched_count = 0
    for sig in signals:
        pi = adapter.query(sig.symbol, sig, snapshot)
        if pi is None:
            continue
        ca_pmci = float(getattr(pi, "ca_pmci", 0.0))
        if ca_pmci < policy.min_ca_pmci_for_boost:
            continue
        boost = min(policy.max_conviction_boost, ca_pmci * policy.max_conviction_boost)
        _raw  = getattr(sig, "confidence", 0.0)
        old   = float(_raw) if _raw is not None else 0.0
        new   = min(10.0, old + boost)
        try:
            sig.confidence = new
        except Exception:
            continue   # frozen dataclass — skip silently
        enriched_count += 1
        log.info(
            "[PIGOpportunityEnrich] symbol=%s ca_pmci=%.3f boost=+%.2f "
            "confidence %.2f→%.2f",
            sig.symbol, ca_pmci, boost, old, new,
        )

    if enriched_count:
        log.info(
            "[PIGOpportunityEnrich] %d/%d signals enriched by institutional DNA.",
            enriched_count, len(signals),
        )
    return signals


# =============================================================================
# Feature builder helpers
# =============================================================================

def _build_observation_features(
    symbol:   str,
    signal:   Optional[Any],
    snapshot: Optional[Any],
) -> Dict[str, float]:
    """
    Build a [0,1]-normalised feature dict from available signal + snapshot data.

    Missing values default to 0.5 (neutral midpoint) to avoid biasing PMCI.
    These features approximate the pre-move MLS observation captured by
    MarketObserver.  Accuracy improves when the full MLS pipeline runs daily.
    """
    feats: Dict[str, float] = {}

    if signal is not None:
        conf = float(getattr(signal, "confidence", 5.0))
        # TradeSignal.confidence is 0–10; normalise to [0,1]
        feats["confidence"] = max(0.0, min(1.0, conf / 10.0))

        rr = float(getattr(signal, "risk_reward_ratio", 2.5))
        feats["risk_reward"] = max(0.0, min(1.0, rr / 5.0))

        direction = getattr(signal, "direction", None)
        if direction is not None:
            d_str = str(direction).upper()
            feats["momentum_5d"] = 0.7 if "BUY" in d_str else (0.3 if "SELL" in d_str else 0.5)
        else:
            feats["momentum_5d"] = 0.5

    if snapshot is not None:
        vix = float(getattr(snapshot, "vix", 20.0))
        # Low VIX → high score (favourable environment); high VIX → low score
        feats["volatility_environment"] = max(0.0, min(1.0, 1.0 - (vix - 12.0) / 40.0))

        breadth = float(getattr(snapshot, "market_breadth", 0.5))
        feats["breadth_contribution"] = max(0.0, min(1.0, breadth))

        pcr = float(getattr(snapshot, "pcr", 1.0))
        # PCR ~0.8–1.2 neutral; below 0.8 bullish; above 1.2 bearish
        feats["pcr_sentiment"] = max(0.0, min(1.0, 1.0 - (pcr - 0.5) / 1.5))

        gs = float(getattr(snapshot, "global_sentiment_score", 0.0))
        # global_sentiment_score is typically -1 to +1
        feats["global_alignment"] = max(0.0, min(1.0, (gs + 1.0) / 2.0))

    return feats


# =============================================================================
# PIGTradingAdapter — Part 6 (Fallback)
# =============================================================================

class PIGTradingAdapter:
    """
    Lightweight adapter between the live trading pipeline and PIG.

    Responsibilities
    ----------------
    * Lazy-load ConsensusLibrary and IDRRepository on first query.
    * Build minimal MarketObservation from available signal + snapshot data.
    * Delegate to PlatformIntelligenceGateway.evaluate_symbol().
    * Return PlatformIntelligence or None — never raises.
    * Record per-call telemetry.

    Fallback behaviour (Part 6)
    ---------------------------
    If MLS infrastructure cannot be loaded (no DNA data, import failure,
    any exception), _ensure_init() sets _init_failed=True and subsequent
    calls return None immediately.  The pipeline continues unaffected.

    Thread safety
    -------------
    query() is fully thread-safe.  Library loading is protected by _init_lock.
    """

    def __init__(
        self,
        policy: Optional[PIGInfluencePolicy] = None,
        config: Any = None,
    ) -> None:
        self._policy    = policy or PIGInfluencePolicy()
        self._cfg       = config
        self._gateway   = None   # PlatformIntelligenceGateway
        self._library   = None   # ConsensusLibrary (loaded once; reloaded via reload_library)
        self._repo      = None   # IDRRepository
        self._init_lock = threading.Lock()
        self._init_done = False
        self._init_failed = False
        self.telemetry  = PIGTelemetry()
        log.info("[PIGTradingAdapter] Initialised (lazy-load).")

    # ── initialisation ────────────────────────────────────────────────────────

    def _ensure_init(self) -> bool:
        """Lazy-load MLS infrastructure.  Returns True if ready."""
        if self._init_done:
            return True
        if self._init_failed:
            return False

        with self._init_lock:
            if self._init_done or self._init_failed:
                return self._init_done
            try:
                from market_learning.pig_gateway import PlatformIntelligenceGateway
                from market_learning.dna_consensus_engine import DNAConsensusEngine
                from market_learning.idr_repository import IDRRepository

                self._gateway = PlatformIntelligenceGateway(config=self._cfg)
                ce = DNAConsensusEngine(config=self._cfg)
                self._library = ce.master_library()
                self._repo    = IDRRepository(config=self._cfg)

                n_dna = len(self._library.all_consensus) if self._library else 0
                log.info("[PIGTradingAdapter] Ready. DNA records: %d", n_dna)
                self._init_done = True
                return True
            except Exception as exc:
                log.warning(
                    "[PIGTradingAdapter] Init failed — trading continues without PIG: %s",
                    exc,
                )
                self._init_failed = True
                return False

    # ── public API ────────────────────────────────────────────────────────────

    def reload_library(self) -> None:
        """Reload ConsensusLibrary from disk (call after daily DNA update)."""
        try:
            from market_learning.dna_consensus_engine import DNAConsensusEngine
            ce  = DNAConsensusEngine(config=self._cfg)
            lib = ce.master_library()
            with self._init_lock:
                self._library = lib
            log.info("[PIGTradingAdapter] Library reloaded. DNA: %d",
                     len(lib.all_consensus) if lib else 0)
        except Exception as exc:
            log.warning("[PIGTradingAdapter] Library reload failed: %s", exc)

    def query(
        self,
        symbol:   str,
        signal:   Optional[Any] = None,
        snapshot: Optional[Any] = None,
    ) -> Optional[Any]:   # PlatformIntelligence | None
        """
        Query PIG for one symbol.  Returns None on any failure (never raises).

        Parameters
        ----------
        symbol   : NSE ticker
        signal   : optional TradeSignal — used to build MarketObservation features
        snapshot : optional MarketSnapshot — used for market context features
        """
        t0 = time.monotonic()

        def _fail(reason: str) -> None:
            lat = (time.monotonic() - t0) * 1000
            if self._policy.telemetry_enabled:
                self.telemetry.record(PIGCallRecord(
                    symbol=symbol, latency_ms=round(lat, 1),
                    available=False, ca_pmci=0.0, evidence_count=0, error=reason,
                ))

        try:
            if not self._ensure_init():
                _fail("init_failed")
                return None

            if not self._library or not len(self._library.all_consensus):
                _fail("no_dna_data")
                return None

            features    = _build_observation_features(symbol, signal, snapshot)
            observation = self._make_observation(symbol, features)

            pi = self._gateway.evaluate_symbol(
                symbol=symbol,
                observation=observation,
                library=self._library,
                market_snapshot=snapshot,
                repo=self._repo,
            )
            lat = (time.monotonic() - t0) * 1000
            if self._policy.telemetry_enabled:
                self.telemetry.record(PIGCallRecord(
                    symbol=symbol,
                    latency_ms=round(lat, 1),
                    available=True,
                    ca_pmci=float(getattr(pi, "ca_pmci", 0.0)),
                    evidence_count=int(getattr(pi, "evidence_count", 0)),
                ))
            return pi

        except Exception as exc:
            log.debug("[PIGTradingAdapter] query(%s) failed: %s", symbol, exc)
            _fail(str(exc)[:80])
            return None

    def is_available(self) -> bool:
        """True if MLS infrastructure loaded successfully."""
        return self._init_done and not self._init_failed

    def dna_count(self) -> int:
        """Number of DNA records in the currently loaded library."""
        if self._library is None:
            return 0
        return len(self._library.all_consensus)

    # ── private ────────────────────────────────────────────────────────────────

    def _make_observation(self, symbol: str, features: Dict[str, float]) -> Any:
        from market_learning.market_observer_models import MarketObservation
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return MarketObservation(
            symbol=symbol,
            feature_timestamp=ts,
            features=features,
            feature_count=len(features),
        )

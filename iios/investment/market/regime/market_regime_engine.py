"""iios/investment/market/regime/market_regime_engine.py
Institutional Market Regime Engine — authoritative regime source for IIOS.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from iios.investment.market.market_constants import MarketRegime
from iios.investment.market.regime.confidence_history import ConfidenceHistory
from iios.investment.market.regime.models import (
    RegimeObservation,
    RegimeSnapshot,
    RegimeType,
    StrategyCompatibility,
    TransitionEvent,
    regime_type_to_market_regime,
)
from iios.investment.market.regime.regime_classifier import (
    DefaultRegimeClassifier,
    RegimeClassifier,
)
from iios.investment.market.regime.regime_confidence import RegimeConfidenceCalculator
from iios.investment.market.regime.regime_detector import RegimeDetector
from iios.investment.market.regime.regime_history import RegimeHistory
from iios.investment.market.regime.regime_score import RegimeScorer
from iios.investment.market.regime.regime_state import RegimeState
from iios.investment.market.regime.regime_transition import RegimeTransition
from iios.investment.market.regime.strategy_regime_mapper import StrategyRegimeMapper
from iios.investment.market.regime.transition_detector import TransitionDetector
from iios.investment.market.regime.transition_probability import TransitionProbabilityModel
from iios.investment.market.regime.transition_statistics import TransitionStatistics

if TYPE_CHECKING:
    from iios.investment.market.structure.models import MarketStructureSnapshot
    from iios.investment.market.market_state.market_snapshot import MarketSnapshot

logger = logging.getLogger(__name__)


class InstitutionalMarketRegimeEngine:
    """
    Authoritative market regime source for IIOS.

    Consumes MarketStructureSnapshot from InstitutionalMarketStructureEngine.
    Maintains current regime, tracks transitions, publishes events.
    Thread-safe. Supports incremental, batch, and async updates.

    Contract:
      - Every strategy must call update() after each structure update
      - No strategy computes its own regime
      - Regime history is persistent within engine lifetime
    """

    def __init__(
        self,
        symbol: str,
        market_id: str = "",
        detector: Optional[RegimeDetector] = None,
        transition_detector: Optional[TransitionDetector] = None,
        probability_model: Optional[TransitionProbabilityModel] = None,
        confidence_calculator: Optional[RegimeConfidenceCalculator] = None,
        scorer: Optional[RegimeScorer] = None,
        strategy_mapper: Optional[StrategyRegimeMapper] = None,
        history_size: int = 500,
    ) -> None:
        self._symbol:         str    = symbol
        self._market_id:      str    = market_id or symbol

        self._detector:           RegimeDetector            = detector or RegimeDetector()
        self._trans_detector:     TransitionDetector        = transition_detector or TransitionDetector()
        self._prob_model:         TransitionProbabilityModel = probability_model or TransitionProbabilityModel()
        self._conf_calc:          RegimeConfidenceCalculator = confidence_calculator or RegimeConfidenceCalculator()
        self._scorer:             RegimeScorer               = scorer or RegimeScorer()
        self._mapper:             StrategyRegimeMapper       = strategy_mapper or StrategyRegimeMapper()

        self._state:              RegimeState               = RegimeState(self._market_id, symbol)
        self._conf_history:       ConfidenceHistory          = ConfidenceHistory(max_size=history_size)
        self._stats:              TransitionStatistics       = TransitionStatistics()
        self._legacy_history:     RegimeHistory              = RegimeHistory()

        self._snapshots:          deque[RegimeSnapshot]      = deque(maxlen=history_size)
        self._transition_events:  deque[TransitionEvent]     = deque(maxlen=history_size)

        self._current:            Optional[RegimeSnapshot]  = None
        self._prev_obs:           Optional[RegimeObservation] = None

        self._lock:               threading.RLock           = threading.RLock()

        # Callbacks
        self._on_regime_change_cbs:  List[Callable[[RegimeSnapshot, RegimeSnapshot], None]] = []
        self._on_transition_cbs:     List[Callable[[TransitionEvent], None]]                = []
        self._on_update_cbs:         List[Callable[[RegimeSnapshot], None]]                 = []

    # ── Core API ──────────────────────────────────────────────────────────────

    def update(
        self,
        structure_snapshot: "MarketStructureSnapshot",
        market_snapshot: Optional["MarketSnapshot"] = None,
    ) -> RegimeSnapshot:
        """Thread-safe incremental update."""
        with self._lock:
            # 1. Build observation
            obs = self._detector.observe(structure_snapshot, market_snapshot)

            # 2. Detect regime
            primary, secondary, base_conf = self._detector.detect(obs)

            # 3. Snapshot current state before mutation
            old_regime = self._state.current_regime()
            old_bars   = self._state.bars_in_current()
            prev_snap  = self._current

            # 4. Detect transition event
            trans_event = self._trans_detector.detect(
                obs, self._prev_obs, old_regime, old_bars
            )
            if trans_event is not None:
                trans_event.market_id = self._market_id
                self._transition_events.append(trans_event)
                for cb in self._on_transition_cbs:
                    try:
                        cb(trans_event)
                    except Exception:
                        logger.warning("on_transition callback raised", exc_info=True)

            # 5. Update state + Markov model
            changed = self._state.set_current(primary)
            if changed and old_regime != RegimeType.UNKNOWN:
                self._prob_model.update(old_regime, primary)
                self._stats.record_regime_end(old_regime, old_bars)
                self._stats.record_transition(old_regime, primary)

            new_bars   = self._state.bars_in_current()

            # 6. Confidence
            trans_prob = self._prob_model.transition_probability(primary)
            confidence = self._conf_calc.calculate(obs, primary, new_bars, trans_prob)

            # 7. Score + stability
            self._conf_history.record(
                self._market_id, confidence, primary, structure_snapshot.timestamp
            )
            stability  = self._conf_history.stability_score(self._market_id)
            reg_score  = self._scorer.score(obs, primary, new_bars, trans_prob, stability)

            # 8. Build snapshot
            snap = RegimeSnapshot(
                market_id=self._market_id,
                symbol=self._symbol,
                primary=primary,
                secondary=secondary,
                confidence=confidence,
                stability=stability,
                persistence_score=reg_score.persistence_score / 100.0,
                duration_bars=new_bars,
                transition_probability=trans_prob,
                market_regime=regime_type_to_market_regime(primary),
                timestamp=structure_snapshot.timestamp,
                observation=obs,
            )

            self._snapshots.append(snap)
            self._current = snap
            self._prev_obs = obs

            # 9. Legacy RegimeHistory on change
            if changed:
                transition = RegimeTransition(
                    market_id=self._market_id,
                    from_regime=regime_type_to_market_regime(old_regime),
                    to_regime=regime_type_to_market_regime(primary),
                    confidence=confidence,
                    trigger=f"regime_engine:{primary.value}",
                    duration_bars=old_bars,
                )
                self._legacy_history.record(transition)

                if prev_snap is not None:
                    for cb in self._on_regime_change_cbs:
                        try:
                            cb(prev_snap, snap)
                        except Exception:
                            logger.warning("on_regime_change callback raised", exc_info=True)

            # 10. Update callbacks
            for cb in self._on_update_cbs:
                try:
                    cb(snap)
                except Exception:
                    logger.warning("on_update callback raised", exc_info=True)

            return snap

    def update_batch(
        self,
        structure_snapshots: List["MarketStructureSnapshot"],
        market_snapshots: Optional[List["MarketSnapshot"]] = None,
    ) -> RegimeSnapshot:
        """Process a list of structure snapshots. Returns final regime."""
        last: Optional[RegimeSnapshot] = None
        for i, ss in enumerate(structure_snapshots):
            ms = None
            if market_snapshots and i < len(market_snapshots):
                ms = market_snapshots[i]
            last = self.update(ss, ms)
        if last is None:
            return RegimeSnapshot(market_id=self._market_id, symbol=self._symbol)
        return last

    async def async_update(
        self,
        structure_snapshot: "MarketStructureSnapshot",
        market_snapshot: Optional["MarketSnapshot"] = None,
    ) -> RegimeSnapshot:
        """Async wrapper over update() using run_in_executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.update, structure_snapshot, market_snapshot
        )

    # ── Query API ─────────────────────────────────────────────────────────────

    def current(self) -> Optional[RegimeSnapshot]:
        with self._lock:
            return self._current

    def current_regime_type(self) -> RegimeType:
        with self._lock:
            return self._state.current_regime()

    def current_market_regime(self) -> MarketRegime:
        with self._lock:
            regime = self._state.current_regime()
            return regime_type_to_market_regime(regime)

    def confidence(self) -> float:
        with self._lock:
            return self._current.confidence if self._current else 0.0

    def stability(self) -> float:
        with self._lock:
            return self._conf_history.stability_score(self._market_id)

    def transition_probability(self) -> float:
        with self._lock:
            regime = self._state.current_regime()
            return self._prob_model.transition_probability(regime)

    def bars_in_regime(self) -> int:
        with self._lock:
            return self._state.bars_in_current()

    def regime_history(self, n: int = 20) -> List[RegimeSnapshot]:
        with self._lock:
            items = list(self._snapshots)
            return items[-n:] if len(items) >= n else items

    def regime_timeline(self) -> List[Dict[str, Any]]:
        """Regime changes with timestamps (from legacy RegimeHistory)."""
        transitions = self._legacy_history.recent(n=1000)
        return [t.to_dict() for t in transitions]

    def transition_timeline(self, n: int = 20) -> List[TransitionEvent]:
        with self._lock:
            items = list(self._transition_events)
            return items[-n:] if len(items) >= n else items

    def strategy_compatibility(self) -> StrategyCompatibility:
        with self._lock:
            regime = self._state.current_regime()
        return self._mapper.compatibility(regime)

    def is_strategy_allowed(self, strategy_type: str) -> bool:
        with self._lock:
            regime = self._state.current_regime()
        return self._mapper.is_allowed(strategy_type, regime)

    def is_strategy_blocked(self, strategy_type: str) -> bool:
        with self._lock:
            regime = self._state.current_regime()
        return self._mapper.is_blocked(strategy_type, regime)

    def is_strategy_discouraged(self, strategy_type: str) -> bool:
        with self._lock:
            regime = self._state.current_regime()
        return self._mapper.is_discouraged(strategy_type, regime)

    def check_trade(
        self,
        strategy_type: str,
        direction: str,
        structure_quality: float = 50.0,
        trend_confirmed: bool = False,
    ) -> Tuple[bool, str]:
        with self._lock:
            regime = self._state.current_regime()
        return self._mapper.check_trade(
            strategy_type=strategy_type,
            regime=regime,
            direction=direction,
            structure_quality=structure_quality,
            trend_confirmed=trend_confirmed,
        )

    def transition_statistics(self) -> TransitionStatistics:
        return self._stats

    def probability_model(self) -> TransitionProbabilityModel:
        return self._prob_model

    # ── Event API ─────────────────────────────────────────────────────────────

    def on_regime_change(
        self, cb: Callable[["RegimeSnapshot", "RegimeSnapshot"], None]
    ) -> None:
        with self._lock:
            self._on_regime_change_cbs.append(cb)

    def on_transition_detected(self, cb: Callable[[TransitionEvent], None]) -> None:
        with self._lock:
            self._on_transition_cbs.append(cb)

    def on_update(self, cb: Callable[["RegimeSnapshot"], None]) -> None:
        with self._lock:
            self._on_update_cbs.append(cb)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def market_id(self) -> str:
        return self._market_id


# ── Backward-compatibility wrapper ────────────────────────────────────────────

class MarketRegimeEngine:
    """
    Backward-compatible engine preserving original interface.
    Uses legacy MarketSnapshot (not MarketStructureSnapshot) interface.
    """

    def __init__(
        self,
        classifier: Optional["RegimeClassifier"] = None,
        history: Optional[RegimeHistory] = None,
    ) -> None:
        self._lock:       threading.RLock         = threading.RLock()
        self._classifier: RegimeClassifier        = classifier or DefaultRegimeClassifier()
        self._history:    RegimeHistory           = history or RegimeHistory()
        self._current:    Dict[str, MarketRegime] = {}
        self._confidence: Dict[str, float]        = {}
        self._bars:       Dict[str, int]          = {}

    def classify(
        self,
        market_id: str,
        snapshot: "MarketSnapshot",
        history: list["MarketSnapshot"] | None = None,
    ) -> Tuple[MarketRegime, float]:
        regime, confidence = self._classifier.classify(snapshot, history or [])
        with self._lock:
            prev = self._current.get(market_id, MarketRegime.UNKNOWN)
            if prev != regime:
                bars = self._bars.get(market_id, 0)
                transition = RegimeTransition(
                    market_id=market_id,
                    from_regime=prev,
                    to_regime=regime,
                    confidence=confidence,
                    trigger=f"classifier:{self._classifier.classifier_id}",
                    duration_bars=bars,
                    timestamp=time.time(),
                )
                self._history.record(transition)
                self._bars[market_id] = 0
            else:
                self._bars[market_id] = self._bars.get(market_id, 0) + 1
            self._current[market_id]    = regime
            self._confidence[market_id] = confidence
        return regime, confidence

    def current_regime(self, market_id: str) -> MarketRegime:
        with self._lock:
            return self._current.get(market_id, MarketRegime.UNKNOWN)

    def confidence(self, market_id: str) -> float:
        with self._lock:
            return self._confidence.get(market_id, 0.0)

    def regime_history(self) -> RegimeHistory:
        return self._history

    def set_classifier(self, classifier: "RegimeClassifier") -> None:
        with self._lock:
            self._classifier = classifier

    def known_markets(self) -> list[str]:
        with self._lock:
            return list(self._current.keys())

    def bars_in_current_regime(self, market_id: str) -> int:
        with self._lock:
            return self._bars.get(market_id, 0)

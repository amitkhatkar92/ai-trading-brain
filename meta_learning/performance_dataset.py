"""
Meta-Learning — Performance Dataset
=====================================
Persistent store of historical (market_features, strategy, result) records.
This is the training data that the MetaModel learns from.

Each record captures:
  • The market feature vector at the time of the trade
  • Which strategy generated the trade
  • The outcome (R-multiple, won/lost, return_pct)
  • The date and regime for human-readable inspection

Records are persisted to JSON so the AI accumulates knowledge across
sessions.  The dataset grows daily and is used for weekly model retraining.

Dataset file: data/ml_performance_dataset.json
"""

from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass
from datetime   import date
from typing     import Optional

from utils import get_logger

log = get_logger(__name__)

DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "ml_performance_dataset.json"
)

# Minimum records before model training is meaningful
MIN_RECORDS_TO_TRAIN = 20


@dataclass
class PerformanceRecord:
    """One (features, strategy, result) observation."""
    date:             str           # YYYY-MM-DD
    strategy:         str
    regime:           str
    vix:              float
    breadth:          float
    fii_flow:         str
    global_sentiment: float
    sector_strength:  float
    pcr:              float
    volatility_level: str
    r_multiple:       float         # positive = win, negative = loss
    return_pct:       float
    won:              bool

    def feature_dict(self) -> dict:
        return {
            "regime":           self.regime,
            "vix":              self.vix,
            "breadth":          self.breadth,
            "fii_flow":         self.fii_flow,
            "global_sentiment": self.global_sentiment,
            "sector_strength":  self.sector_strength,
            "pcr":              self.pcr,
            "volatility_level": self.volatility_level,
        }


class PerformanceDataset:
    """
    Append-only log of (market_conditions, strategy, outcome) records.
    Backed by a JSON file for persistence.

    Usage::
        ds = PerformanceDataset()
        ds.add(record)
        records = ds.get_all()
        records = ds.get_by_strategy("Mean_Reversion")
        ds.save()
    """

    def __init__(self, path: str = DATASET_PATH) -> None:
        self._path    = path
        self._records: list[PerformanceRecord] = []
        self._load()
        log.info("[PerformanceDataset] Initialised. %d records loaded from disk.",
                 len(self._records))

    # ── Public API ────────────────────────────────────────────────────────
    def add(self, record: PerformanceRecord) -> None:
        self._records.append(record)

    def add_from_trade(
        self,
        strategy:         str,
        snapshot,                    # MarketSnapshot object
        r_multiple:       float,
        return_pct:       float,
        won:              bool,
        trade_date:       Optional[str] = None,
    ) -> None:
        """Helper: build a record from a live trade and market snapshot."""
        regime  = getattr(snapshot, "regime", None)
        regime_v = regime.value if hasattr(regime, "value") else str(regime)
        vol_obj  = getattr(snapshot, "volatility", None)
        vol_v    = vol_obj.value if hasattr(vol_obj, "value") else str(vol_obj)

        rec = PerformanceRecord(
            date             = trade_date or str(date.today()),
            strategy         = strategy,
            regime           = regime_v,
            vix              = float(getattr(snapshot, "vix",             18.0)),
            breadth          = float(getattr(snapshot, "market_breadth",  55.0)),
            fii_flow         = str  (getattr(snapshot, "fii_flow",        "neutral")),
            global_sentiment = float(getattr(snapshot, "global_sentiment", 0.5)),
            sector_strength  = float(getattr(snapshot, "sector_strength",  0.5)),
            pcr              = float(getattr(snapshot, "pcr",              1.0)),
            volatility_level = vol_v,
            r_multiple       = round(r_multiple, 4),
            return_pct       = round(return_pct, 4),
            won              = won,
        )
        self.add(rec)

    def get_all(self) -> list[PerformanceRecord]:
        return list(self._records)

    def get_by_strategy(self, strategy: str) -> list[PerformanceRecord]:
        return [r for r in self._records if r.strategy == strategy]

    def get_by_regime(self, regime: str) -> list[PerformanceRecord]:
        return [r for r in self._records if r.regime.lower() == regime.lower()]

    def strategy_names(self) -> list[str]:
        return sorted(set(r.strategy for r in self._records))

    def record_count(self) -> int:
        return len(self._records)

    def is_ready_for_training(self) -> bool:
        return len(self._records) >= MIN_RECORDS_TO_TRAIN

    def save(self) -> None:
        """Persist records to JSON (append mode — never overwrites history)."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            data = [asdict(r) for r in self._records]
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log.debug("[PerformanceDataset] Saved %d records to %s",
                      len(data), self._path)
        except Exception as exc:
            log.warning("[PerformanceDataset] Could not save dataset: %s", exc)

    # ── Private helpers ───────────────────────────────────────────────────
    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in data:
                try:
                    self._records.append(PerformanceRecord(**d))
                except TypeError:
                    pass   # schema mismatch — skip old records
        except Exception as exc:
            log.warning("[PerformanceDataset] Could not load dataset: %s", exc)

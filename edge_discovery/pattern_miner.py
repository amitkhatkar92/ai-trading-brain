"""
Pattern Miner — Edge Discovery Engine Module 2
==============================================
Searches for statistically reliable feature combinations that predict
profitable forward price moves.

Algorithm:
  1. Load the historical feature database (data/ede_feature_db.json)
     — each row is a {features: FeatureVector, forward_return: float}
  2. Build a labelled dataset:   label = 1 if forward_return > THRESHOLD else 0
  3. Fit a DecisionTreeClassifier (sklearn) to find decision rules
  4. Extract all leaf nodes where precision ≥ MIN_PRECISION and
     support ≥ MIN_SUPPORT
  5. Convert each qualifying leaf into a DiscoveredPattern

Each DiscoveredPattern is essentially an IF-THEN rule:
  IF   feature_A > threshold_A
  AND  feature_B < threshold_B
  THEN expected_positive_rate = X%  (support = N samples)

The miner also runs a correlation sweep to surface single-feature
predictors as simple-but-reliable edges.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from utils import get_logger

log = get_logger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────
FORWARD_RETURN_THRESHOLD = 0.008   # 0.8% — minimum "profitable" move
MIN_PRECISION           = 0.58    # 58% hit rate = genuine edge above random
MIN_SUPPORT             = 15      # minimum number of historical samples
MAX_TREE_DEPTH          = 4       # shallow trees = more interpretable rules
MAX_PATTERNS            = 20      # cap on patterns returned per run

# ── Feature DB path ────────────────────────────────────────────────────────
_HERE    = os.path.dirname(__file__)
FEAT_DB_PATH = os.path.join(_HERE, "..", "data", "ede_feature_db.json")


@dataclass
class PatternCondition:
    """One condition in a discovered IF-THEN rule."""
    feature:   str
    operator:  str    # ">" or "<="
    threshold: float


@dataclass
class DiscoveredPattern:
    """
    A statistically validated IF-THEN market pattern.

    Attributes:
        pattern_id      unique identifier
        conditions      list of PatternCondition
        precision       fraction of samples hitting the outcome
        support         number of matching historical samples
        expected_return average forward return when conditions hold
        category        inferred edge type (momentum / reversion / volatility …)
        source_features top features that define this pattern
    """
    pattern_id:      str
    conditions:      List[PatternCondition]
    precision:       float
    support:         int
    expected_return: float
    category:        str                = "unknown"
    source_features: List[str]          = field(default_factory=list)
    description:     str                = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id":      self.pattern_id,
            "conditions":      [
                {"feature": c.feature, "operator": c.operator,
                 "threshold": round(c.threshold, 6)}
                for c in self.conditions
            ],
            "precision":       round(self.precision, 4),
            "support":         self.support,
            "expected_return": round(self.expected_return, 6),
            "category":        self.category,
            "source_features": self.source_features,
            "description":     self.description,
        }


class PatternMiner:
    """
    Discovers predictive patterns from the historical feature database
    using decision-tree rule extraction.

    Requires scikit-learn (already in requirements.txt).
    """

    def __init__(self) -> None:
        log.info("[PatternMiner] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def mine(self, feature_db: List[Dict[str, Any]]) -> List[DiscoveredPattern]:
        """
        Run the full pattern mining pipeline.

        Args:
            feature_db: list of {'features': dict, 'forward_return': float}
        Returns:
            List of DiscoveredPattern, sorted by precision desc
        """
        if len(feature_db) < MIN_SUPPORT * 2:
            log.info("[PatternMiner] Insufficient data (%d rows). Skipping.",
                     len(feature_db))
            return []

        X, y, feat_names = self._build_matrix(feature_db)
        log.info("[PatternMiner] Matrix: %d samples × %d features, "
                 "positive rate=%.1f%%",
                 len(X), len(feat_names), 100 * y.mean())

        tree_patterns   = self._tree_rule_extraction(X, y, feat_names)
        corr_patterns   = self._correlation_sweep(X, y, feat_names)
        all_patterns    = tree_patterns + corr_patterns

        # Deduplicate and sort
        seen = set()
        unique = []
        for p in sorted(all_patterns, key=lambda x: -x.precision):
            key = frozenset(c.feature for c in p.conditions)
            if key not in seen:
                seen.add(key)
                unique.append(p)
        result = unique[:MAX_PATTERNS]
        log.info("[PatternMiner] Discovered %d patterns (qualified).", len(result))
        return result

    # ── Internal ───────────────────────────────────────────────────────────

    def _build_matrix(
        self, db: List[Dict]
    ) -> Tuple["np.ndarray", "np.ndarray", List[str]]:
        """Convert feature dicts → numpy arrays."""
        all_keys = sorted(
            {k for row in db for k in row.get("features", {}).keys()}
        )
        X = np.array([
            [row.get("features", {}).get(k, 0.0) for k in all_keys]
            for row in db
        ], dtype=float)
        y = np.array([
            1 if row.get("forward_return", 0.0) >= FORWARD_RETURN_THRESHOLD else 0
            for row in db
        ], dtype=int)
        # Replace any NaN/Inf
        X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=0.0)
        return X, y, all_keys

    def _tree_rule_extraction(
        self,
        X: "np.ndarray",
        y: "np.ndarray",
        feat_names: List[str],
    ) -> List[DiscoveredPattern]:
        """
        Fit a shallow decision tree, then walk every path from root to leaf
        to extract IF-THEN rules.
        """
        try:
            from sklearn.tree import DecisionTreeClassifier, _tree
        except ImportError:
            log.warning("[PatternMiner] scikit-learn not available — "
                        "skipping tree extraction.")
            return []

        clf = DecisionTreeClassifier(
            max_depth=MAX_TREE_DEPTH,
            min_samples_leaf=MIN_SUPPORT,
            class_weight="balanced",
            random_state=42,
        )
        clf.fit(X, y)

        tree = clf.tree_
        patterns: List[DiscoveredPattern] = []
        pid_counter = [0]

        def _walk(node_id: int, conditions: List[PatternCondition]) -> None:
            if tree.feature[node_id] == _tree.TREE_UNDEFINED:
                # Leaf node
                node_samples = int(tree.n_node_samples[node_id])
                # class_1 count / total
                values = tree.value[node_id][0]
                total  = values.sum()
                if total == 0:
                    return
                precision = values[1] / total if len(values) > 1 else 0.0
                support   = node_samples
                if precision >= MIN_PRECISION and support >= MIN_SUPPORT:
                    pid = f"TREE_{pid_counter[0]:04d}"
                    pid_counter[0] += 1
                    src  = [c.feature for c in conditions]
                    cat  = _infer_category(src)
                    desc = _build_description(conditions, precision, support)
                    patterns.append(DiscoveredPattern(
                        pattern_id=pid,
                        conditions=list(conditions),
                        precision=float(precision),
                        support=support,
                        expected_return=float(precision * 0.018),   # approx
                        category=cat,
                        source_features=src,
                        description=desc,
                    ))
                return

            feat_idx   = tree.feature[node_id]
            threshold  = tree.threshold[node_id]
            feat_name  = feat_names[feat_idx]

            # Left branch: feature <= threshold
            _walk(tree.children_left[node_id],
                  conditions + [PatternCondition(feat_name, "<=", threshold)])
            # Right branch: feature > threshold
            _walk(tree.children_right[node_id],
                  conditions + [PatternCondition(feat_name, ">", threshold)])

        _walk(0, [])
        return patterns

    def _correlation_sweep(
        self,
        X: "np.ndarray",
        y: "np.ndarray",
        feat_names: List[str],
    ) -> List[DiscoveredPattern]:
        """
        Quick univariate scan: for each feature find the split point
        that maximises precision.
        """
        patterns: List[DiscoveredPattern] = []
        for i, feat in enumerate(feat_names):
            col = X[:, i]
            # Try split at median and 75th percentile
            for split in [float(np.percentile(col, 50)),
                          float(np.percentile(col, 75))]:
                mask_high = col > split
                mask_low  = col <= split
                for mask, op in [(mask_high, ">"), (mask_low, "<=")]:
                    if mask.sum() < MIN_SUPPORT:
                        continue
                    prec = float(y[mask].mean())
                    if prec >= MIN_PRECISION:
                        pid = f"CORR_{feat}_{op.strip('=')}_{split:.3f}"
                        patterns.append(DiscoveredPattern(
                            pattern_id=pid,
                            conditions=[PatternCondition(feat, op, split)],
                            precision=prec,
                            support=int(mask.sum()),
                            expected_return=prec * 0.012,
                            category=_infer_category([feat]),
                            source_features=[feat],
                            description=f"{feat} {op} {split:.3f} → {prec:.0%} hit rate",
                        ))
        return patterns


# ── Helpers ────────────────────────────────────────────────────────────────

def _infer_category(features: List[str]) -> str:
    """Classify a pattern into an edge category based on its features."""
    f = " ".join(features).lower()
    if any(k in f for k in ("volume_spike", "volume_ratio", "breakout")):
        return "momentum_volume"
    if any(k in f for k in ("rsi_oversold", "bb_lower", "mean_rev")):
        return "mean_reversion"
    if any(k in f for k in ("iv_", "pcr", "options", "straddle")):
        return "volatility"
    if any(k in f for k in ("sector", "fii", "institutional")):
        return "macro_flow"
    if any(k in f for k in ("mom_", "macd_bull", "strong_trend")):
        return "momentum_trend"
    if any(k in f for k in ("gap_up", "gap_down")):
        return "gap"
    return "composite"


def _build_description(conditions: List[PatternCondition],
                        precision: float, support: int) -> str:
    parts = [f"{c.feature} {c.operator} {c.threshold:.3f}" for c in conditions]
    return (f"IF {' AND '.join(parts)} "
            f"THEN bullish with {precision:.0%} hit rate (n={support})")


# ── Feature DB persistence ─────────────────────────────────────────────────

def load_feature_db() -> List[Dict[str, Any]]:
    if not os.path.exists(FEAT_DB_PATH):
        return []
    try:
        with open(FEAT_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.warning("[PatternMiner] Could not load feature DB: %s", exc)
        return []


def save_feature_db(db: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(FEAT_DB_PATH), exist_ok=True)
    try:
        with open(FEAT_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db[-5_000:], f, indent=2)   # keep last 5 000 rows
    except Exception as exc:
        log.warning("[PatternMiner] Could not save feature DB: %s", exc)


def bootstrap_feature_db(n: int = 500) -> List[Dict[str, Any]]:
    """
    Generate a synthetic historical feature database to seed the pattern miner
    before real data accumulates.

    Synthetic data follows realistic market distributions:
      - Bull periods: high momentum + volume → positive returns
      - Range periods: mean-reversion + IV → moderate returns
      - Bear periods: negative momentum → negative returns
    """
    from models.market_data import RegimeLabel, VolatilityLevel, MarketSnapshot
    from .feature_extractor import FeatureExtractor
    from datetime import datetime, timedelta

    log.info("[PatternMiner] Bootstrapping feature DB with %d synthetic rows…", n)
    extractor = FeatureExtractor()
    db = []
    rng = random.Random(42)
    base_dt = datetime(2024, 1, 1)

    for i in range(n):
        regime  = rng.choice([
            RegimeLabel.BULL_TREND, RegimeLabel.BULL_TREND,   # 2× weight
            RegimeLabel.RANGE_MARKET, RegimeLabel.RANGE_MARKET,
            RegimeLabel.BEAR_MARKET,
        ])
        vol = rng.choice([VolatilityLevel.LOW, VolatilityLevel.MEDIUM,
                          VolatilityLevel.HIGH])
        snap = MarketSnapshot(
            timestamp    = base_dt + timedelta(days=i // 5),
            indices      = {},
            regime       = regime,
            volatility   = vol,
            vix          = rng.uniform(10, 35),
            market_breadth = rng.uniform(0.2, 0.9),
            pcr          = rng.uniform(0.5, 1.8),
            global_sentiment_score = rng.uniform(-0.8, 0.8),
        )
        sym = rng.choice(FeatureExtractor.SYMBOL_UNIVERSE[:5])
        feats = extractor.extract(snap, [sym])
        if not feats:
            continue
        fv = feats[0].features

        # Simulate realistic forward return based on features
        base_ret = 0.0
        if regime == RegimeLabel.BULL_TREND:
            base_ret += 0.006
        elif regime == RegimeLabel.BEAR_MARKET:
            base_ret -= 0.004

        # Volume spike gives momentum boost
        base_ret += fv.get("volume_spike", 0) * rng.uniform(0.003, 0.015)
        # RSI oversold gives mean-reversion bounce
        base_ret += fv.get("rsi_oversold", 0) * rng.uniform(0.001, 0.008)
        # RSI overbought gives fade
        base_ret -= fv.get("rsi_overbought", 0) * rng.uniform(0.001, 0.006)
        # Trend
        base_ret += fv.get("macd_bull", 0) * rng.uniform(0.001, 0.005)

        forward_return = base_ret + rng.gauss(0, 0.006)
        db.append({"features": fv, "forward_return": forward_return})

    save_feature_db(db)
    log.info("[PatternMiner] Bootstrap complete. %d rows saved to %s", len(db), FEAT_DB_PATH)
    return db

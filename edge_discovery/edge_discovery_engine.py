"""
Edge Discovery Engine — Main Orchestrator
==========================================
The central controller that runs the complete edge discovery pipeline.

Pipeline:
  MarketSnapshot
       │
       ▼
  FeatureExtractor      → build feature vectors for 20 symbols
       │
       ▼
  PatternMiner          → mine decision-tree rules from historical DB
       │                  (bootstraps synthetic data on first run)
       ▼
  CandidateStrategyGenerator  → convert patterns into strategy templates
       │
       ▼
  StrategyTester        → walk-forward + OOS backtest each candidate
       │
       ▼
  EdgeRankingEngine     → score, rank and lifecycle-manage all edges
       │
       ▼
  strategy library      → approved edges written to evolved_strategies.json

Then:
  Event published: EDGE_DISCOVERED
  MetaStrategyController picks up new strategies on the next cycle.

When to run:
  • EOD batch         (via orchestrator.run_eod_learning)
  • Manual via CLI    python main.py --discover
  • Background worker (runs every N minutes via TaskQueue)
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.market_data import MarketSnapshot
from utils import get_logger

from .feature_extractor           import FeatureExtractor
from .pattern_miner               import PatternMiner, load_feature_db, save_feature_db, bootstrap_feature_db
from .candidate_strategy_generator import CandidateStrategyGenerator
from .strategy_tester             import StrategyTester, BacktestResult
from .edge_ranking_engine         import EdgeRankingEngine, EdgeRecord

log = get_logger(__name__)

# ── Min rows before mining (build more via append or bootstrap) ─────────────
MIN_DB_ROWS_TO_MINE = 100


class EdgeDiscoveryEngine:
    """
    Self-contained research scientist inside the trading brain.

    Usage inside orchestrator::

        # Initialise once
        self.edge_discovery = EdgeDiscoveryEngine()

        # At EOD or in background
        report = self.edge_discovery.run_discovery_cycle(snapshot)
        log.info(report)

    Trade outcome feedback (for live-edge tracking)::

        self.edge_discovery.record_outcome(strategy_name, won=True)
    """

    def __init__(self) -> None:
        self.feature_extractor  = FeatureExtractor()
        self.pattern_miner      = PatternMiner()
        self.candidate_generator = CandidateStrategyGenerator()
        self.strategy_tester    = StrategyTester()
        self.ranking_engine     = EdgeRankingEngine()
        log.info("[EdgeDiscoveryEngine] All sub-systems ready.")

    # ── Public API ─────────────────────────────────────────────────────────

    def run_discovery_cycle(
        self, snapshot: MarketSnapshot, publish_event: bool = True
    ) -> str:
        """
        Run a complete edge discovery cycle.

        Args:
            snapshot:       current MarketSnapshot (used for feature extraction
                            and to seed the feature database)
            publish_event:  if True, publish EDGE_DISCOVERED to the event bus

        Returns:
            A formatted discovery report string.
        """
        start_ts = datetime.now()
        log.info("═" * 60)
        log.info("  EDGE DISCOVERY ENGINE — Starting cycle")
        log.info("═" * 60)

        # ── STEP 1: Update feature database ────────────────────────────
        db = load_feature_db()
        if len(db) < MIN_DB_ROWS_TO_MINE // 2:
            log.info("[EDE] Feature DB insufficient (%d rows) — bootstrapping…", len(db))
            db = bootstrap_feature_db(n=600)
        else:
            new_rows = self._append_current_features(snapshot, db)
            if new_rows:
                db = db + new_rows
                save_feature_db(db)
                log.info("[EDE] Added %d new feature rows. DB size: %d", len(new_rows), len(db))

        # ── STEP 2: Mine patterns ───────────────────────────────────────
        if len(db) < MIN_DB_ROWS_TO_MINE:
            log.info("[EDE] Still insufficient data (%d / %d). Skipping mine pass.",
                     len(db), MIN_DB_ROWS_TO_MINE)
            return "Edge discovery skipped — insufficient data."

        patterns = self.pattern_miner.mine(db)
        if not patterns:
            log.info("[EDE] No qualifying patterns found this cycle.")
            return "No qualifying patterns found."

        log.info("[EDE] Discovered %d patterns.", len(patterns))

        # ── STEP 3: Generate candidates ─────────────────────────────────
        candidates = self.candidate_generator.generate(patterns)
        if not candidates:
            return "No candidate strategies generated."

        # ── STEP 4: Backtest ────────────────────────────────────────────
        candidates, bt_results = self.strategy_tester.test(candidates, db)

        # ── STEP 5: Rank + persist ──────────────────────────────────────
        n_promoted, n_deprecated = self.ranking_engine.update(candidates, bt_results)
        saved = self.candidate_generator.persist_approved(candidates)

        # ── STEP 6: Register new strategies in StrategyGeneratorAI ─────
        if saved > 0:
            self._hot_register_strategies(candidates)

        # ── STEP 7: Publish event ───────────────────────────────────────
        if publish_event and (n_promoted or n_deprecated):
            self._publish_event(n_promoted, n_deprecated, candidates)

        elapsed = (datetime.now() - start_ts).total_seconds()
        report = self._build_report(
            patterns, candidates, bt_results,
            n_promoted, n_deprecated, elapsed
        )
        log.info("[EDE] Cycle complete in %.1f s. Promoted=%d, Deprecated=%d",
                 elapsed, n_promoted, n_deprecated)
        return report

    def record_outcome(self, strategy_name: str, won: bool) -> None:
        """
        Feed live trade outcomes back into the ranking engine so that
        edges decaying in the live market are automatically retired.
        """
        if strategy_name.startswith("EDG_"):
            self.ranking_engine.record_trade_outcome(strategy_name, won)

    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Return active edges as strategy-param dicts for the MetaController."""
        return [
            {"name": e.name, **e.strategy_params}
            for e in self.ranking_engine.get_active_edges()
        ]

    def get_ranking_report(self) -> str:
        return self.ranking_engine.get_ranking_report()

    # ── Internal ───────────────────────────────────────────────────────────

    def _append_current_features(
        self,
        snapshot: MarketSnapshot,
        existing_db: List[Dict],
    ) -> List[Dict]:
        """
        Extract features from the current snapshot and append to the DB.
        Forward returns are unknown at this point; they are filled in by
        the learning engine after trades close (see `enrich_with_outcomes`).
        """
        import random
        rng = random.Random()

        symbol_features = self.feature_extractor.extract(snapshot)
        new_rows = []
        for sf in symbol_features:
            # We don't know the forward return yet — mark as 0 (neutral)
            # The learning engine enriches this later with actual outcomes
            new_rows.append({
                "features":       sf.features,
                "forward_return": 0.0,       # placeholder — updated by learning
                "symbol":         sf.symbol,
                "ts":             sf.ts_str,
            })
        return new_rows

    def enrich_with_outcomes(self, symbol: str, outcome_return: float) -> None:
        """
        Called by the learning engine after a trade closes to back-fill
        the actual forward return into the feature DB.
        """
        db = load_feature_db()
        for row in reversed(db):
            if row.get("symbol") == symbol and row.get("forward_return") == 0.0:
                row["forward_return"] = outcome_return
                break
        save_feature_db(db)

    def _hot_register_strategies(self, candidates: List) -> None:
        """
        Immediately register approved candidates into STRATEGY_PARAMS so they
        are available in this trading cycle without a restart.
        """
        try:
            from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
            for c in candidates:
                if c.approved and c.name not in STRATEGY_PARAMS:
                    STRATEGY_PARAMS[c.name] = c.to_strategy_params()
                    log.info("[EDE] Hot-registered strategy: %s", c.name)
        except Exception as exc:
            log.debug("[EDE] Hot-register failed: %s", exc)

    def _publish_event(
        self,
        n_promoted: int,
        n_deprecated: int,
        candidates: List,
    ) -> None:
        try:
            from communication.event_bus import get_bus
            from communication.events import EventType, SystemEvent
            bus = get_bus()
            bus.publish(SystemEvent(
                event_type=EventType.EDGE_DISCOVERED,
                source_agent="EdgeDiscoveryEngine",
                payload={
                    "promoted":    n_promoted,
                    "deprecated":  n_deprecated,
                    "top_edge":    candidates[0].name if candidates else "",
                    "active_edges": len(self.ranking_engine.get_active_edges()),
                },
            ))
        except Exception as exc:
            log.debug("[EDE] Event publish error: %s", exc)

    def _build_report(
        self,
        patterns, candidates, bt_results,
        n_promoted, n_deprecated, elapsed
    ) -> str:
        approved = [c for c in candidates if c.approved]
        width = 90
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "",
            "═" * width,
            f"  EDGE DISCOVERY REPORT   [{ts}]",
            "═" * width,
            f"  Patterns mined:     {len(patterns)}",
            f"  Candidates tested:  {len(candidates)}",
            f"  Approved:           {len(approved)}  (promoted to strategy library)",
            f"  Deprecated:         {n_deprecated}",
            f"  Elapsed:            {elapsed:.1f} s",
            "",
        ]
        if approved:
            lines.append(f"  {'Strategy':<33} {'Category':<15} {'Prec':>6} "
                         f"{'Sharpe':>7} {'WR':>6} {'AvgR':>6}")
            lines.append("  " + "─" * (width - 2))
            for cand in approved:
                res = next((r for r in bt_results if r.strategy_name == cand.name), None)
                if res:
                    lines.append(
                        f"  {cand.name:<33} {cand.category:<15} "
                        f"{cand.precision:>5.0%} "
                        f"{res.sharpe_ratio:>7.2f} "
                        f"{res.oos_win_rate:>5.0%} "
                        f"{res.avg_return_r:>6.2f}"
                    )
        lines.append("")
        lines.append(self.ranking_engine.get_ranking_report())
        lines.append("═" * width)
        return "\n".join(lines)

"""
Options Research Pipeline
==========================

Continuous background learning loop for the options knowledge system.

This is the component that transforms the options system from
"passive JSONL writer" to "genuinely self-learning".

Pipeline steps (runs every PIPELINE_INTERVAL_MINUTES minutes):
  1. READ     — Scan observation JSONL for new OUTCOME_OBSERVED records
                (tracks last-read position to avoid reprocessing)
  2. EXTRACT  — Extract feature vectors for each new outcome
  3. UPDATE   — Update pattern engine raw tables with new (feature, pnl) pairs
  4. DISCOVER — Run pattern discovery to find significant patterns
  5. KNOWLEDGE — Record outcomes in knowledge store; trigger state transitions
  6. VALIDATE — Run OOS/WFO validation for VALIDATING-state items
  7. HYPOTHESES — Auto-propose hypotheses from newly significant patterns
  8. COUNTERFACTUAL — Run counterfactual analysis for matured monitors
  9. SHADOW   — Update shadow scorer outcomes
  10. SUMMARISE — Write a daily research summary to data/options_research_log.md

The pipeline also starts at system startup and can be triggered on-demand
after a trade is closed.

Persistence:
  - Pipeline cursor: data/options_pipeline_cursor.json (last-processed line)
  - Research log: data/options_research_log.md (append-only, daily entries)

Singleton: get_options_research_pipeline()
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, date
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_CURSOR_PATH   = "data/options_pipeline_cursor.json"
_RESEARCH_LOG  = "data/options_research_log.md"

PIPELINE_INTERVAL_MINUTES = 5   # run every 5 minutes during market hours


class OptionsResearchPipeline:
    """
    Continuous learning pipeline for the options knowledge system.

    Runs in a background daemon thread.  All steps are wrapped in try/except
    to prevent pipeline failures from affecting production execution.
    """

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._running     = False
        self._thread: Optional[threading.Thread] = None
        self._cursor      = 0     # last-processed JSONL line index
        self._trigger_event = threading.Event()
        os.makedirs("data", exist_ok=True)
        self._load_cursor()

    # ── Public API ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background pipeline thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="OptionsResearchPipeline",
            daemon=True,
        )
        self._thread.start()
        log.info("[ResearchPipeline] Background pipeline started.")

    def stop(self) -> None:
        """Signal the pipeline to stop."""
        with self._lock:
            self._running = False
        self._trigger_event.set()
        log.info("[ResearchPipeline] Stop requested.")

    def trigger_now(self) -> None:
        """Trigger an immediate pipeline run (e.g. after a trade closes)."""
        self._trigger_event.set()

    def run_once(self) -> Dict:
        """
        Run one full pipeline cycle synchronously.
        Returns a summary dict.
        """
        return self._run_pipeline()

    # ── Background loop ────────────────────────────────────────────────────

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self._run_pipeline()
            except Exception as exc:
                log.debug("[ResearchPipeline] Unhandled error in loop: %s", exc)
            # Wait for trigger or next scheduled run
            self._trigger_event.wait(timeout=PIPELINE_INTERVAL_MINUTES * 60)
            self._trigger_event.clear()

    # ── Pipeline steps ─────────────────────────────────────────────────────

    def _run_pipeline(self) -> Dict:
        summary = {
            "run_at":         datetime.now().isoformat(),
            "new_outcomes":   0,
            "patterns_found": 0,
            "ks_updates":     0,
            "cf_analysed":    0,
            "hypos_proposed": 0,
        }

        try:
            # Step 1+2: Read new outcomes + extract features
            new_outcome_pairs = self._step_read_and_extract()
            summary["new_outcomes"] = len(new_outcome_pairs)

            if new_outcome_pairs:
                # Step 3+4: Update pattern engine
                patterns = self._step_pattern_analysis(new_outcome_pairs)
                summary["patterns_found"] = len(patterns)

                # Step 5: Update knowledge store
                ks_updates = self._step_knowledge_update(new_outcome_pairs)
                summary["ks_updates"] = ks_updates

            # Step 6: Validate VALIDATING-state items
            self._step_validate()

            # Step 7: Propose hypotheses from significant patterns
            hypos = self._step_hypotheses()
            summary["hypos_proposed"] = hypos

            # Step 8: Counterfactual analysis
            cf = self._step_counterfactual()
            summary["cf_analysed"] = cf

            # Step 9: Update shadow scorer outcomes
            self._step_shadow_outcomes(new_outcome_pairs)

            # Step 10: Daily summary
            self._step_daily_summary(summary)

        except Exception as exc:
            log.debug("[ResearchPipeline] Pipeline error: %s", exc)
            summary["error"] = str(exc)

        return summary

    def _step_read_and_extract(self) -> List:
        """Read new OUTCOME_OBSERVED records and extract feature vectors."""
        from execution_engine.options_observation_journal import (
            get_options_observation_journal, OBS_OUTCOME_OBSERVED
        )
        from knowledge_system.options_feature_extractor import extract_features

        journal   = get_options_observation_journal()
        all_rows  = journal.read_all()
        new_rows  = all_rows[self._cursor:]

        outcome_pairs = []  # (feature_vector, pnl, opportunity_id, observed_at)
        for row in new_rows:
            if row.get("state") == OBS_OUTCOME_OBSERVED:
                pnl = row.get("actual_pnl")
                if pnl is None:
                    continue
                fv = extract_features(row)
                if fv.is_valid:
                    outcome_pairs.append((
                        fv,
                        float(pnl),
                        row.get("opportunity_id"),
                        row.get("observed_at", ""),
                    ))

        # Advance cursor
        new_cursor = self._cursor + len(new_rows)
        if new_cursor != self._cursor:
            self._cursor = new_cursor
            self._save_cursor()

        return outcome_pairs

    def _step_pattern_analysis(self, outcome_pairs: List) -> List:
        """Update pattern engine and run discovery."""
        from knowledge_system.options_pattern_engine import get_options_pattern_engine
        engine = get_options_pattern_engine()
        for fv, pnl, _, ts in outcome_pairs:
            engine.process_observation(fv.strategy_name, fv, pnl, ts)
        return engine.run_discovery()

    def _step_knowledge_update(self, outcome_pairs: List) -> int:
        """Record outcomes in knowledge store for multiple context keys."""
        from knowledge_system.options_knowledge_store import get_options_knowledge_store

        store = get_options_knowledge_store()
        updates = 0
        for fv, pnl, opportunity_id, _ in outcome_pairs:
            # Index by the richest context key we have
            for ctx_key in [fv.regime_ivr_dte, fv.strategy_regime_dir]:
                if not ctx_key:
                    continue
                store.record_outcome(
                    strategy_name       = fv.strategy_name,
                    context_key         = ctx_key,
                    feature_components  = {
                        "regime":        fv.regime,
                        "ivr_band":      fv.ivr_band,
                        "dte_band":      fv.dte_band,
                        "direction":     fv.direction,
                        "vix_band":      fv.vix_band,
                        "strategy_name": fv.strategy_name,
                    },
                    pnl                 = pnl,
                    opportunity_id      = opportunity_id,
                )
                updates += 1
        return updates

    def _step_validate(self) -> None:
        """Run OOS/WFO validation for VALIDATING-state knowledge items."""
        from knowledge_system.options_knowledge_store import (
            get_options_knowledge_store, KS_VALIDATING
        )
        from knowledge_system.options_validator import validate_with_raw_outcomes
        from execution_engine.options_observation_journal import (
            get_options_observation_journal, OBS_OUTCOME_OBSERVED
        )

        store   = get_options_knowledge_store()
        journal = get_options_observation_journal()
        items   = store.get_items_by_state(KS_VALIDATING)

        for item in items:
            # Retrieve outcomes linked to this item
            outcomes_raw = []
            for oid in item.linked_opportunity_ids:
                recs = journal.read_by_opportunity_id(oid)
                for rec in recs:
                    if rec.get("state") == OBS_OUTCOME_OBSERVED:
                        pnl = rec.get("actual_pnl")
                        if pnl is not None:
                            win = 1 if float(pnl) > 0 else 0
                            outcomes_raw.append((win, float(pnl), rec.get("observed_at", "")))
            if outcomes_raw:
                validate_with_raw_outcomes(item, outcomes_raw)

    def _step_hypotheses(self) -> int:
        """Auto-propose hypotheses from significant patterns."""
        from knowledge_system.options_pattern_engine import get_options_pattern_engine
        from knowledge_system.options_hypothesis_engine import get_options_hypothesis_engine

        pattern_engine = get_options_pattern_engine()
        hyp_engine     = get_options_hypothesis_engine()
        count = 0
        for pattern in pattern_engine.get_significant_patterns():
            h = hyp_engine.propose_from_pattern(pattern)
            if h:
                count += 1

        # Update existing hypotheses from knowledge store state changes
        from knowledge_system.options_knowledge_store import get_options_knowledge_store
        store = get_options_knowledge_store()
        from knowledge_system.options_knowledge_store import (
            KS_VALIDATED, KS_AUTHENTICATED, KS_INVALIDATED
        )
        for item in store.get_items_by_state(KS_VALIDATED):
            hyp_engine.update_from_knowledge_item(item)
        for item in store.get_items_by_state(KS_AUTHENTICATED):
            hyp_engine.update_from_knowledge_item(item)
        for item in store.get_items_by_state(KS_INVALIDATED):
            hyp_engine.update_from_knowledge_item(item)

        return count

    def _step_counterfactual(self) -> int:
        """Run counterfactual analysis for matured monitors."""
        from knowledge_system.options_counterfactual_engine import (
            get_options_counterfactual_engine
        )
        engine = get_options_counterfactual_engine()
        results = engine.run_analysis()

        # Feed false-rejection outcomes back into knowledge store
        if results:
            from knowledge_system.options_knowledge_store import get_options_knowledge_store
            from knowledge_system.options_feature_extractor import extract_features
            store = get_options_knowledge_store()
            for m in results:
                if (m.rejection_classification == "REJECTION_INCORRECT"
                        and m.hypothetical_pnl is not None):
                    # Record the missed opportunity as a negative (we missed profit)
                    # Use a minimal synthetic observation for feature extraction
                    fv = extract_features({
                        "symbol":        m.symbol,
                        "strategy_name": m.strategy_name,
                        "direction":     m.direction,
                        "regime":        m.regime_at_rejection,
                        "confidence":    m.confidence,
                    })
                    if fv.is_valid:
                        # Record with negative pnl to signal "we should have traded this"
                        store.record_outcome(
                            strategy_name      = m.strategy_name,
                            context_key        = fv.regime_ivr_dte,
                            feature_components = {},
                            pnl                = m.hypothetical_pnl,
                            opportunity_id     = m.opportunity_id,
                        )

        return len(results)

    def _step_shadow_outcomes(self, outcome_pairs: List) -> None:
        """Update shadow scorer with actual outcomes."""
        from learning_system.options_shadow_scorer import get_options_shadow_scorer
        scorer = get_options_shadow_scorer()
        for _, pnl, opportunity_id, _ in outcome_pairs:
            if opportunity_id:
                scorer.record_outcome(opportunity_id, pnl)

    def _step_daily_summary(self, summary: Dict) -> None:
        """Write a daily research summary to the research log."""
        today = date.today().isoformat()
        try:
            from knowledge_system.options_knowledge_store import get_options_knowledge_store
            from knowledge_system.options_pattern_engine import get_options_pattern_engine
            from knowledge_system.options_hypothesis_engine import get_options_hypothesis_engine
            from learning_system.options_shadow_scorer import get_options_shadow_scorer
            from knowledge_system.options_counterfactual_engine import get_options_counterfactual_engine

            store   = get_options_knowledge_store()
            pattern_engine = get_options_pattern_engine()
            hyp_engine = get_options_hypothesis_engine()
            shadow  = get_options_shadow_scorer()
            cf      = get_options_counterfactual_engine()

            from knowledge_system.options_knowledge_store import (
                KS_OBSERVED, KS_CANDIDATE, KS_VALIDATING,
                KS_VALIDATED, KS_AUTHENTICATED, KS_DEGRADED,
                KS_INVALIDATED, KS_RETIRED,
            )

            items = store.get_all_items()
            state_counts: Dict[str, int] = {}
            for item in items:
                state_counts[item.state] = state_counts.get(item.state, 0) + 1

            sig_patterns = pattern_engine.get_significant_patterns()
            hypo_summary = hyp_engine.summary()
            shadow_stats = shadow.get_agreement_stats()

            entry = (
                f"\n## Research Pipeline Run — {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"**New outcomes processed:** {summary.get('new_outcomes', 0)}  \n"
                f"**Significant patterns:** {len(sig_patterns)}  \n"
                f"**Knowledge store:**  \n"
                + "\n".join(
                    f"  - {s}: {c}" for s, c in sorted(state_counts.items())
                )
                + f"\n\n**Hypotheses:** {hypo_summary}  \n"
                f"**Shadow agreement rate:** {shadow_stats.get('agree_rate', 0):.1%} "
                f"({shadow_stats.get('total_records', 0)} total)  \n"
                f"**Counterfactual pending:** {cf.pending_count()}  \n"
                f"**CF analysed this run:** {summary.get('cf_analysed', 0)}  \n"
            )

            with open(_RESEARCH_LOG, "a", encoding="utf-8") as fh:
                fh.write(entry)

        except Exception as exc:
            log.debug("[ResearchPipeline] Daily summary error: %s", exc)

    # ── Cursor persistence ─────────────────────────────────────────────────

    def _save_cursor(self) -> None:
        try:
            with open(_CURSOR_PATH, "w", encoding="utf-8") as fh:
                json.dump({"cursor": self._cursor, "updated": datetime.now().isoformat()}, fh)
        except Exception:
            pass

    def _load_cursor(self) -> None:
        if not os.path.exists(_CURSOR_PATH):
            return
        try:
            with open(_CURSOR_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._cursor = int(data.get("cursor", 0))
        except Exception:
            self._cursor = 0


# ── Singleton ──────────────────────────────────────────────────────────────

_PIPELINE_INSTANCE: Optional[OptionsResearchPipeline] = None
_PIPELINE_LOCK      = threading.Lock()


def get_options_research_pipeline() -> OptionsResearchPipeline:
    global _PIPELINE_INSTANCE
    with _PIPELINE_LOCK:
        if _PIPELINE_INSTANCE is None:
            _PIPELINE_INSTANCE = OptionsResearchPipeline()
    return _PIPELINE_INSTANCE

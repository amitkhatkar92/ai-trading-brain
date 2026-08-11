"""predictive_gap/pga_learning.py — Plan and execute A–G learning actions for PGA-001."""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pga_analyzer import StockAnalysis, MISS_CORRECT, MISS_NO_DATA
from .pga_collector import DailyData
from .pga_config import PGAConfig, HYP_REGISTRY, PGA_DIR, LEARNING_CATEGORIES
from .pga_root_cause import RootCause

log = logging.getLogger(__name__)

# Systems that can receive learning actions
TARGET_IDR            = "IDR"
TARGET_RC             = "RC"
TARGET_HKAP           = "HKAP"
TARGET_KDE            = "KDE"
TARGET_SD             = "SD"
TARGET_CALIBRATION    = "CALIBRATION"
TARGET_HYPOTHESIS_REG = "HYPOTHESIS"


@dataclass
class LearningAction:
    action_id: str
    category: str              # "A"–"G"
    symbol: str
    action_type: str           # e.g. "calibrate_pmci", "create_hypothesis"
    target_system: str         # TARGET_* constant
    description: str
    payload: Dict[str, Any] = field(default_factory=dict)
    scheduled: bool = False    # True when the underlying system was invoked
    outcome: str = ""          # result/status after execution


def _make_id() -> str:
    return f"PGA-{uuid.uuid4().hex[:8].upper()}"


def _plan_cat_a(cause: RootCause, analysis: StockAnalysis) -> LearningAction:
    """Category A: Calibrate existing feature weights."""
    return LearningAction(
        action_id=_make_id(),
        category="A",
        symbol=cause.symbol,
        action_type="calibrate_feature_weight",
        target_system=TARGET_CALIBRATION,
        description=(
            f"Recalibrate PMCI/scanner thresholds for {cause.symbol}. "
            f"DNA={analysis.dna_coverage} patterns exist but signal not generated. "
            f"Move={analysis.stock_move.daily_return_pct:+.1f}%"
        ),
        payload={
            "symbol": cause.symbol,
            "miss_type": cause.miss_type,
            "primary_cause": cause.primary_cause,
            "dna_coverage": analysis.dna_coverage,
            "daily_return_pct": analysis.stock_move.daily_return_pct,
            "action": "review_threshold",
        },
    )


def _plan_cat_b(cause: RootCause, analysis: StockAnalysis) -> LearningAction:
    """Category B: Update IDR observation to improve knowledge confidence."""
    return LearningAction(
        action_id=_make_id(),
        category="B",
        symbol=cause.symbol,
        action_type="update_idr_observation",
        target_system=TARGET_IDR,
        description=(
            f"Add observation for {cause.symbol}: move={analysis.stock_move.daily_return_pct:+.1f}% "
            f"({analysis.miss_type}) with {analysis.dna_coverage} DNA patterns. "
            f"Predicted: {analysis.was_predicted}, Actual: {analysis.stock_move.actual_direction}"
        ),
        payload={
            "symbol": cause.symbol,
            "direction": analysis.stock_move.actual_direction,
            "return_pct": analysis.stock_move.daily_return_pct,
            "was_predicted": analysis.was_predicted,
            "dna_count": analysis.dna_coverage,
            "action": "reinforce_observation",
        },
    )


def _plan_cat_c(cause: RootCause, analysis: StockAnalysis, report_date: str) -> LearningAction:
    """Category C: Create a hypothesis about this pattern."""
    sym   = cause.symbol
    move  = analysis.stock_move
    title = (
        f"Why did {sym} move {move.daily_return_pct:+.1f}% "
        f"on {report_date} without IIOS signal?"
    )
    question = (
        f"What combination of conditions caused {sym} to produce a "
        f"{abs(move.daily_return_pct):.1f}% {move.actual_direction.lower()} move "
        f"on {report_date} that was NOT predicted by IIOS scanning?"
    )
    return LearningAction(
        action_id=_make_id(),
        category="C",
        symbol=sym,
        action_type="create_hypothesis",
        target_system=TARGET_HYPOTHESIS_REG,
        description=f"New hypothesis: {title}",
        payload={
            "title": title,
            "research_question": question,
            "symbol": sym,
            "date": report_date,
            "return_pct": move.daily_return_pct,
            "miss_type": cause.miss_type,
            "primary_cause": cause.primary_cause,
            "dna_coverage": analysis.dna_coverage,
            "action": "create_hypothesis",
        },
    )


def _plan_cat_d(cause: RootCause, analysis: StockAnalysis, report_date: str) -> LearningAction:
    """Category D: Schedule a ResearchCoordinator study."""
    sym = cause.symbol
    return LearningAction(
        action_id=_make_id(),
        category="D",
        symbol=sym,
        action_type="schedule_research_study",
        target_system=TARGET_RC,
        description=(
            f"Schedule RC study for {sym}: "
            f"investigate why {sym} moved {analysis.stock_move.daily_return_pct:+.1f}% "
            f"without IIOS prediction on {report_date}"
        ),
        payload={
            "symbol": sym,
            "date": report_date,
            "return_pct": analysis.stock_move.daily_return_pct,
            "miss_type": cause.miss_type,
            "research_question": (
                f"What market dynamics caused {sym} to move "
                f"{abs(analysis.stock_move.daily_return_pct):.1f}% "
                f"on {report_date}?"
            ),
            "action": "schedule_study",
        },
    )


def _plan_cat_e(cause: RootCause, analysis: StockAnalysis) -> LearningAction:
    """Category E: Create candidate DNA for this symbol."""
    return LearningAction(
        action_id=_make_id(),
        category="E",
        symbol=cause.symbol,
        action_type="create_dna_candidate",
        target_system=TARGET_IDR,
        description=(
            f"Create candidate DNA for {cause.symbol}: "
            f"moved {analysis.stock_move.daily_return_pct:+.1f}% with zero DNA coverage"
        ),
        payload={
            "symbol": cause.symbol,
            "return_pct": analysis.stock_move.daily_return_pct,
            "direction": analysis.stock_move.actual_direction,
            "volume": analysis.stock_move.volume,
            "action": "create_dna_candidate",
        },
    )


def _plan_cat_f(cause: RootCause, analysis: StockAnalysis) -> LearningAction:
    """Category F: Schedule HKAP historical replay for this symbol."""
    return LearningAction(
        action_id=_make_id(),
        category="F",
        symbol=cause.symbol,
        action_type="schedule_hkap_replay",
        target_system=TARGET_HKAP,
        description=(
            f"Schedule HKAP replay for {cause.symbol}: "
            f"build historical knowledge about {abs(analysis.stock_move.daily_return_pct):.1f}% "
            f"move patterns"
        ),
        payload={
            "symbol": cause.symbol,
            "move_pct": analysis.stock_move.daily_return_pct,
            "direction": analysis.stock_move.actual_direction,
            "action": "schedule_hkap",
        },
    )


def _plan_cat_g(cause: RootCause, analysis: StockAnalysis) -> LearningAction:
    """Category G: Schedule KDE relationship discovery for this symbol."""
    return LearningAction(
        action_id=_make_id(),
        category="G",
        symbol=cause.symbol,
        action_type="schedule_kde_run",
        target_system=TARGET_KDE,
        description=(
            f"Schedule KDE run for {cause.symbol}: "
            f"discover relationships explaining "
            f"{analysis.stock_move.daily_return_pct:+.1f}% move"
        ),
        payload={
            "symbol": cause.symbol,
            "move_pct": analysis.stock_move.daily_return_pct,
            "action": "schedule_kde",
        },
    )


def _try_create_hypothesis(action: LearningAction) -> bool:
    """
    Attempt to create a hypothesis in the HypothesisRegistry.
    Returns True if successful.
    """
    try:
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry
        from autonomous_research.hypothesis_models import (
            HypothesisClassification, HypothesisPriority,
        )

        kp  = KnowledgeProvider()
        reg = HypothesisRegistry(knowledge_provider=kp)

        p = action.payload
        reg.create_hypothesis(
            title=p["title"],
            research_question=p["research_question"],
            rationale=(
                f"PGA-001 miss identified on {p['date']}: "
                f"{p['symbol']} moved {p['return_pct']:+.1f}% ({p['miss_type']}) "
                f"without IIOS prediction. Primary cause: {p['primary_cause']}."
            ),
            classification=HypothesisClassification.PREDICTIVE_SIGNAL,
            priority=HypothesisPriority.MEDIUM,
            tags=[p["symbol"], "pga", "miss", p["date"]],
        )
        return True
    except Exception as e:
        log.debug("[PGA-Learning] Hypothesis creation failed for %s: %s",
                  action.symbol, e)
        return False


def _try_reinforce_idr(action: LearningAction) -> bool:
    """
    Attempt to record a reinforcing observation in the IDR repository.
    Returns True if successful.
    """
    try:
        from market_learning.idr_repository import IDRRepository
        repo = IDRRepository()

        p = action.payload
        # Try adding an observation for this symbol/direction to reinforce or weaken DNA
        repo.add_observation(
            symbol=p["symbol"],
            direction=p.get("direction", "UP"),
            return_pct=p.get("return_pct", 0.0),
            context={
                "source": "pga_learning",
                "was_predicted": p.get("was_predicted", "NO"),
                "dna_count": p.get("dna_count", 0),
            },
        )
        return True
    except Exception as e:
        log.debug("[PGA-Learning] IDR observation failed for %s: %s",
                  action.symbol, e)
        return False


def _write_pending_actions_json(actions: List[LearningAction], report_dir: Path) -> None:
    """Write a JSON file with pending learning actions for external consumers."""
    data = [
        {
            "action_id": a.action_id,
            "category": a.category,
            "category_desc": LEARNING_CATEGORIES.get(a.category, ""),
            "symbol": a.symbol,
            "action_type": a.action_type,
            "target_system": a.target_system,
            "description": a.description,
            "payload": a.payload,
            "scheduled": a.scheduled,
            "outcome": a.outcome,
        }
        for a in actions
    ]
    out = report_dir / "pga_learning_actions.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    log.info("[PGA-Learning] Wrote %d learning actions → %s", len(data), out)


def plan_actions(
    root_causes: List[RootCause],
    analyses: List[StockAnalysis],
    data: DailyData,
    cfg: PGAConfig,
    report_date: str,
) -> List[LearningAction]:
    """
    Produce a list of learning actions from root cause analysis.
    Actions are planned but not executed here.
    """
    analysis_map = {a.symbol: a for a in analyses}
    actions: List[LearningAction] = []

    for cause in root_causes:
        if cause.miss_type in (MISS_CORRECT, MISS_NO_DATA):
            continue
        if not cause.can_improve:
            continue

        cat = cause.improvement_category
        analysis = analysis_map.get(cause.symbol)
        if analysis is None:
            continue

        if cat == "A":
            actions.append(_plan_cat_a(cause, analysis))
        elif cat == "B":
            actions.append(_plan_cat_b(cause, analysis))
        elif cat == "C":
            actions.append(_plan_cat_c(cause, analysis, report_date))
        elif cat == "D":
            actions.append(_plan_cat_d(cause, analysis, report_date))
        elif cat == "E":
            actions.append(_plan_cat_e(cause, analysis))
        elif cat == "F":
            actions.append(_plan_cat_f(cause, analysis))
        elif cat == "G":
            actions.append(_plan_cat_g(cause, analysis))

    log.info(
        "[PGA-Learning] Planned %d actions — categories: %s",
        len(actions),
        {c: sum(1 for a in actions if a.category == c) for c in "ABCDEFG"},
    )
    return actions


def execute_actions(
    actions: List[LearningAction],
    cfg: PGAConfig,
    report_dir: Path,
) -> List[LearningAction]:
    """
    Execute learning actions that interact with live IIOS subsystems.
    Dry-run mode skips all writes.
    Only Category C (hypotheses) and Category B (IDR) are auto-executed.
    Categories D/E/F/G require manual or scheduled confirmation.
    """
    if cfg.dry_run:
        log.info("[PGA-Learning] DRY RUN — no actions executed")
        for a in actions:
            a.outcome = "DRY_RUN"
        return actions

    for action in actions:
        try:
            if action.category == "C" and action.target_system == TARGET_HYPOTHESIS_REG:
                ok = _try_create_hypothesis(action)
                action.scheduled = ok
                action.outcome = "HYPOTHESIS_CREATED" if ok else "HYPOTHESIS_FAILED"

            elif action.category == "B" and action.target_system == TARGET_IDR:
                ok = _try_reinforce_idr(action)
                action.scheduled = ok
                action.outcome = "IDR_REINFORCED" if ok else "IDR_FAILED"

            elif action.category == "E" and action.target_system == TARGET_IDR:
                # Cat-E: DNA candidate — research is batched for CLE-001 post-EOD executor.
                # Mark as scheduled so the ILC registry records the intent clearly.
                action.scheduled = True
                action.outcome = "CLE_SCHEDULED"

            else:
                # Categories A, D, E, F, G → logged for manual/scheduled execution
                action.outcome = "LOGGED_FOR_REVIEW"

        except Exception as e:
            action.outcome = f"ERROR: {e}"
            log.warning("[PGA-Learning] Action %s failed: %s", action.action_id, e)

    _write_pending_actions_json(actions, report_dir)
    return actions

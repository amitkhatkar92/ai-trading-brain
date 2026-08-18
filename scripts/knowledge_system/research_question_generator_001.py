"""
scripts/knowledge_system/research_question_generator_001.py
============================================================
Stage 3 — Research Question Generator (KSL-001).

Converts detected patterns into explicit, testable research questions.
Deduplicates against existing hypotheses and prior questions.

Research autonomy: YES — creates questions without human approval.
Production autonomy: NO — questions become hypotheses, not changes.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from .ksl_models import (
    KSLEventType,
    PatternRecord,
    PatternType,
    ResearchArea,
    ResearchQuestion,
    ResearchQuestionStatus,
)

ROOT = Path(__file__).resolve().parent.parent.parent
HYPOTHESIS_REGISTRY_PATH = ROOT / "data" / "ars_hypothesis_registry.json"
QUESTION_QUEUE_PATH      = ROOT / "data" / "research_question_queue.jsonl"
KNOWLEDGE_LEDGER         = ROOT / "data" / "knowledge_evidence_ledger.jsonl"

# Minimum pattern strength to generate a research question
MIN_STRENGTH_GENERATE = 0.30
# Minimum pattern strength to consider duplicate-check (below this, just skip)
MIN_STRENGTH_SKIP     = 0.20


# ─────────────────────────────────────────────────────────────────────────────
# Duplicate checking
# ─────────────────────────────────────────────────────────────────────────────


def _load_existing_hypothesis_titles(registry_path: Path = HYPOTHESIS_REGISTRY_PATH) -> Set[str]:
    """Load existing hypothesis titles for fuzzy duplicate detection."""
    if not registry_path.exists():
        return set()
    with open(registry_path) as f:
        data = json.load(f)
    titles: Set[str] = set()
    for h in data.get("hypotheses", {}).values():
        titles.add(h.get("title", "").lower())
        titles.add(h.get("research_question", "").lower())
    return titles


def _load_existing_questions(queue_path: Path = QUESTION_QUEUE_PATH) -> List[Dict]:
    """Load existing research questions from the queue."""
    if not queue_path.exists():
        return []
    questions = []
    with open(queue_path) as f:
        for line in f:
            try:
                questions.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return questions


def _is_duplicate(question_text: str, direction: str, problem_area: str,
                  existing_titles: Set[str],
                  existing_questions: List[Dict]) -> Optional[str]:
    """
    Returns hypothesis_id or question_id if duplicate, else None.
    Uses keyword matching on key concepts.
    Two questions about different directions are NOT duplicates.
    """
    q_lower = question_text.lower()
    key_concepts = _extract_concepts(q_lower)

    # Check hypothesis registry (direction-agnostic — registry doesn't have direction)
    for title in existing_titles:
        existing_concepts = _extract_concepts(title)
        overlap = key_concepts & existing_concepts
        if len(overlap) >= 3:  # 3+ matching key concepts for registry matches
            return "EXISTING_HYPOTHESIS"

    # Check existing questions
    for eq in existing_questions:
        eq_dir = eq.get("direction", "")
        eq_area = eq.get("problem_area", "")
        # Different directions = NOT a duplicate (UP vs DOWN are distinct research questions)
        if direction not in ("BOTH", "") and eq_dir not in ("BOTH", "") and direction != eq_dir:
            continue
        # Different problem areas = NOT a duplicate
        if problem_area and eq_area and problem_area != eq_area:
            continue
        eq_text = eq.get("question", "").lower()
        eq_concepts = _extract_concepts(eq_text)
        overlap = key_concepts & eq_concepts
        if len(overlap) >= 3:  # raised to 3 for more precise dedup
            status = eq.get("status", "GENERATED")
            if status in (ResearchQuestionStatus.VALIDATED.value,
                          ResearchQuestionStatus.REJECTED.value,
                          ResearchQuestionStatus.NO_INCREMENTAL_VALUE if hasattr(ResearchQuestionStatus, 'NO_INCREMENTAL_VALUE') else "NO_INCREMENTAL_VALUE"):
                return eq.get("research_question_id", "EXISTING")
            elif status not in (ResearchQuestionStatus.SUPERSEDED.value,):
                return eq.get("research_question_id", "EXISTING")

    return None


def _extract_concepts(text: str) -> Set[str]:
    """Extract key trading/research concepts from text."""
    concepts = {
        "c2", "ranking", "top-5", "top5", "opening", "gap", "adverse",
        "outranked", "stronger", "openers", "miss", "ranking_miss", "missed",
        "strategy", "reject", "false", "direction", "up", "down", "separate",
        "regime", "bull", "bear", "range", "model", "v3", "discovery",
        "selection", "incremental", "improve", "capture", "accuracy",
    }
    found = set()
    for c in concepts:
        if c in text:
            found.add(c)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# Question templates per pattern type
# ─────────────────────────────────────────────────────────────────────────────


def _generate_ranking_miss_question(p: PatternRecord, rq_id: str) -> ResearchQuestion:
    direction = p.direction
    top_reason = p.data.get("top_reason", "OUTRANKED_BY_STRONGER_OPENERS")
    miss_rate = p.data.get("miss_rate", 0.0)
    total = p.data.get("total_ge2_movers", 0)

    if top_reason == "OUTRANKED_BY_STRONGER_OPENERS":
        question = (
            f"Does incorporating opening-strength supplementary ranking "
            f"(beyond pure gap magnitude) improve {direction} Top-5 ≥2% mover capture "
            f"compared with the frozen C2 baseline? "
            f"Observation: {int(miss_rate*100)}% of ≥2% {direction} movers were missed (n={total}); "
            f"dominant miss reason is OUTRANKED_BY_STRONGER_OPENERS."
        )
        candidate_change = "Add opening-strength feature (e.g., gap + volume ratio) as secondary sort key within C2 framework"
        baseline_desc = "Frozen C2: rank by |gap_pct| only; select top 5"
    elif top_reason == "ADVERSE_OPEN_GAP":
        question = (
            f"Does de-penalizing candidates with small adverse opening gaps "
            f"improve {direction} Top-5 ≥2% mover capture? "
            f"Observation: {int(miss_rate*100)}% of ≥2% {direction} movers missed; "
            f"ADVERSE_OPEN_GAP is the dominant cause."
        )
        candidate_change = "Adjust C2 formula to handle adverse-gap candidates with early-session reversal potential"
        baseline_desc = "Frozen C2: rank by |gap_pct|; adverse-gap candidates ranked near bottom"
    else:  # LOW_C2_SCORE
        question = (
            f"Is the V3 pre-open score capable of identifying which low-C2-rank "
            f"candidates will still move ≥2% on {direction} days? "
            f"Observation: {int(miss_rate*100)}% of ≥2% {direction} movers had low C2 rank."
        )
        candidate_change = "Use V3 score as tiebreaker among C2 ranks 6-15 to rescue missed ≥2% movers"
        baseline_desc = "Frozen C2: V3 score not used in final selection step"

    return ResearchQuestion(
        research_question_id=rq_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_pattern_ids=[p.pattern_id],
        question=question,
        problem_area=ResearchArea.C2_RANKING,
        direction=direction,
        regime_scope=p.regime,
        baseline=baseline_desc,
        candidate_change=candidate_change,
        target_metric="ge2_rate (Top-5 ≥2% mover capture rate, OOS)",
        minimum_sample=270,  # 54 OOS days × 5
        required_data=["post_open_gap_analysis.csv", "v3_retro_candidates.csv", "shadow JSONL"],
        known_data_gaps=["V3 pre-open scores not available for all OOS dates"],
        leakage_risk="LOW — C2 uses only T0_close + T1_open; additional features must be validated",
        research_priority=0.0,  # filled by priority engine
        status=ResearchQuestionStatus.GENERATED,
    )


def _generate_false_reject_question(p: PatternRecord, rq_id: str) -> ResearchQuestion:
    direction = p.direction
    rate = p.data.get("rate", 0.0)
    total = p.data.get("total_rejections", 0)
    question = (
        f"Does removing or softening the strategy gate for {direction} candidates "
        f"improve Top-5 selection quality? "
        f"Observation: {int(rate*100)}% of strategy-rejected {direction} candidates "
        f"were false rejections (would have been ≥2% movers, n={total})."
    )
    return ResearchQuestion(
        research_question_id=rq_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_pattern_ids=[p.pattern_id],
        question=question,
        problem_area=ResearchArea.STRATEGY,
        direction=direction,
        regime_scope="ALL",
        baseline="Strategy acts as context gate; REJECT status influences pool composition",
        candidate_change="Treat strategy rejection as informational only; do not remove candidates from C2 pool",
        target_metric="ge2_rate and false_rejection_rate in OOS",
        minimum_sample=100,
        required_data=["knowledge_vs_strategy_003_rejection_audit.csv", "shadow JSONL"],
        known_data_gaps=["Strategy OOS rejection data limited to 95 rows"],
        leakage_risk="LOW — strategy status uses only pre-open regime + strategy rules",
        research_priority=0.0,
        status=ResearchQuestionStatus.GENERATED,
    )


def _generate_direction_asymmetry_question(p: PatternRecord, rq_id: str) -> ResearchQuestion:
    up_ge2 = p.data.get("up_ge2", 0.0)
    dn_ge2 = p.data.get("dn_ge2", 0.0)
    question = (
        f"Should UP and DOWN directions use separate C2 ranking models or separate "
        f"selection thresholds given observed asymmetry? "
        f"Observation: UP ge2={up_ge2:.3f} vs DOWN ge2={dn_ge2:.3f} in Top-5 selection."
    )
    return ResearchQuestion(
        research_question_id=rq_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_pattern_ids=[p.pattern_id],
        question=question,
        problem_area=ResearchArea.DIRECTION,
        direction="BOTH",
        regime_scope="ALL",
        baseline="Unified C2 formula; identical Top-5 selection per direction",
        candidate_change="Separate UP/DOWN thresholds or direction-specific tiebreaker features",
        target_metric="direction-specific ge2_rate OOS",
        minimum_sample=270,
        required_data=["post_open_gap_analysis.csv", "shadow JSONL"],
        known_data_gaps=[],
        leakage_risk="LOW",
        research_priority=0.0,
        status=ResearchQuestionStatus.GENERATED,
    )


def _generate_regime_question(p: PatternRecord, rq_id: str) -> ResearchQuestion:
    direction = p.direction
    regime = p.regime
    regime_ge2 = p.data.get("regime_ge2", 0.0)
    overall_ge2 = p.data.get("overall_ge2", 0.0)
    n = p.data.get("n_regime", 0)
    question = (
        f"Does the current C2 selection quality degrade materially in "
        f"{direction}+{regime} conditions, and would regime-specific "
        f"selection rules improve outcomes? "
        f"Observation: {direction}+{regime} ge2={regime_ge2:.3f} vs overall ge2={overall_ge2:.3f} (n={n})."
    )
    return ResearchQuestion(
        research_question_id=rq_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_pattern_ids=[p.pattern_id],
        question=question,
        problem_area=ResearchArea.REGIME,
        direction=direction,
        regime_scope=regime,
        baseline=f"Uniform C2 selection; no regime-specific adjustments",
        candidate_change=f"Regime-specific C2 threshold or skip rule for {direction}+{regime}",
        target_metric=f"ge2_rate for {direction}+{regime} subset in OOS",
        minimum_sample=50,
        required_data=["post_open_gap_analysis.csv"],
        known_data_gaps=[f"{regime} regime OOS sample may be small"],
        leakage_risk="LOW — regime label uses pre-open market data",
        research_priority=0.0,
        status=ResearchQuestionStatus.GENERATED,
    )


def _generate_adverse_gap_question(p: PatternRecord, rq_id: str) -> ResearchQuestion:
    direction = p.direction
    rate = p.data.get("rate", 0.0)
    adverse = p.data.get("adverse_gap_misses", 0)
    question = (
        f"Is there a predictable early-session reversal pattern in {direction} "
        f"candidates that open with an adverse gap but subsequently move ≥2%? "
        f"Observation: {int(rate*100)}% of {direction} ranking misses are ADVERSE_OPEN_GAP "
        f"({adverse} candidates)."
    )
    return ResearchQuestion(
        research_question_id=rq_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_pattern_ids=[p.pattern_id],
        question=question,
        problem_area=ResearchArea.C2_RANKING,
        direction=direction,
        regime_scope="ALL",
        baseline="Frozen C2 ranks by |gap_pct|; adverse-gap candidates ranked near bottom",
        candidate_change="Add reversal-detection feature to rescue adverse-gap candidates with strong V3 score",
        target_metric="ADVERSE_OPEN_GAP capture rate in OOS",
        minimum_sample=50,
        required_data=["post_open_gap_analysis.csv", "shadow JSONL"],
        known_data_gaps=["Intraday reversal data not currently available"],
        leakage_risk="MEDIUM — must verify no post-open intraday features used",
        research_priority=0.0,
        status=ResearchQuestionStatus.GENERATED,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────────────────────────────────────


def generate_questions(
    patterns: List[PatternRecord],
    question_queue_path: Path = QUESTION_QUEUE_PATH,
    knowledge_ledger_path: Path = KNOWLEDGE_LEDGER,
    hypothesis_registry_path: Path = HYPOTHESIS_REGISTRY_PATH,
) -> List[ResearchQuestion]:
    """
    Convert patterns to research questions.
    Deduplicates against existing hypotheses and prior questions.
    Returns newly created questions only.
    """
    existing_titles    = _load_existing_hypothesis_titles(hypothesis_registry_path)
    existing_questions = _load_existing_questions(question_queue_path)

    new_questions: List[ResearchQuestion] = []
    question_queue_path.parent.mkdir(parents=True, exist_ok=True)
    knowledge_ledger_path.parent.mkdir(parents=True, exist_ok=True)

    with open(question_queue_path, "a") as qf, \
         open(knowledge_ledger_path, "a") as kf:

        for p in patterns:
            if p.strength < MIN_STRENGTH_GENERATE:
                continue

            rq_id = f"RQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

            # Generate question from pattern type
            rq: Optional[ResearchQuestion] = None
            if p.pattern_type == PatternType.HIGH_RANKING_MISS_RATE:
                rq = _generate_ranking_miss_question(p, rq_id)
            elif p.pattern_type == PatternType.FALSE_REJECT_RATE:
                rq = _generate_false_reject_question(p, rq_id)
            elif p.pattern_type == PatternType.DIRECTION_ASYMMETRY:
                rq = _generate_direction_asymmetry_question(p, rq_id)
            elif p.pattern_type == PatternType.REGIME_UNDERPERFORMANCE:
                rq = _generate_regime_question(p, rq_id)
            elif p.pattern_type == PatternType.ADVERSE_GAP_DOMINATES:
                rq = _generate_adverse_gap_question(p, rq_id)

            if rq is None:
                continue

            # Duplicate check
            dup_id = _is_duplicate(
                rq.question,
                rq.direction,
                rq.problem_area.value,
                existing_titles,
                existing_questions,
            )
            if dup_id:
                rq.duplicate_of = dup_id
                rq.status = ResearchQuestionStatus.SUPERSEDED
                kf.write(json.dumps({
                    "event_type": KSLEventType.DUPLICATE_SUPPRESSED.value,
                    "question_id": rq.research_question_id,
                    "duplicate_of": dup_id,
                    "pattern_type": p.pattern_type.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                continue

            # Write to queue and ledger
            qf.write(json.dumps(rq.to_dict()) + "\n")
            kf.write(json.dumps({
                "event_type": KSLEventType.RESEARCH_QUESTION.value,
                "question_id": rq.research_question_id,
                "question": rq.question,
                "problem_area": rq.problem_area.value,
                "direction": rq.direction,
                "source_pattern_ids": p.pattern_id,
                "timestamp": rq.created_at,
            }) + "\n")

            # Track for within-run dedup
            existing_questions.append(rq.to_dict())
            new_questions.append(rq)

    return new_questions

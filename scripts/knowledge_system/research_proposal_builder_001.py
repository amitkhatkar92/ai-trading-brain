"""
scripts/knowledge_system/research_proposal_builder_001.py
==========================================================
Stage 5 — Research Proposal Builder (KSL-001).

Builds a full, executable research proposal for a prioritized question.
Uses the frozen TRAIN/VAL/OOS splits. Connects to existing research
coordinator conceptually — proposals define what should be run.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .ksl_models import (
    KSLEventType,
    ResearchProposal,
    ResearchQuestion,
)

ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_LEDGER = ROOT / "data" / "knowledge_evidence_ledger.jsonl"

# Frozen split definitions — NEVER redefine
TRAIN_DAYS = 107
VAL_DAYS   = 53
OOS_DAYS   = 54
OOS_START  = "2026-05-14"
OOS_END    = "2026-07-30"

# Frozen baseline metrics from DAILY_SELECTION_QUALITY_AUDIT_001
BASELINE_METRICS = {
    "up_dir_acc_top5":  0.6151,
    "up_ge2_rate_top5": 0.2906,
    "up_ge3_rate_top5": 0.2113,
    "dn_dir_acc_top5":  0.6038,
    "dn_ge2_rate_top5": 0.2415,
    "dn_ge3_rate_top5": 0.1509,
    "up_spearman":      0.359,
    "dn_spearman":      0.355,
}

STANDARD_METRICS = [
    "dir_acc (directional accuracy, OOS Top-5)",
    "ge1_rate (≥1% direction-correct moves)",
    "ge2_rate (≥2% direction-correct moves)",
    "ge3_rate (≥3% direction-correct moves)",
    "avg_t1_ret (average T+1 return)",
    "mfe_avg (average max favorable excursion)",
    "mae_avg (average max adverse excursion)",
    "lift_vs_rem15 (Top-5 vs Remaining-15 ratio)",
    "spearman(score, favorable_return)",
]


def build_proposal(
    rq: ResearchQuestion,
    knowledge_ledger_path: Path = KNOWLEDGE_LEDGER,
) -> ResearchProposal:
    """
    Build a full research proposal for a research question.
    Uses frozen TRAIN/VAL/OOS splits and baseline metrics.
    """
    proposal_id = f"PROP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    # Determine dataset
    primary_csv = ROOT / "reports" / "mover_discovery_v3" / "post_open_gap_analysis.csv"
    dataset_rows = 8560  # confirmed 214 days × 40 candidates
    dataset_path = str(primary_csv.relative_to(ROOT))

    # Compute minimum sample based on direction scope
    if rq.direction in ("UP", "DOWN"):
        min_sample = OOS_DAYS * 5  # 270 per direction
    else:
        min_sample = OOS_DAYS * 10  # 540 both directions

    proposal = ResearchProposal(
        proposal_id=proposal_id,
        research_question_id=rq.research_question_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=f"Research Proposal: {rq.question[:80]}...",
        baseline_description=(
            "Frozen C2 architecture: gap_pct = (T1_open/T0_close-1)*100; "
            "UP: c2_score=+gap_pct; DOWN: c2_score=-gap_pct; "
            "rank descending, select top-5 per direction per day. "
            f"OOS baseline: UP dir_acc={BASELINE_METRICS['up_dir_acc_top5']}, "
            f"ge2={BASELINE_METRICS['up_ge2_rate_top5']}; "
            f"DOWN dir_acc={BASELINE_METRICS['dn_dir_acc_top5']}, "
            f"ge2={BASELINE_METRICS['dn_ge2_rate_top5']}."
        ),
        candidate_description=rq.candidate_change,
        dataset_path=dataset_path,
        dataset_rows=dataset_rows,
        train_days=TRAIN_DAYS,
        val_days=VAL_DAYS,
        oos_days=OOS_DAYS,
        oos_start=OOS_START,
        oos_end=OOS_END,
        metrics=STANDARD_METRICS,
        leakage_test_required=True,
        look_ahead_test=True,
        sample_sufficiency_min=min_sample,
        production_isolation=True,
        expected_delta=f"Target: ge2_rate improvement ≥0.02 (2pp) vs baseline on OOS {rq.direction} Top-5",
        risk_of_regression="Must not reduce baseline dir_acc by more than 0.01 on OOS period",
    )

    # Write to knowledge ledger
    knowledge_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(knowledge_ledger_path, "a") as kf:
        kf.write(json.dumps({
            "event_type": KSLEventType.RESEARCH_PROPOSAL.value,
            "proposal_id": proposal_id,
            "research_question_id": rq.research_question_id,
            "title": proposal.title,
            "oos_start": OOS_START,
            "oos_end": OOS_END,
            "created_at": proposal.created_at,
        }) + "\n")

    return proposal


def build_proposals_for_top_n(
    questions: List[ResearchQuestion],
    n: int = 3,
    min_priority: float = 60.0,
    knowledge_ledger_path: Path = KNOWLEDGE_LEDGER,
) -> List[ResearchProposal]:
    """Build proposals for the top-N prioritized questions above threshold."""
    eligible = [q for q in questions if q.research_priority >= min_priority][:n]
    return [build_proposal(q, knowledge_ledger_path) for q in eligible]

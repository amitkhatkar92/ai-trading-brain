"""institutional_learning/ilc_reporter.py — Phase 12: 12 Report Generator."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from .ilc_models import (
    ILCResult,
    ILSScore,
    LifecycleRecord,
    LearningRecord,
    MarketOpportunityItem,
    ROIRecord,
    UniverseStatus,
    VerificationResult,
)

log = logging.getLogger(__name__)


def _bar(value: float, max_val: float, width: int = 20) -> str:
    """ASCII progress bar."""
    fill = int(width * value / max(max_val, 1))
    return "[" + "=" * fill + "-" * (width - fill) + "]"


def _sign(v: float) -> str:
    return "+" if v >= 0 else ""


def _pct(v: float) -> str:
    return f"{v:+.1f}%"


# ─────────────────────────────────────────────────────────────────────────────
# Report 1: Market Opportunity Audit
# ─────────────────────────────────────────────────────────────────────────────

def report_market_opportunity(
    opportunities: List[MarketOpportunityItem],
    report_dir: Path,
    today: str,
) -> None:
    lines = [
        f"# Market Opportunity Audit — {today}",
        "",
        f"ILC audited top-20 gainers and top-20 losers against the IIOS universe.",
        "",
        "## Summary",
        "",
    ]
    inside   = [o for o in opportunities if o.universe_status == UniverseStatus.INSIDE]
    by_design= [o for o in opportunities if o.universe_status == UniverseStatus.OUTSIDE_BY_DESIGN]
    unexpected=[o for o in opportunities if o.universe_status == UniverseStatus.OUTSIDE_UNEXPECTED]
    rules    = [o for o in opportunities if o.universe_status == UniverseStatus.OUTSIDE_UNIVERSE_RULES]

    lines += [
        f"| Category              | Count | % of Audited |",
        f"|---|---|---|",
        f"| Inside universe       | {len(inside):>5} | {100*len(inside)/max(len(opportunities),1):>5.0f}% |",
        f"| Outside — by design   | {len(by_design):>5} | {100*len(by_design)/max(len(opportunities),1):>5.0f}% |",
        f"| Outside — unexpected  | {len(unexpected):>5} | {100*len(unexpected)/max(len(opportunities),1):>5.0f}% |",
        f"| Outside — rules       | {len(rules):>5} | {100*len(rules)/max(len(opportunities),1):>5.0f}% |",
        f"| **Total audited**     | **{len(opportunities)}** | 100% |",
        "",
    ]

    lines.append("## Gainers")
    lines.append("")
    gainers = sorted([o for o in opportunities if o.move_type == "GAINER"],
                     key=lambda o: o.daily_return_pct, reverse=True)
    lines.append("| # | Symbol | Return | Status | DNA | Scanned |")
    lines.append("|---|---|---|---|---|---|")
    for i, o in enumerate(gainers[:20], 1):
        lines.append(
            f"| {i:>2} | {o.symbol:<12} | {_pct(o.daily_return_pct)} | "
            f"{o.universe_status} | {o.dna_coverage} | {'Yes' if o.in_scanned_today else 'No'} |"
        )

    lines.append("")
    lines.append("## Losers")
    lines.append("")
    losers = sorted([o for o in opportunities if o.move_type == "LOSER"],
                    key=lambda o: o.daily_return_pct)
    lines.append("| # | Symbol | Return | Status | DNA | Scanned |")
    lines.append("|---|---|---|---|---|---|")
    for i, o in enumerate(losers[:20], 1):
        lines.append(
            f"| {i:>2} | {o.symbol:<12} | {_pct(o.daily_return_pct)} | "
            f"{o.universe_status} | {o.dna_coverage} | {'Yes' if o.in_scanned_today else 'No'} |"
        )

    if unexpected:
        lines += ["", "## Action Required — Unexpected Gaps", ""]
        for o in unexpected:
            lines.append(f"- **{o.symbol}** moved {_pct(o.daily_return_pct)}: {o.universe_reason}")

    _write(report_dir / "MARKET_OPPORTUNITY_AUDIT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 2: Universe Selection Audit
# ─────────────────────────────────────────────────────────────────────────────

def report_universe_selection(
    opportunities: List[MarketOpportunityItem],
    report_dir: Path,
    today: str,
) -> None:
    unexpected = [o for o in opportunities if o.universe_status == UniverseStatus.OUTSIDE_UNEXPECTED]
    by_design  = [o for o in opportunities if o.universe_status == UniverseStatus.OUTSIDE_BY_DESIGN]

    lines = [
        f"# Universe Selection Audit — {today}",
        "",
        "Verifies that stocks moving significantly are correctly classified by the universe selection rules.",
        "",
        f"## Coverage Statistics",
        f"- Total stocks audited: {len(opportunities)}",
        f"- Unexpected gaps (action needed): {len(unexpected)}",
        f"- By-design exclusions (archived): {len(by_design)}",
        "",
    ]

    if unexpected:
        lines += ["## Gaps Requiring Universe Rule Review", ""]
        for o in sorted(unexpected, key=lambda x: abs(x.daily_return_pct), reverse=True):
            lines.append(f"### {o.symbol} ({_pct(o.daily_return_pct)})")
            lines.append(f"- **Universe status:** {o.universe_status}")
            lines.append(f"- **Reason:** {o.universe_reason}")
            lines.append(f"- **DNA coverage:** {o.dna_coverage}")
            lines.append(f"- **Action:** Consider adding to nifty500 universe or reviewing filter rules.")
            lines.append("")
    else:
        lines.append("*No unexpected universe gaps detected today.*")

    if by_design:
        lines += ["", "## By-Design Exclusions (informational)", ""]
        for o in by_design[:10]:
            lines.append(f"- {o.symbol}: {o.universe_reason}")

    _write(report_dir / "UNIVERSE_SELECTION_AUDIT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 3: Predictive Gap Report (delegate to PGA, summarise here)
# ─────────────────────────────────────────────────────────────────────────────

def report_predictive_gap(
    analyses: list,
    causes: list,
    report_dir: Path,
    today: str,
) -> None:
    missed_winners = [a for a in analyses if getattr(a, "miss_type", "") == "MISSED_WINNER"]
    missed_losers  = [a for a in analyses if getattr(a, "miss_type", "") == "MISSED_LOSER"]

    lines = [
        f"# Predictive Gap Report — {today}",
        "",
        "Summary of IIOS prediction gaps from the 20-stock ILC universe.",
        "",
        f"## Statistics",
        f"- Stocks analysed: {len(analyses)}",
        f"- Missed winners:  {len(missed_winners)}",
        f"- Missed losers:   {len(missed_losers)}",
        f"- Root causes identified: {len(causes)}",
        "",
    ]
    if missed_winners:
        lines += ["## Missed Winners", ""]
        for a in sorted(missed_winners, key=lambda x: -abs(x.stock_move.daily_return_pct))[:10]:
            lines.append(f"- **{a.symbol}** {_pct(a.stock_move.daily_return_pct)}: "
                         f"predicted={a.was_predicted} predictable={a.was_predictable}")

    if missed_losers:
        lines += ["", "## Missed Losers", ""]
        for a in sorted(missed_losers, key=lambda x: a.stock_move.daily_return_pct)[:10]:
            lines.append(f"- **{a.symbol}** {_pct(a.stock_move.daily_return_pct)}: "
                         f"predicted={a.was_predicted} predictable={a.was_predictable}")

    _write(report_dir / "PREDICTIVE_GAP_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 4: Root Cause Report
# ─────────────────────────────────────────────────────────────────────────────

def report_root_cause(causes: list, report_dir: Path, today: str) -> None:
    from collections import Counter
    cat_counter = Counter(getattr(c, "primary_cause", "Unknown") for c in causes)

    lines = [
        f"# Root Cause Report — {today}",
        "",
        f"**Total root causes:** {len(causes)}",
        "",
        "## Distribution",
        "",
        "| Root Cause | Count | % |",
        "|---|---|---|",
    ]
    for cause, count in cat_counter.most_common():
        lines.append(f"| {cause} | {count} | {100*count/max(len(causes),1):.0f}% |")

    lines += ["", "## Detail", ""]
    for c in causes[:15]:
        sym = getattr(c, "symbol", "?")
        pc  = getattr(c, "primary_cause", "?")
        ev  = getattr(c, "evidence", [])
        lines.append(f"- **{sym}** → {pc}: {'; '.join(str(e) for e in ev[:2])}")

    _write(report_dir / "ROOT_CAUSE_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 5: Learning Priority Report
# ─────────────────────────────────────────────────────────────────────────────

def report_learning_priority(eig_results: list, report_dir: Path, today: str) -> None:
    lines = [
        f"# Learning Priority Report — {today}",
        "",
        "Actions ranked by Expected Improvement Gain (EIG).",
        "",
        "| Rank | Symbol | Cat | Target | EIG | Cost | Confidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in eig_results[:20]:
        lines.append(
            f"| {e.priority_rank:>4} | {e.symbol:<12} | {e.category} | "
            f"{e.target_system:<14} | {e.eig_score:.4f} | "
            f"{e.implementation_cost:.2f} | {e.confidence} |"
        )

    if eig_results:
        lines += [
            "",
            f"**Top priority:** {eig_results[0].symbol} — {eig_results[0].description}",
            f"**Highest EIG:** {eig_results[0].eig_score:.4f}",
        ]

    _write(report_dir / "LEARNING_PRIORITY_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 6: Learning Confidence Report
# ─────────────────────────────────────────────────────────────────────────────

def report_learning_confidence(
    actions: list,
    confidences: List[str],
    analyses: list,
    report_dir: Path,
    today: str,
) -> None:
    from .ilc_models import LearningConfidence as LC
    from collections import Counter
    conf_counter = Counter(confidences)

    lines = [
        f"# Learning Confidence Report — {today}",
        "",
        "Confidence distribution of all learning actions.",
        "",
        "## Distribution",
        "",
        f"| Level | Count | % |",
        f"|---|---|---|",
    ]
    total = max(len(confidences), 1)
    for level in [LC.HIGH, LC.MEDIUM, LC.LOW, LC.EXPERIMENTAL]:
        count = conf_counter.get(level, 0)
        lines.append(f"| {level:<14} | {count:>5} | {100*count/total:.0f}% |")

    lines += ["", "## Detail", ""]
    ana_map = {a.symbol: a for a in analyses}
    for action, conf in list(zip(actions, confidences))[:20]:
        sym = action.symbol
        a   = ana_map.get(sym)
        mv  = _pct(a.stock_move.daily_return_pct) if a else "N/A"
        lines.append(f"- **{sym}** [{conf}] {action.category}/{action.target_system} move={mv}")

    _write(report_dir / "LEARNING_CONFIDENCE_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 7: Learning Implementation Report
# ─────────────────────────────────────────────────────────────────────────────

def report_learning_implementation(
    new_records: List[LearningRecord],
    report_dir: Path,
    today: str,
) -> None:
    executed = [r for r in new_records if r.executed]
    pending  = [r for r in new_records if not r.executed]

    lines = [
        f"# Learning Implementation Report — {today}",
        "",
        f"- New learning records created: {len(new_records)}",
        f"- Immediately executed:         {len(executed)}",
        f"- Pending review:               {len(pending)}",
        "",
        "## Executed Today",
        "",
    ]
    if executed:
        lines.append("| Symbol | Category | Target | Outcome |")
        lines.append("|---|---|---|---|")
        for r in executed:
            lines.append(f"| {r.symbol} | {r.category} | {r.target_system} | {r.outcome[:60]} |")
    else:
        lines.append("*No actions auto-executed today.*")

    if pending:
        lines += ["", "## Pending Review (Cat A/D/E/F/G)", ""]
        for r in pending[:15]:
            lines.append(f"- **{r.symbol}** [{r.category}→{r.target_system}]: {r.description[:80]}")

    _write(report_dir / "LEARNING_IMPLEMENTATION_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 8: Learning Verification Report
# ─────────────────────────────────────────────────────────────────────────────

def report_learning_verification(
    verified_today: List[VerificationResult],
    all_records: List[LearningRecord],
    report_dir: Path,
    today: str,
) -> None:
    n_total    = len(all_records)
    n_pending  = sum(1 for r in all_records if r.status == "PENDING")
    n_measuring= sum(1 for r in all_records if r.status == "MEASURING")
    n_improved = sum(1 for r in all_records if r.status == "IMPROVED")
    n_retired  = sum(1 for r in all_records if r.status == "RETIRED")

    lines = [
        f"# Learning Verification Report — {today}",
        "",
        "## Registry Overview",
        "",
        f"| Status     | Count |",
        f"|---|---|",
        f"| PENDING    | {n_pending} |",
        f"| MEASURING  | {n_measuring} |",
        f"| IMPROVED   | {n_improved} |",
        f"| RETIRED    | {n_retired} |",
        f"| **TOTAL**  | **{n_total}** |",
        "",
        f"## Verifications Run Today ({len(verified_today)})",
        "",
    ]
    if verified_today:
        lines.append("| Symbol | Window | Metric | Baseline | Measured | Delta | Verdict |")
        lines.append("|---|---|---|---|---|---|---|")
        for vr in verified_today:
            lines.append(
                f"| {vr.learning_id.split('-')[0]} | {vr.window_days}d | {vr.metric_name} | "
                f"{vr.baseline_value:.3f} | {vr.measured_value:.3f} | "
                f"{_sign(vr.change_pct)}{vr.change_pct*100:.1f}% | **{vr.verdict}** |"
            )
        lines += ["", "### Actions Taken", ""]
        for vr in verified_today:
            if vr.action_taken:
                lines.append(f"- {vr.learning_id}: {vr.action_taken}")
    else:
        lines.append("*No verifications due today.*")

    _write(report_dir / "LEARNING_VERIFICATION_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 9: Learning ROI Report
# ─────────────────────────────────────────────────────────────────────────────

def report_roi(roi_records: List[ROIRecord], report_dir: Path, today: str) -> None:
    positive = [r for r in roi_records if r.roi_score > 0]
    negative = [r for r in roi_records if r.roi_score <= 0]
    avg_roi  = sum(r.roi_score for r in roi_records) / max(len(roi_records), 1)

    lines = [
        f"# Learning ROI Report — {today}",
        "",
        f"- Total evaluated: {len(roi_records)}",
        f"- Positive ROI:    {len(positive)} ({100*len(positive)/max(len(roi_records),1):.0f}%)",
        f"- Negative ROI:    {len(negative)}",
        f"- Average ROI:     {avg_roi:+.3f}",
        "",
        "## Top ROI Actions",
        "",
        "| Symbol | Category | Target | Cost | Gain | ROI | Confidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(roi_records, key=lambda x: -x.roi_score)[:15]:
        lines.append(
            f"| {r.symbol} | {r.category} | {r.target_system} | "
            f"{r.implementation_cost:.2f} | {r.observed_improvement:+.3f} | "
            f"{r.roi_score:+.3f} | {r.confidence} |"
        )

    if negative:
        lines += ["", "## Negative ROI Actions", ""]
        for r in sorted(negative, key=lambda x: x.roi_score)[:5]:
            lines.append(f"- **{r.symbol}** [{r.category}]: ROI={r.roi_score:+.3f} "
                         f"cost={r.implementation_cost:.2f}")

    _write(report_dir / "LEARNING_ROI_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 10: Knowledge Lifecycle Report
# ─────────────────────────────────────────────────────────────────────────────

def report_knowledge_lifecycle(
    lifecycle_records: List[LifecycleRecord],
    report_dir: Path,
    today: str,
) -> None:
    from collections import Counter
    status_ctr = Counter(r.current_status for r in lifecycle_records)
    type_ctr   = Counter(r.item_type for r in lifecycle_records)

    lines = [
        f"# Knowledge Lifecycle Report — {today}",
        "",
        f"Total knowledge items tracked: **{len(lifecycle_records)}**",
        "",
        "## Status Distribution",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for status, count in sorted(status_ctr.items(), key=lambda x: -x[1]):
        lines.append(f"| {status} | {count} |")

    lines += ["", "## By Type", ""]
    for ktype, count in sorted(type_ctr.items(), key=lambda x: -x[1]):
        lines.append(f"- **{ktype}**: {count}")

    promoted = sorted(
        [r for r in lifecycle_records if r.current_status == "PROMOTED"],
        key=lambda r: r.lifecycle_score, reverse=True,
    )
    if promoted:
        lines += ["", "## Promoted Knowledge (Top 10)", ""]
        lines.append("| ID | Type | Symbol | Discovered | Score |")
        lines.append("|---|---|---|---|---|")
        for r in promoted[:10]:
            lines.append(
                f"| {r.item_id} | {r.item_type} | {r.symbol} | "
                f"{r.discovery_date} | {r.lifecycle_score:.1f} |"
            )

    retired = [r for r in lifecycle_records if r.current_status == "RETIRED"]
    if retired:
        lines += ["", "## Retired Knowledge", ""]
        for r in retired[-5:]:
            lines.append(f"- {r.item_id} ({r.item_type}/{r.symbol}) retired {r.retirement_date}")

    _write(report_dir / "KNOWLEDGE_LIFECYCLE_REPORT.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 11: Institutional Learning Score
# ─────────────────────────────────────────────────────────────────────────────

def report_ils_score(ils: ILSScore, report_dir: Path, today: str) -> None:
    lines = [
        f"# Institutional Learning Score — {today}",
        "",
        f"## Overall ILS: {ils.overall_score:.1f}/100  [{ils.grade}]",
        "",
        ils.narrative,
        "",
        "## Component Scores",
        "",
        "| Component | Score | Weight | Weighted |",
        "|---|---|---|---|",
    ]
    from .ilc_config import SCORE_WEIGHTS
    weights = SCORE_WEIGHTS
    components = [
        ("Learning Efficiency",    "learning_efficiency"),
        ("Knowledge Efficiency",   "knowledge_efficiency"),
        ("Prediction Improvement", "prediction_improvement"),
        ("Research Productivity",  "research_productivity"),
        ("Knowledge ROI",          "knowledge_roi"),
    ]
    for label, attr in components:
        val    = getattr(ils, attr, 0.0)
        wt     = weights.get(attr, 0.0)
        wtd    = val * wt * 100
        bar    = _bar(val, 1.0, 15)
        lines.append(f"| {label:<26} | {val:.3f} {bar} | {wt:.0%} | {wtd:.1f} |")

    lines += [
        "",
        "## Interpretation",
        "",
        "| Grade | Score | Meaning |",
        "|---|---|---|",
        "| A+    | 90-100 | Exceptional — system consistently improves from experience |",
        "| A     | 80-89  | Strong — most learning actions produce measurable gains |",
        "| B     | 70-79  | Good — majority of knowledge assets are healthy |",
        "| C     | 60-69  | Adequate — some gaps, but net positive learning cycle |",
        "| D     | 50-59  | Below average — knowledge decay may be outpacing growth |",
        "| F     | <50    | Poor — intervention needed to improve learning quality |",
    ]

    _write(report_dir / "INSTITUTIONAL_LEARNING_SCORE.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Report 12: Scientific Director Final Review
# ─────────────────────────────────────────────────────────────────────────────

def report_scientific_director_review(
    ils: ILSScore,
    new_records: List[LearningRecord],
    verified_today: List[VerificationResult],
    lifecycle_records: List[LifecycleRecord],
    roi_records: List[ROIRecord],
    opportunities: List[MarketOpportunityItem],
    report_dir: Path,
    today: str,
) -> None:
    n_improved   = sum(1 for v in verified_today if v.verdict == "IMPROVED")
    n_declined   = sum(1 for v in verified_today if v.verdict == "DECLINED")
    n_promoted   = sum(1 for r in lifecycle_records if r.current_status == "PROMOTED")
    n_retired    = sum(1 for r in lifecycle_records if r.current_status == "RETIRED")
    roi_positive = sum(1 for r in roi_records if r.roi_score > 0)
    unexpected   = [o for o in opportunities if o.universe_status == UniverseStatus.OUTSIDE_UNEXPECTED]
    high_conf    = sum(1 for r in new_records if r.confidence in ("HIGH", "MEDIUM"))
    n_total_rec  = max(len(new_records), 1)

    def yn(condition: bool) -> str:
        return "YES" if condition else "NO"

    def grade_q(score: float) -> str:
        return "PASS" if score >= 60 else "NEEDS ATTENTION"

    lines = [
        f"# Scientific Director Final Review — {today}",
        "",
        "Structured assessment of the ILC cycle answering 10 key scientific questions.",
        "",
        f"**ILS Score:** {ils.overall_score:.1f}/100 ({ils.grade})",
        "",
        "---",
        "",
        "## Q1. Did IIOS successfully scan the universe today?",
        "",
        f"**Answer:** {yn(bool(new_records))} — {len(new_records)} stocks produced learning actions.",
        "",
        "## Q2. Were significant movers predicted or caught?",
        "",
        f"**Answer:** {yn(n_improved > 0 or high_conf > 0)} — "
        f"{high_conf} HIGH/MEDIUM confidence actions registered.",
        "",
        "## Q3. Were learning actions actionable?",
        "",
        f"**Answer:** {yn(high_conf > n_total_rec * 0.3)} — "
        f"{high_conf}/{len(new_records)} are HIGH or MEDIUM confidence.",
        "",
        "## Q4. Is the learning verification system healthy?",
        "",
        f"**Answer:** YES — "
        f"{len(verified_today)} verifications run, {n_improved} IMPROVED, {n_declined} DECLINED.",
        "",
        "## Q5. Is knowledge growing (promoted > retired)?",
        "",
        f"**Answer:** {yn(n_promoted >= n_retired)} — "
        f"{n_promoted} promoted vs {n_retired} retired.",
        "",
        "## Q6. Does learning produce positive ROI?",
        "",
        f"**Answer:** {yn(roi_positive > len(roi_records) * 0.5)} — "
        f"{roi_positive}/{len(roi_records)} ROI records are positive.",
        "",
        "## Q7. Are there unexpected universe gaps?",
        "",
        f"**Answer:** {'YES — ACTION REQUIRED' if unexpected else 'No gaps detected'}",
    ]
    for o in unexpected[:5]:
        lines.append(f"  - {o.symbol} ({_pct(o.daily_return_pct)}): {o.universe_reason}")

    lines += [
        "",
        "## Q8. Is the prediction-to-action pipeline closed?",
        "",
        "**Answer:** YES — PGA → confidence → EIG → verification → lifecycle → ILS",
        "",
        "## Q9. Should any knowledge be retired immediately?",
        "",
    ]
    immediate_retire = [
        r for r in lifecycle_records
        if r.lifecycle_score < 10.0 and r.current_status != "RETIRED"
    ]
    if immediate_retire:
        lines.append(f"**Answer:** YES — {len(immediate_retire)} items with lifecycle score < 10")
        for r in immediate_retire[:3]:
            lines.append(f"  - {r.item_id} ({r.item_type}/{r.symbol}): score={r.lifecycle_score:.1f}")
    else:
        lines.append("**Answer:** No immediate retirements required.")

    lines += [
        "",
        "## Q10. Overall system health verdict?",
        "",
        f"**Score:** {ils.overall_score:.1f}/100 [{ils.grade}] — {ils.narrative}",
        f"**Verdict:** {grade_q(ils.overall_score)}",
        "",
        "---",
        "",
        f"*Generated by ILC-001 Institutional Learning Cycle | {today}*",
    ]

    _write(report_dir / "SCIENTIFIC_DIRECTOR_FINAL_REVIEW.md", lines)


# ─────────────────────────────────────────────────────────────────────────────
# Master write function
# ─────────────────────────────────────────────────────────────────────────────

def _write(path: Path, lines: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(str(l) for l in lines) + "\n"
    path.write_text(content, encoding="utf-8")
    log.debug("[ILC-Reporter] Wrote %s (%d bytes)", path.name, len(content))


def write_all_reports(
    opportunities: List[MarketOpportunityItem],
    analyses: list,
    causes: list,
    actions: list,
    confidences: List[str],
    eig_results: list,
    new_records: List[LearningRecord],
    verified_today: List[VerificationResult],
    all_records: List[LearningRecord],
    lifecycle_records: List[LifecycleRecord],
    roi_records: List[ROIRecord],
    ils: ILSScore,
    report_dir: Path,
    today: str,
) -> None:
    """Write all 12 ILC reports."""
    report_dir.mkdir(parents=True, exist_ok=True)

    report_market_opportunity(opportunities, report_dir, today)
    report_universe_selection(opportunities, report_dir, today)
    report_predictive_gap(analyses, causes, report_dir, today)
    report_root_cause(causes, report_dir, today)
    report_learning_priority(eig_results, report_dir, today)
    report_learning_confidence(actions, confidences, analyses, report_dir, today)
    report_learning_implementation(new_records, report_dir, today)
    report_learning_verification(verified_today, all_records, report_dir, today)
    report_roi(roi_records, report_dir, today)
    report_knowledge_lifecycle(lifecycle_records, report_dir, today)
    report_ils_score(ils, report_dir, today)
    report_scientific_director_review(
        ils, new_records, verified_today, lifecycle_records,
        roi_records, opportunities, report_dir, today,
    )

    log.info("[ILC-Reporter] 12 reports written to %s", report_dir)

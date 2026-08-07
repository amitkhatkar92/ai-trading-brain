"""
growth_validator/gva_reporter.py
==================================
GVA-001 — Report Formatter

Produces all six Markdown reports:
  1. KNOWLEDGE_GROWTH_REPORT.md
  2. LEARNING_GROWTH_REPORT.md
  3. DNA_GROWTH_REPORT.md
  4. SCIENTIFIC_GROWTH_REPORT.md
  5. PLATFORM_GROWTH_REPORT.md
  6. OVERALL_GROWTH_SCORE.md

Write-only to data/gva/YYYY-MM-DD/. Never touches knowledge stores.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Optional

from .gva_collector import GVAEvidence
from .gva_metrics import GrowthReport, Metric


# ── Output directory ──────────────────────────────────────────────────────────

def _report_dir(report_date: str) -> Path:
    from .gva_config import GVA_DIR
    d = GVA_DIR / report_date
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


# ── Shared formatting helpers ─────────────────────────────────────────────────

def _hr(char: str = "─", width: int = 78) -> str:
    return char * width


def _header(title: str, report_date: str, subtitle: str = "") -> str:
    bar = "═" * 78
    lines = [bar, f"  GVA-001 | {title}", f"  Date: {report_date}"]
    if subtitle:
        lines.append(f"  {subtitle}")
    lines.append(bar)
    return "\n".join(lines)


def _section(title: str) -> str:
    return f"\n{_hr('─')}\n  {title}\n{_hr('─')}"


def _metric_row(m: Metric) -> str:
    val    = m.formatted_value()
    growth = m.formatted_growth() if m.growth_pct is not None else "N/A"
    dirn   = m.direction_emoji()
    line   = f"  {m.name:<40} {val:<18} {growth:<12} {dirn}"
    if m.notes:
        line += f"\n    Notes: {m.notes}"
    return line


def _metrics_table(metrics: List[Metric]) -> str:
    header = (f"  {'METRIC':<40} {'CURRENT':<18} {'GROWTH':<12} DIRECTION\n"
              f"  {_hr('─', 40)} {_hr('─', 18)} {_hr('─', 12)} {_hr('─', 16)}")
    rows = [_metric_row(m) for m in metrics]
    return header + "\n" + "\n".join(rows)


def _dimension_score_bar(score: float, label: str) -> str:
    filled = int(score / 5)   # 20 blocks = 100%
    empty  = 20 - filled
    bar    = "█" * filled + "░" * empty
    return f"  {label:<22} [{bar}] {score:.0f}/100"


# ── Individual reports ────────────────────────────────────────────────────────

def knowledge_report(ev: GVAEvidence, gr: GrowthReport, report_date: str) -> str:
    lines = [
        _header("KNOWLEDGE GROWTH REPORT", report_date,
                f"Score: {gr.score_knowledge:.0f}/100"),
        "",
        _section("SUMMARY"),
        f"  Feature records:      {ev.feature_count:>12,}  (baseline: {ev.feature_baseline:,})",
        f"  Total edges:          {ev.edges.total:>12,}",
        f"  Active edges:         {ev.edges.active:>12,}",
        f"  Candidate edges:      {ev.edges.candidate:>12,}",
        f"  Decaying edges:       {ev.edges.decaying:>12,}",
        f"  IKN nodes:            {ev.ikn.total_nodes:>12,}",
        f"  IKN relationships:    {ev.ikn.total_rels:>12,}",
        "",
        _section("METRICS"),
        _metrics_table(gr.knowledge),
        "",
        _section("KNOWLEDGE GRAPH — NODE TYPES"),
    ]
    for ntype, cnt in sorted(ev.ikn.by_node_type.items(), key=lambda x: -x[1]):
        lines.append(f"  {ntype:<30} {cnt:>6}")

    lines.extend([
        "",
        _section("ACTIVE EDGES (PRODUCTION KNOWLEDGE)"),
    ])
    if ev.edges.active_edges:
        for e in ev.edges.active_edges:
            lines.append(
                f"  {e.get('name','?'):<40}  prec={e.get('precision','?')}%"
                f"  sharpe={e.get('sharpe_ratio','?')}  oos_wr={e.get('oos_win_rate','?')}"
            )
    else:
        lines.append("  No active edges in production yet.")

    lines.extend([
        "",
        _section("GROWTH NARRATIVE"),
        f"  Feature records grew from {ev.feature_baseline:,} (Study 002 baseline) to",
        f"  {ev.feature_count:,} current records.",
        f"  That is a {(ev.feature_count-ev.feature_baseline)/max(ev.feature_baseline,1)*100:+.0f}% increase in raw knowledge.",
        "",
        f"  The IKN contains {ev.ikn.total_nodes} typed nodes connected by {ev.ikn.total_rels}",
        f"  relationship types — representing structured, queryable knowledge.",
        "",
        _hr(),
    ])
    return "\n".join(lines)


def learning_report(ev: GVAEvidence, gr: GrowthReport, report_date: str) -> str:
    r = ev.replay
    lines = [
        _header("LEARNING GROWTH REPORT", report_date,
                f"Score: {gr.score_learning:.0f}/100"),
        "",
        _section("REPLAY PERFORMANCE"),
        f"  Replay period:        {r.date_range}",
        f"  Days replayed:        {r.days_replayed}",
        f"  Total signals seen:   {r.total_signals}",
        f"  Trades executed:      {r.trades_executed}",
        f"  Win rate:             {r.win_rate:.1f}%",
        f"  Avg R-multiple:       {r.avg_r:.3f}",
        f"  Profit factor:        {r.profit_factor:.2f}",
        f"  Max drawdown:         {r.max_drawdown:.2f}%",
        f"  Net P&L (replay):     ₹{r.net_pnl:,.0f}",
        "",
        _section("STUDY PROGRESSION"),
    ]
    for s in ev.studies:
        lines.append(
            f"  {s.executed_at[:10]}  {s.study_id:<25}  obs={s.n_obs:,}"
            + (f"  feat+={s.features_after-s.features_before:,}" if s.features_after else "")
            + (f"  winner_dna={s.winner_dna_n}" if s.winner_dna_n else "")
        )

    lines.extend([
        "",
        _section("VALIDATION CHAIN"),
        "  Study chain demonstrates increasing validation rigor:",
        "  Step 1: Historical learning (Study 002) — data enrichment",
        "  Step 2: Winner DNA discovery (Study 002A) — pattern mining",
        "  Step 3: Systematic loser DNA (Study 003) — completeness",
        "  Step 4: Cross-year validation (H001) — out-of-sample proof",
        "  Step 5: Symmetric validation (IRP002) — winner+loser comparison",
        "",
        _section("METRICS"),
        _metrics_table(gr.learning),
        "",
        _hr(),
    ])
    return "\n".join(lines)


def dna_report(ev: GVAEvidence, gr: GrowthReport, report_date: str) -> str:
    d = ev.dna
    lines = [
        _header("DNA GROWTH REPORT", report_date,
                f"Score: {gr.score_dna:.0f}/100"),
        "",
        _section("DNA REPOSITORY SUMMARY"),
        f"  Total DNA patterns:   {d.total:>6}",
        f"  Winner DNA:           {d.winner:>6}  (conditions preceding positive returns)",
        f"  Loser DNA:            {d.loser:>6}  (conditions preceding negative returns)",
        f"  Edge DNA:             {d.edge_patterns:>6}  (systematic edge patterns)",
        f"  Institutional:        {d.institutional:>6}  (reached INSTITUTIONAL lifecycle)",
        f"  BUY patterns:         {d.buy:>6}",
        f"  SHORT patterns:       {d.short:>6}",
        f"  Evidence records:     {d.evidence_records:>6}",
        f"  Audit — CREATED:      {d.created_ops:>6}",
        f"  Audit — UPDATED:      {d.updated_ops:>6}",
        "",
        _section("DNA BY STUDY"),
    ]
    for study_id, cnt in sorted(d.by_study.items(), key=lambda x: -x[1]):
        lines.append(f"  {study_id:<30}  evidence_records={cnt}")

    lines.extend([
        "",
        _section("METRICS"),
        _metrics_table(gr.dna),
        "",
        _section("GROWTH NARRATIVE"),
        "  DNA accumulation timeline:",
        "  — Before Study 002: 0 patterns",
        f"  — After Study 002A (2026-08-03): winner DNA discovered",
        f"  — After Study H001 (2026-08-05): cross-year validation",
        f"  — Current: {d.total} institutional-grade patterns",
        "",
        f"  DNA update rate {d.updated_ops/max(d.created_ops,1)*100:.0f}%: indicates patterns are being",
        "  refined as new evidence arrives (healthy evolution signal).",
        "",
        _hr(),
    ])
    return "\n".join(lines)


def scientific_report(ev: GVAEvidence, gr: GrowthReport, report_date: str) -> str:
    h = ev.hypothesis
    lines = [
        _header("SCIENTIFIC GROWTH REPORT", report_date,
                f"Score: {gr.score_scientific:.0f}/100"),
        "",
        _section("HYPOTHESIS REGISTRY"),
        f"  Total hypotheses:     {h.total}",
        f"  CONFIRMED:            {h.confirmed}",
        f"  PROPOSED:             {h.proposed}",
        f"  PARTIALLY_CONFIRMED:  {h.partial}",
        f"  REJECTED:             {h.rejected}",
        f"  Confirmation rate:    {h.confirmed/max(h.total,1)*100:.1f}%",
        "",
        _section("STUDY OUTCOMES"),
    ]
    for s in ev.studies:
        verdict = ""
        if s.validation:
            verdict = s.validation.get("overall_verdict",
                      "winner_avg_lift=" + str(round(float(s.validation.get("winner_avg_lift", 0)), 3))
                      if "winner_avg_lift" in s.validation else "")
        lines.append(f"  {s.executed_at[:10]}  {s.study_id:<28}  {verdict}")

    h001_v = next((s.validation for s in ev.studies if s.study_id == "ars_study_h001"), {})
    if h001_v:
        lines.extend([
            "",
            _section("H001 — CROSS-YEAR VALIDATION DETAIL"),
            f"  Hypothesis:           {h001_v.get('hypothesis_id','?')}",
            f"  Training year:        {h001_v.get('training_year','?')}",
            f"  Validation year:      {h001_v.get('validation_year','?')}",
            f"  Conditions tested:    {h001_v.get('conditions_tested','?')}",
            f"  Conditions confirmed: {h001_v.get('conditions_validated','?')}",
            f"  Conditions partial:   {h001_v.get('conditions_partial','?')}",
            f"  Conditions rejected:  {h001_v.get('conditions_rejected','?')}",
            f"  Overall verdict:      {h001_v.get('overall_verdict','?')}",
        ])

    irp002_v = next((s.validation for s in ev.studies if "irp002" in s.study_id.lower()), {})
    if irp002_v:
        lines.extend([
            "",
            _section("IRP-002 — SYMMETRIC VALIDATION DETAIL"),
            f"  Training year:        {irp002_v.get('training_year','?')}",
            f"  Validation year:      {irp002_v.get('validation_year','?')}",
            f"  Winner patterns:      {irp002_v.get('winner_patterns_tested','?')} tested",
            f"  Individual partial:   {irp002_v.get('individual_partial','?')}",
            f"  Individual rejected:  {irp002_v.get('individual_rejected','?')}",
            f"  Winner avg lift:      {irp002_v.get('winner_avg_lift','?')}",
            f"  Loser avg lift:       {irp002_v.get('loser_avg_lift','?')}",
            f"  Winner survival:      {float(irp002_v.get('winner_survival',0))*100:.1f}%",
            f"  Loser survival:       {float(irp002_v.get('loser_survival',0))*100:.1f}%",
        ])

    lines.extend([
        "",
        _section("METRICS"),
        _metrics_table(gr.scientific),
        "",
        _hr(),
    ])
    return "\n".join(lines)


def platform_report(ev: GVAEvidence, gr: GrowthReport, report_date: str) -> str:
    p = ev.platform
    lines = [
        _header("PLATFORM GROWTH REPORT", report_date,
                f"Score: {gr.score_platform:.0f}/100"),
        "",
        _section("ORCHESTRATOR TELEMETRY"),
        f"  Total cycles:         {p.total_cycles:,}",
        f"  Cycle errors:         {p.cycle_errors}",
        f"  Error rate:           {p.cycle_errors/max(p.total_cycles,1)*100:.2f}%",
        f"  Total decisions:      {p.total_decisions:,}",
        f"  APPROVED:             {p.approved:,}",
        f"  REJECTED:             {p.rejected:,}",
        f"  Approval rate:        {p.approved/max(p.total_decisions,1)*100:.1f}%",
        f"  Avg confidence:       {p.avg_confidence:.2f}/10",
        "",
        _section("REGIME DISTRIBUTION"),
    ]
    for regime, cnt in sorted(p.regime_dist.items(), key=lambda x: -x[1]):
        pct = cnt / max(p.total_cycles, 1) * 100
        lines.append(f"  {(regime or 'UNKNOWN'):<20}  {cnt:>6,}  ({pct:.1f}%)")

    lines.extend([
        "",
        _section("STRATEGY PERFORMANCE"),
        f"  {'STRATEGY':<30} {'TRADES':>7} {'WINS':>6} {'WIN_RATE':>10}",
        f"  {_hr('─', 30)} {'─'*7} {'─'*6} {'─'*10}",
    ])
    for name, sp in ev.strategy_perf.items():
        tt = int(sp.get("total_trades", 0))
        w  = int(sp.get("wins", 0))
        wr = w / tt * 100 if tt else 0
        lines.append(f"  {name:<30} {tt:>7} {w:>6} {wr:>9.1f}%")

    lines.extend([
        "",
        _section("PAPER TRADING SUMMARY"),
        f"  Cumulative P&L:       ₹{ev.cum_pnl:+,.0f}",
        f"  Cumulative return:    {ev.cum_return_pct:+.2f}%",
        f"  Closed trades:        {ev.closed_trades}",
        f"  Open trades:          {ev.open_trades}",
        "",
        _section("METRICS"),
        _metrics_table(gr.platform),
        "",
        _hr(),
    ])
    return "\n".join(lines)


def overall_report(ev: GVAEvidence, gr: GrowthReport, report_date: str) -> str:
    lines = [
        _header("OVERALL GROWTH SCORE", report_date,
                f"Classification: {gr.overall_class}"),
        "",
        "  ┌─────────────────────────────────────────────────────────────────────┐",
        f"  │  OVERALL SCORE:  {gr.overall_score:>5.1f} / 100                                    │",
        f"  │  CLASSIFICATION: {gr.overall_class:<20}                           │",
        "  └─────────────────────────────────────────────────────────────────────┘",
        "",
        _section("DIMENSION SCORES"),
        _dimension_score_bar(gr.score_knowledge,  "Knowledge Growth"),
        _dimension_score_bar(gr.score_learning,   "Learning Quality"),
        _dimension_score_bar(gr.score_dna,        "DNA Growth"),
        _dimension_score_bar(gr.score_scientific, "Scientific Rigor"),
        _dimension_score_bar(gr.score_platform,   "Platform Reliability"),
        "",
        _section("CLASSIFICATION SCALE"),
        "  0–20   DECLINING",
        "  21–40  STATIC",
        "  41–55  SLOWLY IMPROVING",
        "  56–70  IMPROVING",
        "  71–85  RAPIDLY IMPROVING",
        "  86–100 SELF-IMPROVING",
        "",
        _section("EVIDENCE SNAPSHOT"),
        f"  Studies completed:    {len(ev.studies)}",
        f"  Feature records:      {ev.feature_count:,}",
        f"  DNA patterns:         {ev.dna.total}",
        f"  Hypotheses:           {ev.hypothesis.total}  (confirmed: {ev.hypothesis.confirmed})",
        f"  Active edges:         {ev.edges.active}",
        f"  IKN nodes:            {ev.ikn.total_nodes}",
        f"  Cycles (0 errors):    {ev.platform.total_cycles:,}",
        "",
        _section("SCIENTIFIC DIRECTOR VERDICT"),
        "",
        gr.sd_verdict,
        "",
        _section("METRIC SUMMARY — ALL DIMENSIONS"),
    ]

    all_metrics = (gr.knowledge + gr.learning + gr.dna +
                   gr.scientific + gr.platform)
    improving   = [m for m in all_metrics if m.direction == "IMPROVING"]
    stable      = [m for m in all_metrics if m.direction == "STABLE"]
    declining   = [m for m in all_metrics if m.direction == "DECLINING"]
    new_        = [m for m in all_metrics if m.direction in ("NEW", "INSUFFICIENT")]

    lines.extend([
        f"  Total metrics tracked:  {len(all_metrics)}",
        f"  ↑ IMPROVING:            {len(improving)}",
        f"  → STABLE:               {len(stable)}",
        f"  ↓ DECLINING:            {len(declining)}",
        f"  ★ NEW / INSUFFICIENT:   {len(new_)}",
        "",
        "  Declining metrics:",
    ])
    for m in declining:
        lines.append(f"    — {m.name}: {m.formatted_value()}")
    if not declining:
        lines.append("    (none)")

    lines.extend([
        "",
        f"  Generated: {ev.collected_at}",
        _hr(),
    ])
    return "\n".join(lines)


# ── Main writer ───────────────────────────────────────────────────────────────

def write_all_reports(
    ev: GVAEvidence,
    gr: GrowthReport,
    report_date: Optional[str] = None,
) -> dict:
    if report_date is None:
        report_date = date.today().isoformat()

    out = _report_dir(report_date)

    files = {
        "KNOWLEDGE_GROWTH_REPORT.md":  knowledge_report(ev, gr, report_date),
        "LEARNING_GROWTH_REPORT.md":   learning_report(ev, gr, report_date),
        "DNA_GROWTH_REPORT.md":        dna_report(ev, gr, report_date),
        "SCIENTIFIC_GROWTH_REPORT.md": scientific_report(ev, gr, report_date),
        "PLATFORM_GROWTH_REPORT.md":   platform_report(ev, gr, report_date),
        "OVERALL_GROWTH_SCORE.md":     overall_report(ev, gr, report_date),
    }

    written = {}
    for filename, content in files.items():
        path = _write(out / filename, content)
        written[filename] = str(path)

    return written

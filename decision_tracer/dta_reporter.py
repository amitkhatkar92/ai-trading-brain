"""
decision_tracer/dta_reporter.py
=================================
DTA-001 — Report Generator

Generates SYMBOL_DECISION_TRACE.md with the full 12-layer chain
and all 8 audit question answers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .dta_collector import TraceBundle, DNAMatch, EdgeMatch, IKNReference
from .dta_analyzer  import DTAAudit, AuditAnswer


DATA = Path(__file__).parent.parent / "data"
DTA_DIR = DATA / "dta"

_W = 78


def _hr(c: str = "─", w: int = _W) -> str: return c * w
def _dhr() -> str:                         return "═" * _W


def _header(title: str, symbol: str, ts: str) -> str:
    return (
        f"{_dhr()}\n"
        f"  DTA-001 | DECISION TRACEABILITY AUDIT\n"
        f"  Symbol: {symbol}    Generated: {ts}\n"
        f"  {title}\n"
        f"{_dhr()}"
    )


def _section(title: str) -> str:
    return f"\n{_hr()}\n  ▸ {title}\n{_hr()}"


def _sub(title: str) -> str:
    return f"\n  ── {title}"


def _layer(n: int, title: str, status: str = "") -> str:
    badge = f"  [{status}]" if status else ""
    return f"\n  LAYER {n:02d}: {title}{badge}\n  {_hr('·')}"


def _kv(k: str, v: Any, indent: int = 4) -> str:
    pad = " " * indent
    return f"{pad}{k:<32} {v}"


def _bullet(items, indent: int = 4) -> str:
    pad = " " * indent
    return "\n".join(f"{pad}• {item}" for item in items)


def _feat_table(features: dict, limit: int = 20) -> str:
    interesting = [
        "rsi", "rsi_overbought", "rsi_oversold",
        "macd_signal_norm", "macd_bull", "macd_bear",
        "volume_ratio_raw", "volume_spike",
        "mom_1d", "mom_5d", "mom_20d",
        "breadth", "pcr", "vix", "atr_14",
        "adx_score", "avg_conviction",
        "intra_range", "close_pos",
        "regime_score", "regime_bull", "regime_range",
        "global_bias", "sector_flow_count",
    ]
    lines = [f"    {'FEATURE':<30} {'VALUE':>12}"]
    lines.append(f"    {_hr('─', 44)}")
    for k in interesting:
        v = features.get(k)
        if v is not None:
            lines.append(f"    {k:<30} {float(v):>12.4f}")
    # Any extras not in the list
    shown = set(interesting)
    extras = [(k, v) for k, v in features.items() if k not in shown][:max(0, limit - len(interesting))]
    for k, v in extras:
        if v is not None:
            lines.append(f"    {k:<30} {float(v) if isinstance(v, (int, float)) else v!r:>12}")
    return "\n".join(lines)


def _edge_table(matches: list, show_n: int = 8) -> str:
    lines = [
        f"    {'EDGE':<38} {'STATUS':<10} {'PREC':>6} {'SHARPE':>8} "
        f"{'OOS_WR':>7} {'MATCH':>6}",
        f"    {_hr('─', 78)}",
    ]
    for em in matches[:show_n]:
        match_str = f"{em.satisfied_count}/{em.total_count}" if em.total_count else "N/A"
        lines.append(
            f"    {em.name:<38} {em.status:<10} "
            f"{em.precision*100:>5.0f}% {em.sharpe:>8.2f} "
            f"{em.oos_wr*100:>6.0f}% {match_str:>6}"
        )
    return "\n".join(lines)


def _dna_table(matches: list, show_n: int = 15) -> str:
    lines = [
        f"    {'FEATURE':<28} {'DIR':<7} {'CAT':<22} {'CONF':>6} {'MATCH':>7}",
        f"    {_hr('─', 74)}",
    ]
    for m in matches[:show_n]:
        hit = "  ✓ HIT" if m.matched else "     -"
        lines.append(
            f"    {m.feature_name:<28} {m.direction:<7} {m.category:<22} "
            f"{m.confidence:>6.3f} {hit}"
        )
    return "\n".join(lines)


def _ikn_table(refs: list, show_n: int = 12) -> str:
    lines = [
        f"    {'NODE_TYPE':<22} {'NAME':<45}",
        f"    {_hr('─', 70)}",
    ]
    for r in refs[:show_n]:
        lines.append(f"    {r.node_type:<22} {r.name[:45]}")
        for rel in r.relationships[:2]:
            lines.append(f"      └─ {rel[:60]}")
    return "\n".join(lines)


def _decision_history_table(history: list, show_n: int = 10) -> str:
    lines = [
        f"    {'DATE':<14} {'DECISION':<10} {'CONFIDENCE':>11} {'REGIME':<15} {'STRATEGY'}",
        f"    {_hr('─', 72)}",
    ]
    for r in history[:show_n]:
        lines.append(
            f"    {r.ts[:10]:<14} {r.decision:<10} {r.confidence:>11.2f} "
            f"{r.regime:<15} {r.strategy}"
        )
    return "\n".join(lines)


def generate_report(bundle: TraceBundle, audit: DTAAudit) -> str:
    d   = bundle.decision
    ctx = bundle.market_ctx
    sig = bundle.signal
    feat = bundle.features

    lines = [
        _header("DECISION TRACEABILITY AUDIT", bundle.symbol, bundle.audit_ts),
        "",
        _kv("SYMBOL:",    bundle.symbol,      indent=2),
        _kv("DECISION:",  d.decision if d else "NOT FOUND",  indent=2),
        _kv("CONFIDENCE:",f"{d.confidence:.2f}/10" if d else "N/A", indent=2),
        _kv("STRATEGY:",  d.strategy if d else "N/A",        indent=2),
        _kv("CYCLE ID:",  d.cycle_id if d else "N/A",        indent=2),
        _kv("CYCLE TIME:",d.ts[:19] if d else "N/A",         indent=2),
        "",
        f"  {'─'*76}",
        f"  VERDICT: {audit.overall_verdict}",
        f"  {'─'*76}",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # 12-LAYER DECISION CHAIN
    # ══════════════════════════════════════════════════════════════════════════
    lines.append(_section("12-LAYER DECISION CHAIN"))

    # LAYER 1 — Raw Market Data
    lines.append(_layer(1, "RAW MARKET DATA",
                        "OK" if ctx else "N/A"))
    if ctx:
        lines += [
            _kv("Date/Time:",     ctx.ts[:19] if ctx.ts else "N/A"),
            _kv("VIX:",           f"{ctx.vix:.2f}"),
            _kv("Regime:",        ctx.regime),
            _kv("Market breadth:",f"{ctx.breadth:.4f}"),
            _kv("PCR:",           f"{ctx.pcr:.4f}"),
            _kv("Distortion:",    ctx.distortion),
            _kv("Trading allowed:",str(ctx.trading_allowed)),
            _kv("Size multiplier:",f"{ctx.size_multiplier:.2f}×"),
        ]
    else:
        lines.append("    [No market data event found in trace]")

    # LAYER 2 — Feature Extraction
    lines.append(_layer(2, "FEATURE EXTRACTION",
                        "OK" if feat and feat.features else "N/A"))
    if feat and feat.features:
        lines += [
            _kv("Feature record date:", feat.ts or "N/A"),
            _kv("Total features:", str(len(feat.features))),
            "",
        ]
        lines.append(_feat_table(feat.features))
        if feat.forward_return is not None:
            lines.append(_kv("Forward return (recorded):", f"{feat.forward_return:.4f}"))
    else:
        lines.append("    [No feature record found in EDE database for this symbol]")

    # LAYER 3 — PMCI / Scanner Signal
    lines.append(_layer(3, "PMCI SCORE / SCANNER SIGNAL",
                        "OK" if sig else "N/A"))
    if sig:
        lines += [
            _kv("Scanner direction:", sig.direction),
            _kv("Scanner strategy:",  sig.strategy),
            _kv("Scanner confidence:",f"{sig.confidence:.2f}/10"),
            _kv("Source agent:",      sig.source),
        ]
        if ctx and ctx.regime_probs:
            lines.append(_kv("Regime probabilities:", ""))
            for k, v in ctx.regime_probs.items():
                if k != "dominant":
                    lines.append(_kv(f"  {k}:", f"{float(v):.3f}" if isinstance(v, (int, float)) else str(v)))
            lines.append(_kv("Dominant:", ctx.regime_probs.get("dominant", "")))
    else:
        lines.append("    [No scanner signal found for this symbol in cycle]")

    # LAYER 4 — CDS Score / Strategy Mix
    lines.append(_layer(4, "CDS SCORE / STRATEGY ALLOCATION"))
    if ctx and ctx.strategy_mix:
        lines.append(_kv("Meta-top strategy:", ctx.meta_top_strategy))
        lines.append(_kv("Strategy allocation:", ""))
        for strat, alloc in sorted(ctx.strategy_mix.items(), key=lambda x: -x[1]):
            lines.append(_kv(f"  {strat}:", f"{alloc:.4f}"))
    else:
        lines.append("    [Strategy allocation not available in trace]")

    # LAYER 5 — Institutional DNA Matches
    lines.append(_layer(5, "INSTITUTIONAL DNA MATCHES",
                        f"MATCHED: {sum(1 for m in bundle.dna_matches if m.matched)}"))
    matched_count = sum(1 for m in bundle.dna_matches if m.matched)
    lines += [
        _kv("Total DNA patterns evaluated:", str(len(bundle.dna_matches))),
        _kv("Matched (favorable direction):", str(matched_count)),
        _kv("Winner DNA hits:", str(sum(1 for m in bundle.dna_matches if m.matched and m.category == "winner"))),
        _kv("Loser DNA hits:", str(sum(1 for m in bundle.dna_matches if m.matched and m.category == "loser"))),
        "",
    ]
    lines.append(_dna_table(bundle.dna_matches, show_n=15))

    # LAYER 6 — Knowledge Graph References
    lines.append(_layer(6, "KNOWLEDGE GRAPH (IKN) REFERENCES",
                        f"{len(bundle.ikn_refs)} nodes"))
    if bundle.ikn_refs:
        lines.append(_ikn_table(bundle.ikn_refs))
    else:
        lines.append("    [No IKN nodes matched current feature set]")

    # LAYER 7 — Historical Evidence
    lines.append(_layer(7, "HISTORICAL EVIDENCE"))
    lines += [
        _kv("Total decision history records:", str(len(bundle.decision_history))),
        "",
    ]
    if bundle.decision_history:
        lines.append(_decision_history_table(bundle.decision_history))
    else:
        lines.append("    [No prior decision history]")

    # LAYER 8 — Research Studies
    lines.append(_layer(8, "RESEARCH STUDIES"))
    if bundle.study_references:
        for ref in bundle.study_references:
            lines.append(f"    • {ref}")
    else:
        lines.append("    [No study references matched current feature set]")

    # LAYER 9 — Scientific Director
    lines.append(_layer(9, "SCIENTIFIC DIRECTOR OBSERVATIONS"))
    confirmed = [h for h in bundle.hypothesis_refs if h["status"] == "CONFIRMED"]
    proposed  = [h for h in bundle.hypothesis_refs if h["status"] == "PROPOSED"]
    lines += [
        _kv("Confirmed hypotheses:", str(len(confirmed))),
        _kv("Proposed hypotheses:", str(len(proposed))),
    ]
    for h in confirmed[:3]:
        lines.append(f"    ✓ CONFIRMED: [{h['id']}] {h['title']}")
    for h in proposed[:5]:
        lines.append(f"    ○ PROPOSED:  [{h['id']}] {h['title']}")

    # LAYER 10 — Risk Analysis
    lines.append(_layer(10, "RISK ANALYSIS",
                        "PASSED" if (bundle.risk_ctx and bundle.risk_ctx.risk_passed) else "N/A"))
    if bundle.risk_ctx and d:
        rc = bundle.risk_ctx
        lines += [
            _kv("Risk check:", "PASSED" if rc.risk_passed else "FLAGGED"),
            _kv("Monte Carlo simulation:", "APPROVED" if rc.simulation_approved else "REJECTED"),
            _kv("Risk Guardian:", "APPROVED" if rc.guardian_approved else "BLOCKED"),
            _kv("Position modifier:", f"{d.position_modifier:.3f} ({d.position_modifier*100:.0f}% of max)"),
            _kv("Portfolio drawdown:", f"{rc.drawdown_pct:.2f}%"),
            _kv("Open positions:", str(rc.open_positions)),
            _kv("VIX level:", f"{d.vix:.2f}"),
            _kv("Regime:", d.regime),
        ]
        if rc.risk_reasons:
            lines.append(_kv("Risk flags:", ""))
            for r in rc.risk_reasons[:5]:
                lines.append(f"    ! {r[:80]}")
        else:
            lines.append(_kv("Risk flags:", "None"))
        lines.append(_kv("Kill switch thresholds:",
                         "VIX>45 | daily_loss>2% | NIFTY_drop>-5%"))
    else:
        lines.append("    [Risk context not available]")

    # LAYER 11 — Portfolio Decision
    lines.append(_layer(11, "PORTFOLIO DECISION",
                        d.decision if d else "N/A"))
    if d:
        lines += [
            _kv("Final decision:", d.decision),
            _kv("Confidence score:", f"{d.confidence:.4f}/10"),
            _kv("Approval threshold:", "≥6.5 partial-size  ≥6.8 full-size"),
            _kv("Strategy applied:", d.strategy),
            _kv("Position modifier:", f"{d.position_modifier:.3f}"),
        ]
        if d.rejection_reason:
            lines.append(_kv("Rejection reason:", ""))
            lines.append(f"    {d.rejection_reason[:200]}")
    else:
        lines.append("    [No portfolio decision record found]")

    # LAYER 12 — Broker Order
    lines.append(_layer(12, "BROKER ORDER"))
    if d and d.decision == "APPROVED":
        lines += [
            _kv("Order status:", "PLACED (if paper trading) or LIVE"),
            _kv("Broker:", "Dhan (live) / Paper journal (PAPER_TRADING=True)"),
            _kv("Note:", "paper_trades.csv logs open/close if paper mode active"),
        ]
        if bundle.replay_stats:
            rs = bundle.replay_stats
            lines += [
                _kv("Replay reference win rate:", f"{rs.get('win_rate', 0):.1f}%"),
                _kv("Replay avg R-multiple:", f"{rs.get('avg_r_multiple', 0):.3f}"),
                _kv("Replay profit factor:", f"{rs.get('profit_factor', 0):.2f}"),
            ]
    else:
        lines.append("    [Decision was REJECTED — no order placed]")
        if d:
            lines.append(f"    Reason: {d.rejection_reason[:200]}")

    # ══════════════════════════════════════════════════════════════════════════
    # 8 AUDIT QUESTIONS
    # ══════════════════════════════════════════════════════════════════════════
    lines.append(_section("8 AUDIT QUESTIONS"))

    for i, aq in enumerate(audit.answers, 1):
        verdict_badge = {"ANSWERED": "✓", "PARTIAL": "~", "INSUFFICIENT": "?"}.get(aq.verdict, "?")
        lines.append(f"\n  Q{i}: {aq.question}")
        lines.append(f"  {_hr('·', 74)}")
        lines.append(f"  [{verdict_badge} {aq.verdict}]  {aq.answer}")
        if aq.evidence:
            lines.append("")
            for ev in aq.evidence:
                lines.append(f"    • {ev}")

    # ══════════════════════════════════════════════════════════════════════════
    # ALTERNATIVE CANDIDATES
    # ══════════════════════════════════════════════════════════════════════════
    lines.append(_section("ALTERNATIVE CANDIDATES (Same Cycle)"))
    if bundle.alternative_candidates:
        lines.append(
            f"    {'SYMBOL':<16} {'DIRECTION':<10} {'CONFIDENCE':>11} {'STRATEGY'}"
        )
        lines.append(f"    {_hr('─', 62)}")
        for alt in bundle.alternative_candidates:
            flag = " ← TARGET" if alt.symbol == bundle.symbol else ""
            lines.append(
                f"    {alt.symbol:<16} {alt.direction:<10} {alt.confidence:>11.2f} "
                f"{alt.strategy}{flag}"
            )
    else:
        lines.append("    [No alternative candidates found in this cycle]")

    # ══════════════════════════════════════════════════════════════════════════
    # EDGE CONDITIONS DETAIL
    # ══════════════════════════════════════════════════════════════════════════
    lines.append(_section("ACTIVE EDGE CONDITIONS (Fully Evaluated)"))
    active_edges = [e for e in bundle.edge_matches if e.status == "ACTIVE"]
    if active_edges:
        for em in active_edges:
            hit = "FULL MATCH" if em.all_satisfied else f"PARTIAL {em.satisfied_count}/{em.total_count}"
            lines.append(f"\n    [{hit}] {em.name}")
            lines.append(f"    precision={em.precision*100:.0f}%  "
                         f"sharpe={em.sharpe:.2f}  oos_wr={em.oos_wr*100:.0f}%")
            feat_dict = bundle.features.features if bundle.features else {}
            for c in em.conditions:
                fval = feat_dict.get(c.get("feature", ""), "N/A")
                sat  = _eval_cond_str(c, feat_dict)
                lines.append(
                    f"      {sat}  {c.get('feature'):<28} {c.get('operator')} "
                    f"{c.get('threshold')}  (current={fval!r})"
                )
    else:
        lines.append("    [No active edges to evaluate]")

    # ══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    lines.append(f"\n{_dhr()}")
    lines.append(f"  DTA-001 | Generated: {bundle.audit_ts}")
    lines.append(f"  READ-ONLY AUDIT — No knowledge was modified.")
    lines.append(_dhr())
    return "\n".join(lines)


def _eval_cond_str(cond: dict, features: dict) -> str:
    """Return ✓ or ✗ for whether a condition is satisfied."""
    feat = cond.get("feature", "")
    op   = cond.get("operator", "")
    thr  = cond.get("threshold", 0)
    val  = features.get(feat)
    if val is None:
        return " ? "
    try:
        v = float(val)
        t = float(thr)
        if op == "<=" : ok = v <= t
        elif op == "<" : ok = v < t
        elif op == ">=": ok = v >= t
        elif op == ">" : ok = v > t
        else:            ok = abs(v - t) < 1e-9
        return " ✓ " if ok else " ✗ "
    except Exception:
        return " ? "


def write_report(bundle: TraceBundle, audit: DTAAudit,
                 report_date: Optional[str] = None) -> Path:
    from datetime import date
    if report_date is None:
        report_date = date.today().isoformat()

    out_dir = DTA_DIR / report_date
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{bundle.symbol}_DECISION_TRACE.md"
    path     = out_dir / filename
    content  = generate_report(bundle, audit)
    path.write_text(content, encoding="utf-8")
    return path

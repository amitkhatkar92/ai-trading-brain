"""
Research Experiment 001A — Knowledge Generation Validation Pipeline
====================================================================
Transforms RE001 replay evidence into accumulated knowledge.
Runs: FeatureDB enrichment → PatternMiner → CandidateGenerator →
      StrategyTester → EdgeRankingEngine → MetaModel reporting.

Does NOT replay the market. Does NOT modify AI algorithms.
Does NOT optimise parameters.
"""

from __future__ import annotations
import json
import os
import sqlite3
import sys
from datetime import datetime

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# ── Logging ─────────────────────────────────────────────────────────────────
from utils import get_logger
log = get_logger("re001a")

# ── Knowledge store paths ────────────────────────────────────────────────────
FEAT_DB   = os.path.join(ROOT, "data", "ede_feature_db.json")
EDGES_DB  = os.path.join(ROOT, "data", "discovered_edges.json")
STRATS_DB = os.path.join(ROOT, "data", "evolved_strategies.json")
PERF_DB   = os.path.join(ROOT, "data", "strategy_performance.json")
ML_DS     = os.path.join(ROOT, "data", "ml_performance_dataset.json")
RE001_DB  = os.path.join(ROOT, "data", "re001_replay.db")

# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _snapshot_knowledge_store(label: str) -> dict:
    """Return counts for all key knowledge stores."""
    snap = {"label": label, "ts": datetime.now().isoformat()}
    # feature DB
    with open(FEAT_DB) as f:
        feat = json.load(f)
    snap["feat_total"] = len(feat)
    snap["feat_labeled"] = sum(1 for r in feat if r.get("forward_return", 0.0) != 0.0)
    snap["feat_symbols"] = len(set(r.get("symbol", "") for r in feat))
    # edges
    with open(EDGES_DB) as f:
        edges = json.load(f)
    snap["edges_total"] = len(edges)
    by_status: dict[str, int] = {}
    for v in edges.values():
        st = v.get("status", "?")
        by_status[st] = by_status.get(st, 0) + 1
    snap["edges_by_status"] = by_status
    # evolved strategies
    with open(STRATS_DB) as f:
        strats = json.load(f)
    snap["strats_total"] = len(strats)
    # perf
    with open(PERF_DB) as f:
        perf = json.load(f)
    snap["perf_tracked"] = len(perf)
    # ml dataset
    snap["ml_records"] = 0
    if os.path.exists(ML_DS):
        with open(ML_DS) as f:
            ml = json.load(f)
        snap["ml_records"] = len(ml)
    return snap


def _log_banner(msg: str) -> None:
    log.info("═" * 66)
    log.info("  %s", msg)
    log.info("═" * 66)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1 — FEATURE DATABASE ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════

def stage1_enrich_feature_db() -> dict:
    """
    Extract real OHLCV-based feature vectors from re001_replay.db and
    append them — with actual forward_return labels — to ede_feature_db.json.
    """
    _log_banner("STAGE 1 — Feature Database Enrichment")

    conn = sqlite3.connect(RE001_DB)
    conn.row_factory = sqlite3.Row

    # Load all OHLCV data, pivot by (symbol, date)
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily ORDER BY symbol, trade_date"
    )
    rows = cur.fetchall()
    log.info("[Stage1] Loaded %d OHLCV rows from re001_replay.db", len(rows))

    # Build symbol → list[(date, open, high, low, close, volume)]
    from collections import defaultdict
    sym_data: dict[str, list] = defaultdict(list)
    for r in rows:
        sym_data[r["symbol"]].append({
            "d": r["trade_date"],
            "o": r["open"],   "h": r["high"],
            "l": r["low"],    "c": r["close"],
            "v": r["volume"],
        })

    # Load sector_conviction_daily for context features
    cur.execute(
        "SELECT record_date, sector, sector_conviction_score, participation_rate_5d "
        "FROM sector_conviction_daily WHERE data_quality='FULL'"
    )
    sc_rows = cur.fetchall()
    # date → sector → (conviction, part5d)
    sc_map: dict[str, dict[str, tuple]] = defaultdict(dict)
    for r in sc_rows:
        sc_map[r["record_date"]][r["sector"]] = (
            r["sector_conviction_score"] or 0.0,
            r["participation_rate_5d"] or 0.0,
        )

    # Load stock→sector map
    cur.execute("SELECT symbol, primary_sector FROM stock_sector_map")
    sym_sector: dict[str, str] = {r["symbol"]: r["primary_sector"] for r in cur.fetchall()}
    conn.close()

    # Compute features per symbol per date
    new_rows: list[dict] = []
    skipped_no_next = 0
    skipped_no_history = 0

    for symbol, candles in sym_data.items():
        if len(candles) < 6:   # need at least 5 days lookback + current
            skipped_no_history += 1
            continue
        sector = sym_sector.get(symbol, "UNKNOWN")

        for i in range(5, len(candles)):  # start at index 5 (have 5 days history)
            today = candles[i]
            prev1 = candles[i - 1]
            prev5 = candles[i - 5]

            # Forward return requires next day
            if i + 1 >= len(candles):
                skipped_no_next += 1
                continue

            nxt = candles[i + 1]
            if today["c"] <= 0 or nxt["c"] <= 0:
                continue

            # ── Price features ────────────────────────────────────────────
            mom_1d = (today["c"] - prev1["c"]) / prev1["c"] if prev1["c"] > 0 else 0.0
            mom_5d = (today["c"] - prev5["c"]) / prev5["c"] if prev5["c"] > 0 else 0.0

            # Intraday range as volatility proxy
            intra_range = (today["h"] - today["l"]) / today["c"] if today["c"] > 0 else 0.0
            close_pos   = ((today["c"] - today["l"]) / (today["h"] - today["l"])
                           if (today["h"] - today["l"]) > 0 else 0.5)

            # Volume ratio (today vs 5-day avg)
            vols_5 = [candles[i - k]["v"] for k in range(1, 6) if candles[i - k]["v"]]
            avg_vol = sum(vols_5) / len(vols_5) if vols_5 else 1.0
            vol_ratio = (today["v"] / avg_vol) if avg_vol > 0 else 1.0

            # Consecutive up days (momentum)
            cons_up = 0
            for k in range(1, 5):
                if candles[i - k]["c"] < candles[i - k - 1]["c"]:
                    break
                cons_up += 1

            # ── Sector conviction features ─────────────────────────────────
            sc = sc_map.get(today["d"], {}).get(sector, (0.0, 0.0))
            sect_conviction = sc[0]
            sect_part5d = sc[1]

            # Average conviction across all sectors for breadth proxy
            day_sc = sc_map.get(today["d"], {})
            avg_conviction = (sum(v[0] for v in day_sc.values()) / len(day_sc)
                              if day_sc else 0.0)

            # Regime-related features (all sessions are SIDEWAYS = RANGE_MARKET)
            regime_score  = 0.5   # range_market
            regime_bull   = 0.0
            regime_range  = 1.0
            regime_bear   = 0.0
            regime_vol    = 0.0

            # ── Forward return label ─────────────────────────────────────
            forward_return = (nxt["c"] - today["c"]) / today["c"]

            feat_vec = {
                "mom_1d":          round(mom_1d, 6),
                "mom_5d":          round(mom_5d, 6),
                "intra_range":     round(intra_range, 6),
                "close_pos":       round(close_pos, 4),
                "vol_ratio":       round(min(vol_ratio, 5.0), 4),
                "cons_up_days":    float(cons_up),
                "sect_conviction": round(sect_conviction, 4),
                "sect_part5d":     round(sect_part5d, 4),
                "avg_conviction":  round(avg_conviction, 4),
                "regime_score":    regime_score,
                "regime_bull":     regime_bull,
                "regime_range":    regime_range,
                "regime_bear":     regime_bear,
                "regime_volatile": regime_vol,
                "vix":             0.375,    # neutral (no VIX in replay)
                "vix_low":         1.0,      # VIX likely low in SIDEWAYS
                "vix_high":        0.0,
                "breadth":         round(avg_conviction, 4),
                "breadth_strong":  1.0 if avg_conviction > 0.6 else 0.0,
                "breadth_weak":    1.0 if avg_conviction < 0.4 else 0.0,
                "pcr":             0.5,      # neutral
                "pcr_bullish":     0.0,
                "pcr_bearish":     0.0,
                "pcr_neutral":     1.0,
                "global_bias":     0.5,      # neutral
                "sector_flow_count": 1.2,   # 12 sectors / 10
                "event_count":     0.0,
            }

            new_rows.append({
                "features":       feat_vec,
                "forward_return": round(forward_return, 6),
                "symbol":         symbol,
                "ts":             today["d"],
                "source":         "RE001_OHLCV",
                "sector":         sector,
            })

    log.info("[Stage1] Computed %d feature rows from OHLCV "
             "(skipped: no_next=%d, no_history=%d)",
             len(new_rows), skipped_no_next, skipped_no_history)

    # Load existing DB and append
    with open(FEAT_DB) as f:
        existing = json.load(f)

    before = len(existing)
    enriched = existing + new_rows
    with open(FEAT_DB, "w") as f:
        json.dump(enriched, f)
    after = len(enriched)

    labeled_before = sum(1 for r in existing if r.get("forward_return", 0.0) != 0.0)
    labeled_after  = sum(1 for r in enriched if r.get("forward_return", 0.0) != 0.0)
    pos_label = sum(1 for r in new_rows if r["forward_return"] >= 0.008)
    neg_label = sum(1 for r in new_rows if r["forward_return"] < 0.008)

    result = {
        "feat_before":    before,
        "feat_after":     after,
        "feat_added":     after - before,
        "labeled_before": labeled_before,
        "labeled_after":  labeled_after,
        "positive_labels": pos_label,
        "negative_labels": neg_label,
        "positive_rate":   round(pos_label / len(new_rows), 4) if new_rows else 0,
        "symbols_added":   len(set(r["symbol"] for r in new_rows)),
        "dates_covered":   len(set(r["ts"] for r in new_rows)),
    }
    log.info("[Stage1] Feature DB: %d → %d rows (+%d). "
             "Labeled: %d → %d. Positive rate: %.1f%%",
             before, after, after - before,
             labeled_before, labeled_after,
             100 * result["positive_rate"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# STAGES 2-6 — FULL EDGE DISCOVERY PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def stages_2_to_6_run_ede() -> dict:
    """
    Run the complete EdgeDiscoveryEngine cycle.
    Stages: PatternMiner → CandidateGenerator → StrategyTester →
            EdgeRankingEngine → persist to knowledge stores.
    """
    _log_banner("STAGES 2–6 — Edge Discovery Pipeline")

    from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel, SectorFlow
    from edge_discovery.edge_discovery_engine import EdgeDiscoveryEngine
    from edge_discovery.pattern_miner import load_feature_db

    # ── Build a MarketSnapshot reflecting the terminal state of RE001 ───────
    # Source: RE001 findings — 2026-07-30, SIDEWAYS, IT leading
    sector_flows = [
        SectorFlow("IT",               0.85, 1, ["NAUKRI", "INFY", "WIPRO"]),
        SectorFlow("AUTO",             0.72, 2, ["M&M", "HEROMOTOCO", "TVSMOTOR"]),
        SectorFlow("FMCG",             0.63, 3, ["NESTLEIND", "SAPPHIRE"]),
        SectorFlow("PHARMA",           0.55, 4, ["SUNPHARMA", "ABBOTINDIA"]),
        SectorFlow("BANKING_FINANCE",  0.48, 5, ["BAJFINANCE", "ICICIBANK"]),
        SectorFlow("METALS",           0.46, 6, ["JSWSTEEL"]),
        SectorFlow("CHEMICALS",        0.35, 7, ["BASF"]),
        SectorFlow("ENERGY",           0.29, 8, ["GAIL"]),
        SectorFlow("CONSUMER_DURABLES",0.28, 9, ["BLUESTARCO"]),
        SectorFlow("INFRA",            0.21, 10, []),
        SectorFlow("DEFENCE",          0.18, 11, []),
        SectorFlow("TELECOM",          0.15, 12, []),
    ]

    snapshot = MarketSnapshot(
        timestamp            = datetime(2026, 7, 30, 15, 30),
        indices              = {},
        regime               = RegimeLabel.RANGE_MARKET,   # SIDEWAYS maps here
        volatility           = VolatilityLevel.LOW,        # calm market
        vix                  = 14.2,
        fii_dii              = None,
        sector_flows         = sector_flows,
        sector_leaders       = ["NAUKRI", "JSWSTEEL", "SUNPHARMA", "M&M"],
        events_today         = [],
        market_breadth       = 0.62,   # avg of last-day sector participation
        pcr                  = 0.92,   # slightly bullish
        global_bias          = "bullish",
        global_sentiment_score = 0.18,
    )
    log.info("[EDE] MarketSnapshot: %s", snapshot.summary())

    # Capture edges BEFORE
    with open(EDGES_DB) as f:
        edges_before = json.load(f)
    with open(STRATS_DB) as f:
        strats_before = json.load(f)

    ede = EdgeDiscoveryEngine()

    log.info("[EDE] Loading feature DB…")
    db = load_feature_db()
    log.info("[EDE] Feature DB: %d rows", len(db))

    report = ede.run_discovery_cycle(snapshot, publish_event=False)
    log.info("[EDE] Report:\n%s", report)

    # Capture edges AFTER
    with open(EDGES_DB) as f:
        edges_after = json.load(f)
    with open(STRATS_DB) as f:
        strats_after = json.load(f)

    # Compute deltas
    new_edges      = [k for k in edges_after if k not in edges_before]
    updated_edges  = [k for k in edges_after if k in edges_before
                      and edges_after[k].get("status") != edges_before[k].get("status")]
    removed_edges  = [k for k in edges_before if k not in edges_after]
    new_strats     = [k for k in strats_after  if k not in strats_before]

    result = {
        "report":           report,
        "edges_before":     len(edges_before),
        "edges_after":      len(edges_after),
        "new_edges":        new_edges,
        "updated_edges":    updated_edges,
        "removed_edges":    removed_edges,
        "strats_before":    len(strats_before),
        "strats_after":     len(strats_after),
        "new_strats":       new_strats,
        "edges_by_status_after": {
            st: sum(1 for v in edges_after.values() if v.get("status") == st)
            for st in ["ACTIVE", "CANDIDATE", "DECAYING", "DEPRECATED"]
        },
    }
    log.info("[EDE] Δ edges: %+d  |  new=%d  |  updated=%d  |  removed=%d",
             len(edges_after) - len(edges_before),
             len(new_edges), len(updated_edges), len(removed_edges))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6 — METAMODEL REPORTING
# ═══════════════════════════════════════════════════════════════════════════

def stage6_metamodel() -> dict:
    """
    Initialise MetaModel, load any available training data, report readiness.
    Does NOT inject synthetic observations.
    """
    _log_banner("STAGE 6 — MetaModel Status")

    from meta_learning.meta_model import MetaModel
    from meta_learning.performance_dataset import PerformanceDataset

    dataset = PerformanceDataset()
    records = dataset.get_all()
    record_count = len(records)

    log.info("[MetaModel] PerformanceDataset records: %d (need ≥20 to train)",
             record_count)

    model = MetaModel()
    if record_count >= 10:
        from meta_learning.meta_model import Observation
        from meta_learning.feature_extractor import FeatureExtractor
        ext = FeatureExtractor()
        observations = []
        for rec in records:
            fv  = ext.extract_from_dict(rec.feature_dict())
            obs = Observation(
                features   = fv.to_list(),
                strategy   = rec.strategy,
                r_multiple = rec.r_multiple,
            )
            observations.append(obs)
        model.fit(observations)
        trained = model.is_trained()
        log.info("[MetaModel] Fitted with %d observations. Trained: %s",
                 len(observations), trained)
    else:
        log.info("[MetaModel] Insufficient records (%d). Model NOT trained.",
                 record_count)
        trained = False

    return {
        "ml_dataset_exists": os.path.exists(ML_DS),
        "ml_records":        record_count,
        "model_trained":     trained,
        "min_required":      10,
        "reason_not_trained": (
            None if trained else
            "No trade outcomes available from RE001 — all opportunities "
            "remained open at window end. ml_performance_dataset.json not yet created."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7 — KNOWLEDGE STORE FINAL VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def stage7_verify_knowledge_stores() -> dict:
    """Read all knowledge stores and report final state."""
    _log_banner("STAGE 7 — Knowledge Store Final Verification")

    result = {}

    # Feature DB
    with open(FEAT_DB) as f:
        feat = json.load(f)
    result["feat_total"]    = len(feat)
    result["feat_labeled"]  = sum(1 for r in feat if r.get("forward_return", 0.0) != 0.0)
    result["feat_re001"]    = sum(1 for r in feat if r.get("source") == "RE001_OHLCV")
    result["feat_symbols"]  = len(set(r.get("symbol", "") for r in feat))

    # Edges
    with open(EDGES_DB) as f:
        edges = json.load(f)
    result["edges_total"] = len(edges)
    for st in ["ACTIVE", "CANDIDATE", "DECAYING", "DEPRECATED"]:
        result[f"edges_{st.lower()}"] = sum(
            1 for v in edges.values() if v.get("status") == st
        )

    # Strategies
    with open(STRATS_DB) as f:
        strats = json.load(f)
    result["strats_total"] = len(strats)

    # Strategy performance
    with open(PERF_DB) as f:
        perf = json.load(f)
    result["perf_tracked"] = len(perf)

    # ML dataset
    result["ml_exists"]  = os.path.exists(ML_DS)
    result["ml_records"] = 0
    if result["ml_exists"]:
        with open(ML_DS) as f:
            ml = json.load(f)
        result["ml_records"] = len(ml)

    log.info("[Stage7] Feature DB: %d rows (%d labeled, %d from RE001)",
             result["feat_total"], result["feat_labeled"], result["feat_re001"])
    log.info("[Stage7] Edges: %d total | ACTIVE=%d CANDIDATE=%d "
             "DECAYING=%d DEPRECATED=%d",
             result["edges_total"],
             result["edges_active"], result["edges_candidate"],
             result["edges_decaying"], result["edges_deprecated"])
    log.info("[Stage7] Strategies: %d | Perf tracked: %d | ML records: %d",
             result["strats_total"], result["perf_tracked"], result["ml_records"])

    return result


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    start_ts = datetime.now()
    _log_banner("RESEARCH EXPERIMENT 001A — Knowledge Generation Validation")
    log.info("  Input DB  : %s", RE001_DB)
    log.info("  Feat DB   : %s", FEAT_DB)
    log.info("  Edges DB  : %s", EDGES_DB)
    log.info("  Strats DB : %s", STRATS_DB)
    log.info("  Mode      : POST-REPLAY LEARNING (no market replay)")

    # Baseline snapshot
    baseline = _snapshot_knowledge_store("BEFORE")
    log.info("[Baseline] feat=%d (labeled=%d) | edges=%d | strats=%d | ml=%d",
             baseline["feat_total"], baseline["feat_labeled"],
             baseline["edges_total"], baseline["strats_total"],
             baseline["ml_records"])

    # Run pipeline stages
    s1 = stage1_enrich_feature_db()
    s2_6 = stages_2_to_6_run_ede()
    s6_meta = stage6_metamodel()
    s7 = stage7_verify_knowledge_stores()

    # Final snapshot
    final = _snapshot_knowledge_store("AFTER")

    elapsed = (datetime.now() - start_ts).total_seconds()

    # ── Print consolidated report ──────────────────────────────────────────
    print()
    print("=" * 70)
    print("  RESEARCH EXPERIMENT 001A — RESULTS SUMMARY")
    print("=" * 70)

    print("\n--- STAGE 1: Feature Database ---")
    print(f"  Before:          {s1['feat_before']:>6} rows ({s1['labeled_before']} labeled)")
    print(f"  RE001 rows added:{s1['feat_added']:>6}")
    print(f"  After:           {s1['feat_after']:>6} rows ({s1['labeled_after']} labeled)")
    print(f"  Symbols covered: {s1['symbols_added']}")
    print(f"  Dates covered:   {s1['dates_covered']}")
    print(f"  Positive rate:   {100*s1['positive_rate']:.1f}% "
          f"({s1['positive_labels']} pos / {s1['negative_labels']} neg)")

    print("\n--- STAGES 2-6: Edge Discovery Pipeline ---")
    print(f"  Edges BEFORE:    {s2_6['edges_before']}")
    print(f"  Edges AFTER:     {s2_6['edges_after']}")
    print(f"  New edges:       {len(s2_6['new_edges'])}")
    print(f"  Updated edges:   {len(s2_6['updated_edges'])}")
    print(f"  Removed edges:   {len(s2_6['removed_edges'])}")
    print(f"  By status after: {s2_6['edges_by_status_after']}")
    print(f"  New strategies:  {len(s2_6['new_strats'])}")
    if s2_6['new_strats']:
        for s in s2_6['new_strats']:
            print(f"    + {s}")
    print(f"\n  EDE Report:\n{s2_6['report']}")

    print("\n--- STAGE 6: MetaModel ---")
    print(f"  ML dataset exists: {s6_meta['ml_dataset_exists']}")
    print(f"  ML records:        {s6_meta['ml_records']}")
    print(f"  Model trained:     {s6_meta['model_trained']}")
    if s6_meta.get("reason_not_trained"):
        print(f"  Reason:            {s6_meta['reason_not_trained']}")

    print("\n--- STAGE 7: Knowledge Store Final State ---")
    print(f"  Feature DB:      {s7['feat_total']} rows "
          f"({s7['feat_labeled']} labeled, {s7['feat_re001']} from RE001)")
    print(f"  Edges:           {s7['edges_total']} total  "
          f"ACTIVE={s7['edges_active']}  CANDIDATE={s7['edges_candidate']}  "
          f"DECAYING={s7['edges_decaying']}  DEPRECATED={s7['edges_deprecated']}")
    print(f"  Strategies:      {s7['strats_total']}")
    print(f"  ML records:      {s7['ml_records']}")

    print()
    print(f"  Pipeline elapsed: {elapsed:.1f}s")
    print("=" * 70)

    # Save results for report generation
    results = {
        "baseline": baseline,
        "final":    final,
        "stage1":   s1,
        "stage2_6": s2_6,
        "stage6_meta": s6_meta,
        "stage7":   s7,
        "elapsed_s": elapsed,
    }
    with open("data/re001a_results.json", "w") as f:
        json.dump(results, f, indent=2)
    log.info("[RE001A] Results saved to data/re001a_results.json")


if __name__ == "__main__":
    main()

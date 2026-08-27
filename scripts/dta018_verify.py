"""
DTA-018 VPS Verification Script v2
Run inside container: python3 /tmp/dta018_verify.py
"""
import sys, json, pathlib, datetime, collections

ROOT = pathlib.Path("/app")
DATA = ROOT / "data"
KLP  = DATA / "klp"

results = {}
defects = []

# ── PART 1: Bootstrap file presence and record count ─────────────────────────
boot_files = sorted(KLP.glob("BOOTSTRAP_*.jsonl"))
if not boot_files:
    defects.append("CRITICAL: No BOOTSTRAP_*.jsonl files in data/klp/")
    results["bootstrap"] = {"status": "FAIL", "files": 0}
else:
    total_recs = 0
    symbols = set()
    directions = collections.Counter()
    outcomes = collections.Counter()
    no_lookahead_count = 0
    for f in boot_files:
        with f.open() as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    total_recs += 1
                    symbols.add(rec.get("symbol", ""))
                    directions[rec.get("direction", "?")] += 1
                    outcomes[rec.get("first_event", "?")] += 1
                    if rec.get("no_lookahead"):
                        no_lookahead_count += 1
                except:
                    pass
    results["bootstrap"] = {
        "status": "PASS",
        "files": len(boot_files),
        "total_records": total_recs,
        "unique_symbols": len(symbols),
        "directions": dict(directions),
        "outcomes": dict(outcomes),
        "no_lookahead_flag_count": no_lookahead_count,
        "no_lookahead_pct": f"{100*no_lookahead_count/max(total_recs,1):.1f}%",
        "sample_symbols": sorted(symbols)[:10],
    }
    if no_lookahead_count < total_recs * 0.99:
        defects.append(f"MEDIUM: {total_recs - no_lookahead_count} records missing no_lookahead flag")

# ── PART 2: HBE loads bootstrap correctly ────────────────────────────────────
try:
    sys.path.insert(0, str(ROOT))
    from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
    hbe = HistoricalBehaviourEngine(data_dir=KLP)
    n = hbe.load_outcomes()
    tat_profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    sbin_profile = hbe.get_behaviour_profile("SBIN", "BUY")
    results["hbe"] = {
        "status": "PASS",
        "n_loaded": n,
        "tatasteel_ess":   round(tat_profile.metrics.effective_sample_size, 3),
        "tatasteel_tier":  tat_profile.metrics.evidence_tier,
        "tatasteel_level": tat_profile.metrics.evidence_level,
        "sbin_ess":        round(sbin_profile.metrics.effective_sample_size, 3),
        "sbin_tier":       sbin_profile.metrics.evidence_tier,
        "broker_calls":    hbe.broker_calls,
        "orders":          hbe.orders,
    }
    print(f"HBE: n={n} TATASTEEL_ESS={tat_profile.metrics.effective_sample_size:.3f} tier={tat_profile.metrics.evidence_tier}")
    if n < 1000:
        defects.append(f"HIGH: HBE only loaded {n} records (expected ~1170)")
    if hbe.broker_calls != 0:
        defects.append(f"CRITICAL: HBE made {hbe.broker_calls} broker calls")
except Exception as e:
    import traceback
    defects.append(f"CRITICAL: HBE load failed: {e}")
    results["hbe"] = {"status": "FAIL", "error": str(e), "tb": traceback.format_exc()[-400:]}

# ── PART 3: KDA decision semantics test ──────────────────────────────────────
try:
    from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
    kda = KnowledgeDecisionAuthority()
    # Build a fake obs matching ESS=9.870 (DEVELOPING)
    hbe2 = HistoricalBehaviourEngine(data_dir=KLP)
    hbe2.load_outcomes()
    tat_prof = hbe2.get_behaviour_profile("TATASTEEL", "BUY")
    obs = {
        "symbol": "TATASTEEL",
        "direction": "BUY",
        "entry_price": 165.0,
        "stop_loss":   158.0,
        "target_price":176.0,
        "confidence_score": 7.0,
        "trading_date": datetime.date.today().isoformat(),
    }
    result = kda.evaluate(obs, behaviour=tat_prof.metrics)
    results["kda"] = {
        "status": "PASS",
        "tatasteel_decision":  result.decision,
        "tatasteel_ess":       round(tat_prof.metrics.effective_sample_size, 3),
        "tatasteel_tier":      tat_prof.metrics.evidence_tier,
        "evidence_confidence": round(getattr(result, "evidence_confidence", 0.0) or 0.0, 3),
    }
    valid_decisions = ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL", "KNOWLEDGE_HOLD", "KNOWLEDGE_WAIT")
    if result.decision not in valid_decisions:
        defects.append(f"CRITICAL: Unknown KDA decision {result.decision} for TATASTEEL")
    print(f"KDA TATASTEEL: {result.decision} (ESS={tat_prof.metrics.effective_sample_size:.3f} tier={tat_prof.metrics.evidence_tier})")
except Exception as e:
    import traceback
    defects.append(f"HIGH: KDA evaluation failed: {e}")
    results["kda"] = {"status": "FAIL", "error": str(e), "tb": traceback.format_exc()[-400:]}

# ── PART 4: EOD guard ────────────────────────────────────────────────────────
eod_file = DATA / "eod_status.json"
if eod_file.exists():
    try:
        eod_data = json.loads(eod_file.read_text())
        results["eod_guard"] = {"status": "PASS", "data": eod_data}
    except Exception as e:
        results["eod_guard"] = {"status": "WARN", "error": str(e)}
else:
    results["eod_guard"] = {"status": "INFO", "note": "eod_status.json not present — EOD not yet run today"}

# ── PART 5: RiskGuardian state ────────────────────────────────────────────────
rg_state_file = DATA / "risk_guardian_state.json"
if rg_state_file.exists():
    try:
        rg_data = json.loads(rg_state_file.read_text())
        results["risk_guardian"] = {"status": "PASS", "data": rg_data}
        if rg_data.get("trading_halted"):
            defects.append(f"WARN: RiskGuardian is currently HALTED: {rg_data.get('halt_reason')}")
    except Exception as e:
        results["risk_guardian"] = {"status": "WARN", "error": str(e)}
else:
    results["risk_guardian"] = {"status": "INFO", "note": "risk_guardian_state.json not present — not yet initialized"}

# ── PART 6: LOL bridge state ──────────────────────────────────────────────────
lol_bridge_state = DATA / "lol_bridge_state.json"
if lol_bridge_state.exists():
    try:
        lol_data = json.loads(lol_bridge_state.read_text())
        results["lol_bridge"] = {"status": "PASS", "data": lol_data}
    except Exception as e:
        results["lol_bridge"] = {"status": "WARN", "error": str(e)}
else:
    results["lol_bridge"] = {"status": "INFO", "note": "lol_bridge_state.json not present — bridge not yet run"}

# ── PART 7: KFE source inventory ─────────────────────────────────────────────
try:
    from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import build_source_inventory
    inv = build_source_inventory(DATA)
    results["kfe_inventory"] = {
        "status": "PASS",
        "sources": [{"source": s.source, "availability": s.availability, "count": s.record_count} for s in inv],
    }
except Exception as e:
    results["kfe_inventory"] = {"status": "WARN", "error": str(e)}

# ── PART 8: KDA pipeline end-to-end ──────────────────────────────────────────
try:
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    kdp = KnowledgeDecisionPipeline()
    obs = {
        "symbol": "TATASTEEL",
        "direction": "BUY",
        "entry_price": 165.0,
        "stop_loss":   158.0,
        "target_price":176.0,
        "confidence_score": 7.0,
        "opportunity_id": "test-opp-001",
        "trading_date": datetime.date.today().isoformat(),
    }
    market_ctx = {"regime": "BULLISH", "vix": 15.0, "pcr": 0.8, "breadth": 0.6}
    shadow = kdp.run_knowledge_shadow(obs, market_ctx)
    bc = shadow.get("broker_calls", 0)
    results["kdp_pipeline"] = {
        "status": "PASS",
        "decision":       shadow.get("kda_decision"),
        "evidence_state": shadow.get("evidence_state"),
        "ess":            shadow.get("effective_sample_size"),
        "broker_calls":   bc,
    }
    if bc != 0:
        defects.append(f"CRITICAL: KDP made broker calls={bc}")
    print(f"KDP shadow: {shadow.get('kda_decision')} ESS={shadow.get('effective_sample_size')} broker_calls={bc}")
except Exception as e:
    import traceback
    defects.append(f"HIGH: KDP pipeline failed: {e}")
    results["kdp_pipeline"] = {"status": "FAIL", "error": str(e), "tb": traceback.format_exc()[-600:]}

# ── PART 9: Bootstrap temporal integrity ─────────────────────────────────────
# Check no outcome bar crosses the signal date (anti-lookahead)
if boot_files:
    lookahead_violations = 0
    same_day_outcomes = 0
    for f in boot_files:
        with f.open() as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    td = rec.get("trading_date", "")
                    fed = rec.get("first_event_day", "")
                    if fed and td and fed <= td:
                        same_day_outcomes += 1
                except:
                    pass
    results["temporal_integrity"] = {
        "status": "PASS" if same_day_outcomes == 0 else "FAIL",
        "same_day_outcomes": same_day_outcomes,  # should be 0
    }
    if same_day_outcomes > 0:
        defects.append(f"CRITICAL: {same_day_outcomes} bootstrap records have first_event_day <= trading_date (lookahead violation!)")

# ── PART 10: Execution authority check ───────────────────────────────────────
kdp_res = results.get("kdp_pipeline", {})
if kdp_res.get("status") == "PASS" and kdp_res.get("broker_calls", 999) == 0:
    results["execution_authority"] = {"status": "PASS", "note": "KDA pipeline does not place orders (broker_calls=0)"}
elif kdp_res.get("status") != "PASS":
    results["execution_authority"] = {"status": "INFO", "note": "KDP pipeline failed — cannot check broker_calls independently"}
else:
    defects.append("CRITICAL: KDA pipeline made broker calls — execution authority violation")
    results["execution_authority"] = {"status": "FAIL"}

# ── FINAL REPORT ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("DTA-018 VPS VERIFICATION REPORT")
print("="*70)
for k, v in results.items():
    status = v.get("status", "?")
    marker = "✅" if status == "PASS" else ("⚠️" if status in ("WARN","INFO") else "❌")
    print(f"{marker} {k}: {status}")
    if status not in ("PASS",):
        print(f"   {v}")

print("\n── DEFECTS ─────────────────────────────────────────────────────────")
if defects:
    for d in defects:
        print(f"  ❌ {d}")
else:
    print("  ✅ NO DEFECTS FOUND")

print("\n── SUMMARY ─────────────────────────────────────────────────────────")
print(json.dumps(results, indent=2, default=str))
print("="*70)

import json, pathlib, datetime

raw = pathlib.Path("/app/data/daily_candidates.json").read_text()
d = json.loads(raw)

# Top-level metadata
print("=== STORE METADATA ===")
print("prepared_at:               ", d.get("prepared_at"))
print("premarket_refreshed_at:    ", d.get("premarket_refreshed_at"))
print("premarket_refresh_complete:", d.get("premarket_refresh_complete"))
ctx = d.get("context", {})
print("regime:                    ", ctx.get("regime"))
print("scanner_feed_state:        ", ctx.get("scanner_feed_state"))

ss = d.get("scanner_stats", {})
print()
print("=== SCANNER STATS ===")
print("symbols_attempted:  ", ss.get("symbols_attempted"))
print("symbols_successful: ", ss.get("symbols_successful"))
print("symbols_failed:     ", ss.get("symbols_failed"))
print("coverage_pct:       ", ss.get("coverage_pct"))
print("scan_duration_min:  ", ss.get("scan_duration_min"))
print("candidates_written: ", ss.get("candidates_written", ss.get("candidates_found")))
print("sector_cap_removed: ", ss.get("sector_cap_removed"))
print("score_floor_removed:", ss.get("score_floor_removed"))

cands = d.get("candidates", [])
now_utc = datetime.datetime.now(datetime.timezone.utc)

items_s = sorted(cands, key=lambda x: -(float(x.get("score") or x.get("composite_score") or 0)))

print()
print("=== TOP 20 CANDIDATES BY SCORE ===")
print(f"{'#':<3} {'symbol':<18} {'score':<7} {'lifecycle':<12} {'premarket_refined':<18} {'prepared_at':<22} {'valid_until':<22}")
print("-" * 120)

expired_count = 0
fresh_count = 0
ages = []

for i, c in enumerate(items_s, 1):
    sym = c.get("symbol", "?")
    score = float(c.get("score") or c.get("composite_score") or 0)
    lc = c.get("lifecycle_state", "?")
    rs = str(c.get("refinement_status", c.get("premarket_refined", "?")))
    prep = str(c.get("prepared_at", c.get("scanned_at", "")) or "")[:19]
    valid = str(c.get("valid_until_utc", "") or "")[:19]

    age_str = ""
    try:
        prep_dt = datetime.datetime.fromisoformat(prep.replace("Z", "+00:00"))
        age_min = (now_utc - prep_dt).total_seconds() / 60
        age_str = f"{age_min:.0f}m"
        ages.append(age_min)
    except Exception:
        pass

    if i <= 20:
        print(f"{i:<3} {sym:<18} {score:<7.3f} {lc:<12} {rs:<18} {prep:<22} {valid:<22}")

    if lc == "EXPIRED":
        expired_count += 1
    elif lc in ("FRESH", "ACTIVE", "UNKNOWN"):
        fresh_count += 1

print()
print(f"=== FRESHNESS SUMMARY ===")
print(f"total={len(items_s)}  fresh/active/unknown={fresh_count}  expired={expired_count}")
if ages:
    print(f"oldest={max(ages):.0f}m  avg={sum(ages)/len(ages):.0f}m  newest={min(ages):.0f}m")


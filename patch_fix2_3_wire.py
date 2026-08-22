"""
Wire Fix 2: Call validate_and_refresh_sr_levels() from _premarket_init().
Also wire Fix 3: Check daily_candidates.json freshness in _premarket_init().
"""

ORCH = "/app/orchestrator/master_orchestrator.py"

with open(ORCH, "r") as f:
    src = f.read()

# ── Guard ─────────────────────────────────────────────────────────────────
if "validate_and_refresh_sr_levels" in src:
    print("Fix 2 wire already applied — skipping.")
else:
    # Find the end of the GlobalDataAI refresh block in _premarket_init
    ANCHOR_2 = (
        "        # Check data feed health\n"
        "        try:\n"
        "            from data_feeds import get_feed_manager\n"
        "            status = get_feed_manager().get_status()\n"
        "            log.info(\"  📡 Feed status: %s\", status)\n"
        "        except Exception:\n"
        "            pass"
    )
    INSERT_2 = (
        "        # ── Fix 2: S/R level auto-validation ─────────────────────────\n"
        "        # Detects and repairs any resistance<LTP or support>LTP entries\n"
        "        # using ATR(14)-anchored levels fetched from yfinance.\n"
        "        try:\n"
        "            from opportunity_engine.equity_scanner_ai import validate_and_refresh_sr_levels\n"
        "            _sr_result = validate_and_refresh_sr_levels()\n"
        "            if _sr_result[\"repaired\"] > 0:\n"
        "                log.warning(\n"
        "                    \"  ⚠️  S/R levels repaired: %d/%d symbols had broken levels — rebuilt with ATR(14).\",\n"
        "                    _sr_result[\"repaired\"], _sr_result[\"total\"],\n"
        "                )\n"
        "                try:\n"
        "                    from notifications import get_notifier\n"
        "                    get_notifier().market_alert(\n"
        "                        \"🔧 S/R Levels Auto-Repaired\",\n"
        "                        f\"{_sr_result['repaired']} symbol(s) had stale resistance/support \"\n"
        "                        f\"levels.\\nRepaired: {_sr_result['broken_symbols']}\\n\"\n"
        "                        f\"ATR-anchored levels applied — levels are now valid.\",\n"
        "                    )\n"
        "                except Exception:\n"
        "                    pass\n"
        "            else:\n"
        "                log.info(\"  ✅ S/R levels valid — no repair needed.\")\n"
        "        except Exception as _sr_exc:\n"
        "            log.warning(\"  ⚠️  S/R level validation failed: %s\", _sr_exc)\n"
        "\n"
    )

    if ANCHOR_2 not in src:
        print("ERROR: Fix 2 anchor not found — check pre-market init structure")
    else:
        src = src.replace(ANCHOR_2, INSERT_2 + ANCHOR_2, 1)
        print("Fix 2 wire: S/R validator call inserted in _premarket_init()")

# ── Fix 3: Candidate freshness check ─────────────────────────────────────
if "_candidates_freshness_check" in src or "daily_candidates_fresh" in src:
    print("Fix 3 wire already applied — skipping.")
else:
    # Insert after the S/R block we just added, before the data feed check
    # Use the Telegram notification block at end of _premarket_init as anchor
    ANCHOR_3 = (
        "        log.info(\"  Pre-market init complete. Waiting for 09:05 deep scan.\")"
    )
    INSERT_3 = (
        "        # ── Fix 3: Prepared universe freshness check ─────────────────\n"
        "        # If daily_candidates.json is missing or from a previous day,\n"
        "        # trigger Phase D scanner now so first cycle has fresh candidates.\n"
        "        try:\n"
        "            import json as _json\n"
        "            from pathlib import Path as _Path\n"
        "            from datetime import date as _date\n"
        "            _cand_path = _Path(\"data/daily_candidates.json\")\n"
        "            _needs_scan = False\n"
        "            if not _cand_path.exists():\n"
        "                log.warning(\"  ⚠️  daily_candidates.json missing — triggering Phase D scan.\")\n"
        "                _needs_scan = True\n"
        "            else:\n"
        "                _mtime = _date.fromtimestamp(_cand_path.stat().st_mtime)\n"
        "                if _mtime < _date.today():\n"
        "                    log.warning(\n"
        "                        \"  ⚠️  daily_candidates.json is stale (last updated %s) — triggering Phase D scan.\",\n"
        "                        _mtime,\n"
        "                    )\n"
        "                    _needs_scan = True\n"
        "                else:\n"
        "                    _cand_data = _json.loads(_cand_path.read_text())\n"
        "                    _n_cands   = len(_cand_data.get(\"candidates\", []))\n"
        "                    log.info(\"  ✅ Prepared universe fresh: %d candidates.\", _n_cands)\n"
        "            if _needs_scan:\n"
        "                import threading as _threading\n"
        "                _t = _threading.Thread(\n"
        "                    target=self._run_post_market_scan,\n"
        "                    daemon=True, name=\"PremarketPhaseD\",\n"
        "                )\n"
        "                _t.start()\n"
        "                log.info(\"  Phase D scanner triggered in background thread.\")\n"
        "        except Exception as _cand_exc:\n"
        "            log.warning(\"  ⚠️  Candidate freshness check failed: %s\", _cand_exc)\n"
        "\n"
    )

    if ANCHOR_3 not in src:
        print("ERROR: Fix 3 anchor not found — check pre-market init structure")
    else:
        src = src.replace(ANCHOR_3, INSERT_3 + ANCHOR_3, 1)
        print("Fix 3 wire: candidate freshness check inserted in _premarket_init()")

# Write back
with open(ORCH, "w") as f:
    f.write(src)

# Syntax check
import py_compile, tempfile, shutil, os
tmp = tempfile.mktemp(suffix=".py")
shutil.copy2(ORCH, tmp)
try:
    py_compile.compile(tmp, doraise=True)
    print("Syntax check: PASSED")
except py_compile.PyCompileError as e:
    print(f"Syntax check: FAILED — {e}")
finally:
    os.unlink(tmp)

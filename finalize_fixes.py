"""Add refresh_sr_cache() call in _premarket_init and sync files to host."""
import sys, shutil

ORCH = "/app/orchestrator/master_orchestrator.py"

with open(ORCH, "r") as f:
    src = f.read()

if "refresh_sr_cache" in src:
    print("refresh_sr_cache already in orchestrator")
else:
    OLD = (
        "        log.info(\"  Pre-market init complete. Waiting for 09:05 deep scan.\")\n"
    )
    NEW = (
        "        # Refresh dynamic S/R levels for all watchlist symbols (daily)\n"
        "        try:\n"
        "            from opportunity_engine.equity_scanner_ai import refresh_sr_cache\n"
        "            refresh_sr_cache()\n"
        "        except Exception as _src_exc:\n"
        "            log.warning(\"  S/R cache refresh failed: %s\", _src_exc)\n"
        "\n"
        "        log.info(\"  Pre-market init complete. Waiting for 09:05 deep scan.\")\n"
    )
    if OLD not in src:
        print("ERROR: anchor not found in _premarket_init")
        sys.exit(1)
    src = src.replace(OLD, NEW, 1)
    with open(ORCH, "w") as f:
        f.write(src)
    print("OK: refresh_sr_cache() added to _premarket_init")

# Verify syntax
import py_compile
try:
    py_compile.compile(ORCH, doraise=True)
    print("Orchestrator syntax: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
    sys.exit(1)

SCANNER = "/app/opportunity_engine/equity_scanner_ai.py"
try:
    py_compile.compile(SCANNER, doraise=True)
    print("Scanner syntax: OK")
except py_compile.PyCompileError as e:
    print(f"SCANNER SYNTAX ERROR: {e}")
    sys.exit(1)

print("\nSyncing to host...")
shutil.copy2(ORCH, "/root/ai-trading-brain/orchestrator/master_orchestrator.py")
shutil.copy2(SCANNER, "/root/ai-trading-brain/opportunity_engine/equity_scanner_ai.py")
print("Synced both files to host.")

import glob, os

# Check registry files
registry_files = glob.glob("/app/data/closed_orders_*.txt")
print("Registry files:", registry_files)

orphan_ids = {"SIM_NIFTY_SELL_43_20260507", "SIM_RELIANCE_BUY_1742", "SIM_RELIANCE_BUY_1740"}

found_in_registry = set()
for f in registry_files:
    for line in open(f):
        oid = line.strip()
        if oid in orphan_ids:
            found_in_registry.add(oid)
            print(f"FOUND in registry ({f}): {oid}")

not_in_registry = orphan_ids - found_in_registry
print("\nOrphans NOT in registry (never marked closed):", not_in_registry)

# Also print all registry entries
print("\nAll registry entries:")
for f in registry_files:
    lines = [l.strip() for l in open(f) if l.strip()]
    print(f"  {os.path.basename(f)}: {len(lines)} entries")
    for l in lines:
        print(f"    {l}")

#!/usr/bin/env python3
"""
Remove all strategy_name pre-assignments from OpportunityEngine files.
Allows StrategyLab to assign strategies based on active set.
"""
import re
import os

files_to_patch = [
    "opportunity_engine/equity_scanner_ai.py",
    "opportunity_engine/options_opportunity_ai.py",
    "opportunity_engine/arbitrage_ai.py",
]

def remove_strategy_names(content):
    """Remove lines containing strategy_name assignments."""
    # Pattern: any line with strategy_name = "..."
    content = re.sub(
        r'\s*strategy_name\s*=\s*["\'][\w_]+["\']\s*,?\n',
        '',
        content
    )
    return content

for filepath in files_to_patch:
    if not os.path.exists(filepath):
        print(f"❌ {filepath} not found")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    patched = remove_strategy_names(original)
    
    if patched != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(patched)
        print(f"✅ {filepath} patched — strategy_name assignments removed")
    else:
        print(f"⚠️  {filepath} already clean")

print("\n✅ All OpportunityEngine files patched. Ready to test.")

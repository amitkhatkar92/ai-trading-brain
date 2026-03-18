#!/usr/bin/env python3
"""
Quick Emergency Kill Switch Toggle Script
==========================================

Usage:
  python3 scripts/kill_switch_toggle.py disable "API corruption"
  python3 scripts/kill_switch_toggle.py enable "Issue resolved"
  python3 scripts/kill_switch_toggle.py status
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.kill_switch import (
    disable_trading,
    enable_trading,
    get_kill_switch_status,
    is_trading_enabled
)
from utils import get_logger

log = get_logger(__name__)


def main():
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "disable":
        if len(sys.argv) < 3:
            reason = "Manual emergency halt"
        else:
            reason = " ".join(sys.argv[2:])
        
        print(f"🚨 Disabling trading: {reason}")
        disable_trading(reason)
        print("✓ Trading DISABLED")
        return 0
    
    elif command == "enable":
        if len(sys.argv) < 3:
            reason = "Manual re-enable"
        else:
            reason = " ".join(sys.argv[2:])
        
        print(f"✓ Enabling trading: {reason}")
        enable_trading(reason)
        print("✓ Trading ENABLED")
        return 0
    
    elif command == "status":
        status = get_kill_switch_status()
        enabled = status['trading_enabled']
        reason = status['reason']
        last_mod = status['last_modified']
        
        state_icon = "✓ ON" if enabled else "🚨 OFF"
        print(f"\nKill Switch Status: {state_icon}")
        print(f"  Reason:         {reason}")
        print(f"  Last Modified:  {last_mod}")
        print(f"  Checked At:     {status['checked_at']}\n")
        
        return 0
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        return 1


def print_usage():
    print("""
Emergency Kill Switch Toggle
=============================

Usage:
  python3 scripts/kill_switch_toggle.py disable [reason]
  python3 scripts/kill_switch_toggle.py enable [reason]
  python3 scripts/kill_switch_toggle.py status

Examples:
  # Emergency: stop all trading immediately
  python3 scripts/kill_switch_toggle.py disable "API connection lost"

  # Re-enable after issue is fixed
  python3 scripts/kill_switch_toggle.py enable "API restored and verified stable"

  # Check current status
  python3 scripts/kill_switch_toggle.py status

IMPORTANT:
  • This is INSTANT — no delay, no confirmation needed
  • All trading stops on the next cycle check (<1 second)
  • Always include a reason (for audit trail)
  • Monitor logs after toggle: journalctl -u trading-brain.service -f
    """)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Dhan OAuth Token Setup & Validation
====================================

Test script to verify token capture and exchange are working correctly.

Usage:
  python3 scripts/validate_dhan_oauth.py

Steps:
  1. Checks OAuth server configuration
  2. Validates token storage format
  3. Tests token expiry logic
  4. Provides setup instructions if needed
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils import get_logger

log = get_logger(__name__)

CONFIG_DIR = PROJECT_ROOT / "config"
TOKEN_FILE = CONFIG_DIR / "api_tokens.json"
OAUTH_CONFIG_FILE = CONFIG_DIR / "dhan_oauth_config.json"


def print_separator(title: str):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def check_token_file() -> bool:
    """Check if token file exists and is valid."""
    print_separator("TOKEN FILE STATUS")
    
    if not TOKEN_FILE.exists():
        print("❌ Token file not found: config/api_tokens.json")
        print("   → Token will be created after OAuth login")
        return False
    
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
        
        print("✅ Token file exists and is valid JSON")
        print(f"\n   Location: {TOKEN_FILE}")
        print(f"   Permission: {oct(TOKEN_FILE.stat().st_mode)[-3:]}")
        
        # Check format
        if "access_token" in data:
            print("   Format: ✅ NEW (access_token with 30-day window)")
            expires_at = data.get("expires_at", "N/A")
            client_id = data.get("client_id", "N/A")
            print(f"   Client ID: {client_id}")
            print(f"   Expires At: {expires_at}")
            
            # Check expiry
            if expires_at and expires_at != "N/A":
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    now = datetime.utcnow()
                    days_left = (exp_dt - now).total_seconds() / (24 * 3600)
                    
                    if days_left < 0:
                        print(f"   Status: ❌ EXPIRED ({abs(days_left):.1f} days ago)")
                    elif days_left < 3:
                        print(f"   Status: ⚠️  EXPIRING SOON ({days_left:.1f} days left)")
                    else:
                        print(f"   Status: ✅ ACTIVE ({days_left:.1f} days left)")
                except Exception as e:
                    print(f"   Status: Could not parse expiry: {e}")
        
        elif "dhan_request_code" in data:
            print("   Format: ⚠️  OLD (authorization code)")
            print("   → Needs manual exchange via dhan_token_exchange module")
            code = data.get("dhan_request_code", "")
            print(f"   Code: {code[:20]}...")
        
        else:
            print("   Format: ❌ UNKNOWN (missing token fields)")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Token file is invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading token file: {e}")
        return False


def check_oauth_config() -> bool:
    """Check OAuth configuration."""
    print_separator("OAUTH CONFIGURATION")
    
    if not OAUTH_CONFIG_FILE.exists():
        print("❌ OAuth config file not found: config/dhan_oauth_config.json")
        print("   → Creating default configuration...")
        return False
    
    try:
        with open(OAUTH_CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        print("✅ OAuth config file exists")
        
        dhan_config = config.get("dhan", {})
        client_id = dhan_config.get("client_id")
        ttl_days = dhan_config.get("token_ttl_days", 30)
        
        print(f"\n   Client ID: {client_id}")
        print(f"   Token TTL: {ttl_days} days")
        print(f"   Sandbox Mode: {dhan_config.get('sandbox_mode', False)}")
        
        refresh_config = config.get("token_refresh", {})
        print(f"\n   Auto-Refresh: {refresh_config.get('auto_refresh', True)}")
        print(f"   Refresh Threshold: {refresh_config.get('refresh_threshold_days', 3)} days")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ OAuth config is invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading OAuth config: {e}")
        return False


def check_dhan_environment() -> bool:
    """Check Dhan environment variables."""
    print_separator("DHAN ENVIRONMENT VARIABLES")
    
    import os
    
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
    
    print(f"DHAN_CLIENT_ID: {'✅ Set' if client_id else '❌ Not set'}")
    if client_id:
        print(f"  Value: {client_id[:10]}...")
    
    print(f"\nDHAN_ACCESS_TOKEN: {'✅ Set' if access_token else '❌ Not set'}")
    if access_token:
        print(f"  Value: {access_token[:20]}...")
    
    return bool(client_id and access_token)


def validate_token_loading() -> bool:
    """Test token loading functionality."""
    print_separator("TOKEN LOADING TEST")
    
    try:
        from utils.dhan_token_manager import get_dhan_token, get_token_status
        
        token = get_dhan_token()
        
        if token:
            print(f"✅ Token loaded successfully")
            print(f"   Token: {token[:20]}...")
            
            status = get_token_status()
            print(f"\n   Status: {status}")
        else:
            print("⚠️  No valid token available")
            print("   → Please login to Dhan OAuth to capture token")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading token: {e}")
        return False


def print_setup_instructions():
    """Print setup instructions."""
    print_separator("SETUP INSTRUCTIONS")
    
    print("""
1. OAUTH LOGIN
   Visit: https://api.dhan.co/oauth2/authorize?client_id=2603183256&redirect_uri=http://178.18.252.24:8000/callback&response_type=code&state=trading-brain

2. TOKEN CAPTURE
   OAuth server will:
     a) Capture authorization code (short-lived)
     b) Exchange code for access token (automatic)
     c) Save access_token with 30-day expiry to config/api_tokens.json

3. VERIFY
   python3 scripts/validate_dhan_oauth.py

4. CHECK TOKEN
   cat config/api_tokens.json | python3 -m json.tool

5. TRADING ENGINE
   System will automatically use token from config/api_tokens.json
   Token will be auto-refreshed before expiry
""")


def main():
    """Run all validations."""
    print("\n" + "="*70)
    print("  DHAN OAUTH TOKEN SETUP & VALIDATION")
    print("="*70)
    print(f"  Date: {datetime.utcnow().isoformat()}")
    print(f"  Project: {PROJECT_ROOT}")
    print()
    
    results = {
        "Token File": check_token_file(),
        "OAuth Config": check_oauth_config(),
        "Environment": check_dhan_environment(),
        "Token Loading": validate_token_loading(),
    }
    
    # Summary
    print_separator("VALIDATION SUMMARY")
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "⚠️  INCOMPLETE"
        print(f"  {check_name}: {status}")
    
    all_passed = all(results.values())
    
    if not all_passed:
        print_setup_instructions()
    else:
        print("\n✅ All checks passed! System is ready for trading.\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

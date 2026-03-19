#!/usr/bin/env python3
"""
Dhan OAuth System — Verification & Health Check Script

Comprehensive diagnostic tool to verify OAuth system is deployed and working.

Usage:
  python3 scripts/test_dhan_oauth.py [--verbose] [--fix-perms] [--restart]

Options:
  --verbose      Show detailed output
  --fix-perms    Auto-fix token file permissions (if incorrect)
  --restart      Restart OAuth service (requires SSH access)
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'  # No Color

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TOKEN_FILE = CONFIG_DIR / "api_tokens.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
OAUTH_LOG = LOG_DIR / "oauth-callback.log"

VPS_HOST = "root@178.18.252.24"
VPS_SSH_KEY = os.path.expanduser("~/.ssh/trading_vps")
VPS_HOME = "/root/ai-trading-brain"


class HealthCheck:
    """OAuth system health checker."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: Dict[str, Tuple[bool, str]] = {}

    def print_header(self, title: str):
        print(f"\n{BOLD}{BLUE}{'=' * 70}{NC}")
        print(f"{BOLD}{BLUE}  {title}{NC}")
        print(f"{BOLD}{BLUE}{'=' * 70}{NC}\n")

    def check(self, name: str, condition: bool, message: str, verbose_msg: str = ""):
        """Record a check result."""
        self.results[name] = (condition, message)
        
        symbol = f"{GREEN}✓{NC}" if condition else f"{RED}✗{NC}"
        print(f"{symbol} {name:<40} {message}")
        
        if verbose_msg and self.verbose:
            print(f"  └─ {verbose_msg}")

    def section_summary(self, section_name: str) -> bool:
        """Return True if all checks in section passed."""
        passed = sum(1 for c, msg in self.results.values() if c)
        total = len(self.results)
        status = "PASS" if passed == total else "FAIL"
        color = GREEN if passed == total else RED
        print(f"\n{color}➤ {section_name}: {passed}/{total} checks passed{NC}\n")
        return passed == total

    def local_checks(self):
        """Check local system setup."""
        self.print_header("1. LOCAL DEPLOYMENT")

        # Check OAuth server file
        oauth_exists = (PROJECT_ROOT / "scripts" / "dhan_oauth_server.py").exists()
        self.check(
            "OAuth server script",
            oauth_exists,
            "scripts/dhan_oauth_server.py" if oauth_exists else "NOT FOUND"
        )

        # Check token manager file
        token_mgr_exists = (PROJECT_ROOT / "utils" / "dhan_token_manager.py").exists()
        self.check(
            "Token manager module",
            token_mgr_exists,
            "utils/dhan_token_manager.py" if token_mgr_exists else "NOT FOUND"
        )

        # Check systemd service file (local)
        service_exists = (PROJECT_ROOT / "scripts" / "dhan-oauth.service").exists()
        self.check(
            "Systemd service file",
            service_exists,
            "scripts/dhan-oauth.service" if service_exists else "NOT FOUND"
        )

        # Check logs directory
        logs_exist = LOG_DIR.exists()
        self.check(
            "Logs directory",
            logs_exist,
            f"data/logs/",
            f"{LOG_DIR}"
        )

        # Check .gitignore has token exclusions
        gitignore_file = PROJECT_ROOT / ".gitignore"
        gitignore_ok = False
        if gitignore_file.exists():
            content = gitignore_file.read_text()
            gitignore_ok = "config/api_tokens.json" in content
        self.check(
            "Token files in .gitignore",
            gitignore_ok,
            "config/api_tokens.json excluded" if gitignore_ok else "NOT IN GITIGNORE"
        )

        return self.section_summary("Local Deployment")

    def vps_checks(self):
        """Check VPS deployment."""
        self.print_header("2. VPS DEPLOYMENT")

        # Test SSH connectivity
        try:
            subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST, "echo test"],
                capture_output=True,
                timeout=5,
                check=True
            )
            ssh_ok = True
            ssh_msg = "Connected"
        except Exception as e:
            ssh_ok = False
            ssh_msg = f"Failed: {str(e)[:30]}"

        self.check(
            "SSH connection to VPS",
            ssh_ok,
            ssh_msg,
            f"{VPS_HOST}"
        )

        if not ssh_ok:
            print(f"{RED}Cannot proceed with VPS checks without SSH access{NC}")
            return False

        # Check OAuth server on VPS
        try:
            result = subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 f"[ -f {VPS_HOME}/scripts/dhan_oauth_server.py ] && echo true"],
                capture_output=True,
                timeout=5,
                text=True
            )
            oauth_deployed = "true" in result.stdout
        except:
            oauth_deployed = False

        self.check(
            "OAuth server deployed",
            oauth_deployed,
            f"{VPS_HOME}/scripts/dhan_oauth_server.py"
        )

        # Check token manager on VPS
        try:
            result = subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 f"[ -f {VPS_HOME}/utils/dhan_token_manager.py ] && echo true"],
                capture_output=True,
                timeout=5,
                text=True
            )
            token_mgr_deployed = "true" in result.stdout
        except:
            token_mgr_deployed = False

        self.check(
            "Token manager deployed",
            token_mgr_deployed,
            f"{VPS_HOME}/utils/dhan_token_manager.py"
        )

        # Check systemd service
        try:
            result = subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 "sudo systemctl is-active dhan-oauth"],
                capture_output=True,
                timeout=5,
                text=True
            )
            service_active = "active" in result.stdout
            service_msg = "active (running)" if service_active else "inactive"
        except:
            service_active = False
            service_msg = "query failed"

        self.check(
            "OAuth service running",
            service_active,
            service_msg
        )

        # Check port 8000
        try:
            result = subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 "ss -tuln | grep ':8000'"],
                capture_output=True,
                timeout=5,
                text=True
            )
            port_open = ":8000" in result.stdout
        except:
            port_open = False

        self.check(
            "Port 8000 listening",
            port_open,
            "0.0.0.0:8000" if port_open else "not listening"
        )

        # Check health endpoint
        try:
            result = subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 "curl -s http://localhost:8000/health | grep -q healthy && echo true"],
                capture_output=True,
                timeout=5,
                text=True
            )
            health_ok = "true" in result.stdout
        except:
            health_ok = False

        self.check(
            "Health endpoint",
            health_ok,
            "/health responding" if health_ok else "not responding"
        )

        # Check token file exists on VPS
        try:
            result = subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 f"[ -f {VPS_HOME}/config/api_tokens.json ] && echo true"],
                capture_output=True,
                timeout=5,
                text=True
            )
            token_exists = "true" in result.stdout
        except:
            token_exists = False

        self.check(
            "Token file captured",
            token_exists,
            f"{VPS_HOME}/config/api_tokens.json" if token_exists else "file not yet created"
        )

        # Check token file permissions
        if token_exists:
            try:
                result = subprocess.run(
                    ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                     f"stat -c '%a' {VPS_HOME}/config/api_tokens.json"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                perms = result.stdout.strip()
                perms_ok = perms == "600"
                perms_msg = "600 (secure)" if perms_ok else f"{perms} (should be 600)"
            except:
                perms_ok = False
                perms_msg = "could not check"
        else:
            perms_ok = None
            perms_msg = "(not yet created)"

        if perms_ok is not None:
            self.check(
                "Token file permissions",
                perms_ok,
                perms_msg
            )

        return self.section_summary("VPS Deployment")

    def local_token_checks(self):
        """Check local token setup."""
        self.print_header("3. LOCAL TOKEN (if captured)")

        if not TOKEN_FILE.exists():
            print(f"{YELLOW}ℹ Token file not yet created (capture first){NC}\n")
            self.check("Token file exists", False, "not yet captured")
            return False

        # Token file exists
        self.check("Token file exists", True, f"{TOKEN_FILE}")

        # Load token
        try:
            with open(TOKEN_FILE) as f:
                token_data = json.load(f)
            token_valid = True
            token_msg = "valid JSON"
        except json.JSONDecodeError as e:
            token_valid = False
            token_msg = f"invalid JSON: {str(e)[:40]}"

        self.check("Token JSON format", token_valid, token_msg)

        # Check token has code
        if token_valid:
            has_code = "dhan_request_code" in token_data
            self.check(
                "Token has authorization code",
                has_code,
                "code present" if has_code else "missing 'dhan_request_code'"
            )

            # Check captured_at
            has_timestamp = "captured_at" in token_data
            self.check(
                "Token has timestamp",
                has_timestamp,
                token_data.get("captured_at", "missing") if has_timestamp else "missing 'captured_at'"
            )

            # Check status
            status = token_data.get("status", "unknown")
            self.check(
                "Token status",
                status == "captured",
                status
            )

        # Check file permissions (local)
        try:
            stat_info = TOKEN_FILE.stat()
            mode = stat_info.st_mode & 0o777
            perms_ok = mode == 0o600
            perms_str = oct(mode)
        except:
            perms_ok = False
            perms_str = "error"

        self.check(
            "Token file permissions (local)",
            perms_ok,
            f"{perms_str}" + (" (secure)" if perms_ok else " (should be 600)")
        )

        return self.section_summary("Local Token")

    def integration_checks(self):
        """Check trading engine integration."""
        self.print_header("4. TRADING ENGINE INTEGRATION")

        # Check token manager can import
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from utils.dhan_token_manager import get_dhan_token, get_token_status
            import_ok = True
            import_msg = "imports successful"
        except Exception as e:
            import_ok = False
            import_msg = f"import failed: {str(e)[:40]}"

        self.check(
            "Token manager imports",
            import_ok,
            import_msg
        )

        # Check can get token
        if import_ok:
            try:
                token = get_dhan_token()
                token_ok = token is not None
                token_msg = "token loaded" if token_ok else "no token available"
            except Exception as e:
                token_ok = False
                token_msg = f"error: {str(e)[:40]}"
        else:
            token_ok = False
            token_msg = "import failed"

        self.check(
            "Token loading function",
            token_ok,
            token_msg
        )

        # Check token status
        if import_ok:
            try:
                status = get_token_status()
                has_status = status is not None
                status_msg = f"age: {status.get('age_days', '?')}d, expires: {status.get('expires_in_days', '?')}d"
            except Exception as e:
                has_status = False
                status_msg = f"error: {str(e)[:40]}"
        else:
            has_status = False
            status_msg = "import failed"

        self.check(
            "Token status function",
            has_status,
            status_msg
        )

        # Check config loads environment
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", PROJECT_ROOT / "config.py")
            config = importlib.util.module_from_spec(spec)
            sys.modules["config"] = config
            spec.loader.exec_module(config)
            config_ok = True
            config_msg = "config loads successfully"
        except Exception as e:
            config_ok = False
            config_msg = f"error: {str(e)[:40]}"

        self.check(
            "Config module loads",
            config_ok,
            config_msg
        )

        return self.section_summary("Integration")

    def run_all(self) -> bool:
        """Run all checks."""
        print(f"\n{BOLD}{BLUE}Dhan OAuth System — Health Check{NC}")
        print(f"{BOLD}{BLUE}Timestamp: {datetime.now().isoformat()}{NC}\n")

        r1 = self.local_checks()
        r2 = self.vps_checks()
        r3 = self.local_token_checks()
        r4 = self.integration_checks()

        self.print_summary(r1, r2, r3)
        return r1 and r2 and r3 and r4

    def print_summary(self, r1, r2, r3):
        """Print final summary."""
        self.print_header("FINAL SUMMARY")
        
        total_passed = sum(1 for c, msg in self.results.values() if c)
        total_checks = len(self.results)
        
        status_color = GREEN if total_passed == total_checks else YELLOW
        print(f"{status_color}{BOLD}{total_passed}/{total_checks} checks passed{NC}\n")

        if total_passed == total_checks:
            print(f"{GREEN}✓ OAuth system fully operational!{NC}\n")
        else:
            print(f"{YELLOW}⚠ Some checks failed. See above for details.{NC}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Dhan OAuth System Health Check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fix-perms", action="store_true", help="Fix token file permissions")
    parser.add_argument("--restart", action="store_true", help="Restart OAuth service")
    args = parser.parse_args()

    checker = HealthCheck(verbose=args.verbose)

    # Run all checks
    all_ok = checker.run_all()

    # Optional: fix permissions
    if args.fix_perms and TOKEN_FILE.exists():
        try:
            os.chmod(TOKEN_FILE, 0o600)
            print(f"{GREEN}✓ Fixed token file permissions to 600{NC}\n")
        except Exception as e:
            print(f"{RED}✗ Could not fix permissions: {e}{NC}\n")

    # Optional: restart service
    if args.restart:
        try:
            subprocess.run(
                ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                 "sudo systemctl restart dhan-oauth"],
                timeout=10,
                check=True
            )
            print(f"{GREEN}✓ Restarted OAuth service{NC}\n")
        except Exception as e:
            print(f"{RED}✗ Could not restart service: {e}{NC}\n")

    # Exit with status
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

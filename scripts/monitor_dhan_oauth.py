#!/usr/bin/env python3
"""
Dhan OAuth System — Real-time Monitor

Monitor OAuth server health, token file changes, and expiration warnings in real-time.

Usage:
  python3 scripts/monitor_dhan_oauth.py [--vps] [--follow-logs] [--check-interval 5]

Options:
  --vps              Connect to VPS and monitor remote service
  --follow-logs      Follow OAuth server logs in real-time
  --check-interval   Health check interval in seconds (default: 5)
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
DIM = '\033[2m'
NC = '\033[0m'  # No Color

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TOKEN_FILE = CONFIG_DIR / "api_tokens.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
OAUTH_LOG = LOG_DIR / "oauth-callback.log"

VPS_HOST = "root@178.18.252.24"
VPS_SSH_KEY = os.path.expanduser("~/.ssh/trading_vps")
VPS_HOME = "/root/ai-trading-brain"


class OAuthMonitor:
    """Monitor OAuth system health."""

    def __init__(self, check_interval: int = 5, vps: bool = False):
        self.check_interval = check_interval
        self.vps = vps
        self.last_token_mtime = 0
        self.last_log_size = 0

    def clear_screen(self):
        """Clear terminal."""
        os.system("clear" if os.name != "nt" else "cls")

    def print_header(self, title: str):
        """Print section header."""
        print(f"\n{BOLD}{BLUE}{'=' * 70}{NC}")
        print(f"{BOLD}{BLUE}  {title}{NC}")
        print(f"{BOLD}{BLUE}{'=' * 70}{NC}\n")

    def status_line(self, name: str, status: str, value: str = "", color: str = ""):
        """Print status line."""
        if not color:
            color = GREEN if status == "✓" else RED if status == "✗" else YELLOW

        status_fmt = f"{color}{BOLD}{status}{NC}"
        print(f"  {status_fmt}  {name:<30}  {value}")

    def check_oauth_service(self) -> Dict:
        """Check OAuth service status."""
        result = {
            "running": False,
            "pid": None,
            "memory": None,
            "uptime": None,
            "port_listening": False,
        }

        if self.vps:
            # Remote check
            try:
                # Check if service is active
                res = subprocess.run(
                    ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                     "sudo systemctl is-active dhan-oauth"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                result["running"] = "active" in res.stdout

                # Get PID and memory
                if result["running"]:
                    res = subprocess.run(
                        ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                         "sudo systemctl status dhan-oauth --no-pager | grep 'Main PID'"],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                    # Parse: Main PID: 71750 (python3)
                    if "PID" in res.stdout:
                        parts = res.stdout.split()
                        if len(parts) >= 3:
                            result["pid"] = parts[2]

                    # Get memory
                    res = subprocess.run(
                        ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                         "sudo systemctl status dhan-oauth --no-pager | grep Memory"],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                    if "Memory" in res.stdout:
                        # Parse: Memory: 12.3M
                        parts = res.stdout.split()
                        if len(parts) >= 2:
                            result["memory"] = parts[1]

                # Check port
                res = subprocess.run(
                    ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                     "ss -tuln | grep ':8000'"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                result["port_listening"] = ":8000" in res.stdout

            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                print(f"{RED}SSH connection failed: {e}{NC}")
                return result
        else:
            # Local check via systemctl
            try:
                res = subprocess.run(
                    ["systemctl", "is-active", "dhan-oauth"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                result["running"] = "active" in res.stdout

                if result["running"]:
                    # Get status details
                    res = subprocess.run(
                        ["systemctl", "status", "dhan-oauth", "--no-pager"],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                    for line in res.stdout.split("\n"):
                        if "Main PID" in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                result["pid"] = parts[2]
                        if "Memory" in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                result["memory"] = parts[1]

                    # Check port
                    res = subprocess.run(
                        ["ss", "-tuln"],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                    result["port_listening"] = ":8000" in res.stdout

            except Exception:
                pass

        return result

    def check_health_endpoint(self) -> Dict:
        """Check OAuth health endpoint."""
        result = {
            "responding": False,
            "status": None,
            "timestamp": None,
            "latency_ms": None,
        }

        if self.vps:
            cmd = f"curl -s -w '%{{time_total}}' -o /tmp/health.json http://localhost:8000/health && cat /tmp/health.json"
            try:
                res = subprocess.run(
                    ["ssh", "-i", VPS_SSH_KEY, VPS_HOST, cmd],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if res.returncode == 0:
                    output = res.stdout
                    # Parse JSON
                    try:
                        health_json = json.loads(output)
                        result["responding"] = True
                        result["status"] = health_json.get("status")
                        result["timestamp"] = health_json.get("timestamp")
                    except:
                        pass
            except:
                pass
        else:
            try:
                import time
                start = time.time()
                res = subprocess.run(
                    ["curl", "-s", "http://localhost:8000/health"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                elapsed = (time.time() - start) * 1000
                result["latency_ms"] = f"{int(elapsed)}ms"

                if res.returncode == 0:
                    health_json = json.loads(res.stdout)
                    result["responding"] = True
                    result["status"] = health_json.get("status")
                    result["timestamp"] = health_json.get("timestamp")
            except:
                pass

        return result

    def check_token_file(self) -> Dict:
        """Check token file status."""
        result = {
            "exists": False,
            "age_seconds": None,
            "size": None,
            "has_code": False,
            "status": None,
            "captured_at": None,
        }

        if self.vps:
            try:
                # Check if exists
                res = subprocess.run(
                    ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                     f"[ -f {VPS_HOME}/config/api_tokens.json ] && cat {VPS_HOME}/config/api_tokens.json"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if res.returncode == 0 and res.stdout:
                    result["exists"] = True
                    try:
                        token_data = json.loads(res.stdout)
                        result["has_code"] = "dhan_request_code" in token_data
                        result["status"] = token_data.get("status")
                        result["captured_at"] = token_data.get("captured_at")
                    except:
                        pass
            except:
                pass
        else:
            if TOKEN_FILE.exists():
                result["exists"] = True
                result["size"] = TOKEN_FILE.stat().st_size
                result["age_seconds"] = time.time() - TOKEN_FILE.stat().st_mtime

                try:
                    with open(TOKEN_FILE) as f:
                        token_data = json.load(f)
                    result["has_code"] = "dhan_request_code" in token_data
                    result["status"] = token_data.get("status")
                    result["captured_at"] = token_data.get("captured_at")
                except:
                    pass

        return result

    def display_dashboard(self):
        """Display monitoring dashboard."""
        self.clear_screen()

        print(f"{BOLD}{CYAN}Dhan OAuth System Monitor{NC}")
        print(f"{DIM}Running in {'VPS' if self.vps else 'Local'} mode | Refreshing every {self.check_interval}s{NC}")
        print(f"{DIM}Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NC}")

        # Service status
        self.print_header("1. OAuth SERVICE")
        service = self.check_oauth_service()

        self.status_line(
            "Service running",
            "✓" if service["running"] else "✗",
            "active" if service["running"] else "inactive"
        )
        if service["pid"]:
            self.status_line("Process PID", "ℹ", f"PID {service['pid']}")
        if service["memory"]:
            self.status_line("Memory usage", "ℹ", f"{service['memory']}")
        self.status_line(
            "Port 8000",
            "✓" if service["port_listening"] else "✗",
            "listening" if service["port_listening"] else "not listening"
        )

        # Health endpoint
        self.print_header("2. HEALTH ENDPOINT")
        health = self.check_health_endpoint()

        self.status_line(
            "Health responding",
            "✓" if health["responding"] else "✗",
            "responding" if health["responding"] else "not responding"
        )
        if health["responding"]:
            self.status_line(
                "Health status",
                "✓" if health["status"] == "healthy" else "⚠",
                health["status"] or "unknown"
            )
        if health["latency_ms"]:
            self.status_line("Response latency", "ℹ", health["latency_ms"])

        # Token file
        self.print_header("3. TOKEN FILE")
        token = self.check_token_file()

        self.status_line(
            "Token file",
            "✓" if token["exists"] else "○",
            "captured" if token["exists"] else "waiting"
        )
        if token["exists"]:
            if token["age_seconds"]:
                age_str = f"{int(token['age_seconds'])}s ago"
            else:
                age_str = "recent"
            self.status_line("Age", "ℹ", age_str)

            self.status_line(
                "Contains code",
                "✓" if token["has_code"] else "✗",
                "yes" if token["has_code"] else "no"
            )

            status_color = GREEN if token["status"] == "captured" else YELLOW
            self.status_line(
                f"Capture status",
                "✓",
                token["status"] or "unknown",
                status_color
            )

            if token["captured_at"]:
                self.status_line("Captured at", "ℹ", token["captured_at"][:19])

        # Quick commands
        self.print_header("QUICK COMMANDS")
        print(f"  {BLUE}View logs:{NC}          tail -f {OAUTH_LOG}")
        print(f"  {BLUE}Service status:{NC}      systemctl status dhan-oauth")
        print(f"  {BLUE}Restart service:{NC}     sudo systemctl restart dhan-oauth")
        print(f"  {BLUE}View token:{NC}          cat {TOKEN_FILE}")
        print(f"\n  {DIM}Press Ctrl+C to exit{NC}\n")

    def run(self):
        """Run monitoring loop."""
        try:
            while True:
                self.display_dashboard()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print(f"\n{DIM}Monitor stopped{NC}\n")
            sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Dhan OAuth System Monitor")
    parser.add_argument("--vps", action="store_true", help="Monitor remote VPS service")
    parser.add_argument("--follow-logs", action="store_true", help="Follow OAuth server logs")
    parser.add_argument("--check-interval", type=int, default=5, help="Health check interval (seconds)")
    args = parser.parse_args()

    if args.follow_logs:
        # Follow logs
        if args.vps:
            try:
                subprocess.run(
                    ["ssh", "-i", VPS_SSH_KEY, VPS_HOST,
                     f"tail -f {VPS_HOME}/data/logs/oauth-callback.log"],
                    text=True
                )
            except KeyboardInterrupt:
                print(f"\n{DIM}Log following stopped{NC}\n")
        else:
            try:
                if not OAUTH_LOG.exists():
                    print(f"{YELLOW}Log file not found: {OAUTH_LOG}{NC}\n")
                    sys.exit(1)
                subprocess.run(["tail", "-f", str(OAUTH_LOG)])
            except KeyboardInterrupt:
                print(f"\n{DIM}Log following stopped{NC}\n")
    else:
        # Dashboard monitor
        monitor = OAuthMonitor(check_interval=args.check_interval, vps=args.vps)
        monitor.run()


if __name__ == "__main__":
    main()

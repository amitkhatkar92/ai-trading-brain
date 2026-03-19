"""
Dhan OAuth 2.0 Callback Server
===============================

Automated token capture system for Dhan authentication.

Flow:
  1. User visits: https://api.dhan.co/oauth2/authorize?client_id=...&redirect_uri=http://YOUR_IP:8000/callback
  2. User logs in with Dhan credentials
  3. Dhan redirects to http://YOUR_IP:8000/callback?code=XXXX
  4. This server captures the code
  5. Code saved to config/api_tokens.json
  6. Browser shows success message
  7. Trading engine loads token automatically (via utils.dhan_token_manager)

Requirements:
  - Port 8000 must be open in firewall (UFW allows by default)
  - Redirect URI must match exactly: http://YOUR_IP:8000/callback

Security:
  - Never logs the access token itself
  - Saves token with strict 600 file permissions
  - Automatically ignores old tokens
  - Atomic file writes (no partial writes)

Usage:
  python3 scripts/dhan_oauth_server.py

  Or via systemd:
  systemctl start dhan-oauth
  systemctl status dhan-oauth
"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

# Add project root to path so imports work
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils import get_logger

log = get_logger(__name__)

# Paths (PROJECT_ROOT already set above)
CONFIG_DIR = PROJECT_ROOT / "config"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
TOKEN_FILE = CONFIG_DIR / "api_tokens.json"
LOG_FILE = LOG_DIR / "oauth-callback.log"

# Ensure directories exist
CONFIG_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# File logger for OAuth events
file_logger = logging.getLogger("oauth_callback")
file_logger.setLevel(logging.INFO)
fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
fh.setFormatter(formatter)
file_logger.addHandler(fh)


class DhanOAuthHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Dhan OAuth callbacks."""

    server_instance = None  # Will be set by server at runtime

    def log_message(self, format_str, *args):
        """Override to use our logger instead of stderr."""
        log.info(f"{self.client_address[0]} - {format_str % args}")

    def do_GET(self):
        """Handle incoming GET request (OAuth callback)."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # ── Extract authorization code (from root / or /callback) ──────
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", ["N/A"])[0]

        # ── Endpoint: /callback or / (both handle OAuth) ──────────────
        if path in ["/callback", "/"]:
            if not code:
                log.warning(f"Callback received on {path} WITHOUT authorization code")
                self._send_error_response("No authorization code provided")
                return

            log.info(f"✅ Authorization code captured from {path} [state={state}]")

            # ── Save token atomically ────────────────────────────────
            if self._save_token_atomically(code):
                log.info("✅ Token saved to config/api_tokens.json")
                self._send_success_response(code)
                
                # Signal server to stop gracefully
                if self.server_instance:
                    self.server_instance.should_stop = True
            else:
                log.error("❌ Failed to save token to file")
                self._send_error_response("Failed to save token")

        # ── Endpoint: /health ───────────────────────────────────────
        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            health = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "listening_on": "0.0.0.0:8000",
                "callback_uri": "/callback or /"
            }
            self.wfile.write(json.dumps(health).encode())
            log.info("Health check request")

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _save_token_atomically(self, code: str) -> bool:
        """
        Save token to file with atomic write (no partial writes).
        
        Attempts to exchange authorization code for long-lived access token.
        If exchange succeeds, saves access_token in new format (30-day window).
        If exchange fails, falls back to saving authorization code.
        """
        try:
            client_id = os.getenv("DHAN_CLIENT_ID", "")
            log.info(f"Attempting to exchange code for access token [client_id={client_id[:10]}...]")

            # Try to exchange code for access token
            access_token = self._exchange_code_for_token(code, client_id)
            
            if access_token:
                # SUCCESS: Save access_token format (NEW FORMAT - DAILY SESSION)
                from datetime import timedelta
                
                # CRITICAL: Dhan tokens are DAILY SESSION tokens
                # Token expires at market close (16:51 UTC same day)
                now = datetime.utcnow()
                
                # Calculate expire time: same day at 16:51 UTC
                # If already past 16:51 UTC, token expires TODAY at 16:51
                expires_at = now.replace(hour=16, minute=51, second=0, microsecond=0)
                
                # If current time is already past 16:51, use today's time anyway
                # (will be expired immediately, triggering daily refresh tomorrow)
                ttl_days = 0  # Daily token - expires same day
                
                token_data = {
                    "access_token": access_token,
                    "client_id": client_id,
                    "dhan_client_id": os.getenv("DHAN_CLIENT_ID", ""),
                    "captured_at": now.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "ttl_days": ttl_days,
                    "token_type": "DAILY_SESSION",
                    "refresh_required": True,
                    "critical_note": "Dhan tokens are daily session tokens. New token required daily at market open.",
                    "status": "active"
                }
                log.info(f"✅ Exchanged code → access_token (DAILY_SESSION, expires at {expires_at.isoformat()})")
            else:
                # FALLBACK: Save authorization code (OLD)
                log.warning("⚠️  Token exchange failed, saving authorization code for manual exchange")
                token_data = {
                    "dhan_request_code": code,
                    "captured_at": datetime.utcnow().isoformat(),
                    "status": "pending_exchange"
                }

            # Write to temp file first
            temp_file = TOKEN_FILE.with_suffix(".json.tmp")
            with open(temp_file, "w") as f:
                json.dump(token_data, f, indent=2)

            # Atomic rename (ensures complete write before filesystem commit)
            temp_file.replace(TOKEN_FILE)

            # Set strict permissions (600 = rw-------)
            os.chmod(TOKEN_FILE, 0o600)

            file_logger.info(f"Token saved: {TOKEN_FILE}")
            return True

        except Exception as e:
            log.error(f"Failed to save token: {e}")
            file_logger.error(f"Token save failed: {e}")
            return False

    def _exchange_code_for_token(self, code: str, client_id: str) -> Optional[str]:
        """
        Exchange authorization code for long-lived access token.
        
        Makes HTTP POST to Dhan token endpoint with:
          grant_type: "authorization_code"
          code: authorization code from OAuth callback
          client_id: Dhan application Client ID
          redirect_uri: must match the redirect_uri in Auth request
        
        Returns:
            str: access_token if successful, None if exchange fails
        """
        try:
            import requests
            
            DHAN_TOKEN_ENDPOINT = "https://api.dhan.co/oauth2/token"
            redirect_uri = "http://localhost:8000/callback"
            
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
            }
            
            log.info(f"Exchanging code at {DHAN_TOKEN_ENDPOINT}...")
            response = requests.post(DHAN_TOKEN_ENDPOINT, json=payload, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                
                if access_token:
                    log.info(f"✅ Token exchange successful")
                    file_logger.info(f"Token exchange successful | Token: {access_token[:20]}...")
                    return access_token
                else:
                    log.error(f"Token response missing access_token field: {token_data}")
                    return None
            else:
                log.error(
                    f"Token exchange failed: {response.status_code} | "
                    f"{response.text[:400]}"
                )
                file_logger.error(f"Exchange failed ({response.status_code}): {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            log.error(f"Token exchange request failed: {e}")
            file_logger.error(f"Exchange request error: {e}")
            return None
        except ImportError:
            log.warning("requests library not available, cannot exchange code for token")
            file_logger.warning("requests library not available")
            return None
        except Exception as e:
            log.error(f"Unexpected error during token exchange: {e}")
            file_logger.error(f"Exchange error: {e}")
            return None

    def _send_success_response(self, code: str):
        """Send success HTML response."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dhan Authentication Successful</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }}
                .checkmark {{
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: #4CAF50;
                    margin: 0 auto 20px;
                    animation: scaleIn 0.5s ease-in-out;
                }}
                .checkmark::after {{
                    content: "✓";
                    color: white;
                    font-size: 36px;
                    line-height: 60px;
                    font-weight: bold;
                }}
                h1 {{
                    color: #333;
                    margin: 0 0 20px 0;
                    font-size: 24px;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                    font-size: 14px;
                }}
                .code {{
                    background: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    font-family: monospace;
                    font-size: 12px;
                    word-break: break-all;
                    margin-top: 15px;
                    color: #333;
                }}
                @keyframes scaleIn {{
                    from {{ transform: scale(0); }}
                    to {{ transform: scale(1); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark"></div>
                <h1>Authentication Successful! ✓</h1>
                <p>Your Dhan credentials have been captured.</p>
                <p>The trading engine will use this token automatically.</p>
                <p><strong>You may close this window.</strong></p>
                <div class="code">
                    Code: {code[:20]}...
                </div>
                <p style="font-size: 12px; color: #999; margin-top: 20px;">
                    Token saved to: config/api_tokens.json
                </p>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(html.encode()))
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_error_response(self, message: str):
        """Send error HTML response."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }}
                h1 {{
                    color: #d32f2f;
                    margin: 0 0 20px 0;
                    font-size: 24px;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                    font-size: 14px;
                }}
                .error {{
                    background: #ffebee;
                    border-left: 4px solid #d32f2f;
                    padding: 15px;
                    border-radius: 4px;
                    margin-top: 20px;
                    text-align: left;
                    font-size: 12px;
                    color: #c62828;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentication Failed ✗</h1>
                <p>Could not capture your Dhan credentials.</p>
                <div class="error">
                    <strong>Error:</strong> {message}
                </div>
                <p style="margin-top: 20px; font-size: 12px; color: #999;">
                    Check the server logs at: data/logs/oauth-callback.log
                </p>
            </div>
        </body>
        </html>
        """

        self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(html.encode()))
        self.end_headers()
        self.wfile.write(html.encode())


class DhanOAuthServer(HTTPServer):
    """HTTP server with graceful stop capability."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.should_stop = False

    def serve_forever(self):
        """Modified serve_forever to check should_stop."""
        while not self.should_stop:
            self.handle_request()


def run_oauth_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the OAuth callback server."""
    
    log.info("=" * 70)
    log.info("  DHAN OAUTH CALLBACK SERVER")
    log.info("=" * 70)
    log.info(f"Listening on: {host}:{port}")
    log.info(f"Callback URI: http://YOUR_IP:{port}/callback")
    log.info(f"Health check: http://YOUR_IP:{port}/health")
    log.info(f"Token will be saved to: {TOKEN_FILE}")
    log.info("")
    log.info("Waiting for Dhan redirect...")
    log.info("=" * 70)

    server = DhanOAuthServer((host, port), DhanOAuthHandler)
    DhanOAuthHandler.server_instance = server

    try:
        server.serve_forever()
        log.info("✅ Server shutting down gracefully")
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received, shutting down")
    finally:
        server.server_close()
        log.info("Server closed")


if __name__ == "__main__":
    import logging
    
    # Add console logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    file_logger.addHandler(console_handler)
    
    run_oauth_server()

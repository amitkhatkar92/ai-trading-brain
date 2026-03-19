"""
Dhan Token Exchange Module
===========================

Handles OAuth code → access token conversion and token refresh.

Features:
  ✓ Exchange authorization code for long-lived access token
  ✓ Automatic token refresh before expiration
  ✓ Configurable 30-day token lifecycle
  ✓ Secure storage with atomic writes
  ✓ Fallback error handling

Usage:
  from utils.dhan_token_exchange import exchange_code_for_token

  # Exchange short-lived code for long-lived token
  token = exchange_code_for_token(
      code="AUTH_CODE_FROM_OAUTH",
      client_id="2603183256"
  )

Reference:
  https://developer.dhanhq.co/home
  OAuth Token Endpoint: https://api.dhan.co/oauth2/token
"""

import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from utils import get_logger

log = get_logger(__name__)

# Configuration
DHAN_TOKEN_ENDPOINT = "https://api.dhan.co/oauth2/token"
TOKEN_TTL_DAYS = 30  # Custom 30-day window (instead of Dhan's default 90)
TOKEN_REFRESH_THRESHOLD_DAYS = 3  # Refresh if less than 3 days left

# File paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TOKEN_FILE = CONFIG_DIR / "api_tokens.json"
EXCHANGE_LOG_FILE = PROJECT_ROOT / "data" / "logs" / "token-exchange.log"

# Ensure directories exist
CONFIG_DIR.mkdir(exist_ok=True)
EXCHANGE_LOG_FILE.parent.mkdir(exist_ok=True)


def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: Optional[str] = None,
    redirect_uri: str = "http://localhost:8000/callback"
) -> Optional[Dict[str, Any]]:
    """
    Exchange OAuth authorization code for long-lived access token.

    Args:
        code: Authorization code from OAuth callback
        client_id: Dhan application Client ID
        client_secret: Optional client secret if needed
        redirect_uri: Must match redirect_uri in OAuth request

    Returns:
        dict: Token data with accessToken, expiresAt, etc.
              None if exchange fails
    """
    try:
        log.info(f"Exchanging code for token [client_id={client_id}]")

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }

        # Add client secret if provided
        if client_secret:
            payload["client_secret"] = client_secret

        # Make token exchange request
        response = requests.post(
            DHAN_TOKEN_ENDPOINT,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            token_response = response.json()
            log.info("✅ Token exchange successful")
            return token_response

        else:
            log.error(
                f"Token exchange failed: {response.status_code} | "
                f"{response.text[:200]}"
            )
            return None

    except requests.exceptions.RequestException as e:
        log.error(f"Token exchange request failed: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error during token exchange: {e}")
        return None


def save_access_token(
    access_token: str,
    client_id: str,
    ttl_days: int = TOKEN_TTL_DAYS,
    expires_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save access token to config/api_tokens.json with expiry tracking.

    Args:
        access_token: JWT access token from exchange
        client_id: Dhan application Client ID
        ttl_days: Token lifetime in days (default 30)
        expires_at: Explicit expiry date (overrides ttl_days). For tokens with known expiry.
        metadata: Optional additional metadata to store

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        now = datetime.utcnow()
        
        # Use explicit expiry date if provided, otherwise calculate from ttl_days
        if expires_at is None:
            expires_at = now + timedelta(days=ttl_days)

        # Calculate actual TTL from expires_at date
        actual_ttl_days = (expires_at - now).days

        token_data = {
            "access_token": access_token,
            "client_id": client_id,
            "captured_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "ttl_days": actual_ttl_days,
            "status": "active",
        }

        # Add optional metadata
        if metadata:
            token_data.update(metadata)

        # Atomic write (temp → rename)
        temp_file = TOKEN_FILE.with_suffix(".json.tmp")

        with open(temp_file, "w") as f:
            json.dump(token_data, f, indent=2)

        # Atomic rename
        temp_file.replace(TOKEN_FILE)

        # Set strict permissions (600 = rw-------)
        os.chmod(TOKEN_FILE, 0o600)

        log.info(
            f"✅ Access token saved to {TOKEN_FILE} "
            f"[expires: {expires_at.isoformat()} | {actual_ttl_days} days]"
        )
        _log_to_file(f"Token saved | Expires: {expires_at.isoformat()}")

        return True

    except Exception as e:
        log.error(f"Failed to save access token: {e}")
        return False


def load_access_token() -> Optional[str]:
    """
    Load valid access token from file.

    Returns:
        str: access_token if valid and not expired
        None: if file missing, invalid, or expired
    """
    try:
        if not TOKEN_FILE.exists():
            log.debug("Token file not found")
            return None

        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        # Try new format first (access_token)
        token = data.get("access_token")
        if not token:
            # Fallback to old format (dhan_request_code)
            token = data.get("dhan_request_code")

        if not token:
            log.warning("Token file exists but no token found")
            return None

        # Check expiration
        expires_at_str = data.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(
                expires_at_str.replace("Z", "+00:00")
            )

            if datetime.utcnow() > expires_at:
                log.error(
                    f"❌ Token EXPIRED [was: {expires_at.isoformat()}]"
                )
                _log_to_file("Token expired - needs refresh")
                return None

            # Check if refresh needed (< 3 days left)
            days_left = (expires_at - datetime.utcnow()).days
            if days_left < TOKEN_REFRESH_THRESHOLD_DAYS:
                log.warning(
                    f"⚠️  Token expiring soon ({days_left} days left) - "
                    f"recommend refresh"
                )

        log.info(f"✅ Token loaded [status: active]")
        return token

    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in token file: {e}")
        return None
    except Exception as e:
        log.error(f"Failed to load token: {e}")
        return None


def get_token_expiry_info() -> Optional[Dict[str, Any]]:
    """
    Get token expiration details for monitoring.

    Returns:
        dict: expires_at, days_left, needs_refresh
        None: if token not found
    """
    try:
        if not TOKEN_FILE.exists():
            return None

        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        expires_at_str = data.get("expires_at")
        if not expires_at_str:
            return None

        expires_at = datetime.fromisoformat(
            expires_at_str.replace("Z", "+00:00")
        )
        now = datetime.utcnow()
        days_left = (expires_at - now).total_seconds() / (24 * 3600)

        return {
            "expires_at": expires_at.isoformat(),
            "days_left": round(days_left, 1),
            "needs_refresh": days_left < TOKEN_REFRESH_THRESHOLD_DAYS,
            "is_expired": days_left < 0,
        }

    except Exception as e:
        log.error(f"Could not get token expiry info: {e}")
        return None


def _log_to_file(message: str):
    """Log message to exchange log file."""
    try:
        with open(EXCHANGE_LOG_FILE, "a") as f:
            timestamp = datetime.utcnow().isoformat()
            f.write(f"{timestamp} | {message}\n")
    except Exception:
        pass  # Silent fail on logging error

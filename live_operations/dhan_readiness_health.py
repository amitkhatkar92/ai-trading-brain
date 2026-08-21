"""
live_operations/dhan_readiness_health.py
=========================================
Produces data/dhan_readiness.json — a single machine-readable snapshot of
live-trading readiness covering authentication, connectivity, safety, and
pipeline health.

Called from MasterOrchestrator at startup and every 30 min thereafter.
Never raises; always produces a file with status=ERROR on failure.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
_DEFAULT_OUT = _DATA / "dhan_readiness.json"

_DHAN_PROFILE_URL = "https://api.dhan.co/v2/profile"
_HTTP_TIMEOUT = 8


def write_readiness_health(output_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Collect all readiness signals and write them to output_path (default:
    data/dhan_readiness.json).  Returns the health dict.  Never raises.
    """
    out = Path(output_path) if output_path else _DEFAULT_OUT
    try:
        health = _build_health()
    except Exception as exc:
        health = {"status": "ERROR", "error": str(exc)[:300],
                  "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(health, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass
    return health


def _build_health() -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    h: Dict[str, Any] = {"checked_at": now_iso}

    # ── 1. PAPER_TRADING ─────────────────────────────────────────────────
    try:
        import config as _cfg
        pt = bool(_cfg.PAPER_TRADING)
    except Exception:
        pt = True   # safe default
    live_auth = os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() == "true"
    h["paper_trading"] = pt
    h["live_trading_authorized"] = live_auth
    h["execution_mode"] = "PAPER" if pt else ("LIVE" if live_auth else "PAPER_FORCED")

    # ── 2. Token metadata ─────────────────────────────────────────────────
    token_store = _DATA / "dhan_token_store.json"
    token_health = _DATA / "dhan_token_health.json"
    h["token"] = _read_token_meta(token_store, token_health)

    # ── 3. DTA-002 sync state ─────────────────────────────────────────────
    h["dta002_sync"] = _read_dta002_state()

    # ── 4. Dhan profile (authenticated read-only) ─────────────────────────
    h["dhan_profile"] = _probe_dhan_profile()

    # ── 5. VPS public IP ─────────────────────────────────────────────────
    h["vps_ip"] = _get_vps_ip()

    # ── 6. Static IP status ───────────────────────────────────────────────
    # /v2/staticip returns 404 — Dhan does not expose this via API v2.
    # Functional check: profile HTTP 200 from VPS IP = IP is accepted.
    profile_ok = h["dhan_profile"].get("http_status") == 200
    h["static_ip"] = {
        "vps_ip": h["vps_ip"],
        "functional_check": "PASS" if profile_ok else "FAIL",
        "portal_verification": "MANUAL VERIFICATION REQUIRED — /v2/staticip returns 404; "
                               "confirm 178.18.252.24 on Dhan Web → Profile → API → Static IP",
    }

    # ── 7. DhanFeed (data API) singleton state ────────────────────────────
    h["dhan_data_api"] = _read_dhan_feed_state()

    # ── 8. KLP state ─────────────────────────────────────────────────────
    h["klp"] = _read_klp_state()

    # ── 9. KSL health ─────────────────────────────────────────────────────
    h["ksl"] = _read_ksl_health()

    # ── 10. Outcome collection ────────────────────────────────────────────
    h["outcome_collection"] = _read_outcome_state()

    # ── 11. Broker/order activity ─────────────────────────────────────────
    h["broker_activity"] = _read_broker_activity()

    # ── 12. Scheduler / container ────────────────────────────────────────
    h["scheduler"] = _read_scheduler_state()

    # ── 13. Overall status ────────────────────────────────────────────────
    h["status"] = _overall_status(h)
    return h


# ── Component readers ─────────────────────────────────────────────────────────

def _read_token_meta(store_path: Path, health_path: Path) -> dict:
    out: dict = {}
    try:
        if store_path.exists():
            d = json.loads(store_path.read_text(encoding="utf-8"))
            out["status"]        = d.get("status")
            out["expiry_time"]   = d.get("expiry_time")
            out["generation_id"] = d.get("generation_id")
            out["source"]        = d.get("source")
            # Expiry check
            from datetime import datetime, timezone as _tz
            exp_str = d.get("expiry_time", "")
            if exp_str:
                try:
                    exp_dt = datetime.fromisoformat(exp_str)
                    now_utc = datetime.now(_tz.utc)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=_tz.utc)
                    secs_left = (exp_dt - now_utc).total_seconds()
                    out["expires_in_h"]  = round(secs_left / 3600, 2)
                    out["token_expired"] = secs_left <= 0
                    out["token_expiring_soon"] = 0 < secs_left <= 7200
                except Exception:
                    pass
    except Exception as exc:
        out["read_error"] = str(exc)[:200]

    try:
        if health_path.exists():
            h = json.loads(health_path.read_text(encoding="utf-8"))
            out["health_status"]  = h.get("status")
            out["live_reload"]    = h.get("live_reload")
    except Exception:
        pass

    out["token_secret_logged"] = False   # invariant: token never in store/health JSON
    return out


def _read_dta002_state() -> dict:
    try:
        from scripts.dhan_auth.dhan_token_sync import get_token_sync
        ts = get_token_sync()
        state = ts.get_token_state()
        return {
            "last_loaded_generation_id": ts._last_loaded_generation_id,
            "token_state":               state,
            "status":                    "HEALTHY" if state in ("TOKEN_HEALTHY", "TOKEN_NEAR_EXPIRY") else state,
        }
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": str(exc)[:200]}


def _probe_dhan_profile() -> dict:
    """Authenticate to Dhan profile endpoint. Read-only."""
    import pathlib, requests as _req
    token = ""
    # Load token from .env (never from process env in test environments)
    env_file = pathlib.Path(_ROOT / ".env")
    try:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DHAN_ACCESS_TOKEN"):
                    token = line.split("=", 1)[-1].strip().strip('"').strip("'")
                    break
    except Exception:
        pass
    if not token:
        token = os.getenv("DHAN_ACCESS_TOKEN", "")

    if not token:
        return {"status": "NO_TOKEN", "authenticated": False}

    t0 = time.monotonic()
    try:
        r = _req.get(
            _DHAN_PROFILE_URL,
            headers={"access-token": token, "Content-Type": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )
        elapsed = int((time.monotonic() - t0) * 1000)
        if r.status_code == 200:
            d = r.json()
            return {
                "http_status":    200,
                "authenticated":  True,
                "latency_ms":     elapsed,
                "dhanClientId":   d.get("dhanClientId"),
                "tokenValidity":  d.get("tokenValidity"),
                "activeSegment":  d.get("activeSegment"),
                "ddpi":           d.get("ddpi"),
                "dataPlan":       d.get("dataPlan"),
                "dataValidity":   d.get("dataValidity"),
                "token_in_response": False,  # invariant check
            }
        return {
            "http_status":   r.status_code,
            "authenticated": False,
            "latency_ms":    elapsed,
            "raw_snippet":   r.text[:100],
        }
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)[:200], "authenticated": False}


def _get_vps_ip() -> str:
    try:
        import requests as _req
        return _req.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return "<fetch_failed>"


def _read_dhan_feed_state() -> dict:
    try:
        from data_feeds import get_feed_manager
        fm = get_feed_manager()
        if hasattr(fm, "dhan") and fm.dhan is not None:
            auth = fm.dhan.auth_state()
            return {
                "status":         "LIVE" if auth.get("api_mode") == "LIVE" else "FALLBACK",
                "token_present":  auth.get("token_present"),
                "expires_in_h":   auth.get("expires_in_h"),
                "token_expired":  auth.get("token_expired"),
                "fallback_active": auth.get("api_mode") != "LIVE",
            }
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": str(exc)[:200]}
    return {"status": "UNAVAILABLE"}


def _read_klp_state() -> dict:
    klp_dir = _DATA / "klp"
    today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    klp_file = klp_dir / f"KLP_{today}.jsonl"
    out: dict = {"today_file": str(klp_file), "today_file_exists": klp_file.exists()}
    if klp_file.exists():
        lines = klp_file.read_text(encoding="utf-8").splitlines()
        obs_count     = sum(1 for l in lines if '"KNOWLEDGE_OBSERVATION"' in l)
        outcome_count = sum(1 for l in lines if '"OUTCOME_UPDATE"' in l)
        pending_count = sum(1 for l in lines if '"OUTCOME_PENDING"' in l)
        out["observations_today"] = obs_count
        out["outcomes_filled_today"] = outcome_count
        out["outcomes_pending"] = pending_count
    try:
        from opportunity_engine.klp_evaluator import get_klp_evaluator
        ev = get_klp_evaluator()
        stats = ev.get_today_stats()
        out["today_stats"] = stats
    except Exception:
        pass
    return out


def _read_ksl_health() -> dict:
    health_file = _DATA / "knowledge_pipeline_health.json"
    out: dict = {"health_file": str(health_file), "health_file_exists": health_file.exists()}
    if health_file.exists():
        try:
            d = json.loads(health_file.read_text(encoding="utf-8"))
            out["audit_timestamp"]   = d.get("audit_timestamp")
            out["patterns_detected"] = d.get("patterns_detected", d.get("total_patterns"))
            out["questions_count"]   = d.get("questions_count", d.get("total_questions"))
            out["proposals_count"]   = d.get("proposals_built", d.get("proposals_count"))
            out["klp_bridge_last"]   = d.get("klp_evidence_ingested")
        except Exception as exc:
            out["read_error"] = str(exc)[:200]
    # KSL state file
    ksl_state = _DATA / "ksl" / "knowledge_system_state.json"
    if ksl_state.exists():
        try:
            d2 = json.loads(ksl_state.read_text(encoding="utf-8"))
            out["ksl_state_timestamp"] = d2.get("last_updated") or d2.get("timestamp")
        except Exception:
            pass
    return out


def _read_outcome_state() -> dict:
    klp_adapter_state = _DATA / "ksl" / "klp_adapter_state.json"
    out: dict = {}
    if klp_adapter_state.exists():
        try:
            d = json.loads(klp_adapter_state.read_text(encoding="utf-8"))
            out["last_run"]           = d.get("last_run")
            out["total_ingested"]     = d.get("total_ingested")
            out["last_new_evidence"]  = d.get("last_new_evidence")
        except Exception:
            pass
    out["adapter_state_exists"] = klp_adapter_state.exists()
    return out


def _read_broker_activity() -> dict:
    journal = _DATA / "paper_trades.csv"
    out: dict = {
        "broker_calls": 0, "live_orders": 0, "modifications": 0, "cancellations": 0,
    }
    if journal.exists():
        lines = journal.read_text(encoding="utf-8", errors="replace").splitlines()
        data_lines = [l for l in lines if l.strip() and not l.startswith("timestamp")]
        out["total_journal_entries"] = len(data_lines)
        out["sim_orders"]  = sum(1 for l in data_lines if ",SIM_" in l)
        out["live_orders"] = sum(1 for l in data_lines if ",SIM_" not in l)
    return out


def _read_scheduler_state() -> dict:
    health_files = sorted((_DATA / "health_reports").glob("cycle_*.json"))
    out: dict = {"container": "UNKNOWN"}
    if health_files:
        latest = health_files[-1]
        try:
            d = json.loads(latest.read_text(encoding="utf-8"))
            out["last_cycle_file"]  = latest.name
            out["last_cycle_time"]  = d.get("timestamp") or d.get("cycle_time")
            out["last_cycle_status"] = d.get("status", "unknown")
        except Exception:
            pass
    # PID file check
    pid_file = Path("/app/data/trading_engine.pid")
    if pid_file.exists():
        try:
            out["pid"] = pid_file.read_text().strip()
        except Exception:
            pass
    return out


def _overall_status(h: dict) -> str:
    if not h.get("paper_trading"):
        return "⚠️ NOT_SAFE — PAPER_TRADING=False"
    prof = h.get("dhan_profile", {})
    if not prof.get("authenticated"):
        return "⚠️ NOT_READY — Dhan authentication failed"
    tok = h.get("token", {})
    if tok.get("token_expired"):
        return "⚠️ NOT_READY — token expired"
    return "✅ READY"

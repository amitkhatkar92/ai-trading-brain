"""
scripts/momentum_knowledge_builder.py
======================================
Builds the knowledge evidence ledger from 10 years of daily data.

APPROACH — top-mover selection (not fixed watchlist + RSI trigger):
  For each trading day D over 10 years:
    1. Compute daily return for all 230 Nifty universe symbols
    2. Select top 10 gainers  → direction = BUY
    3. Select bottom 10 losers → direction = SELL
    4. Record: regime, sector, magnitude of move, RSI state at day D
    5. Compute outcomes at T+1, T+3, T+5 (strictly future — no lookahead)
    6. outcome_class: WIN if T+3 continues in direction, LOSS if reverses

WHY top-movers (not RSI on fixed stocks):
  The KDA needs to recognise conditions that PRECEDED large moves.
  Training on confirmed large-movers (sorted by actual return) gives
  the knowledge base real examples of what strong moves look like,
  how they resolve at T+1/T+3/T+5, and which regime+sector combinations
  repeat this pattern.

Guarantees:
  • no_lookahead = True — features use only close[D]; outcomes use close[D+N]
  • Idempotent — skips (symbol, trade_date, direction) already in ledger
  • event_type = "EVIDENCE" — compatible with KnowledgeFusionEngine
  • source = "momentum_replay" — distinguishable from historical_replay records

Usage (run on VPS host, not inside container):
  cd /root/ai-trading-brain
  python3 scripts/momentum_knowledge_builder.py
  
  Or inside container:
  docker exec ai-trading-brain python3 /app/scripts/momentum_knowledge_builder.py
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    raise SystemExit("pip install yfinance pandas numpy")

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
KEL  = ROOT / "data" / "knowledge_evidence_ledger.jsonl"
KEL.parent.mkdir(parents=True, exist_ok=True)

# ── Config ─────────────────────────────────────────────────────────────────────
TOP_N           = 10        # top 10 gainers + bottom 10 losers per day
MIN_MOVE_PCT    = 0.80      # minimum |daily move| % to qualify as a "mover"
RSI_PERIOD      = 14
SMA_FAST        = 20
SMA_SLOW        = 50
FETCH_START     = "2015-12-01"   # pull from Dec 2015 so Jan 2016 has SMA warmup
OUTCOME_DAYS    = [1, 3, 5]
SOURCE_TAG      = "momentum_replay"

# ── Outcome classification thresholds ─────────────────────────────────────────
WIN_THRESHOLD   =  0.50     # T+3 must move >= 0.5% in signal direction → WIN
LOSS_THRESHOLD  = -0.50     # T+3 moves >= 0.5% against direction → LOSS


# ── Load universe from nifty500_universe.json ─────────────────────────────────

def _load_universe() -> list[dict]:
    u_file = ROOT / "data" / "nifty500_universe.json"
    if not u_file.exists():
        raise SystemExit(f"Missing {u_file} — run the universe rebuild first.")
    data = json.loads(u_file.read_text(encoding="utf-8"))
    # Keep only entries with a valid yahoo_ticker
    valid = [d for d in data if d.get("yahoo_ticker") and d.get("symbol")]
    print(f"[MKB] Universe loaded: {len(valid)} symbols from nifty500_universe.json")
    return valid


# ── RSI (Wilder / EWM) ────────────────────────────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


# ── Regime from NIFTY 50-day SMA ──────────────────────────────────────────────

def _compute_regime(nifty_close: pd.Series) -> pd.Series:
    sma  = nifty_close.rolling(SMA_SLOW, min_periods=SMA_SLOW // 2).mean()
    reg  = pd.Series("RANGE", index=nifty_close.index)
    reg[nifty_close > sma * 1.02]  = "BULL"
    reg[nifty_close < sma * 0.98]  = "BEAR"
    return reg


# ── Idempotency guard ─────────────────────────────────────────────────────────

def _load_existing_keys(path: Path) -> set[str]:
    """(symbol, trade_date, direction) triplets already in ledger with our source tag."""
    keys: set[str] = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("source") == SOURCE_TAG:
                keys.add(f"{r['symbol']}|{r['trade_date']}|{r['direction']}")
        except Exception:
            pass
    print(f"[MKB] Existing {SOURCE_TAG} records in KEL: {len(keys)}")
    return keys


# ── Main builder ──────────────────────────────────────────────────────────────

def build() -> None:
    universe = _load_universe()
    sym_to_sector: dict[str, str] = {d["symbol"]: d.get("sector", "UNKNOWN") for d in universe}
    tickers_ns = [d["yahoo_ticker"] if d["yahoo_ticker"].endswith(".NS")
                  else d["symbol"] + ".NS"
                  for d in universe]

    print(f"[MKB] Fetching {len(tickers_ns)} tickers × 10y from yfinance …")
    all_tickers = tickers_ns + ["^NSEI"]
    raw = yf.download(
        tickers=all_tickers,
        start=FETCH_START,
        interval="1d",
        auto_adjust=True,
        progress=True,
        threads=True,
    )
    if raw is None or raw.empty:
        raise SystemExit("[MKB] yfinance returned empty data.")

    if isinstance(raw.columns, pd.MultiIndex):
        closes  = raw["Close"]
        volumes = raw["Volume"] if "Volume" in raw else pd.DataFrame()
    else:
        closes  = raw
        volumes = pd.DataFrame()

    print(f"[MKB] Downloaded {len(closes)} trading days × {closes.shape[1]} symbols.")

    # ── NIFTY regime ──────────────────────────────────────────────────────────
    nifty_col = "^NSEI" if "^NSEI" in closes.columns else None
    if nifty_col:
        regime_s = _compute_regime(closes[nifty_col].dropna())
        print(f"[MKB] Regime computed. BULL={(regime_s=='BULL').sum()} "
              f"RANGE={(regime_s=='RANGE').sum()} BEAR={(regime_s=='BEAR').sum()}")
    else:
        regime_s = pd.Series(dtype=str)
        print("[MKB] WARNING: ^NSEI missing — regime defaults to RANGE.")

    # ── Per-symbol RSI & SMA matrices (vectorised) ─────────────────────────────
    print("[MKB] Computing RSI and SMA matrices …")
    stock_cols = [c for c in closes.columns if c != "^NSEI"]
    stock_closes = closes[stock_cols].copy()

    rsi_matrix  = stock_closes.apply(_rsi, axis=0)
    sma20_matrix = stock_closes.rolling(SMA_FAST, min_periods=SMA_FAST // 2).mean()
    sma50_matrix = stock_closes.rolling(SMA_SLOW, min_periods=SMA_SLOW // 2).mean()

    # Volume ratio: today's volume vs 20-day average (if volume data available)
    if not volumes.empty:
        vol_cols    = [c for c in volumes.columns if c != "^NSEI"]
        vol_avail   = stock_closes.columns.intersection(vol_cols)
        vol_matrix  = volumes[vol_avail] if len(vol_avail) else pd.DataFrame()
        vol_sma     = vol_matrix.rolling(20, min_periods=5).mean() if not vol_matrix.empty else pd.DataFrame()
        vol_ratio_m = (vol_matrix / vol_sma.replace(0, float("nan"))) if not vol_matrix.empty else pd.DataFrame()
    else:
        vol_ratio_m = pd.DataFrame()

    # ── Daily returns matrix ──────────────────────────────────────────────────
    daily_ret = stock_closes.pct_change() * 100   # in %

    # ── Load existing keys for idempotency ────────────────────────────────────
    existing_keys = _load_existing_keys(KEL)

    # ── Iterate day by day ────────────────────────────────────────────────────
    trading_days = stock_closes.index
    # Need at least SMA warmup + RSI warmup; need T+5 in future
    start_idx = max(SMA_SLOW + RSI_PERIOD, 0)
    end_idx   = len(trading_days) - 6    # leave room for T+5

    written = 0
    skipped = 0
    days_processed = 0

    with KEL.open("a", encoding="utf-8") as fout:
        for i in range(start_idx, end_idx):
            day     = trading_days[i]
            day_str = str(day)[:10]

            # Daily returns for all stocks on this day
            day_ret = daily_ret.iloc[i].dropna()
            if len(day_ret) < TOP_N * 3:   # need enough valid stocks
                continue

            # Select top/bottom movers above minimum threshold
            sorted_ret = day_ret.sort_values(ascending=False)
            top_up    = sorted_ret[sorted_ret >=  MIN_MOVE_PCT].head(TOP_N)
            top_down  = sorted_ret[sorted_ret <= -MIN_MOVE_PCT].tail(TOP_N)

            if len(top_up) == 0 and len(top_down) == 0:
                continue   # flat market day, skip

            # Regime for this day
            regime = "RANGE"
            if not regime_s.empty and day in regime_s.index:
                regime = str(regime_s.loc[day])

            for direction, movers in [("BUY", top_up), ("SELL", top_down)]:
                for ticker_col, move_pct in movers.items():
                    bare = str(ticker_col).replace(".NS", "").strip()
                    key  = f"{bare}|{day_str}|{direction}"
                    if key in existing_keys:
                        skipped += 1
                        continue

                    # Features at day D (no lookahead — all computed up to day D)
                    close_d  = stock_closes[ticker_col].iloc[i]
                    rsi_d    = rsi_matrix[ticker_col].iloc[i]  if ticker_col in rsi_matrix.columns  else float("nan")
                    sma20_d  = sma20_matrix[ticker_col].iloc[i] if ticker_col in sma20_matrix.columns else float("nan")
                    sma50_d  = sma50_matrix[ticker_col].iloc[i] if ticker_col in sma50_matrix.columns else float("nan")

                    sma20_ratio = float(close_d / sma20_d) if sma20_d and sma20_d > 0 else None
                    sma50_ratio = float(close_d / sma50_d) if sma50_d and sma50_d > 0 else None

                    vol_ratio = None
                    if not vol_ratio_m.empty and ticker_col in vol_ratio_m.columns:
                        vr = vol_ratio_m[ticker_col].iloc[i]
                        vol_ratio = float(vr) if not pd.isna(vr) else None

                    # Outcomes: T+1, T+3, T+5 (strictly future)
                    def _ret_at(n: int) -> float | None:
                        j = i + n
                        if j >= len(trading_days):
                            return None
                        c_n = stock_closes[ticker_col].iloc[j]
                        if pd.isna(c_n) or close_d <= 0:
                            return None
                        return round(float((c_n - close_d) / close_d * 100), 4)

                    t1 = _ret_at(1)
                    t3 = _ret_at(3)
                    t5 = _ret_at(5)

                    # Directional outcome (positive = move continued in signal direction)
                    dir_t3 = (t3 if direction == "BUY" else -t3) if t3 is not None else None

                    if dir_t3 is not None:
                        if dir_t3 >= WIN_THRESHOLD:
                            outcome_class = "WIN"
                        elif dir_t3 <= LOSS_THRESHOLD:
                            outcome_class = "LOSS"
                        else:
                            outcome_class = "NEUTRAL"
                    else:
                        outcome_class = "PENDING"

                    sector = sym_to_sector.get(bare, "UNKNOWN")

                    rec = {
                        "observation_id": f"MKB_{bare}_{day_str}_{direction}_{uuid.uuid4().hex[:8]}",
                        "event_type":     "EVIDENCE",
                        "source":         SOURCE_TAG,
                        "symbol":         bare,
                        "trade_date":     day_str,
                        "direction":      direction,
                        "regime":         regime,
                        "sector":         sector,
                        "no_lookahead":   True,
                        # Features (from day D)
                        "rsi_at_signal":  round(float(rsi_d), 2) if not pd.isna(rsi_d) else None,
                        "sma20_ratio":    round(sma20_ratio, 4) if sma20_ratio else None,
                        "sma50_ratio":    round(sma50_ratio, 4) if sma50_ratio else None,
                        "vol_ratio":      round(vol_ratio, 2)   if vol_ratio   else None,
                        "day_move_pct":   round(float(move_pct), 4),   # magnitude of the big move
                        "mover_rank":     int(sorted_ret.index.get_loc(ticker_col)) + 1,
                        # Outcomes (strictly future)
                        "t1_ret_pct":     t1,
                        "t3_ret_pct":     t3,
                        "t5_ret_pct":     t5,
                        "outcome_class":  outcome_class,
                        "outcome_available": t1 is not None,
                        # KFE compat fields
                        "v3_score":       None,
                        "c2_score":       None,
                        "ge2":            (outcome_class == "WIN") if outcome_class != "PENDING" else None,
                        "written_at":     datetime.now(timezone.utc).isoformat(),
                    }

                    fout.write(json.dumps(rec) + "\n")
                    existing_keys.add(key)
                    written += 1

            days_processed += 1
            if days_processed % 250 == 0:
                print(f"  [MKB] {day_str} — processed {days_processed} days, "
                      f"written={written}, skipped={skipped}")

    print(f"\n[MKB] COMPLETE — days={days_processed} written={written} skipped={skipped}")
    print(f"[MKB] KEL path: {KEL}")
    print(f"[MKB] Expected pattern: {TOP_N*2} records/day × {days_processed} days")
    print(f"[MKB] The KDA now has {written + skipped} momentum-replay evidence records.")


if __name__ == "__main__":
    build()

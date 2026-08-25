"""
scripts/historical_knowledge_replay.py
========================================
One-time (idempotent) knowledge base builder.

Replays 10 years of daily price data for all watchlist symbols,
detects RSI-based patterns (purely knowledge-based, no strategy labels),
evaluates outcomes at T+1, and writes EVIDENCE records to
data/knowledge_evidence_ledger.jsonl.

Design guarantees
-----------------
• no_lookahead = True: signal uses only data up to and including day D;
  outcome uses close[D+1] which is strictly future relative to signal.
• Idempotent: (symbol, trade_date, direction) triplets already in the
  ledger are skipped — safe to run multiple times.
• No strategy labels: evidence is purely pattern-based (RSI zone, regime).
• Regime proxy: NIFTY50 vs its 50-day SMA (BULL / RANGE / BEAR).

Usage
-----
  python3 scripts/historical_knowledge_replay.py

Run on the VPS host (NOT inside the container) since it writes to ./data/.
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
    raise SystemExit("Install yfinance, pandas, numpy first: pip install yfinance pandas numpy")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).parent.parent
KEL    = ROOT / "data" / "knowledge_evidence_ledger.jsonl"
KEL.parent.mkdir(parents=True, exist_ok=True)

# ── Watchlist symbols (38 stocks + 2 indices) ─────────────────────────────────
_WATCHLIST_NS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "TATASTEEL.NS", "INFY.NS",
    "BANKBARODA.NS", "LT.NS", "COALINDIA.NS", "HCLTECH.NS", "SBIN.NS",
    "AXISBANK.NS", "ONGC.NS", "KOTAKBANK.NS", "BHARTIARTL.NS", "ITC.NS",
    "BAJAJFINSV.NS", "HINDALCO.NS", "ULTRACEMCO.NS", "TECHM.NS", "NTPC.NS",
    "HINDUNILVR.NS", "ASIANPAINT.NS", "BAJFINANCE.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "WIPRO.NS", "POWERGRID.NS", "TITAN.NS", "DRREDDY.NS",
    "ADANIENT.NS", "TATACONSUM.NS", "NESTLEIND.NS", "HAVELLS.NS",
    "GRASIM.NS", "JSWSTEEL.NS", "ADANIPORTS.NS", "DIVISLAB.NS",
]
_NIFTY_TICKER = "^NSEI"

# ── Sector map (mirrors knowledge_fusion_engine._SYMBOL_SECTOR) ───────────────
_SECTOR: dict[str, str] = {
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "BANKBARODA": "BANK", "INDUSINDBK": "BANK",
    "BAJAJFINSV": "FINSERVICES", "BAJFINANCE": "FINSERVICES",
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "TECHM": "IT", "HCLTECH": "IT",
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "NTPC": "ENERGY",
    "POWERGRID": "ENERGY", "COALINDIA": "ENERGY",
    "TATASTEEL": "METALS", "JSWSTEEL": "METALS", "HINDALCO": "METALS",
    "MARUTI": "AUTO", "LT": "INFRA",
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "DIVISLAB": "PHARMA",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG", "TATACONSUM": "FMCG",
    "ASIANPAINT": "CONSUMER", "HAVELLS": "CONSUMER", "TITAN": "CONSUMER",
    "BAJAJFINSV": "FINSERVICES", "ULTRACEMCO": "CEMENT",
    "BHARTIARTL": "TELECOM", "ADANIENT": "CONGLOMERATE",
    "ADANIPORTS": "INFRA", "GRASIM": "CEMENT",
}

# ── Parameters ────────────────────────────────────────────────────────────────
RSI_PERIOD   = 14
SMA_PERIOD   = 50       # NIFTY SMA for regime proxy
BUY_RSI_MAX  = 40       # RSI below this → BUY signal
SELL_RSI_MIN = 65       # RSI above this → SELL signal
FETCH_PERIOD = "10y"    # yfinance period
SOURCE_TAG   = "historical_replay"


def _rsi(close: "pd.Series", period: int = 14) -> "pd.Series":
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_l = loss.ewm(alpha=1/period, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _regime_series(nifty_close: "pd.Series") -> "pd.Series":
    """Returns a Series of 'BULL'/'BEAR'/'RANGE' indexed by date."""
    sma = nifty_close.rolling(SMA_PERIOD, min_periods=SMA_PERIOD // 2).mean()
    regime = pd.Series("RANGE", index=nifty_close.index)
    regime[nifty_close > sma * 1.01] = "BULL"
    regime[nifty_close < sma * 0.99] = "BEAR"
    return regime


def _load_existing_keys(kel_path: Path) -> set[str]:
    """Return (symbol, trade_date, direction) keys already written."""
    existing: set[str] = set()
    if not kel_path.exists():
        return existing
    for line in kel_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("source") == SOURCE_TAG:
                key = f"{r.get('symbol','')}|{r.get('trade_date','')}|{r.get('direction','')}"
                existing.add(key)
        except Exception:
            pass
    return existing


def run() -> None:
    print(f"[HistoricalKnowledgeReplay] Starting — fetching {len(_WATCHLIST_NS)} symbols × 10y …")

    # ── Download all data in one batch ────────────────────────────────────────
    all_tickers = _WATCHLIST_NS + [_NIFTY_TICKER]
    raw = yf.download(
        tickers=all_tickers,
        period=FETCH_PERIOD,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw is None or raw.empty:
        raise SystemExit("[HistoricalKnowledgeReplay] yfinance returned empty data.")

    closes: pd.DataFrame = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    print(f"  Downloaded {len(closes)} trading days × {len(closes.columns)} tickers.")

    # ── Regime proxy from NIFTY50 ─────────────────────────────────────────────
    nifty_col = _NIFTY_TICKER if _NIFTY_TICKER in closes.columns else None
    if nifty_col:
        regime_s = _regime_series(closes[nifty_col].dropna())
        print(f"  Regime series computed. BULL={( regime_s=='BULL').sum()} RANGE={(regime_s=='RANGE').sum()} BEAR={(regime_s=='BEAR').sum()}")
    else:
        regime_s = None
        print("  WARNING: NIFTY data missing — regime will default to RANGE.")

    # ── Load existing keys (idempotency) ─────────────────────────────────────
    existing_keys = _load_existing_keys(KEL)
    print(f"  Existing replay records: {len(existing_keys)}")

    # ── Process each symbol ──────────────────────────────────────────────────
    written = 0
    skipped = 0

    with KEL.open("a", encoding="utf-8") as fout:
        for ns_sym in _WATCHLIST_NS:
            bare = ns_sym.replace(".NS", "")
            if ns_sym not in closes.columns:
                print(f"  SKIP {bare}: no data in download.")
                continue

            price = closes[ns_sym].dropna()
            if len(price) < RSI_PERIOD + 5:
                print(f"  SKIP {bare}: insufficient data ({len(price)} rows).")
                continue

            rsi_s = _rsi(price, RSI_PERIOD)
            sector = _SECTOR.get(bare, "UNKNOWN")

            sym_written = 0
            for i in range(RSI_PERIOD, len(price) - 1):   # -1 to allow T+1 outcome
                day_date  = price.index[i]
                next_date = price.index[i + 1]
                day_str   = str(day_date)[:10]

                rsi_val   = rsi_s.iloc[i]
                if pd.isna(rsi_val):
                    continue

                # Signal detection — purely RSI-based, no strategy label
                if rsi_val < BUY_RSI_MAX:
                    direction = "BUY"
                elif rsi_val > SELL_RSI_MIN:
                    direction = "SELL"
                else:
                    continue  # no signal

                # Skip if already written
                key = f"{bare}|{day_str}|{direction}"
                if key in existing_keys:
                    skipped += 1
                    continue

                # Outcome (T+1) — strictly future relative to signal day
                close_d  = float(price.iloc[i])
                close_d1 = float(price.iloc[i + 1])
                if close_d <= 0:
                    continue
                t1_ret = (close_d1 - close_d) / close_d * 100.0

                # ge2: was the directional call correct at T+1?
                ge2 = (t1_ret > 0.0) if direction == "BUY" else (t1_ret < 0.0)

                # v3_score: normalized signal strength
                if direction == "BUY":
                    v3 = round(max(0.0, min(1.0, (BUY_RSI_MAX - rsi_val) / BUY_RSI_MAX)), 4)
                else:
                    v3 = round(max(0.0, min(1.0, (rsi_val - SELL_RSI_MIN) / (100 - SELL_RSI_MIN))), 4)

                # Regime
                regime = "RANGE"
                if regime_s is not None and day_date in regime_s.index:
                    regime = regime_s.loc[day_date]

                record = {
                    "event_type":   "EVIDENCE",
                    "evidence_id":  str(uuid.uuid4()),
                    "symbol":       bare,
                    "trade_date":   day_str,
                    "direction":    direction,
                    "regime":       regime,
                    "sector":       sector,
                    "classification": f"RSI_{'OVERSOLD' if direction == 'BUY' else 'OVERBOUGHT'}",
                    "rsi_at_signal": round(float(rsi_val), 2),
                    "t1_ret_pct":   round(t1_ret, 4),
                    "ge2":          ge2,
                    "v3_score":     v3,
                    "no_lookahead": True,
                    "source":       SOURCE_TAG,
                    "recorded_at":  datetime.now(timezone.utc).isoformat(),
                }
                fout.write(json.dumps(record) + "\n")
                existing_keys.add(key)
                written   += 1
                sym_written += 1

            print(f"  {bare:14s}  wrote={sym_written:4d} records")

    print(f"\n[HistoricalKnowledgeReplay] Done. written={written} skipped={skipped}")
    print(f"  KEL path: {KEL}")
    print(f"  Total KEL lines now: {sum(1 for l in KEL.read_text().splitlines() if l.strip())}")


if __name__ == "__main__":
    run()

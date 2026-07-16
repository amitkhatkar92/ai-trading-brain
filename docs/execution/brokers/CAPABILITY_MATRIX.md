# Broker Capability Matrix

Complete reference of all `BrokerCapabilityCode` values, exchanges,
products, and time-in-force options defined by the Broker Abstraction Layer.

---

## Capabilities (`BrokerCapabilityCode`)

| Code | Value | Description |
|---|---|---|
| `MARKET_ORDER` | "MARKET_ORDER" | Submit market orders |
| `LIMIT_ORDER` | "LIMIT_ORDER" | Submit limit orders |
| `STOP_ORDER` | "STOP_ORDER" | Submit stop-loss orders |
| `STOP_LIMIT` | "STOP_LIMIT" | Submit stop-limit orders |
| `BRACKET_ORDER` | "BRACKET_ORDER" | Submit bracket orders (BO) |
| `COVER_ORDER` | "COVER_ORDER" | Submit cover orders (CO) |
| `AMO` | "AMO" | After-Market Orders |
| `GTT` | "GTT" | Good-Till-Triggered orders |
| `ICEBERG` | "ICEBERG" | Iceberg / disclosed-quantity orders |
| `BASKET` | "BASKET" | Basket / multi-leg orders |
| `PARTIAL_FILL` | "PARTIAL_FILL" | Handle partial fill events |
| `MARGIN` | "MARGIN" | Margin trading |
| `INTRADAY` | "INTRADAY" | Intraday MIS products |
| `PAPER_TRADING` | "PAPER_TRADING" | Simulated fills, no real money |
| `BACKTEST` | "BACKTEST" | Historical replay |
| `STREAMING` | "STREAMING" | Real-time market data stream |
| `HISTORICAL` | "HISTORICAL" | Historical OHLCV data |
| `MULTI_ACCOUNT` | "MULTI_ACCOUNT" | Sub-account or family-account support |

---

## Exchanges (`Exchange`)

| Code | Value | Market |
|---|---|---|
| `NSE` | "NSE" | National Stock Exchange, India |
| `BSE` | "BSE" | Bombay Stock Exchange, India |
| `NFO` | "NFO" | NSE Futures & Options |
| `BFO` | "BFO" | BSE Futures & Options |
| `MCX` | "MCX" | Multi Commodity Exchange |
| `CDS` | "CDS" | Currency Derivatives, NSE |
| `NYSE` | "NYSE" | New York Stock Exchange |
| `NASDAQ` | "NASDAQ" | NASDAQ |
| `CME` | "CME" | Chicago Mercantile Exchange |
| `BINANCE` | "BINANCE" | Binance crypto exchange |
| `UNKNOWN` | "UNKNOWN" | Unrecognised or unset |

---

## Product Types (`ProductType`)

| Code | Value | Description |
|---|---|---|
| `CNC` | "CNC" | Cash-and-Carry (delivery, equity) |
| `MIS` | "MIS" | Margin Intraday Square-off |
| `NRML` | "NRML" | Normal (F&O overnight carry-forward) |
| `CO` | "CO" | Cover Order |
| `BO` | "BO" | Bracket Order |
| `MTF` | "MTF" | Margin Trade Funding |
| `UNKNOWN` | "UNKNOWN" | Unrecognised or unset |

---

## Time-In-Force (`TimeInForce`)

| Code | Value | Description |
|---|---|---|
| `DAY` | "DAY" | Valid for the trading session |
| `IOC` | "IOC" | Immediate-or-Cancel |
| `FOK` | "FOK" | Fill-or-Kill |
| `GTC` | "GTC" | Good-Till-Cancelled |
| `GTT` | "GTT" | Good-Till-Triggered |
| `AT_OPEN` | "AT_OPEN" | Execute at market open |
| `AT_CLOSE` | "AT_CLOSE" | Execute at market close |

---

## Broker Modes (`BrokerMode`)

| Code | Value | Description |
|---|---|---|
| `LIVE` | "LIVE" | Real money, real exchange |
| `PAPER` | "PAPER" | Simulated fills, no real money |
| `SIMULATION` | "SIMULATION" | Replay historical data |
| `BACKTEST` | "BACKTEST" | Full backtest mode |

---

## Connection States (`BrokerConnectionState`)

| Code | Value | Description |
|---|---|---|
| `DISCONNECTED` | "DISCONNECTED" | Not connected |
| `CONNECTING` | "CONNECTING" | Connection in progress |
| `CONNECTED` | "CONNECTED" | Active connection |
| `RECONNECTING` | "RECONNECTING" | Auto-reconnect in progress |
| `DISCONNECTING` | "DISCONNECTING" | Graceful teardown in progress |
| `FAILED` | "FAILED" | Connection failed |

---

## Health Statuses (`BrokerHealthStatus`)

| Code | Value | Description |
|---|---|---|
| `HEALTHY` | "HEALTHY" | All systems nominal |
| `DEGRADED` | "DEGRADED" | Elevated latency or partial failure |
| `UNHEALTHY` | "UNHEALTHY" | System failure |
| `UNKNOWN` | "UNKNOWN" | Not yet checked |
| `INITIALISING` | "INITIALISING" | Starting up |

---

## Planned Adapter Capability Profiles

| Adapter | Order types | Exchanges | Products |
|---|---|---|---|
| Dhan | MARKET, LIMIT, STOP, AMO, GTT | NSE, BSE, NFO, BFO, MCX, CDS | CNC, MIS, NRML |
| Zerodha | MARKET, LIMIT, STOP, BRACKET, COVER, GTT | NSE, BSE, NFO, BFO, MCX, CDS | CNC, MIS, NRML, CO, BO |
| Interactive Brokers | MARKET, LIMIT, STOP, STOP_LIMIT, ICEBERG, BASKET | NYSE, NASDAQ, CME | CNC, NRML, MTF |
| Binance | MARKET, LIMIT, STOP, STOP_LIMIT | BINANCE | MIS, NRML |
| Paper Broker | All capabilities | All exchanges | All products |
| Backtest Broker | MARKET, LIMIT, STOP | NSE, BSE, NFO | CNC, MIS, NRML |

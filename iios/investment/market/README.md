# Market Intelligence Engine

**Package:** `iios/investment/market/`  
**Version:** 1.0.0  
**System ID:** `iios:market:engine`

---

## Overview

The Market Intelligence Engine is the primary market awareness subsystem of IIOS. It transforms raw market observations (prices, volumes, breadth, spreads) into structured `MarketIntelligence` objects that downstream engines consume.

**Scope:** Generic market intelligence framework. Does NOT implement trading signals, buy/sell decisions, or broker integrations.

---

## Architecture

```
MarketIntelligenceEngine   ← singleton entry-point
│
├── MarketManager          ← pipeline orchestrator
│   ├── MarketStateManager ← market lifecycle (open/close/halt)
│   ├── MarketStructureEngine
│   │   ├── TrendAnalyzer        ← linear-regression trend
│   │   ├── BreadthAnalyzer      ← advance/decline breadth
│   │   ├── VolatilityAnalyzer   ← realized annualized vol
│   │   ├── LiquidityAnalyzer    ← volume + spread scoring
│   │   └── CorrelationAnalyzer  ← pairwise Pearson correlation
│   └── MarketRegimeEngine
│       ├── RegimeClassifier (ABC)
│       ├── DefaultRegimeClassifier
│       └── RegimeHistory
│
├── MarketRegistry         ← pluggable component registry
├── MarketFactory          ← static object factories
└── MarketContext          ← thread-local session context
```

### Analysis Pipeline (per cycle)

1. Auto-register market if unknown
2. Build `MarketSnapshot` from raw inputs
3. `MarketStructureEngine.analyze()` → populates trend / vol / liquidity / breadth on snapshot
4. `MarketRegimeEngine.classify()` → reads dimensions from snapshot, produces `(MarketRegime, confidence)`
5. Compile `MarketIntelligence` with health scores, observations, opportunities, threats
6. Update statistics and history

---

## Quick Start

```python
from iios.investment.market import get_market_engine

engine = get_market_engine()
engine.initialize()

intel = engine.analyze(
    "NSE",
    prices   = {"RELIANCE": 2500.0, "TCS": 3800.0, "INFY": 1700.0},
    volumes  = {"RELIANCE": 5_000_000, "TCS": 3_000_000, "INFY": 4_000_000},
    changes  = {"RELIANCE": 0.012, "TCS": -0.005, "INFY": 0.008},
    advances = 1200,
    declines = 300,
)

print(intel.regime)           # MarketRegime.BULL
print(intel.trend)            # TrendDirection.UP
print(intel.market_health_score)  # 0–100
print(intel.opportunities)   # list[str]
```

---

## Subpackages

| Subpackage | Contents |
|---|---|
| `market_state/` | `MarketState`, `MarketSnapshot`, `MarketStateManager`, `MarketStatistics` |
| `regime/` | `RegimeClassifier`, `DefaultRegimeClassifier`, `MarketRegimeEngine`, `RegimeHistory`, `RegimeTransition` |
| `analytics/` | `TrendAnalyzer`, `BreadthAnalyzer`, `VolatilityAnalyzer`, `LiquidityAnalyzer`, `CorrelationAnalyzer`, `MarketStructureEngine` |
| `models/` | `MarketIntelligence`, `MarketHealth`, `MarketSummary`, `MarketSignal` |
| `microstructure/` | Future: order book, tick data |
| `breadth/` | Future: McClellan, TRIN |
| `liquidity/` | Future: funding, LOB depth |
| `volatility/` | Future: term structure, skew |
| `correlation/` | Future: DCC, copula |
| `sentiment/` | Future: news NLP, options sentiment |

---

## Regime Detection

The default classifier (`DefaultRegimeClassifier`) uses priority rules:

| Priority | Regime | Conditions |
|---|---|---|
| 1 | CRISIS | EXTREME vol + DOWN trend + VERY_NARROW breadth |
| 2 | BEAR | DOWN + NARROW/VERY_NARROW breadth |
| 3 | BULL | UP + BROAD/VERY_BROAD breadth |
| 4 | RECOVERY | UP + MODERATE breadth |
| 5 | HIGH_VOLATILITY | EXTREME or HIGH volatility |
| 6 | LOW_VOLATILITY | VERY_LOW volatility |
| 7 | EXPANSION | UP trend + LOW volatility |
| 8 | SIDEWAYS | SIDEWAYS trend |
| 9 | CONTRACTION | DOWN trend (residual) |
| 10 | UNKNOWN | fallback |

### Custom Classifier

```python
from iios.investment.market import MarketFactory, get_market_engine

clf = MarketFactory.make_function_classifier(
    "my_ml_classifier", "ML Regime Classifier",
    fn=lambda snapshot, history: (my_model.predict(snapshot), 0.85),
)
engine.register_classifier(clf, overwrite=True)
```

---

## Extending

### Custom Regime Classifier

```python
from iios.investment.market.regime.regime_classifier import RegimeClassifier
from iios.investment.market.market_constants import MarketRegime

class MyClassifier(RegimeClassifier):
    @property
    def classifier_id(self) -> str: return "my_classifier"
    @property
    def name(self) -> str: return "My Classifier"

    def classify(self, snapshot, history):
        # custom logic
        return MarketRegime.BULL, 0.80
```

### Custom Analyzer

```python
registry = get_market_registry()
registry.register_analyzer("my_analyzer", MyAnalyzer())
```

---

## Integration with Investment Intelligence Engine

```python
from iios.investment import get_investment_engine, IntelligenceType
from iios.investment.market import get_market_engine

inv_engine    = get_investment_engine()
market_engine = get_market_engine()

inv_engine.initialize()
market_engine.initialize()

# Register Market Intelligence Engine as domain engine
inv_engine.register_domain_engine(IntelligenceType.MARKET, market_engine)

# Future engines retrieve market intelligence
mie = registry.get_domain_engine(IntelligenceType.MARKET)
intel = mie.analyze("NSE", prices={"A": 100.0})
```

---

## Error Codes

All exceptions carry an `MI-` prefix code:

| Range | Domain |
|---|---|
| MI-010–MI-013 | Market State |
| MI-020–MI-023 | Regime |
| MI-030–MI-033 | Snapshot |
| MI-040–MI-042 | Analysis |
| MI-050–MI-052 | Engine Lifecycle |
| MI-060–MI-063 | Registry |
| MI-070–MI-073 | Data |

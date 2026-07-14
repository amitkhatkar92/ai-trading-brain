# Evidence Guide

## Evidence Sources

| Source | Used By Agent |
|---|---|
| `TECHNICAL_ANALYSIS` | TechnicalAnalystAgent |
| `FUNDAMENTAL_ANALYSIS` | FundamentalAnalystAgent |
| `MARKET_INTELLIGENCE` | MarketIntelligenceAgent |
| `COMPANY_INTELLIGENCE` | CompanyIntelligenceAgent |
| `MACRO_ANALYSIS` | MacroAnalystAgent |
| `RISK_INTELLIGENCE` | RiskAnalystAgent |
| `STRATEGY_INTELLIGENCE` | PortfolioAnalystAgent |
| `EXECUTION_ANALYSIS` | ExecutionAnalystAgent |
| `SENTIMENT_ANALYSIS` | SentimentAnalystAgent |
| `LEARNING_ENGINE`, `HISTORICAL_RESULTS` | StrategyLearningAgent |

## Creating Evidence

```python
from iios.investment.strategy.debate import (
    make_evidence, EvidenceSource, EvidenceReliability, EvidenceWeight,
)

ev = make_evidence(
    session_id="sid-001",
    source=EvidenceSource.TECHNICAL_ANALYSIS,
    category="momentum",
    title="RSI Oversold",
    description="RSI at 32 indicates potential reversal",
    raw_score=72.0,          # 0–100, >50 bullish, <50 bearish
    reliability=EvidenceReliability.HIGH,
    weight=EvidenceWeight.MEDIUM,
    relevance=0.85,          # 0–1 relevance to current opportunity
)
```

## Score Formula

```
weighted_score = raw_score × (0.40×reliability + 0.30×recency + 0.30×relevance) × weight_multiplier
```

Capped at 100.

| Component | Weight |
|---|---|
| Reliability | 40% |
| Recency (24h decay) | 30% |
| Relevance | 30% |

## EvidenceReliability

| Value | Score |
|---|---|
| `VERIFIED` | 1.0 |
| `HIGH` | 0.8 |
| `MEDIUM` | 0.6 |
| `LOW` | 0.4 |
| `UNVERIFIED` | 0.2 |

## EvidenceWeight Multipliers

| Value | Multiplier |
|---|---|
| `CRITICAL` | 3.0 |
| `HIGH` | 2.0 |
| `MEDIUM` | 1.0 |
| `LOW` | 0.5 |
| `INFORMATIONAL` | 0.25 |

## Pre-loading Evidence

Pass evidence directly in the `DebateContext` for offline scenarios:

```python
context = DebateContext(
    pre_loaded_evidence=[
        {
            "source":      "technical_analysis",
            "category":    "momentum",
            "title":       "RSI Signal",
            "description": "RSI oversold",
            "raw_score":   70.0,
            "reliability": "high",
            "weight":      "medium",
            "relevance":   0.8,
        }
    ]
)
```

## IIOS Integration

Provide adapters implementing the protocol interfaces:

```python
from iios.investment.strategy.debate import EvidenceCollector

class MyMarketAdapter:
    def get_market_summary(self, symbol: str) -> dict:
        return {"regime": "bullish", "vix": 14.0}

collector = EvidenceCollector(market_intelligence=MyMarketAdapter())
engine    = StrategyDebateEngine(evidence_collector=collector)
```

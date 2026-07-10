"""iios/integration/news/news_constants.py

All enumerations and module-level constants for the News & Alternative Data Framework.
Error code prefix: ND-
"""
from __future__ import annotations

from enum import Enum, IntEnum


# ── News classification ───────────────────────────────────────────────────────

class NewsCategory(str, Enum):
    EARNINGS         = "earnings"
    DIVIDEND         = "dividend"
    MERGER_ACQ       = "merger_acquisition"
    IPO              = "ipo"
    SPINOFF          = "spinoff"
    RESTRUCTURING    = "restructuring"
    CORPORATE        = "corporate"
    MACRO_ECONOMIC   = "macro_economic"
    CENTRAL_BANK     = "central_bank"
    INTEREST_RATES   = "interest_rates"
    INFLATION        = "inflation"
    GDP              = "gdp"
    EMPLOYMENT       = "employment"
    GEOPOLITICS      = "geopolitics"
    REGULATORY       = "regulatory"
    LEGAL            = "legal"
    COMMODITIES      = "commodities"
    ENERGY           = "energy"
    TECHNOLOGY       = "technology"
    HEALTHCARE       = "healthcare"
    FINANCIAL        = "financial"
    MARKETS          = "markets"
    CRYPTO           = "crypto"
    ESG              = "esg"
    ANALYST_UPGRADE  = "analyst_upgrade"
    ANALYST_DOWNGRADE = "analyst_downgrade"
    PRODUCT_LAUNCH   = "product_launch"
    MANAGEMENT_CHANGE = "management_change"
    INSIDER_TRADING  = "insider_trading"
    SEC_FILING       = "sec_filing"
    GENERAL          = "general"
    UNKNOWN          = "unknown"


class NewsImportance(IntEnum):
    """Numerical rank — higher = more important."""
    MINIMAL  = 1
    LOW      = 2
    MEDIUM   = 3
    HIGH     = 4
    CRITICAL = 5


class NewsUrgency(str, Enum):
    BREAKING  = "breaking"     # live, requires immediate attention
    URGENT    = "urgent"       # < 15 min old
    NORMAL    = "normal"       # standard delivery
    SCHEDULED = "scheduled"    # future-dated event
    DELAYED   = "delayed"      # arrived with latency


class NewsLanguage(str, Enum):
    EN = "en"   # English
    HI = "hi"   # Hindi
    ZH = "zh"   # Chinese
    JA = "ja"   # Japanese
    DE = "de"   # German
    FR = "fr"   # French
    ES = "es"   # Spanish
    KO = "ko"   # Korean
    PT = "pt"   # Portuguese
    AR = "ar"   # Arabic
    UNKNOWN = "unknown"


class NewsRegion(str, Enum):
    GLOBAL          = "global"
    NORTH_AMERICA   = "north_america"
    LATIN_AMERICA   = "latin_america"
    EUROPE          = "europe"
    MIDDLE_EAST     = "middle_east"
    AFRICA          = "africa"
    ASIA_PACIFIC    = "asia_pacific"
    INDIA           = "india"
    CHINA           = "china"
    JAPAN           = "japan"
    UNKNOWN         = "unknown"


# ── Sentiment ─────────────────────────────────────────────────────────────────

class SentimentLabel(str, Enum):
    VERY_BULLISH = "very_bullish"   # strong positive
    BULLISH      = "bullish"        # positive
    NEUTRAL      = "neutral"        # no directional bias
    BEARISH      = "bearish"        # negative
    VERY_BEARISH = "very_bearish"   # strong negative
    UNKNOWN      = "unknown"        # not yet analysed


# ── Events ────────────────────────────────────────────────────────────────────

class NewsEventType(str, Enum):
    EARNINGS_RELEASE    = "earnings_release"
    EARNINGS_GUIDANCE   = "earnings_guidance"
    DIVIDEND_ANNOUNCE   = "dividend_announce"
    MERGER_ANNOUNCE     = "merger_announce"
    ACQUISITION         = "acquisition"
    IPO_ANNOUNCE        = "ipo_announce"
    IPO_PRICING         = "ipo_pricing"
    BOND_ISSUANCE       = "bond_issuance"
    SHARE_BUYBACK       = "share_buyback"
    MANAGEMENT_CHANGE   = "management_change"
    REGULATORY_ACTION   = "regulatory_action"
    COURT_RULING        = "court_ruling"
    CENTRAL_BANK_MEETING = "central_bank_meeting"
    RATE_DECISION       = "rate_decision"
    ECONOMIC_RELEASE    = "economic_release"
    PRODUCT_LAUNCH      = "product_launch"
    PARTNERSHIP         = "partnership"
    ANALYST_RATING      = "analyst_rating"
    INSIDER_TRADE       = "insider_trade"
    SEC_FILING          = "sec_filing"
    HALT                = "halt"
    GENERAL_NEWS        = "general_news"
    UNKNOWN             = "unknown"


class EventImpact(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


# ── Alternative Data ──────────────────────────────────────────────────────────

class AlternativeDataType(str, Enum):
    SOCIAL_MEDIA       = "social_media"
    ANALYST_REPORT     = "analyst_report"
    ECONOMIC_CALENDAR  = "economic_calendar"
    CORPORATE_FILING   = "corporate_filing"
    SATELLITE_DATA     = "satellite_data"
    SHIPPING_DATA      = "shipping_data"
    WEATHER_DATA       = "weather_data"
    SUPPLY_CHAIN       = "supply_chain"
    ESG_DATA           = "esg_data"
    SEARCH_TRENDS      = "search_trends"
    CONSUMER_TRENDS    = "consumer_trends"
    WEB_TRAFFIC        = "web_traffic"
    APP_DOWNLOADS      = "app_downloads"
    CREDIT_CARD_DATA   = "credit_card_data"
    PATENT_FILINGS     = "patent_filings"
    JOB_POSTINGS       = "job_postings"
    FOOT_TRAFFIC       = "foot_traffic"
    INSIDER_DATA       = "insider_data"
    OPTIONS_FLOW       = "options_flow"
    DARK_POOL          = "dark_pool"
    CUSTOM             = "custom"


# ── Provider ──────────────────────────────────────────────────────────────────

class NewsProviderStatus(str, Enum):
    DISCONNECTED  = "disconnected"
    CONNECTING    = "connecting"
    CONNECTED     = "connected"
    STREAMING     = "streaming"
    DEGRADED      = "degraded"
    RECONNECTING  = "reconnecting"
    FAILED        = "failed"
    SHUTTING_DOWN = "shutting_down"


# ── Engine ────────────────────────────────────────────────────────────────────

class NewsEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Sentiment scope ───────────────────────────────────────────────────────────

class SentimentScope(str, Enum):
    NEWS     = "news"
    COMPANY  = "company"
    SECTOR   = "sector"
    MARKET   = "market"
    SOCIAL   = "social"
    COMPOSITE = "composite"


# ── Module metadata ───────────────────────────────────────────────────────────

NEWS_ENGINE_VERSION      = "1.0.0"
NEWS_ENGINE_SYSTEM_ID    = "iios:integration:news:engine"
NEWS_ERROR_PREFIX        = "ND"

# Limits
DEFAULT_MAX_PROVIDERS          = 100
DEFAULT_MAX_ARTICLE_BODY_CHARS = 100_000   # truncate bodies over this
DEFAULT_MAX_TAGS               = 50
DEFAULT_DEDUP_WINDOW           = 100_000   # articles in rolling dedup set
DEFAULT_CLASSIFICATION_BATCH   = 50        # articles per classify batch

# Timeouts
DEFAULT_FETCH_TIMEOUT_SEC      = 30.0
DEFAULT_CONNECT_TIMEOUT_SEC    = 15.0
DEFAULT_STREAM_BUFFER_SIZE     = 5_000

# Quality thresholds
MIN_ARTICLE_TITLE_LEN          = 5
MIN_ARTICLE_BODY_LEN           = 10
DEFAULT_STALE_ARTICLE_SEC      = 86_400   # 24 hours

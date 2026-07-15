"""tests/unit/investment/portfolio/risk/conftest.py

Shared pytest fixtures for Portfolio Risk Engine tests.
"""
import pytest

from iios.investment.portfolio.risk.risk_types import RiskPosition


# ---------------------------------------------------------------------------
# Position fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pos_equity_tech() -> RiskPosition:
    return RiskPosition(
        symbol="TCS",
        weight=0.15,
        sector="technology",
        industry="it_services",
        asset_class="equity",
        country="IN",
        currency="INR",
        risk_score=0.55,
        conviction=0.8,
        confidence=0.75,
        liquidity=0.9,
        credit_quality=0.8,
    )


@pytest.fixture
def pos_equity_bank() -> RiskPosition:
    return RiskPosition(
        symbol="HDFCBANK",
        weight=0.12,
        sector="finance",
        industry="banking",
        asset_class="equity",
        country="IN",
        currency="INR",
        risk_score=0.45,
        conviction=0.7,
        confidence=0.70,
        liquidity=0.85,
        credit_quality=0.85,
    )


@pytest.fixture
def pos_bond() -> RiskPosition:
    return RiskPosition(
        symbol="GSEC10Y",
        weight=0.20,
        sector="government",
        industry="sovereign_debt",
        asset_class="bond",
        country="IN",
        currency="INR",
        risk_score=0.15,
        conviction=0.6,
        confidence=0.80,
        liquidity=0.95,
        credit_quality=0.95,
    )


@pytest.fixture
def pos_intl() -> RiskPosition:
    return RiskPosition(
        symbol="AAPL",
        weight=0.10,
        sector="technology",
        industry="consumer_electronics",
        asset_class="equity",
        country="US",
        currency="USD",
        risk_score=0.50,
        conviction=0.75,
        confidence=0.70,
        liquidity=0.95,
        credit_quality=0.90,
    )


@pytest.fixture
def pos_illiquid() -> RiskPosition:
    return RiskPosition(
        symbol="SMALLCAP1",
        weight=0.08,
        sector="consumer_discretionary",
        industry="retail",
        asset_class="equity",
        country="IN",
        currency="INR",
        risk_score=0.75,
        conviction=0.5,
        confidence=0.55,
        liquidity=0.20,
        credit_quality=0.55,
    )


@pytest.fixture
def positions_5_diverse(
    pos_equity_tech, pos_equity_bank, pos_bond, pos_intl, pos_illiquid
):
    """5 diverse positions summing to 0.65 weight — realistic."""
    return [pos_equity_tech, pos_equity_bank, pos_bond, pos_intl, pos_illiquid]


@pytest.fixture
def positions_3_concentrated():
    """3 highly concentrated positions (one sector)."""
    return [
        RiskPosition(
            symbol="RELIANCE",
            weight=0.50,
            sector="energy",
            industry="oil_gas",
            asset_class="equity",
            country="IN",
            currency="INR",
            risk_score=0.60,
            conviction=0.9,
            confidence=0.8,
            liquidity=0.85,
            credit_quality=0.80,
        ),
        RiskPosition(
            symbol="ONGC",
            weight=0.30,
            sector="energy",
            industry="oil_gas",
            asset_class="equity",
            country="IN",
            currency="INR",
            risk_score=0.55,
            conviction=0.7,
            confidence=0.7,
            liquidity=0.80,
            credit_quality=0.75,
        ),
        RiskPosition(
            symbol="BPCL",
            weight=0.20,
            sector="energy",
            industry="oil_refining",
            asset_class="equity",
            country="IN",
            currency="INR",
            risk_score=0.58,
            conviction=0.65,
            confidence=0.65,
            liquidity=0.75,
            credit_quality=0.72,
        ),
    ]


@pytest.fixture
def positions_bond_heavy():
    """Bond-heavy portfolio for interest rate risk testing."""
    return [
        RiskPosition(
            symbol="GSEC10Y",
            weight=0.40,
            sector="government",
            industry="sovereign",
            asset_class="bond",
            country="IN",
            currency="INR",
            risk_score=0.10,
            conviction=0.9,
            confidence=0.95,
            liquidity=0.99,
            credit_quality=0.99,
        ),
        RiskPosition(
            symbol="CORPBOND",
            weight=0.30,
            sector="corporate",
            industry="corporate_debt",
            asset_class="fixed_income",
            country="IN",
            currency="INR",
            risk_score=0.20,
            conviction=0.75,
            confidence=0.80,
            liquidity=0.70,
            credit_quality=0.80,
        ),
        RiskPosition(
            symbol="NIFTY50",
            weight=0.30,
            sector="diversified",
            industry="index",
            asset_class="equity",
            country="IN",
            currency="INR",
            risk_score=0.40,
            conviction=0.70,
            confidence=0.70,
            liquidity=0.95,
            credit_quality=0.85,
        ),
    ]


@pytest.fixture
def positions_intl_heavy():
    """FX-heavy portfolio for currency risk testing."""
    return [
        RiskPosition(
            symbol="AAPL",
            weight=0.25,
            sector="technology",
            industry="consumer_electronics",
            asset_class="equity",
            country="US",
            currency="USD",
            risk_score=0.45,
            conviction=0.8,
            confidence=0.80,
            liquidity=0.95,
            credit_quality=0.90,
        ),
        RiskPosition(
            symbol="MSFT",
            weight=0.20,
            sector="technology",
            industry="software",
            asset_class="equity",
            country="US",
            currency="USD",
            risk_score=0.40,
            conviction=0.85,
            confidence=0.85,
            liquidity=0.95,
            credit_quality=0.92,
        ),
        RiskPosition(
            symbol="HDFC",
            weight=0.30,
            sector="finance",
            industry="banking",
            asset_class="equity",
            country="IN",
            currency="INR",
            risk_score=0.40,
            conviction=0.75,
            confidence=0.75,
            liquidity=0.90,
            credit_quality=0.85,
        ),
        RiskPosition(
            symbol="EUSTOCK",
            weight=0.25,
            sector="diversified",
            industry="etf",
            asset_class="equity",
            country="DE",
            currency="EUR",
            risk_score=0.45,
            conviction=0.65,
            confidence=0.65,
            liquidity=0.85,
            credit_quality=0.85,
        ),
    ]


@pytest.fixture
def single_position():
    return [
        RiskPosition(
            symbol="NIFTY",
            weight=1.0,
            sector="diversified",
            industry="index",
            asset_class="equity",
            country="IN",
            currency="INR",
            risk_score=0.40,
            conviction=0.70,
            confidence=0.70,
            liquidity=0.95,
            credit_quality=0.85,
        )
    ]


# Duck-typed plan fixture for engine tests
class _MockPlan:
    def __init__(self, positions):
        self.plan_id       = "test-plan-001"
        self.allocation_id = "alloc-001"
        self._positions    = positions

    @property
    def positions(self):
        return self._positions


@pytest.fixture
def mock_plan_diverse(positions_5_diverse):
    return _MockPlan(positions_5_diverse)


@pytest.fixture
def mock_plan_concentrated(positions_3_concentrated):
    return _MockPlan(positions_3_concentrated)

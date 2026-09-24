# conftest.py -- IIOS Shared Test Configuration
# Fixtures available to all test suites.
# Foundation: IIOS-FCR-001 (CERTIFIED)

# Force numpy to initialise fully before any test runs.
# This prevents a circular-import AttributeError in pytest.approx()
# triggered by certain test-file orderings on Python 3.14 + numpy 2.x.
try:
    import numpy as _np  # noqa: F401
    _ = _np.isscalar  # exercise the attribute that triggers the bug
except Exception:
    pass

# Force pandas/yfinance to initialise fully before any test runs. Self-
# learning #31/#32's non-blocking background-worker acquisition modules
# (company_growth_signal.py, corporate_event_signal.py) import yfinance
# from a spawned daemon thread; if that thread's first-ever `import
# yfinance` races against a LATER test's own `import yfinance` on the
# main thread, pandas's Cython extension modules can end up partially
# initialised ("AttributeError: partially initialized module 'pandas'").
# Same root cause class as the numpy guard above -- pre-import here so
# it's already fully loaded in sys.modules before any thread touches it.
try:
    import pandas as _pd  # noqa: F401
    import yfinance as _yf  # noqa: F401
except Exception:
    pass

import pytest

# --- Shared fixtures (implement in Wave 1) ---

# @pytest.fixture(scope='session')
# def iios_config():
#     from enterprise_ai_platform.config.config_service import ConfigurationService
#     return ConfigurationService.get_snapshot()

# @pytest.fixture(scope='session')
# def iios_container():
#     from enterprise_ai_platform.infrastructure.configuration.di_container import DIContainer
#     return DIContainer.instance()

# @pytest.fixture
# def mock_clock():
#     from enterprise_ai_platform.infrastructure.platform.clock_service import FakeClock
#     return FakeClock()

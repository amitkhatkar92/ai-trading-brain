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

import pytest

# --- Shared fixtures (implement in Wave 1) ---

# @pytest.fixture(scope='session')
# def iios_config():
#     from iios.config.config_service import ConfigurationService
#     return ConfigurationService.get_snapshot()

# @pytest.fixture(scope='session')
# def iios_container():
#     from iios.infrastructure.configuration.di_container import DIContainer
#     return DIContainer.instance()

# @pytest.fixture
# def mock_clock():
#     from iios.infrastructure.platform.clock_service import FakeClock
#     return FakeClock()

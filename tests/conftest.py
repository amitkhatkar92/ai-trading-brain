# conftest.py -- IIOS Shared Test Configuration
# Fixtures available to all test suites.
# Foundation: IIOS-FCR-001 (CERTIFIED)

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

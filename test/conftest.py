from brandizpyes.logging import logger_config
import os

import pytest

"""
Pytest configuration file, which the framework picks up at startup.

[Details here](https://docs.pytest.org/en/stable/reference/fixtures.html)

"""
def pytest_configure ( config: pytest.Config ):
	"""
	Configures various pytest settings:

	* markers for tests
	* Logging
	"""

	config.addinivalue_line (
		"markers", "integration: Integration test marker."
	)

	# Utility to setup logging from YAML
	cfg_path = os.path.dirname ( __file__ ) + "/resources/logging-test.yml"
	logger_config ( __name__, cfg_path = cfg_path )

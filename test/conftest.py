import os
import logging.config

import pytest
import yaml

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

	# Setup logging from YAML config file
	cfg_path = os.path.join(os.path.dirname(__file__), "resources/logging-test.yml")
	with open(cfg_path) as f:
		config = yaml.safe_load(f)
	logging.config.dictConfig(config)
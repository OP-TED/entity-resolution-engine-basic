SHELL=/bin/bash -o pipefail

#
# ERE Makefile: Developer-friendly interface for testing & quality assurance
#
# This Makefile provides quick, discoverable targets for common development tasks.
# It uses your active Poetry environment for fast feedback during development.
#
# For CI/CD: Use `tox` (see tox.ini) for reproducible, isolated test environments.
# tox is independent of Poetry and manages its own dependencies in CI.
#
# Three-environment model (Cosmic Python / Clean Code):
#   make test-unit              → pytest + coverage (your venv, fast)
#   make lint                   → pylint checks (your venv, fast)
#   make check-clean-code       → tox isolated: pylint + radon + xenon
#   make check-architecture     → tox isolated: import-linter
#   make all-quality-checks     → full pipeline: lint + architecture + clean-code
#
# For CI/CD in GitHub Actions:
#   tox -e py312,architecture,clean-code
#

BUILD_PRINT = \e[1;34m
END_BUILD_PRINT = \e[0m

PROJECT_PATH = $(shell pwd)
SRC_PATH = ${PROJECT_PATH}/src
TEST_PATH = ${PROJECT_PATH}/test
BUILD_PATH = ${PROJECT_PATH}/dist
INFRA_PATH = ${PROJECT_PATH}/infra
PACKAGE_NAME = ere

ICON_DONE = [✔]
ICON_ERROR = [x]
ICON_WARNING = [!]
ICON_PROGRESS = [-]

#-----------------------------------------------------------------------------
# Dev commands
#-----------------------------------------------------------------------------
.PHONY: help install-poetry install build
help: ## Display available targets
	@ echo -e "$(BUILD_PRINT)Available targets:$(END_BUILD_PRINT)"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Development:$(END_BUILD_PRINT)"
	@ echo "    install              - Install project dependencies via Poetry"
	@ echo "    install-poetry       - Install Poetry if not present"
	@ echo "    build                - Build the package distribution"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Testing:$(END_BUILD_PRINT)"
	@ echo "    test                 - Run all tests"
	@ echo "    test-unit            - Run unit tests with coverage (fast, your venv)"
	@ echo "    test-integration     - Run integration tests only"
	@ echo "    test-coverage        - Generate HTML coverage report"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Code Quality (Developer):$(END_BUILD_PRINT)"
	@ echo "    format               - Format code with Ruff"
	@ echo "    lint                 - Run pylint checks (your venv, fast)"
	@ echo "    lint-fix             - Auto-fix with Ruff"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Code Quality (CI/Isolated):$(END_BUILD_PRINT)"
	@ echo "    check-clean-code     - Clean-code checks: pylint + radon + xenon (tox)"
	@ echo "    check-architecture   - Validate layer contracts (tox)"
	@ echo "    all-quality-checks   - Run all quality checks"
	@ echo "    ci                   - Full CI pipeline for GitHub Actions"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Infrastructure (Docker):$(END_BUILD_PRINT)"
	@ echo "    infra-build          - Build the ERE Docker image"
	@ echo "    infra-up             - Start full stack (Redis + ERE) in detached mode"
	@ echo "    infra-down           - Stop and remove stack containers and networks"
	@ echo "    infra-logs           - Tail ERE container logs"
	@ echo ""
	@ echo -e "  $(BUILD_PRINT)Utilities:$(END_BUILD_PRINT)"
	@ echo "    clean                - Remove build artifacts and caches"
	@ echo "    help                 - Display this help message"
	@ echo ""

install-poetry: ## Install Poetry if not present
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Installing Poetry $(END_BUILD_PRINT)"
	@ pip install "poetry>=2.0.0"
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Poetry is installed$(END_BUILD_PRINT)"

install: install-poetry ## Install project dependencies
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Installing ERE requirements$(END_BUILD_PRINT)"
	@ poetry lock
	@ poetry install --with dev
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) ERE requirements are installed$(END_BUILD_PRINT)"

build: ## Build the package distribution
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Building package$(END_BUILD_PRINT)"
	@ poetry build
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Package built successfully$(END_BUILD_PRINT)"

#-----------------------------------------------------------------------------
# Testing commands
#-----------------------------------------------------------------------------
.PHONY: test test-unit test-integration test-coverage
test: ## Run all tests
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running all tests$(END_BUILD_PRINT)"
	@ poetry run pytest $(TEST_PATH)
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) All tests passed$(END_BUILD_PRINT)"

test-unit: ## Run unit tests with coverage (fast, uses your venv)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running unit tests with coverage$(END_BUILD_PRINT)"
	@ poetry run pytest $(TEST_PATH) -m "not integration" \
	    --cov=src --cov-report=term-missing --cov-report=html
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Unit tests passed (coverage: htmlcov/index.html)$(END_BUILD_PRINT)"

test-integration: ## Run integration tests only
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running integration tests$(END_BUILD_PRINT)"
	@ poetry run pytest $(TEST_PATH) -m "integration"
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Integration tests passed$(END_BUILD_PRINT)"

test-coverage: ## Generate detailed HTML coverage report
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Generating coverage report$(END_BUILD_PRINT)"
	@ poetry run pytest $(TEST_PATH) -m "not integration" \
	    --cov=src --cov-report=html --cov-report=term-missing
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Coverage report: htmlcov/index.html$(END_BUILD_PRINT)"

#-----------------------------------------------------------------------------
# Code quality commands
#-----------------------------------------------------------------------------
.PHONY: format lint lint-fix check-clean-code check-architecture all-quality-checks ci

format: ## Format code with Ruff
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Formatting code$(END_BUILD_PRINT)"
	@ poetry run ruff format $(SRC_PATH) $(TEST_PATH)
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Format complete$(END_BUILD_PRINT)"

lint: ## Run pylint checks (style, naming, SOLID principles) — uses your venv
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running pylint checks$(END_BUILD_PRINT)"
	@ poetry run pylint --rcfile=.pylintrc ./src ./test
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Pylint checks passed$(END_BUILD_PRINT)"

lint-fix: ## Auto-fix code style with Ruff
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Auto-fixing with Ruff$(END_BUILD_PRINT)"
	@ poetry run ruff check --fix $(SRC_PATH) $(TEST_PATH)
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Auto-fix complete$(END_BUILD_PRINT)"

check-clean-code: ## Clean-code checks: pylint + radon + xenon (isolated tox)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running clean-code checks (tox isolated)$(END_BUILD_PRINT)"
	@ tox -e clean-code
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Clean-code checks passed$(END_BUILD_PRINT)"

check-architecture: ## Validate architectural boundaries (isolated tox)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Checking architecture contracts (tox isolated)$(END_BUILD_PRINT)"
	@ tox -e architecture
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Architecture checks passed$(END_BUILD_PRINT)"

all-quality-checks: lint check-clean-code check-architecture ## Run all: lint + clean-code + architecture
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) All quality checks passed!$(END_BUILD_PRINT)"

ci: ## Full CI pipeline for GitHub Actions (tox)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Running full CI pipeline$(END_BUILD_PRINT)"
	@ tox -e py312,architecture,clean-code
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) CI pipeline complete$(END_BUILD_PRINT)"

#-----------------------------------------------------------------------------
# Infrastructure commands (Docker)
#-----------------------------------------------------------------------------
.PHONY: infra-build infra-up infra-down infra-logs

infra-build: ## Build the ERE Docker image
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Building ERE Docker image$(END_BUILD_PRINT)"
	@ docker compose -f $(INFRA_PATH)/docker-compose.yml build
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) ERE image built$(END_BUILD_PRINT)"

infra-up: ## Start full stack: Redis + ERE (docker compose up --build)
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Starting ERE stack$(END_BUILD_PRINT)"
	@ docker compose -f $(INFRA_PATH)/docker-compose.yml up --build -d
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) ERE stack is running — use 'make infra-logs' to follow output$(END_BUILD_PRINT)"

infra-down: ## Stop and remove ERE stack containers and networks
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Stopping ERE stack$(END_BUILD_PRINT)"
	@ docker compose -f $(INFRA_PATH)/docker-compose.yml down
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) ERE stack stopped$(END_BUILD_PRINT)"

infra-logs: ## Tail logs from the ERE container
	@ docker compose -f $(INFRA_PATH)/docker-compose.yml logs -f ere

#-----------------------------------------------------------------------------
# Utility commands
#-----------------------------------------------------------------------------
.PHONY: clean
clean: ## Remove build artifacts and caches
	@ echo -e "$(BUILD_PRINT)$(ICON_PROGRESS) Cleaning build artifacts and caches$(END_BUILD_PRINT)"
	@ rm -rf $(BUILD_PATH)
	@ rm -rf .pytest_cache
	@ rm -rf .tox
	@ rm -rf *.egg-info
	@ rm -rf htmlcov coverage.xml
	@ poetry run ruff clean
	@ find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@ find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@ find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@ echo -e "$(BUILD_PRINT)$(ICON_DONE) Clean complete$(END_BUILD_PRINT)"

# Default target
.DEFAULT_GOAL := help

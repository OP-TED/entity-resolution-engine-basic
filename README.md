# basic-ere
A basic implementation of the Entity Resolution Engine (ERE).

## Requirements
TODO. For testing, you need: Python, Poetry, Docker (used by pytest + testcontainers).

## Make targets overview

Run `make` or `make help` to see all available targets.

**Development:**
- `make install` - Install project dependencies via Poetry
- `make install-poetry` - Install Poetry if not present
- `make build` - Build the package distribution

**Testing:**
- `make test` - Run all tests
- `make test-unit` - Run unit tests only (exclude integration)
- `make test-integration` - Run integration tests only

**Code Quality:**
- `make format` - Format code with Ruff
- `make lint-check` - Run Ruff linting checks
- `make lint-fix` - Run Ruff checks with auto-fix

**Utilities:**
- `make clean` - Remove build artifacts and caches

## TODO
* Complete this hereby README
* CLI wrapper to start the Redis service
* Dockerisation
* github action for test, build, and linting.

## TODO: Resolver implementation

See the dedicated shape and [here](docs/resolution-tools.md).

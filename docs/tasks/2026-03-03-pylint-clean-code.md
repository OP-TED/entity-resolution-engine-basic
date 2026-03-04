# Task: Fix pylint clean-code issues (non-E0401)

**Date:** 2026-03-03
**Status:** In Progress
**Branch:** feature/ERS1-124/implement-ere

## Objective
Raise pylint clean-code score from 6.55/10 by fixing ~80 warnings across 20 files.
All `E0401` import errors are environment noise (packages unavailable in linter venv) — skip them.

## Scope
- **Files:** 20 source/test files in `src/` and `test/`
- **Categories:** 13 (W1203, C0413/C0411, W1514, W2301, W0622, R1735, W0612, C0104, R0917, W0718, W0212, R1714/C0206, W0105)
- **Excluded:** W0621 (pytest fixtures), W0611 (unused in integration tests), E1101 (future Python 3.13)

## Acceptance Criteria
- [ ] Pylint score > 7.5/10
- [ ] All non-E0401 warnings addressed per plan
- [ ] All tests pass (unit + BDD)
- [ ] No regressions in CI/layer boundaries

## Slices & Progress

### Slice 1: W1203 — Logging f-strings → lazy % formatting
**Status:** TODO
**Files:** `services/__init__.py`, `services/redis.py`, `entrypoints/queue_worker.py`, `entrypoints/app.py`, `adapters/redis.py`, `utils/logging.py`

### Slice 2: C0413/C0411 — Import ordering & positioning
**Status:** TODO
**Files:** `services/entity_resolution_service.py`, `services/__init__.py`, `services/redis.py`, `entrypoints/queue_worker.py`, `adapters/redis.py`, `adapters/splink_linker_impl.py`, `test/adapters/stubs.py`

### Slice 3: W1514 — open() missing encoding
**Status:** TODO
**Files:** `services/factories.py`, `adapters/rdf_mapper.py`, `test/conftest.py`

### Slice 4: W2301 — Unnecessary ellipsis in abstract methods
**Status:** TODO
**Files:** `adapters/repositories.py`, `adapters/rdf_mapper_port.py`, `models/ports/linker.py`

### Slice 5: W0622 — Redefining built-in (ConnectionError, TimeoutError)
**Status:** TODO
**Files:** `adapters/redis.py`

### Slice 6: R1735 — Use dict literal instead of dict()
**Status:** TODO
**Files:** `adapters/splink_linker_impl.py`

### Slice 7: W0612 — Unused variables
**Status:** TODO
**Files:** `adapters/splink_linker_impl.py`

### Slice 8: C0104 — Disallowed names
**Status:** TODO
**Files:** `services/entity_resolution_service.py`, `entrypoints/queue_worker.py`, `adapters/duckdb_repositories.py`, `adapters/splink_linker_impl.py`, `adapters/utils.py`, `models/resolver/ids.py`, `models/resolver/mention.py`, `utils/__init__.py`
**Note:** Also update `.pylintrc` to add `value` to `good-names`

### Slice 9: R0917 — Too many positional arguments
**Status:** DEFERRED
**Note:** Scheduled for follow-up; too large for current scope

### Slice 10: W0718 — Broad exception caught
**Status:** TODO
**Files:** `services/entity_resolution_service.py`, `entrypoints/queue_worker.py`, `entrypoints/app.py`, `adapters/splink_linker_impl.py`

### Slice 11: W0212 — Protected member access
**Status:** TODO
**Files:** `adapters/splink_linker_impl.py`, `utils/logging.py`, `entrypoints/app.py`

### Slice 12: Style improvements (R1714, C0206)
**Status:** TODO
**Files:** `test/adapters/stubs.py`

### Slice 13: W0105 — String statement (module docstring)
**Status:** TODO
**Files:** `test/conftest.py`

## Notes

- Each slice should be self-contained and testable.
- Run `make check-clean-code` after each category to verify progress.
- Commit after completing a category.
- No changes to layer boundaries or architecture.

## Changes Log

(To be updated as work progresses)


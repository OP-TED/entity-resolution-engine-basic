# ERE — Agent Operating Instructions

This file governs how AI agents operate in this repository.
It complements `CLAUDE.md` (which governs Claude Code specifically) and `.claude/CLAUDE.md` (project instructions).

---

## Commits and PRs

- **Never auto-commit** unless the user explicitly asks.
- **Never force-push** to `main` or `develop`.
- **Never add co-author lines**, tool names, or agent names to commit messages.
- Commit format: `type(scope): concise description` — e.g. `feat(adapters): add splink resolver factory`.
- Stage only files you modified: `git add <file>`, never `git add -A` blindly.
- Before committing, run `make lint` and `make test-unit` to verify nothing is broken.
- PRs target `develop` (not `main`) unless told otherwise.
- When creating a PR, include a short summary and a test-plan checklist.

---

## Working Methodology

### Before touching code

1. Read `WORKING.md` — it points to the active task file.
2. Read the referenced `docs/tasks/yyyy-mm-dd-*.md` fully.
3. Understand the current branch state: `git log --oneline -10`.

### Running the stack for integration tests

Integration tests require Redis to be running. Start it first:

```bash
make infra-up          # starts Redis + RedisInsight via Docker Compose
make test-integration  # then run integration tests
make infra-down        # tear down when done
```

Unit tests do **not** require any infrastructure:

```bash
make test-unit         # fast, self-contained, uses your venv
```

### Typical development loop

```bash
make install           # first time or after pyproject.toml changes
make test-unit         # red → green → refactor
make lint              # quick style check
make check-architecture  # verify import-linter contracts
make all-quality-checks  # before opening a PR
```

---

## Tooling Reference

| Target | What it does |
|--------|-------------|
| `make install` | Install deps via Poetry |
| `make test-unit` | pytest unit suite + coverage report |
| `make test-integration` | integration tests (Redis must be up) |
| `make test-coverage` | HTML coverage report → `htmlcov/index.html` |
| `make lint` | pylint (fast, your venv) |
| `make format` | Ruff formatter |
| `make lint-fix` | Ruff auto-fix |
| `make check-clean-code` | pylint + radon + xenon (tox isolated) |
| `make check-architecture` | import-linter contracts (tox isolated) |
| `make all-quality-checks` | lint + clean-code + architecture |
| `make ci` | full tox pipeline (py312 + architecture + clean-code) |
| `make infra-up` | Start Redis stack (Docker Compose) |
| `make infra-down` | Stop Redis stack |
| `make infra-watch` | Live-reload mode (syncs `src/` and `src/config/`) |

---

## Architecture Rules (enforced by import-linter)

Dependency direction must never be violated:

```
entrypoints → services → models
                       ↘
                       adapters → models
```

- `models/` — no I/O, no framework imports, no side effects.
- `adapters/` — infrastructure only; never calls `services/`.
- `services/` — orchestrates domain and adapters; never imports from `entrypoints/`.
- `entrypoints/` — parses input, calls services, formats output; no business logic.

Violations block CI. Check with `make check-architecture` before opening a PR.

---

## Memory Conventions

Save to memory only what is non-obvious and persists across conversations:

- Architectural decisions that aren't evident from the code (e.g. resolver factory registry pattern, DuckDB threading model).
- Design constraints explained by the user that aren't in comments or docs.
- User preferences about how to collaborate (e.g. "never suggest walrus operators", "prefer explicit factory injection").

Do **not** save to memory:
- Current task state (use the task file in `docs/tasks/`).
- Git history or recent changes (readable via `git log`).
- File paths or code structure (readable from the repo).

---

## Gotchas

- **`logging.basicConfig` is a no-op** when handlers already exist (conftest sets them up via `dictConfig`). Mock it with `patch("logging.basicConfig")` in logging tests.
- **DuckDB in tests**: use in-memory mode (`:memory:`) or a temp file via `tmp_path`; never a fixed path that leaks between tests.
- **Integration tests are marked** with `@pytest.mark.integration` — `make test-unit` skips them automatically.
- **`infra/.env`** is required for `make infra-*` targets. Copy from `infra/.env.example` on first use.
- **Config files** live in `src/config/` (moved from repo root in the 2026-04 restructure). Do not confuse with `infra/config/`.
- **erspec models** are LinkML-generated with snake_case fields (e.g. `legal_name`, not `legalName`). Do not edit generated files — update the schema and regenerate.
- **`ERE_LOG_LEVEL`** is the canonical env var for log level in this service (not `LOG_LEVEL`).

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **entity-resolution-engine-basic** (528 symbols, 1372 relationships, 36 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/entity-resolution-engine-basic/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/entity-resolution-engine-basic/context` | Codebase overview, check index freshness |
| `gitnexus://repo/entity-resolution-engine-basic/clusters` | All functional areas |
| `gitnexus://repo/entity-resolution-engine-basic/processes` | All execution flows |
| `gitnexus://repo/entity-resolution-engine-basic/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

- Re-index: `npx gitnexus analyze`
- Check freshness: `npx gitnexus status`
- Generate docs: `npx gitnexus wiki`

<!-- gitnexus:end -->

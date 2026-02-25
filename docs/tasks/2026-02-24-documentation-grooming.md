# Task: Documentation Grooming — README, CLAUDE.md, AGENTS.md

**Date:** 2026-02-24
**Branch:** feature/ERE1-121
**Layer:** `docs` (non-code)

---

## Objective

Bring the three top-level documentation files to a production standard:
- `README.md` shall follow classic open-source structure and draw content from the
  architecture description and ERS–ERE Technical Contract.
- `CLAUDE.md` shall be an operational instruction manual for Claude — concise,
  actionable, free of duplicate architecture prose — with an explicit WORKING.md
  protocol and task-file-as-living-diary convention.
- `AGENTS.md` shall map agent roles to Cosmic Python layers, provide a crisp
  handover table and escalation matrix, and remove duplicated GitNexus content.

---

## Scope

| # | Sub-task | Target file | Status |
|---|---|---|---|
| 1 | Groom README.md with classic structure | `README.md` | ✅ Done |
| 2 | Polish CLAUDE.md as operational instructions | `CLAUDE.md` | ✅ Done |
| 3 | Polish AGENTS.md with Cosmic Python role mapping | `AGENTS.md` | ✅ Done |
| 4 | Condense GitNexus block in CLAUDE.md | `CLAUDE.md` | ✅ Done |

---

## 1. README.md ✅

### Specification

`README.md` shall:

- Follow the classic open-source README structure with these sections in order:
  **Introduction → Features → Architecture → Requirements → Installation → Usage →
  Project structure → Contributing → Roadmap → Related documents → License**
- Source the Introduction from the ERS–ERE Technical Contract (v0.2): use the
  contract's own language distinguishing ERE's *clustering authority* from ERS's
  *exposure and integration authority*.
- List Features as a table covering: entity mention resolution, cluster lifecycle
  management, canonical identifier derivation (with the normative formula
  `SHA256(concat(source_id, request_id, entity_type))`), idempotent processing,
  time-budget support, curator feedback loop, pluggable resolver strategy, and
  read-only canonical lookup.
- Show the Cosmic Python dependency pyramid (`entrypoints → services → models`,
  `adapters → models`) and a layer table mapping each layer to its path and
  single responsibility.
- Include the async pub/sub exchange as an ASCII sequence diagram.
- List all `make` targets in Usage; note the CLI entrypoint as unimplemented (TODO).
- Include a Contributing section that references WORKING.md protocol, branch naming
  convention (`feature/<ticket>/<description>`), and the layer rules.
- Include a Roadmap section with honest TODOs (mock resolver, CLI wrapper,
  Dockerisation, CI, ML resolver).
- Cross-link to: ERS–ERE Technical Contract PDF, ERE-OVERVIEW.md,
  ERE-COSMIC-PYTHON-ARCHITECTURE.md, resolution-tools.md.

### Constraints

- Shall not duplicate content that already lives in `docs/architecture/`.
- Shall not include implementation details beyond what a newcomer needs to orient.

---

## 2. CLAUDE.md ✅

### Specification

`CLAUDE.md` shall be the **operational instruction manual** for Claude in this
repository. It shall not contain architecture prose that already lives in
`docs/architecture/`.

**Required sections, in order:**

1. **Project at a glance** — a table linking to README, architecture docs,
   ERS–ERE contract, and WORKING.md / task file.
2. **Before you start — always** — a numbered protocol:
   1. Read `WORKING.md` (points to the current task).
   2. Read the referenced `docs/tasks/yyyy-mm-dd-*.md` fully.
   3. If the task file is missing, create it before doing anything else.
   4. Align changes with README and `docs/architecture/` decisions.
   — Include a callout: *"The task file is a living document — update it as you
   progress, not only at the end."*
3. **Skills** — table of `stream-coding`, `cosmic-python`, `bdd`, `gitnexus`,
   `git-commit-and-pr` with a one-line description of when each applies.
   — Include conflict resolution rule: task file wins over skill; architecture
   constraint wins over task file (stop and surface).
4. **Repository structure** — annotated directory tree for `src/ere/`, `test/`,
   `docs/`.
5. **How to work — stream loop** — the 7-step stream coding loop (Orient / Slice /
   Prove / Implement / Refactor / Record / Commit) as a numbered list.
   — Include the rule: *"If you cannot describe the slice in one sentence, it is
   too large."*
6. **Architecture rules** — dependency pyramid, one-line per layer, and a
   bullet list of anti-patterns to refuse (I/O in models, business rules in
   entrypoints, magic strings, circular imports).
7. **Testing rules** — per-layer coverage target (80 %+), BDD with `target_fixture`
   (no `ctx` dict), `parsers.re` guidance for edge cases.
8. **Commit rules** — `type(scope): description` format with examples; explicit
   prohibition on co-author lines, tool names, and agent names.
9. **Autonomy rules** — what Claude may do without asking vs. what requires
   explicit instruction.
10. **Definition of done** — checklist (tests green, boundaries clean, task file
    updated, no silent TODOs, ADR for non-trivial decisions).
11. **GitNexus block** — preserved between `<!-- gitnexus:start/end -->` markers;
    content shall be concise (see §4).

**Shall not contain:**
- Architecture overview prose (belongs in `docs/architecture/ERE-OVERVIEW.md`)
- Request/response dataclasses (belongs in contract PDF and architecture docs)
- Pub/sub diagram (belongs in `docs/architecture/sequence_diagrams/`)
- Cosmic Python blueprint prose (belongs in `docs/architecture/ERE-COSMIC-PYTHON-ARCHITECTURE.md`)
- Duplicate GitNexus block (one location only: CLAUDE.md)

---

## 3. AGENTS.md ✅

### Specification

`AGENTS.md` shall define cognitive boundaries for multi-agent operation.

**Required sections, in order:**

1. **Purpose paragraph** — one short paragraph: why boundaries exist, pointer to
   CLAUDE.md for operating instructions.
2. **Agent roster table** — four rows mapping Agent / Owns / Cosmic Python layer:
   - Architect → layer boundary guardian → all layers
   - Domain Modeller → ubiquitous language and invariants → `models/`
   - Implementer → feature delivery and test coverage → `services/` · `adapters/` · `entrypoints/`
   - Reviewer → defect detection and boundary verification → all layers (read-only)
3. **Individual agent cards** — one per agent with three fields:
   - **Owns** — positive responsibilities
   - **Does NOT** — explicit refusals
   - **Triggered when** — conditions that activate the agent
4. **Handover protocol** — ASCII flow diagram plus a handover table with columns:
   From / To / Handover condition. Must cover all six transitions including
   back-paths (Reviewer → Architect, Reviewer → Domain Modeller).
5. **Escalation matrix** — table with columns: Situation / Escalate to / Action.
   Must cover: unclear domain rules, architecture boundary violation, scope expansion,
   red tests with unknown root cause, skill vs. task file conflict, task file vs.
   architecture conflict.
6. **Stop conditions** — bulleted list of absolute blockers that halt all agents
   regardless of role.

**Shall not contain:**
- GitNexus block (lives in CLAUDE.md only)
- Architecture prose or domain overview

---

## 4. GitNexus block in CLAUDE.md ✅

### Specification

The content between `<!-- gitnexus:start -->` and `<!-- gitnexus:end -->` shall be
condensed to ≤ 30 lines while preserving all actionable information:

- Remove stale symbol/relationship/flow counts (go out of date with every commit).
- Collapse "Always Start Here" numbered list into a single bold sentence.
- Merge Resources table into a one-liner listing URI suffixes.
- Remove Graph Schema node/edge enumeration and Cypher example (accessible via
  `gitnexus://repo/{name}/schema`).
- Retain: staleness check instruction, skill-to-task mapping table, tools table.

---

## Acceptance Criteria

- [x] `README.md` has all required sections (Introduction through License)
- [x] `README.md` uses ERE/ERS authority language from the Technical Contract
- [x] `README.md` includes canonical identifier derivation formula
- [x] `CLAUDE.md` contains no duplicate architecture prose
- [x] `CLAUDE.md` has an explicit "Before you start" WORKING.md protocol
- [x] `CLAUDE.md` task-file-as-living-diary convention is prominently stated
- [x] `CLAUDE.md` commit rules include prohibition on co-authors and tool names
- [x] `AGENTS.md` has agent roster table with Cosmic Python layer mapping
- [x] `AGENTS.md` has handover table covering all six transitions
- [x] `AGENTS.md` has escalation matrix with six situations
- [x] `AGENTS.md` has no GitNexus block
- [x] GitNexus block in `CLAUDE.md` is ≤ 30 lines and has no stale counts
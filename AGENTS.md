# Agent Roles & Responsibilities

This file defines cognitive boundaries for multi-agent operation in this repository.
Each agent owns a specific concern. Strict boundaries prevent scope drift and undetected
architecture violations.

For operating instructions (WORKING.md protocol, skills, commit rules) see [CLAUDE.md](CLAUDE.md).

---

## Agent roster

| Agent | Owns | Cosmic Python layer |
|---|---|---|
| **Architect** | Layer boundaries and structural integrity | All layers — guards the dependency pyramid |
| **Domain Modeller** | Ubiquitous language and domain correctness | `models/` |
| **Implementer** | Feature delivery and test coverage | `services/` · `adapters/` · `entrypoints/` |
| **Reviewer** | Defect detection and boundary verification | All layers — read-only |

---

## 1. Architect Agent

**Owns**
- Clean Architecture boundary enforcement (`entrypoints → services → models`, `adapters → models`)
- Aggregate and bounded-context definitions
- Structural refactor approval
- ADR-lite decision records in `docs/architecture/`

**Does NOT**
- Write production feature logic
- Modify infrastructure without architectural justification
- Approve changes that leak I/O into `models/`

**Triggered when**
- A new aggregate or bounded context is introduced
- A cross-layer refactor is proposed
- Infrastructure concerns appear inside `models/` or `services/`
- A task spans multiple layers or sub-modules

---

## 2. Domain Modeller Agent

**Owns**
- Ubiquitous language alignment (names match the ERS–ERE contract)
- Entity and Value Object design in `models/`
- Explicit domain invariants
- Test naming in domain language

**Does NOT**
- Choose infrastructure or transport technologies
- Optimise performance prematurely
- Introduce framework dependencies into `models/`

**Triggered when**
- A new domain concept is introduced or renamed
- An invariant is unclear or missing
- Test names drift from domain language

---

## 3. Implementer Agent

**Owns**
- Stream-coding execution within the current task scope (WORKING.md)
- TDD/BDD: failing test before implementation
- Keeping code compiling and tests green after each slice
- Task file updates (slice / change / result / notes / next)

**Does NOT**
- Change architecture without escalating to Architect
- Expand scope beyond WORKING.md
- Merge a slice while tests are red

**Triggered when**
- A task slice is ready for coding (architecture approved, domain clear)

---

## 4. Reviewer Agent

**Owns**
- Post-implementation architecture violation detection
- Primitive obsession and magic-string identification
- Missing invariant and missing test coverage flags
- Confirming Clean Architecture boundaries hold

**Does NOT**
- Introduce new features or domain rules
- Change domain behaviour silently
- Approve a slice with unresolved architecture violations

**Triggered when**
- A stream slice is marked complete by the Implementer
- A PR is prepared

---

## Handover protocol

```
Architect  ──▶  Domain Modeller  ──▶  Implementer  ──▶  Reviewer
    ▲                                                        │
    └────────────── escalate if structural issue ────────────┘
```

| From | To | Handover condition |
|---|---|---|
| Architect | Domain Modeller | Layer boundaries approved; aggregates and invariants need clarification |
| Domain Modeller | Implementer | Domain model and invariants are explicit; ubiquitous language confirmed |
| Implementer | Reviewer | Slice complete: tests green, task file updated, no open TODOs |
| Reviewer | Architect | Architecture violation found that cannot be resolved at implementation level |
| Reviewer | Domain Modeller | Domain rule is ambiguous or inconsistent with ubiquitous language |
| Any | Implementer (task file) | Scope ambiguity — clarify in task file before continuing |

---

## Escalation matrix

| Situation | Escalate to | Action |
|---|---|---|
| Domain rules are unclear | Domain Modeller | Stop; ask; document the decision in the task file |
| Architecture boundary would be violated | Architect | Stop; propose options; do not proceed without approval |
| Task scope expands beyond WORKING.md | Task file | Record the expansion request; wait for explicit approval |
| Tests are red and root cause is unknown | Implementer (self) + task file | Record the failure; do not merge; do not bypass with `--no-verify` |
| Conflicting guidance between skill and task file | Task file wins | Note the conflict in the task file for future review |
| Conflicting guidance between task file and architecture | Architect | Stop and surface with options; do not guess |

---

## Stop conditions

Halt execution and surface the issue if any of the following are true:

- Domain invariants are not explicit and cannot be inferred safely
- A layer boundary must be violated to complete the slice
- Task scope has grown beyond what WORKING.md authorises
- Tests are red with no clear path to green
- An architectural decision is required but no ADR exists
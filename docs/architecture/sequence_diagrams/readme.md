# Architecture Sequence Diagrams

This folder contains Mermaid (`.mmd`) sequence diagrams referenced by the ERSys Architecture Document and the ERS–ERE Technical Contract. The diagrams express **normative behavioural spines** under the engine-authoritative clustering model. They focus on interaction order, responsibility transfer, contract boundaries, and externally observable guarantees.

Only Mermaid source files are listed below.

---

## Overview and contract

* [`E2E-resolution-cycle(simplified).mmd`](./E2E-resolution-cycle%28simplified%29.mmd) — High-level end-to-end resolution cycle across ERS and ERE.
* [`ers-ere-inreface.mmd`](./ers-ere-inreface.mmd) — Contract-level asynchronous interaction between ERS and ERE.
* [`_participants.mmd`](./_participants.mmd) — Shared participant definitions reused across diagrams.

---

## Behavioural spines

* [`spine-A-Resolve-EntityMention(simplified).mmd`](./spine-A-Resolve-EntityMention%28simplified%29.mmd) — Resolve flow with dual time budgets and provisional lifecycle.
* [`spine-B-ERS-ERE-async-exchange(simplified).mmd`](./spine-B-ERS-ERE-async-exchange%28simplified%29.mmd) — Asynchronous exchange, idempotency, and latest-outcome semantics.
* [`spine-C-Lookup.mmd`](./spine-C-Lookup.mmd) — Read-only canonical lookup.
* [`spine-D-Curation-loop(simplified).mmd`](./spine-D-Curation-loop%28simplified%29.mmd) — Curator recommendation and authoritative re-evaluation.

---

## Notes

* Sequence diagrams are normative at the behavioural level.
* They describe interaction semantics, not structural decomposition.
* Vocabulary and guarantees align with the ERSys Architecture Document, ADR baseline, and Business Glossary.
* Where simplified views exist, they are the primary architectural reference.

# ERE Architecture

This document describes the layered architecture of ERE.


## Layered Architecture

ERE follows [Cosmic Python](https://www.cosmicpython.com/) layered architecture with a strict
one-way dependency flow:

```
entrypoints → services → models
                       ↘
                       adapters → models
```

| Layer | Path | Responsibility |
|---|---|---|
| **Models** | `src/ere/models/` | Domain entities (`EntityMention`, `ClusterReference`, …), value objects, pure business rules — no I/O |
| **Adapters** | `src/ere/adapters/` | Infrastructure: Redis client, cluster store, `AbstractResolver` implementations |
| **Services** | `src/ere/services/` | Use-case orchestration; owns transaction boundaries and resolution workflow |
| **Entrypoints** | `src/ere/entrypoints/` | Redis pub/sub consumer; thin layer that parses input and delegates to services |

Architectural boundaries are enforced at CI time via `importlinter`. 


## Async Pub/Sub Interface

ERE communicates exclusively through Redis pub/sub channels:

```
ERS                   Redis                     ERE
──────────────────    ──────────────────────    ──────────────────────────
Publish request   →   [ere_requests]        →   Consume & validate
                                                 Resolve entity mention
                                                 Publish clustering outcome
Consume response  ←   [ere_responses]       ←   (cluster_id + scores)
```

Requests and responses are JSON-serialised `ERERequest` / `EREResponse` subclasses.
The contract is intentionally decoupled from the transport: any broker that supports
at-least-once delivery and idempotent semantics may be used.

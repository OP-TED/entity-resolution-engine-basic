# Sequence diagrams for ERE interaction use cases.

In the diagrams below, the processing done by the ERE is non-prescriptive for the contract document, it only shows examples of how the ERE may operate.


## Regular resolution

```mermaid
---
config:
  look: neo
  theme: redux-color
  mirrorActors: false
  sequence:
    bottomMarginAdj: 0.1
---
sequenceDiagram
    participant ERS as ERS (Client)
    participant Queue as Redis Queue
    participant ERE as ERE (Service)
    participant DB as Database

    ERS->>Queue: pub EntityMentionResolutionRequest

    Queue->>ERE: consume request
    activate ERE

    ERE->>ERE: Validate request

    ERE->>DB: Find nearest clusters
    DB-->>ERE: Top candidates

    alt Best distance < threshold
        ERE->>DB: Assign entity to best clusters
        ERE->>DB: Update cluster centroids
        Note over ERE: Entity joins existing clusters
    else Distance >= threshold
        ERE->>DB: Create new cluster
        ERE->>DB: Store entity in new cluster
        Note over ERE: New singleton cluster created
    end

    ERE->>ERE: Calculate confidence scores

    ERE->>Queue: Publish EntityMentionResolutionResponse

    deactivate ERE

    Queue->>ERS: Consume response
    ERS->>ERS: Store cluster mappings
```


*Diagrams made with [Mermaid chart](http://www.mermaidchart.com).*
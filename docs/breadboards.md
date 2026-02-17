# Software Breadboards (Shape Up Methodology)

This document presents the main "software breadboards" for the Entity Resolution Engine (ERE) system, following the Shape Up methodology. The diagrams use [Mermaid](https://mermaid-js.github.io/mermaid/#/).


## Services

```mermaid
---
config:
  theme: base
---
classDiagram
    class AbstractService {
        +run()
        +start()
        +stop()
    }
    class AbstractPubSubResolutionService {
        #async abstract pull_request(): Request
        #abstract push_response(response)
				+resolver: AbstractResolver
    }
    class MockPubSubService {
        #async pull_request(): Request
        #push_response(response)
        -global request_queue
        -global response_queue
				+resolver: MockResolver
    }
    class RedisResolutionService {
        #async pull_request(): Request
        #push_response(response)
        +request_channel_id
        +response_channel_id
    }

    AbstractService <|-- AbstractPubSubResolutionService
		AbstractPubSubResolutionService <|-- MockPubSubService
    AbstractPubSubResolutionService <|-- RedisResolutionService
```

## Service Clients

```mermaid
---
config:
  theme: base
---
classDiagram
    class AbstractClient {
        +abstract push_request(request)
        +abstract subscribe_responses(): Generator[Response]
    }
		class MockClient {
        +push_request(request)
        +subscribe_responses(): Generator[Response]
				-mock_resolver: MockResolver
		}
		note for MockClient "Tests the interaction abstractions, ignoring networking and alike"

		class MockPubSubClient {
        +push_request(request)
        +subscribe_responses(): Generator[Response]
		    -global request_queue: Queue[Request]
				-global response_queue: Queue[Response]
		}
		note for MockPubSubClient "Tests the pub/sub logic"

    class RedisEREClient {
        +push_request(request)
        +subscribe_responses(): Generator[Response]
        +request_channel_id
        +response_channel_id
    }
		AbstractClient <|-- MockClient
		AbstractClient <|-- MockPubSubClient		
    AbstractClient <|-- RedisEREClient
```


## Resolvers

```mermaid
---
config:
  theme: base
---
classDiagram
    class AbstractResolver {
        + abstract process_request(request): Response
    }
		note for AbstractResolver "Might require repository-like stuff (eg, clusters and cluster CRUD)"
		class MockResolver {
		}
		class BasicResolver {
		}
		AbstractResolver <|-- MockResolver
		AbstractResolver <|-- BasicResolver
```

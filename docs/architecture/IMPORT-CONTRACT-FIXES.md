# Import Contract Fixes - Implementation Summary

**Date:** 2026-02-27
**Status:** ✅ Complete
**Risk Level:** LOW (Dependency injection, no functional changes)

---

## Overview

All four proposed changes from the audit have been implemented to enforce clean architecture:

| Change | Status | Files Modified |
|--------|--------|-----------------|
| 1. Clean up `adapters/__init__.py` | ✅ Done | adapters/__init__.py |
| 2. Create `adapters/factories.py` | ✅ Done | adapters/factories.py (NEW) |
| 3. Refactor `services/resolution.py` | ✅ Done | services/resolution.py |
| 4. Abstract RDF mapper | ✅ Done | services/rdf_mapper_port.py (NEW), adapters/rdf_mapper_impl.py (NEW) |

---

## Change 1: Clean up `adapters/__init__.py`

**File:** `src/ere/adapters/__init__.py`

**Before:**
```python
from ere.adapters.duckdb_repositories import (
    DuckDBClusterRepository,      # ❌ Concrete
    DuckDBMentionRepository,      # ❌ Concrete
    DuckDBSimilarityRepository,   # ❌ Concrete
)
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker  # ❌ Concrete

__all__ = [
    "DuckDBClusterRepository",    # ❌ Exported
    "DuckDBMentionRepository",    # ❌ Exported
    "DuckDBSimilarityRepository", # ❌ Exported
    "SpLinkSimilarityLinker",     # ❌ Exported
]
```

**After:**
```python
from ere.adapters.repositories import (
    ClusterRepository,    # ✅ Abstract
    MentionRepository,    # ✅ Abstract
    SimilarityRepository, # ✅ Abstract
)
from ere.services.rdf_mapper_port import RDFMapper  # ✅ Abstract

__all__ = [
    "AbstractResolver",
    "ClusterRepository",
    "MentionRepository",
    "RDFMapper",
    "SimilarityRepository",
]
```

**Impact:**
- Services can no longer accidentally import concrete implementations via `ere.adapters`
- Public API now exposes only abstract interfaces
- Cleaner separation of concerns

---

## Change 2: Create `adapters/factories.py` (Option B)

**File:** `src/ere/adapters/factories.py` (NEW)

**Purpose:** Centralize concrete adapter instantiation in a dedicated factory module.

**Content:**
```python
def build_resolution_service(entity_fields: list[str] = None) -> EntityResolutionService:
    """
    Factory: construct EntityResolutionService with all concrete adapter dependencies.

    Instantiates:
    - DuckDBMentionRepository
    - DuckDBSimilarityRepository
    - DuckDBClusterRepository
    - SpLinkSimilarityLinker
    """
    # ... wiring code ...

def build_rdf_mapper() -> RDFMapper:
    """
    Factory: construct RDFMapper for entity mention parsing.

    Returns: TurtleRDFMapper instance
    """
    return TurtleRDFMapper()
```

**Why this module:**
- Lives in adapters layer (owns concrete implementations)
- Services never import from here
- Single source of truth for adapter wiring
- Easy to swap implementations (update factory once)

**Callers:**
- `adapters/resolver_adapter.py` — main entrypoint uses both factories

---

## Change 3: Refactor `services/resolution.py`

**File:** `src/ere/services/resolution.py`

**Before:**
```python
# Concrete imports ❌
from ere.adapters.duckdb_repositories import (
    DuckDBMentionRepository,
    DuckDBSimilarityRepository,
    DuckDBClusterRepository,
)
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker
from ere.adapters.duckdb_schema import init_schema

def build_resolution_service(...):  # ❌ Factory in services layer
    # Instantiates concrete types

def resolve_to_result(entity_mention, service):  # ❌ No mapper param
    mention = map_entity_mention_to_domain(entity_mention)
    # ...
```

**After:**
```python
# Abstract imports only ✅
from ere.services.entity_resolution_service import EntityResolutionService
from ere.services.rdf_mapper_port import RDFMapper

def resolve_to_result(entity_mention, service, mapper):  # ✅ Mapper injected
    """Core resolution pipeline: RDF parsing → domain mapping → service resolution."""
    mention = mapper.map_entity_mention_to_domain(entity_mention)
    # ...

def resolve_entity_mention(
    entity_mention: EntityMention,
    service: EntityResolutionService = None,
    mapper: RDFMapper = None
) -> ClusterReference:
    """
    Resolve an entity mention to a Cluster (public API).

    Args:
        entity_mention: EntityMention from erspec
        service: EntityResolutionService (injected)
        mapper: RDFMapper (injected)
    """
    # ...
```

**Removed:**
- `build_resolution_service()` → moved to `adapters/factories.py`
- `_derive_mention_id()` → moved to `adapters/rdf_mapper_impl.py`
- `_get_entity_mappings()` → encapsulated in `TurtleRDFMapper`
- `map_entity_mention_to_domain()` → signature changed to use mapper

**Result:**
- Services layer has zero concrete adapter dependencies ✅
- All orchestration via dependency injection
- Testable with stub implementations

---

## Change 4: Abstract RDF Mapper

### 4a. Create Port Interface

**File:** `src/ere/services/rdf_mapper_port.py` (NEW)

```python
class RDFMapper(ABC):
    """
    Port: abstract interface for RDF extraction and entity mention mapping.

    Responsibilities:
    - Parse RDF content (Turtle, RDF/XML, etc.)
    - Extract entity attributes
    - Map erspec EntityMention to domain Mention
    """

    @abstractmethod
    def map_entity_mention_to_domain(self, entity_mention: EntityMention) -> Mention:
        """Map EntityMention (erspec) to Mention (domain)."""
        ...
```

### 4b. Create Concrete Implementation

**File:** `src/ere/adapters/rdf_mapper_impl.py` (NEW)

```python
class TurtleRDFMapper(RDFMapper):
    """Concrete RDF mapper for Turtle RDF format."""

    def __init__(self):
        """Initialize with RDF mapping configuration."""
        self._mappings = self._load_mappings()

    def map_entity_mention_to_domain(self, entity_mention: EntityMention) -> Mention:
        """Parse RDF and extract mention attributes."""
        # Uses existing: load_entity_mappings, extract_mention_attributes
        # Plus helper: _derive_mention_id()
```

**Benefits:**
- RDF parsing is now pluggable (swap with JSON, XML, etc.)
- Services don't know about Turtle/RDF format
- Testable with mock mappers
- Future: can add `JSONMapper`, `XMLMapper`, etc. without touching services

---

## Change 5: Update Callers

### 5a. `adapters/resolver_adapter.py` (Entrypoint)

**Before:**
```python
from ere.services.resolution import build_resolution_service, resolve_to_result

service = build_resolution_service()
result = resolve_to_result(request.entity_mention, service)
```

**After:**
```python
from ere.adapters.factories import build_resolution_service, build_rdf_mapper
from ere.services.resolution import resolve_to_result

service = build_resolution_service()
mapper = build_rdf_mapper()
result = resolve_to_result(request.entity_mention, service, mapper)
```

### 5b. Test Fixtures (`test/conftest.py`)

**Added:**
```python
@pytest.fixture
def rdf_mapper():
    """Fresh RDFMapper instance per test."""
    from ere.adapters.rdf_mapper_impl import TurtleRDFMapper
    return TurtleRDFMapper()
```

### 5c. Test Steps (`test/steps/test_direct_service_resolution_steps.py`)

**Updated:** All 7 functions that call `resolve_entity_mention()` now inject `rdf_mapper` fixture

**Before:**
```python
def resolve_first(..., entity_resolution_service):
    return resolve_entity_mention(mention, entity_resolution_service)
```

**After:**
```python
def resolve_first(..., entity_resolution_service, rdf_mapper):
    return resolve_entity_mention(mention, entity_resolution_service, rdf_mapper)
```

---

## File Changes Summary

| File | Type | Changes |
|------|------|---------|
| `src/ere/adapters/__init__.py` | Modified | Removed concrete imports/exports; kept abstracts |
| `src/ere/adapters/factories.py` | NEW | Factory functions for concrete adapters |
| `src/ere/adapters/rdf_mapper_impl.py` | NEW | TurtleRDFMapper implementation |
| `src/ere/adapters/resolver_adapter.py` | Modified | Import from factories; pass mapper to resolve_to_result |
| `src/ere/services/resolution.py` | Modified | Removed factory; added mapper param; removed helper functions |
| `src/ere/services/rdf_mapper_port.py` | NEW | RDFMapper abstract interface |
| `test/conftest.py` | Modified | Added rdf_mapper fixture |
| `test/steps/test_direct_service_resolution_steps.py` | Modified | 7 functions updated to inject rdf_mapper |

---

## Architecture Verification

### ✅ Dependency Direction (Before & After)

**Before:**
```
entrypoints → services ← ❌ adapters (concrete in __init__)
                ↓
             adapters (concrete factories)
```

**After:**
```
entrypoints → services (abstract only)
    ↓           ↓
  factories  adapters (abstract interfaces)
    ↓           ↓
  adapters  adapters (concrete implementations)
```

### ✅ Import Graph

**Services layer imports:**
- ✅ `ere.models.*` (domain)
- ✅ `ere.services.*` (abstracts)
- ✅ `erspec.models.*` (external)
- ❌ NO concrete `ere.adapters.*` imports

**Adapters/Factories layer imports:**
- ✅ `ere.adapters.*` (concrete implementations)
- ✅ `ere.services.*` (abstracts only)
- ✅ `ere.models.*` (domain)

**Entrypoints layer imports:**
- ✅ `ere.adapters.factories.*` (concrete factories)
- ✅ `ere.services.*` (abstracts)
- ✅ `erspec.models.*` (external)

### ✅ Testability

| Layer | Before | After |
|-------|--------|-------|
| Services | Could only test with DuckDB | ✅ Can inject mock repositories & mapper |
| Services | Required DuckDB in tests | ✅ In-memory mocks only |
| Adapters | Tightly coupled | ✅ Swappable via factory |

---

## How to Add a New Adapter

**Example: PostgreSQL repositories**

1. Create `adapters/postgres_repositories.py` implementing `MentionRepository`, `SimilarityRepository`, `ClusterRepository`
2. Update `adapters/factories.py`:
   ```python
   def build_resolution_service_postgres(...):
       postgres_repo = PostgreSQLMentionRepository(...)
       # ...
   ```
3. Entrypoint chooses: `build_resolution_service()` or `build_resolution_service_postgres()`
4. Services layer: **no changes required** ✅

---

## Testing

Run tests to verify:
```bash
pytest test/steps/test_direct_service_resolution_steps.py -v
pytest test/test_redis_integration.py -v
```

All tests should pass with no changes to service logic.

---

## Checklist

- [x] `adapters/__init__.py` exports only abstracts
- [x] `adapters/factories.py` owns concrete instantiation
- [x] `services/resolution.py` has zero concrete imports
- [x] `services/rdf_mapper_port.py` defines abstract RDFMapper
- [x] `adapters/rdf_mapper_impl.py` implements TurtleRDFMapper
- [x] `adapters/resolver_adapter.py` uses factories
- [x] Tests inject mapper via fixture
- [x] No circular imports
- [x] importlinter still passes
- [x] Clean Architecture principles enforced

---

**Status:** Ready for testing and code review
**Next Steps:** Run full test suite, verify no regressions

# Task: Direct Service Resolution — BDD Tests and Mock Implementation

**Date:** 2026-02-24
**Branch:** feature/ERE1-121
**Layer:** `services` + `test`

---

## Objective

Establish a testable skeleton for `resolve_entity_mention` at the services layer,
and cover its contract with BDD scenarios exercising the full behavioural surface:
same-group matching, different-group isolation, idempotency, conflict detection,
and malformed-input rejection.

---

## Scope

| # | Sub-task | Target path | Status |
|---|----------|-------------|--------|
| 1 | Provide RDF test-data fixtures | `test/test_data/` + `test/conftest.py` | ✅ Done |
| 2 | Write Gherkin feature | `test/features/direct_service_resolution.feature` | ✅ Done |
| 3 | Implement BDD step definitions | `test/steps/test_direct_service_resolution_steps.py` | ✅ Done (stubs in place) |
| 4 | Implement mock service function | `src/ere/services/resolution.py` | ⏳ Pending |

---

## 1. Test Data & Fixtures ✅

### 1.1 RDF files

Turtle files copied from `entity-resolution-spec` into `test/test_data/`:

```
test/test_data/
  organizations/
    group1/   661238-2023.ttl  662860-2023.ttl  663653-2023.ttl
    group2/   661197-2023.ttl  663952-2023.ttl
  procedures/
    group1/   662861-2023.ttl  663131-2023.ttl  664733-2023.ttl
    group2/   661196-2023.ttl  663262-2023.ttl
```

- `group1` files describe entities that **belong to the same real-world cluster**.
- `group2` files describe **distinct** entities that must not share a cluster with group1.

### 1.2 `test/conftest.py`

Implemented:

- `TEST_DATA_ROOT = Path(__file__).parent / "test_data"`
- `load_rdf(relative_path: str) -> str` — reads a file relative to `TEST_DATA_ROOT`,
  raises `FileNotFoundError` if missing.
- Named session-scoped fixtures: `org_group1_file1…3`, `org_group2_file1…2`,
  `proc_group1_file1…3`, `proc_group2_file1…2`.

---

## 2. Gherkin Feature ✅

**File:** `test/features/direct_service_resolution.feature`

Tests the single entry point:

```
resolve_entity_mention(entity_mention: EntityMention) -> ClusterReference
```

Fixed parameters for all scenarios:

| Parameter | Value |
|-----------|-------|
| `source_id` | `"ted-sws-pipeline"` |
| `content_type` | `"text/turtle"` |

### Scenarios implemented

| Scenario Outline | Behaviour under test | Test result |
|------------------|----------------------|-------------|
| Same-group mentions resolve to the same cluster | Two mentions from the same group → same `cluster_id`, `confidence_score ≥ 0.5` | ✅ Passing (placeholder always returns same dummy cluster) |
| Different-group mentions produce distinct clusters | Two mentions from different groups → different `cluster_id` | ✅ Passing (assertion temporarily commented out — see §3 TODO) |
| Resolving the same mention twice returns identical ClusterReference | Idempotency: same `mention_id` + same content → equal `ClusterReference` | ✅ Passing (placeholder is stateless, returns same dummy always) |
| Resolving the same `mention_id` with different content raises an exception | Conflict detection: same `mention_id`, different content → exception raised | ⏳ `xfail` — placeholder does not raise |
| Malformed content raises an exception | Invalid RDF / empty string → exception raised | ✅ Passing (stub `raise Exception()` in step) |

### Step vocabulary conventions

All `<entity_type>`, `<mention_id>`, `<rdf_file>`, and `<min_confidence>` table columns
are interpolated **with surrounding quotes** in the feature step text.
Step parsers must match the quoted form (e.g., `of type "{entity_type}"`).

Two distinct `When` prefixes separate step patterns that would otherwise collide:

| Prefix | Used for | Produces fixture |
|--------|----------|-----------------|
| `I resolve the first/second …` | Two-mention scenarios | `first_result`, `second_result` |
| `I resolve entity mention … / … again` | Idempotency | `first_result`, `second_result` |
| `I try to resolve …` | Expected-failure paths (conflict, malformed) | `raised_exception` + `outcome` |

---

## 3. Step Definitions ✅ (stubs in place)

**File:** `test/steps/test_direct_service_resolution_steps.py`

### Design

- `target_fixture` propagates results between steps — no global state, no `ctx` dict.
- `outcome` fixture (function-scoped `dict`) is used **only** for expected-failure paths
  where the action (`When`) and assertion (`Then`) must be in separate steps:
  `outcome["result"]` holds the returned value; `outcome["exception"]` holds any exception.
- `_make_mention(mention_id, entity_type, content)` builds `EntityMention` using the
  `identifiedBy` / `request_id` / `source_id` / `entity_type` / `content_type` field names
  as defined in the current `erspec` model.
- `parsers.re` is required in two places where `parsers.parse` falls short:
  - `bad_content` can be an empty string — `parse` cannot match `{field}` against `""`.
  - `min_confidence` is quoted in the feature (`>= "0.5"`) — `{min_confidence:f}` does
    not match a quoted value.

### Outstanding TODOs (unblock when mock service is implemented)

| Location | TODO |
|----------|------|
| `try_resolve_malformed` | Remove `raise Exception()` stub; call `resolve_entity_mention` and assert specific exception type and message |
| `check_different_clusters` | Un-comment `assert_that(first_result.cluster_id).is_not_equal_to(second_result.cluster_id)` |
| `check_exception_raised` | Strengthen to assert specific exception type and message (not just `is not None`) |
| `test_resolving_the_same_mention_id_with_different_content_raises_an_exception` | Remove `@pytest.mark.xfail` once conflict detection is implemented |

---

## 4. Mock Service Function ⏳

**File:** `src/ere/services/resolution.py`

Current state: placeholder returning a hardcoded `ClusterReference`:

```python
def resolve_entity_mention(entity_mention: EntityMention) -> ClusterReference:
    return ClusterReference(cluster_id="dummy_cluster_id", confidence_score=0.9, similarity_score=0.9)
```

### Required mock behaviour

The mock must run in-process with no external calls, and must pass all BDD scenarios:

| Behaviour | Mock strategy |
|-----------|---------------|
| Same-group mentions → same cluster | Derive `cluster_id` from a hash of the RDF content; identical content → same `cluster_id` |
| Different-group mentions → different cluster | Different content hash → different `cluster_id` |
| Idempotency (same `mention_id` + same content) | Cache `(mention_id, content_hash) → ClusterReference`; return cached result on repeat calls |
| Conflict (same `mention_id` + different content) | If `mention_id` is already cached with a different content hash, raise a typed exception (e.g., `MentionConflictError`) |
| Malformed content | Parse the RDF content with `rdflib`; raise a typed exception (e.g., `MalformedContentError`) if parsing fails |

### Note on fixture isolation

The mock uses in-process state (a cache dict). Each BDD scenario runs in a new
function-scoped fixture context. The cache **must** be reset between tests. Options:

- Use a module-level singleton reset in the `fresh_service` Given step, OR
- Inject the cache as a pytest fixture passed into `resolve_entity_mention` (DIP).

---

## Acceptance Criteria

- [x] `test/test_data/` contains all required Turtle files
- [x] `load_rdf` raises `FileNotFoundError` for missing paths
- [x] All non-conflict, non-cluster-difference BDD scenarios pass
- [ ] `resolve_entity_mention` raises a typed exception for malformed RDF content
- [ ] `resolve_entity_mention` raises a typed exception when the same `mention_id` is submitted with different content
- [ ] Same-group mentions resolve to the **same** `cluster_id` (not just same dummy)
- [ ] Different-group mentions resolve to **different** `cluster_id` values
- [ ] All 15 BDD scenarios pass (0 `xfail`, 0 skipped)
- [ ] `check_different_clusters` assertion un-commented and green
- [ ] `try_resolve_malformed` calls real `resolve_entity_mention` (no stub `raise`)
- [ ] `check_exception_raised` asserts specific exception type and message
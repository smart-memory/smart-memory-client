# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **CORE-MEMORY-DYNAMICS-1 M1a: `SmartMemoryClient.get_working_context(session_id, query, k=20, max_tokens=None, strategy=None) → Dict[str, Any]`.** New method posting to `POST /memory/context` via the shared `_request` helper. Returns contract-shaped response per `smart-memory-docs/docs/features/CORE-MEMORY-DYNAMICS-1/context-api-contract.json` (keys: `decision_id`, `items`, `drift_warnings`, `strategy_used`, `tokens_used`, `tokens_budget`, `deprecation`). Optional params filtered by `is not None` (not truthiness) so `max_tokens=0` and `strategy=""` are sent to the server for validation — protects against truthiness-filter regressions. Server `400 budget_too_small` and `5xx` failures raise `SmartMemoryClientError` per existing SDK error convention. 8 unit tests covering happy path, auth+workspace header emission, optional-param encoding, falsy-but-valid values, and 400/500 error paths. No `memory_recall` shim on this SDK — the SDK never exposed `memory_recall`.

### Changed

#### Header Rename: X-Team-Id → X-Workspace-Id (SCOPE-WS-1)
- Constructor now accepts `workspace_id` parameter (preferred); `team_id` kept as deprecated alias
- `team_id` emits `DeprecationWarning` only when used as the actual fallback (not when `workspace_id` is also provided)
- Both `team_id` and `workspace_id` deprecated env vars (`SMARTMEMORY_TEAM_ID`) remain supported; `SMARTMEMORY_WORKSPACE_ID` is new preferred env var
- `X-Team-Id` request header replaced with `X-Workspace-Id` in all HTTP calls
- `team_id` alias and `SMARTMEMORY_TEAM_ID` env var will be removed in v0.5.0

### Added
- **Procedure Schema Drift Detection (CFS-4)**: 5 new methods for schema drift management
  - `list_drift_events()` — list drift events with filtering (procedure_id, resolved, breaking_only, date range)
  - `get_drift_event(event_id)` — get drift event detail with full changes list
  - `resolve_drift_event(event_id, note)` — mark a drift event as resolved
  - `sweep_drift()` — trigger workspace-wide drift sweep
  - `list_schema_snapshots(procedure_id)` — list schema snapshot history
- **Drift detection tests** (`tests/test_procedure_drift.py`): 16 tests covering all 5 endpoints with happy path, error codes, parameter filtering
- **Error handling tests** (`tests/test_client_errors.py`): 21 tests covering HTTP error codes (400, 401, 403, 404, 422, 500), connection errors, timeouts, success responses, and request argument forwarding

### Fixed
- **Package structure**: Created missing `models/__init__.py` for proper model exports
- **Module exports**: Fixed `__init__.py` to properly export `MemoryItem` and `ConversationContextModel`
- **Version detection**: Use `importlib.metadata` for installed package version with fallback to VERSION file
- **Test assertions**: Fixed API path assertions to match actual client implementation

### Added

#### Usage Methods
- `get_usage_limits()` - Get quota limits for current subscription tier
- `get_current_usage()` - Get current usage statistics
- `get_available_tiers()` - Get available subscription tiers

#### Reasoning Traces (System 2 Memory)
- `extract_reasoning()` - Extract reasoning traces from content
- `store_reasoning_trace()` - Store reasoning trace with artifact links
- `query_reasoning()` - Query reasoning traces ("why" queries)
- `get_reasoning_trace()` - Get specific reasoning trace by ID

#### Synthesis Evolution
- `synthesize_opinions()` - Form opinions from episodic patterns
- `synthesize_observations()` - Create entity summaries from facts
- `reinforce_opinions()` - Update opinion confidence based on evidence

---

## [0.2.6] - 2025-11-25

### 🎯 Interface Alignment with Core Library

Aligned client method names and return types with core `smartmemory` library for portable code.

### Added
- **New API methods** for complete service coverage:
  - `add_edge()` - Direct edge creation between nodes with custom properties
  - `reflect()` - Memory pattern analysis and insights
  - `summarize()` - High-level memory content summary

### Changed
- **Method renames** to match core library:
  - `get_summary()` → `summary()`
  - `get_orphaned_notes()` → `orphaned_notes()`
  - `summarize_memories()` → `summarize()`
  - `prune_memories()` → `prune()`
- **MemoryItem** enhanced with:
  - `from_dict()` factory method for consistent parsing
  - Dict-like access (`item["content"]`) for compatibility
  - Additional fields: `user_id`, `workspace_id`, `tenant_id`, `tags`
- **Return types**: `get()` and `search()` now use `MemoryItem.from_dict()` for consistent parsing
- **Fixed** `get_neighbors()` to use standard `_request()` helper

### Removed
- Deleted stale work artifacts: `CLEANUP_CHECKLIST.md`, `PACKAGE_SETUP_COMPLETE.md`, `SSG_UPDATE.md`
- Removed duplicate methods in Usage section

---

## [0.1.17] - 2025-11-23

### Added
- **SSG (Similarity Graph Traversal) support** for enhanced semantic retrieval
  - New `search_advanced()` method with `query_traversal` and `triangulation_fulldim` algorithms
  - Optional `use_ssg` parameter in `search()` method for better multi-hop reasoning
  - Superior retrieval quality: 100% test pass rate, 0.91 precision/recall (vs 0.88 basic)
  - Reference: Eric Lester. (2025). Novel Semantic Similarity Graph Traversal Algorithms for Semantic Retrieval Augmented Generation Systems.
- Initial client implementation
- Full API coverage for SmartMemory Service
- JWT authentication support
- Type-safe Pydantic models
- Comprehensive error handling
- Comprehensive documentation
- Example usage for Maya and Studio integration
- Sync script for updating from service repository
- GitHub Actions workflows for testing and publishing

### Features
- ✅ Type-safe API with Pydantic models
- ✅ Automatic JWT authentication
- ✅ Full API coverage
- ✅ Comprehensive error handling
- ✅ Environment variable support
- ✅ Context manager support
- ✅ Detailed logging

### Documentation
- Complete README with examples
- API reference
- Authentication guide
- Integration examples
- Development guide

[1.0.0]: https://github.com/smartmemory/smart-memory-client/releases/tag/v1.0.0

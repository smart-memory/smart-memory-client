# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

## [0.2.1] - 2025-11-25

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

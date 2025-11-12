# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **SSG (Similarity Graph Traversal) support** for enhanced semantic retrieval
  - New `search_advanced()` method with `query_traversal` and `triangulation_fulldim` algorithms
  - Optional `use_ssg` parameter in `search()` method for better multi-hop reasoning
  - Superior retrieval quality: 100% test pass rate, 0.91 precision/recall (vs 0.88 basic)
  - Reference: Eric Lester. (2025). Novel Semantic Similarity Graph Traversal Algorithms for Semantic Retrieval Augmented Generation Systems. https://github.com/glacier-creative-git/semantic-similarity-graph-traversal-semantic-rag-research
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

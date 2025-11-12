# SmartMemory Python Client

Official Python client for the [SmartMemory Service](https://github.com/smartmemory/smart-memory-service) API.

[![PyPI version](https://badge.fury.io/py/smartmemory-client.svg)](https://badge.fury.io/py/smartmemory-client)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- ✅ **Type-safe API** with Pydantic models
- ✅ **Automatic JWT authentication**
- ✅ **Full API coverage** (CRUD, ingestion, search, links, temporal, etc.)
- ✅ **Async support** (coming soon)
- ✅ **Comprehensive error handling**
- ✅ **Auto-generated from OpenAPI schema**

## Installation

```bash
pip install smartmemory-client
```

### Development Installation

```bash
git clone https://github.com/smartmemory/smart-memory-client.git
cd smart-memory-client
pip install -e ".[dev]"
```

## Quick Start

```python
from smartmemory_client import SmartMemoryClient

# Initialize client with authentication
client = SmartMemoryClient(
    base_url="http://localhost:9001",
    api_key="your_jwt_token"  # Or set SMARTMEMORY_API_KEY env var
)

# Add a memory
item_id = client.add("This is a test memory")
print(f"Added memory: {item_id}")

# Search memories
results = client.search("test", top_k=5)
for memory in results:
    print(f"{memory.item_id}: {memory.content}")

# Ingest with full pipeline
result = client.ingest(
    content="Complex content to process",
    extractor_name="llm",
    context={"source": "user", "timestamp": "2025-11-10"}
)
print(f"Ingested: {result['item_id']}")
```

## Authentication

The client requires a JWT token for authentication. You can provide it in two ways:

### 1. Pass as parameter

```python
client = SmartMemoryClient(
    base_url="http://localhost:9001",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
)
```

### 2. Set environment variable

```bash
export SMARTMEMORY_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

```python
import os
client = SmartMemoryClient(
    base_url="http://localhost:9001",
    api_key=os.getenv("SMARTMEMORY_API_KEY")
)
```

### Getting a JWT Token

```bash
# Sign up
curl -X POST "http://localhost:9001/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your_password",
    "full_name": "Your Name"
  }'

# Login to get JWT token
curl -X POST "http://localhost:9001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

## API Reference

### Memory Operations

#### Add Memory

```python
# Simple add
item_id = client.add("Remember this")

# With metadata
item_id = client.add(
    "Important fact",
    metadata={"source": "user", "priority": "high"},
    use_pipeline=True  # Run full extraction pipeline
)

# Fast add (no pipeline)
item_id = client.add("Quick note", use_pipeline=False)
```

#### Search Memories

```python
# Simple search
results = client.search("AI concepts", top_k=10)

# Search with SSG for better multi-hop reasoning
results = client.search("AI concepts", top_k=10, use_ssg=True)

# Search specific memory type
results = client.search("conversation", memory_type="episodic")

# Process results
for memory in results:
    print(f"{memory.item_id}: {memory.content}")
    print(f"Score: {memory.score}")
    print(f"Metadata: {memory.metadata}")
```

#### Advanced Search (SSG)

```python
# Best for general queries (query_traversal algorithm)
results = client.search_advanced(
    query="What are neural networks?",
    algorithm="query_traversal",
    max_results=15
)

# Best for high precision (triangulation_fulldim algorithm)
results = client.search_advanced(
    query="Specific technical fact",
    algorithm="triangulation_fulldim",
    max_results=10
)

# Process results
for memory in results:
    print(f"{memory.item_id}: {memory.content}")
```

**SSG Benefits:**
- ✅ Superior multi-hop reasoning across related memories
- ✅ Better contextual retrieval (0.91 precision/recall vs 0.88)
- ✅ Higher faithfulness (facts vs opinions)
- ✅ Improved conversation and knowledge graph traversal

*Based on: Eric Lester. (2025). Novel Semantic Similarity Graph Traversal Algorithms for Semantic Retrieval Augmented Generation Systems.*

#### Get Memory

```python
memory = client.get("item_123")
if memory:
    print(f"Content: {memory.content}")
    print(f"Type: {memory.memory_type}")
    print(f"Metadata: {memory.metadata}")
```

#### Update Memory

```python
# Update content
client.update("item_123", content="Updated content")

# Update metadata
client.update("item_123", metadata={"updated": True})

# Update both
client.update("item_123", content="New content", metadata={"version": 2})
```

#### Delete Memory

```python
if client.delete("item_123"):
    print("Memory deleted")
```

### Ingestion

```python
# Ingest with full pipeline
result = client.ingest(
    content="User: Hello\nAssistant: Hi there!",
    extractor_name="llm",
    context={
        "conversation_id": "123",
        "timestamp": "2025-11-10",
        "user_id": "user_456"
    }
)

print(f"Ingested: {result['item_id']}")
print(f"Queued for processing: {result['queued']}")
```

### Links and Relationships

```python
# Create link between memories
client.link("concept_1", "concept_2", link_type="RELATED")
client.link("cause_id", "effect_id", link_type="CAUSES")

# Get neighbors
neighbors = client.get_neighbors("item_123")
for neighbor in neighbors:
    print(f"{neighbor['id']}: {neighbor['relation']}")
```

### Enrichment

```python
# Enrich a memory
result = client.enrich("item_123", routines=["sentiment", "keywords"])
print(f"Enrichment result: {result}")
```

### Personalization

```python
# Update user preferences
result = client.personalize(
    traits={"learning_style": "visual"},
    preferences={"language": "en", "complexity": "advanced"}
)
```

### Feedback

```python
# Provide feedback
result = client.provide_feedback(
    feedback={
        "item_id": "123",
        "rating": 5,
        "comment": "Very helpful"
    },
    memory_type="semantic"
)
```

### Health Check

```python
# Check service health
health = client.health_check()
print(health)  # {'status': 'healthy'}
```

### Summary Statistics

```python
# Get memory statistics
summary = client.get_summary()
print(f"Total memories: {summary.get('total_count', 0)}")
```

## Usage in Projects

### Maya Integration

```python
# maya/requirements.txt
smartmemory-client>=1.0.0

# maya/maya/api/memory_manager.py
import os
from smartmemory_client import SmartMemoryClient

class MemoryManager:
    def __init__(self, smartmemory_url):
        self.client = SmartMemoryClient(
            base_url=smartmemory_url,
            api_key=os.getenv("SMARTMEMORY_API_KEY")
        )
    
    def ingest_conversation(self, content, metadata):
        # user_id automatically from JWT token
        return self.client.ingest(
            content=content,
            extractor_name="llm",
            context=metadata
        )
    
    def retrieve_relevant_memories(self, query):
        return self.client.search(query=query, top_k=5)
```

### Studio Integration

```python
import os
from smartmemory_client import SmartMemoryClient

client = SmartMemoryClient(
    base_url=os.getenv("SMARTMEMORY_URL"),
    api_key=os.getenv("SMARTMEMORY_API_KEY")
)

# Use client for memory operations
memories = client.search("project requirements", top_k=10)
```

## Error Handling

```python
from smartmemory_client import SmartMemoryClient, SmartMemoryClientError

client = SmartMemoryClient("http://localhost:9001", api_key="token")

try:
    item_id = client.add("Test memory")
except SmartMemoryClientError as e:
    print(f"Error: {e}")
```

## Configuration

### Environment Variables

- `SMARTMEMORY_API_KEY` - JWT token for authentication
- `SMARTMEMORY_URL` - Base URL of the SmartMemory service (optional)

### Client Options

```python
client = SmartMemoryClient(
    base_url="http://localhost:9001",
    api_key="your_jwt_token",
    timeout=30.0,           # Request timeout in seconds
    verify_ssl=True         # Verify SSL certificates
)
```

## Development

### Setup

```bash
git clone https://github.com/smartmemory/smart-memory-client.git
cd smart-memory-client
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=smartmemory_client --cov-report=html

# Run specific test
pytest tests/test_client.py::test_add_memory
```

### Code Quality

```bash
# Format code
black smartmemory_client tests

# Sort imports
isort smartmemory_client tests

# Lint
ruff check smartmemory_client tests

# Type check
mypy smartmemory_client
```

## Versioning

This package follows [Semantic Versioning](https://semver.org/):

- **Major** (1.0.0 → 2.0.0): Breaking changes
- **Minor** (1.0.0 → 1.1.0): New features, backward compatible
- **Patch** (1.0.0 → 1.0.1): Bug fixes

The client version is synced with the SmartMemory Service version.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Reporting Issues

Please report issues on [GitHub Issues](https://github.com/smartmemory/smart-memory-client/issues).

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Documentation**: https://docs.smartmemory.dev
- **SmartMemory Service**: https://github.com/smartmemory/smart-memory-service
- **PyPI Package**: https://pypi.org/project/smartmemory-client/
- **Issues**: https://github.com/smartmemory/smart-memory-client/issues

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with ❤️ by the SmartMemory Team**

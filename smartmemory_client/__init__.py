"""
SmartMemory Python Client

Official Python client for the SmartMemory Service API.

Installation:
    pip install smartmemory-client

Usage:
    from smartmemory_client import SmartMemoryClient

    client = SmartMemoryClient(
        base_url="http://localhost:9001",
        api_key="your_jwt_token"
    )

    # Add memory
    item_id = client.add("Test memory")

    # Search
    results = client.search("test", top_k=5)

    # Ingest
    result = client.ingest(
        content="Complex content",
        extractor_name="llm",
        context={"key": "value"}
    )

For more information:
    https://github.com/smartmemory/smart-memory-client
    https://docs.smartmemory.dev
"""

from smartmemory_client.client import SmartMemoryClient, SmartMemoryClientError

__version__ = "1.0.0"
__all__ = ["SmartMemoryClient", "SmartMemoryClientError"]

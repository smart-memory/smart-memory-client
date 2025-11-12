"""Tests for SmartMemory Client"""

import pytest
from smartmemory_client import SmartMemoryClient, SmartMemoryClientError


def test_client_initialization():
    """Test client can be initialized"""
    client = SmartMemoryClient("http://localhost:9001")
    assert client.base_url == "http://localhost:9001"
    assert client.api_key is None


def test_client_initialization_with_api_key():
    """Test client can be initialized with API key"""
    client = SmartMemoryClient("http://localhost:9001", api_key="test_token")
    assert client.base_url == "http://localhost:9001"
    assert client.api_key == "test_token"


def test_client_repr():
    """Test client string representation"""
    client = SmartMemoryClient("http://localhost:9001")
    assert "SmartMemoryClient" in repr(client)
    assert "unauthenticated" in repr(client)
    
    client_with_auth = SmartMemoryClient("http://localhost:9001", api_key="token")
    assert "authenticated" in repr(client_with_auth)


def test_client_context_manager():
    """Test client can be used as context manager"""
    with SmartMemoryClient("http://localhost:9001") as client:
        assert client is not None


def test_smartmemory_client_error():
    """Test SmartMemoryClientError exception"""
    with pytest.raises(SmartMemoryClientError):
        raise SmartMemoryClientError("Test error")


# Integration tests (require running service)
@pytest.mark.integration
def test_health_check():
    """Test health check endpoint"""
    client = SmartMemoryClient("http://localhost:9001")
    health = client.health_check()
    assert health["status"] == "healthy"


@pytest.mark.integration
def test_add_memory_requires_auth():
    """Test that add memory requires authentication"""
    client = SmartMemoryClient("http://localhost:9001")
    with pytest.raises(SmartMemoryClientError):
        client.add("Test memory")


@pytest.mark.integration
def test_search_requires_auth():
    """Test that search requires authentication"""
    client = SmartMemoryClient("http://localhost:9001")
    with pytest.raises(SmartMemoryClientError):
        client.search("test")

"""
Test configuration for smart-memory-client.

Provides fixtures for both unit tests and integration tests.
Integration tests require a running smart-memory-service.
"""

import os
import uuid

import pytest
import httpx


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require running service)",
    )
    config.addinivalue_line(
        "markers", "golden: marks tests as golden flow tests (critical user journeys)"
    )
    config.addinivalue_line(
        "markers", "contract: marks tests as contract tests (API stability)"
    )
    config.addinivalue_line("markers", "harness: marks tests as error harness tests")
    config.addinivalue_line(
        "markers", "invariant: marks tests as invariant tests (logic kernels)"
    )
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (require external services)"
    )


# Default service URL for integration tests
SERVICE_URL = os.getenv("SMARTMEMORY_SERVICE_URL", "http://localhost:9001")


def _cleanup_test_users_best_effort():
    """Best-effort cleanup for prefixed test users.

    Uses shared service_common helper when available (monorepo runs),
    otherwise silently skips to avoid blocking standalone client tests.
    """
    try:
        from service_common.testing import cleanup_test_users

        cleanup_test_users(["test-", "test_", "sso_smoke_"])
    except Exception:
        pass


@pytest.fixture(scope="session")
def service_url():
    """Base URL for the SmartMemory service."""
    return SERVICE_URL


@pytest.fixture(scope="session")
def service_available(service_url):
    """Check if the service is available. Skip tests if not."""
    try:
        resp = httpx.get(f"{service_url}/health", timeout=5.0)
        if resp.status_code == 200:
            return True
    except Exception:
        pass
    pytest.skip(f"SmartMemory service not available at {service_url}")


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_users_session():
    _cleanup_test_users_best_effort()
    yield
    _cleanup_test_users_best_effort()


@pytest.fixture(scope="class")
def test_user(service_url, service_available):
    """Create a unique test user via signup.

    Returns dict with:
        - email: test user email
        - password: test user password
        - access_token: JWT token for authentication
        - workspace_id: workspace ID for the user
    """
    unique_id = uuid.uuid4().hex[:8]
    email = f"test_{unique_id}@example.com"
    password = "TestPassword123!"

    # Sign up the user
    signup_data = {
        "email": email,
        "password": password,
        "name": f"Test User {unique_id}",
    }

    resp = httpx.post(f"{service_url}/auth/signup", json=signup_data, timeout=10.0)
    if resp.status_code not in (200, 201):
        pytest.fail(f"Failed to sign up test user: {resp.status_code} {resp.text}")

    data = resp.json()

    # Extract tokens - may be nested under "tokens"
    tokens = data.get("tokens", data)
    user = data.get("user", data)

    return {
        "email": email,
        "password": password,
        "access_token": tokens.get("access_token"),
        "workspace_id": user.get("tenant_id") or data.get("workspace_id"),
        "user_id": user.get("id") or data.get("user_id"),
        "team_id": user.get("default_team_id"),
    }


@pytest.fixture(scope="class")
def authenticated_client(service_url, test_user):
    """Create an authenticated SmartMemoryClient.

    Uses the test user's JWT token for authentication.
    Sets the correct team_id for the user's tenant.
    """
    from smartmemory_client import SmartMemoryClient

    client = SmartMemoryClient(
        base_url=service_url,
        token=test_user["access_token"],
        team_id=test_user["team_id"],
    )

    yield client


@pytest.fixture
def unique_content():
    """Generate unique content for test isolation."""
    return f"Test content {uuid.uuid4().hex[:8]}"

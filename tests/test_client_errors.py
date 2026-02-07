"""Tests for SmartMemory client error handling.

Covers HTTP error codes, connection errors, timeouts, and successful responses.
All HTTP calls are mocked so no running server is required.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from smartmemory_client.client import SmartMemoryClient, SmartMemoryClientError

BASE_URL = "http://localhost:9001"
API_KEY = "test_token_abc123"


@pytest.fixture
def client() -> SmartMemoryClient:
    """Create a SmartMemoryClient configured for testing."""
    return SmartMemoryClient(base_url=BASE_URL, api_key=API_KEY)


def _build_response(
    status_code: int, body: str = "", json_data: dict | None = None
) -> MagicMock:
    """Build a mock httpx.Response with the given status code and body."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = body

    if status_code >= 400:
        request = MagicMock(spec=httpx.Request)
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"{status_code} Error",
            request=request,
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None

    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.return_value = {}

    return resp


class TestHTTPErrorCodes:
    """Verify that HTTP error status codes are translated to SmartMemoryClientError."""

    @patch("smartmemory_client.client.httpx.request")
    def test_400_bad_request_raises_error_with_detail(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        detail_text = '{"detail":"Invalid memory_type value"}'
        mock_request.return_value = _build_response(400, body=detail_text)

        with pytest.raises(SmartMemoryClientError, match="Request failed") as exc_info:
            client._request("POST", "/memory/add", json_body={"content": "x"})

        assert "Invalid memory_type value" in str(exc_info.value)

    @patch("smartmemory_client.client.httpx.request")
    def test_404_not_found_raises_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(404, body="Not found")

        with pytest.raises(SmartMemoryClientError, match="Request failed"):
            client._request("GET", "/memory/nonexistent-id")

    @patch("smartmemory_client.client.httpx.request")
    def test_500_internal_server_error_raises_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(500, body="Internal Server Error")

        with pytest.raises(SmartMemoryClientError, match="Request failed"):
            client._request("GET", "/memory/some-id")

    @patch("smartmemory_client.client.httpx.request")
    def test_422_unprocessable_entity_raises_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        detail_text = (
            '{"detail":[{"msg":"field required","type":"value_error.missing"}]}'
        )
        mock_request.return_value = _build_response(422, body=detail_text)

        with pytest.raises(SmartMemoryClientError, match="Request failed") as exc_info:
            client._request("POST", "/memory/add", json_body={})

        assert "field required" in str(exc_info.value)

    @patch("smartmemory_client.client.httpx.request")
    def test_401_unauthorized_raises_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(401, body="Unauthorized")

        with pytest.raises(SmartMemoryClientError, match="Request failed"):
            client._request("GET", "/memory/some-id")

    @patch("smartmemory_client.client.httpx.request")
    def test_403_forbidden_raises_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(403, body="Forbidden")

        with pytest.raises(SmartMemoryClientError, match="Request failed"):
            client._request("GET", "/memory/some-id")

    @patch("smartmemory_client.client.httpx.request")
    def test_error_detail_included_in_exception_message(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        """The response body text should appear in the exception message as 'Detail:'."""
        error_body = "Memory item not found: abc-123"
        mock_request.return_value = _build_response(404, body=error_body)

        with pytest.raises(
            SmartMemoryClientError, match="Detail:.*Memory item not found"
        ):
            client._request("GET", "/memory/abc-123")


class TestConnectionErrors:
    """Verify that transport-level errors are wrapped in SmartMemoryClientError."""

    @patch("smartmemory_client.client.httpx.request")
    def test_connect_error_raises_client_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(
            SmartMemoryClientError, match="Request failed.*Connection refused"
        ):
            client._request("GET", "/memory/some-id")

    @patch("smartmemory_client.client.httpx.request")
    def test_timeout_error_raises_client_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.side_effect = httpx.TimeoutException("Read timed out")

        with pytest.raises(
            SmartMemoryClientError, match="Request failed.*Read timed out"
        ):
            client._request("GET", "/memory/some-id")

    @patch("smartmemory_client.client.httpx.request")
    def test_generic_exception_raises_client_error(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.side_effect = RuntimeError("Unexpected failure")

        with pytest.raises(
            SmartMemoryClientError, match="Request failed.*Unexpected failure"
        ):
            client._request("GET", "/memory/some-id")


class TestSuccessfulResponses:
    """Verify correct handling of successful HTTP responses."""

    @patch("smartmemory_client.client.httpx.request")
    def test_200_returns_parsed_json(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        expected = {"id": "mem-123", "content": "hello", "memory_type": "semantic"}
        mock_request.return_value = _build_response(200, json_data=expected)

        result = client._request("GET", "/memory/mem-123")

        assert result == expected

    @patch("smartmemory_client.client.httpx.request")
    def test_201_returns_parsed_json(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        expected = {"id": "mem-456"}
        mock_request.return_value = _build_response(201, json_data=expected)

        result = client._request(
            "POST", "/memory/add", json_body={"content": "new memory"}
        )

        assert result == expected

    @patch("smartmemory_client.client.httpx.request")
    def test_204_no_content_returns_none(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(204)

        result = client._request("DELETE", "/memory/mem-123")

        assert result is None

    @patch("smartmemory_client.client.httpx.request")
    def test_200_with_list_response(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        expected = [{"id": "1"}, {"id": "2"}]
        mock_request.return_value = _build_response(200, json_data=expected)

        result = client._request("GET", "/memory/search", params={"query": "test"})

        assert result == expected


class TestRequestArguments:
    """Verify that _request passes correct arguments to httpx.request."""

    @patch("smartmemory_client.client.httpx.request")
    def test_passes_correct_url(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(200, json_data={})

        client._request("GET", "/memory/items")

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[0][1] == f"{BASE_URL}/memory/items"

    @patch("smartmemory_client.client.httpx.request")
    def test_passes_authorization_header(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(200, json_data={})

        client._request("GET", "/memory/items")

        call_kwargs = mock_request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert headers["Authorization"] == f"Bearer {API_KEY}"

    @patch("smartmemory_client.client.httpx.request")
    def test_passes_team_id_header(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(200, json_data={})

        client._request("GET", "/memory/items")

        call_kwargs = mock_request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert "X-Team-Id" in headers

    @patch("smartmemory_client.client.httpx.request")
    def test_passes_json_body(self, mock_request: MagicMock, client: SmartMemoryClient):
        mock_request.return_value = _build_response(200, json_data={"id": "new"})
        body = {"content": "test memory", "memory_type": "semantic"}

        client._request("POST", "/memory/add", json_body=body)

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs.get("json") == body

    @patch("smartmemory_client.client.httpx.request")
    def test_passes_query_params(
        self, mock_request: MagicMock, client: SmartMemoryClient
    ):
        mock_request.return_value = _build_response(200, json_data=[])
        params = {"query": "test", "top_k": 5}

        client._request("GET", "/memory/search", params=params)

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs.get("params") == params

    @patch("smartmemory_client.client.httpx.request")
    def test_passes_timeout(self, mock_request: MagicMock, client: SmartMemoryClient):
        mock_request.return_value = _build_response(200, json_data={})

        client._request("GET", "/memory/items")

        call_kwargs = mock_request.call_args
        assert call_kwargs.kwargs.get("timeout") == client.timeout

    @patch("smartmemory_client.client.httpx.request")
    def test_no_auth_header_when_no_api_key(self, mock_request: MagicMock):
        """Client without api_key should not send Authorization header."""
        no_auth_client = SmartMemoryClient(base_url=BASE_URL)
        mock_request.return_value = _build_response(200, json_data={})

        no_auth_client._request("GET", "/memory/items")

        call_kwargs = mock_request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert "Authorization" not in headers

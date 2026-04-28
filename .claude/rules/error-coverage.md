# Error Test Coverage Rules

## Required Error Status Codes
Every public SDK method must have tests covering:
- **Happy path** (200/201) — at least one test
- **404** — resource not found
- **400** — validation error / bad request
- **500** — server error

## Pattern
```python
class TestErrorHandling:
    @patch("smartmemory_client.client.httpx.request")
    def test_resource_not_found(self, mock_req, client):
        resp = MagicMock()
        resp.status_code = 404
        resp.text = "Not found"
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=resp
        )
        mock_req.return_value = resp
        with pytest.raises(SmartMemoryClientError, match="Request failed"):
            client.get_resource("nonexistent")

    @patch("smartmemory_client.client.httpx.request")
    def test_bad_request(self, mock_req, client):
        # Same pattern with status_code=400

    @patch("smartmemory_client.client.httpx.request")
    def test_server_error(self, mock_req, client):
        # Same pattern with status_code=500
```

## Shared Contracts
- Before implementing SDK methods, read the relevant contract (check `docs/features/<FEATURE-ID>/` first, then legacy `/contracts/`)
- New contracts go in `smart-memory-docs/docs/features/<FEATURE-ID>/`; legacy `/contracts/` is not git-tracked
- Use the EXACT field names and enum values from contracts in tests

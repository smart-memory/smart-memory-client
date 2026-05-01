# Error Test Coverage Rules

## Required Error Status Codes
Every public SDK method must have tests covering:
- **Happy path** (200/201) — at least one test
- **404** — resource not found
- **400** — validation error / bad request
- **500** — server error

When the method has authn/authz semantics, also cover **401/403**.

## Typed Exception Hierarchy (SDK-CONSISTENCY-1 B3)

The SDK raises typed subclasses of `SmartMemoryClientError` based on HTTP status:

| Status            | Exception                       |
|-------------------|---------------------------------|
| 401, 403          | `SmartMemoryPermissionError`    |
| 400, 409, 422     | `SmartMemoryValidationError`    |
| 404               | `SmartMemoryNotFoundError`      |
| 5xx               | `SmartMemoryServerError`        |
| transport / other | `SmartMemoryClientError` (base) |

All subclasses inherit from `SmartMemoryClientError`, so existing `pytest.raises(SmartMemoryClientError)` assertions continue to pass. Prefer typed assertions in new code.

## Pattern (typed — preferred for new tests)

```python
from smartmemory_client import (
    SmartMemoryNotFoundError,
    SmartMemoryPermissionError,
    SmartMemoryValidationError,
    SmartMemoryServerError,
)

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
        with pytest.raises(SmartMemoryNotFoundError) as exc_info:
            client.get_resource("nonexistent")
        assert exc_info.value.status_code == 404

    @patch("smartmemory_client.client.httpx.request")
    def test_bad_request(self, mock_req, client):
        # Same pattern with status_code=400 → SmartMemoryValidationError

    @patch("smartmemory_client.client.httpx.request")
    def test_server_error(self, mock_req, client):
        # Same pattern with status_code=500 → SmartMemoryServerError
```

## Pattern (legacy — still passes)

```python
with pytest.raises(SmartMemoryClientError, match="Request failed"):
    client.get_resource("nonexistent")
```

This still works because typed exceptions inherit from `SmartMemoryClientError` and preserve the `"Request failed: ..."` message prefix. Migrate to typed assertions when touching the test.

## get/update/delete raise (do not return sentinels)

`client.get(item_id)` → `MemoryItem` (raises on missing/forbidden, never returns `None`).
`client.update(item_id, ...)` → `None` (raises on failure, never returns `False`).
`client.delete(item_id)` → `None` (raises on failure, never returns `False`).

This was changed in 0.6.0 (SDK-CONSISTENCY-1 B3). Prior versions silently swallowed `Exception` and returned sentinel values, hiding 404/403/500 distinctions from callers.

## Shared Contracts
- Before implementing SDK methods, read the relevant contract (check `docs/features/<FEATURE-ID>/` first, then legacy `/contracts/`)
- New contracts go in `smart-memory-docs/docs/features/<FEATURE-ID>/`; legacy `/contracts/` is not git-tracked
- Use the EXACT field names and enum values from contracts in tests

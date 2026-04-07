# Testing Guide (Backend)

> How to run, write, and interpret tests for the FixMyText backend.

## Stack

| Tool | Role |
|------|------|
| [pytest](https://docs.pytest.org/) | Test runner |
| [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) | Async test support |
| [pytest-cov](https://pytest-cov.readthedocs.io/) | Coverage reporting |
| [httpx](https://www.python-httpx.org/) | HTTP client for async tests |
| [unittest.mock](https://docs.python.org/3/library/unittest.mock.html) | Mocking (DB sessions, external services) |

---

## Setup

All commands must be run from the `backend/` directory.

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or, if `.venv` already exists:

```bash
source .venv/bin/activate
```

---

## Running Tests

### Run all tests once

```bash
pytest tests/
```

### Run all tests with coverage report

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

Coverage thresholds are enforced — the command exits with a non-zero code if total coverage falls below **70%**.

To explicitly fail below 70%:

```bash
pytest tests/ --cov=app --cov-fail-under=70
```

### Run a single test file

```bash
pytest tests/test_auth.py
```

### Run tests matching a name pattern

```bash
pytest tests/ -k "register"
```

### Verbose output

```bash
pytest tests/ -v
```

### Combine flags

```bash
pytest tests/test_auth.py -v --tb=short
```

---

## Coverage Report

After running with `--cov`, two outputs are produced:

| Output | Location | Use |
|--------|----------|-----|
| Terminal summary | Printed after tests | Quick pass/fail check |
| HTML report | `htmlcov/index.html` | Line-by-line visual breakdown |

To generate the HTML report:

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html     # macOS
xdg-open htmlcov/index.html # Linux
```

---

## Test File Conventions

- Test files live in `tests/`
- Naming: `test_<module>.py` or `test_<feature>.py`
- Test functions: `test_<what_it_tests>()`

```
tests/
  conftest.py                    ← shared fixtures (mock DB, fake user, TestClient)
  test_auth.py                   ← /auth/* endpoints + auth_service unit tests
  test_deps.py                   ← auth dependency (get_current_user, get_optional_user)
  test_endpoints.py              ← legacy text endpoint smoke tests
  test_history.py                ← /history/* endpoints
  test_security.py               ← JWT tokens, password hashing
  test_services.py               ← pass_service, region_service, razorpay_service
  test_share.py                  ← /share/* endpoints
  test_text_endpoints.py         ← /text/* endpoints (local + AI mocked)
  test_text_service.py           ← text_service pure unit tests
  test_text_service_extended.py  ← additional text_service coverage
  test_user_data.py              ← /user/* endpoints
```

---

## Architecture: Mock-Based Testing

Tests do **not** require a running PostgreSQL database or external API keys. All external dependencies are replaced with mocks via FastAPI's [dependency injection override](https://fastapi.tiangolo.com/advanced/testing-dependencies/).

### Key fixtures (`tests/conftest.py`)

| Fixture | What it provides |
|---------|-----------------|
| `fake_user` | A `User` ORM instance (no DB required) |
| `mock_db` | An `AsyncMock` SQLAlchemy session |
| `client` | Authenticated `TestClient` (all endpoints work) |
| `anon_client` | Anonymous `TestClient` (no user, no auth header) |
| `unauth_client` | TestClient where `/auth/*` endpoints will 401 |

### How the mock DB works

The `mock_db` fixture returns an `AsyncMock` that mimics `AsyncSession`:

```python
# Scalar query (single value)
mock_db.execute.return_value.scalar.return_value = 0

# List query
mock_db.execute.return_value.scalars.return_value.all.return_value = []

# Get by PK
mock_db.get.return_value = some_orm_object

# Refresh (sets timestamps on new objects)
# Handled automatically by the smart side_effect in conftest.py
```

Override for specific tests:

```python
def test_my_endpoint(client, mock_db):
    from unittest.mock import MagicMock

    result = MagicMock()
    result.scalar.return_value = 42
    mock_db.execute.return_value = result

    resp = client.get("/api/v1/some/endpoint")
    assert resp.status_code == 200
```

### Mocking external services

For AI-powered endpoints, patch the AI service method directly:

```python
from unittest.mock import AsyncMock, patch

def test_summarize_with_mock_ai(client):
    with patch("app.services.ai_service.SummarizerService.summarize", AsyncMock(return_value="Summary.")):
        resp = client.post("/api/v1/text/summarize", json={"text": "Long text..."})
    assert resp.status_code == 200
    assert resp.json()["result"] == "Summary."
```

For tool-access checks (every text endpoint calls these):

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def patch_access_checks():
    _ALLOW = {"allowed": True, "reason": "free"}
    with (
        patch("app.api.v1.endpoints.text.check_tool_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.check_visitor_access", AsyncMock(return_value=_ALLOW)),
        patch("app.api.v1.endpoints.text.record_tool_discovery", AsyncMock()),
    ):
        yield
```

---

## Writing Tests

### Endpoint test (basic pattern)

```python
def test_get_preferences_no_record(client, mock_db):
    mock_db.get.return_value = None  # no existing preferences row
    resp = client.get("/api/v1/user/preferences")
    assert resp.status_code == 200
    data = resp.json()
    assert "theme" in data
```

### Async service unit test

```python
import pytest

@pytest.mark.asyncio
async def test_auth_service_register_new_user():
    from app.services.auth_service import register
    from tests.conftest import make_mock_db
    from unittest.mock import MagicMock

    db = make_mock_db()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # email not taken
    db.execute.return_value = result

    user = await register(db, "new@test.com", "password123", "New User")
    assert user.email == "new@test.com"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
```

### Testing 401 / 404 / 422 errors

```python
def test_history_requires_auth(unauth_client):
    resp = unauth_client.get("/api/v1/history")
    assert resp.status_code == 401

def test_missing_field_returns_422(client):
    resp = client.post("/api/v1/history", json={"tool_id": "uppercase"})  # missing required fields
    assert resp.status_code == 422
```

### Creating ORM instances without a DB

Use the `make_user()` helper from conftest, or the pattern below for other models:

```python
from app.db.models.operation_history import OperationHistory
import uuid
from datetime import datetime, UTC

row = OperationHistory(
    user_id=uuid.uuid4(),
    tool_id="uppercase",
    tool_label="Uppercase",
    tool_type="api",
    input_preview="hello",
    output_preview="HELLO",
    input_length=5,
    output_length=5,
    status="success",
)
row.id = uuid.uuid4()
row.created_at = datetime.now(UTC)
```

> **Note:** Always use the model's `__init__` constructor (e.g., `OperationHistory(...)`) rather than `OperationHistory.__new__(OperationHistory)`. The constructor sets up SQLAlchemy's `_sa_instance_state` which is required for attribute access.

---

## External Services Mocked

| Service | How to mock |
|---------|-------------|
| Groq AI | `patch("app.services.ai_service.SomeService.method", AsyncMock(...))` |
| Razorpay | `patch("app.services.razorpay_service.get_client", ...)` |
| ip-api.com geolocation | `patch("httpx.AsyncClient", ...)` (see `test_services.py`) |
| PostgreSQL | `mock_db` fixture (AsyncMock session) |

---

## Coverage Thresholds

| Metric | Threshold |
|--------|-----------|
| Total statements | 70% |

Coverage is measured only over `app/` (not `main.py` or `alembic/`).

---

## Debugging a Failing Test

1. **Run the single file** with verbose output:
   ```bash
   pytest tests/test_auth.py -v --tb=long
   ```

2. **Add a breakpoint**:
   ```python
   import pdb; pdb.set_trace()
   ```

3. **Print the response body** when a status code is unexpected:
   ```python
   resp = client.post("/api/v1/auth/register", json={...})
   print(resp.json())  # see validation error details
   assert resp.status_code == 200
   ```

4. **Check mock call counts**:
   ```python
   mock_db.commit.assert_awaited_once()
   mock_db.add.assert_called_with(some_object)
   print(mock_db.execute.call_args_list)  # see all execute calls
   ```

5. **Configure call order** for `execute`:
   ```python
   call_count = 0
   async def execute_side_effect(stmt):
       nonlocal call_count
       call_count += 1
       result = MagicMock()
       if call_count == 1:
           result.scalar.return_value = None
       elif call_count == 2:
           result.scalars.return_value.all.return_value = []
       return result
   mock_db.execute.side_effect = execute_side_effect
   ```

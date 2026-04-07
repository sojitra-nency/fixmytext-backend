# Lint & Format Guide (Backend)

> How to check and fix linting and formatting issues in the FixMyText backend.

All commands must be run from the `backend/` directory with the virtual environment activated.

```bash
source .venv/bin/activate
```

The backend uses [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting — it replaces flake8, isort, and black in a single tool.

---

## Configuration

Ruff is configured in `pyproject.toml`:

| Setting | Value |
|---------|-------|
| Target Python | 3.12 |
| Line length | 120 characters |
| Lint rules | `E`, `F`, `W` (PEP 8), `I` (imports), `S` (security), `B` (bugbear), `UP` (modernization) |
| Excluded paths | `.venv/`, `alembic/`, `__pycache__/` |

---

## Check for issues (no changes made)

```bash
# Lint check
ruff check .

# Format check — shows files that would be reformatted
ruff format --check .
```

Both commands exit with a non-zero code if issues are found. This is what CI runs.

---

## Fix issues

```bash
# Auto-fix safe lint violations
ruff check . --fix

# Auto-format all files
ruff format .
```

### Fix everything in one shot

```bash
ruff check . --fix && ruff format .
```

---

## Understand a specific violation

```bash
# Show the rule explanation for a given code (e.g. E501, B008)
ruff rule E501
```

---

## Common violations

| Code | Meaning | Fix |
|------|---------|-----|
| `I001` | Unsorted imports | `ruff check . --fix` |
| `E501` | Line too long (> 120 chars) | Shorten the line manually |
| `F401` | Unused import | Remove it |
| `UP006` | Use `list` instead of `List` (Python 3.9+) | `ruff check . --fix` |
| `B006` | Mutable default argument | Refactor to use `None` |

---

## CI behavior

The lint job runs before tests — a failure blocks the test job.

CI runs (`.github/workflows/ci.yml`):

```bash
ruff check .
ruff format --check .
```

CI does not auto-fix. Fix locally and push again.

---

## Pre-push checklist

```bash
ruff check . --fix && ruff format .
pytest tests/
```

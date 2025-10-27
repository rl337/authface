# UV Project Management Guide

This project uses [`uv`](https://github.com/astral-sh/uv), a fast Python package installer and resolver written in Rust.

## Key Concepts

### 1. **Project Structure**
- `pyproject.toml` - Modern Python project configuration (replaces `setup.py` and `requirements.txt`)
- `.python-version` - Pins the Python version for reproducibility
- `.venv/` - Virtual environment (gitignored)
- `uv.lock` - Lock file for deterministic builds (gitignored)

### 2. **Dependency Management**

In `pyproject.toml`:
```toml
[project]
dependencies = [
    "aiohttp>=3.9.0",
    "torch>=2.2.0",
    # ...
]

[dependency-groups]
dev = [
    "pytest>=8.1.0",
    "mypy>=1.9.0",
]
```

### 3. **Common Commands**

```bash
# Install dependencies (creates .venv if needed)
uv sync

# Run Python with dependencies
uv run python script.py

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev pytest

# Install and run in one command
uv run pytest

# Update all dependencies to latest compatible versions
uv sync --upgrade

# Pin Python version
uv python pin 3.12

# Check which Python version will be used
uv python list
```

## Best Practices

1. **Always use `uv run`** to execute commands in the virtual environment
2. **Pin Python version** with `.python-version` for reproducibility
3. **Use version ranges** in dependencies (e.g., `>=3.9.0`) rather than exact pins
4. **Separate dev dependencies** using `dependency-groups`
5. **Commit `.python-version`** but don't commit `.venv/` or `uv.lock`

## Migration from pip/Poetry

1. Replace `requirements.txt` → `pyproject.toml`
2. Replace `poetry.lock` → `uv.lock` (gitignored)
3. Use `uv sync` instead of `pip install -r requirements.txt`
4. Use `uv run` instead of activating virtual environment

## GitHub Actions Integration

Use the official action:
```yaml
- uses: astral-sh/setup-uv@v4
  with:
    python-version: "3.12"
- run: uv sync
- run: uv run pytest
```


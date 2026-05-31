# Contributing to fzf-ai

Thank you for considering contributing! This document outlines the development workflow.

## Setup

```bash
git clone https://github.com/tuxcanfly/fzf-ai
cd fzf-ai

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest  # for running tests
```

## Development

### Project Structure

```
bin/
├── fzf-ai              # Main launcher (bash, fzf bindings)
├── fzf-ai-index        # Session indexer (Python)
├── fzf-ai-preview      # Preview renderer (Python)
├── fzf-ai-resume       # Session resumer (bash)
├── fzf-ai-ui           # Dynamic UI helpers (bash)
├── fzf-ai-actions      # Session management (Python)
├── fzf-ai-highlight    # Code syntax highlighter (Python)
├── fzf-ai-stats        # Usage analytics dashboard (Python)
└── stores/
    ├── __init__.py      # Plugin discovery mechanism
    └── EXAMPLE.py       # Plugin template
tests/
├── conftest.py          # Shared fixtures & factory functions
└── unit/
    ├── test_indexer.py  # 70 tests
    ├── test_previewer.py # 48 tests
    ├── test_ui.py       # 27 tests
    ├── test_resume.py   # 13 tests
    ├── test_highlight.py # 8 tests
    ├── test_actions.py  # 14 tests
    ├── test_stats.py    # 5 tests
    └── test_plugins.py  # 7 tests
```

### Running Tests

```bash
# Run all tests
PYTHONPATH="$PWD/bin" python -m pytest tests/

# Run with coverage
PYTHONPATH="$PWD/bin" python -m pytest tests/ -v --tb=short

# Run a specific test file
PYTHONPATH="$PWD/bin" python -m pytest tests/unit/test_indexer.py

# Run quickly (exclude slow integration tests)
PYTHONPATH="$PWD/bin" python -m pytest tests/ -m "not slow"
```

### Adding a New Agent

Create a plugin in `bin/stores/`:

```python
# stores/my_agent.py
from fzf_ai_index import Record, _parallel_read, _JSON_LOADS, stdjson
from pathlib import Path

SESSION_DIR = Path.home() / ".my_agent" / "sessions"

def walk(cache: dict | None = None):
    for path in SESSION_DIR.glob("*.jsonl"):
        rec = Record(agent="my-agent", session_id=path.stem, source=str(path))
        rec.title = "my session"
        rec.msgs = 1
        yield rec
```

Then run: `fzf-ai my-agent`

### Code Style

- Python: Follow PEP 8. Use type hints. Run `ruff check bin/` before committing.
- Bash: Use `set -euo pipefail`. Run `bash -n` to validate syntax.
- Tests: Every new feature needs tests. Use the existing patterns in `tests/`.

### Pull Request Process

1. Run the full test suite: `PYTHONPATH="$PWD/bin" python -m pytest tests/`
2. Add tests for new functionality
3. Update the README if user-facing behaviour changes
4. Make sure CI passes (lint → test → build)

## Architecture Notes

### Index Format (9-column TSV)

```
1 agent-raw  2 session_id  3 source       ← hidden, machine-only
4 agent-badge 5 updated    6 msgs          ← visible, padded + ANSI
7 cwd        8 title                       ← visible
9 search-blob (rendered off-screen)        ← hidden, for content search
```

### Performance Patterns

- **Substring pre-filter**: Check `"type":"user" in line` before JSON decode (5x faster)
- **orjson**: Hard dependency for 2-3x faster JSON decode
- **ProcessPoolExecutor**: True multi-core parallelism for CPU-bound file parsing
- **SQLite JOINs**: Single query replaces 3 separate ones for opencode
- **Index cache**: Avoids re-parsing unchanged files across runs

### Key UX Decisions

- `exec`-after-exit, not `become`: Avoids terminal-state race with some AI CLIs
- Smart-case exact matching by default: Content blob is long; exact matching avoids false positives
- Compact JSON fixtures: Tests use `separators=(",", ":")` to match real agent output

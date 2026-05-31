"""
EXAMPLE: Creating a custom session store plugin for fzf-ai.

Copy this file to a new name (e.g. ``copilot.py``) and implement the
``walk()`` function.  Run ``fzf-ai <your-agent-name>`` to use it.

The ``walk()`` function receives a ``cache`` dict (optional) and
must yield ``Record`` objects.  Import ``Record`` from the indexer.

Minimal example::

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

Then run::

    fzf-ai my-agent
"""

# This file is intentionally not a real plugin — it's documentation.
# The leading "EXAMPLE" in the filename prevents discovery.

"""Plugin system for fzf-ai session stores.

Each agent's session store is a module in this directory that exports
a module-level ``walk()`` generator. The indexer discovers plugins by
scanning this directory.

Plugin API
----------
A plugin module must export a function::

    def walk(cache: dict | None = None, record_builder=None):
        \"\"\"Yield dicts with keys: agent, session_id, source, updated,
        msgs, cwd, title, prompts.\"\"\"

The agent name is derived from the filename (e.g. ``stores/claude.py``
→ agent ``claude``).

The ``record_builder`` is a callable ``(agent, session_id, source) ->
Record`` provided by the indexer, with methods ``add_search_text(text)``,
``add_prompt(text)``, and ``as_row() -> str``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Iterator


WalkFn = Callable[..., Iterator[dict[str, Any]]]
StorePlugin = tuple[str, WalkFn]


def discover_stores(store_dir: Path | None = None) -> dict[str, WalkFn]:
    """Discover store plugins in the stores/ directory.

    Returns a dict mapping agent name to walk function.
    """
    if store_dir is None:
        store_dir = Path(__file__).resolve().parent

    stores: dict[str, WalkFn] = {}
    for entry in sorted(store_dir.iterdir()):
        if entry.suffix != ".py" or entry.stem == "__init__":
            continue
        mod_name = f"_fzfaistore_{entry.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, entry)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            continue

        walk_fn = getattr(mod, "walk", None)
        if walk_fn is None or not callable(walk_fn):
            continue
        stores[entry.stem] = walk_fn

    return stores

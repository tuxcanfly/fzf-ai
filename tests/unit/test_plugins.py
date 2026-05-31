"""Tests for the store plugin system (bin/stores/__init__.py)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest


def test_discover_stores_imports():
    """stores module should import without error."""
    from stores import discover_stores
    assert callable(discover_stores)


def test_discover_stores_finds_nothing_in_empty_dir(tmp_path: Path):
    """An empty directory should produce no plugins."""
    from stores import discover_stores
    plugins = discover_stores(tmp_path)
    assert isinstance(plugins, dict)
    assert len(plugins) == 0


def test_discover_stores_skips_init(tmp_path: Path):
    """__init__.py should not be treated as a plugin."""
    (tmp_path / "__init__.py").write_text("")
    from stores import discover_stores
    plugins = discover_stores(tmp_path)
    assert "__init__" not in plugins


def test_discover_stores_loads_walk_function(tmp_path: Path):
    """A .py file with a walk() function should be discovered."""
    plugin = tmp_path / "testagent.py"
    plugin.write_text("""
def walk(cache=None):
    yield {"agent": "testagent", "session_id": "s1", "source": "/tmp/s1.jsonl"}
""")
    from stores import discover_stores
    plugins = discover_stores(tmp_path)
    assert "testagent" in plugins


def test_discover_stores_skips_no_walk(tmp_path: Path):
    """A .py file without walk() should be skipped."""
    plugin = tmp_path / "noop.py"
    plugin.write_text("# no walk function")
    from stores import discover_stores
    plugins = discover_stores(tmp_path)
    assert "noop" not in plugins


def test_plugin_execution(tmp_path: Path):
    """A discovered plugin's walk() should yield records."""
    plugin = tmp_path / "testagent.py"
    plugin.write_text("""
def walk(cache=None):
    yield {"agent": "testagent", "session_id": "s1", "source": "/tmp/s1.jsonl", "msgs": 3}
    yield {"agent": "testagent", "session_id": "s2", "source": "/tmp/s2.jsonl", "msgs": 5}
""")
    from stores import discover_stores
    plugins = discover_stores(tmp_path)
    fn = plugins["testagent"]
    records = list(fn())
    assert len(records) == 2
    assert records[0]["session_id"] == "s1"
    assert records[1]["msgs"] == 5


def test_plugin_import_from_indexer():
    """The plugin system should be importable from the indexer's context."""
    # Use the same symlink technique as test_indexer
    _SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-index"
    _LINK = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf_ai_index.py"
    if not _LINK.is_file() and not _LINK.is_symlink():
        _LINK.symlink_to(_SCRIPT.name)
        import atexit
        atexit.register(lambda: _LINK.unlink(missing_ok=True))
    sys.path.insert(0, str(_LINK.parent))
    try:
        import fzf_ai_index as idx
        # Built-in walkers should resolve
        claude = idx._resolve_walker("claude")
        assert claude is not None
        # Unknown agent should return None
        unknown = idx._resolve_walker("nonexistent_agent_xyz")
        assert unknown is None
    finally:
        sys.path.pop(0)

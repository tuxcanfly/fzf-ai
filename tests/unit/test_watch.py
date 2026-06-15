"""Unit tests for fzf-ai-watch (bin/fzf-ai-watch)."""

from __future__ import annotations

import signal
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.conftest import _j, claude_prompt

# The watch script has a hyphen in its filename, so we create a temporary
# symlink with a Python-valid module name and import through that.
_SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-watch"
_LINK = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf_ai_watch.py"
if not _LINK.is_file() and not _LINK.is_symlink():
    _LINK.symlink_to(_SCRIPT.name)
    import atexit
    atexit.register(lambda: _LINK.unlink(missing_ok=True))
sys.path.insert(0, str(_LINK.parent))
import fzf_ai_watch as watch


class TestWatchModule:
    def test_imports_indexer(self):
        """The watcher module should successfully load the indexer."""
        assert hasattr(watch, "_idx_module")
        assert hasattr(watch._idx_module, "WALKERS")

    def test_run_update_populates_cache(
        self, claude_dir: Path, tmp_home: Path, monkeypatch, tmp_path: Path
    ):
        """_run_update should parse files and store them in the SQLite cache."""
        monkeypatch.setattr(watch._idx_module, "HOME", tmp_home)
        monkeypatch.setattr(watch._idx_module, "HOME_STR", str(tmp_home))
        monkeypatch.setattr(watch._idx_module, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(
            watch._idx_module, "_get_index_cache_path", lambda: tmp_path / "index.db"
        )

        path = claude_dir / "p" / "s1.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(_j(claude_prompt("hello")) + "\n")

        watch._run_update(["claude"])

        con = watch._idx_module._open_cache_db()
        try:
            cur = con.execute("SELECT COUNT(*) FROM sources WHERE agent='claude'")
            assert cur.fetchone()[0] == 1
        finally:
            con.close()

    def test_watch_loop_runs_and_stops(self, monkeypatch):
        """The main loop should run at least one update and stop on SIGINT."""
        updates = []

        def _fake_update(agents):
            updates.append(agents)

        monkeypatch.setattr(watch, "_run_update", _fake_update)
        monkeypatch.setattr(watch, "WATCH_INTERVAL", 1)
        monkeypatch.setattr(sys, "argv", ["fzf-ai-watch"])

        def _send_signal_after_short_delay():
            time.sleep(0.1)
            signal.raise_signal(signal.SIGINT)

        t = threading.Thread(target=_send_signal_after_short_delay, daemon=True)
        t.start()

        rc = watch.main()
        assert rc == 0
        assert len(updates) >= 1
        assert set(updates[0]) == set(watch._idx_module.WALKERS.keys())

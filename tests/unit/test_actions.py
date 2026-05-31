"""Tests for fzf-ai-actions (bin/fzf-ai-actions).

Tests cover:
  - Tag add/remove/list
  - Star toggle
  - Delete (trash)
  - Export to markdown
  - Rename
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-actions"


def run_action(*args: str, **env) -> subprocess.CompletedProcess:
    """Run the actions script with given args."""
    merged_env = {
        **{"PATH": "/usr/bin:/bin:/usr/local/bin"},
        **{"XDG_STATE_HOME": str(Path.cwd())},
        **(env or {}),
    }
    result = subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=5,
        env=merged_env,
    )
    return result


# ============================================================================
# Tag tests
# ============================================================================

class TestTag:
    def test_add_tag(self, tmp_path: Path):
        os.environ["XDG_STATE_HOME"] = str(tmp_path)
        result = run_action("tag", "sid-1", "/tmp/session.jsonl", "important",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Added" in result.stdout

        # Verify persisted
        tags_file = tmp_path / "fzf-ai" / "tags.json"
        assert tags_file.is_file()
        data = json.loads(tags_file.read_text())
        assert data["sid-1"] == ["important"]

    def test_remove_tag(self, tmp_path: Path):
        os.environ["XDG_STATE_HOME"] = str(tmp_path)
        run_action("tag", "sid-1", "/tmp/s.jsonl", "important",
                   XDG_STATE_HOME=str(tmp_path))
        result = run_action("tag", "sid-1", "/tmp/s.jsonl", "important",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Removed" in result.stdout

    def test_list_tags_empty(self, tmp_path: Path):
        result = run_action("list-tags", XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0

    def test_list_tags_with_data(self, tmp_path: Path):
        run_action("tag", "sid-1", "/tmp/s.jsonl", "important",
                   XDG_STATE_HOME=str(tmp_path))
        run_action("tag", "sid-2", "/tmp/s2.jsonl", "bug",
                   XDG_STATE_HOME=str(tmp_path))
        result = run_action("list-tags", XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "sid-1" in result.stdout or "sid-2" in result.stdout


# ============================================================================
# Star tests
# ============================================================================

class TestStar:
    def test_star_session(self, tmp_path: Path):
        result = run_action("star", "sid-1", "/tmp/s.jsonl",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Starred" in result.stdout

    def test_unstar_session(self, tmp_path: Path):
        run_action("star", "sid-1", "/tmp/s.jsonl",
                   XDG_STATE_HOME=str(tmp_path))
        result = run_action("star", "sid-1", "/tmp/s.jsonl",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Unstarred" in result.stdout


# ============================================================================
# Delete tests
# ============================================================================

class TestDelete:
    def test_delete_missing_file(self, tmp_path: Path):
        result = run_action("delete", "sid-1", "/tmp/nonexistent.jsonl",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode != 0

    def test_delete_session(self, tmp_path: Path):
        session_file = tmp_path / "session.jsonl"
        session_file.write_text("{}\n")
        result = run_action("delete", "sid-1", str(session_file),
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Deleted" in result.stdout
        # File should be moved, not deleted in place
        assert not session_file.is_file()

    def test_delete_sqlite(self, tmp_path: Path):
        result = run_action("delete", "sid-1", "sqlite:/tmp/test.db",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode != 0
        assert "Cannot delete" in result.stderr


# ============================================================================
# Export tests
# ============================================================================

class TestExport:
    def test_export_missing(self, tmp_path: Path):
        result = run_action("export", "sid-1", "/tmp/nonexistent.jsonl",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode != 0

    def test_export_session(self, tmp_path: Path):
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"hello"}]}}\n'
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"world"}]}}\n'
        )
        result = run_action("export", "sid-1", str(session_file),
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Exported" in result.stdout

        # Check the export file
        export_dir = tmp_path / "fzf-ai" / "exports"
        assert list(export_dir.glob("*.md"))


# ============================================================================
# Rename tests
# ============================================================================

class TestRename:
    def test_rename_session(self, tmp_path: Path):
        result = run_action("rename", "sid-1", "/tmp/s.jsonl", "My Session",
                           XDG_STATE_HOME=str(tmp_path))
        assert result.returncode == 0
        assert "Renamed" in result.stdout


# ============================================================================
# Help / error
# ============================================================================

class TestErrors:
    def test_no_args(self):
        result = run_action()
        assert result.returncode != 0

    def test_unknown_command(self):
        result = run_action("foobar")
        assert result.returncode != 0

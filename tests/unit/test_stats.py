"""Tests for fzf-ai-stats (bin/fzf-ai-stats)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-stats"


def test_stats_script_exists():
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & 0o111  # executable


def test_stats_json_output(tmp_path: Path):
    """Run with --json flag and validates the output structure."""
    result = subprocess.run(
        [str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **{"PATH": "/usr/bin:/bin:/usr/local/bin"},
            "XDG_CACHE_HOME": str(tmp_path),
            "XDG_STATE_HOME": str(tmp_path),
        },
    )
    # Should not crash — may return "no data" or actual stats
    assert result.returncode == 0


def test_stats_with_cache(tmp_path: Path):
    """Create a minimal cache and verify stats parse it."""
    cache_dir = tmp_path / "fzf-ai"
    cache_dir.mkdir(parents=True)

    # Write a minimal index cache
    cache = {
        "v": 1,
        "sources": {
            "/tmp/session1.jsonl": {
                "mtime": 1000.0,
                "size": 100,
                "source": "/tmp/session1.jsonl",
                "records": [
                    {
                        "agent": "claude",
                        "session_id": "s1",
                        "source": "/tmp/s1.jsonl",
                        "updated": 1776420000.0,
                        "msgs": 5,
                        "cwd": "/home/user/proj1",
                        "title": "refactor auth",
                        "prompts": ["refactor auth"],
                    },
                    {
                        "agent": "codex",
                        "session_id": "s2",
                        "source": "/tmp/s2.jsonl",
                        "updated": 1776506400.0,
                        "msgs": 10,
                        "cwd": "/home/user/proj2",
                        "title": "fix bug",
                        "prompts": ["fix bug"],
                    },
                ],
            },
        },
    }
    cache_file = cache_dir / "index.json"
    cache_file.write_text(json.dumps(cache))

    # Test JSON output
    result = subprocess.run(
        [str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **{"PATH": "/usr/bin:/bin:/usr/local/bin"},
            "XDG_CACHE_HOME": str(tmp_path),
            "XDG_STATE_HOME": str(tmp_path),
        },
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["total_sessions"] == 2
    assert data["total_messages"] == 15
    assert data["total_projects"] == 2
    assert data["agents"]["claude"] == 1
    assert data["agents"]["codex"] == 1

    # Test terminal output
    result2 = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **{"PATH": "/usr/bin:/bin:/usr/local/bin"},
            "XDG_CACHE_HOME": str(tmp_path),
            "XDG_STATE_HOME": str(tmp_path),
        },
    )
    assert result2.returncode == 0
    assert "claude" in result2.stdout.lower()
    assert "sessions" in result2.stdout.lower()
    assert "projects" in result2.stdout.lower()


def test_stats_empty_cache(tmp_path: Path):
    """Empty cache directory should produce a helpful message."""
    result = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **{"PATH": "/usr/bin:/bin:/usr/local/bin"},
            "XDG_CACHE_HOME": str(tmp_path),
            "XDG_STATE_HOME": str(tmp_path),
        },
    )
    assert result.returncode == 0
    assert "data" in result.stdout.lower() or "session" in result.stdout.lower()


def test_stats_days_filter(tmp_path: Path):
    """--days flag filters to recent sessions only."""
    cache_dir = tmp_path / "fzf-ai"
    cache_dir.mkdir(parents=True)

    # One session from long ago, one recent
    import time as _time
    now = _time.time()  # actual current timestamp
    cache = {
        "v": 1,
        "sources": {
            "/tmp/old.jsonl": {
                "mtime": 1000.0,
                "size": 100,
                "source": "/tmp/old.jsonl",
                "records": [
                    {
                        "agent": "claude",
                        "session_id": "old",
                        "source": "/tmp/old.jsonl",
                        "updated": now - 86400 * 30,  # 30 days ago
                        "msgs": 5,
                        "cwd": "/p",
                        "title": "old",
                        "prompts": ["old"],
                    },
                ],
            },
            "/tmp/new.jsonl": {
                "mtime": 1000.0,
                "size": 100,
                "source": "/tmp/new.jsonl",
                "records": [
                    {
                        "agent": "codex",
                        "session_id": "new",
                        "source": "/tmp/new.jsonl",
                        "updated": now - 86400 * 2,  # 2 days ago
                        "msgs": 3,
                        "cwd": "/p",
                        "title": "new",
                        "prompts": ["new"],
                    },
                ],
            },
        },
    }
    cache_file = cache_dir / "index.json"
    cache_file.write_text(json.dumps(cache))

    result = subprocess.run(
        [str(SCRIPT), "--json", "--days", "7"],
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **{"PATH": "/usr/bin:/bin:/usr/local/bin"},
            "XDG_CACHE_HOME": str(tmp_path),
            "XDG_STATE_HOME": str(tmp_path),
        },
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["total_sessions"] == 1  # only the recent one
    assert data["agents"].get("codex") == 1

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

    # Write a minimal TSV snapshot matching the indexer output format.
    # Columns: agent session_id source agent-badge updated msgs cwd title [blob]
    rows = [
        "claude\ts1\t/tmp/s1.jsonl\tclaude  \t2026-04-17 10:00\t   5\t/home/user/proj1\trefactor auth",
        "codex\ts2\t/tmp/s2.jsonl\tcodex   \t2026-04-18 10:00\t  10\t/home/user/proj2\tfix bug",
    ]
    cache_file = cache_dir / "index.tsv"
    cache_file.write_text("\n".join(rows) + "\n")

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
    from datetime import datetime, timezone
    now = _time.time()
    old_ts = now - 86400 * 30
    new_ts = now - 86400 * 2

    def _fmt(epoch: float) -> str:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    rows = [
        f"claude\told\t/tmp/old.jsonl\tclaude  \t{_fmt(old_ts)}\t   5\t/p\told",
        f"codex\tnew\t/tmp/new.jsonl\tcodex   \t{_fmt(new_ts)}\t   3\t/p\tnew",
    ]
    cache_file = cache_dir / "index.tsv"
    cache_file.write_text("\n".join(rows) + "\n")

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

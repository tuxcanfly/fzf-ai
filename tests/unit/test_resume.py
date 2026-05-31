"""Unit tests for fzf-ai-resume (bin/fzf-ai-resume).

Tests cover:
  - Agent dispatch for claude, codex, opencode, droid, pi
  - --print-cmd mode
  - cwd expansion (tilde → $HOME)
  - Error handling for unknown agents
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-resume"


def run_resume(*args: str, cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the resume script with given args. Always uses --print-cmd for safety."""
    merged_env = {**{"PATH": "/usr/bin:/bin:/usr/local/bin"}, **(env or {})}
    result = subprocess.run(
        [str(SCRIPT), "--print-cmd", *args],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=cwd or str(Path.home()),
        env=merged_env,
    )
    return result


# ============================================================================
# Agent dispatch
# ============================================================================

class TestClaude:
    def test_resume_cmd(self):
        result = run_resume("claude", "sid-123", "/tmp/test.jsonl", "/home/user/proj")
        assert result.returncode == 0
        assert "claude" in result.stdout
        assert "--resume" in result.stdout
        assert "sid-123" in result.stdout

    def test_resume_cmd_no_cwd(self):
        result = run_resume("claude", "sid-123", "/tmp/test.jsonl")
        assert result.returncode == 0
        assert "claude" in result.stdout


class TestCodex:
    def test_resume_cmd_with_cwd(self):
        result = run_resume("codex", "sid-123", "/tmp/test.jsonl", "/home/user/proj")
        assert result.returncode == 0
        assert "codex" in result.stdout
        assert "resume" in result.stdout

    def test_resume_cmd_no_cwd(self):
        result = run_resume("codex", "sid-123", "/tmp/test.jsonl", "")
        assert result.returncode == 0
        assert "codex" in result.stdout


class TestOpencode:
    def test_resume_cmd_with_cwd(self):
        result = run_resume("opencode", "sid-123", "sqlite:/tmp/test.db", "/home/user/proj")
        assert result.returncode == 0
        assert "opencode" in result.stdout
        assert "--session" in result.stdout

    def test_resume_cmd_no_cwd(self):
        result = run_resume("opencode", "sid-123", "sqlite:/tmp/test.db", "")
        assert result.returncode == 0
        assert "opencode" in result.stdout


class TestDroid:
    def test_resume_cmd(self):
        result = run_resume("droid", "sid-123", "/tmp/test.jsonl", "/home/user/proj")
        assert result.returncode == 0
        assert "droid" in result.stdout
        assert "--resume" in result.stdout


class TestPi:
    def test_resume_cmd_with_source(self, tmp_path: Path):
        source = tmp_path / "session.jsonl"
        source.write_text("{}")
        result = run_resume("pi", "sid-123", str(source))
        assert result.returncode == 0
        assert "pi" in result.stdout
        assert "--session" in result.stdout

    def test_resume_cmd_no_source(self):
        result = run_resume("pi", "sid-123", "")
        assert result.returncode == 0
        assert "pi" in result.stdout
        # Without a valid source file, falls back to --resume
        assert "--resume" in result.stdout


# ============================================================================
# Error handling
# ============================================================================

class TestErrors:
    def test_unknown_agent(self):
        result = run_resume("unknown-agent", "sid-123", "/tmp/test.jsonl")
        assert result.returncode != 0
        assert "unknown" in result.stderr.lower()

    def test_missing_agent_arg(self):
        result = run_resume()
        assert result.returncode != 0


# ============================================================================
# ~ expansion
# ============================================================================

class TestTildeExpansion:
    def test_tilde_only(self):
        result = run_resume("claude", "sid-1", "/tmp/x.jsonl", "~",
                           env={"HOME": "/home/testuser"})
        assert result.returncode == 0

    def test_tilde_path(self):
        result = run_resume("claude", "sid-1", "/tmp/x.jsonl", "~/proj",
                           env={"HOME": "/home/testuser"})
        assert result.returncode == 0

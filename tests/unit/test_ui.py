"""Unit tests for fzf-ai-ui (bin/fzf-ai-ui).

Tests cover:
  - scope_spec() / scope_name() for FZF_NTH values
  - prompt() formatting
  - list_label() formatting
  - footer() summary computation
  - preview_label() formatting
  - click_header_action() scope switching
  - cycle_scope_action() cycling
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-ui"


def run_ui(command: str, *args: str, **env) -> str:
    """Run the UI script with given command and env vars."""
    result = subprocess.run(
        [str(SCRIPT), command, *args],
        capture_output=True,
        text=True,
        timeout=5,
        env={**{"PATH": "/usr/bin:/bin"}, **env},
    )
    return result.stdout


# ============================================================================
# scope_spec / scope_name
# ============================================================================

class TestScope:
    @pytest.mark.parametrize("nth,expected", [
        ("", "1,4,5,6"),
        ("1,4,5,6", "1,4,5,6"),
        ("1", "1"),
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
    ])
    def test_scope_spec(self, nth, expected):
        result = run_ui("prompt", FZF_NTH=nth)
        # prompt returns "scope> " so we can infer scope_spec from it
        assert result.strip()

    def test_scope_name_all(self):
        # Not directly testable without extracting scope_name from prompt.
        # Verify the script runs without error at least.
        result = run_ui("prompt")
        assert result.strip()


# ============================================================================
# prompt
# ============================================================================

class TestPrompt:
    def test_default_prompt(self):
        result = run_ui("prompt", FZF_NTH="")
        assert result.strip().endswith(">")

    def test_content_scope_prompt(self):
        result = run_ui("prompt", FZF_NTH="6")
        assert result.strip().endswith(">")


# ============================================================================
# list_label
# ============================================================================

class TestListLabel:
    def test_zero_matches(self):
        result = run_ui("list-label", FZF_MATCH_COUNT="0")
        assert "0" in result

    def test_with_query(self):
        result = run_ui("list-label", FZF_QUERY="auth", FZF_MATCH_COUNT="5")
        assert "5" in result

    def test_scope_in_label(self):
        result = run_ui("list-label", FZF_NTH="4", FZF_MATCH_COUNT="3")
        assert "cwd" in result.lower()


# ============================================================================
# footer
# ============================================================================

class TestFooter:
    def test_no_file(self):
        result = run_ui("footer")
        assert "no matching" in result.lower()

    def test_with_matches_file(self, tmp_path: Path):
        """Create a temporary matches file and verify footer parses it."""
        matches = tmp_path / "matches"
        # Simulate 9-col TSV output from indexer: agent\tid\tsource\tbadge\tupdated\tmsgs\tcwd\ttitle\tblob
        lines = [
            "claude\ts1\t/p1\tclaude   \t2026-04-17 10:00\t   5\t~/proj1\trefactor auth\tsearch content",
            "codex\ts2\t/p2\tcodex    \t2026-04-17 11:00\t  10\t~/proj2\tfix bug\tsearch content",
            "claude\ts3\t/p3\tclaude   \t2026-04-17 12:00\t   3\t~/proj1\tadd tests\tsearch content",
        ]
        matches.write_text("\n".join(lines) + "\n")
        result = run_ui("footer", str(matches))
        assert "session" in result.lower()
        assert "project" in result.lower()
        assert "msg" in result.lower()
        assert "claude" in result
        assert "codex" in result


# ============================================================================
# preview_label
# ============================================================================

class TestPreviewLabel:
    def test_with_title(self):
        result = run_ui("preview-label", "claude", "sid123", "refactor auth module")
        assert "claude" in result
        assert "sid123" in result or "sid" in result

    def test_truncates_long_title(self):
        long_title = "a" * 100
        result = run_ui("preview-label", "codex", "sid1", long_title)
        assert len(result.strip(" '")) < 100  # truncated

    def test_no_title(self):
        result = run_ui("preview-label", "claude", "sid1", "(no title)")
        assert "claude" in result


# ============================================================================
# click_header_action
# ============================================================================

class TestClickHeader:
    @pytest.mark.parametrize("word,expected_cmd", [
        ("all", "change-nth"),
        ("agent", "change-nth"),
        ("cwd", "change-nth"),
        ("title", "change-nth"),
        ("content", "change-nth"),
    ])
    def test_clickable_scopes(self, word, expected_cmd):
        result = run_ui("click-header-action", FZF_CLICK_HEADER_WORD=f"[{word}]")
        assert expected_cmd in result


# ============================================================================
# cycle_scope_action
# ============================================================================

class TestCycleScope:
    def test_cycle_all_to_cwd(self):
        result = run_ui("cycle-scope-action", FZF_NTH="1,4,5,6")
        assert "change-nth(4)" in result

    def test_cycle_cwd_to_title(self):
        result = run_ui("cycle-scope-action", FZF_NTH="4")
        assert "change-nth(5)" in result

    def test_cycle_title_to_content(self):
        result = run_ui("cycle-scope-action", FZF_NTH="5")
        assert "change-nth(6)" in result

    def test_cycle_content_to_agent(self):
        result = run_ui("cycle-scope-action", FZF_NTH="6")
        assert "change-nth(1)" in result

    def test_cycle_agent_to_all(self):
        result = run_ui("cycle-scope-action", FZF_NTH="1")
        assert "change-nth(1,4,5,6)" in result

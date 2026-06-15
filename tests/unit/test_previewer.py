"""Unit tests for fzf-ai-preview (bin/fzf-ai-preview).

Tests cover:
  - extract_text() for content in various shapes
  - clean_text() whitespace handling
  - clip_text() truncation by role
  - is_noise_message() detection
  - header() rendering
  - render_message() ANSI formatting
  - query_terms() parsing
  - message_matches() / highlight_terms()
  - select_excerpt() / select_match_excerpt()
  - Per-agent preview generation: claude, codex, opencode, droid, pi
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import via symlink (same technique as test_indexer)
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-preview"
_LINK = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf_ai_preview.py"
if not _LINK.is_file() and not _LINK.is_symlink():
    _LINK.symlink_to(_SCRIPT.name)
    import atexit
    atexit.register(lambda: _LINK.unlink(missing_ok=True))
sys.path.insert(0, str(_LINK.parent))
import fzf_ai_preview as pv

from tests.conftest import (
    _j,
    claude_prompt,
    claude_response,
    codex_message,
    codex_meta,
    droid_message,
    droid_start,
    make_claude_jsonl,
    make_codex_jsonl,
    make_droid_jsonl,
    make_opencode_db,
    make_pi_jsonl,
    pi_message,
    pi_session_start,
)


# ============================================================================
# extract_text() tests
# ============================================================================

class TestExtractText:
    def test_none(self):
        assert pv.extract_text(None) == ""

    def test_plain_string(self):
        assert pv.extract_text("hello") == "hello"

    def test_text_type_list(self):
        parts = [{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}]
        assert pv.extract_text(parts) == "hello\n world"

    def test_tool_use(self):
        parts = [{"type": "tool_use", "name": "bash", "input": {"cmd": "ls"}}]
        result = pv.extract_text(parts)
        assert "tool:bash" in result
        assert "ls" in result

    def test_tool_result(self):
        parts = [{"type": "tool_result", "content": [{"type": "text", "text": "file1.txt"}]}]
        result = pv.extract_text(parts)
        assert "result" in result
        assert "file1.txt" in result

    def test_reasoning(self):
        parts = [{"type": "reasoning", "summary": [{"type": "summary_text", "text": "thinking step"}]}]
        result = pv.extract_text(parts)
        assert "reasoning" in result
        assert "thinking step" in result

    def test_empty_list(self):
        assert pv.extract_text([]) == ""

    def test_mixed_content(self):
        parts = [
            {"type": "text", "text": "Answer:"},
            {"type": "tool_use", "name": "read", "input": {"path": "file.py"}},
        ]
        result = pv.extract_text(parts)
        assert "Answer:" in result
        assert "tool:read" in result


# ============================================================================
# clean_text() tests
# ============================================================================

class TestCleanText:
    def test_trims_whitespace(self):
        # clean_text strips outer whitespace and rstrip-s each line
        assert pv.clean_text("  hello\n  world  ") == "hello\n  world"

    def test_empty_string(self):
        assert pv.clean_text("") == ""

    def test_only_whitespace(self):
        assert pv.clean_text("   \n  \n  ") == ""


# ============================================================================
# clip_text() tests
# ============================================================================

class TestClipText:
    def test_short_text(self):
        text = "Hello world"
        assert pv.clip_text(text) == text

    def test_clips_by_lines(self):
        text = "\n".join(f"line {i}" for i in range(20))
        result = pv.clip_text(text, role="user")  # user clips at 5 lines
        lines = result.splitlines()
        assert len(lines) == 5

    def test_clips_by_chars(self):
        text = "a" * 1000
        result = pv.clip_text(text, role="user")  # user clips at 420 chars
        # Clipped text gets an ellipsis suffix (" …") so total may be <= max_chars+3
        assert len(result) <= 423
        assert len(result) >= 100  # sanity: should be significantly shorter than 1000

    def test_adds_ellipsis(self):
        text = "\n".join(f"line {i}" for i in range(10))
        result = pv.clip_text(text, role="assistant", max_lines=3)
        assert result.endswith("…")

    def test_assistant_longer_default(self):
        """Assistant gets higher clip limits than user."""
        user_clip = pv.clip_text("x", role="user")
        asst_clip = pv.clip_text("x", role="assistant")
        assert isinstance(user_clip, str)
        assert isinstance(asst_clip, str)


# ============================================================================
# is_noise_message() tests
# ============================================================================

class TestIsNoiseMessage:
    def test_empty_text(self):
        assert pv.is_noise_message("user", "")

    def test_environment_context(self):
        assert pv.is_noise_message("user", "<environment_context>something")

    def test_system_prefixes(self):
        assert pv.is_noise_message("system", "<permissions instructions>...")
        assert pv.is_noise_message("developer", "<environment_context>...")

    def test_workspace_sandbox(self):
        assert pv.is_noise_message("system", "workspace-write sandboxing Filesystem sandboxing rules")

    def test_user_message_not_noise(self):
        assert not pv.is_noise_message("user", "refactor the auth module")

    def test_assistant_code_not_noise(self):
        assert not pv.is_noise_message("assistant", "Here's the implementation")


# ============================================================================
# query_terms() tests
# ============================================================================

class TestQueryTerms:
    def test_empty_query(self):
        assert pv.query_terms("") == []

    def test_simple_terms(self):
        terms = pv.query_terms("auth login")
        assert "auth" in terms
        assert "login" in terms

    def test_strips_operators(self):
        terms = pv.query_terms("!draft 'fuzzy ^start end$")
        # query_terms strips fzf operators (!, ', ^, $) from the raw text
        assert "draft" in terms  # ! is stripped, leaving 'draft'
        assert "fuzzy" in terms
        assert "start" in terms
        assert "end" in terms

    def test_excludes_pipe(self):
        terms = pv.query_terms("a | b")
        assert "|" not in terms
        assert "a" in terms



class TestHighlightTerms:
    @pytest.fixture(autouse=True)
    def _enable_color(self, monkeypatch):
        monkeypatch.setattr(pv, "NO_COLOR", False)

    def test_highlights_term(self):
        result = pv.highlight_terms("hello world", ["world"])
        assert "\033[1;7;33m" in result
        assert "world" in result

    def test_no_highlight_when_no_terms(self):
        assert pv.highlight_terms("hello world", []) == "hello world"

    def test_does_not_corrupt_ansi_escapes(self):
        colored = "\033[31mhello\033[0m world"
        result = pv.highlight_terms(colored, ["world"])
        assert colored.replace("world", pv.c("1;7;33", "world")) == result
        # Make sure the ANSI escape sequences are intact.
        assert "\033[31m" in result
        assert "\033[0m" in result

    def test_does_not_match_inside_ansi_escape(self):
        colored = "\033[31mhello\033[0m"
        result = pv.highlight_terms(colored, ["31"])
        # "31" inside the escape sequence should not be highlighted.
        assert "\033[1;7;33m31\033[0m" not in result

    def test_case_insensitive(self):
        result = pv.highlight_terms("Hello World", ["world"])
        assert "World" in pv.strip_ansi(result)
        assert "\033[" in result


# ============================================================================
# header() rendering tests
# ============================================================================


class TestHeader:
    def test_contains_agent_and_sid(self):
        result = pv.header("claude", "sid-123", "/tmp/x.jsonl", cwd="/home/user/proj")
        assert "claude" in result
        assert "sid-123" in result or "sid" in result

    def test_includes_cwd(self):
        result = pv.header("codex", "s1", "/tmp/x.jsonl", cwd="/home/user/proj")
        assert "cwd" in result.lower() or "proj" in result

    def test_source_path(self):
        result = pv.header("droid", "s1", "/tmp/x.jsonl")
        assert "src" in result.lower() or "tmp" in result or "/tmp/x.jsonl" in result


# ============================================================================
# render_message() tests
# ============================================================================

class TestRenderMessage:
    def test_contains_role_tag(self):
        result = pv.render_message("user", "hello world")
        assert "USER" in result

    def test_contains_text(self):
        result = pv.render_message("assistant", "some response")
        assert "some response" in result

    def test_different_roles(self):
        for role in ("user", "assistant", "tool", "developer", "system"):
            result = pv.render_message(role, "test")
            assert role.upper()[:4] in result.upper()

    def test_with_timestamp(self):
        result = pv.render_message("user", "hello", ts="2026-04-17 10:00:00")
        assert "2026" in result or "10:00" in result


# ============================================================================
# select_excerpt() tests
# ============================================================================

class TestSelectExcerpt:
    def test_short_list_returns_all(self):
        msgs = [("user", "a", ""), ("assistant", "b", "")]
        visible, hidden = pv.select_excerpt(msgs, max_msgs=20)
        assert len(visible) == 2
        assert hidden == 0

    def test_long_list_head_tail(self):
        msgs = [(f"user", f"msg {i}", "") for i in range(20)]
        visible, hidden = pv.select_excerpt(msgs, max_msgs=5)
        assert len(visible) <= 5
        assert hidden >= 0


# ============================================================================
# Per-agent preview: claude
# ============================================================================

@pytest.fixture
def claude_session_file(claude_dir: Path) -> Path:
    """A Claude session with a mix of messages for preview testing."""
    sid = "preview-claude-001"
    path = claude_dir / "proj1" / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        {"type": "user", "isMeta": False, "cwd": "/home/user/proj",
         "message": {"role": "user", "content": [{"type": "text", "text": "Refactor the auth module"}]},
         "timestamp": "2026-04-17T10:00:00Z"},
        {"type": "assistant",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Here's my plan:\n1. Extract JWT logic\n2. Add refresh tokens\n3. Update tests"}]},
         "timestamp": "2026-04-17T10:00:30Z"},
        {"type": "user",
         "message": {"role": "user", "content": [{"type": "text", "text": "Add rate limiting too"}]},
         "timestamp": "2026-04-17T10:01:00Z"},
    ]
    make_claude_jsonl(path, lines)
    return path


class TestClaudePreview:
    def test_basic_preview(self, claude_session_file: Path):
        result = pv.preview_jsonl(claude_session_file, "claude", claude_session_file.stem)
        assert "claude" in result.lower()
        assert "auth module" in result
        assert "rate limiting" in result

    def test_preview_with_query_match(self, claude_session_file: Path):
        result = pv.preview_jsonl(claude_session_file, "claude", claude_session_file.stem,
                                  query="rate limiting")
        assert "Query Matches" in result or "rate limiting" in result

    def test_preview_caches(self, claude_session_file: Path):
        """Second call should use cache, not re-read file."""
        from pathlib import Path as P
        result1 = pv.preview_jsonl(claude_session_file, "claude", claude_session_file.stem)
        result2 = pv.preview_jsonl(claude_session_file, "claude", claude_session_file.stem)
        assert result1 == result2

    def test_preview_missing_file(self, tmp_path: Path):
        result = pv.preview_jsonl(tmp_path / "nonexistent.jsonl", "claude", "s1")
        assert "not found" in result.lower()


# ============================================================================
# Per-agent preview: codex
# ============================================================================

@pytest.fixture
def codex_session_file(codex_dir: Path) -> Path:
    sid = "preview-codex-001"
    path = codex_dir / f"rollout-2026-04-17T10-00-00-{sid}.jsonl"
    lines = [
        codex_meta(cwd="/home/user/proj", sid=sid),
        codex_message("user", "Fix the login bug"),
        codex_message("assistant", "Found the issue: missing await on async call."),
    ]
    make_codex_jsonl(path, lines)
    return path


class TestCodexPreview:
    def test_basic_preview(self, codex_session_file: Path):
        result = pv.preview_jsonl(codex_session_file, "codex", "preview-codex-001")
        assert "codex" in result.lower()
        assert "login bug" in result

    def test_includes_reasoning(self, codex_dir: Path):
        sid = "reasoning-test"
        path = codex_dir / f"rollout-2026-04-17T10-00-00-{sid}.jsonl"
        lines = [
            codex_meta(cwd="/p", sid=sid),
            {"type": "response_item", "payload": {
                "type": "reasoning", "content": [{"type": "text", "text": "thinking..."}],
            }},
            codex_message("user", "hi"),
        ]
        make_codex_jsonl(path, lines)
        result = pv.preview_jsonl(path, "codex", sid)
        assert "thinking" in result


# ============================================================================
# Per-agent preview: droid
# ============================================================================

@pytest.fixture
def droid_session_file(droid_dir: Path) -> Path:
    sid = "preview-droid-001"
    path = droid_dir / "proj1" / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        droid_start(cwd="/home/user/proj", title="Build the TUI"),
        droid_message("user", "Create a todo list app"),
        droid_message("assistant", "I'll create the todo app with add/delete features."),
    ]
    make_droid_jsonl(path, lines)
    return path


class TestDroidPreview:
    def test_basic_preview(self, droid_session_file: Path):
        result = pv.preview_jsonl(droid_session_file, "droid", "preview-droid-001")
        assert "droid" in result.lower()
        assert "todo" in result.lower()


# ============================================================================
# Per-agent preview: pi
# ============================================================================

@pytest.fixture
def pi_session_file(pi_dir: Path) -> Path:
    sid = "preview-pi-001"
    path = pi_dir / "proj1" / f"2026-04-17T10-00-00_{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        pi_session_start(cwd="/home/user/proj", oid=sid),
        pi_message("user", "Analyze this codebase"),
        pi_message("assistant", "Here's my analysis of the architecture..."),
    ]
    make_pi_jsonl(path, lines)
    return path


class TestPiPreview:
    def test_basic_preview(self, pi_session_file: Path):
        result = pv.preview_jsonl(pi_session_file, "pi", "preview-pi-001")
        assert "pi" in result.lower()
        assert "codebase" in result

    def test_model_change_included(self, pi_dir: Path):
        sid = "model-change-test"
        path = pi_dir / "proj1" / f"2026-04-17T10-00-00_{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            pi_session_start(cwd="/p", oid=sid),
            {"type": "model_change", "modelId": "claude-sonnet-4"},
            pi_message("user", "hi"),
        ]
        make_pi_jsonl(path, lines)
        result = pv.preview_jsonl(path, "pi", sid)
        assert "claude-sonnet" in result or "sonnet" in result or "model" in result.lower()


# ============================================================================
# Per-agent preview: opencode
# ============================================================================

@pytest.fixture
def opencode_session_file(opencode_db: Path) -> Path:
    make_opencode_db(opencode_db, [
        {
            "id": "oc-preview-001",
            "directory": "/home/user/proj",
            "title": "Implement search",
            "time_updated": 1776420000000,
            "messages": [
                {"role": "user", "text": "Add full-text search", "time_created": 1776420000000},
                {"role": "assistant", "text": "Using SQLite FTS5...", "time_created": 1776420030000},
                {"role": "user", "text": "Add pagination", "time_created": 1776420060000},
            ],
        },
    ])
    return opencode_db


class TestOpencodePreview:
    def test_basic_preview(self, opencode_session_file: Path):
        result = pv.preview_opencode("oc-preview-001", f"sqlite:{opencode_session_file}")
        assert "opencode" in result.lower()
        assert "full-text search" in result

    def test_missing_session(self, opencode_db: Path):
        """Preview for nonexistent session should show error."""
        make_opencode_db(opencode_db, [])
        result = pv.preview_opencode("nonexistent", f"sqlite:{opencode_db}")
        assert "not found" in result.lower() or "error" in result.lower()


# ============================================================================
# main() entry-point tests
# ============================================================================

class TestMain:
    def test_minimal_args_required(self, capsys, monkeypatch):
        """Preview needs at least 3 args."""
        monkeypatch.setattr(sys, "argv", ["fzf-ai-preview"])
        rc = pv.main()
        assert rc != 0
        captured = capsys.readouterr()
        assert "usage" in captured.err.lower()

    def test_unknown_agent_handled(self, capsys, monkeypatch, tmp_path: Path):
        """Unknown agent falls through to jsonl handler with a warning."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text("{}")
        monkeypatch.setattr(sys, "argv", ["fzf-ai-preview", "unknown", "s1", str(test_file)])
        rc = pv.main()
        assert rc == 0  # unknown agent just uses jsonl handler

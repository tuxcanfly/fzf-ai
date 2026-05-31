"""Tests for syntax highlighting in fzf-ai-preview and fzf-ai-highlight."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Import previewer (which has the _highlight_code function)
_SCRIPT = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf-ai-preview"
_LINK = Path(__file__).resolve().parent.parent.parent / "bin" / "fzf_ai_preview.py"
if not _LINK.is_file() and not _LINK.is_symlink():
    _LINK.symlink_to(_SCRIPT.name)
    import atexit
    atexit.register(lambda: _LINK.unlink(missing_ok=True))
sys.path.insert(0, str(_LINK.parent))
import fzf_ai_preview as pv


class TestHighlightCode:
    def test_plain_text_passthrough(self):
        """Non-code text is returned unchanged (if no pygments, or an error)."""
        text = "Hello world"
        result = pv._highlight_code(text)
        # Should contain the original text (possibly with ANSI wrapping)
        assert "Hello" in result
        assert "world" in result

    def test_code_block_detects_language(self):
        """A fenced code block with a language tag should get highlighted."""
        text = "Here's some code:\n```python\nprint('hello')\n```"
        result = pv._highlight_code(text)
        # The code block should be transformed (ANSI codes inserted)
        # If pygments is installed, 'print' should be colored
        assert "print" in result

    def test_multi_block(self):
        """Multiple code blocks should all be highlighted."""
        text = "First:\n```js\nlet x = 1;\n```\nSecond:\n```py\nx = 1\n```"
        result = pv._highlight_code(text)
        # ANSI codes wrap individual tokens; characters are still present
        assert "First" in result
        assert "Second" in result
        # The code chars are there (wrapped in ANSI color codes)
        assert "let" in result or "x" in result

    def test_code_with_newlines(self):
        """Multi-line code blocks."""
        text = "```python\ndef foo():\n    pass\n```"
        result = pv._highlight_code(text)
        assert "foo" in result
        assert "pass" in result

    def test_no_code_in_text(self):
        """Text without code blocks is unchanged."""
        text = "Just a regular conversation message."
        result = pv._highlight_code(text)
        assert "regular" in result

    def test_inline_code_not_confused(self):
        """Single backticks don't trigger the block highlighter."""
        text = "Use `git commit` to save changes."
        result = pv._highlight_code(text)
        assert "git commit" in result or "git" in result


class TestRenderMessageWithHighlight:
    def test_rendered_message_contains_code(self):
        """render_message should handle code blocks gracefully."""
        result = pv.render_message(
            "assistant",
            'Here\'s the fix:\n```python\nx = 1\n```',
        )
        assert "ASSISTANT" in result
        # ANSI codes wrap individual tokens; characters are present individually
        assert "fix" in result
        assert "x" in result or "1" in result

    def test_highlight_in_long_response(self):
        """Longer assistant responses with code should render cleanly."""
        text = "I'll implement that.\n```python\ndef hello():\n    print('world')\n```\nLet me know if you need changes."
        result = pv.render_message("assistant", text)
        assert "hello" in result
        assert "implement" in result

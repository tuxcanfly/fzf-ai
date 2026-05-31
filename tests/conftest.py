"""Shared fixtures and helpers for fzf-ai tests."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

import pytest


# Agents write compact JSON (no spaces after colons/commas).
# Our substring-based fast-paths depend on this format.
def _j(o) -> str:
    """Compact JSON serialization matching real agent output."""
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Synthetic JSONL / SQLite fixture builders
# ---------------------------------------------------------------------------

def make_claude_jsonl(path: Path, lines: list[dict]) -> Path:
    """Write a Claude-format JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(_j(obj) + "\n")
    return path


def make_codex_jsonl(path: Path, lines: list[dict]) -> Path:
    """Write a Codex-format JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(_j(obj) + "\n")
    return path


def make_droid_jsonl(path: Path, lines: list[dict]) -> Path:
    """Write a Droid-format JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(_j(obj) + "\n")
    return path


def make_pi_jsonl(path: Path, lines: list[dict]) -> Path:
    """Write a Pi-format JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(_j(obj) + "\n")
    return path


def make_opencode_db(path: Path, session_data: list[dict]) -> Path:
    """Build a synthetic opencode SQLite database.

    session_data is a list of dicts, one per session, with keys:
      id, directory, title, time_updated,
      messages: [{"role": ..., "text": ..., "time_created": ...}, ...]
    """
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA cache_size=-64000")

    # Schema matching opencode >=1.x
    con.execute("""
        CREATE TABLE session (
            id TEXT PRIMARY KEY,
            directory TEXT,
            title TEXT,
            time_updated INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            time_created INTEGER,
            data TEXT,
            FOREIGN KEY (session_id) REFERENCES session(id)
        )
    """)
    con.execute("""
        CREATE TABLE part (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            session_id TEXT,
            time_created INTEGER,
            data TEXT,
            FOREIGN KEY (message_id) REFERENCES message(id)
        )
    """)
    con.execute("CREATE INDEX idx_message_session ON message(session_id)")
    con.execute("CREATE INDEX idx_part_message ON part(message_id)")
    con.execute("CREATE INDEX idx_part_session ON part(session_id)")

    for sd in session_data:
        con.execute(
            "INSERT INTO session (id, directory, title, time_updated) VALUES (?, ?, ?, ?)",
            (sd["id"], sd.get("directory", ""), sd.get("title", ""), sd.get("time_updated", 0)),
        )
        for msg in sd.get("messages", []):
            role = msg.get("role", "user")
            text = msg.get("text", "")
            tc = msg.get("time_created", 0)
            data = _j({"role": role})
            con.execute(
                "INSERT INTO message (session_id, time_created, data) VALUES (?, ?, ?)",
                (sd["id"], tc, data),
            )
            mid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            part_data = _j({"type": "text", "text": text})
            con.execute(
                "INSERT INTO part (message_id, session_id, time_created, data) VALUES (?, ?, ?, ?)",
                (mid, sd["id"], tc, part_data),
            )

    con.commit()
    con.close()
    return path


def make_legacy_opencode_db(path: Path, session_data: list[dict]) -> Path:
    """Build a synthetic legacy opencode SQLite database (sessions/messages/files)."""
    con = sqlite3.connect(str(path))
    con.execute("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            message_count INTEGER,
            updated_at INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            parts TEXT,
            created_at INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    con.execute("""
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            path TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    for sd in session_data:
        con.execute(
            "INSERT INTO sessions (id, title, message_count, updated_at) VALUES (?, ?, ?, ?)",
            (sd["id"], sd.get("title", ""), len(sd.get("messages", [])), sd.get("time_updated", 0)),
        )
        for msg in sd.get("messages", []):
            parts = _j([{"type": "text", "text": msg.get("text", "")}])
            con.execute(
                "INSERT INTO messages (session_id, role, parts, created_at) VALUES (?, ?, ?, ?)",
                (sd["id"], msg.get("role", "user"), parts, msg.get("time_created", 0)),
            )

    con.commit()
    con.close()
    return path


# ---------------------------------------------------------------------------
# Common fixture snippets
# ---------------------------------------------------------------------------

def claude_prompt(text: str, ts: str = "2026-04-17T10:00:00Z", is_meta: bool = False) -> dict:
    return {
        "type": "user",
        "isMeta": is_meta,
        "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        "timestamp": ts,
    }


def claude_response(text: str, ts: str = "2026-04-17T10:00:30Z") -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        "timestamp": ts,
    }


def codex_message(role: str, text: str, ts: str = "2026-04-17T10:00:00Z") -> dict:
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "content": [{"type": "text", "text": text}],
        },
        "timestamp": ts,
    }


def codex_meta(cwd: str = "/home/user/proj", sid: str = "meta-session-id") -> dict:
    return {
        "type": "session_meta",
        "payload": {"cwd": cwd, "id": sid},
        "timestamp": "2026-04-17T09:59:00Z",
    }


def droid_start(cwd: str = "/home/user/proj", title: str = "My Session") -> dict:
    return {"type": "session_start", "cwd": cwd, "title": title}


def droid_message(role: str, text: str, ts: str = "2026-04-17T10:00:00Z") -> dict:
    return {
        "type": "message",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
        "timestamp": ts,
    }


def pi_session_start(cwd: str = "/home/user/proj", oid: str = "pi-uuid") -> dict:
    return {"type": "session", "cwd": cwd, "id": oid}


def pi_message(role: str, text: str, ts: str = "2026-04-17T10:00:00Z") -> dict:
    return {
        "type": "message",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
        "timestamp": ts,
    }


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_home(monkeypatch, tmp_path: Path) -> Path:
    """Temporary $HOME so we don't touch real session stores in tests."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
    # Also patch os.path.expanduser and $HOME
    monkeypatch.setenv("HOME", str(fake_home))
    return fake_home


@pytest.fixture
def claude_dir(tmp_home: Path) -> Path:
    """Create ~/.claude/projects/ and return it."""
    d = tmp_home / ".claude" / "projects"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def codex_dir(tmp_home: Path) -> Path:
    """Create ~/.codex/sessions/YYYY/MM/DD/ and return it."""
    d = tmp_home / ".codex" / "sessions" / "2026" / "04" / "17"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def droid_dir(tmp_home: Path) -> Path:
    """Create ~/.factory/sessions/ and return it."""
    d = tmp_home / ".factory" / "sessions"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def pi_dir(tmp_home: Path) -> Path:
    """Create ~/.pi/agent/sessions/ and return it."""
    d = tmp_home / ".pi" / "agent" / "sessions"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def opencode_db(tmp_home: Path) -> Path:
    """Create a global opencode db directory."""
    d = tmp_home / ".local" / "share" / "opencode"
    d.mkdir(parents=True)
    return d / "opencode.db"


@pytest.fixture
def sample_claude_jsonl(claude_dir: Path) -> Path:
    """A minimal valid Claude session file."""
    sid = "550e8400-e29b-41d4-a716-446655440000"
    path = claude_dir / "proj1" / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        {"type": "user", "isMeta": False,
         "message": {"role": "user", "content": [{"type": "text", "text": "refactor the auth module"}]},
         "timestamp": "2026-04-17T10:00:00Z", "cwd": "/home/user/proj"},
        {"type": "assistant",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Here's the plan for auth refactor..."}]},
         "timestamp": "2026-04-17T10:00:30Z"},
        {"type": "user",
         "message": {"role": "user", "content": [{"type": "text", "text": "add tests too"}]},
         "timestamp": "2026-04-17T10:01:00Z"},
        {"type": "assistant",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Tests added."}]},
         "timestamp": "2026-04-17T10:01:30Z"},
    ]
    make_claude_jsonl(path, lines)
    return path


@pytest.fixture
def sample_codex_jsonl(codex_dir: Path) -> Path:
    """A minimal valid Codex session file."""
    sid = "cod-session-uuid-1234"
    path = codex_dir / f"rollout-2026-04-17T10-00-00-{sid}.jsonl"
    lines = [
        codex_meta(cwd="/home/user/proj", sid=sid),
        codex_message("user", "fix the login bug"),
        codex_message("assistant", "Looking at the login code..."),
        codex_message("user", "use bcrypt"),
        codex_message("assistant", "Done, switched to bcrypt."),
    ]
    make_codex_jsonl(path, lines)
    return path


@pytest.fixture
def sample_droid_jsonl(droid_dir: Path) -> Path:
    """A minimal valid Droid session file."""
    sid = "droid-uuid-5678"
    path = droid_dir / "proj1" / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        droid_start(cwd="/home/user/proj", title="Build the TUI"),
        droid_message("user", "Create a todo app"),
        droid_message("assistant", "I'll build a todo app with..."),
    ]
    make_droid_jsonl(path, lines)
    return path


@pytest.fixture
def sample_pi_jsonl(pi_dir: Path) -> Path:
    """A minimal valid Pi session file."""
    sid = "pi-uuid-9012"
    path = pi_dir / "proj1" / f"2026-04-17T10-00-00_{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        pi_session_start(cwd="/home/user/proj", oid=sid),
        pi_message("user", "Analyze this codebase"),
        pi_message("assistant", "Here's my analysis of..."),
    ]
    make_pi_jsonl(path, lines)
    return path


@pytest.fixture
def sample_opencode_db(opencode_db: Path) -> Path:
    """A minimal valid opencode SQLite database."""
    make_opencode_db(opencode_db, [
        {
            "id": "oc-session-001",
            "directory": "/home/user/proj",
            "title": "Implement search",
            "time_updated": 1744876800000,  # ms
            "messages": [
                {"role": "user", "text": "Add search to the app", "time_created": 1744876800000},
                {"role": "assistant", "text": "Here's a search implementation...", "time_created": 1744876830000},
                {"role": "user", "text": "Make it fuzzy", "time_created": 1744876860000},
                {"role": "assistant", "text": "Added fuzzy search.", "time_created": 1744876890000},
            ],
        },
    ])
    return opencode_db

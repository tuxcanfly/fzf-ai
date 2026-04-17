# fzf-ai

Fuzzy-find and resume any AI coding session across **claude-code**, **codex**,
**opencode**, **droid** (factory), and **pi** from a single fzf picker.

```
┌──── AI coding sessions ──────────────────────────────────────────────────┐
│  claude    2026-04-17 03:16     6  ~/Work/fzfai        refactor preview  │
│▶ codex     2026-04-16 12:01    53  ~/Work/kimi-ai/...  ai-missions impl  │
│  pi        2026-04-16 11:16    30  ~/Work/kimi-ai/...  hi                │
│  droid     2026-04-04 17:47    20  ~/Work/droid-ai/... tui todo app      │
│  opencode  2025-08-11 20:03     2  ~/                   Greeting message │
└──────────────────────────────────────────────────────────────────────────┘
```

## What it does

* **Indexes every session** on disk:
  * claude ─ `~/.claude/projects/<proj>/<uuid>.jsonl`
  * codex  ─ `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
  * opencode ─ the global sqlite db at `~/.local/share/opencode/opencode.db`
    (tables `session` / `message` / `part`). Legacy per-project
    `<repo>/.opencode/opencode.db` files are deliberately skipped — those
    sessions are not resumable by current opencode and just created
    ghost rows.
  * droid  ─ `~/.factory/sessions/<proj>/<uuid>.jsonl`
  * pi     ─ `~/.pi/agent/sessions/<proj>/<iso>_<uuid>.jsonl`
* Sorts newest-first and shows a rich ANSI preview of the real conversation
  (first prompt, last replies, tool calls, reasoning, model, cwd).
* **Exact-match by default** across agent / cwd / title / user prompts.
  fzf runs with `--exact`, so typing `noita` finds sessions containing
  `noita`. Use `'word` to fall back to fuzzy for a single term, `!word`
  to exclude, `^word` / `word$` for prefix / suffix.
* On **enter**, fzf exits cleanly, then the launcher `exec`s the correct
  CLI from the session's original cwd. Using `exec`-after-exit (rather
  than fzf's `become` action) avoids a terminal-state race that caused
  codex to hang and opencode's input to freeze on hand-off.
  * `claude --resume <id>`
  * `codex resume -C <cwd> <id>`   (explicit `-C` suppresses codex's
    interactive "change directory?" prompt)
  * `opencode <cwd> --session <id>` (passes the project dir as positional
    so opencode opens the correct db and finds the session)
  * `droid --resume <id>`
  * `pi --session <path>` (preferred) or `pi --resume <id>`

## Install

```bash
# put the scripts on your PATH
ln -s "$PWD/bin/fzf-ai"          ~/.local/bin/fzf-ai
ln -s "$PWD/bin/fzf-ai-index"    ~/.local/bin/fzf-ai-index
ln -s "$PWD/bin/fzf-ai-preview"  ~/.local/bin/fzf-ai-preview
ln -s "$PWD/bin/fzf-ai-resume"   ~/.local/bin/fzf-ai-resume
```

Requires: `fzf` ≥ 0.50, `python3` (stdlib only), each AI CLI you want to
resume on your `$PATH`.

## Usage

```bash
fzf-ai                    # browse everything
fzf-ai claude codex       # only these agents
```

### Search syntax (exact-match by default)

| query             | meaning                                    |
|-------------------|--------------------------------------------|
| `noita`           | contains `noita`                           |
| `noita webgpu`    | contains `noita` AND contains `webgpu`     |
| `'word`           | fuzzy-match for this term (unquote)        |
| `^use`            | starts with `use`                          |
| `.md$`            | ends with `.md`                            |
| `!draft`          | excludes items containing `draft`          |
| `a | b | c`       | OR                                         |

### Keys

| key            | action                                            |
|----------------|---------------------------------------------------|
| `enter`        | resume session in its native CLI (cd to its cwd) |
| `ctrl-o`       | open a shell in the session's working directory  |
| `ctrl-e`       | open the raw `.jsonl` in `$EDITOR`               |
| `ctrl-y`       | copy session id to clipboard                     |
| `ctrl-r`       | reload the index                                 |
| `?`            | toggle preview pane                              |
| `alt-p`        | cycle preview position (right / down / wide)     |
| `alt-1..5`     | filter to claude / codex / opencode / droid / pi |
| `alt-0`        | clear filter                                     |

## How it fits together

```
bin/fzf-ai            ─ bash launcher wiring fzf bindings
bin/fzf-ai-index      ─ python: walks every session store, emits 8-col TSV
bin/fzf-ai-preview    ─ python: renders a conversation preview for fzf
bin/fzf-ai-resume     ─ bash:   cd into cwd and exec the right AI CLI
```

The index format (TAB-separated):

```
1 agent(raw)   2 session_id   3 source      ← hidden, machine only
4 agent(ui)    5 updated      6 msgs        ← visible, padded + ANSI
7 cwd          8 title                       ← visible
9 search blob (concat of all user prompts)  ← visible but past the right
                                               edge, used for --nth match
```

fzf's `--with-nth=4,5,6,7,8,9` hides columns 1-3 from the list while
keeping them available to `{1}..{3}` in preview, resume, and execute
bindings. `--nth=1,4,5,6` (indices into the transformed view) tells fzf
to fuzzy-match against agent, cwd, title, and the search blob. The blob
extends off the right edge of the terminal so fzf's default line
truncation keeps the UI clean while still searching the full text.

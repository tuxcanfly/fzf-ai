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
  (first real prompt, last user prompt, recent replies, tool calls,
  reasoning, model, cwd). Boilerplate environment / policy blocks are
  hidden from the preview when possible.
* **Exact-match by default** across agent / cwd / title / hidden session
  content snippets.
  fzf runs with `--exact`, so typing `noita` finds sessions containing
  `noita`. Use `'word` to fall back to fuzzy for a single term, `!word`
  to exclude, `^word` / `word$` for prefix / suffix.
* Uses newer `fzf` features to make the picker behave like a small TUI:
  * `reload-sync` for clean initial load and reindex without flicker
  * `change-nth` + `FZF_NTH` to switch search scopes on the fly
  * `click-header` so the scope tags in the header are clickable
  * `bg-transform-*` + `{*f}` to render a live footer summary of matches
  * `--history` for persistent query history between runs
  * `--tmux` so it opens in a popup automatically when run inside tmux
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

### Option 1: Using pip (recommended)
```bash
# Install from the source distribution
pip install fzf_ai-1.0.0.tar.gz
# Or install from PyPI when published
pip install fzf-ai
```

The pip installation will automatically add the scripts to your PATH if you have
the Python bin directory in your PATH (typically `~/.local/bin` or `~/Library/Python/3.x/bin`).

### Option 2: Using Make (traditional method)
```bash
# Clone or download the repository
cd fzf-ai
make install-symlink
# Make sure ~/.local/bin is in your PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Option 3: Manual installation
```bash
# Add the bin directory to your PATH
export PATH="$PWD/bin:$PATH"
# Or create symlinks to a directory in your PATH
ln -s "$PWD/bin/fzf-ai"          ~/.local/bin/fzf-ai
ln -s "$PWD/bin/fzf-ai-index"    ~/.local/bin/fzf-ai-index
ln -s "$PWD/bin/fzf-ai-preview"  ~/.local/bin/fzf-ai-preview
ln -s "$PWD/bin/fzf-ai-resume"   ~/.local/bin/fzf-ai-resume
```

### Option 3: Manual installation
```bash
# put the scripts on your PATH
ln -s "$PWD/bin/fzf-ai"          ~/.local/bin/fzf-ai
ln -s "$PWD/bin/fzf-ai-index"    ~/.local/bin/fzf-ai-index
ln -s "$PWD/bin/fzf-ai-preview"  ~/.local/bin/fzf-ai-preview
ln -s "$PWD/bin/fzf-ai-resume"   ~/.local/bin/fzf-ai-resume
```

Requires: `fzf` ≥ 0.63, `python3` (stdlib only), each AI CLI you want to
resume on your `$PATH`.

## PyPI Publishing

GitHub Actions trusted publishing is configured in
`.github/workflows/pypi-publish.yml`.

Regular validation for pushes and pull requests runs in
`.github/workflows/ci.yml`.

To enable it on PyPI, add a Trusted Publisher for project `fzf-ai` with:

* owner: `tuxcanfly`
* repository: `fzf-ai`
* workflow: `.github/workflows/pypi-publish.yml`
* environment: `pypi`

If `fzf-ai` does not exist on PyPI yet, create a pending publisher under
your PyPI account with the same values.

Publishing flow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow will build the sdist/wheel, run `twine check`, and publish to
PyPI using GitHub OIDC instead of a long-lived API token.

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

| key            | action                                              |
|----------------|-----------------------------------------------------|
| `enter`        | resume session in its native CLI (cd to its cwd)   |
| `ctrl-o`       | open a shell in the session's working directory    |
| `ctrl-e`       | open the raw `.jsonl` / sqlite source in `$EDITOR` |
| `ctrl-y`       | copy session id to clipboard                       |
| `ctrl-k`       | copy the exact resume command to clipboard         |
| `ctrl-p`       | move up                                            |
| `ctrl-n`       | move down                                          |
| `ctrl-r`       | rebuild the index in place                         |
| `ctrl-s`       | cycle search scope: `all → cwd → title → content → agent` |
| `?`            | toggle preview pane                                |
| `alt-p`        | cycle preview position / hide preview              |
| `alt-1..5`     | filter to claude / codex / opencode / droid / pi   |
| `alt-0`        | clear the temporary agent filter                   |

### Scope Switching

The header is clickable. Click `[all]`, `[cwd]`, `[title]`, `[content]`,
or `[agent]` to change what `fzf` searches against. The current
scope is reflected in the prompt and in the dynamic list label.

### Query History

Search history is persisted at:

```bash
${XDG_STATE_HOME:-~/.local/state}/fzf-ai/query-history
```

`fzf-ai` rebinds `ctrl-p` / `ctrl-n` back to list navigation, so query
history remains available through fzf's alternate history actions only if
you bind them yourself.

### Footer Summary

The footer is computed asynchronously from the current match set using
fzf's `{*f}` placeholder. It shows:

* matched session count
* distinct project count
* summed message count
* per-agent counts for the current match set

## How it fits together

```
bin/fzf-ai            ─ bash launcher wiring advanced fzf bindings
bin/fzf-ai-index      ─ python: walks every session store, emits 9-col TSV
bin/fzf-ai-preview    ─ python: renders a conversation preview for fzf
bin/fzf-ai-resume     ─ bash:   cd into cwd and exec the right AI CLI
bin/fzf-ai-ui         ─ bash:   dynamic labels / scope switching / footer stats
```

The index format (TAB-separated):

```
1 agent(raw)   2 session_id   3 source      ← hidden, machine only
4 agent(ui)    5 updated      6 msgs        ← visible, padded + ANSI
7 cwd          8 title                       ← visible
9 search blob (hidden session content)      ← pushed past the right edge,
                                               used for content search only
```

fzf runs with:

```bash
--with-nth=4,5,6,7,8,9
```

That keeps columns 1-3 hidden from the list while still exposing:

* transformed field `1` = agent
* transformed field `4` = cwd
* transformed field `5` = title
* transformed field `6` = hidden content blob

So `change-nth` can dynamically retarget the search scope without
rebuilding the list.

## Notes

* The indexer reads JSONL session stores in parallel. Set
  `FZFAI_INDEX_JOBS=<n>` to override the worker count.
* The launcher now requires `fzf >= 0.63.0` because it relies on
  `reload-sync`, footer sections, async transforms, and `{*f}`.

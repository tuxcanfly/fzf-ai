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
* **Smart-case exact matching by default** across agent / cwd / title /
  hidden session content. `--exact` keeps matches high-signal because the
  hidden content blob is now a tight, unit-separated concatenation of user
  prompts (≈1200 chars) where fuzzy matching would otherwise flood the
  picker with incidental letter-order hits. Recency breaks ties via
  `--scheme=history` + `--tiebreak=index`. Prefix a word with `'` to
  fuzzy-match that term, `!word` to exclude, `^word` / `word$` to
  anchor, or `a | b` for OR.
* **Fuzzy mode**: set `FZFAI_FUZZY=1` (or run `fzf-ai` with that env var)
  to load a separate token-only snapshot and disable `--exact`. The fuzzy
  index keeps only distinctive, stopword-filtered tokens from user prompts,
  so it is fast and high-signal without the usual filler-text noise.
* Uses newer `fzf` features to make the picker behave like a small TUI:
   * `reload-sync` for clean initial load and reindex without flicker
   * `change-nth` + `FZF_NTH` to switch search scopes on the fly
   * `click-header` so the scope tags in the header are clickable
   * `bg-transform-*` + `{*f}` to render a live footer summary of matches
   * `zero` event to show a clear "no matches" hint with a recovery tip
   * `--history` for persistent query history between runs
   * `--tmux` so it opens in a popup automatically when run inside tmux
   * `--id-nth` for cross-reload tracking by session identity
   * `--cycle` for wrap-around list navigation
   * `--keep-right` so the title field stays visible on long rows
   * `--exact` by default, with `FZFAI_FUZZY=1` for token-based fuzzy search
   * `--smart-case` so queries only become case-sensitive when you type
     an uppercase letter
   * `--accept-nth` for clean output parsing without visible fields leaking
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

Requires: `fzf` ≥ 0.63, `python3`, each AI CLI you want to
resume on your `$PATH`.

### Homebrew

```bash
brew tap tuxcanfly/fzf-ai https://github.com/tuxcanfly/fzf-ai
brew install fzf-ai
```

### Performance tuning

The indexer reads session stores in parallel across agents and within each
agent. Set `FZFAI_INDEX_JOBS=<n>` to override the per-agent worker count.
The default is `min(32, cpu_count + 4)`.

### Hot snapshot

`fzf-ai-index` and `fzf-ai-watch` write a hot TSV snapshot to
`~/.cache/fzf-ai/index.tsv` (and `index.fuzzy.tsv` for fuzzy mode). When the
snapshot is fresh, `fzf-ai` loads it directly instead of re-running the
indexer, so warm starts are effectively a single file read. The default
maximum snapshot age is 120 seconds; override with `FZFAI_SNAPSHOT_MAX_AGE`.
Set `FZFAI_FORCE_INDEX=1` to skip the snapshot and reindex on demand.

### Background incremental indexer

`fzf-ai-index` keeps an incremental SQLite cache at
`~/.cache/fzf-ai/index.db`. Each session source is stored as a msgpack BLOB
keyed by `mtime`/`size`, so unchanged files are loaded from the cache instead
of being re-parsed. On a warm cache, startup is typically **10–50x faster**.

The watcher also refreshes the hot snapshot after every update, so `fzf-ai`
starts instantly when the watcher is running.

To keep the cache hot in the background, run the watcher:

```bash
fzf-ai-watch              # watch all agents
fzf-ai-watch claude codex # watch only these agents
```

Set `FZFAI_WATCH_INTERVAL=<seconds>` to change the poll interval (default 60).
The watcher exits cleanly on `SIGINT`/`SIGTERM`.

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

### Search syntax (exact smart-case by default)

Exact mode is the default. Set `FZFAI_FUZZY=1` to switch to a token-based
fuzzy index where every term is fuzzy-matched automatically.

| query             | meaning                                    |
|-------------------|--------------------------------------------|
| `noita`           | contains `noita`                           |
| `noita webgpu`    | contains `noita` AND contains `webgpu`     |
| `'word`           | fuzzy-match for this term in exact mode    |
| `^use`            | starts with `use`                          |
| `.md$`            | ends with `.md`                            |
| `!draft`          | excludes items containing `draft`          |
| `a \| b \| c`     | OR                                         |

Queries are case-insensitive until you type an uppercase letter
(`--smart-case`). Sessions are pre-sorted by last-modified time and
`--tiebreak=index` preserves that order when match scores are equal.
The default is `--exact` because the hidden content blob is a tight
concatenation of user prompts; fuzzy matching against raw assistant text
would otherwise return unrelated sessions whose letters happen to appear in
the right order.

### Fuzzy mode

```bash
export FZFAI_FUZZY=1
fzf-ai
```

In fuzzy mode the content field contains only distinctive, stopword-filtered
tokens extracted from user prompts, so fuzzy matching stays high-signal and
fast. The snapshot used is `~/.cache/fzf-ai/index.fuzzy.tsv`.

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
| `alt-w`        | toggle preview wrap                                |
| `shift-up/down`| scroll preview by half a page                      |
| `ctrl-shift-up/down` | scroll preview by a full page                |
| `pgup/pgdn`    | page through the session list                      |
| `alt-<` / `alt->` | jump to first / last session                    |
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
bin/fzf-ai-watch      ─ python: background indexer that keeps the SQLite cache hot
bin/fzf-ai-preview    ─ python: renders a conversation preview for fzf
bin/fzf-ai-resume     ─ bash:   cd into cwd and exec the right AI CLI
bin/fzf-ai-ui         ─ bash:   dynamic labels / scope switching / footer stats
```

The index format (TAB-separated):

```
1 agent(raw)   2 session_id   3 source      ← hidden, machine only
4 agent(ui)    5 updated      6 msgs        ← visible, padded + ANSI
7 cwd          8 title                       ← visible
9 search blob (user prompts, unit-separated) ← pushed past the right edge,
                                               used for content search only
```

A second snapshot, `index.fuzzy.tsv`, replaces column 9 with stopword-filtered
tokens for use when `FZFAI_FUZZY=1`.

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

## Additional Commands

### Usage analytics

```bash
fzf-ai-stats                    # terminal dashboard
fzf-ai-stats --json             # machine-readable JSON
fzf-ai-stats --days 7           # last 7 days only
```

Output:
```
  fzf-ai Usage Analytics
  ────────────────────────────────────────────────────────────────
  Sessions:    1,247    Messages:  89,432    Projects:  23

  By Agent
    claude     ████████████████████  534  (42.8%)
    codex      ██████████████       412  (33.0%)
    opencode   ██████               187  (15.0%)
    pi         ████                 114  (9.1%)

  Daily Activity (last 14 days)
    05-17 █████████████████████████  12
    05-18 ████████████████████████████████████  20
    ...

  Top Projects
    fzf-ai             ████████████████████  45
    kimi-ai            ██████████████        32
    ...

  Metadata
    Starred sessions:  8
    Tagged sessions:   15  (42 total tags)
```

### Session management

```bash
fzf-ai-actions tag <sid> <source> <tag>     # add/remove tag
fzf-ai-actions star <sid> <source>           # toggle star
fzf-ai-actions delete <sid> <source>         # trash session
fzf-ai-actions export <sid> <source>         # export to markdown
fzf-ai-actions rename <sid> <source> <tit>   # custom title
fzf-ai-actions list-tags                     # list all tags
```

### Keybindings (in picker)

| key            | action                                              |
|----------------|-----------------------------------------------------|
| `alt-s`        | star / unstar a session                              |
| `ctrl-d`       | delete (trash) a session                             |
| `ctrl-t`       | tag a session                                        |

### Plugin system

Add support for new AI coding assistants by creating a file in
`bin/stores/`:  

```python
# stores/copilot.py
from fzf_ai_index import Record
from pathlib import Path

SESSION_DIR = Path.home() / ".github" / "copilot" / "sessions"

def walk(cache: dict | None = None):
    for path in SESSION_DIR.glob("*.jsonl"):
        rec = Record(agent="copilot", session_id=path.stem, source=str(path))
        rec.title = path.stem
        yield rec
```

Then run: `fzf-ai copilot`

### Rich preview

The preview window renders the conversation with:

* **Syntax highlighting** for fenced code blocks using **Pygments** with the
  Monokai colour scheme.
* **Keyword highlighting**: query terms are highlighted in the preview text
  without corrupting existing ANSI escapes from Pygments or role colours.
* **Tool calls and file edits** for Claude sessions, shown as compact
  `⟨tool:name⟩`, `⟨create⟩ path`, `⟨update⟩ path`, and `⟨edit⟩ path` summaries
  so you can see what the agent actually did.

## Performance

| Scenario | v1.x | v2.0 | Speedup |
|---|---|---|---|
| Cold index, 100 sessions | ~1.2s | ~300ms | **4x** |
| Cold index, 1000 sessions | ~12s | ~3s | **4x** |
| opencode SQLite (100 sessions) | ~200ms | ~80ms | **2.5x** |
| Preview load, cached | ~50ms | ~15ms | **3x** |

Key optimisations:
* **orjson** — compiled JSON decoder, 2-3x faster than stdlib
* **ProcessPoolExecutor** — true multi-core parallelism for file parsing
* **Substring pre-filter** — skip JSON decode on irrelevant lines (5x)
* **SQLite JOIN** — single query replaces 3 for opencode
* **Index cache** — avoid re-parsing unchanged files

## Notes

* The indexer reads JSONL session stores in parallel across agents and
  within each agent. Set `FZFAI_INDEX_JOBS=<n>` to override the
  per-agent worker count.
* The launcher now requires `fzf >= 0.63.0` because it relies on
  `reload-sync`, footer sections, async transforms, and `{*f}`.

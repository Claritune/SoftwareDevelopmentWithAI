# Implementation Tasks: Unlinked Mentions

Task breakdown for the developer agents, scoped to each agent's boundaries.
Spec: [`unlinked-mentions.md`](./unlinked-mentions.md)

## Contract v2 — Approved Decisions

The following decisions are **locked** and override any conflicting wording elsewhere:

1. **`--link` failure exits with code 1.** When `link_mention` returns `False`, the CLI
   prints a `[red]` message and `raise typer.Exit(1)` (matches the project's error
   convention). Tests assert exit code 1 on failure.
2. **Conversion inserts the canonical title.** `link_mention` wraps the mention using the
   target note's canonical `title` (`[[{target.title}]]`) — NOT the body's verbatim
   casing — so the resulting wiki link actually resolves. This overrides the spec's
   "preserve original casing" wording.
3. **Duplicate titles are out of scope for v1.** Detection stays permissive; `link_mention`
   takes explicit IDs so it is unambiguous. No warn/disambiguation UI this version.

Minor (non-blocking) decisions: `--all` takes precedence if combined with `NOTE_ID`; the
CLI flag param is named to avoid shadowing the builtin `all`; storage sorts results by
title for deterministic tests; code-block exclusion and `--min-length` remain out of scope.

## Execution Order

1. **storage-dev** — defines and implements the detection + conversion API (blocks CLI).
2. **cli-dev** — adds the `mentions` command that calls the storage API.
3. **qa** — writes CLI/integration tests (can start once the API contract below is agreed).
4. **code-reviewer** + **pattern-enforcer** — run in parallel after implementation.

The API contract in the storage-dev task is the coordination point: cli-dev and qa
build against these exact signatures.

---

## Task 1 — storage-dev

**Scope:** `src/brain_cli/storage/store.py`, `tests/test_storage.py`

Implement unlinked-mention detection and one-step link conversion as new methods on
`NoteStore`. This is a **non-LLM, pure string-matching** feature — no imports from
`search` or `entities`, no new dependencies.

### API to implement

```python
def find_unlinked_mentions(self, note_id: str) -> list[tuple[str, str]]:
    """Return (mentioning_note_id, snippet) for every OTHER note whose body
    mentions this note's title as text but has no [[wiki link]] to it.
    Returns [] if note_id does not exist."""

def find_all_unlinked_mentions(self) -> dict[str, list[tuple[str, str]]]:
    """Vault-wide scan. Maps target_note_id -> list of (mentioning_note_id, snippet)."""

def link_mention(self, mentioning_note_id: str, target_note_id: str) -> bool:
    """Wrap the FIRST unlinked occurrence of the target's title in the mentioning
    note's body with [[...]], then save() (which rebuilds the link index).
    Return True on success, False if either note is missing or no occurrence found."""
```

### Requirements / invariants
- **Matching:** case-insensitive, **whole-word** (use `re` with `re.escape(title)` and
  `\b` boundaries). Title "AI" must not match "email"; "Data" must not match "Database".
- A note never matches itself (AC-4).
- Suppress the mention if a link between the two notes already exists — reuse
  `note.outgoing_links()` / the existing link index to check (AC / edge case "already linked").
- **Snippet:** a short window of text around the matched term (mirror the ~200-char
  snippet convention used elsewhere; centering on the match is a nice-to-have).
- `link_mention` preserves the title's original casing when inserting `[[...]]` and must
  go through `save()` so the link index rebuilds (do not hand-edit `links.json`).
- Follow storage rules: `pathlib.Path` I/O, `datetime.now()`, return `None`/`bool`
  conventions, no data written outside the vault.

### Return-type decision
Return plain `tuple[str, str]` (id, snippet) to keep this fully inside the storage
scope (no edits to the shared `models.py`). If a richer type is later desired, propose
adding a `MentionResult` model to `models.py` as a separate shared-types change — do not
add it unilaterally.

### Tests (`tests/test_storage.py`)
Unit tests for the three methods using `tmp_path`: happy path, whole-word boundary
(no false "Database"/"email" matches), self-mention excluded, already-linked suppressed,
missing note returns `[]`/`False`, and `link_mention` round-trip (mention disappears +
new link appears in the index after conversion).

### Handoff note for cli-dev
Document the three signatures above as final so cli-dev can wire the command. If any
signature changes during implementation, update this file.

---

## Task 2 — cli-dev

**Scope:** `src/brain_cli/cli.py`

Add a `mentions` Typer command that calls the storage API from Task 1. **No business
logic here** — only argument handling, delegation to `NoteStore`, and Rich output.
This feature needs no OpenAI, so do **not** add a `_has_openai_key()` check.

### Command shape

```
brain mentions [NOTE_ID]                          # unlinked mentions of one note
brain mentions --all                              # vault-wide scan
brain mentions NOTE_ID --link MENTIONING_NOTE_ID  # convert first occurrence to [[link]]
```

- Parameters use `Annotated[...]`; include the standard `--vault` / `-v` option.
- `NOTE_ID` is an optional argument; require either `NOTE_ID` or `--all` (error in
  `[red]`, exit code 1, if neither is given).
- Build the store with the existing `_store(vault)` helper. Resolve mentioning-note IDs
  to titles via `store.get(...)` for display.

### Output
- Single note / `--all`: Rich `Table` with columns like `Mentioned In (ID)`, `Title`,
  `Snippet` (dim, capped width). For `--all`, group rows under each mentioned note.
- No results: `[dim]No unlinked mentions found.[/dim]` (AC-6).
- Note not found: `[red]Note not found:[/red] {id}`, exit 1 (match existing commands).
- `--link` success: `[green]Linked ...[/green]`; if `link_mention` returns `False`,
  print a `[red]`/`[yellow]` message explaining nothing was linked.

### Depends on
Task 1 signatures (`find_unlinked_mentions`, `find_all_unlinked_mentions`,
`link_mention`).

---

## Task 3 — qa

**Scope:** `tests/` (new CLI/integration file, e.g. `tests/test_cli_mentions.py` — do
**not** edit `tests/test_storage.py`, which is storage-dev's).

Write tests that exercise the `mentions` command end-to-end via Typer's
`CliRunner`, using `tmp_path` vaults. No API key required (this feature has no LLM path).

Cover:
- **Happy path:** create notes where B's body mentions A's title unlinked → `mentions A`
  lists B.
- **--all:** multiple unlinked pairs surface and are grouped correctly.
- **Conversion:** `mentions A --link B` inserts `[[A title]]` into B, and a follow-up
  `mentions A` no longer lists B while `links B` / `graph` now shows the edge.
- **Edge cases:** whole-word boundary (no false match), self-mention excluded,
  already-linked suppressed, missing note → exit code 1, neither `NOTE_ID` nor `--all`
  → exit code 1, empty vault → friendly message.

Each test independent; follow `test_{module}_{behavior}` naming.

---

## Task 4 — code-reviewer

Review the storage and CLI diffs after Tasks 1–2. Produce the structured review
(Critical Issues / Pattern Violations / Suggestions / Positive Notes) with file + line
references. Pay special attention to:
- **Regex safety:** `re.escape` on titles; correct `\b` word-boundary behavior.
- **Module boundaries:** storage does not import `search`/`entities`; only CLI imports modules.
- **CLI discipline:** no business logic leaked into `cli.py`; goes through `NoteStore`.
- `datetime.now()` usage and `link_mention` saving via `save()` (index consistency).
- Input validation at the CLI boundary (the `NOTE_ID` vs `--all` requirement).

---

## Task 5 — pattern-enforcer

**Scope:** all of `src/brain_cli/`.

After implementation, verify the new code against `rules/patterns.md` and fix any
deviations directly: DateTime (`datetime.now()`), error-handling conventions
(`None`/`bool`, exceptions propagate), import structure (no cross-module imports; shared
types only in `models.py`), and constructor/lazy-init patterns (unchanged here, but
confirm nothing new violates them). Report violations with file + line, then apply fixes.

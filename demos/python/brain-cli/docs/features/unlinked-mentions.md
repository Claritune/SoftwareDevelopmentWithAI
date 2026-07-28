# Feature Spec: Unlinked Mentions

**Status:** Proposed
**Author:** Product Manager Agent
**Type:** Non-LLM feature (pure string matching)

## Summary

Surface places where a note's title is mentioned in other notes' text but is not
yet wrapped in a `[[wiki link]]`. This reinforces BrainCLI's core "Connect"
pillar by helping users discover connections they forgot to make — with zero LLM,
zero embeddings, and no new dependencies. Works fully offline / without an API key.

## Motivation

Connections in BrainCLI only exist when a user manually types `[[links]]`. But
knowledge naturally accumulates in notes that reference each other by name without
ever being linked. This feature (a staple of Obsidian, and called out as a gap in
`SPEC.md` lines 72 and 99) turns those latent references into actionable link
suggestions.

## User Stories

- **US-1** — As a user, I want to see where a note's title is mentioned in *other*
  notes' text but not yet linked, so that I can discover connections I forgot to make.
- **US-2** — As a user, I want to run this across my whole vault, so that I can find
  all missing links in one pass during a "gardening" session.
- **US-3** — As a user, I want to convert a discovered mention into a real `[[link]]`,
  so that acting on the suggestion is one step, not manual editing.

## Acceptance Criteria

### Single note — `brain mentions <note_id>`
- **AC-1:** Returns every *other* note whose body contains this note's title as text,
  but which does **not** already have a `[[wiki link]]` to it.
- **AC-2:** Output shows the mentioning note's ID, title, and a short snippet with the
  matched text in context.
- **AC-3:** Matching is case-insensitive and whole-word (title "AI" does not match
  "email" or "brain").
- **AC-4:** A note is never reported as mentioning itself.

### Vault-wide — `brain mentions --all`
- **AC-5:** Lists all unlinked mention pairs across the vault, grouped by the
  mentioned note.
- **AC-6:** If there are none, prints a friendly "No unlinked mentions found." message.

### Convert action — `brain mentions <note_id> --link <mentioning_note_id>`
- **AC-7:** Wraps the first unlinked occurrence of the title in the mentioning note's
  body with `[[...]]`, saves via `NoteStore`, and the link index rebuilds automatically
  (existing `save()` behavior). The inserted link uses the target's **canonical title**
  (`[[{target.title}]]`) so it resolves — see Contract v2 decision #2.
- **AC-8:** After conversion, that pair no longer appears in mention results and now
  appears under `brain links` / `brain graph`.
- **AC-9:** If nothing is linked (`link_mention` returns `False`), the CLI prints a
  `[red]` message and exits with code 1 — see Contract v2 decision #1.

## Edge Cases

- **Duplicate titles:** out of scope for v1 (Contract v2 decision #3). Detection stays
  permissive; `link_mention` takes explicit IDs so conversion is unambiguous. A
  warn/disambiguation UI is deferred to a follow-up.
- **Common-word titles** (e.g. "Notes", "Ideas") → whole-word matching limits noise;
  a `--min-length` guard can skip very short titles.
- **Substring overlap:** title "Data" must not match "Database" (whole-word rule).
- **Already partially linked:** if a link between the two notes already exists, suppress
  the mention (avoid nagging).
- **Case/whitespace:** normalize on comparison, preserve original casing on insertion.
- **Empty vault / note not found:** clear error, exit code 1, consistent with existing
  commands.
- **Aliases:** no alias field exists today, so only exact titles are matched (see Scope).

## Priority

**High.** Highest value-per-effort non-LLM feature: reinforces the core "Connect"
pillar, closes a stated gap vs. Obsidian, and is cheap to build (string scan over
`store.list_notes()`, reusing `Note.outgoing_links()` to know what's already linked).
Ship **US-1 + US-2 (detection) first**; **US-3 (conversion)** is a fast follow.

## Scope Boundaries (explicitly NOT included)

- No fuzzy/semantic matching or LLM involvement — exact, case-insensitive, whole-word only.
- No alias matching (no alias field in the `Note` model yet — separate feature).
- No auto-linking without explicit user action (no destructive bulk rewrite).
- No matching inside code blocks or frontmatter — body text only.
- No new dependency; implemented with the standard library over existing storage.

## Affected Modules

- `src/brain_cli/storage/store.py` — detection helper (find unlinked mentions).
- `src/brain_cli/cli.py` — the `mentions` command and output rendering.

# Storage Module Rules

## Scope
- `src/brain_cli/storage/store.py`
- `tests/test_storage.py`

## Invariants
- The vault directory contains `.md` files — one per note
- Each file has YAML frontmatter (delimited by `---`) followed by content
- Frontmatter fields: id, title, tags, created_at, updated_at
- The `.brain/` subdirectory holds derived indexes — never source data
- `links.json` maps note_id → list of linked note_ids
- Link index is rebuilt on every save (not just updated incrementally)
- Wiki links `[[Title]]` resolve via title, not ID

## Patterns
- Use `yaml.safe_load` for parsing, `yaml.dump` for writing
- Return `None` for missing notes, not exceptions
- Return `bool` for delete operations
- All file I/O uses `pathlib.Path`
- Datetime fields use `datetime.now()` (not utcnow)

## Do NOT
- Store any data outside the vault directory
- Import from search or entities modules (no circular deps)
- Add database dependencies — storage is file-based only

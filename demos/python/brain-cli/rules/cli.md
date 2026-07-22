# CLI Module Rules

## Scope
- `src/brain_cli/cli.py`

## Invariants
- CLI is the integration layer — it imports and calls modules, never implements business logic
- All commands accept `--vault` to override the default vault path
- Commands that need OpenAI check `_has_openai_key()` before constructing SearchEngine/EntityExtractor
- Output uses Rich tables for lists, Rich markup for inline formatting

## Patterns
- Use Typer with type annotations (Annotated[...])
- Use Rich Console for all output
- Tables for list/search results, inline formatting for single items
- Error states: print in [red], exit with code 1
- Success states: print in [green]
- Informational: print in [cyan] or [dim]

## Do NOT
- Implement business logic in CLI commands — delegate to modules
- Access the filesystem directly — go through NoteStore
- Construct OpenAI clients directly — go through SearchEngine/EntityExtractor

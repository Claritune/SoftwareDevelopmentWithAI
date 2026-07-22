# Entities Module Rules

## Scope
- `src/brain_cli/entities/extractor.py`
- `tests/test_entities.py`

## Invariants
- Entities are stored in `.brain/entities.json` inside the vault
- Entity types: person, organization, technology, project, location, concept
- Each entity links back to its source note (id + title)
- Re-extracting for a note replaces all previous entities for that note
- LLM is initialized lazily (only when extract() is called)

## Patterns
- Use `langchain_openai.ChatOpenAI` with `with_structured_output()`
- Define Pydantic schemas for structured LLM output (ExtractedEntities)
- Model: gpt-4o-mini, temperature: 0
- Persistence: `model_dump(mode="json")` for writing, `Entity(**item)` for reading
- `load_dotenv()` at module level
- Entity search is case-insensitive

## Do NOT
- Import from storage or search modules
- Initialize the LLM in __init__ (lazy init via _get_llm)
- Store entities anywhere except the JSON file
- Use async LLM calls — keep it synchronous

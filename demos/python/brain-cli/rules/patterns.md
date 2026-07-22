# Cross-Module Patterns

These patterns must be consistent across all modules. The Pattern Enforcer agents
use this file as the canonical reference.

## LLM Interaction Pattern
```python
from langchain_openai import ChatOpenAI  # or OpenAIEmbeddings

class MyModule:
    def __init__(self, vault_path: Path, openai_api_key: str | None = None):
        self._openai_api_key = openai_api_key
        self._llm: ChatOpenAI | None = None  # lazy init

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            kwargs = {"model": "gpt-4o-mini", "temperature": 0}
            if self._openai_api_key:
                kwargs["api_key"] = self._openai_api_key
            self._llm = ChatOpenAI(**kwargs)
        return self._llm
```

## Structured Output Pattern
```python
from pydantic import BaseModel

class MyOutput(BaseModel):
    field: str

structured_llm = self._get_llm().with_structured_output(MyOutput)
result: MyOutput = structured_llm.invoke(prompt)
```

## JSON Persistence Pattern
```python
# Writing
data = [item.model_dump(mode="json") for item in items]
path.write_text(json.dumps(data, indent=2, default=str))

# Reading
data = json.loads(path.read_text())
items = [MyModel(**item) for item in data]
```

## Error Handling Pattern
- Return `None` for "not found" (don't raise)
- Return `bool` for "did it work" operations
- Let OpenAI/LangChain exceptions propagate — the CLI layer handles user messaging
- Use `_has_openai_key()` check in CLI before calling OpenAI-dependent code

## DateTime Pattern
- Always use `datetime.now()` (not `utcnow()`, not `timezone.utc`)
- Store as ISO format strings in YAML/JSON
- Pydantic handles parsing automatically

## Import Pattern
- Modules do NOT import each other (no circular deps)
- Only the CLI imports all modules
- Shared types live in `models.py`

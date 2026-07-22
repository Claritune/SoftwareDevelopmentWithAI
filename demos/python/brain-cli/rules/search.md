# Search Module Rules

## Scope
- `src/brain_cli/search/engine.py`
- `tests/test_search.py`

## Invariants
- ChromaDB data lives in `.brain/chroma/` inside the vault
- Collection name is always `"notes"`
- Embeddings use OpenAI `text-embedding-3-small` model
- Note text for embedding = title + tags + content joined by newlines
- Keyword search is standalone (no OpenAI dependency)
- Semantic search requires OpenAI API key

## Patterns
- Use `langchain_openai.OpenAIEmbeddings` for embedding generation
- Use `chromadb.PersistentClient` for vector storage
- Keyword search: case-insensitive substring match, score 1.0 for title / 0.5 for content
- Semantic search: score = 1.0 - distance (ChromaDB L2 distance)
- Snippet = first 200 chars of document text
- `load_dotenv()` at module level

## Do NOT
- Import from storage or entities modules
- Implement keyword search inside the SearchEngine class (keep it as standalone function)
- Cache embeddings in memory — ChromaDB handles persistence

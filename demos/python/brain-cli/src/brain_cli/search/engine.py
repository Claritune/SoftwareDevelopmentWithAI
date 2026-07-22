from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from brain_cli.models import Note, SearchResult

load_dotenv()


def keyword_search(query: str, notes: list[Note], limit: int = 10) -> list[SearchResult]:
    results: list[SearchResult] = []
    q = query.lower()

    for note in notes:
        if q in note.title.lower():
            score = 1.0
        elif q in note.content.lower():
            score = 0.5
        else:
            continue

        results.append(SearchResult(
            note_id=note.id,
            title=note.title,
            snippet=note.content[:200],
            score=score,
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


class SearchEngine:
    def __init__(self, vault_path: Path, openai_api_key: str | None = None):
        chroma_path = vault_path / ".brain" / "chroma"
        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._collection = self._client.get_or_create_collection(
            name="notes",
            metadata={"hnsw:space": "cosine"},
        )

        kwargs = {"model": "text-embedding-3-small"}
        if openai_api_key:
            kwargs["api_key"] = openai_api_key
        self._embeddings = OpenAIEmbeddings(**kwargs)

    def _note_text(self, note: Note) -> str:
        parts = [note.title]
        if note.tags:
            parts.append(" ".join(note.tags))
        if note.content:
            parts.append(note.content)
        return "\n".join(parts)

    def index_note(self, note: Note) -> None:
        text = self._note_text(note)
        embedding = self._embeddings.embed_query(text)
        self._collection.upsert(
            ids=[note.id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "title": note.title,
                "tags": ",".join(note.tags),
            }],
        )

    def remove_note(self, note_id: str) -> None:
        self._collection.delete(ids=[note_id])

    def keyword_search(
        self, query: str, notes: list[Note], limit: int = 10
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        q = query.lower()

        for note in notes:
            if q in note.title.lower():
                score = 1.0
            elif q in note.content.lower():
                score = 0.5
            else:
                continue

            results.append(SearchResult(
                note_id=note.id,
                title=note.title,
                snippet=note.content[:200],
                score=score,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def semantic_search(
        self, query: str, limit: int = 10
    ) -> list[SearchResult]:
        embedding = self._embeddings.embed_query(query)
        count = self._collection.count()
        chroma_results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(limit, count) if count > 0 else 1,
        )

        results: list[SearchResult] = []
        ids = chroma_results["ids"][0]
        distances = chroma_results["distances"][0]
        documents = chroma_results["documents"][0]
        metadatas = chroma_results["metadatas"][0]

        for doc_id, distance, document, metadata in zip(
            ids, distances, documents, metadatas
        ):
            results.append(SearchResult(
                note_id=doc_id,
                title=metadata["title"],
                snippet=document[:200],
                score=1.0 - distance,
            ))

        return results

    def reindex_all(self, notes: list[Note]) -> None:
        self._client.delete_collection("notes")
        self._collection = self._client.get_or_create_collection(
            name="notes",
            metadata={"hnsw:space": "cosine"},
        )
        for note in notes:
            self.index_note(note)

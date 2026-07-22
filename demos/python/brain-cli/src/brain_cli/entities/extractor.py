import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from brain_cli.models import Entity, Note

load_dotenv()


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str


class ExtractedEntities(BaseModel):
    entities: list[ExtractedEntity]


EXTRACTION_PROMPT = (
    "Extract all named entities from the following note. "
    "For each entity, provide its name and entity_type. "
    "entity_type must be one of: person, organization, technology, "
    "project, location, concept.\n\n"
    "Title: {title}\n\n"
    "{content}"
)


class EntityExtractor:
    def __init__(self, vault_path: Path, openai_api_key: str | None = None):
        self._entities_path = vault_path / ".brain" / "entities.json"
        self._openai_api_key = openai_api_key
        self._llm: ChatOpenAI | None = None

        self._entities: list[Entity] = []
        self._load()

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            kwargs: dict = {"model": "gpt-4o-mini", "temperature": 0}
            if self._openai_api_key:
                kwargs["api_key"] = self._openai_api_key
            self._llm = ChatOpenAI(**kwargs)
        return self._llm

    def extract(self, note: Note) -> list[Entity]:
        structured_llm = self._get_llm().with_structured_output(ExtractedEntities)
        prompt = EXTRACTION_PROMPT.format(title=note.title, content=note.content)
        result: ExtractedEntities = structured_llm.invoke(prompt)

        new_entities = [
            Entity(
                name=e.name,
                entity_type=e.entity_type,
                source_note_id=note.id,
                source_note_title=note.title,
            )
            for e in result.entities
        ]

        self._entities = [
            e for e in self._entities if e.source_note_id != note.id
        ]
        self._entities.extend(new_entities)
        self._save()

        return new_entities

    def get_entities(self, note_id: str) -> list[Entity]:
        return [e for e in self._entities if e.source_note_id == note_id]

    def get_all_entities(self) -> list[Entity]:
        return list(self._entities)

    def find_notes_for_entity(self, entity_name: str) -> list[Entity]:
        name_lower = entity_name.lower()
        return [e for e in self._entities if e.name.lower() == name_lower]

    def remove_note_entities(self, note_id: str) -> None:
        self._entities = [
            e for e in self._entities if e.source_note_id != note_id
        ]
        self._save()

    def _save(self) -> None:
        self._entities_path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.model_dump(mode="json") for e in self._entities]
        self._entities_path.write_text(json.dumps(data, indent=2, default=str))

    def _load(self) -> None:
        if not self._entities_path.exists():
            return
        data = json.loads(self._entities_path.read_text())
        self._entities = [Entity(**item) for item in data]

from datetime import datetime
from pydantic import BaseModel, Field
import uuid


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class Note(BaseModel):
    id: str = Field(default_factory=_new_id)
    title: str
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def outgoing_links(self) -> list[str]:
        import re
        return re.findall(r"\[\[(.+?)\]\]", self.content)


class Entity(BaseModel):
    name: str
    entity_type: str
    source_note_id: str
    source_note_title: str
    extracted_at: datetime = Field(default_factory=datetime.now)


class SearchResult(BaseModel):
    note_id: str
    title: str
    snippet: str = ""
    score: float = 0.0

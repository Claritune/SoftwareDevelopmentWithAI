from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import yaml

from brain_cli.models import Note


class NoteStore:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self._brain_dir = self.vault_path / ".brain"
        self._brain_dir.mkdir(exist_ok=True)
        self._links_path = self._brain_dir / "links.json"
        self._link_index: dict[str, list[str]] = self._load_link_index()

    def _load_link_index(self) -> dict[str, list[str]]:
        if self._links_path.exists():
            return json.loads(self._links_path.read_text())
        return {}

    def _persist_link_index(self) -> None:
        self._links_path.write_text(json.dumps(self._link_index, indent=2))

    def _note_path(self, note_id: str) -> Path:
        return self.vault_path / f"{note_id}.md"

    def _serialize(self, note: Note) -> str:
        frontmatter = {
            "id": note.id,
            "title": note.title,
            "tags": note.tags,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
        }
        fm_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{fm_text}---\n\n{note.content}\n"

    def _deserialize(self, text: str) -> Note | None:
        text = text.strip()
        if not text.startswith("---"):
            return None

        end = text.find("---", 3)
        if end == -1:
            return None

        fm_raw = text[3:end].strip()
        content = text[end + 3:].strip()
        meta = yaml.safe_load(fm_raw)
        if not isinstance(meta, dict):
            return None

        return Note(
            id=meta["id"],
            title=meta["title"],
            content=content,
            tags=meta.get("tags", []),
            created_at=meta["created_at"],
            updated_at=meta["updated_at"],
        )

    def _build_title_map(self) -> dict[str, str]:
        title_map: dict[str, str] = {}
        for path in self.vault_path.glob("*.md"):
            note = self._deserialize(path.read_text())
            if note:
                title_map[note.title] = note.id
        return title_map

    def _resolve_title_to_id(self, title: str) -> str | None:
        title_map = self._build_title_map()
        return title_map.get(title)

    def _update_link_index_for(self, note: Note) -> None:
        title_map = self._build_title_map()
        linked_titles = note.outgoing_links()
        resolved_ids = [
            title_map[t] for t in linked_titles if t in title_map
        ]
        self._link_index[note.id] = resolved_ids
        self._persist_link_index()

    def save(self, note: Note) -> Note:
        note.updated_at = datetime.now()
        self._note_path(note.id).write_text(self._serialize(note))
        self.rebuild_link_index()
        return note

    def get(self, note_id: str) -> Note | None:
        path = self._note_path(note_id)
        if not path.exists():
            return None
        return self._deserialize(path.read_text())

    def delete(self, note_id: str) -> bool:
        path = self._note_path(note_id)
        if not path.exists():
            return False
        path.unlink()
        self._link_index.pop(note_id, None)
        self._persist_link_index()
        return True

    def list_notes(self, tag: str | None = None) -> list[Note]:
        notes: list[Note] = []
        for path in self.vault_path.glob("*.md"):
            note = self._deserialize(path.read_text())
            if note is None:
                continue
            if tag is not None and tag not in note.tags:
                continue
            notes.append(note)
        return notes

    def get_backlinks(self, note_id: str) -> list[str]:
        return [
            src_id
            for src_id, targets in self._link_index.items()
            if note_id in targets
        ]

    def get_links(self, note_id: str) -> list[str]:
        return self._link_index.get(note_id, [])

    def get_orphans(self) -> list[str]:
        all_ids = {p.stem for p in self.vault_path.glob("*.md")}
        linked_from = set(self._link_index.keys())
        linked_to: set[str] = set()
        for targets in self._link_index.values():
            linked_to.update(targets)

        connected = set()
        for nid in all_ids:
            if self._link_index.get(nid):
                connected.add(nid)
            if nid in linked_to:
                connected.add(nid)

        return list(all_ids - connected)

    def rebuild_link_index(self) -> None:
        title_map = self._build_title_map()
        self._link_index = {}
        for path in self.vault_path.glob("*.md"):
            note = self._deserialize(path.read_text())
            if note is None:
                continue
            linked_titles = note.outgoing_links()
            self._link_index[note.id] = [
                title_map[t] for t in linked_titles if t in title_map
            ]
        self._persist_link_index()

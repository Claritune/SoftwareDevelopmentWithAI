from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import yaml

from brain_cli.models import Note

# Width (characters) of the context window used for mention snippets.
_SNIPPET_WIDTH = 200


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

    # ------------------------------------------------------------------
    # Unlinked mentions
    # ------------------------------------------------------------------
    def _mention_pattern(self, title: str) -> re.Pattern[str]:
        """Compile a case-insensitive, whole-word matcher for a note title.

        Uses ``re.escape`` so regex-special characters in the title are treated
        literally, ``\\b`` word boundaries so "Data" does not match "Database",
        and lookarounds so occurrences already wrapped in ``[[...]]`` are skipped.
        """
        escaped = re.escape(title)
        return re.compile(rf"(?<!\[)\b{escaped}\b(?!\])", re.IGNORECASE)

    def _find_first_mention(
        self, pattern: re.Pattern[str], content: str
    ) -> re.Match[str] | None:
        """Return the first unlinked occurrence of the title, or ``None``."""
        return pattern.search(content)

    def _make_snippet(self, content: str, match: re.Match[str]) -> str:
        """Build a ~200-char context window centered on the match.

        Newlines/whitespace are collapsed to single spaces and ellipses mark
        truncation on either side.
        """
        center = (match.start() + match.end()) // 2
        half = _SNIPPET_WIDTH // 2
        start = max(0, center - half)
        end = min(len(content), start + _SNIPPET_WIDTH)
        # Re-extend the start if we clipped against the end of the content.
        start = max(0, end - _SNIPPET_WIDTH)

        window = re.sub(r"\s+", " ", content[start:end]).strip()
        if start > 0:
            window = f"…{window}"
        if end < len(content):
            window = f"{window}…"
        return window

    def _scan_mentions(
        self, target: Note, notes: list[Note]
    ) -> list[tuple[str, str]]:
        """Find unlinked mentions of ``target`` across ``notes``.

        Returns ``(mentioning_note_id, snippet)`` tuples, sorted by the
        mentioning note's title for deterministic output. A note never matches
        itself, and notes that already link the target are suppressed.
        """
        if not target.title:
            return []

        pattern = self._mention_pattern(target.title)
        results: list[tuple[str, str, str]] = []
        for note in notes:
            if note.id == target.id:
                continue
            if target.title in note.outgoing_links():
                continue
            match = self._find_first_mention(pattern, note.content)
            if match is None:
                continue
            results.append((note.title, note.id, self._make_snippet(note.content, match)))

        results.sort(key=lambda r: (r[0], r[1]))
        return [(note_id, snippet) for _title, note_id, snippet in results]

    def find_unlinked_mentions(self, note_id: str) -> list[tuple[str, str]]:
        """Return ``(mentioning_note_id, snippet)`` for every OTHER note whose
        body mentions this note's title as text but has no ``[[wiki link]]`` to
        it. Returns ``[]`` if the note is missing or has an empty title.
        """
        target = self.get(note_id)
        if target is None or not target.title:
            return []
        return self._scan_mentions(target, self.list_notes())

    def find_all_unlinked_mentions(self) -> dict[str, list[tuple[str, str]]]:
        """Vault-wide scan. Maps ``target_note_id`` -> list of
        ``(mentioning_note_id, snippet)``, including only targets with at least
        one unlinked mention.
        """
        notes = self.list_notes()
        result: dict[str, list[tuple[str, str]]] = {}
        for target in notes:
            mentions = self._scan_mentions(target, notes)
            if mentions:
                result[target.id] = mentions
        return result

    def link_mention(
        self, mentioning_note_id: str, target_note_id: str
    ) -> bool:
        """Wrap the FIRST unlinked occurrence of the target's title in the
        mentioning note's body with ``[[...]]`` using the target's canonical
        title, then ``save()`` so the link index rebuilds.

        Returns ``True`` on success, ``False`` if either note is missing, they
        are the same note, or no unlinked occurrence exists.
        """
        if mentioning_note_id == target_note_id:
            return False

        mentioning = self.get(mentioning_note_id)
        target = self.get(target_note_id)
        if mentioning is None or target is None or not target.title:
            return False

        pattern = self._mention_pattern(target.title)
        match = self._find_first_mention(pattern, mentioning.content)
        if match is None:
            return False

        content = mentioning.content
        mentioning.content = (
            content[: match.start()]
            + f"[[{target.title}]]"
            + content[match.end():]
        )
        self.save(mentioning)
        return True

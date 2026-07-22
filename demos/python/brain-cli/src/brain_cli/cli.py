import os
from pathlib import Path
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from brain_cli.models import Note
from brain_cli.storage.store import NoteStore
from brain_cli.search.engine import SearchEngine, keyword_search
from brain_cli.entities.extractor import EntityExtractor

load_dotenv()

app = typer.Typer(help="BrainCLI — A Second Brain personal knowledge management system.")
console = Console()

DEFAULT_VAULT = Path.cwd() / "vault"


def _vault_path(vault: Path | None) -> Path:
    return vault or DEFAULT_VAULT


def _store(vault: Path | None) -> NoteStore:
    return NoteStore(_vault_path(vault))


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _search(vault: Path | None) -> SearchEngine:
    return SearchEngine(_vault_path(vault))


def _extractor(vault: Path | None) -> EntityExtractor:
    return EntityExtractor(_vault_path(vault))


VaultOption = Annotated[
    Optional[Path],
    typer.Option("--vault", "-v", help="Path to the vault directory."),
]


@app.command()
def create(
    title: Annotated[str, typer.Argument(help="Title of the note.")],
    content: Annotated[str, typer.Option("--content", "-c", help="Note content.")] = "",
    tags: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Tags for the note.")] = None,
    vault: VaultOption = None,
    extract_entities: Annotated[bool, typer.Option("--extract", "-e", help="Extract entities after creation.")] = False,
):
    """Create a new note."""
    store = _store(vault)
    note = Note(title=title, content=content, tags=tags or [])
    saved = store.save(note)

    if _has_openai_key():
        search = _search(vault)
        search.index_note(saved)

    console.print(f"[green]Created note:[/green] {saved.title} [dim]({saved.id})[/dim]")

    if extract_entities:
        if not _has_openai_key():
            console.print("[yellow]Skipping entity extraction — OPENAI_API_KEY not set.[/yellow]")
        else:
            extractor = _extractor(vault)
            entities = extractor.extract(saved)
            if entities:
                console.print(f"[cyan]Extracted {len(entities)} entities:[/cyan]")
                for e in entities:
                    console.print(f"  • {e.name} [dim]({e.entity_type})[/dim]")


@app.command()
def view(
    note_id: Annotated[str, typer.Argument(help="ID of the note to view.")],
    vault: VaultOption = None,
):
    """View a note by its ID."""
    store = _store(vault)
    note = store.get(note_id)
    if not note:
        console.print(f"[red]Note not found:[/red] {note_id}")
        raise typer.Exit(1)

    console.print(f"[bold]{note.title}[/bold]  [dim]({note.id})[/dim]")
    console.print(f"[dim]Created: {note.created_at:%Y-%m-%d %H:%M}  |  Updated: {note.updated_at:%Y-%m-%d %H:%M}[/dim]")
    if note.tags:
        console.print(f"[cyan]Tags:[/cyan] {', '.join(note.tags)}")
    console.print()
    console.print(note.content)


@app.command()
def edit(
    note_id: Annotated[str, typer.Argument(help="ID of the note to edit.")],
    content: Annotated[Optional[str], typer.Option("--content", "-c", help="New content.")] = None,
    title: Annotated[Optional[str], typer.Option("--title", help="New title.")] = None,
    add_tag: Annotated[Optional[list[str]], typer.Option("--add-tag", help="Add a tag.")] = None,
    remove_tag: Annotated[Optional[list[str]], typer.Option("--remove-tag", help="Remove a tag.")] = None,
    vault: VaultOption = None,
):
    """Edit an existing note."""
    store = _store(vault)
    note = store.get(note_id)
    if not note:
        console.print(f"[red]Note not found:[/red] {note_id}")
        raise typer.Exit(1)

    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    if add_tag:
        note.tags = list(set(note.tags + add_tag))
    if remove_tag:
        note.tags = [t for t in note.tags if t not in remove_tag]

    saved = store.save(note)

    if _has_openai_key():
        search = _search(vault)
        search.index_note(saved)

    console.print(f"[green]Updated note:[/green] {saved.title} [dim]({saved.id})[/dim]")


@app.command()
def delete(
    note_id: Annotated[str, typer.Argument(help="ID of the note to delete.")],
    vault: VaultOption = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
):
    """Delete a note."""
    store = _store(vault)
    note = store.get(note_id)
    if not note:
        console.print(f"[red]Note not found:[/red] {note_id}")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete '{note.title}'?")
        if not confirm:
            raise typer.Abort()

    if _has_openai_key():
        search = _search(vault)
        search.remove_note(note_id)

    extractor = _extractor(vault)
    extractor.remove_note_entities(note_id)

    store.delete(note_id)
    console.print(f"[red]Deleted:[/red] {note.title}")


@app.command(name="list")
def list_notes(
    tag: Annotated[Optional[str], typer.Option("--tag", "-t", help="Filter by tag.")] = None,
    vault: VaultOption = None,
):
    """List all notes."""
    store = _store(vault)
    notes = store.list_notes(tag=tag)

    if not notes:
        console.print("[dim]No notes found.[/dim]")
        return

    table = Table(title="Notes")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Tags", style="cyan")
    table.add_column("Updated", style="dim")

    for note in sorted(notes, key=lambda n: n.updated_at, reverse=True):
        table.add_row(
            note.id,
            note.title,
            ", ".join(note.tags),
            note.updated_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    semantic: Annotated[bool, typer.Option("--semantic", "-s", help="Use semantic search.")] = False,
    vault: VaultOption = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results.")] = 10,
):
    """Search notes by keyword or semantically."""
    store = _store(vault)

    if semantic:
        if not _has_openai_key():
            console.print("[red]Semantic search requires OPENAI_API_KEY.[/red]")
            raise typer.Exit(1)
        engine = _search(vault)
        results = engine.semantic_search(query, limit=limit)
    else:
        notes = store.list_notes()
        results = keyword_search(query, notes, limit=limit)

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = Table(title=f"Search results for '{query}'" + (" (semantic)" if semantic else ""))
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Snippet", style="dim", max_width=60)

    for r in results:
        table.add_row(r.note_id, r.title, f"{r.score:.2f}", r.snippet[:60])

    console.print(table)


@app.command()
def links(
    note_id: Annotated[str, typer.Argument(help="Note ID to show links for.")],
    vault: VaultOption = None,
):
    """Show links and backlinks for a note."""
    store = _store(vault)
    note = store.get(note_id)
    if not note:
        console.print(f"[red]Note not found:[/red] {note_id}")
        raise typer.Exit(1)

    console.print(f"[bold]Links for:[/bold] {note.title} [dim]({note.id})[/dim]\n")

    outgoing = store.get_links(note_id)
    if outgoing:
        console.print("[cyan]Outgoing links →[/cyan]")
        for lid in outgoing:
            linked = store.get(lid)
            name = linked.title if linked else lid
            console.print(f"  → {name} [dim]({lid})[/dim]")
    else:
        console.print("[dim]No outgoing links.[/dim]")

    console.print()

    backlinks = store.get_backlinks(note_id)
    if backlinks:
        console.print("[cyan]← Backlinks[/cyan]")
        for lid in backlinks:
            linked = store.get(lid)
            name = linked.title if linked else lid
            console.print(f"  ← {name} [dim]({lid})[/dim]")
    else:
        console.print("[dim]No backlinks.[/dim]")


@app.command()
def graph(vault: VaultOption = None):
    """Show the full link graph as an adjacency list."""
    store = _store(vault)
    notes = store.list_notes()

    if not notes:
        console.print("[dim]No notes in vault.[/dim]")
        return

    console.print("[bold]Link Graph[/bold]\n")
    for note in notes:
        outgoing = store.get_links(note.id)
        if outgoing:
            targets = []
            for lid in outgoing:
                linked = store.get(lid)
                targets.append(linked.title if linked else lid)
            console.print(f"  {note.title} → {', '.join(targets)}")
        else:
            console.print(f"  {note.title} [dim](no links)[/dim]")

    orphans = store.get_orphans()
    if orphans:
        console.print(f"\n[yellow]Orphan notes ({len(orphans)}):[/yellow]")
        for oid in orphans:
            note = store.get(oid)
            name = note.title if note else oid
            console.print(f"  • {name} [dim]({oid})[/dim]")


@app.command()
def entities(
    note_id: Annotated[Optional[str], typer.Argument(help="Note ID (omit to show all).")] = None,
    find: Annotated[Optional[str], typer.Option("--find", "-f", help="Find notes mentioning this entity.")] = None,
    vault: VaultOption = None,
):
    """Show or search extracted entities."""
    extractor = _extractor(vault)

    if find:
        matches = extractor.find_notes_for_entity(find)
        if not matches:
            console.print(f"[dim]No entities matching '{find}'.[/dim]")
            return

        table = Table(title=f"Notes mentioning '{find}'")
        table.add_column("Entity", style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Note", style="dim")

        for e in matches:
            table.add_row(e.name, e.entity_type, f"{e.source_note_title} ({e.source_note_id})")
        console.print(table)
        return

    if note_id:
        ents = extractor.get_entities(note_id)
    else:
        ents = extractor.get_all_entities()

    if not ents:
        console.print("[dim]No entities found.[/dim]")
        return

    table = Table(title="Entities")
    table.add_column("Name", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Source Note", style="dim")

    for e in ents:
        table.add_row(e.name, e.entity_type, f"{e.source_note_title} ({e.source_note_id})")

    console.print(table)


@app.command()
def reindex(vault: VaultOption = None):
    """Rebuild all indexes from the vault files."""
    store = _store(vault)
    search = _search(vault)

    notes = store.list_notes()
    store.rebuild_link_index()
    search.reindex_all(notes)

    console.print(f"[green]Reindexed {len(notes)} notes.[/green]")


if __name__ == "__main__":
    app()

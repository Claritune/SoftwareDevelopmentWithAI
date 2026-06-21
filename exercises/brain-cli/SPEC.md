# BrainCLI — A Second Brain System

## Final Exercise: Software Development with AI Workshop

---

## What Is a "Second Brain"?

Your biological brain is excellent at having ideas but terrible at storing them. A "Second Brain" is a personal knowledge management system that lives outside your head — a place to capture, organize, connect, and retrieve everything you learn and think about.

The term was popularized by Tiago Forte, but the practice is centuries old. Commonplace books, Zettelkasten index cards, and personal wikis are all variations on the same idea: externalize your knowledge so your mind is free to think, not remember.

A good Second Brain system has four properties:

- **Capture** — quickly save any thought, note, or reference without friction
- **Connect** — link ideas to each other so that related knowledge surfaces naturally
- **Retrieve** — find anything you've saved, even when you've forgotten you saved it
- **Evolve** — your knowledge base grows smarter over time, not just bigger

---

## How Obsidian Works (Reference)

Obsidian is the most widely used Second Brain tool among developers. Understanding its design decisions will save you research time and inform your own implementation.

### Storage: Plain Markdown Files in a Vault

Obsidian stores every note as a plain `.md` (Markdown) file inside a regular folder on your local filesystem. This folder is called a **vault**. There is no database, no proprietary format — just files you can open with any text editor.

This is a deliberate design choice: your data outlives any tool. If Obsidian disappears tomorrow, your notes are still readable `.md` files.

The vault is monitored for filesystem changes, so notes edited externally (in VS Code, via a script, through Git) are automatically picked up.

### Metadata: YAML Frontmatter

Each note can have structured metadata at the very top, in a YAML block delimited by `---`:

```yaml
---
title: "Conway's Law and Agent Architecture"
tags:
  - architecture
  - agents
  - organization
aliases:
  - Conway's Law
created: 2026-06-10
---

The actual note content starts here...
```

Obsidian calls these **properties**. They support typed fields: text, numbers, dates, lists, checkboxes, and links. Properties enable filtering, sorting, and querying across your vault.

Key design principles:
- Frontmatter must be the very first thing in the file
- Property names should be consistent across notes (e.g. always `created`, never sometimes `date_created`)
- Five well-maintained properties are better than twenty inconsistent ones

### Linking: Wiki-Style Internal Links

The core of Obsidian's power is `[[wiki-style links]]` between notes. Typing `[[` opens an autocomplete for existing note titles.

```markdown
This connects to [[Conway's Law and Agent Architecture]].
You can also link to a specific heading: [[Conway's Law#Reverse Conway]].
Aliases work too: [[Conway's Law]].
```

Links are **bidirectional** by design. If Note A links to Note B, then Note B automatically shows Note A in its **backlinks** panel. You never have to create the reverse link manually — the system maintains a backlink index.

The vault also detects **unlinked mentions**: places where a note's title appears in another note's text but isn't wrapped in `[[]]`.

### Graph View

Obsidian visualizes the vault as a knowledge graph — notes are nodes, links are edges. The graph reveals clusters of related ideas, orphan notes with no connections, and hub notes that connect many topics.

NOTE: The graph view is not related to the LangGraph library. 

### Search

Obsidian provides full-text search across all notes and their metadata. The search supports:
- Boolean operators (`meeting AND work`, `meeting OR work`)
- Exact phrases (`"second brain"`)
- Negation (`meeting -work`)
- Regex patterns (`/\d{4}-\d{2}-\d{2}/`)
- Property filters (`[status:draft]`, `[tags:architecture]`)
- Path filters (`path:projects/`)

The search is keyword-based (not semantic). There is no built-in vector search — semantic search is available only through community plugins.

### Tags

Notes can have tags both in frontmatter and inline in the body (`#architecture`). Tags support hierarchy via nesting (`#projects/mobile`). Tags serve as a lightweight organizational layer alongside links and folders.

### What Obsidian Does NOT Do

- No built-in semantic/AI search
- No entity extraction or knowledge graph beyond simple note links
- No temporal tracking of how facts change over time
- No AI-assisted note enrichment

These gaps are where your implementation will go beyond Obsidian.

---

## Your Task

Build **BrainCLI** — a CLI-based Second Brain system in Python.

BrainCLI should follow Obsidian's core philosophy (local markdown files, wiki-style linking, backlinks) but extend it with AI-powered capabilities that Obsidian lacks: semantic search and intelligent entity extraction.

---

## Requirements

### R1: Note Management

- R1.1: Create a note with a title, body content, and optional tags
- R1.2: View a note by title or identifier
- R1.3: Edit a note's content
- R1.4: Delete a note
- R1.5: List all notes, with optional filtering by tag
- R1.6: Notes are stored as Markdown files with YAML frontmatter
- R1.7: Each note has at minimum: title, creation timestamp, last modified timestamp, tags, and a unique identifier

### R2: Linking and Backlinks

- R2.1: Note content supports `[[wiki-style links]]` to other notes
- R2.2: The system maintains a backlink index — for any note, you can query which other notes link to it
- R2.3: When a note is created, updated, or deleted, the link index updates accordingly
- R2.4: The system can report orphan notes (notes with no incoming or outgoing links)
- R2.5: The system can display the link graph as an adjacency list (which notes connect to which)

### R3: Search

- R3.1: Full-text keyword search across note contents
- R3.2: Semantic search — find notes by meaning, not just exact words (e.g., searching "software architecture" should find a note about "system design patterns" even if it never uses the word "architecture")
- R3.3: Search results include the note identifier, title, and a relevance indicator
- R3.4: Search should work across both note content and metadata (tags, title)

### R4: AI-Powered Entity Extraction

- R4.1: When a note is saved, the system extracts notable entities (people, organizations, projects, technologies, locations) from its content
- R4.2: Entity extraction uses a local LLM (e.g., Llama 3.1 8B via Ollama)
- R4.3: Extracted entities are stored with the relationship to their source note
- R4.4: The system can answer "what do my notes say about [entity]?" — returning all notes and extracted facts related to a given entity
- R4.5: When newer notes contradict earlier extracted facts, the system tracks both versions with timestamps rather than silently overwriting

### R5: CLI Interface

- R5.1: All functionality is accessible through a command-line interface
- R5.2: No graphical UI is required
- R5.3: The CLI should support at minimum the following operations: create, view, edit, delete, list, search, links (show links/backlinks for a note), graph (show full link graph), entities (show extracted entities)
- R5.4: The CLI should provide clear help text for all commands
- R5.5: Output should be human-readable in terminal

### R6: Data Integrity

- R6.1: The vault (note storage directory) is the source of truth — all notes exist as readable `.md` files at all times
- R6.2: Any indexes, caches, or databases are derived from the vault and can be rebuilt from scratch
- R6.3: Deleting a note removes the file and cleans up references in all indexes

---

## Non-Requirements (Out of Scope)

- GUI or web interface
- Multi-user or collaboration
- Sync across devices
- Note templates
- Attachment handling (images, PDFs)
- Note-to-note transclusion / embedding

---

## Technical Constraints

- **Language:** Python 3.12+
- **LLM:** Local model via Ollama (Llama 3.1 8B recommended). Ollama is pre-installed.
- **No external API calls** for core functionality — everything runs locally
- **Testing:** pytest

---

## Suggested (Not Mandated) Architecture

The requirements above describe WHAT the system should do. HOW you structure it is up to you and your AI agent. However, here is an observation worth considering:

The requirements cluster naturally into four areas of responsibility: note storage (R1, R6), linking (R2), search (R3), and entity extraction (R4), with the CLI (R5) as the integration layer on top. Whether you organize your code around these clusters is a design decision — and one worth documenting.

---

## Getting Started

Use the QRSPI methodology from Day 1 to plan before you implement. Set up your project with AGENTS.md, rules, and hooks before writing application code. Apply TDD where appropriate. Write ADRs for your key design decisions.

Good luck. Build something that would make your future self grateful.

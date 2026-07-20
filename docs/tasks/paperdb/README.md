# PaperDB Implementation — Parallel Task Breakdown

## Overview

PaperDB is implemented by multiple agents working in parallel. Each agent owns a specific set of files and must not modify files owned by other agents. All agents reference the shared design document: [`docs/topical_audit/paper_db_notes.md`](../../topical_audit/paper_db_notes.md).


NOTE:
most of dependnecies are already instaled in venv ML which you can activate like this
```
prokop@GTX3090:~/git/AutoCrunchCoder$ venvML
(ML) prokop@GTX3090:~/git/AutoCrunchCoder$ 
```

## Task assignments

| Task | Agent responsibility | Depends on |
|------|----------------------|------------|
| [Task 1: Foundation](task1_foundation.md) | DB schema, models, repository, package skeleton, PaperDB API | — (critical path) |
| [Task 2: Identity & Migration](task2_identity_migration.md) | Hashing, dedup, DOI normalization, BibTeX parsing, scanner, legacy migration | Task 1 (db models, repository) |
| [Task 3: Search & Retrieval](task3_search_retrieval.md) | FTS5 search, weighted ranking with --explain, context pack assembly | Task 1 (db models, repository) |
| [Task 4: CLI & MCP](task4_cli_mcp.md) | Typer CLI, MCP server (read-only by default) | Task 1 (PaperDB API) |
| [Task 5: Extraction & Ingest](task5_extraction_ingest.md) | Docling backend, equation extraction, method extraction, ingest pipeline, fetch | Task 1 (db models, repository) |
| [Task 6: Taxonomy & Synthesis](task6_taxonomy_synthesis.md) | Tag extraction, tag aliases, summaries, method cards, topic reviews | Task 1 (db models, repository) |

## Parallelization strategy

```
Time →

Task 1 (Foundation) ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░
Task 2 (Identity)   ░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░
Task 3 (Search)     ░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░
Task 4 (CLI/MCP)    ░░░░░░░░░░░░░░░░████████████████░░░░░░░░░░
Task 5 (Extraction) ░░░░░░░░░░░░░░░░██████████████████████████
Task 6 (Taxonomy)   ░░░░░░░░░░░░░░░░██████████████████████████
```

- **Task 1 is the critical path.** It must be completed first (or at least the API interface defined).
- **Tasks 2-6 can start immediately** by coding against the PaperDB API interface defined in Task 1's spec. Use stub/mock implementations for testing until Task 1 is ready.
- **No file conflicts**: each file is owned by exactly one task.

## File ownership map

| File | Owner |
|------|-------|
| `pyproject.toml` (repo root) | Task 1 |
| `paperdb/__init__.py` | Task 1 |
| `paperdb/paths.py` | Task 1 |
| `paperdb/config.py` | Task 1 |
| `paperdb/db/__init__.py` | Task 1 |
| `paperdb/db/connection.py` | Task 1 |
| `paperdb/db/schema.sql` | Task 1 |
| `paperdb/db/migrations/` | Task 1 |
| `paperdb/db/repository.py` | Task 1 |
| `paperdb/db/models.py` | Task 1 |
| `paperdb/identity/__init__.py` | Task 1 (creates empty) |
| `paperdb/ingest/__init__.py` | Task 1 (creates empty) |
| `paperdb/extract/__init__.py` | Task 1 (creates empty) |
| `paperdb/search/__init__.py` | Task 1 (creates empty) |
| `paperdb/synthesis/__init__.py` | Task 1 (creates empty) |
| `paperdb/taxonomy/__init__.py` | Task 1 (creates empty) |
| `paperdb/identity/hashing.py` | Task 2 |
| `paperdb/identity/matching.py` | Task 2 |
| `paperdb/identity/metadata.py` | Task 2 |
| `paperdb/ingest/scanner.py` | Task 2 |
| `paperdb/ingest/migration.py` | Task 2 |
| `paperdb/search/fts.py` | Task 3 |
| `paperdb/search/ranking.py` | Task 3 |
| `paperdb/search/context.py` | Task 3 |
| `paperdb/cli.py` | Task 4 |
| `paperdb/mcp.py` | Task 4 |
| `paperdb/extract/base.py` | Task 5 |
| `paperdb/extract/docling_backend.py` | Task 5 |
| `paperdb/extract/equations.py` | Task 5 |
| `paperdb/extract/methods.py` | Task 5 |
| `paperdb/ingest/pipeline.py` | Task 5 |
| `paperdb/ingest/jobs.py` | Task 5 |
| `paperdb/ingest/fetch.py` | Task 5 |
| `paperdb/taxonomy/extraction.py` | Task 6 |
| `paperdb/taxonomy/aliases.py` | Task 6 |
| `paperdb/synthesis/summaries.py` | Task 6 |
| `paperdb/synthesis/method_cards.py` | Task 6 |
| `paperdb/synthesis/topic_reviews.py` | Task 6 |

## Rules for all agents

1. **Read the design doc first**: `docs/topical_audit/paper_db_notes.md` — especially §7 (architecture), §8 (data directory), §9 (schema), and §18 (design decisions).
2. **Only modify files you own.** If you need a change in another agent's file, document it as a dependency note and wait.
3. **Task 1 creates all `__init__.py` files** for subpackages (empty or minimal). Other agents must NOT modify these.
4. **Code against the PaperDB API interface**, not against internal repository details. The API is defined in `paperdb/__init__.py` by Task 1.
5. **Write tests** in `tests/paperdb/test_<task_name>/` — each task has its own test directory.
6. **Follow existing project conventions**: see `AGENTS.md`, use `pyCruncher.Agent` for LLM access, `config/LLMs.toml` for provider config.
7. **Fail loud**: no silent try/except. Crashes with stack traces > masked bugs.
8. **Compact code**: unlimited line width, short names for math symbols, inline comments.

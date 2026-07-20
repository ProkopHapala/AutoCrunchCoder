# Task 1: Foundation — DB Schema, Models, Repository, Package Skeleton

## Your role

You build the **critical-path foundation** that all other agents depend on. Your deliverables are: the SQLite schema, Pydantic models, the repository layer (all SQL), the `PaperDB` public API facade, and the package skeleton with all `__init__.py` files.

## Files you own (ONLY modify these)

```
pyproject.toml                              # at AutoCrunchCoder repo root
paperdb/__init__.py                         # PaperDB main class — public API facade
paperdb/paths.py                            # data dir resolution (~/paperdb/, PAPERDB_DATA env)
paperdb/config.py                           # LLM config via pyCruncher.Agent + config/LLMs.toml
paperdb/db/__init__.py
paperdb/db/connection.py                    # SQLite connection, WAL, PRAGMA foreign_keys=ON
paperdb/db/schema.sql                       # canonical schema (from §9 of design doc)
paperdb/db/migrations/001_init.sql          # first migration
paperdb/db/repository.py                    # ALL SQL queries — CRUD for every table
paperdb/db/models.py                        # Pydantic models: Paper, Tag, Equation, Method, SearchUnit, etc.
```

You also create **empty `__init__.py`** files for all subpackages:
```
paperdb/identity/__init__.py
paperdb/ingest/__init__.py
paperdb/extract/__init__.py
paperdb/search/__init__.py
paperdb/synthesis/__init__.py
paperdb/taxonomy/__init__.py
```

## Files you must NOT touch

Everything else. Other agents own:
- Task 2: `paperdb/identity/hashing.py`, `matching.py`, `metadata.py`, `paperdb/ingest/scanner.py`, `migration.py`
- Task 3: `paperdb/search/fts.py`, `ranking.py`, `context.py`
- Task 4: `paperdb/cli.py`, `paperdb/mcp.py`
- Task 5: `paperdb/extract/*.py`, `paperdb/ingest/pipeline.py`, `jobs.py`, `fetch.py`
- Task 6: `paperdb/taxonomy/*.py`, `paperdb/synthesis/*.py`

## Reference

Read `docs/topical_audit/paper_db_notes.md` — especially:
- **§7** (architecture) — module layout
- **§8** (data directory) — `~/paperdb/` layout, representations and their roles, source of truth
- **§9** (database schema) — full SQL schema with all tables, triggers, indices
- **§12** (packaging) — `pyproject.toml` at repo root
- **§13** (environment) — env vars, PATH
- **§18 D18** (architecture rule) — CLI/MCP/GUI → PaperDB API → repository/services
- **§18 D19** (source of truth) — SQLite authoritative for structured data

## Steps

### Step 1: Package skeleton

1. Create `pyproject.toml` at AutoCrunchCoder repo root (NOT inside `paperdb/`). See §12 of design doc for exact content. Dependencies: `bibtexparser`, `openai`, `pydantic`, `jinja2`, `requests`, `typer`, `toml`. Optional: `docling`, `PyQt5`, `fastmcp`, `sqlite-vec`, `sentence-transformers`. No self-referential `all` extra.
2. Create `paperdb/__init__.py` with the `PaperDB` class (see Step 5 below).
3. Create `paperdb/paths.py` — resolve data directory from `PAPERDB_DATA` env var (default `~/paperdb/`). Provide `get_data_dir()`, `get_db_path()`, `get_papers_dir()`, `get_legacy_dir()`, `get_logs_dir()`. Create directories on demand.
4. Create `paperdb/config.py` — load LLM config from `config/LLMs.toml` using `pyCruncher.Agent`. Provide `get_llm_config(key)` that returns provider settings. Default key from `PAPERDB_LLM` env var.
5. Create all empty `__init__.py` files for subpackages.

### Step 2: DB connection

1. Create `paperdb/db/connection.py`:
   - `get_connection(db_path=None)` → SQLite connection with `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`.
   - Context manager support.
   - Single connection per process (don't open one per operation).

### Step 3: Schema

1. Create `paperdb/db/schema.sql` — copy the full schema from §9 of the design doc. This includes:
   - `papers` (no `preferred_file_id` — use `paper_files.is_preferred` instead)
   - `paper_files` (with partial unique index for preferred, indices on `paper_id` and `sha256`)
   - `search_units` (with `run_id`, `source_type`, `source_id`)
   - `search_units_fts` (FTS5 external content)
   - FTS5 sync triggers (`search_units_ai`, `search_units_ad`, `search_units_au`)
   - `processing_runs` (with `source_file_id`, `input_sha256`, `output_path`, `supersedes_run_id`)
   - `tags`, `tag_aliases` (NOT globally unique — `UNIQUE(tag_id, normalized_alias)`), `paper_tags` (with `run_id`)
   - `equations`, `equation_variables`
   - `methods` (simplified — `card_json` for evolving fields), `method_equations` junction
   - `summaries`
   - `topics`, `topic_papers`, `topic_overviews`
   - `context_packs`
   - `citations`
2. Create `paperdb/db/migrations/001_init.sql` — same as schema.sql but as a migration.

### Step 4: Models

1. Create `paperdb/db/models.py` — Pydantic models for all entities:
   - `Paper` (id, paper_key, doi, arxiv_id, title, authors_text, year, journal, abstract, keywords, essence, markdown_path, json_path, bibtex_path, created_at, updated_at)
   - `PaperFile` (id, paper_id, path, file_role, version_label, file_size, modified_time, sha256, exists_now, is_preferred, last_seen)
   - `SearchUnit` (id, paper_id, run_id, unit_type, source_type, source_id, section_path, page_from, page_to, content)
   - `ProcessingRun` (id, paper_id, operation, backend, backend_version, model_name, prompt_version, configuration_json, config_hash, source_file_id, input_sha256, output_path, supersedes_run_id, status, started_at, finished_at, message)
   - `Tag` (id, canonical_name, category)
   - `TagAlias` (tag_id, alias, normalized_alias)
   - `PaperTag` (paper_id, tag_id, source, run_id, confidence, raw_name)
   - `Equation` (id, paper_id, run_id, latex_raw, latex_normalized, equation_number, section_path, page_number, bbox_json, context_before, context_after, parser, confidence, verification_status)
   - `EquationVariable` (id, equation_id, symbol, meaning, source_page, source_context)
   - `Method` (id, paper_id, run_id, name, method_type, purpose, complexity, confidence, card_json, source_passages_json, created_at)
   - `MethodEquation` (method_id, equation_id, role)
   - `Summary` (id, paper_id, run_id, model_name, prompt_version, content, timestamp, is_active)
   - `ContextPack` (id, query, filters_json, selected_units_json, content, output_path, created_at)
   - `Topic`, `TopicPaper`, `TopicOverview`
   - `Citation`

### Step 5: Repository

1. Create `paperdb/db/repository.py` — ALL SQL queries. This is the single place where SQL lives. Provide:
   - `Repository(connection)` class
   - Papers: `upsert_paper()`, `get_paper()`, `get_paper_by_key()`, `get_paper_by_doi()`, `list_papers()`, `update_paper_paths()`
   - Files: `add_paper_file()`, `get_files_for_paper()`, `set_preferred_file()`, `find_file_by_hash()`
   - Search units: `replace_search_units(paper_id, units)` — transactional delete+insert, `get_search_units_for_paper()`
   - Processing runs: `start_run()`, `finish_run()`, `get_current_run()`, `supersede_run()`, `find_equivalent_run()`
   - Tags: `upsert_tag()`, `add_alias()`, `resolve_alias()`, `get_tags_for_paper()`, `add_paper_tag()`
   - Equations: `upsert_equation()`, `get_equations_for_paper()`, `add_variable()`
   - Methods: `upsert_method()`, `get_methods_for_paper()`, `link_method_equation()`
   - Summaries: `add_summary()`, `get_active_summary()`, `list_summaries()`
   - Context packs: `save_context_pack()`, `get_context_pack()`
   - Topics: `upsert_topic()`, `add_topic_paper()`, `save_topic_overview()`
   - Citations: `add_citation()`, `get_citations_for_paper()`
   - Stats: `get_status_counts()`

### Step 6: PaperDB API facade

1. Create `paperdb/__init__.py` with `PaperDB` class — the stable public API that CLI, MCP, and other modules use. This is the **interface contract** that other agents code against:

```python
class PaperDB:
    def __init__(self, data_dir=None, db_path=None): ...

    # Papers
    def get_paper(self, id_or_key_or_doi) -> Paper: ...
    def list_papers(self, limit=100, offset=0) -> list[Paper]: ...
    def upsert_paper(self, paper: Paper) -> int: ...

    # Files
    def add_file(self, paper_id, path, role=None) -> int: ...
    def get_files(self, paper_id) -> list[PaperFile]: ...
    def set_preferred_file(self, paper_id, file_id): ...

    # Search (delegates to search/ module — Task 3 implements)
    def search(self, query, required_tags=None, preferred_tags=None, year_range=None, limit=20, explain=False) -> list[SearchResult]: ...
    def retrieve_context(self, query, token_budget=24000, include=None, filters=None) -> ContextPack: ...

    # Processing (delegates to ingest/ module — Tasks 2/5 implement)
    def scan_folder(self, path, recursive=True): ...
    def ingest_paper(self, paper_id, operations=None): ...
    def get_processing_status(self, paper_id) -> dict: ...

    # Content access
    def get_markdown(self, paper_id) -> str: ...
    def get_equations(self, paper_id) -> list[Equation]: ...
    def get_methods(self, paper_id) -> list[Method]: ...
    def get_tags(self, paper_id) -> list[Tag]: ...
    def get_summary(self, paper_id) -> str: ...

    # Taxonomy (delegates to taxonomy/ module — Task 6 implements)
    def list_tags(self, category=None) -> list[Tag]: ...
    def merge_tags(self, tag_id, alias): ...

    # Status
    def status(self) -> dict: ...
```

2. Initially, methods that delegate to other tasks' modules can raise `NotImplementedError("Task N implements this")`. Other agents will replace these with real implementations.

### Step 7: Tests

1. Create `tests/paperdb/test_foundation/` with tests:
   - `test_connection.py` — WAL mode, FK enforcement
   - `test_schema.py` — all tables exist, triggers work
   - `test_repository.py` — CRUD for each table, transactional search unit replacement
   - `test_models.py` — Pydantic model validation
   - `test_paths.py` — data dir resolution, env var override

## Deliverable checklist

- [ ] `pyproject.toml` at repo root
- [ ] `paperdb/__init__.py` with `PaperDB` class (API interface)
- [ ] `paperdb/paths.py`, `paperdb/config.py`
- [ ] All `__init__.py` files for subpackages (empty)
- [ ] `paperdb/db/connection.py`, `schema.sql`, `migrations/001_init.sql`
- [ ] `paperdb/db/models.py` — all Pydantic models
- [ ] `paperdb/db/repository.py` — all SQL CRUD
- [ ] Tests in `tests/paperdb/test_foundation/`
- [ ] `pip install -e .` works and `python -c "from paperdb import PaperDB"` succeeds

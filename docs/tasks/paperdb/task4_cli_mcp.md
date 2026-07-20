# Task 4: CLI & MCP Server

## Your role

You build the **user-facing access layer**: the Typer CLI (`paperdb` command) and the MCP server (for coding agents like Cursor, Claude Desktop, Devin, OpenCode). Both are thin wrappers — no SQL, no parsing logic — all goes through the `PaperDB` API facade.

## Files you own (ONLY modify these)

```
paperdb/cli.py                     # Typer CLI — thin wrapper over PaperDB API
paperdb/mcp.py                     # MCP server — read-only by default
```

## Files you must NOT touch

- `paperdb/__init__.py`, `paperdb/paths.py`, `paperdb/config.py` — Task 1
- `paperdb/db/*` — Task 1
- `paperdb/identity/*`, `paperdb/ingest/scanner.py`, `migration.py` — Task 2
- `paperdb/search/*` — Task 3
- `paperdb/extract/*`, `paperdb/ingest/pipeline.py`, `jobs.py`, `fetch.py` — Task 5
- `paperdb/taxonomy/*`, `paperdb/synthesis/*` — Task 6
- All `__init__.py` files — Task 1

## Reference

Read `docs/topical_audit/paper_db_notes.md` — especially:
- **§10** (CLI design) — full command list with examples
- **§12** (packaging) — `pyproject.toml` scripts entry, system-wide accessibility
- **§13** (environment) — PATH, env vars, `.bashrc` template
- **§14** (MCP server) — transport modes, agent config, tool catalog, resources
- **§18 D17** (MCP design) — scientific tasks, read-only by default
- **§18 D18** (architecture) — CLI/MCP/GUI → PaperDB API → repository/services

## Dependencies

- **Task 1 must be complete** (or API interface defined). You need:
  - `paperdb.PaperDB` — the API facade. ALL your code calls methods on this class.
  - `paperdb.paths` — for data directory in `--data-dir` flag
  - `paperdb.config` — for LLM config key in `--llm-config` flag

- **Tasks 2, 3, 5, 6** implement the methods you call. Until they're ready, methods will raise `NotImplementedError`. You can still build and test the CLI/MCP structure against the API interface.

## Interface contract

You call `PaperDB` methods. Here's what's available (defined by Task 1):

```python
db = PaperDB(data_dir=None, db_path=None)
db.scan_folder(path, recursive=True)
db.ingest_paper(paper_id, operations=None)
db.search(query, required_tags=None, preferred_tags=None, year_range=None, limit=20, explain=False)
db.retrieve_context(query, token_budget=24000, include=None, filters=None)
db.get_paper(id_or_key_or_doi)
db.get_markdown(paper_id)
db.get_equations(paper_id)
db.get_methods(paper_id)
db.get_tags(paper_id)
db.get_summary(paper_id)
db.list_tags(category=None)
db.status()
```

## Steps

### Step 1: CLI (`paperdb/cli.py`)

Build with `typer`. Single command `paperdb` (alias `papers`). All commands delegate to `PaperDB` — no SQL, no parsing.

```python
import typer
from paperdb import PaperDB

app = typer.Typer(name="paperdb", help="Scientific paper compiler and retrieval service")

def get_db(ctx: typer.Context) -> PaperDB:
    """Get PaperDB instance from context."""
```

Commands to implement (from §10 of design doc):

```bash
# Scanning & ingestion
paperdb scan <folder> --recursive          # → db.scan_folder()
paperdb sync [--folder <path>]             # → db.scan_folder() on watched folders + ingest new
paperdb add <path_or_url_or_doi>           # → fetch + ingest single paper
paperdb ingest --all|--folder|--paper      # → db.ingest_paper()

# Search
paperdb search <query> [--tag <tag>] [--year <range>] [--explain] [--limit N]
paperdb context <query> [--budget N] [--include <types>] [--out <file>] [--save]

# Inspection
paperdb inspect <paper_key>                # → db.get_paper() + processing status
paperdb get <paper_key> --markdown|--json|--bib|--all
paperdb equations <paper_key>              # → db.get_equations()
paperdb methods <query>                    # → search for methods across papers
paperdb method <paper_key> --name <name>   # → show method card with evidence

# Tags
paperdb tags [--category <cat>]
paperdb tags --merge <tag1> <tag2>
paperdb related <paper_key>

# Topical overviews
paperdb topic <topic> [--json] [--out <file>]
paperdb compare <topic> --axes <axes>

# Export
paperdb export --bibtex --out <file>

# Re-processing
paperdb reindex --re-summarize [--llm-config <key>]
paperdb reindex --re-tag
paperdb reindex --re-extract-equations

# Status
paperdb status [--missing <field>] [--needs-reprocessing]

# Server modes
paperdb mcp --transport stdio|sse [--port N]
paperdb gui

# Migration
paperdb migrate --from <db_path> [--from-mendeley <bib_path>]
```

Output formatting:
- Default: human-readable (tables, colored text).
- `--json`: JSON output for LLM/programmatic consumption.
- `--explain`: show scoring breakdown for search results.
- Use `rich` for table formatting if available (add to dependencies if needed).

### Step 2: MCP server (`paperdb/mcp.py`)

Build with `fastmcp` (or `mcp` package). **Read-only by default.** Mutating tools are separate and opt-in.

```python
from fastmcp import FastMCP
from paperdb import PaperDB

mcp = FastMCP("paperdb")
db = PaperDB()
```

Transport modes (from §14):
```bash
paperdb mcp --transport stdio          # for IDE-integrated agents
paperdb mcp --transport sse --port 8000  # for remote/web agents
```

#### Discovery tools (scientific tasks)

| Tool | Implementation |
|------|----------------|
| `search_papers(query, required_tags, preferred_tags, excluded_tags, year_range, limit)` | `db.search()` with explain=True |
| `find_methods(problem, constraints, limit)` | `db.search()` filtered by method-type tags + retrieve method cards |
| `find_equations(concept, variables, tags, limit)` | `db.search()` filtered + `db.get_equations()` for top papers |
| `compare_methods(problem, comparison_axes, constraints, max_papers)` | Search + assemble comparison matrix |
| `build_topic_review(topic, focus, constraints, max_papers)` | Multi-step: search → method cards → compare → synthesize |

#### Inspection tools

| Tool | Implementation |
|------|----------------|
| `get_paper(paper_id_or_key_or_doi)` | `db.get_paper()` |
| `get_paper_markdown(paper_id)` | `db.get_markdown()` |
| `get_paper_methods(paper_id)` | `db.get_methods()` |
| `get_paper_equations(paper_id)` | `db.get_equations()` |
| `get_related_papers(paper_id, limit)` | Papers sharing tags |
| `explain_paper_match(paper_id, query)` | Why this paper matched |

#### Context pack tool

| Tool | Implementation |
|------|----------------|
| `retrieve_context(query, token_budget, include, filters)` | `db.retrieve_context()` |

#### Taxonomy tools

| Tool | Implementation |
|------|----------------|
| `list_tags(category)` | `db.list_tags()` |
| `list_tag_aliases(tag_id)` | Tag aliases for a canonical tag |

#### Mutating tools (separate, NOT enabled by default)

| Tool | Notes |
|------|-------|
| `ingest_pdf(path_or_url)` | Opt-in only. Requires `--allow-mutations` flag. |
| `reprocess_document(paper_id, operations)` | Opt-in only. |
| `merge_tags(tag_id, alias)` | Opt-in only. |

#### Resources

```
paperdb://paper/{paper_key}          → paper metadata + summary
paperdb://paper/{paper_key}/markdown → full markdown
paperdb://paper/{paper_key}/json     → structured JSON
paperdb://paper/{paper_key}/bib      → BibTeX
paperdb://tags                       → all tags grouped by category
paperdb://context/{id}               → saved context pack
```

### Step 3: Tests

1. Create `tests/paperdb/test_cli_mcp/`:
   - `test_cli.py` — invoke CLI commands with `typer.testing.CliRunner`, verify output format
   - `test_cli_search.py` — search with various flags, --explain, --json
   - `test_mcp.py` — verify MCP tool schemas, test read-only enforcement
   - `test_mcp_context.py` — retrieve_context tool returns context pack

## Deliverable checklist

- [ ] `paperdb/cli.py` — all commands from §10, thin wrapper over PaperDB
- [ ] `paperdb/mcp.py` — MCP server with all tools from §14, read-only by default
- [ ] `paperdb mcp --transport stdio` starts and responds to tool calls
- [ ] `paperdb search "test" --explain` produces formatted output
- [ ] `paperdb context "test" --out context.md` writes a context pack file
- [ ] Tests in `tests/paperdb/test_cli_mcp/`

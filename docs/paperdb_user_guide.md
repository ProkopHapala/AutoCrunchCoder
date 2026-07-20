# PaperDB — User Guide

PaperDB is a local scientific paper knowledge base. It compiles PDFs into structured
scientific representations (Markdown + JSON + BibTeX), indexes them with full-text search
and semantic tags, retrieves relevant context for LLM coding agents, and generates topical
overviews comparing methods across papers.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Environment Setup](#2-environment-setup)
3. [Installation](#3-installation)
4. [Data Directory Structure](#4-data-directory-structure)
5. [CLI Usage](#5-cli-usage)
6. [Python API](#6-python-api)
7. [MCP Server — Resident Mode](#7-mcp-server--resident-mode)
8. [LLM Agent Integration](#8-llm-agent-integration)
9. [Data Conversion — Legacy Migration](#9-data-conversion--legacy-migration)
10. [Folder Management](#10-folder-management)
11. [Verification State and Remaining Limitations](#11-verification-state-and-remaining-limitations)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / MCP / GUI                       │
│                  (paperdb/cli.py, mcp.py)                │
├─────────────────────────────────────────────────────────┤
│                  PaperDB API (facade)                    │
│                  (paperdb/__init__.py)                   │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ identity │  ingest  │  search  │ extract  │  synthesis   │
│ (hashing,│ (scanner,│ (FTS5,   │ (docling,│ (summaries,  │
│  matching│  pipeline│  ranking,│  equations│ method_cards,│
│  metadata│  fetch,  │  context)│  methods)│ topic_reviews│
│  migration│  jobs)  │          │          │  taxonomy)   │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│              Repository (all SQL)                        │
│              (paperdb/db/repository.py)                  │
├─────────────────────────────────────────────────────────┤
│              SQLite (papers.db, WAL mode)                │
└─────────────────────────────────────────────────────────┘
```

**Key design principles:**
- **Markdown is the central representation** — each paper has one `.md` file containing
  the generated scientific summary + extracted source text.
- **SQLite is the source of truth** for structured metadata; JSON and BibTeX are
  synchronized materialized views.
- **Search units** (section/paragraph/equation/method level) power FTS5, not paper-level blobs.
- **Processing provenance** — every operation (convert, summarize, tag, extract) is tracked
  in `processing_runs` with backend, model, config hash, and input SHA-256.
- **Read-only MCP by default** — mutating tools require `--allow-mutations`.

---

## 2. Environment Setup

### Prerequisites

- Python ≥ 3.10
- `venvML` virtual environment (already configured on this machine)
- Docling CLI (for PDF conversion) — install separately: `pip install docling`
- An LLM API key (for summarization, tagging, method reconstruction)

### Activate the virtual environment

```bash
prokop@GTX3090:~/git/AutoCrunchCoder$ venvML
(ML) prokop@GTX3090:~/git/AutoCrunchCoder$
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPERDB_DATA` | `~/paperdb/` | Root data directory for database, papers, logs |
| `PAPERDB_DB` | `$PAPERDB_DATA/papers.db` | Override SQLite database path |
| `PAPERDB_LLM` | first template in `config/LLMs.toml` | LLM config key for summarize/tag/extract |
| `DEEPSEEK_API_KEY` | — | API key for DeepSeek models |
| `GOOGLE_API_KEY` | — | API key for Google/Gemini models |

Example:
```bash
export PAPERDB_DATA=~/paperdb
export PAPERDB_LLM=deepseek-coder
export DEEPSEEK_API_KEY=sk-...
```

### LLM configuration

PaperDB uses `config/LLMs.toml` as the single source of truth for LLM provider profiles.
Available templates include: `deepseek-coder`, `gemini-flash`, `gemini-pro`, `claude-sonnet`, and more.

To use a specific LLM for summarization/tagging:
```bash
export PAPERDB_LLM=gemini-flash
```

---

## 3. Installation

### From the repository

```bash
cd ~/git/AutoCrunchCoder
venvML
pip install -e .
```

This installs the `paperdb` command-line tool and Python package.

### Optional extras

```bash
pip install -e ".[docling]"   # PDF conversion via Docling
pip install -e ".[mcp]"       # MCP server (fastmcp)
pip install -e ".[vlm]"       # VLM-based PDF extraction (pdf2image, Pillow)
pip install -e ".[vector]"    # Vector search (sqlite-vec, sentence-transformers)
```

### Verify installation

```bash
paperdb status
python -c "from paperdb import PaperDB; db = PaperDB(); print(db.status())"
```

---

## 4. Data Directory Structure

After setup and usage, the data directory looks like:

```
~/paperdb/
├── papers.db              # SQLite database (source of truth)
├── .hash_cache.json       # SHA-256 cache (size+mtime keyed)
├── papers/                # One .md/.json/.bib per paper, grouped by year
│   ├── 2016/
│   │   ├── Macklin_2016_XPBD__p0001.md
│   │   ├── Macklin_2016_XPBD__p0001.json
│   │   └── Macklin_2016_XPBD__p0001.bib
│   ├── 2020/
│   │   └── ...
│   └── unknown/
│       └── ...            # Papers with no year metadata
├── legacy/                # Copy of migrated legacy data (non-destructive)
│   └── consolidated.db    # Copied from tests/paper_pipeline_out/
└── logs/
│   ├── migration_report.md  # Generated during migration
│   └── debug/               # Raw parser output (if --keep-debug)
```

Remote PDFs are acquired only when the caller supplies an explicit destination outside PaperDB's generated-artifact tree.

**Key rules:**
- Scanned/local PDFs are **never moved, copied, or renamed** — they stay in their original location.
- DOI input without `--dest-dir` creates or enriches a metadata-only record. arXiv and direct URL acquisition require `--dest-dir`.
- The database tracks file paths and SHA-256 hashes.
- One `.md`, `.json`, `.bib` bundle per paper, named `{paper_key}__p{id:04d}.{ext}`.
- `paper_key` format: `Author_Year_Keyword` (e.g. `Macklin_2016_XPBD`).

---

## 5. CLI Usage

The CLI is a thin wrapper over the PaperDB Python API. All commands support `--json` for
machine-readable output.

### Scanning & ingestion

```bash
# Scan a folder for PDFs and index them (PDFs stay in place)
paperdb scan ~/Downloads/Milan_Articles\ Self-Assembly/

# Add a local paper in place
paperdb add ~/Downloads/paper.pdf

# DOI without a destination imports metadata/BibTeX only
paperdb add 10.1021/acs.jctc.4c00001

# Remote PDF acquisition always names a user-owned destination
paperdb add 10.1021/acs.jctc.4c00001 --dest-dir ~/Downloads/papers
paperdb add 2401.02058 --dest-dir ~/Downloads/papers
paperdb add https://example.org/paper.pdf --dest-dir ~/Downloads/papers

# Ingest (convert + extract equations + methods + summarize + tag)
paperdb ingest --paper Macklin_2016_XPBD
paperdb ingest --all
paperdb ingest --folder ~/Downloads/Milan_Articles\ Self-Assembly/

# Sync: scan watched folders and process new/changed papers
paperdb sync --folder ~/Downloads/Milan_Articles\ Self-Assembly/
```

### Search

```bash
# Basic search
paperdb search "XPBD position-based dynamics"

# With tag filters and year range
paperdb search "molecular dynamics" --tag solver:xpbd --tag domain:game_physics --year 2015-2025

# Exclude tags with ! prefix
paperdb search "Ewald summation" --tag !method:ML

# Show scoring breakdown
paperdb search "constraint compliance" --explain

# JSON output for scripting
paperdb search "GPU collision" --json --limit 50
```

### Context packs

```bash
# Assemble a context pack for an LLM agent
paperdb context "short-range interaction search on GPU" --budget 24000 --out context.md

# Include only specific content types
paperdb context "Ewald summation" --include equations,methods --out ewald_context.md

# Save to database for reproducibility
paperdb context "XPBD" --save
```

### Inspection

```bash
# Full metadata + tags + processing status
paperdb inspect Macklin_2016_XPBD

# Get paper content in various formats
paperdb get Macklin_2016_XPBD --markdown
paperdb get Macklin_2016_XPBD --json
paperdb get Macklin_2016_XPBD --bib
paperdb get Macklin_2016_XPBD --all

# List extracted equations
paperdb equations Macklin_2016_XPBD

# Show method card
paperdb method Macklin_2016_XPBD --name "XPBD"

# Find related papers
paperdb related Macklin_2016_XPBD --limit 10
```

### Tags

```bash
# List all tags
paperdb tags

# Filter by category
paperdb tags --category solver

# Merge duplicate tags
paperdb tags --merge "molecular dynamics" "MD"
```

### Topical overviews

```bash
# Generate a topical review comparing methods across papers
paperdb topic "molecular force fields" --out force_fields_review.md

# Compare methods along specific axes
paperdb compare "GPU collision methods" --axes complexity,parallelization,scalability
```

### Export

```bash
# Export entire library as BibTeX
paperdb export --bibtex --out library.bib
```

### Status

```bash
# Database statistics
paperdb status

# List papers missing specific fields
paperdb status --missing bibtex
paperdb status --needs-reprocessing
```

### Re-processing

```bash
# Re-run specific operations with updated LLM config
paperdb reindex --re-summarize --llm-config gemini-pro
paperdb reindex --re-tag --re-extract-equations
```

### Migration

```bash
# Import from a legacy database file or its containing run directory
paperdb migrate --from ~/git/AutoCrunchCoder/tests/paper_pipeline_out/consolidated.db
paperdb migrate --from ~/git/AutoCrunchCoder/tests/paper_pipeline_out/

# Import from Mendeley BibTeX
paperdb migrate --from-mendeley ~/Documents/mendeley.bib
```

---

## 6. Python API

```python
from paperdb import PaperDB

db = PaperDB()  # uses PAPERDB_DATA or ~/paperdb/

# Scan and index PDFs
results = db.scan_folder("~/Downloads/papers/")

# Local files are indexed in place; DOI can be metadata-only
paper_id = db.add_paper("10.1021/acs.jctc.4c00001")

# arXiv/direct URL, or a requested DOI PDF, needs an explicit destination
paper_id = db.add_paper("2401.02058", dest_dir="~/Downloads/papers")

# Ingest (convert + extract + summarize + tag)
result = db.ingest_paper(paper_id)

# Search
results = db.search("XPBD constraint compliance", explain=True)
for r in results:
    print(f"{r.paper.paper_key}: score={r.score} breakdown={r.breakdown}")

# Context pack
pack = db.retrieve_context("GPU collision detection", token_budget=16000)
print(pack.content)

# Access content
markdown = db.get_markdown(paper_id)
equations = db.get_equations(paper_id)
methods = db.get_methods(paper_id)
tags = db.get_tags(paper_id)
summary = db.get_summary(paper_id)

# Topical review
review = db.build_topic_review("molecular force fields", max_papers=20)
print(review['content'])

# Status
print(db.status())

db.close()
```

---

## 7. MCP Server — Resident Mode

The MCP (Model Context Protocol) server exposes PaperDB's scientific retrieval capabilities
to LLM coding agents. It is **read-only by default**.

### Starting the MCP server

```bash
# stdio mode — for IDE-integrated agents (Cursor, Claude Desktop, Windsurf)
paperdb mcp --transport stdio

# SSE mode — for remote/web agents (Devin, OpenCode)
paperdb mcp --transport sse --port 8000

# With mutations enabled (ingest, reprocess, merge tags)
paperdb mcp --transport stdio --allow-mutations
```

### Available MCP tools

**Discovery tools (read-only):**
- `search_papers(query, required_tags, preferred_tags, excluded_tags, year_range, limit)`
- `find_methods(problem, constraints, limit)`
- `find_equations(concept, variables, tags, limit)`
- `compare_methods(problem, comparison_axes, constraints, max_papers)`
- `build_topic_review(topic, focus, constraints, max_papers)`

**Inspection tools (read-only):**
- `get_paper(paper_id_or_key_or_doi)`
- `get_paper_markdown(paper_id)`
- `get_paper_methods(paper_id)`
- `get_paper_equations(paper_id)`
- `get_related_papers(paper_id, limit)`
- `explain_paper_match(paper_id, query)`

**Context pack tool (read-only):**
- `retrieve_context(query, token_budget, include, filters)`

**Taxonomy tools (read-only):**
- `list_tags(category)`
- `list_tag_aliases(tag_name)`

**Mutating tools (require `--allow-mutations`):**
- `ingest_pdf(path_or_url, tags, dest_dir)` — `dest_dir` is required for arXiv/direct URL acquisition
- `reprocess_document(paper_id, operations)`
- `merge_tags(canonical, alias)`

**Resources:**
- `paperdb://paper/{paper_key}` — paper metadata + summary
- `paperdb://paper/{paper_key}/markdown` — full markdown
- `paperdb://paper/{paper_key}/json` — structured JSON
- `paperdb://paper/{paper_key}/bib` — BibTeX
- `paperdb://tags` — all tags grouped by category
- `paperdb://context/{id}` — saved context pack

---

## 8. LLM Agent Integration

### Cursor

Add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "paperdb": {
      "command": "paperdb",
      "args": ["mcp", "--transport", "stdio"]
    }
  }
}
```

Cursor will automatically discover PaperDB tools. The agent can search papers, retrieve
context packs, inspect method cards, and find equations.

### Windsurf (Cascade)

Add to `.windsurf/mcp_config.json` in your project:
```json
{
  "mcpServers": {
    "paperdb": {
      "command": "paperdb",
      "args": ["mcp", "--transport", "stdio"]
    }
  }
}
```

### Claude Desktop

Add to `~/.config/claude-desktop/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "paperdb": {
      "command": "paperdb",
      "args": ["mcp", "--transport", "stdio"]
    }
  }
}
```

### Devin

Devin supports MCP over SSE. Start the server:
```bash
paperdb mcp --transport sse --port 8000
```

Then in Devin's settings, add an MCP server:
- **URL**: `http://localhost:8000`
- **Transport**: SSE

### Codex (OpenAI)

Codex can use MCP via stdio. Add to your Codex configuration:
```json
{
  "mcp_servers": {
    "paperdb": {
      "command": "paperdb",
      "args": ["mcp", "--transport", "stdio"]
    }
  }
}
```

### OpenCode

OpenCode supports MCP over SSE. Start the server:
```bash
paperdb mcp --transport sse --port 8000
```

Configure in OpenCode's MCP settings:
- **Endpoint**: `http://localhost:8000/sse`
- **Transport**: SSE

### Using PaperDB with any LLM agent

Even without MCP integration, you can use PaperDB via CLI in any agent:

```bash
# Search and pipe results to an agent
paperdb search "Ewald summation 2D periodicity" --json

# Generate a context pack file for an agent to read
paperdb context "short-range interaction search on GPU" --out /tmp/context.md

# Get equations for a specific paper
paperdb equations Macklin_2016_XPBD --json
```

---

## 9. Data Conversion — Legacy Migration

### What needs to be converted

The existing legacy data lives in:
```
~/git/AutoCrunchCoder/tests/paper_pipeline_out/
├── consolidated.db          # 895 papers, 1279 tags, 2556 article_tags
├── 20260223_192818/         # Processing runs with markdown/, summaries/, chunks/
├── 20260223_195058/         # Another run
├── 20260224_105840/         # Another run
└── 20260224_113308/         # Latest run (docling + formulas)
```

The `consolidated.db` has columns: `id, original_pdf_path, stem, doi, bibtex_ok, bibtex_path,
bibtex_error, bibtex_text, title, authors, year, journal, keywords, shadow_md_path,
shadow_pdf_path, rename_target_md, rename_target_pdf, md_path, timestamp, essence, run_name`.

### Running the migration

```bash
# 1. Activate environment
venvML

# 2. Run migration (non-destructive — copies to ~/paperdb/legacy/)
paperdb migrate --from ~/git/AutoCrunchCoder/tests/paper_pipeline_out/consolidated.db
```

Or via Python:
```python
from paperdb import PaperDB
db = PaperDB()
result = db.migrate_from_db("~/git/AutoCrunchCoder/tests/paper_pipeline_out/consolidated.db")
print(f"Migrated: {result['papers_migrated']}, Failed: {result['papers_failed']}")
print(f"Report: {result['report_path']}")
```

### What the migration does

1. **Copies** the legacy source tree to `~/paperdb/legacy/` (non-destructive); input may be a DB file or directory
2. **Reads** all 895 papers, 1279 tags, 2556 article_tags from legacy DB
3. **Generates** `paper_key` for each paper (`Author_Year_Keyword` format)
4. **Selects best markdown** by backend priority: `docling+formulas > docling > vlm > pdfminer`
5. **Imports existing summaries** as `processing_runs` with `operation='migrate_summary'`
6. **Consolidates tags** using clean_tags.py rules, builds `tag_aliases`
7. **Indexes PDF paths** — PDFs stay in their original location
8. **Generates** `.md` / `.json` / `.bib` bundles in `~/paperdb/papers/<year>/`
9. **Builds search units** from migrated markdown
10. **Produces migration report** at `~/paperdb/logs/migration_report.md`

### Post-migration: reprocessing

After migration, papers with low-quality backends (pdfminer) or missing summaries
should be re-processed:

```bash
# Check which papers need reprocessing
paperdb status --needs-reprocessing

# Re-process all papers needing it
paperdb reindex --re-summarize --re-tag --llm-config gemini-flash
```

### Migrating from Mendeley BibTeX

```bash
paperdb migrate --from-mendeley ~/Documents/mendeley_library.bib
```

This parses the BibTeX, matches PDFs by filename/DOI, and imports metadata + file paths.

---

## 10. Folder Management

### Where PDFs should be

PDFs **stay where they are**. PaperDB never moves, copies, or renames PDFs. The database
tracks absolute paths and SHA-256 hashes. If a PDF is moved, the next scan will detect it
by hash and update the path.

### Recommended folder structure

```
~/Downloads/papers/          # Your PDF collection (any structure)
├── self-assembly/
│   ├── paper1.pdf
│   └── paper2.pdf
├── force-fields/
│   └── ...
└── ...

~/paperdb/                   # PaperDB data (auto-created)
├── papers.db
├── papers/                  # Generated .md/.json/.bib bundles
├── legacy/                  # Migrated legacy data
└── logs/
```

### Moving PDFs

If you reorganize your PDF folders:
1. Just move the PDFs wherever you want.
2. Re-scan: `paperdb scan ~/Downloads/papers/ --recursive`
3. PaperDB will detect moved PDFs by SHA-256 hash and update the path in `paper_files`.

### Moving the PaperDB data directory

```bash
# Move the entire data directory
mv ~/paperdb /data/paperdb

# Set the environment variable
export PAPERDB_DATA=/data/paperdb

# Verify
paperdb status
```

### Using multiple databases

```bash
# Use a specific database file
paperdb --db-path /data/project_papers.db status

# Or via environment variable
export PAPERDB_DB=/data/project_papers.db
```

### Watching folders for new papers

PaperDB does not have a daemon mode yet. To keep your library up-to-date:

```bash
# Option 1: Cron job (every hour)
crontab -e
# Add: 0 * * * * cd ~/git/AutoCrunchCoder && venvML && paperdb sync --folder ~/Downloads/papers/

# Option 2: Manual sync after downloading new papers
paperdb scan ~/Downloads/papers/ --recursive
paperdb ingest --all
```

---

## 11. Verification State and Remaining Limitations

The integration-gap list in `docs/tasks/paperdb/task7_integration_gaps.md` is retained as the historical task specification. The current implementation now exposes the repository/facade contracts named there and has automated verification, but repository policy treats the corrections as **unconfirmed until the user reviews the test evidence**.

Current automated evidence:

- `python -m pytest tests/paperdb/ --tb=short`: 319 passed.
- `python -m compileall -q paperdb`: successful.
- `git diff --check`: clean.
- Regression coverage includes durable writes after reopening SQLite, active/superseded processing versions, atomic LLM-tag visibility, exact raw equation preservation, metadata-only and typed-tag retrieval, bounded ranking bonuses, structured equation/method indexing, saved context packs, independent reprocessing from changed Markdown, and idempotent file-or-directory legacy migration.

The following features remain outside this correction pass:

- GUI: `paperdb gui` still reports that no GUI is implemented.
- Vector search: optional enhancement; FTS5 remains the supported default.
- Citation extraction/graph population: the schema exists, but automated extraction/import is not implemented.
- Daemon/file watcher: use explicit `paperdb sync --folder ...` or scheduled invocation.
- Production validation with the full legacy corpus, Docling installation, and live LLM/CrossRef/arXiv services still requires the user's environment and credentials.

Recommended operational validation:

1. Run migration against a copy/source path and inspect `logs/migration_report.md`.
2. Scan an explicit PDF library folder; PaperDB indexes files in place.
3. Run ingestion on a small representative paper set before a full-library batch.
4. Inspect generated Markdown, structured JSON, BibTeX, equations, method evidence, and search/context results.
5. Confirm the behavior before changing any task/checklist status fields.

# Pipelines Tutorial: Papers (PDF) + Repositories (Code)

This repository contains two **staged, best-effort pipelines** designed for *scientific knowledge extraction* and *codebase understanding*.

Both pipelines follow the same core philosophy:

- **Non-blocking**: failures in one step do not stop the run; they are logged and reported.
- **Non-destructive**: the source inputs (PDFs / repo code) are not modified.
- **Reproducible outputs**: results are written into a dedicated output folder.
- **Didactic artifacts**: intermediate outputs (chunks/skeletons/graphs) are saved to help debugging and downstream tooling.

This document is a tutorial for **users** and a guide for **developers**.

## 1. Quickstart (recommended)

Activate the project environment:

```bash
source ~/venvs/ML/bin/activate
```

### 1.1 Paper pipeline (PDF -> Markdown -> Summary -> Graph)

Run on a small sample first:

```bash
python tests/test_paper_pipeline.py --limit 3 --backend auto --text-model phi-4
```

### 1.2 Repo mapper (repo -> skeletons/graphs/rollups in .shadow)

Structure-only (fast):

```bash
python tests/test_repo_mapper.py
```

With LM Studio summaries for a few files:

```bash
python tests/test_repo_mapper.py --use-llm --llm-backend lmstudio --max-llm-files 10 \
  --lmstudio-url http://10.26.201.142:1234/v1 --lmstudio-model liquid/lfm2.5-1.2b
```

## 2. Paper pipeline: PDF -> Markdown -> Summary -> Graph

### 2.1 Entry points

- **CLI runner**: `tests/test_paper_pipeline.py`  
  A lightweight wrapper (argparse) that constructs a config and calls the library.

- **Reusable library**: `pyCruncher/paper_pipeline.py`  
  Contains the full implementation.

### 2.2 What the paper pipeline does (high-level)

For each PDF:

1. **Discover PDFs** in a folder.
2. **Optional metadata** from BibTeX (Mendeley export).
3. **Convert PDF -> Markdown** using one backend:
   - `docling` (preferred)
   - LM Studio **vision** model (fallback)
   - `pdfminer` raw text (last resort)
4. **Chunk** the markdown into section-sized pieces.
5. **Extract equations** (regex over `$...$` and `$$...$$`).
6. **Summarize** the paper using a local text model (LM Studio).
7. **Extract graph concepts** from the structured summary.
8. **Emit reports** (`report.md`, `report.json`) and a simple graph TSV.

### 2.3 Output directory layout

Default output dir is:

- `tests/paper_pipeline_out/`

A typical run produces:

```
paper_pipeline_out/
├── markdown/              # full markdown per PDF (YAML header + content)
├── summaries/             # structured summaries per PDF
├── chunks/                # per-paper chunk files + equations.md
├── graph_edges.tsv        # paper -> concept edges
├── report.md              # run table + stats
└── report.json            # machine-readable run report
```

### 2.4 CLI reference

```bash
python tests/test_paper_pipeline.py --help
```

Important flags:

- `--pdf-dir <dir>`
- `--out-dir <dir>`
- `--limit N` (use `--limit 0` for all PDFs)
- `--backend docling|vlm|pdfminer|auto`
- `--vlm-model <model_id>`
- `--text-model <model_id>`
- `--embed-model <model_id>`
- `--lmstudio-url http://<host>:1234/v1`
- `--skip-summary`
- `--skip-embed`
- `--bibtex-path <file>`
- `--no-bibtex`

### 2.5 Backends and dependencies

#### A) Docling (preferred)

The pipeline calls the **Docling CLI**:

```bash
docling <pdf> --to md --output <out> --device auto --enrich-formula --image-export-mode placeholder
```

If `docling` is not installed or fails on a particular PDF, the pipeline continues and tries the next backend (if enabled).

#### B) LM Studio vision backend (fallback)

This backend calls the local OpenAI-compatible API:

- `GET  <lmstudio_url>/models`
- `POST <lmstudio_url>/chat/completions`

The implementation tries to use `pdf2image` (if installed) to send PNG pages; otherwise it tries to send the PDF as base64.

Notes:

- Vision inference is VRAM-heavy.
- If your GPU is already busy (e.g. `olmocr-2-7b` loaded), prefer Docling.

#### C) pdfminer (last resort)

`pdfminer.six` extracts raw text. This is usually worse for equations and layout, but can rescue OCR failures.

### 2.6 Summarization and context limits

Summarization is performed by LM Studio text model.

Key practical constraints:

- Some models may be loaded with small context (e.g. 4096 tokens).
- The pipeline truncates the markdown to a default max (`max_chars=8000` in `summarize_paper`) to avoid context overflow.

If you want better summaries:

- Load a model with larger context in LM Studio
- Or implement chunk-wise summarization (developer extension)

### 2.7 Knowledge graph output

The paper pipeline currently produces a minimal graph file:

- `graph_edges.tsv` with columns:
  - `paper`
  - `concept`

The `concept` strings are extracted from `## Keywords` and `## Connections` sections in the summary.

This TSV is intentionally simple so you can feed it into:

- Obsidian graph view (after conversion)
- `networkx`
- Gephi
- your own HTML/JS visualization

### 2.8 Postprocess existing run: shadow tree + DOI/BibTeX + rename plan + SQLite DB

If you already have a completed run folder (i.e. it contains `logs/processed.json` and `markdown/*.md`), you can postprocess it **without re-converting PDFs**.

#### What postprocess does

| Feature | Description | Output |
|---------|-------------|--------|
| **Shadow tree** | Copies existing `.md` files into a folder tree mirroring the original PDF directory structure | `shadow_tree/<relpath>.md` |
| **DOI/BibTeX enrichment** | Tries `pdf2doi` → CrossRef BibTeX fetch → DOI from markdown → CrossRef title search | `shadow_tree/<relpath>.bib` (if found) |
| **Rename plan** | Proposes new filenames based on BibTeX fields using template | `logs/rename_plan.tsv` |
| **SQLite DB** | Indexes all metadata + full-text search over markdown content | `papers.db` |

#### CLI flags

| Flag | Description |
|------|-------------|
| `--postprocess-only` | Enable postprocess mode (skip conversion) |
| `--run-dir` | Path to existing run folder (required) |
| `--pdf-root` | Original PDF root directory (required, for relative paths) |
| `--mirror-root` | Where to create shadow tree (default: `<run-dir>/shadow_tree`) |
| `--no-mirror` | Skip shadow tree creation |
| `--no-bibtex-pass` | Skip DOI/BibTeX enrichment |
| `--rename-plan` | Generate rename plan (requires BibTeX) |
| `--apply-rename` | Apply rename by copying into `<run-dir>/renamed/` (non-destructive) |
| `--rename-template` | Template for rename (default: `{first_author}_{journal}_{year}_{short_title}`) |
| `--db-path` | Custom SQLite DB path (default: `<run-dir>/papers.db`) |
| `--limit N` | Process only first N items (0=all) |

#### Example commands

Postprocess 3 items (test run):
```bash
python tests/test_paper_pipeline.py \
  --postprocess-only \
  --run-dir /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049 \
  --pdf-root /home/prokop/Desktop/PAPERs \
  --mirror-root /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049/shadow_tree \
  --rename-plan \
  --limit 3
```

Postprocess all items:
```bash
python tests/test_paper_pipeline.py \
  --postprocess-only \
  --run-dir /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049 \
  --pdf-root /home/prokop/Desktop/PAPERs \
  --rename-plan
```

#### Database guide

The SQLite database (`papers.db`) is your **local Zotero/Mendeley alternative** optimized for LLM access.

##### Opening the database

```bash
# Using litecli (recommended, nice UI)
litecli /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049/papers.db

# Using sqlite3 (basic)
sqlite3 /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049/papers.db

# Using Python
python -c "
import sqlite3
conn = sqlite3.connect('/home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049/papers.db')
cur = conn.cursor()
for row in cur.execute('SELECT stem, doi, bibtex_ok FROM papers LIMIT 5'):
    print(row)
"
```

##### Important tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `papers` | Main paper index | `original_pdf_path`, `stem`, `doi`, `bibtex_ok`, `bibtex_path`, `shadow_md_path`, `shadow_pdf_path`, `rename_target_md`, `rename_target_pdf`, `md_path`, `timestamp` |
| `processing_log` | Operation log | `stem`, `operation`, `status`, `message`, `timestamp` |
| `papers_fts` | Full-text search index | `stem`, `doi`, `title`, `authors`, `year`, `journal`, `md_text` |

##### Search examples

```sql
-- List all papers with DOI found
SELECT stem, doi, bibtex_ok FROM papers WHERE bibtex_ok = 1 LIMIT 10;

-- Find papers by year
SELECT stem, year FROM papers WHERE year = '2024' LIMIT 10;

-- Find papers by journal keyword
SELECT stem, journal FROM papers WHERE journal LIKE '%Physical Review%' LIMIT 10;

-- Full-text search in markdown content (FTS5)
SELECT stem, snippet(papers_fts, 3, '<<', '>>', '...', 32) AS context
FROM papers_fts
WHERE papers_fts MATCH 'density functional'
LIMIT 10;

-- Search by author
SELECT stem, authors FROM papers WHERE authors LIKE '%Smith%' LIMIT 10;

-- Get all paths for a paper
SELECT stem, original_pdf_path, md_path, shadow_md_path, bibtex_path
FROM papers WHERE stem = 'DFT_c_code';
```

##### Combining with processed.json

The database complements `logs/processed.json`:

| File | Use case |
|------|----------|
| `papers.db` | Fast SQL queries, full-text search, programmatic access |
| `logs/processed.json` | Full per-item details, human-readable, version control friendly |
| `logs/postprocess_summary.json` | Run statistics (counts, timing, paths) |

#### File responsibility summary

| File/Directory | Responsibility |
|----------------|----------------|
| `markdown/*.md` | Original conversion output (YAML header + content) |
| `shadow_tree/` | Mirrored markdown matching original PDF directory structure |
| `shadow_tree/*.bib` | BibTeX files fetched during postprocess |
| `papers.db` | SQLite index for fast queries + FTS |
| `logs/processed.json` | Per-item processing record (updated by postprocess) |
| `logs/processed.json.bak_*` | Automatic backups before postprocess modifications |
| `logs/postprocess_summary.json` | Postprocess run statistics |
| `logs/rename_plan.tsv` | Proposed renames (if `--rename-plan` used) |
| `renamed/` | Copies with new names (if `--apply-rename` used) |

#### Safety notes

- `logs/processed.json` is always backed up before modification
- `--apply-rename` never modifies originals; it copies to `renamed/`
- Rename collisions cause loud failure (no silent overwrites)
- Network timeouts on CrossRef requests (10s default)

## 3. Repo mapper: repo -> skeletons/graphs/rollups in a shadow directory

### 3.1 Entry points

- **Library module**: `pyCruncher/repo_mapper.py`
- **CLI test driver**: `tests/test_repo_mapper.py`
- **Tutorial (existing)**: `docs/repo_mapper_tutorial.md`

This section is a condensed tutorial; for deeper details see `docs/repo_mapper_tutorial.md`.

### 3.2 Non-destructive shadow output

Repo mapper never edits the repo.

All outputs go to:

- `.shadow/<timestamp>/...`

This is important for:

- repeatable runs
- comparing outputs across changes
- keeping artifacts out of git (you should ignore `.shadow/`)

### 3.3 What the repo mapper does (high-level)

1. **Discover files** (extension filters + ignore patterns)
2. **Extract structure**
   - Python: stdlib `ast`
   - C/C++: `ctags` (JSON output)
3. **Generate skeletons** per file
4. **Collect git metadata** per file (commit counts, dates)
5. **Optional LLM summarization** of a small subset
   - LM Studio (local)
   - DeepSeek (remote)
6. **Generate rollups**
   - folder stats
   - concept map
   - tech matrix
7. **Export graphs**
   - Python import edges TSV
   - symbols JSON
8. **Write a report** (md + json)

### 3.4 Output layout

Typical output:

```
.shadow/<run_id>/
├── ctags_output.json
├── report.md
├── report.json
├── skeletons/
├── summaries/
├── rollups/
└── graphs/
```

### 3.5 LLM usage under resource constraints

To keep VRAM/RAM usage low:

- Use a small text model (e.g. `liquid/lfm2.5-1.2b`)
- Limit summarization with `--max-llm-files`

## 4. Troubleshooting

### 4.1 LM Studio connectivity

Check models:

```bash
curl -s http://localhost:1234/v1/models | head
```

Common pitfalls:

- Wrong URL (must include `/v1`)
- Model listed but not loadable (LM Studio returns 404/400)

### 4.2 Docling issues

Symptoms:

- `Docling CLI not found`
- `Docling produced no .md files`
- timeouts on large PDFs

Mitigations:

- run with smaller `--limit`
- use `--backend vlm` fallback

### 4.3 ctags issues (repo mapper)

If `ctags` isn’t installed or on PATH, repo mapper will skip that stage and continue.

## 5. Developer notes (how it works, how to extend)

### 5.1 Paper pipeline internals (`pyCruncher/paper_pipeline.py`)

Core objects:

- `PaperPipelineConfig`: explicit inputs/flags controlling the run
- `PaperResult`: per-PDF outputs and stage statuses

Core functions:

- Conversion backends: `convert_docling`, `convert_vlm`, `convert_pdfminer`
- Chunking: `chunk_markdown`
- Equations: `extract_equations`
- Summaries: `summarize_paper`
- Embeddings: `embed_text`
- Graph concepts: `extract_graph_concepts`
- Reporting: `generate_report`
- Orchestration: `run_paper_pipeline`

Extension ideas that fit the current design:

- Chunk-wise summarization and merge
- Citation graph extraction from BibTeX (DOI -> crosslinks)
- Better equation parsing (label/number extraction)
- Optional persistent vector index (only if you want RAG)

### 5.2 Repo mapper internals (`pyCruncher/repo_mapper.py`)

See `docs/repo_mapper_tutorial.md` for the full explanation.

Extension ideas:

- integrate `dependency_graph_tree_sitter.py` for deeper call graphs
- C/C++ include graph (`#include`) as file->file edges
- embeddings-based duplicate detection using LM Studio embeddings

## 6. Recommended workflows

### Paper pipeline

- Start with `--backend docling --skip-summary` to validate conversion quality.
- Postprocess an existing run to add DOI/BibTeX, DB, rename plan, and summaries:

  ```bash
  # Activate your ML venv first
  source ~/venvs/ML/bin/activate
  cd /home/prokop/git/AutoCrunchCoder/tests

  python test_paper_pipeline.py \
    --postprocess-only \
    --run-dir /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049 \
    --pdf-root /home/prokop/Desktop/PAPERs \
    --crossref-only \
    --summarize-md \
    --lmstudio-url http://10.26.201.142:1234/v1 \
    --text-model phi-4 \
    --rename-plan \
    --limit 0
  ```

  What it does:
  - Generates/updates BibTeX per item (`shadow_tree/.../*.bib`) using DOI→CrossRef (CrossRef-only skips pdf2doi search).
  - Streams progress safely: `logs/processed_live.json`, `processed_live.tsv`, `bibtex_live.json`; keeps `processed.json` with backups.
  - Populates SQLite `papers.db` with DOI/BibTeX fields, titles/authors/year/journal/keywords, paths, and summary status.
  - Writes summaries from existing markdown into `summaries/<stem>.md` and mirrors them into `shadow_tree/.../<stem>.summary.md`.
  - Builds `logs/rename_plan.tsv` (non-destructive suggestions); use `--apply-rename` to copy into `renamed/`.

- Add embeddings only if you plan to cluster/search (flag `--skip-embed` in main pipeline controls that stage).

### Knowledge graph + Vault + MCP

- Build the knowledge graph (LLM-extracted domains/math/solvers/data-structures) and Markdown vault for an existing run:

  ```bash
  # Activate your ML venv first
  source ~/venvs/ML/bin/activate
  cd /home/prokop/git/AutoCrunchCoder/tests

  python test_paper_pipeline.py \
    --run-dir /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049 \
    --build-kg \
    --build-vault
  ```

  What it does:
  - Parses existing summaries, uses `instructor` + `pydantic` on your local LLM (`--lmstudio-url`, `--text-model`) to extract: domains, math_classes, solvers, data_structures.
  - Stores them in SQLite `papers.db` via tables `tags` and `article_tags`; updates `papers.essence` with a short 1–2 sentence summary.
  - Generates a human-readable Markdown vault under `<run_dir>/vault/` with `Master_Index.md` and per-topic `Topic_<tag>.md` pages linking to summary/PDF/BibTeX.

- Review results (human mode):
  - Open the DB: `tests/paper_pipeline_out/20260218_191049/papers.db` in DB Browser for SQLite (`sqlitebrowser`).
  - Open the vault: `tests/paper_pipeline_out/20260218_191049/vault/`. Start with `Master_Index.md`; individual topic pages list essence + links (best viewed in Obsidian/VS Code).

- Use with coding agents via MCP (deterministic SQL, no vector-RAG):

  ```bash
  source ~/venvs/ML/bin/activate
  cd /home/prokop/git/AutoCrunchCoder/tests

  # Point the MCP server at your run's DB
  mcp run mcp_research_server.py /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049/papers.db
  ```

  In Cursor/Claude Desktop: Settings → Features → MCP → Add New →
  - Type: command
  - Name: `ResearchDB`
  - Command: `/home/prokop/venvs/ML/bin/python /home/prokop/git/AutoCrunchCoder/tests/mcp_research_server.py /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/20260218_191049/papers.db`

  Available tools (from `tests/mcp_research_server.py`):
  - `search_by_math_solver(solver_name)`
  - `search_by_topic(topic_name)`
  - `get_equations(summary_path)`
  - `get_algorithms(summary_path)`

  Example chat prompt to Cursor: “Find papers using Conjugate Gradient via `search_by_math_solver`, then call `get_algorithms` on the best match and write CUDA code.”

### Repo mapper

- Run structure-only first
- Then enable LLM summaries for a small subset
- Only later add expensive stages (tree-sitter) when needed

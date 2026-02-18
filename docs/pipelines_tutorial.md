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

- Start with `--backend docling --skip-summary` to validate conversion quality
- Then enable summarization (`--text-model phi-4` or another loaded model)
- Add embeddings only if you plan to cluster/search

### Repo mapper

- Run structure-only first
- Then enable LLM summaries for a small subset
- Only later add expensive stages (tree-sitter) when needed

# Repo Mapper: Repository Analysis in a Shadow Directory

This document explains how to use the consolidated repository analysis pipeline implemented in:

- `pyCruncher/repo_mapper.py` (library module)
- `tests/test_repo_mapper.py` (CLI test driver / reference runner)

The design goal is **non-destructive analysis**:

- The source repository is never modified.
- All generated artifacts go into a separate **shadow** directory: `.shadow/<timestamp>/...`

This makes it safe to iterate, compare runs, and keep analysis outputs out of your working tree.

## What it does (high-level)

`repo_mapper` runs a staged pipeline that can:

- Discover source files in a repo (with extension filters + ignore patterns)
- Extract structure
  - Python: `ast` (stdlib)
  - C/C++: `ctags` JSON (universal-ctags)
- Generate per-file **skeletons** (symbol-centric summaries)
- Collect per-file **git metadata** (last touched date, creation date, commit count)
- Optionally run **LLM summarization**
  - LM Studio (OpenAI-compatible local API)
  - DeepSeek API (remote fallback)
- Generate rollups
  - Folder statistics
  - Concept map
  - Tech matrix (CSV)
- Export simple graph artifacts
  - Python import edges (TSV)
  - Symbols (JSON)
- Produce a final report (Markdown + JSON)

## Outputs (shadow directory layout)

A typical run produces:

```
.shadow/<run_id>/
├── ctags_output.json              # raw ctags JSON (if enabled)
├── report.md                      # human-readable run report
├── report.json                    # machine-readable report (lightweight)
├── test_results.md                # only produced by tests/test_repo_mapper.py
├── skeletons/                     # per-file skeletons (mirrors repo layout)
│   └── <relpath>.skeleton.md
├── summaries/                     # per-file LLM summaries (subset, mirrors repo layout)
│   └── <relpath>.summary.md
├── rollups/
│   ├── tech_matrix.csv            # folder × language file counts
│   └── concept_map.md             # folder grouped listing (status + git info)
└── graphs/
    ├── import_edges.tsv           # Python import edges: from_file → to_module
    └── symbols.json               # full symbol dump (ctags + python ast)
```

Notes:

- `skeletons/` is usually generated for **all** discovered files.
- `summaries/` is typically generated for a **limited number** of files (`--max-llm-files`).

## Quickstart (recommended)

Activate your existing ML environment:

```bash
source ~/venvs/ML/bin/activate
```

### 1) Run structure-only analysis (fast, no LLM)

```bash
python tests/test_repo_mapper.py
```

This runs:

- discovery
- Python AST sampling tests
- ctags test
- skeleton generation test
- git metadata test
- rollup test
- full pipeline run (no LLM)

### 2) Run full pipeline with LM Studio summaries

If LM Studio is running with an OpenAI-compatible endpoint:

- Localhost example: `http://localhost:1234/v1`
- LAN example (your setup): `http://10.26.201.142:1234/v1`

Run:

```bash
python tests/test_repo_mapper.py --use-llm --llm-backend lmstudio --max-llm-files 10 \
  --lmstudio-url http://10.26.201.142:1234/v1 --lmstudio-model liquid/lfm2.5-1.2b
```

### 3) Run full pipeline with DeepSeek fallback

DeepSeek key is expected in `tests/deepseek.key`.

```bash
python tests/test_repo_mapper.py --use-llm --llm-backend deepseek --max-llm-files 5
```

## Understanding the reports

### `report.md`

Contains:

- Summary statistics (files, symbols, summaries, errors)
- A per-file table:
  - language, line count
  - symbol counts
  - whether LLM summary was generated
  - git last touched + commit count
  - parsing/summarization errors (if any)
- Folder statistics section

### `report.json`

Designed to be small and easy to post-process.

It includes:

- counts and folder stats
- per-file simplified data (language, lines, symbols, top classes/functions, status)

### `graphs/import_edges.tsv`

This is a simple, useful artifact even without deep type analysis:

- `from_file` is a Python file path
- `to_module` is the imported module name (best-effort from AST)

You can use this to:

- build folder-level dependency summaries
- feed graph tools (`networkx`, Gephi, custom web viz)

## CLI reference (tests/test_repo_mapper.py)

The CLI is meant as both:

- a test harness
- an example of how to drive `repo_mapper` safely

Key options:

- `--repo-root <path>`
- `--shadow-dir <path>`
- `--max-files <N>`
- `--use-llm`
- `--llm-backend lmstudio|deepseek|none`
- `--lmstudio-url <url>`
- `--lmstudio-model <model>`
- `--max-llm-files <N>`
- `--skip-stages ...` (fine-grained stage skipping)
- `--only-full` (just run the end-to-end pipeline)

Examples:

```bash
# Analyze only a small subset (fast iteration)
python tests/test_repo_mapper.py --max-files 30

# Only run the full pipeline
python tests/test_repo_mapper.py --only-full

# Full pipeline + LLM summaries for 3 files
python tests/test_repo_mapper.py --use-llm --only-full --max-llm-files 3 \
  --lmstudio-url http://10.26.201.142:1234/v1 --lmstudio-model liquid/lfm2.5-1.2b
```

## Resource constraints / performance notes

This repo was tested under constrained resources:

- GPU memory may already be heavily used (e.g. by `olmocr-2-7b` for PDF processing)

Recommended tactics:

- Keep `--max-llm-files` small.
- Prefer small local text models for repo summarization (e.g. `liquid/lfm2.5-1.2b`).
- Use `--max-files` to bound discovery if you are iterating quickly.

The pipeline is designed to be **best-effort**:

- if LLM is unavailable, it still generates skeletons + rollups + reports
- failures are captured as per-file errors and the run continues

## How it works (developer view)

### Main orchestrator

`run_repo_mapper(...)` in `pyCruncher/repo_mapper.py` performs:

1. File discovery (`discover_files`)
2. Python AST analysis (`analyze_python_file`)
3. ctags run + parse (`run_ctags_json`, `parse_ctags_json`)
4. Skeleton generation (`generate_skeleton`)
5. Git metadata (`git_file_stats`)
6. Optional LLM summarization
   - LM Studio via `openai` client (`summarize_file_llm`)
   - DeepSeek via `requests` (`summarize_file_deepseek`)
7. Rollups
   - folder stats (`compute_folder_stats`)
   - tech matrix (`generate_tech_matrix`, `tech_matrix_to_csv`)
   - concept map (`generate_concept_map`)
   - import edges (`build_import_edges`)
8. Emit outputs (md/json/tsv)

### Data model

Key dataclasses:

- `SymbolInfo` (one symbol)
- `FileAnalysis` (per-file computed fields)
- `RepoAnalysis` (whole-run container)

These are intentionally simple so they can be:

- serialized to JSON
- extended later with richer analyzers (tree-sitter, type inference)

## Integration points (future extensions)

This repository already contains more advanced analyzers that are not yet wired into `repo_mapper`:

- `pyCruncher/dependency_graph_tree_sitter.py` (tree-sitter structure)
- `pyCruncher/python_type_analyzer.py` and `pyCruncher/cpp_type_analyzer.py`

Next steps that fit naturally into this pipeline:

- **C/C++ include graph**: parse `#include` lines into file→file edges
- **Function call graph**:
  - Python: `ast.Call` extraction + name resolution heuristics
  - C++: tree-sitter-based call expression collection
- **Folder-level rollup summaries**: concatenate file summaries, then ask LLM for module-level summaries
- **Embeddings**: use LM Studio `/v1/embeddings` to embed summaries and cluster similar modules
- **Visualization**: render graphs into HTML (e.g. d3) or export to GraphML

## Relationship to the paper pipeline

For paper processing (PDF→Markdown→summaries→knowledge graph), see:

- `tests/test_paper_pipeline.py`

The repo mapper and paper pipeline share the same philosophy:

- staged processing
- robust skip-on-failure
- outputs captured into a dedicated output directory
- an explicit final report that tells you what worked and what didn’t

## Troubleshooting

### `ctags` failures

Symptoms:

- report contains global error: `ctags failed or not installed`

Fix:

- install universal-ctags and ensure `ctags` is on `PATH`

### LM Studio connection failures

Symptoms:

- report includes `LM Studio connection failed: ...`
- summaries are skipped / recorded as errors

Fix:

- verify server is running:
  - `GET http://<host>:1234/v1/models`
- use the correct URL (note the `/v1` suffix)

### DeepSeek failures

Symptoms:

- HTTP error status or timeout

Fix:

- confirm `tests/deepseek.key` exists and is valid

## Recommended workflow

- **First pass**: run without LLM, generate skeletons + graphs + rollups.
- **Second pass**: run LLM summarization on a small curated subset.
- **Third pass**: add folder-level rollups and embedding clustering.

This avoids wasting compute on large summarization runs before structure is correct.

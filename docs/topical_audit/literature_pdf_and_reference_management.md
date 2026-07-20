# 1. Literature, PDF & Reference Management

## What this topic does

Turn a collection of scientific PDFs into a structured, queryable, LLM-ready knowledge base. The pipeline is deliberately offline-first: it can use local Docling, local LM-Studio vision models, and local embeddings, with optional cloud fallbacks for metadata (CrossRef DOI/BibTeX).

## Main challenges and how they are solved

- **PDFs with equations and complex layouts**: the pipeline tries `docling` first, then a local VLM (`olmocr-2-7b`/`phi-4` via LM Studio), and finally `pdfminer` as a fallback. Each backend is wrapped in a fail-soft function so one broken PDF does not kill the batch.
- **Equations and metadata extraction**: LaTeX display/inline math is captured with regex, DOIs are mined from text and `pdf2doi`, and missing metadata is filled from CrossRef or a user-supplied BibTeX export.
- **Too much content for the LLM context window**: markdown is split by heading level (`chunk_markdown`), summaries are produced per-chunk, and only the structured essence is stored in SQLite.
- **Connecting papers to code**: a knowledge-graph stage tags each article with scientific domains, math classes, solvers, and data structures (`knowledge_graph.py`).

## Core files and their essence

### `pyCruncher/paper_pipeline.py`

The main reusable pipeline. Its work is tracked by the `PaperResult` dataclass.

- `discover_pdfs()` / `discover_pdfs_recursive()` — find PDFs in a folder, optionally limited.
- `convert_docling()` / `convert_vlm()` / `convert_pdfminer()` — three PDF→markdown backends, each returns `(md_text, error_or_None)`.
- `chunk_markdown()` — split markdown by `#`, `##`, `###` headings; keeps equations intact.
- `extract_equations()` — collect `$$...$$` and `$...$` math.
- `summarize_paper()` — ask the configured text model to produce a structured summary (title, keywords, essence, key results, equations, algorithms, methods, connections).
- `embed_text()` — generate an embedding vector using a local nomic embedding model via the OpenAI-compatible endpoint.
- `postprocess_existing_run()` — re-scan a finished run, resolve DOIs/BibTeX, propose file renames, and build `papers.db`.
- `_db_init()`, `_db_upsert_paper()`, `_db_log()` — SQLite schema and FTS index for title, authors, year, journal, and markdown text.

### `pyCruncher/bib_utils.py`

Helper for turning BibTeX/Mendeley exports into usable metadata.

- `load_bib()` — load a `.bib` file and iterate entries, printing title/abstract; supports `nmax` limits.
- `decode_latex()` — convert LaTeX-encoded strings to Unicode and strip braces.
- `extract_ngrams()` — use `sklearn CountVectorizer` to find common word n-grams in a corpus.
- `convert_custom_path()` — strip Mendeley `:` and `:pdf` path decorators.

### `pyCruncher/knowledge_graph.py`

Builds a typed knowledge graph on top of the SQLite database.

- `ArticleMetadata` (pydantic) — structured schema for essence, domains, math classes, solvers, data structures.
- `init_kg_db()` — creates `tags` and `article_tags` tables and adds an `essence` column to `papers`.
- `build_knowledge_graph()` — reads `report.json`, sends summaries to the model, and inserts categorized tags per paper.

### Tests and examples

- `tests/test_paper_pipeline.py` — CLI runner with `--limit`, `--backend`, `--skip-summary`, `--postprocess`, etc.
- `examples/knowledge/pdf_extraction.py`, `pdf_summarization.py`, `bibtex_classification.py`, `ingest_chroma.py` — focused worked examples.
- `tests/RAG_retrival_*.py`, `examples/knowledge/rag_*.py` — RAG retrieval experiments over the generated markdown/Chroma index.

### Documentation and data

- `docs/pipelines_tutorial.md` — end-to-end tutorial covering PDF and repo pipelines.
- `docs/tools_for_pdf_science_articles.md`, `docs/PDF_an_article_tools_discusion.md` — PDF tool surveys and discussions.
- `docs/setup_Database_SQL.md` — SQLite setup and query examples.
- `prompts/sumarize_article_pdf.md` — prompt template for article summarization.
- `eFF_Su_2009.pdf` — sample PDF for testing.
- `tests/paper_pipeline_out/` — generated run directories (output, not source).

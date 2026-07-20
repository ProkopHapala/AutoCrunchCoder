# AutoCrunchCoder — Repository Topical Audit

This audit divides the repository into four work-streams. Each work-stream has its own sub-document in this folder, and every source-code folder has its own `README.md`. The goal is to separate concerns, make the codebase searchable, and keep the three main themes (papers/LLMs/code) connected to the scientific/HPC tooling that actually executes the generated code.

## The four work-streams

1. **[Literature, PDF & reference management](01_literature_pdf_and_reference_management.md)** — Ingest scientific PDFs, normalize Mendeley/Zotero/BibTeX metadata, build a local SQLite + full-text-search paper database, and prepare structured summaries/RAG indexes for LLM consumption.
2. **[Local LLMs & API integration](02_local_llms_and_api_integration.md)** — A multi-provider agent layer (OpenAI, Google, DeepSeek, Anthropic, LM Studio, Ollama, Groq, OpenRouter) with tool-use, streaming, FIM, JSON mode, and MCP/VS Code integration.
3. **[Codebase processing & review](03_codebase_processing_and_review.md)** — Static analysis of Python and C++ (AST, ctags, tree-sitter), repository skeleton/rollup generation, dependency graphs, and automated code documentation.
4. **[Scientific computation, math & visualization](04_scientific_computation_math_and_visualization.md)** — Symbolic math with Maxima, C++/OpenCL/CUDA force-field and vector kernels, and a web-based 3D molecule renderer.

## Source-code folder READMEs

Every source folder (excluding output/temporary directories) now has a `README.md` describing what the folder contains and how it links to the topics above. The top-level `README.md` remains the project elevator pitch.

## Layout conventions

- `pyCruncher/` — core Python library (agents, analyzers, paper pipeline).
- `pyCruncher2/` — reorganized scientific-computing module.
- `cpp/` — performance-critical C++/header kernels.
- `molecule_renderer/` — standalone web viewer.
- `prokop-bot/` — VS Code extension.
- `tests/` — experimental test drivers and examples.
- `examples/` — curated topic-specific examples.
- `prompts/` — LLM prompt templates.
- `Maxima/` — symbolic math scripts.
- `config/LLMs.toml` — provider/model registry.

## Excluded folders

`tests/paper_pipeline_out/`, `tests/temp/`, `tests/__pycache__/`, `.shadow/`, `prokop-bot/out/`, and `prokop-bot/node_modules/` are output/temporary and were intentionally left without READMEs.

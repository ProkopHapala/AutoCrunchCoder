# FeatureChecklist — AutoCrunchCoder

Status legend: **[x]** implemented & tested · **[~]** partially implemented / WIP · **[ ]** planned / not started

## 1. Literature, PDF & Reference Management
*Topic audit: [01_literature_pdf_and_reference_management.md](docs/topical_audit/01_literature_pdf_and_reference_management.md)*

- [x] PDF discovery (`discover_pdfs`, `discover_pdfs_recursive`)
- [x] PDF→markdown via docling backend
- [x] PDF→markdown via local VLM (olmocr / phi-4 via LM Studio)
- [x] PDF→markdown via pdfminer fallback
- [x] Equation extraction (`$$...$$` and `$...$`)
- [x] DOI mining from text + `pdf2doi`
- [x] CrossRef metadata lookup
- [x] BibTeX/Mendeley metadata import (`bib_utils.py`)
- [x] Markdown chunking by heading level
- [x] LLM paper summarization (structured output)
- [x] Local embedding generation (nomic via OpenAI-compatible endpoint)
- [x] SQLite database with FTS index (`papers.db`)
- [x] Knowledge graph tagging (`knowledge_graph.py`)
- [x] ChromaDB RAG ingestion (`examples/knowledge/ingest_chroma.py`)
- [x] RAG retrieval experiments (DeepSeek, Gemini)
- [ ] Batch postprocessing CLI polish (rename proposals, dedup)

## 2. Local LLMs & API Integration
*Topic audit: [02_local_llms_and_api_integration.md](docs/topical_audit/02_local_llms_and_api_integration.md)*

- [x] Abstract `Agent` base class with common interface
- [x] OpenAI provider (`AgentOpenAI.py`)
- [x] DeepSeek provider with FIM + JSON mode (`AgentDeepSeek.py`)
- [x] Google Gemini provider (`AgentGoogle.py`)
- [x] Anthropic Claude provider (`AgentAnthropic.py`) — basic, no tool calling yet
- [x] Groq support (via `AgentOpenAI` with custom base_url)
- [x] OpenRouter support (via `AgentOpenAI`)
- [x] LM Studio local inference (via `AgentOpenAI`)
- [x] Ollama local inference (via `AgentOpenAI`)
- [x] HuggingFace client (`tests/huggingface_client.py`)
- [x] Tool-use framework (`ToolScheme.schema()` from Python functions)
- [x] Streaming completions
- [x] Conversation history management
- [x] Provider/model registry (`config/LLMs.toml`)
- [x] API key resolution (env var → `providers.key` file)
- [x] MCP servers (chemistry, LAMMPS HTTP/stdio, Maxima)
- [x] MCP clients (chemistry, LAMMPS)
- [x] VS Code extension (`prokop-bot/`)
- [~] Anthropic tool calling — interface present, not fully wired
- [ ] Unified provider test suite (currently scattered one-off tests)

## 3. Codebase Processing & Review
*Topic audit: [03_codebase_processing_and_review.md](docs/topical_audit/03_codebase_processing_and_review.md)*

- [x] File discovery with ignore globs (`repo_mapper.py`)
- [x] Python AST analysis (classes, methods, functions, imports)
- [x] Universal-ctags integration (JSON output)
- [x] C++ tree-sitter analysis (scopes, classes, methods, calls)
- [x] Python tree-sitter analysis (types, scopes, calls)
- [x] Dependency graph from tree-sitter (`dependency_graph_tree_sitter.py`)
- [x] Dependency graph from ctags (`ctags_dependency.py`)
- [x] File skeleton generation
- [x] LLM file summarization (DeepSeek, generic)
- [x] Folder stats / tech matrix / concept map roll-ups
- [x] Import edge building
- [x] Non-destructive `.shadow/` output tree
- [x] Doxygen-style documentation generation (`CodeDocumenter.py`)
- [x] Markdown documentation generation (`CodeDocumenter_md.py`)
- [x] Git history → markdown (`git_utils.py`)
- [x] Knowledge vault generation (`vault_generator.py`)
- [~] C++ analysis completeness — some edge cases in templates/namespaces
- [~] Python analysis completeness — import resolution for relative imports
- [ ] Automated PR review pipeline
- [ ] Incremental analysis (only changed files)

## 4. Scientific Computation, Math & Visualization
*Topic audit: [04_scientific_computation_math_and_visualization.md](docs/topical_audit/04_scientific_computation_math_and_visualization.md)*

- [x] Maxima CAS wrapper (`run_maxima()`, `get_derivs()`)
- [x] Maxima script runner with timeout
- [x] Symbolic derivative computation
- [x] Definite integral computation
- [x] Numerical vs analytical derivative checking
- [x] Expression step evaluation
- [x] Force-field code generation prompts (`prompts/ImplementPotential/`)
- [x] Formula verification via Maxima (`check_formulas()`)
- [x] FLOP counting (`count_operations()`)
- [x] C++ Vec3/Vec4/Vec2 header-only vector classes
- [x] C++ force-field evaluators (Coulomb, LJ, LJQ)
- [x] Force-field parameter derivatives (variational)
- [x] OpenCL base class with device selection (`OpenCLBase.py`)
- [x] OpenCL kernel loading and compilation
- [x] OpenCL numeric integration examples
- [x] CUDA N-body example
- [x] OpenCL N-body example
- [x] Biot-Savart GPU integration
- [x] Non-bonded GPU scan
- [x] Periodic table / element data (`elements.py`)
- [x] Shared plotting helpers (`plotUtils.py`)
- [x] 3D molecule renderer (Three.js: atoms, bonds, selection)
- [x] Maxima reusable function scripts (`Maxima/my_functions.mac`)
- [~] `pyCruncher2` reorganization — partially migrated from `pyCruncher`
- [ ] Automated force-field fitting pipeline
- [ ] GPU multi-device support
- [ ] Molecule renderer: trajectory animation

## Cross-Cutting

- [x] Topical audit documentation (`docs/topical_audit/`)
- [x] Per-folder README.md index
- [x] CODEMAP.md repo navigation
- [x] FeatureChecklist.md (this file)
- [x] AGENTS.md agent guidelines
- [ ] CI/CD pipeline
- [ ] Automated regression test suite (`pytest -m "not slow"`)
- [ ] Package distribution (PyPI / pip install)

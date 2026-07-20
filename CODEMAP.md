# CODEMAP — AutoCrunchCoder Repository Structure

Quick-navigation map of the repository. Each entry links to the folder's own `README.md` where available. For per-topic deep dives see `docs/topical_audit/`.

## Top-level layout

```
AutoCrunchCoder/
├── paperdb/             # Scientific paper knowledge base — SQLite+FTS5, PDF ingestion, extraction, search, CLI, MCP
├── pyCruncher/          # Core Python library — agents, analyzers, paper pipeline
├── pyCruncher2/         # Reorganized scientific-computing module (CAS, GPU, elements)
├── cpp/                 # Header-only C++ kernels (Vec3, Vec4, ForceFields)
├── molecule_renderer/   # Web-based 3D molecule viewer (Three.js)
├── prokop-bot/          # VS Code extension for IDE integration
├── tests/               # Experimental test drivers and examples
├── examples/            # Curated topic-specific examples
├── prompts/             # LLM prompt templates
├── Maxima/              # Maxima CAS scripts
├── config/              # Provider/model registry (LLMs.toml)
├── doc/                 # Reference docs, tutorials, provider notes
├── docs/                # Design docs, topical audits, status reports
├── scripts/             # Utility scripts
├── vscode/              # Packaged VS Code extension (.vsix)
├── AGENTS.md            # Agent guidelines for this repo
├── CODEMAP.md           # This file
├── FeatureChecklist.md  # Feature status tracker
└── README.md            # Project elevator pitch
```

## paperdb/ — Scientific Paper Knowledge Base

**Central module of the repo.** Structured paper database with SQLite + FTS5 full-text search.Indexes PDFs (SHA-256 dedup, DOI/arXiv metadata lookup), extracts equations (LaTeX with source coordinates), method cards (source_algorithm + reconstructed_method via LLM), summaries, and taxonomy tags with aliases. Provides explainable search ranking, context-pack assembly for LLM agents, topical review generation, Typer CLI, and MCP server.

See **[SKILL.md](paperdb/SKILL.md)** for CLI usage guide for coding agents.

### Architecture

`PaperDB` facade (`__init__.py`) delegates to submodules. `Repository` (`db/repository.py`) is the single SQL access layer. All methods accept Pydantic model objects or keyword arguments.

```
paperdb/
├── __init__.py          # PaperDB facade — public API, delegates to submodules
├── cli.py               # Typer CLI — thin wrapper over PaperDB API
├── mcp.py               # MCP server (FastMCP) — read-only by default, mutations opt-in
├── config.py            # LLM config loading via pyCruncher.Agent + config/LLMs.toml
├── paths.py             # Data directory resolution (PAPERDB_DATA env, default ~/paperdb/)
├── SKILL.md             # CLI usage guide for coding agents
├── db/
│   ├── schema.sql       # Canonical SQLite schema — papers, paper_files, processing_runs, search_units, tags, equations, methods, summaries, topics, context_packs
│   ├── models.py        # Pydantic models for all entities (Paper, PaperFile, Tag, Equation, Method, Summary, etc.)
│   ├── repository.py    # Repository — ALL SQL lives here. CRUD for every table. Accepts Pydantic objects or kwargs.
│   └── connection.py    # Singleton SQLite connection (WAL, foreign_keys ON), init_schema(), db_transaction()
├── identity/
│   ├── hashing.py       # SHA-256 computation with lazy size+mtime cache
│   ├── matching.py      # Paper identity: hash/DOI/metadata matching, paper key generation, find_or_create
│   └── metadata.py      # DOI normalization, BibTeX parsing, CrossRef/arXiv metadata lookup
├── ingest/
│   ├── scanner.py       # Scan folders for PDFs, index by hash, Mendeley BibTeX import
│   ├── fetch.py         # Add papers from DOI/arXiv/URL — fetch metadata, download PDF
│   ├── pipeline.py      # Full ingest pipeline: convert→extract equations→extract methods→summarize→tag→build search units
│   ├── jobs.py          # Incremental job execution with processing_runs (skip-if-equivalent logic)
│   └── migration.py     # Legacy DB migration — import old SQLite data into new schema
├── extract/
│   ├── base.py          # Abstract BaseParser interface + ExtractionResult dataclass
│   ├── docling_backend.py # Docling CLI backend — PDF→Markdown+JSON, equation extraction from structured output
│   ├── equations.py     # Equation extraction from Docling output — LaTeX normalization, variable definitions
│   └── methods.py       # Method card extraction — source_algorithm detection, LLM-based reconstructed_method
├── taxonomy/
│   ├── extraction.py    # LLM-based tag extraction from paper markdown — JSON parsing, alias resolution
│   └── aliases.py       # Tag alias normalization, canonical resolution, merge tags, consolidation rules
├── synthesis/
│   ├── summaries.py     # LLM-generated scientific summaries — deactivate old, store new, format for embedding
│   ├── method_cards.py  # Method card reconstruction from source_algorithm + reconstructed_method via LLM
│   └── topic_reviews.py # Multi-step topical review: query→search→retrieve methods→compare→synthesize via LLM
├── search/
│   ├── fts.py           # FTS5 full-text search on search_units — query sanitization, markdown splitting
│   ├── ranking.py       # Weighted scoring: FTS + tag matches + year filters + scoring breakdown
│   └── context.py       # Context pack assembly: two-stage retrieval, token budget, comparison matrix, bibliography
└── docs/tasks/paperdb/  # Task breakdown and integration gap tracking (parallel development history)
```

### Key Design Decisions

- **Semantic identity, not hash-based**: Papers identified by `paper_key` (human-readable: `Macklin_2016_XPBD`), DOI, or arXiv ID. Multiple files can map to the same paper.
- **Processing runs over boolean flags**: `processing_runs` table tracks which operation ran with which backend/config — enables skip-if-equivalent and provenance tracking.
- **Search units, not whole-paper FTS**: Content indexed at section/paragraph/equation/method level for precise retrieval.
- **Method cards**: Two types — `source_algorithm` (extracted from paper text) and `reconstructed_method` (LLM-reconstructed with assumptions, steps, I/O).
- **Context packs**: Assembled markdown with selected papers, equations, methods, comparison matrix, bibliography — the primary artifact for feeding to coding agents.

## pyCruncher/ — Core Library

### LLM Agents & Tool-Use

One abstract `Agent` base class, multiple provider subclasses. Model profiles (name, base_url, api_key env var) are loaded from `config/LLMs.toml` by template name — no hardcoded URLs or keys. Tool calling is provider-agnostic: `try_tool()` dispatches to registered Python callbacks; each subclass only implements `extract_tool_call()`.

| File | Essence |
|------|---------|
| `Agent.py` | Abstract base: `load_template()` reads `config/LLMs.toml`, `try_tool()` dispatches tool calls, `bHistory`/`bTools` gate conversation state and tool injection |
| `AgentOpenAI.py` | Workhorse for all OpenAI-style endpoints (OpenAI, Groq, OpenRouter, LM Studio, Ollama) — same code, different `base_url` in the profile |
| `AgentDeepSeek.py` | Adds FIM (fill-in-the-middle) for code infilling and `query_json()`/`stream_json()` with `response_format={'type':'json_object'}`; imports math tools for registration |
| `AgentGoogle.py` | Adapts to Gemini's `generate_content`/`parts` API; converts `ToolScheme` dicts to `FunctionDeclaration`; `prepare_generation_config()` maps kwargs to `GenerationConfig` |
| `AgentAnthropic.py` | Minimal Claude Messages API wrapper — tool calling not fully wired; uses `from Agent import Agent` (standalone-style import) |
| `ToolScheme.py` | Introspects Python function signatures + docstrings → OpenAI/Gemini tool schema; `bOnlyRequired` omits optional params; `strict:True` enforces exact schema |
| `tools.py` | Callable math tools: `symbolic_derivative()` (Maxima), `compute_integral()`, `compute_numerical_derivative()` (NumPy), `check_numerical_vs_analytical_derivative()` (SymPy vs finite-diff) |

### Codebase Analysis

Dual-parser strategy: ctags (fast, many languages) + tree-sitter (precise AST). All output goes to `.shadow/` — source repo is never modified. Python files use stdlib `ast`; C++ uses tree-sitter + ctags.

| File | Essence |
|------|---------|
| `repo_mapper.py` | Main orchestrator: `discover_files()` → `analyze_python_file()` (AST) → `run_ctags_json()` → `generate_skeleton()` → optional `summarize_file_llm()` → roll-ups (`generate_tech_matrix()`, `generate_concept_map()`, `build_import_edges()`) |
| `cpp_type_analyzer.py` | Tree-sitter C++ analyzer: `TypeCollector` visitor populates `TypeRegistry` with nested `Scope` objects (namespaces, classes, methods, calls); `DEBUG_LEVEL=2` enables TRACE logging |
| `python_type_analyzer.py` | Tree-sitter Python analyzer: mirrors C++ design with `Scope`, `ClassInfo`, `FunctionInfo`, `TypeRegistry`; tracks imports and call relationships |
| `dependency_graph_tree_sitter.py` | AST-level call graph: `FunctionInfo.calls: Set[str]` extracted from syntax tree (more accurate than text scanning); `parse_directory()` returns file→FileInfo |
| `ctags.py` | `run_ctags()` drives universal-ctags with `--output-format=json`; `process_ctags_json_by_files()` groups by file/class; `process_ctags_json_claude()` reformats for LLM input |
| `ctags_dependency.py` | `DependencyProcessor` scans function bodies for known identifiers (textual, not AST — fast but may false-positive on comments/strings); `FunctionInfo.qualified_name` disambiguates methods |
| `scoped_cpp.py` | Regex-based C++ parser: `FUNCTION_MODIFIERS` handles `const`/`override`/`noexcept`/`[[attr]]`; strips comments first; misses templates/operators — use tree-sitter for accuracy |
| `get_function_headers_cpp.py` | Regex function-signature extractor; `is_not_function()` filters control-flow keywords; `re.VERBOSE` pattern with inline comments |
| `CodeDocumenter.py` | LLM-powered Doxygen generator: `find_function_end()` (brace matching), three context strategies (`get_function_context*`), uses `AgentDeepSeek` by default |
| `CodeDocumenter_md.py` | Markdown variant: supports DeepSeek + Gemini; `bLogPrompts=True` saves prompts for debugging; `max_context_size` controls per-request source size |
| `tree_sitter_utils.py` | Parser setup: builds C++ language lib from `/home/prokophapala/SW/vendor/tree-sitter-cpp` → `build/my-languages.so`; `get_qualified_name()` walks up tree; `visit_tree()` DFS callback |
| `file_utils.py` | Workhorse scanner: `should_ignore()` (fnmatch globs, not .gitignore), `process_files_serial()` (ThreadPoolExecutor timeout), `save/load_file_paths()` for resumable batches |
| `git_utils.py` | `get_commit_log()` / `get_commit_diff()` / `process_commit()` — subprocess git, no GitPython; writes Markdown changelog pages |
| `compile_utils.py` | ctypes bridge: pre-defined `array1d`/`array2d`/`array1i` ndpointer types; `g++ -shared` compilation via subprocess; no CMake |
| `vault_generator.py` | Jinja2 templates → Obsidian Markdown notes per topic; `file://` links open PDFs from shadow dir; handles missing fields gracefully |

### Paper Pipeline & Knowledge

Offline-first, fail-soft PDF→SQLite pipeline. Three backends tried in order (docling → local VLM → pdfminer). DOIs mined from text + resolved via CrossRef. Knowledge graph tags articles with scientific domains, math classes, solvers, data structures.

| File | Essence |
|------|---------|
| `paper_pipeline.py` | `PaperResult` dataclass tracks status; `convert_docling/vlm/pdfminer()` each return `(md, error)`; `chunk_markdown()` splits by headings; `summarize_paper()` asks model for structured summary; `postprocess_existing_run()` resolves DOIs/BibTeX; `_db_*` functions manage SQLite + FTS |
| `bib_utils.py` | `decode_latex()` via latexcodec + brace stripping; `extract_ngrams()` with sklearn + custom stopwords (English + BibTeX field names); `convert_custom_path()` strips Mendeley `:pdf` decorators |
| `knowledge_graph.py` | `ArticleMetadata` (pydantic) schema for essence/domains/math_classes/solvers/data_structures; `init_kg_db()` creates `tags`+`article_tags` tables (migration-safe `ALTER TABLE`); `build_knowledge_graph()` sends summaries to LLM for classification |

### Scientific Math

Maxima CAS as ground truth for symbolic derivatives. `code_derivs.py` verifies LLM-generated force-field code by comparing expressions against Maxima reference.

| File | Essence |
|------|---------|
| `Maxima.py` | Subprocess wrapper: `display2d:false` for machine-parseable output; `$` = silent, `;` = print; `get_derivs(E, DOFs)` computes E + all dE/dof in one batch |
| `code_derivs.py` | `makeFormulas()` calls Maxima; `check_formulas()` generates Maxima diff script (zero = correct); `count_operations()` crude FLOP estimate (pow=20, div=3, mul=1, add=1); fills `prompts/ImplementPotential/` templates |
| `CheckNumerical.py` | Minimal finite-difference: `getNumDerivs()` central difference (O(h²)); `checkDerivs()` has syntax error (missing default for `params`) — experimental/incomplete |

## pyCruncher2/scientific/ — Scientific Computing

Reorganized versions of pyCruncher scientific modules. Same logic, cleaner package structure.

| Path | Essence |
|------|---------|
| `cas/maxima.py` | Same as `pyCruncher/Maxima.py` — subprocess wrapper, `display2d:false`, `$` vs `;` |
| `cas/code_derivs.py` | Same as `pyCruncher/code_derivs.py` — Maxima→LLM code verification, FLOP counting |
| `cas/maxima_tools.py` | Same as `pyCruncher/tools.py` — callable math tools: `symbolic_derivative()`, `compute_integral()`, numerical cross-validation |
| `gpu/OpenCLBase.py` | `select_device()` prefers NVIDIA (PoCL/CPU timings must not be reported as GPU); `OpenCLBase` manages context/queue/buffer dict; `load_program()` compiles `.cl` + extracts kernel headers via regex |
| `gpu/clUtils.py` | Flat helper functions (not a class): `bytePerFloat=4` for memory calc; `FFT=None` lazy-init; rounding global sizes to local-size multiples |
| `gpu/opencl.py` | Standalone smoke test: `PYOPENCL_CTX` env selects device; `sys.path.append('../')` for in-dir execution |
| `gpu/cuda.py` | Standalone smoke test: `pycuda.autoinit` default context; `SourceModule` runtime compilation (no nvcc); reads `./nbody.cu` |
| `gpu/run_biot_savart.py` | Biot-Savart magnetic field integration on GPU |
| `gpu/run_scanNonBond.py` | Non-bonded interaction scan on GPU |
| `gpu/test_num_integral_cl.py` | Numerical integration test on OpenCL |
| `gpu/kernels/` | `.cl` kernel source files |
| `elements.py` | Flat list of element tuples indexed by constants (`index_Z`, `index_Rcov`, `index_color`, etc.); SSOT for element properties — no class, just data |
| `plotUtils.py` | `plotEF()` 2×1 subplot for E/F validation; `numDeriv()` from arrays; element colors from `elements.py` for consistency with 3D renderer |

## cpp/ — C++ Kernels

Header-only vector math + inline force-field evaluators. Designed for `Vec3d` (double precision) in scientific computing. All functions inline for zero-overhead abstraction.

| File | Essence |
|------|---------|
| `Vec3.h` | `Vec3T<T>` union (`x/y/z` = `a/b/c` = `array[3]`); swizzles (`xzy()`, `yxz()`...); `dot()`, `cross()`, `norm()`, `normalize()`; typedefs `Vec3i/f/d/b`; constants `Vec3dZero/One/X/Y/Z` |
| `Vec4.h` | 4D counterpart of Vec3 — homogeneous coordinates, quaternions |
| `Vec2.h` | 2D counterpart — 2D geometry, texture coords |
| `ForceFields.cpp` | `getCoulomb()/_getCoulomb()` energy+force+variational deriv w.r.t. `qq`; `getLJ()/_getLJ()` with `E0`/`R0` params; `getLJQ()` combined; `varCoulomb()/varLJ()/varLJQ()` for parameter optimization |

## molecule_renderer/ — 3D Viewer

Standalone Three.js viewer — no Python dependency for rendering. `server.py` is just a convenience static server.

| File | Essence |
|------|---------|
| `moleculeRenderer.js` | `MoleculeRenderer.renderMolecule()` — sphere meshes for atoms, cylinder meshes for bonds; positions/rotates bonds from two atom vectors |
| `molecule.js` | `Molecule` class: atom symbols, positions, automatic bond generation by distance |
| `sceneSetup.js` | Camera, lights, renderer configuration |
| `selectionManager.js` | Click/selection handling for atoms |
| `utility.js` | Shared utility functions |
| `server.py` | Minimal `http.server` static file server for local preview |
| `index.html` | Entry point — loads Three.js and renderer modules |

## prokop-bot/ — VS Code Extension

| Path | Essence |
|------|---------|
| `src/extension.ts` | Extension entry point — registers commands, views, and Python script invocations |
| `src/webview.ts` | Webview panel: chat UI, model selection, response display |
| `src/treeDataProvider.ts` | Tree view of agent sessions / conversation history |
| `src/script.py` / `script_agent.py` | Python helpers called by the extension to run agents locally |

## examples/ — Curated Examples

| Path | Essence |
|------|---------|
| `MCP/` | MCP servers (chemistry, LAMMPS, Maxima) + matching clients — demonstrates how an LLM consumes external tools via Model Context Protocol |
| `knowledge/` | PDF extraction, summarization, BibTeX classification, Chroma vector store ingestion, RAG queries (DeepSeek + Gemini) — worked examples for the paper pipeline |
| `scientific/` | Maxima derivative computation, OpenCL/CUDA N-body, Slater-orbital integration — end-to-end scientific computing examples |

## prompts/ — LLM Prompt Templates

| Path | Essence |
|------|---------|
| `ImplementPotential/` | Force-field code generation pipeline: `coder_system_prompt.md` + `matematician_system_prompt.md` define agent personas; `code_first.md`/`code_cpp.md` generate code; `simplify.md`/`substitution.md` optimize expressions; `code_incorect_result.md`/`code_not_compile.md` handle failures; `understand.md` explains concepts |
| `cpp_templates/` | `FFderivs.cpp` — reference C++ force-field derivative code used as a prompt input |
| `sumarize_article_pdf.md` | Prompt template for structured article summarization (title, keywords, essence, equations, algorithms) |

## config/ — Configuration

| File | Essence |
|------|---------|
| `LLMs.toml` | SSOT for provider profiles: model name, base URL, API-key env var name, context length; read by `Agent.load_template()` |

## doc/ & docs/ — Documentation

| Path | Essence |
|------|---------|
| `doc/LLMs.md` | LLM agent system design — abstract interface, provider subclasses, tool-use flow |
| `doc/MCP_*.md` | MCP integration guides: Perplexity, Gemini, DeepSeek, Maxima servers |
| `doc/MaximaTutorial.md` | Maxima CAS tutorial — symbolic differentiation, expression simplification |
| `doc/OpenCLBase.md` | OpenCLBase class reference — device selection, buffer management, kernel loading |
| `doc/Doxygen.md` | Doxygen comment conventions for C++ documentation |
| `doc/ctags.md` | universal-ctags usage guide — JSON output format, kind filters |
| `doc/Providers/` | Per-provider setup notes (Anthropic, DeepSeek, Google, etc.) |
| `docs/topical_audit/` | Four work-stream deep dives (literature, LLMs, codebase, scientific) |
| `docs/pipelines_tutorial.md` | End-to-end tutorial: PDF pipeline + repo pipeline |
| `docs/repo_mapper_tutorial.md` | Repository mapper usage and output structure |
| `docs/cpp_analyzer_status.md` | C++ tree-sitter analyzer: what works, known limitations |
| `docs/python_analyzer_status.md` | Python tree-sitter analyzer status |
| `docs/dependency_graph_analyzer.md` | Dependency graph design: ctags vs tree-sitter approaches |
| `docs/NumIntegrationCL.md` | OpenCL numerical integration notes and benchmarks |
| `docs/setup_Database_SQL.md` | SQLite schema, FTS index setup, and example queries for paper DB |

## tests/ — Test Drivers

Experimental scripts — run them to verify functionality. Full output must be visible (no `| tail`, `| grep`, `&`).

| File | Tests |
|------|-------|
| `test_LLM_Agent.py` | Agent base class — template loading, API key resolution |
| `test_DeepSeek*.py` | DeepSeek connectivity, FIM completion, JSON mode, tool calling |
| `test_GoogleAI*.py` | Gemini connectivity, `generate_content`, tool declarations |
| `test_Groq*.py` | Groq connectivity, tool calling |
| `test_LMstutio.py` | LM Studio local inference — `check_lmstudio_with_url()` |
| `test_repo_mapper.py` | Repo mapper pipeline — discovery → AST → ctags → skeleton → LLM summary |
| `test_cpp_type_analyzer.py` | C++ tree-sitter analyzer — scope/class/call extraction |
| `test_python_type_analyzer.py` | Python tree-sitter analyzer — imports, classes, calls |
| `test_dependency_graph*.py` | Dependency graph builders (ctags + tree-sitter variants) |
| `test_ctags.py` | ctags JSON processing — file/class grouping |
| `test_tree_sitter.py` | Tree-sitter parser setup and node traversal |
| `test_documenter*.py` | Code documentation generation (Doxygen + Markdown) |
| `test_paper_pipeline.py` | PDF pipeline CLI — `--limit`, `--backend`, `--postprocess` |
| `test_bibtex*.py` | BibTeX loading, LaTeX decoding, n-gram extraction |
| `test_maxima_derivs.py` | Maxima derivative computation — `get_derivs()` |
| `test_pymaxima.py` | Maxima subprocess wrapper — `run_maxima()` |
| `test_pyOpenCL.py` / `test_pyCUDA.py` | GPU compute smoke tests |
| `test_coder_forcefield*.py` | Force-field code generation + `check_formulas()` verification |
| `test_GenerateErrorCode.py` | Error code generation |
| `test_GitToMarkdown.py` | Git history → Markdown conversion |
| `Cpp_Train/` | C++ training/reference snippets for code generation |
| `GitCommits/` | Git commit summaries generated by multiple LLM models |
| `Model_Benchmarks/` | LLM benchmark results and comparisons |

# pyCruncher

The core Python library for AutoCrunchCoder. Contains the multi-provider LLM agent system, code analyzers, paper pipeline, and scientific tooling.

## LLM Agents

One abstract `Agent` base class with provider subclasses. Model profiles loaded from `config/LLMs.toml` — no hardcoded URLs or keys. Tool calling is provider-agnostic.

- `Agent.py` — Abstract base: `load_template()`, `try_tool()`, `query()`, `stream()`. `bHistory`/`bTools` gate conversation state and tool injection.
- `AgentOpenAI.py` — Workhorse for all OpenAI-style endpoints (OpenAI, Groq, OpenRouter, LM Studio, Ollama). Same code, different `base_url`.
- `AgentDeepSeek.py` — Adds FIM (fill-in-the-middle) and `query_json()`/`stream_json()` with strict JSON output.
- `AgentGoogle.py` — Adapts to Gemini's `generate_content`/`parts` API; converts `ToolScheme` dicts to `FunctionDeclaration`.
- `AgentAnthropic.py` — Minimal Claude Messages API wrapper (tool calling not fully wired).
- `ToolScheme.py` — Introspects Python function signatures + docstrings → OpenAI/Gemini tool schema.
- `tools.py` — Callable math tools: `symbolic_derivative()` (Maxima), `compute_integral()`, `check_numerical_vs_analytical_derivative()` (SymPy vs finite-diff).

## Codebase Analysis

Dual-parser strategy: ctags (fast, many languages) + tree-sitter (precise AST). All output to `.shadow/` — source repo never modified.

- `repo_mapper.py` — Main orchestrator: file discovery → AST/ctags → skeletons → optional LLM summaries → roll-ups (tech matrix, concept map, import edges).
- `cpp_type_analyzer.py` — Tree-sitter C++ analyzer: `TypeCollector` visitor → `TypeRegistry` with nested scopes, classes, methods, calls.
- `python_type_analyzer.py` — Tree-sitter Python analyzer: mirrors C++ design; tracks imports, classes, calls.
- `dependency_graph_tree_sitter.py` — AST-level call graph (`FunctionInfo.calls: Set[str]`); more accurate than text scanning.
- `ctags.py` — Universal-ctags driver with JSON output; groups by file/class; `process_ctags_json_claude()` reformats for LLM input.
- `ctags_dependency.py` — `DependencyProcessor` scans function bodies for known identifiers (textual — fast but may false-positive).
- `scoped_cpp.py` — Regex-based C++ parser (fast, no deps); handles `const`/`override`/`noexcept`; misses templates/operators.
- `get_function_headers_cpp.py` — Regex function-signature extractor; filters control-flow keywords.
- `CodeDocumenter.py` — LLM-powered Doxygen generator: brace-matching for function bodies, three context strategies.
- `CodeDocumenter_md.py` — Markdown variant: supports DeepSeek + Gemini; `bLogPrompts` for debugging.
- `tree_sitter_utils.py` — Parser setup (builds C++ lib from vendor checkout), `get_qualified_name()`, `visit_tree()`.
- `file_utils.py` — Workhorse scanner: fnmatch ignore patterns, serial processing with timeout, resumable path logs.
- `git_utils.py` — Subprocess git → Markdown changelog (no GitPython dependency).
- `compile_utils.py` — ctypes bridge: `g++ -shared` compilation, pre-defined NumPy ndpointer types.
- `vault_generator.py` — Jinja2 → Obsidian Markdown notes with `file://` links.

## Paper Pipeline

Offline-first, fail-soft PDF→SQLite pipeline. Three backends (docling → VLM → pdfminer). DOIs resolved via CrossRef. Knowledge graph tags articles.

- `paper_pipeline.py` — `PaperResult` dataclass; `convert_*()` backends; `chunk_markdown()`; `summarize_paper()`; `postprocess_existing_run()`; SQLite + FTS.
- `bib_utils.py` — `decode_latex()` via latexcodec; `extract_ngrams()` with sklearn; Mendeley path cleanup.
- `knowledge_graph.py` — `ArticleMetadata` (pydantic); `init_kg_db()` (migration-safe); `build_knowledge_graph()` via LLM classification.

## Scientific Math

- `Maxima.py` — Subprocess wrapper: `display2d:false`; `$` = silent, `;` = print; `get_derivs(E, DOFs)` batch derivative.
- `code_derivs.py` — `check_formulas()` generates Maxima diff script (zero = correct); `count_operations()` FLOP estimate; fills `prompts/ImplementPotential/` templates.
- `CheckNumerical.py` — Minimal finite-difference (experimental/incomplete — has syntax error in `checkDerivs`).

See `docs/topical_audit/` for the topical breakdown and `tests/` for usage examples.

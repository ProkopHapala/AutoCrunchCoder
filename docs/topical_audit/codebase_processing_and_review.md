# 3. Codebase Processing & Review

## What this topic does

Analyze scientific codebases (mostly Python and C++) to produce navigable skeletons, dependency graphs, automatic documentation, and review roll-ups. Everything is written to a non-destructive `.shadow/` output tree so the original repo is never touched.

## Main challenges and how they are solved

- **Parsing C++ reliably**: the framework uses `ctags` plus `tree-sitter` plus custom scope/type registries; if one parser fails the next one is still available.
- **Understanding dependencies**: `ctags_dependency.py` and `dependency_graph_tree_sitter.py` build call graphs from parsed source.
- **LLM context limits**: `repo_mapper.py` generates concise file skeletons from AST/ctags first, then optionally asks an LLM for a summary only when needed.
- **Non-destructive analysis**: `repo_mapper.py` always outputs to a shadow directory and never edits the input repo.

## Core files and their essence

### `pyCruncher/repo_mapper.py`

The main repository analysis orchestrator.

- `discover_files()` — scan a repo for code files, honoring extension and ignore globs (`DEFAULT_IGNORES`).
- `analyze_python_file()` — stdlib AST parser that extracts classes, methods, top-level functions, imports, and line counts.
- `run_ctags_json()` / `parse_ctags_json()` — run universal-ctags and load its JSON output.
- `generate_skeleton()` — create a concise per-file text skeleton from `FileAnalysis` and `SymbolInfo`.
- `summarize_file_llm()` / `summarize_file_deepseek()` — ask a local model to summarize a file from its skeleton and a head chunk.
- `compute_folder_stats()` / `generate_tech_matrix()` / `generate_concept_map()` — roll-ups: per-folder language counts, a folder×language CSV, and a concept map grouped by folder.
- `build_import_edges()` — build file→module edges from Python imports.
- `run_repo_mapper()` — top-level driver that walks discovery → AST/ctags → skeletons → optional LLM summaries → report.

### `pyCruncher/cpp_type_analyzer.py`

Typed C++ analysis using tree-sitter.

- `Scope`, `ScopeType`, `AccessSpecifier`, `Location`, `ParameterInfo`, `FunctionCall`, `FunctionInfo`, `MethodInfo`, `VariableInfo`, `ClassInfo`, `NamespaceInfo`, `TypeInfo`, `TypeRegistry`, `TypeCollector` — dataclasses and visitor that track C++ scopes, classes, methods, variables, and function calls.
- The registry lets other tools ask "what is defined in this namespace/class?" and "what does this function call?".

### `pyCruncher/python_type_analyzer.py`

Same idea for Python.

- `Scope`, `ClassInfo`, `FunctionInfo`, `MethodInfo`, `TypeRegistry`, `TypeCollector` — tree-sitter-based Python type/scope registry.
- Tracks imports, class fields, method signatures, and call relationships.

### `pyCruncher/dependency_graph_tree_sitter.py`

Builds a dependency/call graph directly from tree-sitter syntax trees.

- `DependencyGraphTreeSitter` — `parse_file()` and `parse_directory()` for C++ and Python; stores `FunctionInfo`, `ClassInfo`, `FileInfo` objects with call sets.
- Complements the ctags-based dependency processor below.

### `pyCruncher/ctags.py` and `pyCruncher/ctags_dependency.py`

- `ctags.py` — `run_ctags()`, `process_ctags_json_by_files()`, `process_ctags_json_by_files_2()`, `process_ctags_json_claude()` — drive `universal-ctags` and organize the JSON output by file and by class.
- `ctags_dependency.py` — `DependencyProcessor` extracts function body identifiers, builds call dependencies, and can build a dependency tree and `FunctionInfo` records with `qualified_name`.

### `pyCruncher/CodeDocumenter.py`

Generate Doxygen-style documentation with an LLM.

- `CodeDocumenter` — loads a ctags database, reads a file, and generates per-function/method docs using `AgentDeepSeek`.
- `find_function_end()` — brace-matching to locate function bodies.
- `get_function_context()`, `get_function_context_wholefile()`, `get_function_context_body()` — decide how much context to send to the model.

### `pyCruncher/tree_sitter_utils.py`

Tree-sitter plumbing.

- `get_parser()` — build the C++ language library from the vendor checkout (`/home/prokophapala/SW/vendor/tree-sitter-cpp`) and create a parser.
- `get_node_text()`, `get_qualified_name()`, `visit_tree()` — common tree-sitter helpers.

### Support utilities

- `pyCruncher/file_utils.py` — `find_files()`, `should_ignore()`, `read_file()`, `write_file()`, `save_file_paths()`, `load_file_paths()`, `process_files_serial()`. The workhorse file scanner.
- `pyCruncher/git_utils.py` — `get_commit_log()`, `get_commit_diff()`, `get_commit_changes()`, `write_commit_to_markdown()`, `process_commit()` — turn git history into markdown.
- `pyCruncher/compile_utils.py` — ctypes array type helpers and a quick `g++` pipeline for compiling `nbody` into a shared library.
- `pyCruncher/vault_generator.py` — knowledge-vault generation from code (lightweight wrapper).

### Tests and docs

- `tests/test_repo_mapper.py`, `test_documenter.py`, `test_python_type_analyzer.py`, `test_cpp_type_analyzer.py`, `test_ctags.py`, `test_dependency_graph*.py`, `test_tree_sitter.py` — test drivers for each analyzer.
- `docs/repo_mapper_tutorial.md`, `docs/cpp_analyzer_status.md`, `docs/python_analyzer_status.md`, `docs/dependency_graph_analyzer.md`, `doc/Doxygen.md`, `doc/ctags.md` — design/status/tutorials.

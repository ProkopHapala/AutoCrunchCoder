AutoCrunchCoder is an AI-driven framework for scientific software development — it uses LLMs to automate code generation, analysis, refactoring, and documentation across computational chemistry/physics workflows. Numerical correctness, reproducibility, and simplicity are paramount.

## Quick Navigation

- **[CODEMAP.md](CODEMAP.md)** — full repository structure with per-file role descriptions
- **[FeatureChecklist.md](FeatureChecklist.md)** — feature status tracker (implemented / WIP / planned)
- **[docs/topical_audit/](docs/topical_audit/)** — four work-stream deep dives:
  1. [Literature, PDF & reference management](docs/topical_audit/01_literature_pdf_and_reference_management.md)
  2. [Local LLMs & API integration](docs/topical_audit/02_local_llms_and_api_integration.md)
  3. [Codebase processing & review](docs/topical_audit/03_codebase_processing_and_review.md)
  4. [Scientific computation, math & visualization](docs/topical_audit/04_scientific_computation_math_and_visualization.md)

## Core Principles

- **KISS** (Keep It Simple), Simplest solution that works. One-liner > ten-liner.
- **AHA** (Avoid Hasty Abstractions), avoid boilerplate
- **YAGNI** : **Surgical Edits** — Touch only what's needed. No unrelated cleanup. Comment out, don't delete. Ask if ambiguous.
- **DRY** : Inventory existing code before writing new. Generalize rather than duplicate. Check `pyCruncher/` and `pyCruncher2/` for reusable functions before creating new ones.
- **SoC** (Separation of Concerns), separate module for Agents, Analyzers, Paper pipeline, GPU kernels, CLI, GUI. Thin test scripts call general workhorse functions from `pyCruncher/`.
- **SSOT** : `config/LLMs.toml` is the single source of truth for provider/model profiles. `pyCruncher/paper_pipeline.py` is the SSOT for the PDF→knowledge pipeline. `pyCruncher/repo_mapper.py` is the SSOT for codebase analysis.
- **TDD** : Define verification before coding. For LLM-generated code, verify against Maxima symbolic reference or numerical finite-difference checks. Run tests after every change.
- **Fail Fast** : No silent fallbacks (try-catch). Crashes with stack traces > masked bugs. Look for root cause, not symptoms.
- **Compact code**, unlimited line length (function calls must be one line). Short names for math symbols (`E_tot`, `T_ij`, `dE_r`).

## Never Do This

- Never delete or rearrange existing code without explicit permission
- Never perform unrelated aesthetic/style edits
- Never apply quick-fixes that hide root causes (e.g. hard-coded outputs)
- Never reinvent functionality already implemented. Inventory first — check `pyCruncher/`, `pyCruncher2/`, `examples/`, and `tests/` for existing implementations.
- Never copy-paste between modules — extract to shared lib and import.
- **Ask, don't guess** — when you encounter a problem where you are not sure, ask the user instead of trying to infer it.
- **NEVER mark an issue as "fixed", "resolved", or "done" without explicit USER confirmation.** This applies to bug reports, task documents, ToDo items, and any status tracking. A code change is NOT proof of a fix. You must: (1) run a test or verification that demonstrates the fix, (2) show the result to the USER, (3) wait for USER confirmation before updating any status field. Violating this rule is considered a critical error. When in doubt, leave the status as "investigating" or "unverified".

## Debugging & Testing

**Fail loud** — crashes with stack traces > masked bugs. Debug prints gated by verbosity. Tests in `tests/` are experimental drivers — run them to verify functionality. For LLM-generated scientific code, verify numerical correctness via parity checks against Maxima symbolic reference or analytical/physical invariants.

- **Agent tests:** `tests/test_LLM_Agent.py`, `test_DeepSeek*.py`, `test_GoogleAI*.py`, `test_Groq*.py`, `test_LMstutio.py`
- **Analyzer tests:** `tests/test_repo_mapper.py`, `test_cpp_type_analyzer.py`, `test_python_type_analyzer.py`, `test_dependency_graph*.py`, `test_ctags.py`, `test_tree_sitter.py`
- **Paper pipeline:** `tests/test_paper_pipeline.py`, `test_bibtex*.py`, `test_sumarize_pdfs*.py`
- **Scientific math:** `tests/test_maxima_derivs.py`, `test_pymaxima.py`, `test_coder_forcefield*.py`, `test_pyOpenCL.py`, `test_pyCUDA.py`
- **Never filter test stdout** — `| tail`, `| grep`, `&` are forbidden when running tests. Full output must be visible for debugging.
- **Refactoring discipline**: Before refactoring, run each old file, show results to USER for review. Identify useful features from each version. Reproduce carefully. Only delete old files after explicit USER approval.

## LLM Agent Development

- All providers inherit from `pyCruncher/Agent.py` — follow the abstract interface (`setup_client`, `query`, `stream`, `get_response_text`, `extract_tool_call`).
- New providers go in `pyCruncher/Agent<Name>.py` and must be registered in `config/LLMs.toml`.
- Tool schemas are auto-generated from Python function signatures via `ToolScheme.schema()` — annotate types and docstrings.
- Math tools (`pyCruncher/tools.py`) use Maxima + SymPy + NumPy for symbolic/numerical verification — reuse, don't reimplement.
- For force-field code generation, use the prompt templates in `prompts/ImplementPotential/` and verify with `code_derivs.check_formulas()`.

## Codebase Analysis

- `pyCruncher/repo_mapper.py` is the main orchestrator — always output to `.shadow/` (non-destructive).
- C++ analysis uses tree-sitter + ctags (dual parser for robustness).
- Python analysis uses stdlib AST + tree-sitter.
- Dependency graphs: use `dependency_graph_tree_sitter.py` for tree-sitter-based, `ctags_dependency.py` for ctags-based.
- Documentation generation: `CodeDocumenter.py` (Doxygen) or `CodeDocumenter_md.py` (Markdown).

## Performance & Languages

- Minimize Python orchestration; push compute to OpenCL/CUDA kernels. Flat arrays, cache-aware, preallocate.
- GPU/OpenCL: memory latency, gather over scatter, local memory, minimize host-device transfers. Use `pyCruncher2/scientific/gpu/OpenCLBase.py` as the orchestration layer.
- C++ kernels: header-only `Vec3`/`Vec4`/`Vec2` in `cpp/` — prefer `Vec3d` (double) for scientific precision. Inline force-field functions in `cpp/ForceFields.cpp`.
- Maxima CAS: use `pyCruncher/Maxima.py` or `pyCruncher2/scientific/cas/maxima.py` for symbolic derivations — never hard-code derived expressions, always compute them.

## Documentation & Navigation

- Before writing: search existing implementations in `pyCruncher/`, `pyCruncher2/`, and `examples/`.
- After implementing: update `README.md`, `CODEMAP.md`, and `FeatureChecklist.md` if new files/features are added.
- `docs/topical_audit/` — cross-implementation maps per work-stream (4 topics)
- `README.md` per folder — local index; `CODEMAP.md` — full repo structure
- Visualization: separate compute from plotting; `plt.show()` only in CLI/main, never in library code. Use `pyCruncher2/scientific/plotUtils.py` for shared plotting helpers.
- `molecule_renderer/` — web-based 3D viewer using Three.js; keep it standalone (no Python dependency for rendering).

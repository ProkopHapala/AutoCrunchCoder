# pyCruncher vs pyCruncher2 — Relationship, Status, and Open Issues

## TL;DR

`pyCruncher/` is the **active, complete** core library. `pyCruncher2/` is an **incomplete reorganization** attempt that was supposed to split the flat `pyCruncher/` modules into a proper Python package with sub-packages (`agents/`, `knowledge/`, `utils/`, `scientific/`). Only the `scientific/` sub-package was ever created. The `examples/` scripts were written against the *planned* `pyCruncher2/` structure and are **broken** — they import from modules that don't exist.

---

## 1. What pyCruncher/ is

`pyCruncher/` is the **single working library**. All 28 Python modules are flat (no subdirectories), all tests import from it, and all non-example code uses it. It contains:

- **Agents**: `Agent.py`, `AgentOpenAI.py`, `AgentDeepSeek.py`, `AgentGoogle.py`, `AgentAnthropic.py`, `ToolScheme.py`
- **Code analysis**: `repo_mapper.py`, `cpp_type_analyzer.py`, `python_type_analyzer.py`, `ctags.py`, `ctags_dependency.py`, `tree_sitter_utils.py`, `dependency_graph_tree_sitter.py`, `scoped_cpp.py`, `get_function_headers_cpp.py`, `CodeDocumenter.py`, `CodeDocumenter_md.py`
- **Paper pipeline**: `paper_pipeline.py`, `bib_utils.py`, `knowledge_graph.py`, `vault_generator.py`
- **Scientific math**: `Maxima.py`, `code_derivs.py`, `tools.py`, `CheckNumerical.py`
- **Utilities**: `file_utils.py`, `git_utils.py`, `compile_utils.py`

**Status**: Complete, actively used, all tests pass through it.

## 2. What pyCruncher2/ was meant to be

`pyCruncher2/` was intended to be a **reorganized version** of `pyCruncher/` with a proper Python package structure. The planned layout (inferred from the `examples/` imports that reference it):

```
pyCruncher2/                    ← PLANNED but never completed
├── __init__.py                 ← MISSING (not a proper package)
├── agents/                     ← NEVER CREATED
│   ├── __init__.py
│   ├── base.py                 ← AgentResponse, base Agent class
│   ├── openai.py               ← AgentOpenAI
│   ├── deepseek.py             ← AgentDeepSeek
│   └── google.py               ← AgentGoogle
├── knowledge/                  ← NEVER CREATED
│   ├── __init__.py
│   └── store/
│       ├── faiss.py            ← setup_vector_store (FAISS)
│       └── chroma.py           ← setup_vector_store (Chroma)
├── utils/                      ← NEVER CREATED
│   ├── __init__.py
│   └── files.py                ← find_files, write_file, read_file
└── scientific/                 ← PARTIALLY CREATED (this is all that exists)
    ├── elements.py             ← exists (no pyCruncher counterpart)
    ├── plotUtils.py            ← exists (no pyCruncher counterpart)
    ├── cas/
    │   ├── maxima.py           ← copy of pyCruncher/Maxima.py (with subprocess fix)
    │   ├── code_derivs.py      ← copy of pyCruncher/code_derivs.py
    │   └── maxima_tools.py     ← copy of pyCruncher/tools.py
    └── gpu/
        ├── OpenCLBase.py       ← exists (no pyCruncher counterpart)
        ├── clUtils.py          ← exists (no pyCruncher counterpart)
        ├── opencl.py           ← standalone smoke test (not a library)
        ├── cuda.py             ← standalone smoke test (not a library)
        ├── run_biot_savart.py  ← example script
        ├── run_scanNonBond.py  ← example script
        ├── test_num_integral_cl.py ← test script
        └── kernels/            ← .cl source files
```

## 3. What actually exists in pyCruncher2/

Only `pyCruncher2/scientific/` was created. It contains:

| Path | Origin | Status |
|------|--------|--------|
| `scientific/cas/maxima.py` | Copy of `pyCruncher/Maxima.py` | **Diverged** — uses `subprocess.run` instead of `Popen` polling (debug fix) |
| `scientific/cas/code_derivs.py` | Copy of `pyCruncher/code_derivs.py` | **Identical** (only docstring added) |
| `scientific/cas/maxima_tools.py` | Copy of `pyCruncher/tools.py` | **Identical** (only docstring added) |
| `scientific/gpu/OpenCLBase.py` | No pyCruncher counterpart | **Unique** — OpenCL orchestration class |
| `scientific/gpu/clUtils.py` | No pyCruncher counterpart | **Unique** — OpenCL helper functions |
| `scientific/gpu/opencl.py` | No pyCruncher counterpart | **Unique** — standalone smoke test script |
| `scientific/gpu/cuda.py` | No pyCruncher counterpart | **Unique** — standalone smoke test script |
| `scientific/gpu/run_*.py` | No pyCruncher counterpart | **Unique** — GPU example scripts |
| `scientific/elements.py` | No pyCruncher counterpart | **Unique** — periodic table data |
| `scientific/plotUtils.py` | No pyCruncher counterpart | **Unique** — shared plotting helpers |

**Key point**: `pyCruncher2/` has no `__init__.py` at the top level — it's not even a proper Python package. The `scientific/cas/__init__.py` exists but is empty.

## 4. What's missing from pyCruncher2/

### 4.1 Entire sub-packages never created

| Planned sub-package | pyCruncher/ source | Status |
|---------------------|---------------------|--------|
| `pyCruncher2/agents/` | `Agent.py`, `AgentOpenAI.py`, `AgentDeepSeek.py`, `AgentGoogle.py`, `AgentAnthropic.py`, `ToolScheme.py` | **Not started** |
| `pyCruncher2/knowledge/` | `paper_pipeline.py`, `bib_utils.py`, `knowledge_graph.py`, `vault_generator.py` | **Not started** |
| `pyCruncher2/utils/` | `file_utils.py`, `git_utils.py`, `compile_utils.py` | **Not started** |
| `pyCruncher2/analysis/` | `repo_mapper.py`, `cpp_type_analyzer.py`, `python_type_analyzer.py`, `ctags.py`, `ctags_dependency.py`, `tree_sitter_utils.py`, `dependency_graph_tree_sitter.py`, `scoped_cpp.py`, `get_function_headers_cpp.py`, `CodeDocumenter.py`, `CodeDocumenter_md.py` | **Not started** (not even referenced in examples) |

### 4.2 Missing `__init__.py` files

- `pyCruncher2/__init__.py` — **missing** (package not importable in standard Python)
- `pyCruncher2/scientific/__init__.py` — **missing**
- `pyCruncher2/scientific/gpu/__init__.py` — **missing**

Only `pyCruncher2/scientific/cas/__init__.py` exists (empty).

### 4.3 Missing functions in existing files

The `examples/` scripts import functions that don't exist in the `pyCruncher2/` files:

| Example import | Expected in | Actually exists? |
|----------------|-------------|-----------------|
| `from pyCruncher2.scientific.gpu.cuda import compile_cuda_kernel, allocate_and_copy` | `gpu/cuda.py` | **No** — `cuda.py` is a standalone script with no function definitions |
| `from pyCruncher2.scientific.gpu.opencl import setup_opencl_context, compile_opencl_kernel, create_buffer` | `gpu/opencl.py` | **No** — `opencl.py` is a standalone script with no function definitions |
| `from pyCruncher2.scientific.cas.maxima import MaximaSession` | `cas/maxima.py` | **No** — `maxima.py` has `run_maxima`, `get_derivs`, `run_maxima_script` but no `MaximaSession` class |

## 5. Broken examples

The following `examples/` scripts import from `pyCruncher2/` paths that **do not exist** and will fail on import:

| File | Broken imports |
|------|----------------|
| `examples/knowledge/rag_deepseek.py` | `pyCruncher2.agents.deepseek`, `pyCruncher2.knowledge.store.faiss` |
| `examples/knowledge/rag_gemini_chroma.py` | `pyCruncher2.agents.google`, `pyCruncher2.knowledge.store.chroma` |
| `examples/knowledge/pdf_extraction.py` | `pyCruncher2.agents.base`, `pyCruncher2.agents.openai` |
| `examples/knowledge/file_summarization.py` | `pyCruncher2.agents.openai`, `pyCruncher2.agents.deepseek`, `pyCruncher2.utils.files` |
| `examples/knowledge/pdf_summarization.py` | `pyCruncher2.agents.openai`, `pyCruncher2.utils.files` |
| `examples/knowledge/bibtex_classification.py` | `pyCruncher2.agents.openai`, `pyCruncher2.agents.deepseek` |
| `examples/scientific/cuda_nbody.py` | `pyCruncher2.scientific.gpu.cuda.compile_cuda_kernel` (function doesn't exist) |
| `examples/scientific/opencl_nbody.py` | `pyCruncher2.scientific.gpu.opencl.setup_opencl_context` (function doesn't exist) |
| `examples/scientific/slater_orbital_integration.py` | `pyCruncher2.scientific.cas.maxima.MaximaSession` (class doesn't exist) |

**Working** examples (imports resolve):
- `examples/MCP/mcp_server_maxima.py` — imports `run_maxima, get_derivs, run_maxima_script` from `pyCruncher2.scientific.cas.maxima` ✓
- `examples/MCP/mcp_server_maxima_stdio.py` — same ✓
- `examples/scientific/maxima_derivatives.py` — imports `get_derivs` from `pyCruncher2.scientific.cas.maxima` ✓

## 6. Who uses what?

| Consumer | Imports from `pyCruncher/` | Imports from `pyCruncher2/` |
|----------|---------------------------|----------------------------|
| `tests/` (all test scripts) | **Yes** (all) | **No** |
| `examples/MCP/mcp_server_maxima*.py` | No | **Yes** (works) |
| `examples/scientific/maxima_derivatives.py` | No | **Yes** (works) |
| `examples/scientific/cuda_nbody.py` | No | **Yes** (broken) |
| `examples/scientific/opencl_nbody.py` | No | **Yes** (broken) |
| `examples/scientific/slater_orbital_integration.py` | No | **Yes** (broken) |
| `examples/knowledge/*.py` (6 files) | No | **Yes** (all broken) |
| `pyCruncher/` internal imports | **Yes** (self) | **No** |
| `pyCruncher2/` internal imports | No | **Yes** (self, within `scientific/`) |

**Bottom line**: `pyCruncher/` is used by all tests and the actual pipeline. `pyCruncher2/` is used only by `examples/`, and most of those are broken.

## 7. Code divergence

The only meaningful code divergence is in `maxima.py`:

| Aspect | `pyCruncher/Maxima.py` | `pyCruncher2/scientific/cas/maxima.py` |
|--------|------------------------|---------------------------------------|
| `run_maxima_script()` | `Popen` + manual polling loop with timeout | `subprocess.run` with `timeout` parameter |
| Robustness | Can hang if Maxima waits for input | Cleaner — `subprocess.run` handles timeout natively |
| Status | Original, used by tests | Debug/improved version, not tested |

`code_derivs.py` and `maxima_tools.py` (formerly `tools.py`) are identical except for the added module docstring.

## 8. Options for resolution

### Option A: Complete the reorganization

Finish `pyCruncher2/` as originally planned:
1. Create `pyCruncher2/__init__.py` and all missing `__init__.py` files.
2. Create `pyCruncher2/agents/` — move/copy agent classes from `pyCruncher/`.
3. Create `pyCruncher2/knowledge/` — move/copy paper pipeline modules.
4. Create `pyCruncher2/utils/` — move/copy utility modules.
5. Create `pyCruncher2/analysis/` — move/copy code analysis modules.
6. Add library functions to `gpu/cuda.py` and `gpu/opencl.py` (extract from smoke tests).
7. Add `MaximaSession` class to `cas/maxima.py`.
8. Update all `tests/` to import from `pyCruncher2/`.
9. Deprecate `pyCruncher/` or make it a thin compatibility shim.

**Pros**: Clean package structure, proper separation of concerns.
**Cons**: Large effort, high risk of breaking tests, no immediate user benefit.

### Option B: Abandon pyCruncher2/, fix examples

Accept that `pyCruncher/` is the library. Fix the broken examples to import from `pyCruncher/` instead. Move the unique `pyCruncher2/scientific/` files (elements, plotUtils, GPU code) into `pyCruncher/` or a separate `scientific/` directory.

**Pros**: Minimal effort, fixes all broken examples, eliminates confusion.
**Cons**: Loses the cleaner package structure dream.

### Option C: Keep as-is, document the gap

Leave both directories. Document that `pyCruncher2/` is an incomplete reorganization. Fix only the broken examples by adding `sys.path` hacks or conditional imports.

**Pros**: No code movement, no risk.
**Cons**: Confusing for anyone new to the repo, broken examples remain broken.

### Recommendation

**Option B** is the most pragmatic. The reorganization was started but abandoned — the cost of completing it outweighs the benefit for a single-user research codebase. The unique files in `pyCruncher2/scientific/` (elements, plotUtils, OpenCLBase, clUtils, GPU examples) should be preserved, but the duplicate CAS files should be consolidated back to `pyCruncher/` (keeping the improved `subprocess.run` version from `pyCruncher2/`).

# AutoCrunchCoder

AutoCrunchCoder is a sophisticated, AI-driven framework for scientific software development, with a special focus on computational chemistry and physics. It leverages Large Language Models (LLMs) to automate and assist in the complex workflow of scientific research, from mathematical derivation to numerical simulation and visualization.

## Core Philosophy

The project aims to streamline the development of number-crunching scientific code by combining:
- **AI-Augmented Development**: Using LLMs for code generation, analysis, and refactoring.
- **Symbolic Mathematics**: Integrating with Computer Algebra Systems (CAS) like Maxima to derive and simplify equations.
- **High-Performance Computing**: Generating and analyzing C++ and Python code for performance-critical simulations, including GPU support with OpenCL/CUDA.
- **End-to-End Workflow**: Supporting the entire research pipeline, from literature analysis (RAG) to final visualization.

## Navigation

- **[CODEMAP.md](CODEMAP.md)** — full repository structure with per-file role descriptions
- **[FeatureChecklist.md](FeatureChecklist.md)** — feature status tracker (implemented / WIP / planned)
- **[AGENTS.md](AGENTS.md)** — guidelines for AI agents working in this repo
- **[docs/topical_audit/](docs/topical_audit/)** — four work-stream deep dives:
  1. [Literature, PDF & reference management](docs/topical_audit/01_literature_pdf_and_reference_management.md)
  2. [Local LLMs & API integration](docs/topical_audit/02_local_llms_and_api_integration.md)
  3. [Codebase processing & review](docs/topical_audit/03_codebase_processing_and_review.md)
  4. [Scientific computation, math & visualization](docs/topical_audit/04_scientific_computation_math_and_visualization.md)

## Implemented Features

- **Multi-LLM Agent System**: A flexible agent system (`pyCruncher/`) supporting OpenAI, Google, DeepSeek, Anthropic, Groq, OpenRouter, LM Studio, and Ollama — all behind a uniform `Agent` base class.
- **Tool-Use Framework**: Auto-generate OpenAI/Gemini tool schemas from Python function signatures via `ToolScheme.schema()`; math tools use Maxima + SymPy + NumPy for symbolic/numerical verification.
- **Codebase Analysis**: Static analysis for C++ and Python using tree-sitter + ctags (dual parser). Generates file skeletons, dependency/call graphs, folder stats, and LLM-assisted summaries — all written non-destructively to `.shadow/`.
- **Automated Documentation**: Doxygen-style (`CodeDocumenter.py`) and Markdown (`CodeDocumenter_md.py`) documentation generation from source code analysis.
- **PDF & Literature Pipeline**: Ingest scientific PDFs via docling / local VLM / pdfminer, extract equations and DOIs, fill metadata from CrossRef/BibTeX, chunk and summarize with LLMs, store in SQLite with full-text search, and build a typed knowledge graph.
- **RAG & Knowledge Graph**: ChromaDB ingestion, RAG retrieval experiments, and knowledge-graph tagging of papers by scientific domain, math class, solver, and data structure.
- **Symbolic Math Integration**: Maxima CAS wrapper for symbolic differentiation, integration, and simplification — used to derive and verify force-field expressions.
- **Force-Field Code Generation**: Prompt templates (`prompts/ImplementPotential/`) for LLM-driven force-field implementation, with automatic formula verification via `check_formulas()` and FLOP counting.
- **Scientific Computing Backend**: Header-only C++ vector classes (`Vec3`/`Vec4`/`Vec2`) and inline force-field evaluators (Coulomb, LJ, LJQ) with parameter derivatives.
- **GPU Computing**: OpenCL orchestration layer (`OpenCLBase.py`) with device selection, kernel loading, and examples for N-body, Biot-Savart integration, and non-bonded scans. CUDA N-body example also included.
- **3D Molecule Viewer**: Web-based Three.js renderer (`molecule_renderer/`) for visualizing atomic configurations and bonds — standalone, no Python dependency.
- **MCP Integration**: Model Context Protocol servers for chemistry, LAMMPS, and Maxima, with corresponding client examples.
- **IDE Integration**: A VS Code extension (`prokop-bot/`) to interact with the framework directly from the editor.
- **Git History Analysis**: Convert git commits to markdown summaries for multi-model benchmarking.

## Directory Structure

*   **`pyCruncher/`**: The core Python library containing the agent system, code analyzers, and integrations with scientific tools.
*   **`cpp/`**: C++ source code for high-performance scientific calculations (e.g., `ForceFields.cpp`).
*   **`tests/`**: A large collection of scripts for experimenting, testing, and demonstrating various features of the framework.
*   **`examples/`**: A curated set of examples showcasing different capabilities like agent usage, code analysis, and scientific computing.
*   **`doc/` & `docs/`**: Extensive documentation covering project goals, architecture, tool integrations, and tutorials.
*   **`molecule_renderer/`**: A web-based 3D molecule viewer.
*   **`prokop-bot/`**: A VS Code extension for IDE integration.
*   **`Maxima/`**: Scripts and functions for the Maxima Computer Algebra System.

## Installation & Usage

1.  **Set up a Python environment**: It is recommended to use a virtual environment.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up API Keys**: Configure your LLM API keys as environment variables (e.g., `OPENAI_API_KEY`, `GOOGLE_API_KEY`) or add them to a `providers.key` file (see `config/LLMs.toml` for details).
4.  **Explore**: Run scripts from the `tests/` or `examples/` directories to see the framework in action.
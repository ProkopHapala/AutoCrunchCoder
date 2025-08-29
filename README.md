# AutoCrunchCoder

AutoCrunchCoder is a sophisticated, AI-driven framework for scientific software development, with a special focus on computational chemistry and physics. It leverages Large Language Models (LLMs) to automate and assist in the complex workflow of scientific research, from mathematical derivation to numerical simulation and visualization.

## Core Philosophy

The project aims to streamline the development of number-crunching scientific code by combining:
- **AI-Augmented Development**: Using LLMs for code generation, analysis, and refactoring.
- **Symbolic Mathematics**: Integrating with Computer Algebra Systems (CAS) like Maxima to derive and simplify equations.
- **High-Performance Computing**: Generating and analyzing C++ and Python code for performance-critical simulations, including GPU support with OpenCL/CUDA.
- **End-to-End Workflow**: Supporting the entire research pipeline, from literature analysis (RAG) to final visualization.

## Implemented Features

- **Multi-LLM Agent System**: A flexible agent system (`pyCruncher/`) that supports multiple LLM providers, including OpenAI, Google, DeepSeek, and Anthropic.
- **Tool-Use Framework**: Robust support for function calling, allowing LLMs to use custom Python functions to perform tasks.
- **Code Analysis**: Static analysis capabilities for both C++ and Python using `tree-sitter` and `ctags` to understand code structure and dependencies.
- **Symbolic Math Integration**: A dedicated module for interacting with the Maxima CAS to perform symbolic differentiation, integration, and simplification.
- **Scientific Computing Backend**: C++ code for performance-critical tasks like force field calculations and N-body simulations, with examples for OpenCL and CUDA.
- **Retrieval-Augmented Generation (RAG)**: Scripts and examples for using RAG with vector stores like ChromaDB and FAISS to query codebase knowledge.
- **3D Molecule Viewer**: A web-based molecule renderer (`molecule_renderer/`) to visualize simulation outputs.
- **IDE Integration**: A VS Code extension (`prokop-bot/`) to interact with the framework directly from the editor.

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
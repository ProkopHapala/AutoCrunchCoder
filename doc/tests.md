# Tests in ./tests Directory

## LLM Integration and Usage
These scripts demonstrate how to interact with various LLMs (Large Language Models) and their APIs.

### DeepSeek Integration
- **test_DeepSeek.py**: Tests the functionality of the `AgentDeepSeek` class by sending a prompt to DeepSeek's agent.
- **test_DeepSeek_FIM.py**: Uses the FIM (Function Inversion Method) completion feature of the `AgentDeepSeek` class to complete a C++ function for calculating the Lennard-Jones potential.
- **test_DeepSeek_JSON.py**: Tests the functionality of the `AgentDeepSeek` class by sending a prompt and expecting a JSON-formatted response.
- **test_DeepSeek_Tools.py**: Uses a custom tool named `symbolic_derivative` to compute the derivative of the Lennard-Jones potential using DeepSeek's agent.

### Google AI Integration
- **test_GoogleAI.py**: Tests the functionality of the `AgentGoogle` class from the `pyCruncher` library by using a series of unit tests. These tests verify the agent's ability to generate code, stream responses, use tools, manage conversation history, handle errors, and set system prompts.
- **test_GoogleAI_Tools.py**: Tests the functionality of the `AgentGoogle` class by registering and using a custom tool (`symbolic_derivative`) to compute the derivative of the Lennard-Jones potential, ensuring the agent can effectively utilize external tools.

### Hugging Face Integration
- **huggingface_client.py**: Demonstrates how to use Hugging Face InferenceClient to generate text.

### LM Studio Integration
- **LMstudio_agents.py**: Demonstrates how to use LM Studio agents for coding, planning, critiquing, and mathematician tasks.
- **LMstudio_client.py**: Provides a simple client for interacting with LM Studio's API.
- **LMstudio_simple.py**: Generates C/C++ code for evaluating energy and force in an n-body system using the Lennard-Jones + Coulomb potential.

## Retrieval-Augmented Generation (RAG)
These scripts demonstrate the use of RAG with different models and vector stores.

- **RAG_retrival_DeepSeek.py**: Demonstrates RAG with DeepSeek, loading a FAISS index of code embeddings to answer questions about the codebase.
- **RAG_retrival_GeminiFlash_chroma.py**: Uses Gemini Flash and Chroma for RAG, retrieving relevant code chunks from a Chroma database to answer questions.
- **RAG_retrival_GeminiFlash.py**: Another implementation of RAG using Gemini Flash with a FAISS index instead of Chroma.

## Document Processing and Summarization
These scripts focus on processing documents, summarizing content, and generating documentation.

- **ingest_langchain_ollama.py**: Uses LangChain and Ollama to create embeddings for documents and store them in a Chroma database, demonstrating RAG.
- **ingest_langchain.py**: Similar to `ingest_langchain_ollama.py`, but uses HuggingFaceEmbeddings and stores the embeddings in a FAISS index.
- **test_bibtex.py**: Processes BibTeX entries and classifies research articles based on their titles and abstracts, summarizing the key insights and defining keywords or research areas.
- **test_bibtex2.py**: Loads a BibTeX file, extracts titles and abstracts, modifies an entry, and exports the modified entries to a new BibTeX file.
- **test_GitToMarkdown.py**: Processes Git commit messages and generates summaries of the commits in Markdown format.

## Code Analysis and Dependency Graph
These scripts analyze code and extract dependencies between functions, methods, and classes.

- **test_agent_analysis.py**: Tests the agent hierarchy within the `pyCruncher` library, analyzing inheritance relationships between agent classes using `tree-sitter`.

### C++
- **test_cpp_file_analysis.py**: Tests the `pyCruncher/scoped_cpp.py` which extract function (and method) headers within classes and other scopes in C++ code using just regex.
- **test_cpp_type_analyzer.py**: Tests the `cpp_type_analyzer` module, which uses `tree-sitter` to parse C++ code and extract type information.
- **test_dependency_graph.py**: Tests the `ctags_dependency` module, which analyzes dependencies in both Python and C++ code using `ctags`.
- **test_dependency_graph_tree_sitter.py**: Tests the `dependency_graph_tree_sitter` module, which uses `tree-sitter` to parse C++ code and extract dependencies.
- **test_dependency_graph_tree_sitter_deps.py**: Tests the `dependency_graph_tree_sitter` module, focusing on finding dependencies of a C++ file and parsing a file with all its dependencies.
- **test_tree_sitter.py**: Uses `tree-sitter` to parse C++ code and generate Markdown documentation for classes, methods, and properties.

### Python

- **test_python_imports.py**: Tests the handling of imports in Python code using `tree-sitter`, verifying that the `TypeCollector` class correctly tracks imports and resolves function calls.
- **test_python_type_analyzer.py**: Tests the `python_type_analyzer` module, which uses `tree-sitter` to parse Python code and extract type information.

## Code Generation and Error Testing
These scripts focus on generating code and testing for errors.

- **test_GenerateErrorCode.py**: Generates subtle error examples in C/C++ code for educational purposes, focusing on common pitfalls such as boundary conditions and uninitialized variables.
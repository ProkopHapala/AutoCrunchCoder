# 2. Local LLMs & API Integration

## What this topic does

Provide one uniform Python class for talking to many different LLM providers and local inference servers. It also lets the models call Python helper functions (tool-use) and exposes the framework through MCP servers and a VS Code extension.

## Main challenges and how they are solved

- **Many providers, many message formats**: an abstract `Agent` base class defines a common interface (`query`, `stream`, `get_response_text`, `extract_tool_call`). Each provider subclasses it and translates to its native SDK.
- **Keys and base URLs scattered everywhere**: `config/LLMs.toml` stores model profiles; `Agent.load_template()` reads them and resolves the API key from an environment variable first, then a `providers.key` TOML file.
- **Tool calling requires JSON schemas**: `ToolScheme.schema()` builds an OpenAI/Gemini-style function schema automatically from a Python function signature and docstring.
- **Local vs remote**: because `AgentOpenAI` uses the standard `openai` client with a configurable `base_url`, the same code works for OpenAI, Groq, OpenRouter, LM Studio, and Ollama.

## Core files and their essence

### `pyCruncher/Agent.py`

Base class for all agents.

- `load_template()` — load the selected model profile from `config/LLMs.toml`.
- `get_api_key()` — look up the API key from env var or `providers.key`.
- `try_tool()` — detect tool calls in a model response and run the registered Python callback.
- Abstract methods `setup_client()`, `query()`, `stream()`, `get_response_text()`, `extract_tool_call()`.

### `pyCruncher/AgentOpenAI.py`

OpenAI-compatible implementation. Covers OpenAI, Groq, OpenRouter, LM Studio, Ollama, and any other OpenAI-style endpoint.

- `setup_client()` — create `OpenAI(api_key=..., base_url=...)`.
- `query()` — chat completion with optional tools and conversation history (`bHistory`, `bTools`).
- `stream()` — streaming completion with history.
- `extract_tool_call()` — returns `message.tool_calls` for the base class to dispatch.

### `pyCruncher/AgentDeepSeek.py`

DeepSeek-specific extras, inherits from `AgentOpenAI`.

- `fim_completion()` — fill-in-the-middle completion for coder models.
- `query_json()` / `stream_json()` — force JSON-object output and parse it.
- It also imports math tools from `pyCruncher/tools.py` for numerical checks.

### `pyCruncher/AgentGoogle.py`

Google Gemini implementation.

- `setup_client()` — `genai.configure(api_key=...)` then `GenerativeModel(model)`.
- `query()` / `stream()` — `generate_content` with optional `tools`, `generation_config`, history.
- `get_response_text()` — reads `message.text`.

### `pyCruncher/AgentAnthropic.py`

Anthropic Claude implementation (basic version).

- `setup_client()`, `query()`, `stream()` around the `anthropic` Messages API.
- Tool calling is not fully wired yet, but the base interface is there.

### `pyCruncher/ToolScheme.py`

Turn Python functions into LLM-callable tool schemas.

- `schema(function, bOnlyRequired=False)` — introspect signature and type annotations; parse the docstring for parameter descriptions; emit an OpenAI-style `function` schema.
- `parse_docstring()` — extract function description and `name: description` parameter lines.

### `pyCruncher/tools.py`

Actual tool implementations that agents can call for math/scientific checks.

- `symbolic_derivative()` — compute a derivative through Maxima.
- `compute_numerical_derivative()` — finite-difference check.
- `compute_integral()` — definite integral via Maxima.
- `compute_expression_steps()` — evaluate a list of named sub-expressions.
- `check_numerical_vs_analytical_derivative()` — compare SymPy analytical derivative with a NumPy finite-difference value.

### `config/LLMs.toml`

Provider registry: model name, base URL, API-key environment variable, context length, etc.

### MCP and IDE integration

- `examples/MCP/mcp_server_*.py` / `mcp_client_*.py` — Model Context Protocol servers for chemistry, LAMMPS, and Maxima; clients showing how an LLM consumes them.
- `prokop-bot/src/extension.ts` — VS Code extension entry; `webview.ts` / `treeDataProvider.ts` provide the UI; `script.py` / `script_agent.py` are Python helpers invoked by the extension.
- `doc/LLMs.md`, `doc/MCP_*.md`, `doc/ollama_from_LMstudio.md` — design and setup notes.

### Tests

- `tests/test_LLM_Agent.py`, `test_GoogleAI.py`, `test_Groq.py`, `test_DeepSeek*.py`, `test_LMstutio.py`, `LMstudio_*.py`, `huggingface_client.py` — one-off connectivity/functionality tests.

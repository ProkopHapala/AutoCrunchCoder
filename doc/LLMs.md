# LLM Agent System in AutoCrunchCoder

This document describes the design and usage of the LLM agent system within the AutoCrunchCoder project, located in the `pyCruncher/` directory.

## 1. Core Agent Architecture

The agent system is built around a central abstract base class, `Agent`, which defines a common interface for interacting with various Large Language Models (LLMs).

### `Agent` (pyCruncher/Agent.py)

This abstract class provides the foundational structure for all specific agent implementations.

**Key Responsibilities:**
- **Configuration Loading**: Loads model configurations, API keys, and base URLs from `config/LLMs.toml`. It standardizes how different models are set up.
- **History Management**: Maintains a conversation history (`self.history`) and includes a mechanism to trim it to stay within the model's context window.
- **Tool Registration**: Provides a generic framework for registering custom functions (`tools`) that the LLM can call. The `register_tool` method uses `ToolScheme.py` to generate a JSON schema for the function, which is then provided to the model.
- **Abstract Methods**: Defines the core interface that all subclasses must implement:
    - `setup_client()`: Initializes the specific LLM provider's client.
    - `query()`: Sends a query to the model.
    - `stream()`: Streams a response from the model.
    - `get_response_text()`: Extracts the text content from a model's response.
    - `extract_tool_call()`: Parses a model's response to find and extract any tool/function calls.

## 2. Provider-Specific Implementations

These classes inherit from `Agent` and implement the provider-specific logic for API interaction.

### `AgentOpenAI` (pyCruncher/AgentOpenAI.py)

- **Provider**: OpenAI (and compatible APIs like Groq, OpenRouter).
- **Client**: Uses the `openai` Python library.
- **Features**:
    - Implements `query` and `stream` methods for standard chat completions.
    - Handles OpenAI's specific format for `tool_calls`.
    - Serves as a base class for other OpenAI-compatible agents like `AgentDeepSeek`.

### `AgentDeepSeek` (pyCruncher/AgentDeepSeek.py)

- **Provider**: DeepSeek.
- **Inherits from**: `AgentOpenAI`.
- **Client**: Uses the `openai` library, as DeepSeek's API is OpenAI-compatible.
- **Special Features**:
    - `fim_completion()`: Implements "Fill In the Middle" completion, a feature specific to some coder models.
    - `query_json()`: A convenience method to enforce JSON output from the model.

### `AgentGoogle` (pyCruncher/AgentGoogle.py)

- **Provider**: Google (Gemini models).
- **Client**: Uses the `google-generativeai` Python library.
- **Features**:
    - Implements the standard `query` and `stream` methods using the Gemini API.
    - `register_tool` is adapted to create `FunctionDeclaration` objects, which is the format Google's API expects for tools.
    - `extract_tool_call` is implemented to parse tool calls from the Gemini response format.

### `AgentAnthropic` (pyCruncher/AgentAnthropic.py)

- **Provider**: Anthropic (Claude models).
- **Client**: Uses the `anthropic` Python library.
- **Features**:
    - Implements `query` and `stream` for the Anthropic Messages API.
    - **Note**: As of the current implementation, tool/function calling is not fully implemented for the Anthropic agent in this module, though the base class structure supports it.

## 3. How to Use the Agents

1.  **Configuration**: Add a new model profile to `config/LLMs.toml`. Define its `model_name`, `api_key_var` (the environment variable for the API key), and `base_url`.
2.  **Instantiation**: Create an instance of the desired agent class, passing the template name from the TOML file.
    ```python
    from pyCruncher.AgentDeepSeek import AgentDeepSeek

    # Assumes a "deepseek-coder" template exists in LLMs.toml
    agent = AgentDeepSeek(template_name="deepseek-coder")
    ```
3.  **Registering Tools**: Define a Python function and register it with the agent.
    ```python
    def get_current_weather(location: str, unit: str = "Celsius"):
        """Gets the current weather in a given location."""
        # ... implementation ...
        return f"The weather in {location} is 25 degrees {unit}."

    agent.register_tool(get_current_weather)
    ```
4.  **Querying the Model**: Call the `query` method. If the prompt triggers a tool, the agent will handle the call and return the final response.
    ```python
    prompt = "What is the weather like in San Francisco?"
    response_message = agent.query(prompt)
    print(agent.get_response_text(response_message))
    ```

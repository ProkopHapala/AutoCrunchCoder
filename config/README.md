# config

Configuration files for the AutoCrunchCoder framework. This is the single source of truth (SSOT) for provider/model profiles.

## Files

- `LLMs.toml` — Provider/model registry: model name, base URL, API-key environment variable name, context length, and optional `providers.key` for file-based key storage. Read by `Agent.load_template()` to configure each agent instance. One entry per model template (e.g. `deepseek-coder`, `gemini-1.5-pro`, `lmstudio-local`).

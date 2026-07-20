# prokop-bot

VS Code extension for AutoCrunchCoder — provides a chat UI inside VS Code that connects to the `pyCruncher/` agent system. Users can select a model profile from `config/LLMs.toml`, send prompts, and view streaming responses in a webview panel.

## Features

- Chat with any configured LLM agent (DeepSeek, Gemini, OpenAI, LM Studio, etc.) directly from VS Code
- Model selection via `config/LLMs.toml` profiles
- Streaming response display in a webview panel
- Tree view of agent sessions and conversation history
- Python helper scripts bridge TypeScript → `pyCruncher/Agent*.py`

## Build & Package

```bash
npm install
npm run compile
# Package as .vsix:
npx vsce package
```

## Project Structure

- `src/extension.ts` — Extension entry point
- `src/webview.ts` — Webview chat panel
- `src/treeDataProvider.ts` — Session tree view
- `src/script.py` / `script_agent.py` — Python helpers invoked by the extension

See `src/README.md` for source-level details.

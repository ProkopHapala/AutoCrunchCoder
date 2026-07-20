# prokop-bot/src

TypeScript source code for the `prokop-bot` VS Code extension. The extension provides a chat UI inside VS Code that connects to local or remote LLM agents and displays responses in a webview panel.

## Files

- `extension.ts` — Extension entry point: registers commands, views, and Python script invocations. Activates the agent system when the extension loads.
- `webview.ts` — Webview panel implementation: chat UI, model selection, streaming response display.
- `treeDataProvider.ts` — Tree view data provider for agent sessions and conversation history.
- `script.py` — Helper Python script invoked by the extension to run agents locally (bridges TypeScript → Python agent system).
- `script_agent.py` — Agent helper script with more advanced agent configuration.
- `test/extension.test.ts` — Extension unit tests.

See `../README.md` for build and package instructions.

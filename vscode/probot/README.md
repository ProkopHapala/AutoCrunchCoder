# Probot Context (VS Code / Windsurf / Antigravity)

A minimal JavaScript (no TypeScript) extension that lets you:

- Right-click any `.md` file → **Set as Context Buffer** (remembered per workspace).
- Right-click a file in the explorer → **Add to Context Buffer** (captures whole file).
- Right-click a selection in the editor → **Add to Context Buffer** (captures only the selection).

The captured snippet is appended to the buffer in this format:

```
## <file name>
[from line, char]:[to line, char]

```<language>
<content>
```
```

## Project Structure

```
vscode/probot/
├── extension.js      # Extension logic (CommonJS)
├── package.json      # Contribution points + metadata
└── .vscodeignore     # Packaging ignore list
```

## Local Development

1. Open `vscode/probot` in VS Code.
2. Press **F5** to launch the **Extension Development Host**.
3. In that window:
   - Create or choose a Markdown file (e.g., `context.md`).
   - Right-click it → **Set as Context Buffer**.
   - Open any file, select code, right-click → **Add to Context Buffer**.
   - Or right-click a file in the explorer → **Add to Context Buffer**.
4. Inspect the buffer file to verify appended snippets.

## Packaging a VSIX

Requires Node.js and `@vscode/vsce`:

```bash
npm install -g @vscode/vsce
vsce package
```

This produces `probot-context-<version>.vsix` in the folder.

## Installing from VSIX

- **VS Code / Windsurf / Antigravity**: Extensions panel → `...` menu → **Install from VSIX...** → select the file.

## Publishing (optional)

- **Open VSX**: create an account/namespace, generate a token, then `npm install -g ovsx` and `ovsx publish`.
- **VS Code Marketplace**: requires Azure DevOps publisher setup; follow `vsce publish` docs.

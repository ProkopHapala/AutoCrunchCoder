## USER 1

I want to make simple extension to VS Code, Windsurf and Antigravity which basically add context menu to right mouse button. When you right click on file in explorer, or when you select block of code and right click, it will add option "add to context" and paste this into code block into selected file which is actually selected as context buffer (i.e. context buffer is some .md file with a given name). An other context menu command will be "set file as context buffer"

Now the files or blocks should be added into context buffer file within code blocs, like this

## [file name]
[from line, char]:[to line, char]

```[language]
[clipboard]
```

where the params [file name], [language] and [from line, char]:[to line, char] are automatically determined

The purpose of this should be to assemble source code files for "human router" when using LLMs

let me know if you understant?

if yes, please tell me how to create vscode extension (I want to use simple javascript not typescript, because typescript need compilation and it is overcomplicated ), how should look like the template for vscode extension, and how can i publish it in opesource extensions used by windsurf and antigravity

---

## Gemini

Yes, I understand completely. You are building a **"Context Aggregator"** to manually curate code snippets into a single Markdown file. This is a very common workflow when preparing a prompt for an LLM (Large Language Model) to ensure it has exactly the context it needs without sending the whole codebase.

Here is the guide to building this using **Plain JavaScript** (CommonJS), skipping TypeScript to keep it simple and compile-free.

### Step 1: Create the Project Structure

Create a new folder named `human-router-context` (or whatever you like) and inside it, you only need two main files to start.

Structure:
```text
human-router-context/
├── extension.js       // The logic
├── package.json       // The configuration and menu definitions
└── .vscodeignore      // (Optional) Files to ignore when packaging
```

### Step 2: The `package.json`

This file tells VS Code (and Windsurf/Antigravity) where to put the "Right Click" buttons.

Create `package.json` and paste this:

```json
{
  "name": "human-router-context",
  "displayName": "Human Router Context",
  "description": "Right click to add files or code blocks to a context buffer Markdown file.",
  "version": "0.0.1",
  "engines": {
    "vscode": "^1.75.0"
  },
  "categories": [
    "Other"
  ],
  "activationEvents": [
    "onStartupFinished"
  ],
  "main": "./extension.js",
  "contributes": {
    "commands": [
      {
        "command": "hrc.setContextBuffer",
        "title": "Set as Context Buffer"
      },
      {
        "command": "hrc.addToContext",
        "title": "Add to Context Buffer"
      }
    ],
    "menus": {
      "explorer/context": [
        {
          "command": "hrc.setContextBuffer",
          "group": "7_modification",
          "when": "resourceExtname == .md"
        },
        {
          "command": "hrc.addToContext",
          "group": "7_modification",
          "when": "resourceScheme == file"
        }
      ],
      "editor/context": [
        {
          "command": "hrc.addToContext",
          "group": "navigation",
          "when": "editorHasSelection"
        }
      ]
    }
  }
}
```

### Step 3: The `extension.js`

This is the logic. It uses standard Node.js `fs` (file system) to append text to your file.

Create `extension.js` and paste this:

```javascript
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    // 1. Command: Set the target file (Context Buffer)
    let setBufferDisposable = vscode.commands.registerCommand('hrc.setContextBuffer', async (uri) => {
        if (uri && uri.fsPath) {
            // Save the path to Workspace State so it remembers it for this project
            await context.workspaceState.update('contextBufferPath', uri.fsPath);
            vscode.window.showInformationMessage(`Context Buffer set to: ${path.basename(uri.fsPath)}`);
        } else {
            vscode.window.showErrorMessage("Please right-click a valid .md file in the explorer.");
        }
    });

    // 2. Command: Add to Context (Works for Files AND Selected Text)
    let addToContextDisposable = vscode.commands.registerCommand('hrc.addToContext', async (uri) => {
        
        // Retrieve the stored Context Buffer path
        const bufferPath = context.workspaceState.get('contextBufferPath');
        if (!bufferPath) {
            vscode.window.showErrorMessage("No Context Buffer set! Right-click a .md file and select 'Set as Context Buffer' first.");
            return;
        }

        const editor = vscode.window.activeTextEditor;
        let contentToAppend = "";
        
        // SCENARIO A: Triggered from Editor Text Selection
        // (If there is an active editor AND the command wasn't triggered specifically on a file in explorer different from the open one, 
        // OR if the uri passed is effectively the same as the document)
        if (editor && editor.selection && !editor.selection.isEmpty) {
            
            const doc = editor.document;
            const selection = editor.selection;
            const text = doc.getText(selection);
            
            // Calculate coords (human readable, so +1 for lines)
            const fileName = path.basename(doc.fileName);
            const startLine = selection.start.line + 1;
            const startChar = selection.start.character;
            const endLine = selection.end.line + 1;
            const endChar = selection.end.character;
            const lang = doc.languageId;

            contentToAppend = `\n## ${fileName}\n[${startLine}, ${startChar}]:[${endLine}, ${endChar}]\n\n\`\`\`${lang}\n${text}\n\`\`\`\n`;
        } 
        
        // SCENARIO B: Triggered from File Explorer (Whole File)
        else if (uri && uri.fsPath) {
            try {
                const doc = await vscode.workspace.openTextDocument(uri);
                const fileName = path.basename(uri.fsPath);
                const lang = doc.languageId;
                const text = doc.getText();
                // For whole files, we usually denote start to end
                const lineCount = doc.lineCount;

                contentToAppend = `\n## ${fileName}\n[1, 0]:[${lineCount}, 0]\n\n\`\`\`${lang}\n${text}\n\`\`\`\n`;
            } catch (err) {
                vscode.window.showErrorMessage(`Error reading file: ${err.message}`);
                return;
            }
        } else {
            vscode.window.showWarningMessage("Please select some text or right-click a file.");
            return;
        }

        // Perform the Append Operation
        try {
            fs.appendFileSync(bufferPath, contentToAppend);
            vscode.window.setStatusBarMessage(`Added to context: ${path.basename(bufferPath)}`, 3000);
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to write to context buffer: ${err.message}`);
        }
    });

    context.subscriptions.push(setBufferDisposable);
    context.subscriptions.push(addToContextDisposable);
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
```

### Step 4: How to Test locally

1.  Open VS Code.
2.  Open the `human-router-context` folder you created.
3.  Press **F5**. This will open a new window called "Extension Development Host".
4.  In that new window:
    *   Create a file `context.md`.
    *   Right-click `context.md` -> **Set as Context Buffer**.
    *   Open a code file, select text, right-click -> **Add to Context Buffer**.
    *   Check `context.md` to see if it worked.

### Step 5: How to Package and Install (Windsurf, Antigravity, VS Code)

Since you want to use this in Windsurf (Codeium) and Antigravity (assuming you mean a fork or Cursor-like editor), you usually don't need to publish this to the public marketplace if it's just for you or your team. You can create a **.vsix** file.

**1. Install vsce (VS Code Extensions tool)**
You need Node.js installed on your computer. Open your terminal:
```bash
npm install -g @vscode/vsce
```

**2. Package the extension**
In your `human-router-context` folder, run:
```bash
vsce package
```
*Note: If it complains about missing "repository" field in package.json, just add `"repository": {"type": "git", "url": "https://github.com/placeholder"},` or answer "Yes" to continue without it.*

This will generate a file like `human-router-context-0.0.1.vsix`.

**3. Install in Windsurf / Antigravity**

*   **Windsurf:** Open Windsurf -> Extensions Panel (Ctrl+Shift+X) -> Click the "..." (Views and More actions) menu at the top right of the panel -> **Install from VSIX...** -> Select your file.
*   **VS Code / Others:** Same process.

### Step 6: Publishing to Open Source Registries (Optional)

If you want to publish this so anyone can download it without the `.vsix` file:

1.  **VS Code Marketplace:** This is strictly controlled by Microsoft. You need an Azure DevOps account.
2.  **Open VSX (The Open Source Alternative):** This is the registry used by VSCodium and many forks.
    *   Go to [open-vsx.org](https://open-vsx.org/).
    *   Create an account (GitHub login).
    *   Create a namespace.
    *   Get an Access Token.
    *   Run: `ovsx publish` (requires installing `npm install -g ovsx`).

**Recommendation:** For a personal utility like this, sticking to the **.vsix** method (Step 5) is significantly faster and requires no accounts or maintenance.

---

## Probot (final implementation notes, install & test, pitfalls)

Location: `vscode/probot`  
Built VSIX: `probot-context-0.0.1.vsix` (packaged locally, no marketplace needed)

### What it does (current behavior)
- Context buffer is a chosen Markdown file (set via context menu).
- Add to Context works from:
  - Explorer (whole file)
  - Tab context (whole file)
  - Editor context (selection → range; no selection → whole file)
- Captured block format:
  - `## <filename>`
  - `path: <relative path>`
  - `range: Lx:Cy-Lz:Cw` or `(whole file)`
  - fenced code block with language (Fortran normalized to `fortran`)
  - `---` separator
- Automatic TOC:
  - Maintains `## Table of Contents` at top.
  - Adds a list item linking to each block via an anchor placed before the block header.
  - Anchor slug is derived from relative path/filename.

### How to run locally for testing
1) Open folder `vscode/probot` in VS Code.  
2) Press **F5** (Run Extension) → opens **Extension Development Host** window (use that window for testing, not the one with debug controls).  
3) In the dev-host window:
   - Create/choose a Markdown buffer (e.g., `context.md`), right-click → **ProBot: set as Output**.
   - Add code:
     - Right-click selection in editor → **ProBot: to Context** (captures selection; trims blank lines).
     - Right-click editor with no selection → captures whole file.
     - Right-click file in explorer or tab → captures whole file.
   - Check `context.md` for appended snippets and updated TOC.

### Packaging to VSIX (no account required)
```bash
cd /home/prokophapala/git/AutoCrunchCoder/vscode/probot
vsce package
```
Produces `probot-context-0.0.1.vsix`. Install in Windsurf/VS Code/Cursor via Extensions panel → `...` → **Install from VSIX...**.

### Publishing (optional)
- Open VSX requires an Eclipse Foundation account and signing their publisher agreement; if you don’t want an account, skip and use VSIX.
- VS Code Marketplace requires Azure DevOps publisher and PAT; not needed for local install.

### Pitfalls encountered
- **Missing repository/license warnings**: fixed by adding `repository` and `license` in `package.json` and adding `LICENSE`. Re-run `vsce package` to avoid prompts.
- **Extension window confusion**: The dev-host is a separate window from the debugger window; interact in the dev-host.
- **Language ID**: Fortran normalized to `fortran` for fenced code blocks.
- **Explorer vs editor selection**: Explorer/tab always captures whole file; editor with selection captures range; editor with no selection captures whole file.

# Task

I have this vscode-extension called prokop-bot that I use to chat with my AI assistant. I would like to make it more user-friendly and add some features that I think would be useful for my workflow.

I would like to implement several other features:

1) How to make side panel for the extension ? (similar as Cody, Continue, or Claude-dev has)
2) How to integrate keyboard shortcuts shortcuts ?
3) How to get filename of the file opened in the vscode tab ? 
4) How to make context menu for files in the Explorer side-panel ?

Please implement it for me.

# Context

## This is what Perplexity AI told me to do ([see](https://www.perplexity.ai/search/how-to-make-simple-vscode-exte-xO3dy..BT1emdXQGZOtxbw])):

Here’s how you can implement the features you mentioned for your VSCode extension:

### 1. Creating a Side Panel for the Extension

To create a side panel similar to those used by other extensions, you can use a **Webview**. Here’s how to do it:

- **Update `package.json`**:
  Add a view container and views to your `package.json`:

  ```json
  "viewsContainers": {
      "activitybar": [
          {
              "id": "myExtensionViewContainer",
              "title": "My Extension",
              "icon": "./assets/icon.png"
          }
      ]
  },
  "views": {
      "myExtensionViewContainer": [
          {
              "type": "webview",
              "id": "myWebview",
              "name": "My Webview"
          }
      ]
  }
  ```

- **Create a Webview Provider**:
  Implement a Webview provider in your `extension.ts`:

  ```typescript
  import * as vscode from 'vscode';

  class MyWebviewProvider implements vscode.WebviewViewProvider {
      constructor(private readonly context: vscode.ExtensionContext) {}

      resolveWebviewView(webviewView: vscode.WebviewView) {
          webviewView.webview.html = this.getHtmlForWebview();
      }

      private getHtmlForWebview() {
          return `<html><body><h1>Hello from the Webview!</h1></body></html>`;
      }
  }

  export function activate(context: vscode.ExtensionContext) {
      const provider = new MyWebviewProvider(context);
      context.subscriptions.push(
          vscode.window.registerWebviewViewProvider('myWebview', provider)
      );
  }
  ```

### 2. Integrating Keyboard Shortcuts

To add keyboard shortcuts to your extension, you can define them in your `package.json`:

```json
"contributes": {
    "keybindings": [
        {
            "command": "extension.yourCommandId",
            "key": "ctrl+k ctrl+y", // Replace with your desired shortcut
            "when": "editorTextFocus"
        }
    ]
}
```

### 3. Getting the Filename of the Opened File

You can easily get the filename of the currently opened file using the following code in your command:

```typescript
const editor = vscode.window.activeTextEditor;
if (editor) {
    const document = editor.document;
    const filename = document.fileName; // Full path
    const basename = path.basename(filename); // Just the filename
    console.log(`Current file: ${basename}`);
}
```

### 4. Creating a Context Menu for Files in the Explorer Side Panel

To add context menu items for files in the Explorer, you can define them in `package.json` under the `menus` section:

```json
"contributes": {
    "menus": {
        "explorer/context": [
            {
                "command": "extension.yourExplorerCommandId",
                "when": "resourceType == 'file'",
                "group": "navigation"
            }
        ]
    }
}
```

Then, register the command in your `extension.ts`:

```typescript
let disposableExplorerCommand = vscode.commands.registerCommand('extension.yourExplorerCommandId', (uri: vscode.Uri) => {
    // uri contains information about the file clicked in Explorer
    console.log(`File clicked: ${uri.fsPath}`);
});

context.subscriptions.push(disposableExplorerCommand);
```

### Summary

- **Side Panel**: Implemented using Webviews.
- **Keyboard Shortcuts**: Defined in `package.json`.
- **Filename Retrieval**: Accessed via `activeTextEditor`.
- **Context Menu**: Added for files in Explorer using `menus` in `package.json`.

By following these steps, you will be able to implement the desired features in your VSCode extension effectively. If you have further questions or need additional details on any of these topics, feel free to ask!

Citations:
[1] https://dev.to/estruyf/creating-a-vscode-extension-for-all-other-extensions-3pgi
[2] https://github.com/denyocrworld/vscode-extension-with-sidebar-webview
[3] https://www.reddit.com/r/vscode/comments/ldsv23/any_documentation_available_to_create_a_vs_code/
[4] https://code.visualstudio.com/docs/editor/custom-layout
[5] https://stackoverflow.com/questions/68759258/sidebar-panel-vscode-extension
[6] https://code.visualstudio.com/api/ux-guidelines/sidebars
[7] https://code.visualstudio.com/api/ux-guidelines/panel
[8] https://code.visualstudio.com/docs/editor/extension-marketplace


## This is current content of relevant files:

### package.json

/home/prokop/git/AutoCrunchCoder/prokop-bot/package.json

```JSON
{
  "name": "prokop-bot",
  "displayName": "Prokop_Bot",
  "description": "Provide utilities how to interact with code and text especially with help of LLMs (large language models) and especially in context of scientific programing and writing",
  "version": "0.0.1",
  "engines": {
    "vscode": "^1.94.0"
  },
  "categories": [
    "Other"
  ],
  "activationEvents": [],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
        {
            "command": "extension.encloseSelection",
            "title": "Prokop_Bot: [[Selection]]"
        },
        {
            "command": "extension.sendToPython",
            "title": "Prokop_Bot: python(Selection)"
        }
    ],
    "menus": {
      "editor/context": [
        {
            "command": "extension.encloseSelection",
            "when": "editorHasSelection",
            "group": "navigation"
        },
        {
            "command": "extension.sendToPython",
            "when": "editorHasSelection",
            "group": "navigation"
        }
      ]
    }
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "pretest": "npm run compile && npm run lint",
    "lint": "eslint src",
    "test": "vscode-test"
  },
  "devDependencies": {
    "@types/vscode": "^1.94.0",
    "@types/mocha": "^10.0.8",
    "@types/node": "20.x",
    "@typescript-eslint/eslint-plugin": "^8.7.0",
    "@typescript-eslint/parser": "^8.7.0",
    "eslint": "^9.11.1",
    "typescript": "^5.6.2",
    "@vscode/test-cli": "^0.0.10",
    "@vscode/test-electron": "^2.4.1"
  }
}
```

### extension.ts

in file : `/home/prokop/git/AutoCrunchCoder/prokop-bot/src/extension.ts`

```typescript
// Help With writing VScode extension
// https://www.perplexity.ai/search/how-to-make-simple-vscode-exte-xO3dy..BT1emdXQGZOtxbw


// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    console.log('Congratulations, your extension "prokop-bot" is now active!');
    console.log(`Current working directory: ${process.cwd()}`);

    // Register the command to enclose selection
    let disposableEnclose = vscode.commands.registerCommand('extension.encloseSelection', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            const selection = editor.selection;
            const selectedText = editor.document.getText(selection);
            const newText = `[[${selectedText}]]`; // Adjusted to double square brackets
            
            editor.edit(editBuilder => {
                editBuilder.replace(selection, newText);
            });
        }
    });


    // Command to send selected text to Python script
    let disposableSendToPython = vscode.commands.registerCommand('extension.sendToPython', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            const selection    = editor.selection;
            const selectedText = editor.document.getText(selection);
            

            // Adjust the path to your Python script
            //const pythonScriptPath = path.join(__dirname, 'script.py');

            const pythonScriptPath = path.join(__dirname, '..','src', 'script.py'); // Adjusted for out directory
            //const pythonScriptPath = '/path/to/your/script.py'; // Change this to your actual script path

            // Execute the Python script with the selected text as an argument
            exec(`python "${pythonScriptPath}" "${selectedText}"`, (error, stdout, stderr) => {
                if (error) {
                    console.error(`Error executing script: ${error.message}`);
                    return;
                }
                if (stderr) {
                    console.error(`Script error: ${stderr}`);
                    return;
                }
                // Output the result of the script
                console.log(`Output: ${stdout}`);
                vscode.window.showInformationMessage(`Output: ${stdout}`);
            });
        }
    });

    // Add both disposables to context subscriptions
    context.subscriptions.push(disposableEnclose);

}

// This method is called when your extension is deactivated
export function deactivate() {}
```

# Task

I have this vscode-extension called prokop-bot that I use to chat with my AI assistants. I would like to make it more user-friendly and add some features that I think would be useful for my workflow.

I would like to implement new feature called "Add to Markdown". The feature should take current selection from editor and add it to the markdown file `Prokobot_context.md`.
 - if such file does not exist, create it
 - if such file exists, append the selection to the end of the file
 - we should make another button which clean this file (or create new one)
 - each new addition should have H2 markdown header (e.g. like `## file: something.py ` )
 - It should be followed by a full path and start end end of the selection within the file (line number, character on the line)
 - The content of the selection should be enclosed in multiline code block.

 So it should look like something like this:

 ```Markdown
### file: extension.ts
path: /home/prokop/git/AutoCrunchCoder/prokop-bot/src/extension.ts
start line: 10 character: 5
end line: 12 character: 26
```typescript 
... content of the selection ...
```    
```

Maybe if you know about better format of line start and end, you can make it better. Ideally if it is some standard format, e.g. used by diff tools, or git, etc.

Please, implement it for me.

# Context

## This is current content of relevant files you should edit:

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
        },
        {
            "command": "prokopBot.explorerCommand",
            "title": "Prokop Bot: Run Python Tool"
        },
        {
            "command": "extension.addTabToList",
            "title": "Prokop_Bot: Add this tab to..."
        }
    ],
    "keybindings": [
        {
            "command": "extension.encloseSelection",
            "key": "ctrl+]",
            "when": "editorTextFocus"
        },
        {
            "command": "extension.sendToPython",
            "key": "ctrl+k ctrl+p",
            "when": "editorTextFocus"
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
      ],
      "explorer/context": [
        {
          "command": "prokopBot.explorerCommand",
          "when": "resourceLangId == python",
          "group": "navigation",
          "title": "Prokop Bot: Run Python Tool"
        }
      ],
      "tab/context": [
        {
          "command": "extension.addTabToList",
          "when": "editorFocus",
          "group": "navigation",
          "title": "Prokop_Bot: Add this tab to..."
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
    let disposable_encloseSelection = vscode.commands.registerCommand('extension.encloseSelection', () => {
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
let disposable_sendToPython = vscode.commands.registerCommand('extension.sendToPython', () => {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        const document = editor.document;
        const filePath = document.fileName;
        const fileName = path.basename(filePath);
        const languageId = document.languageId; // Get the programming 

        // Get cursor position
        const cursorPosition = editor.selection.active;   // This gives you the current cursor position
        const cursorLine = cursorPosition.line;           // Line number of the cursor
        const cursorCharacter = cursorPosition.character; // Character position in the line

        // Get selection start and end positions
        const selectionStart = selection.start;   // Start position of the selection
        const selectionEnd   = selection.end;     // End position of the selection
        const startLine      = selectionStart.line;
        const startCharacter = selectionStart.character;
        const endLine        = selectionEnd.line;
        const endCharacter   = selectionEnd.character;

        console.log("Prokop-bot::disposable_sendToPython()");

        const dbg_output = `File(${languageId}): ${fileName} path=${filePath}\n` +
            `Cursor Position: Line ${cursorLine + 1}, Character ${cursorCharacter + 1}\n` + // +1 for user-friendly display
            `Selection Start: Line ${startLine + 1}, Character ${startCharacter + 1}\n` +
            `Selection End: Line ${endLine + 1}, Character ${endCharacter + 1}`;

        console.log("Prokop-bot::disposable_sendToPython()",dbg_output);
        vscode.window.showInformationMessage( dbg_output );

        // Adjust the path to your Python script
        const pythonScriptPath = path.join(__dirname, '..', 'src', 'script.py');

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
            console.log(`---Output: ${stdout}`);
            vscode.window.showInformationMessage(`---Output: ${stdout}`);
        });
    }
});

    // Register the explorer context menu command
    const disposable_explorerCommand = vscode.commands.registerCommand('prokopBot.explorerCommand', (uri: vscode.Uri) => {
        const filePath = uri.fsPath;
        vscode.window.showInformationMessage(`Prokop Bot action on: ${filePath}`);

        const pythonScriptPath = path.join(context.extensionPath, 'src', 'script.py');

        exec(`python "${pythonScriptPath}" "${filePath}"`, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error executing script: ${error.message}`);
                vscode.window.showErrorMessage(`Error executing script: ${error.message}`);
                return;
            }
            if (stderr) {
                console.error(`Script error: ${stderr}`);
                vscode.window.showErrorMessage(`Script error: ${stderr}`);
                return;
            }
            // Display the output
            console.log(`Output: ${stdout}`);
            vscode.window.showInformationMessage(`Script Output: ${stdout}`);
        });
    });

    // Command for adding tab to list
    let disposable_addTabToList = vscode.commands.registerCommand('extension.addTabToList', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            const document = editor.document;
            const filename = document.fileName; // Get the full path of the file
            const basename = path.basename(filename); // Get just the filename

            // Implement your functionality here, e.g., add to a list or perform some action
            vscode.window.showInformationMessage(`Added tab: ${basename}`);
            console.log(`Tab added: ${basename}`);
        }
    });

    // Add both disposables to context subscriptions
    //context.subscriptions.push(disposableEnclose);

    // Add all disposables to the context's subscriptions
    context.subscriptions.push(
            disposable_encloseSelection,
            disposable_sendToPython,
            disposable_explorerCommand,
            disposable_addTabToList
        );

}

// This method is called when your extension is deactivated
export function deactivate() {}
```
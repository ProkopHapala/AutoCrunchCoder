// Help With writing VScode extension
// https://www.perplexity.ai/search/how-to-make-simple-vscode-exte-xO3dy..BT1emdXQGZOtxbw

// NOTE:
// 1) compile the extension with `~/git/AutoCrunchCoder/prokop-bot$ npm run compile` to update the javascript file (extension.js)
// 2) debug with F5 (Run Extension)


// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';


// Webview Provider Class
class ProkopBotWebviewProvider implements vscode.WebviewViewProvider {

    private webviewView: vscode.WebviewView | undefined;
    public static readonly viewType = 'prokopBotWebview';

    constructor(private readonly context: vscode.ExtensionContext) {}

    resolveWebviewView(webviewView: vscode.WebviewView) {
        this.webviewView = webviewView;
        webviewView.webview.options = {
            // Enable scripts in the webview
            enableScripts: true,
            // Restrict the webview to only load resources from `media` directory
            localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, 'media')]
        };
        console.log('ProkopBotWebviewProvider::resolveWebviewView():  webviewView.webview.html = this.getHtmlForWebview(webviewView.webview); ');
        webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(message => {
            switch (message.command) {
                case 'showMarkdownSections':
                    this.showMarkdownSections();
                    break;
                case 'showJsonTree':
                    this.showJsonTree();
                    break;
            }
        });
    }

    private getHtmlForWebview(webview: vscode.Webview): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, 'media', 'main.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, 'media', 'styles.css'));
        console.log('ProkopBotWebviewProvider::getHtmlForWebview(): return HTML ');
        return `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src ${webview.cspSource}; style-src ${webview.cspSource};">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link href="${styleUri}" rel="stylesheet">
                <title>Prokop Bot</title>
            </head>
            <body>
                <h1>Prokop Bot Context</h1>
                <div id="content">
                    <button id="showMarkdownBtn">Show Markdown Sections</button>
                    <button id="showJsonBtn">Show JSON Tree</button>
                    <div id="treeView"></div>
                </div>
                <script src="${scriptUri}"></script>
            </body>
            </html>
        `;
    }

    private async showMarkdownSections() {
        console.log('Reading Markdown file');
        const markdownContent = await this.readMarkdownFile();
        console.log('Rendering Markdown sections');
        const sections = this.renderMarkdownSections(markdownContent);
        console.log('Updating webview content');
        this.updateWebviewContent(sections);
    }
    
    private async showJsonTree() {
        console.log('Reading JSON file');
        const jsonContent = await this.readJsonFile();
        console.log('Rendering JSON tree');
        const tree = this.renderJsonTree(jsonContent);
        console.log('Updating webview content');
        this.updateWebviewContent(tree);
    }

    private async readMarkdownFile(): Promise<string> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return '';
        }
        const markdownFilePath = path.join(workspaceFolders[0].uri.fsPath, 'Prokobot_context.md');
        return fs.promises.readFile(markdownFilePath, 'utf8');
    }

    private async readJsonFile(): Promise<any> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return {};
        }
        const jsonFilePath = path.join(workspaceFolders[0].uri.fsPath, 'Prokobot_context.json');
        const jsonContent = await fs.promises.readFile(jsonFilePath, 'utf8');
        return JSON.parse(jsonContent);
    }

    private renderMarkdownSections(markdownContent: string): string {
        const sections = markdownContent.match(/^### .+$/gm) || [];
        return `<ul>${sections.map(section => `<li>${section.replace('### ', '')}</li>`).join('')}</ul>`;
    }

    private renderJsonTree(jsonContent: any): string {
        function renderNode(node: any): string {
            if (typeof node !== 'object' || node === null) {
                return `<li>${node}</li>`;
            }
            return Object.entries(node).map(([key, value]) => {
                if (typeof value === 'object' && value !== null) {
                    return `<li>${key}<ul>${renderNode(value)}</ul></li>`;
                }
                return `<li>${key}: ${value}</li>`;
            }).join('');
        }
        return `<ul>${renderNode(jsonContent)}</ul>`;
    }

    public updateWebviewContent(content: string) {
        if (this.webviewView) {
            this.webviewView.webview.postMessage({ command: 'updateContent', content });
        }
    }

}



// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    console.log('Congratulations, your extension "prokop-bot" is now active!');
    console.log(`Current working directory: ${process.cwd()}`);

    // Register the Webview View Provider
    const prokopBotWebviewProvider = new ProkopBotWebviewProvider(context);
    console.log('ProkoBot::activate():  context.subscriptions.push() ');
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(ProkopBotWebviewProvider.viewType, prokopBotWebviewProvider)
    );

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


async function addToMarkdown(selectedText: string, fileName: string, fullPath: string, startLine: number, startCharacter: number, endLine: number, endCharacter: number) {
    // ... (existing markdown content creation)

    const jsonContent = {
        file: fileName,
        path: fullPath,
        location: `@@ -${startLine},${startCharacter} +${endLine},${endCharacter} @@`,
        content: selectedText
    };

    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('No workspace folder found.');
        return;
    }
    const workspacePath = workspaceFolders[0].uri.fsPath;
    const markdownFilePath = path.join(workspacePath, 'Prokobot_context.md');
    const jsonFilePath = path.join(workspacePath, 'Prokobot_context.json');


    // Prepare the markdown content
    const markdownContent = `### file: ${fileName}\n` +
        `path: \`${fullPath}\n\`` +
        `location: @@ -${startLine},${startCharacter} +${endLine},${endCharacter} @@\n` +
        //`start line: ${startLine} character: ${startCharacter}\n` +
        //`end line: ${endLine} character: ${endCharacter}\n` +
        '```typescript\n' +
        `${selectedText}\n` +
        '```\n\n';

    // Append to markdown file
    await fs.promises.appendFile(markdownFilePath, markdownContent);

    // Append to JSON file
    let jsonData = [];
    try {
        const existingData = await fs.promises.readFile(jsonFilePath, 'utf8');
        jsonData = JSON.parse(existingData);
    } catch (error) {
        // File doesn't exist or is empty, start with an empty array
    }
    jsonData.push(jsonContent);
    await fs.promises.writeFile(jsonFilePath, JSON.stringify(jsonData, null, 2));

    vscode.window.showInformationMessage(`Added content to ${markdownFilePath} and ${jsonFilePath}`);
}

function renderMarkdownSections(markdownContent: string): string {
    const sections = markdownContent.match(/^### .+$/gm) || [];
    return sections.map(section => `<li>${section.replace('### ', '')}</li>`).join('');
}

function renderJsonTree(jsonContent: any): string {
    function renderNode(node: any): string {
        if (typeof node !== 'object' || node === null) {
            return `<li>${node}</li>`;
        }
        return Object.entries(node).map(([key, value]) => {
            if (typeof value === 'object' && value !== null) {
                return `<li>${key}<ul>${renderNode(value)}</ul></li>`;
            }
            return `<li>${key}: ${value}</li>`;
        }).join('');
    }
    return `<ul>${renderNode(jsonContent)}</ul>`;
}

// Register the command to add selection to Markdown
let disposable_addToMarkdown = vscode.commands.registerCommand('extension.addToMarkdown', async () => {
    
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor found.');
        return;
    }

    const selection = editor.selection;
    if (selection.isEmpty) {
        vscode.window.showErrorMessage('No text selected.');
        return;
    }

    const selectedText = editor.document.getText(selection);
    const document = editor.document;
    const filePath = document.fileName;
    const fileName = path.basename(filePath);
    const fullPath = path.resolve(filePath);

    const start = selection.start;
    const end = selection.end;

    // Formatting start and end positions
    const startLine = start.line + 1; // Lines are zero-based
    const startCharacter = start.character + 1; // Characters are zero-based
    const endLine = end.line + 1;
    const endCharacter = end.character + 1;

    await addToMarkdown(selectedText, fileName, fullPath, startLine, startCharacter, endLine, endCharacter);

    // // Prepare the markdown content
    // const markdownContent = `### file: ${fileName}\n` +
    //     `path: \`${fullPath}\n\`` +
    //     `location: @@ -${startLine},${startCharacter} +${endLine},${endCharacter} @@\n` +
    //     //`start line: ${startLine} character: ${startCharacter}\n` +
    //     //`end line: ${endLine} character: ${endCharacter}\n` +
    //     '```typescript\n' +
    //     `${selectedText}\n` +
    //     '```\n\n';

    // // Define the path for Prokobot_context.md in the workspace root
    // const workspaceFolders = vscode.workspace.workspaceFolders;
    // if (!workspaceFolders) {
    //     vscode.window.showErrorMessage('No workspace folder found.');
    //     return;
    // }
    // const workspacePath = workspaceFolders[0].uri.fsPath;
    // const markdownFilePath = path.join(workspacePath, 'Prokobot_context.md');

    // // Check if the file exists
    // fs.access(markdownFilePath, fs.constants.F_OK, (err) => {
    //     if (err) {
    //         // File does not exist, create it with the content
    //         fs.writeFile(markdownFilePath, markdownContent, (err) => {
    //             if (err) {
    //                 vscode.window.showErrorMessage(`Failed to create ${markdownFilePath}: ${err.message}`);
    //             } else {
    //                 vscode.window.showInformationMessage(`Created and added content to ${markdownFilePath}`);
    //             }
    //         });
    //     } else {
    //         // File exists, append the content
    //         fs.appendFile(markdownFilePath, markdownContent, (err) => {
    //             if (err) {
    //                 vscode.window.showErrorMessage(`Failed to append to ${markdownFilePath}: ${err.message}`);
    //             } else {
    //                 vscode.window.showInformationMessage(`Appended content to ${markdownFilePath}`);
    //             }
    //         });
    //     }
    // });

});

 // Register the command to clean the Markdown file
 let disposable_cleanMarkdown = vscode.commands.registerCommand('extension.cleanMarkdown', async () => {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('No workspace folder found.');
        return;
    }
    const workspacePath = workspaceFolders[0].uri.fsPath;
    const markdownFilePath = path.join(workspacePath, 'Prokobot_context.md');

    fs.access(markdownFilePath, fs.constants.F_OK, (err) => {
        if (err) {
            // File does not exist, create an empty one
            fs.writeFile(markdownFilePath, '', (err) => {
                if (err) {
                    vscode.window.showErrorMessage(`Failed to create ${markdownFilePath}: ${err.message}`);
                } else {
                    vscode.window.showInformationMessage(`Created ${markdownFilePath}`);
                }
            });
        } else {
            // File exists, clear its contents
            fs.truncate(markdownFilePath, 0, (err) => {
                if (err) {
                    vscode.window.showErrorMessage(`Failed to clear ${markdownFilePath}: ${err.message}`);
                } else {
                    vscode.window.showInformationMessage(`Cleared contents of ${markdownFilePath}`);
                }
            });
        }
    });
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
            disposable_addToMarkdown,
            disposable_cleanMarkdown,
            disposable_addTabToList
        );

}

// This method is called when your extension is deactivated
export function deactivate() {}
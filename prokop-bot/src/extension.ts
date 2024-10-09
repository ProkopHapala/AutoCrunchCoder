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
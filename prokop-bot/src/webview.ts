import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

// Webview Provider Class
export class ProkopBotWebviewProvider implements vscode.WebviewViewProvider {

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
                case 'sendToAgent':
                    this.sendToAgent();
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
                    <button id="sendToAgentBtn">Send to Agent</button>
                    <div id="treeView"></div>
                </div>
                <script src="${scriptUri}"></script>
            </body>
            </html>
        `;
    }

    private async sendToAgent() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace folder found.');
            return;
        }
        const markdownFilePath = path.join(workspaceFolders[0].uri.fsPath, 'Prokobot_context.md');
        const markdownContent = await fs.promises.readFile(markdownFilePath, 'utf8');
    
        // Call Python script
        const pythonScriptPath = path.join(__dirname, '..', 'src', 'script_agent.py');
        const { exec } = require('child_process');
        //exec(`python "${pythonScriptPath}" "${markdownContent}"`, async (error: any, stdout: string, stderr: string) => {
        // exec(`source ~/venvML/bin/activate && python "${pythonScriptPath}" "${markdownContent}"`, {
        //     shell: '/bin/bash'
        exec(`source ~/venvML/bin/activate && python "${pythonScriptPath}" "${markdownContent}"`, {
            shell: '/bin/bash'        
        }, async (error: any, stdout: string, stderr: string) => {
            if (error) {
                vscode.window.showErrorMessage(`Error: ${error.message}`);
                return;
            }
            if (stderr) {
                vscode.window.showErrorMessage(`Error: ${stderr}`);
                return;
            }
            // Create a new file with the agent's response
            const responseFilePath = path.join(workspaceFolders[0].uri.fsPath, 'agent_response.md');
            await fs.promises.writeFile(responseFilePath, stdout);
    
            // Open the response in a Markdown preview
            const responseUri = vscode.Uri.file(responseFilePath);
            await vscode.commands.executeCommand('markdown.showPreview', responseUri);
        });
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

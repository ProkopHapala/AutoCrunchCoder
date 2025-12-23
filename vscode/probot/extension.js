const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    // Command: Set the target file (Context Buffer)
    const setBufferDisposable = vscode.commands.registerCommand('probot.setContextBuffer', async (uri) => {
        if (uri && uri.fsPath) {
            await context.workspaceState.update('contextBufferPath', uri.fsPath);
            vscode.window.showInformationMessage(`Context Buffer set to: ${path.basename(uri.fsPath)}`);
        } else {
            vscode.window.showErrorMessage('Please right-click a valid .md file in the explorer.');
        }
    });

    // Command: Add to Context (works for files and selected text)
    const addToContextDisposable = vscode.commands.registerCommand('probot.addToContext', async (uri) => {
        const bufferPath = context.workspaceState.get('contextBufferPath');
        if (!bufferPath) {
            vscode.window.showErrorMessage("No Context Buffer set! Right-click a .md file and select 'Set as Context Buffer' first.");
            return;
        }

        const editor = vscode.window.activeTextEditor;
        let contentToAppend = '';
        let tocEntry = '';

        const workspaceFolders = vscode.workspace.workspaceFolders;
        const workspaceRoot = workspaceFolders && workspaceFolders.length > 0 ? workspaceFolders[0].uri.fsPath : '';

        const toRel = (filePath) => {
            if (workspaceRoot && filePath.startsWith(workspaceRoot)) {
                return path.relative(workspaceRoot, filePath);
            }
            return filePath;
        };

        const invokedOnUri = uri && uri.fsPath;
        const editorMatchesUri = editor && invokedOnUri && editor.document.uri.fsPath === uri.fsPath;
        const selectionAvailable = editor && editor.selection && !editor.selection.isEmpty;

        // Scenario A: Editor (selection or whole file), if no URI or URI matches the editor
        if (editor && (!invokedOnUri || editorMatchesUri)) {
            const doc = editor.document;
            const fileName = path.basename(doc.fileName);
            const filePath = doc.fileName;
            const relativePath = toRel(filePath);
            const lang = normalizeLangId(doc.languageId);

            if (selectionAvailable) {
                const selection = editor.selection;
                let text = doc.getText(selection);
                // Trim leading/trailing empty lines
                text = text.replace(/^\s*\n+/, '').replace(/\n+\s*$/, '');

                const startLine = selection.start.line + 1;
                const startChar = selection.start.character + 1;
                const endLine = selection.end.line + 1;
                const endChar = selection.end.character + 1;

                const anchor = makeAnchor(fileName, relativePath);
                tocEntry = `- [${fileName} (${startLine}:${startChar}-${endLine}:${endChar})](#${anchor})`;
                contentToAppend =
                    `\n<a id="${anchor}"></a>\n` +
                    `## ${fileName}\n` +
                    `path: ${relativePath}\n` +
                    `range: L${startLine}:C${startChar}-L${endLine}:C${endChar}\n\n` +
                    `\`\`\`${lang}\n${text}\n\`\`\`\n---\n`;
            } else {
                const text = doc.getText();
                const anchor = makeAnchor(fileName, relativePath);
                tocEntry = `- [${fileName} (whole file)](#${anchor})`;
                contentToAppend =
                    `\n<a id="${anchor}"></a>\n` +
                    `## ${fileName}\n` +
                    `path: ${relativePath}\n` +
                    `range: (whole file)\n\n` +
                    `\`\`\`${lang}\n${text}\n\`\`\`\n---\n`;
            }
        }

        // Scenario B: Triggered from File Explorer or tab context (whole file via URI)
        else if (invokedOnUri) {
            try {
                const doc = await vscode.workspace.openTextDocument(uri);
                const fileName = path.basename(uri.fsPath);
                const lang = normalizeLangId(doc.languageId);
                const text = doc.getText();
                const relativePath = toRel(uri.fsPath);

                const anchor = makeAnchor(fileName, relativePath);
                tocEntry = `- [${fileName} (whole file)](#${anchor})`;
                contentToAppend =
                    `\n<a id="${anchor}"></a>\n` +
                    `## ${fileName}\n` +
                    `path: ${relativePath}\n` +
                    `range: (whole file)\n\n` +
                    `\`\`\`${lang}\n${text}\n\`\`\`\n---\n`;
            } catch (err) {
                vscode.window.showErrorMessage(`Error reading file: ${err.message}`);
                return;
            }
        } else {
            vscode.window.showWarningMessage('Please open or right-click a file.');
            return;
        }

        try {
            const newContent = await mergeWithToc(bufferPath, tocEntry, contentToAppend);
            fs.writeFileSync(bufferPath, newContent);
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
    deactivate,
};

function normalizeLangId(langId) {
    if (!langId) return '';
    const lower = langId.toLowerCase();
    if (lower.includes('fortran')) return 'fortran';
    return langId;
}

function makeAnchor(fileName, relativePath) {
    const base = `${relativePath || fileName}`.toLowerCase();
    return base.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

async function mergeWithToc(bufferPath, tocEntry, blockContent) {
    const tocHeader = '## Table of Contents';
    let existing = '';
    if (fs.existsSync(bufferPath)) {
        existing = fs.readFileSync(bufferPath, 'utf8');
    }

    if (!tocEntry) {
        return existing + blockContent;
    }

    if (existing.includes(tocHeader)) {
        const lines = existing.split('\n');
        const headerIndex = lines.indexOf(tocHeader);
        let insertAt = headerIndex + 1;
        while (insertAt < lines.length && lines[insertAt].startsWith('- ')) {
            insertAt += 1;
        }
        lines.splice(insertAt, 0, tocEntry);
        const rebuilt = lines.join('\n');
        return rebuilt + blockContent;
    }

    // No TOC yet; create one at the top
    return `${tocHeader}\n${tocEntry}\n\n${existing}${existing ? '\n' : ''}${blockContent}`;
}

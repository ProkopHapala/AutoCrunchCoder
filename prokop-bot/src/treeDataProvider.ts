import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export class ContextTreeDataProvider implements vscode.TreeDataProvider<ContextItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<ContextItem | undefined | null | void> = new vscode.EventEmitter<ContextItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<ContextItem | undefined | null | void> = this._onDidChangeTreeData.event;

    constructor(private workspaceRoot: string) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: ContextItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ContextItem): Thenable<ContextItem[]> {
        if (!this.workspaceRoot) {
            vscode.window.showInformationMessage('No context in empty workspace');
            return Promise.resolve([]);
        }

        if (element) {
            return Promise.resolve(this.getContextChildren(element));
        } else {
            return Promise.resolve(this.getContextRoots());
        }
    }

    private getContextRoots(): ContextItem[] {
        const markdownPath = path.join(this.workspaceRoot, 'Prokobot_context.md');
        const jsonPath = path.join(this.workspaceRoot, 'Prokobot_context.json');
        const roots: ContextItem[] = [];

        if (fs.existsSync(markdownPath)) {
            roots.push(new ContextItem('Markdown Sections', vscode.TreeItemCollapsibleState.Collapsed, 'markdown'));
        }
        if (fs.existsSync(jsonPath)) {
            roots.push(new ContextItem('JSON Tree', vscode.TreeItemCollapsibleState.Collapsed, 'json'));
        }

        return roots;
    }

    private getContextChildren(element: ContextItem): ContextItem[] {
        if (element.contextType === 'markdown') {
            return this.getMarkdownSections();
        } else if (element.contextType === 'json') {
            return this.getJsonTree();
        }
        return [];
    }

    private getMarkdownSections(): ContextItem[] {
        const markdownPath = path.join(this.workspaceRoot, 'Prokobot_context.md');
        const content = fs.readFileSync(markdownPath, 'utf-8');
        const sections = content.match(/^### .+$/gm) || [];
        return sections.map(section => new ContextItem(section.replace('### ', ''), vscode.TreeItemCollapsibleState.None));
    }

    private getJsonTree(): ContextItem[] {
        const jsonPath = path.join(this.workspaceRoot, 'Prokobot_context.json');
        const content = fs.readFileSync(jsonPath, 'utf-8');
        const jsonContent = JSON.parse(content);
        return this.parseJsonToItems(jsonContent);
    }

    private parseJsonToItems(json: any): ContextItem[] {
        if (Array.isArray(json)) {
            return json.flatMap((item, index) => {
                const itemNode = new ContextItem(`Item ${index}`, vscode.TreeItemCollapsibleState.Collapsed);
                return [itemNode, ...Object.entries(item).map(([key, value]) => 
                    new ContextItem(`${key}: ${value}`, vscode.TreeItemCollapsibleState.None)
                )];
            });
        }
        return Object.entries(json).map(([key, value]) => 
            new ContextItem(`${key}: ${value}`, vscode.TreeItemCollapsibleState.None)
        );
    }
    
    
}

class ContextItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextType?: string,
        public readonly children?: ContextItem[]
    ) {
        super(label, collapsibleState);
    }
}

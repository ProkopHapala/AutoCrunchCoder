// media/main.js

(function () {
    const vscode = acquireVsCodeApi();

    document.addEventListener('DOMContentLoaded', () => {
        const showMarkdownBtn = document.getElementById('showMarkdownBtn');
        const showJsonBtn = document.getElementById('showJsonBtn');
        const treeView = document.getElementById('treeView');

        showMarkdownBtn.addEventListener('click', () => {
            console.log('Show Markdown button clicked');
            vscode.postMessage({ command: 'showMarkdownSections' });
        });

        showJsonBtn.addEventListener('click', () => {
            console.log('Show JSON button clicked');
            vscode.postMessage({ command: 'showJsonTree' });
        });

        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.command) {
                case 'updateContent':
                    //document.getElementById('treeView').innerHTML = message.content;
                    treeView.innerHTML = message.content;
                    break;
            }
        });
        
    });
})();
// media/main.js

(function () {
    const vscode = acquireVsCodeApi();

    document.addEventListener('DOMContentLoaded', () => {
        
        const showMarkdownBtn = document.getElementById('showMarkdownBtn');
        showMarkdownBtn.addEventListener('click', () => {
            console.log('Show Markdown button clicked');
            vscode.postMessage({ command: 'showMarkdownSections' });
        });

        const showJsonBtn = document.getElementById('showJsonBtn');
        showJsonBtn.addEventListener('click', () => {
            console.log('Show JSON button clicked');
            vscode.postMessage({ command: 'showJsonTree' });
        });

        const sendToAgentBtn = document.getElementById('sendToAgentBtn');
        sendToAgentBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'sendToAgent' });
        });

        const treeView = document.getElementById('treeView');
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
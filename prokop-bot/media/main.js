// media/main.js

(function () {
    const vscode = acquireVsCodeApi();

    // Function to send a message to the extension to show the filename
    function showFilename() {
        vscode.postMessage({ command: 'showFilename' });
    }

    // Add event listener to the button
    document.addEventListener('DOMContentLoaded', () => {
        const showFilenameBtn = document.getElementById('showFilenameBtn');
        const filenameDisplay = document.getElementById('filenameDisplay');

        if (showFilenameBtn) {
            showFilenameBtn.addEventListener('click', showFilename);
        }

        // Listen for messages from the extension
        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.command) {
                case 'displayFilename':
                    filenameDisplay.textContent = `Current file: ${message.filename}`;
                    break;
            }
        });
    });
})();

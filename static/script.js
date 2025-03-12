// Initialize CodeMirror
let editor = CodeMirror.fromTextArea(document.getElementById("code-editor"), {
    mode: "python",
    theme: "monokai",
    lineNumbers: true,
    indentUnit: 4,
    autoCloseBrackets: true,
    matchBrackets: true,
    lineWrapping: true
});

// Get DOM elements
const runButton = document.getElementById('run-button');
const clearButton = document.getElementById('clear-button');
const outputElement = document.getElementById('output');
const errorElement = document.getElementById('error');
const apiResponseElement = document.getElementById('api-response');

// API-related buttons
const fetchConversationsButton = document.getElementById('fetch-conversations');
const fetchFactsButton = document.getElementById('fetch-facts');
const fetchTodosButton = document.getElementById('fetch-todos');

// Run code function
async function runCode() {
    const code = editor.getValue();

    try {
        const response = await fetch('/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code: code })
        });

        const data = await response.json();

        if (data.success) {
            outputElement.textContent = data.output || 'No output';
            errorElement.textContent = data.error || '';
        } else {
            outputElement.textContent = '';
            errorElement.textContent = data.error || 'An error occurred while executing the code';
        }
    } catch (error) {
        errorElement.textContent = 'Failed to execute code: ' + error.message;
    }
}

// Clear output function
function clearOutput() {
    outputElement.textContent = '';
    errorElement.textContent = '';
    apiResponseElement.textContent = '';
}

// API functions
async function fetchApiData(endpoint) {
    try {
        const response = await fetch(`/api/${endpoint}`);
        const data = await response.json();
        apiResponseElement.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        apiResponseElement.textContent = `Error fetching ${endpoint}: ${error.message}`;
    }
}

// Event listeners
runButton.addEventListener('click', runCode);
clearButton.addEventListener('click', clearOutput);
fetchConversationsButton.addEventListener('click', () => fetchApiData('conversations'));
fetchFactsButton.addEventListener('click', () => fetchApiData('facts'));
fetchTodosButton.addEventListener('click', () => fetchApiData('todos'));

// Add keyboard shortcut (Ctrl/Cmd + Enter) to run code
editor.setOption('extraKeys', {
    'Ctrl-Enter': runCode,
    'Cmd-Enter': runCode
});
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

// Pagination state
let currentPages = {
    conversations: 1,
    facts: 1,
    todos: 1
};

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

// Create pagination controls
function createPaginationControls(data, endpoint) {
    const controls = document.createElement('div');
    controls.className = 'pagination-controls';

    // Previous button
    const prevButton = document.createElement('button');
    prevButton.textContent = '← Previous';
    prevButton.disabled = data.page <= 1;
    prevButton.onclick = () => {
        currentPages[endpoint]--;
        fetchApiData(endpoint);
    };

    // Page info
    const pageInfo = document.createElement('span');
    pageInfo.textContent = `Page ${data.page} of ${data.total_pages}`;
    pageInfo.className = 'page-info';

    // Next button
    const nextButton = document.createElement('button');
    nextButton.textContent = 'Next →';
    nextButton.disabled = data.page >= data.total_pages;
    nextButton.onclick = () => {
        currentPages[endpoint]++;
        fetchApiData(endpoint);
    };

    controls.appendChild(prevButton);
    controls.appendChild(pageInfo);
    controls.appendChild(nextButton);

    return controls;
}

// API functions
async function fetchApiData(endpoint) {
    try {
        const page = currentPages[endpoint];
        const response = await fetch(`/api/${endpoint}?page=${page}&per_page=10`);
        const data = await response.json();

        // Clear previous content
        apiResponseElement.innerHTML = '';

        // Add pagination controls
        apiResponseElement.appendChild(createPaginationControls(data, endpoint));

        // Add data display
        const dataDisplay = document.createElement('pre');
        dataDisplay.textContent = JSON.stringify(data, null, 2);
        apiResponseElement.appendChild(dataDisplay);
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
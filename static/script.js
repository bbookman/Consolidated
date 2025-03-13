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


// Function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Function to create a card element
function createCard(item, type) {
    const card = document.createElement('div');
    card.className = 'card';

    let content = '';
    switch(type) {
        case 'conversations':
            content = `
                <h4>${item.Title || 'Conversation'}</h4>
                <p>${item.Summary || 'No summary available'}</p>
                <div class="timestamp">Created: ${formatDate(item['Created At'])}</div>
            `;
            break;
        case 'facts':
            content = `
                <h4>Fact</h4>
                <p>${item.Text}</p>
                <div class="status ${item.Confirmed === 'Yes' ? 'completed' : 'pending'}">
                    ${item.Confirmed === 'Yes' ? 'Confirmed' : 'Pending'}
                </div>
            `;
            break;
        case 'todos':
            content = `
                <h4>${item.Task}</h4>
                <div class="status ${item.Completed === 'Yes' ? 'completed' : 'pending'}">
                    ${item.Completed === 'Yes' ? 'Completed' : 'Pending'}
                </div>
            `;
            break;
    }

    card.innerHTML = content;
    return card;
}

// Function to display data as cards
function displayDataAsCards(data, type) {
    const cardsContainer = document.getElementById(`${type}-cards`);
    cardsContainer.innerHTML = '';

    const items = data[type] || [];
    items.forEach(item => {
        cardsContainer.appendChild(createCard(item, type));
    });

    // Show/hide sections based on data
    document.getElementById(`${type}-section`).style.display = 
        items.length > 0 ? 'block' : 'none';
}

// API functions
async function fetchApiData(endpoint) {
    try {
        const page = currentPages[endpoint];
        const response = await fetch(`/api/${endpoint}?page=${page}&per_page=10`);
        const data = await response.json();

        // Clear previous pagination controls
        const paginationContainer = document.getElementById('pagination-controls');
        paginationContainer.innerHTML = '';

        // Add pagination controls
        paginationContainer.appendChild(createPaginationControls(data, endpoint));

        // Display data as cards
        displayDataAsCards(data, endpoint);
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        document.getElementById(`${endpoint}-cards`).innerHTML = 
            `<div class="error-card">Error fetching ${endpoint}: ${error.message}</div>`;
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
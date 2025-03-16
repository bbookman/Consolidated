// Pagination state
let currentPages = {
    conversations: 1,
    facts: 1,
    todos: 1
};

// API-related buttons
const fetchConversationsButton = document.getElementById('fetch-conversations');
const fetchFactsButton = document.getElementById('fetch-facts');
const fetchTodosButton = document.getElementById('fetch-todos');

// Function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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
        const response = await fetch(`/api/${endpoint}?page=${page}`);
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
fetchConversationsButton.addEventListener('click', () => fetchApiData('conversations'));
fetchFactsButton.addEventListener('click', () => fetchApiData('facts'));
fetchTodosButton.addEventListener('click', () => fetchApiData('todos'));
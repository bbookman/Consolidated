// Function to format date
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch (error) {
        return dateString || 'Unknown date';
    }
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
                <div class="timestamp">Added: ${formatDate(item['Created At'])}</div>
            `;
            break;
        case 'todos':
            content = `
                <h4>${item.Task}</h4>
                <div class="status ${item.Completed === 'Yes' ? 'completed' : 'pending'}">
                    ${item.Completed === 'Yes' ? 'Completed' : 'Pending'}
                </div>
                <div class="timestamp">Created: ${formatDate(item['Created At'])}</div>
            `;
            break;
        case 'lifelogs':
            content = `
                <h4>${item.Title || 'Lifelog'}</h4>
                <p>${item.Description || 'No description available'}</p>
                <div class="tags">Tags: ${item.Tags || 'None'}</div>
                <div class="timestamp">Created: ${formatDate(item['Created At'])}</div>
            `;
            break;
    }

    card.innerHTML = content;
    return card;
}

// Function to display data as cards
function displayDataAsCards(items, type) {
    const cardsContainer = document.getElementById(`${type}-cards`);
    if (!cardsContainer) {
        console.error(`Container for ${type} not found`);
        return;
    }
    
    cardsContainer.innerHTML = '';

    if (!items || items.length === 0) {
        cardsContainer.innerHTML = `<div class="empty-state">No ${type} found</div>`;
        return;
    }

    items.forEach(item => {
        cardsContainer.appendChild(createCard(item, type));
    });

    // Show section
    document.getElementById(`${type}-section`).style.display = 'block';
}

// Display error message
function displayError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-card';
    errorDiv.textContent = `Error: ${message}`;
    
    const dataDisplay = document.getElementById('data-display');
    dataDisplay.innerHTML = '';
    dataDisplay.appendChild(errorDiv);
}

// Display database stats
function displayDatabaseStats(stats) {
    const statsContainer = document.getElementById('db-stats-display');
    if (!statsContainer) return;
    
    let statsHTML = '<div class="stats-cards">';
    
    // Bee API stats (in first row)
    statsHTML += '<div class="stats-row">';
    statsHTML += '<h4>Bee API</h4>';
    
    // Conversations stats
    if (stats.conversations) {
        statsHTML += `
            <div class="stats-card">
                <h4>Conversations</h4>
                <p>Total processed: ${stats.conversations.processed || 0}</p>
                <p>Added to database: ${stats.conversations.added || 0}</p>
                <p>Already existed: ${stats.conversations.skipped || 0}</p>
            </div>
        `;
    }
    
    // Facts stats
    if (stats.facts) {
        statsHTML += `
            <div class="stats-card">
                <h4>Facts</h4>
                <p>Total processed: ${stats.facts.processed || 0}</p>
                <p>Added to database: ${stats.facts.added || 0}</p>
                <p>Already existed: ${stats.facts.skipped || 0}</p>
            </div>
        `;
    }
    
    // Todos stats
    if (stats.todos) {
        statsHTML += `
            <div class="stats-card">
                <h4>Todos</h4>
                <p>Total processed: ${stats.todos.processed || 0}</p>
                <p>Added to database: ${stats.todos.added || 0}</p>
                <p>Already existed: ${stats.todos.skipped || 0}</p>
            </div>
        `;
    }
    statsHTML += '</div>'; // End of first row
    
    // Limitless API stats (in second row)
    statsHTML += '<div class="stats-row">';
    statsHTML += '<h4>Limitless API</h4>';
    
    // Lifelogs stats
    if (stats.lifelogs) {
        statsHTML += `
            <div class="stats-card">
                <h4>Lifelogs</h4>
                <p>Total processed: ${stats.lifelogs.processed || 0}</p>
                <p>Added to database: ${stats.lifelogs.added || 0}</p>
                <p>Already existed: ${stats.lifelogs.skipped || 0}</p>
            </div>
        `;
    } else {
        statsHTML += `
            <div class="stats-card">
                <h4>Lifelogs</h4>
                <p>No data available</p>
            </div>
        `;
    }
    
    statsHTML += '</div>'; // End of second row
    statsHTML += '</div>'; // End of stats-cards
    
    statsContainer.innerHTML = statsHTML;
}

// When the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listener for refresh button
    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            window.location.reload();
        });
    }
    
    // Check if we have initial data from the server
    if (typeof initialData !== 'undefined') {
        console.log('Initial data loaded:', initialData);
        
        // Check if there's an error
        if (initialData.error) {
            displayError(initialData.error);
            return;
        }
        
        // Display the data
        if (initialData.conversations) {
            displayDataAsCards(initialData.conversations, 'conversations');
        }
        
        if (initialData.facts) {
            displayDataAsCards(initialData.facts, 'facts');
        }
        
        if (initialData.todos) {
            displayDataAsCards(initialData.todos, 'todos');
        }
        
        if (initialData.lifelogs) {
            displayDataAsCards(initialData.lifelogs, 'lifelogs');
        }
        
        // Display database stats
        if (initialData.db_stats) {
            displayDatabaseStats(initialData.db_stats);
        }
    } else {
        console.warn('No initial data found.');
    }
});
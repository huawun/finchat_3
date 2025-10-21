/**
 * Chat interface JavaScript for RedShift Chatbot
 */

// Global variables
let conversationId = null;

// DOM elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const loadingOverlay = document.getElementById('loadingOverlay');
const statusIndicator = document.getElementById('statusIndicator');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    setupEventListeners();
});

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Send button click
    sendButton.addEventListener('click', handleSendMessage);
    
    // Enter key press
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Auto-resize input (optional enhancement)
    messageInput.addEventListener('input', () => {
        // Could add auto-resize logic here if needed
    });
}

/**
 * Check application health
 */
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        if (data.status === 'healthy') {
            updateStatus('connected', 'Connected');
        } else {
            updateStatus('error', 'Connection Error');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        updateStatus('error', 'Connection Error');
    }
}

/**
 * Update status indicator
 */
function updateStatus(status, text) {
    statusIndicator.className = `status-indicator ${status}`;
    statusIndicator.querySelector('.status-text').textContent = text;
}

/**
 * Handle send message
 */
async function handleSendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Disable input
    setInputEnabled(false);
    
    // Display user message
    displayUserMessage(message);
    
    // Clear input
    messageInput.value = '';
    
    // Show loading
    showLoading(true);
    
    try {
        // Send to API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Update conversation ID
            conversationId = data.conversation_id;
            
            // Display bot response
            displayBotMessage(data);
        } else {
            // Display error
            displayErrorMessage(data.error || 'An error occurred');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        displayErrorMessage('Failed to send message. Please try again.');
    } finally {
        showLoading(false);
        setInputEnabled(true);
        messageInput.focus();
    }
}

/**
 * Display user message
 */
function displayUserMessage(message) {
    const messageElement = createMessageElement('user', message);
    chatMessages.appendChild(messageElement);
    scrollToBottom();
}

/**
 * Display bot message
 */
function displayBotMessage(data) {
    const messageElement = createMessageElement('bot', data.response);
    
    // Add SQL query if present
    if (data.sql_query) {
        const sqlElement = createSQLElement(data.sql_query);
        messageElement.querySelector('.message-content').appendChild(sqlElement);
    }
    
    // Add results table if present
    if (data.results && data.results.length > 0) {
        const tableElement = createTableElement(data.results);
        messageElement.querySelector('.message-content').appendChild(tableElement);
    }
    
    // Add execution time
    if (data.execution_time) {
        const timeElement = document.createElement('div');
        timeElement.className = 'execution-time';
        timeElement.textContent = `Executed in ${data.execution_time}s`;
        messageElement.querySelector('.message-content').appendChild(timeElement);
    }
    
    chatMessages.appendChild(messageElement);
    scrollToBottom();
}

/**
 * Display error message
 */
function displayErrorMessage(errorText) {
    const messageElement = createMessageElement('bot', 'Sorry, something went wrong.');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.innerHTML = `<p>${escapeHtml(errorText)}</p>`;
    
    messageElement.querySelector('.message-content').appendChild(errorElement);
    chatMessages.appendChild(messageElement);
    scrollToBottom();
}

/**
 * Create message element
 */
function createMessageElement(type, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = type === 'user' ? '👤' : '🤖';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = formatMessageText(text);
    
    content.appendChild(textDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    return messageDiv;
}

/**
 * Create SQL query element
 */
function createSQLElement(sql) {
    const container = document.createElement('div');
    container.style.marginTop = '12px';
    
    const label = document.createElement('div');
    label.className = 'sql-label';
    label.textContent = 'Generated SQL:';
    
    const sqlDiv = document.createElement('div');
    sqlDiv.className = 'sql-query';
    sqlDiv.textContent = sql;
    
    container.appendChild(label);
    container.appendChild(sqlDiv);
    
    return container;
}

/**
 * Create results table element
 */
function createTableElement(results) {
    const container = document.createElement('div');
    container.className = 'results-table';
    
    const count = document.createElement('div');
    count.className = 'results-count';
    count.textContent = `${results.length} row(s) returned`;
    container.appendChild(count);
    
    if (results.length === 0) {
        return container;
    }
    
    const table = document.createElement('table');
    
    // Create header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const columns = Object.keys(results[0]);
    
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create body
    const tbody = document.createElement('tbody');
    
    results.forEach(row => {
        const tr = document.createElement('tr');
        
        columns.forEach(col => {
            const td = document.createElement('td');
            td.textContent = formatCellValue(row[col]);
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
    
    return container;
}

/**
 * Format message text (preserve line breaks)
 */
function formatMessageText(text) {
    return escapeHtml(text)
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

/**
 * Format cell value
 */
function formatCellValue(value) {
    if (value === null || value === undefined) {
        return 'NULL';
    }
    
    if (typeof value === 'object') {
        return JSON.stringify(value);
    }
    
    return String(value);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Scroll to bottom of chat
 */
function scrollToBottom() {
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

/**
 * Enable/disable input
 */
function setInputEnabled(enabled) {
    messageInput.disabled = !enabled;
    sendButton.disabled = !enabled;
}
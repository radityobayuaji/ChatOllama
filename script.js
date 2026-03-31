'use strict';

const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const chatWindow = document.getElementById('chatWindow');
const chatHistoryKey = 'chatHistory';

// Load chat history from localStorage
function loadChatHistory() {
    const chatHistory = JSON.parse(localStorage.getItem(chatHistoryKey)) || [];
    chatHistory.forEach(msg => appendMessage(msg));
}

// Append message to chat window
function appendMessage(msg) {
    const messageElement = document.createElement('div');
    messageElement.textContent = msg;
    chatWindow.appendChild(messageElement);
}

// Send message to Ollama API
async function sendMessage(message) {
    const response = await fetch('http://localhost:11434/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
    });
    const data = await response.json();
    appendMessage('Ollama: ' + data.response);
    saveMessage('You: ' + message);
    saveMessage('Ollama: ' + data.response);
}

// Save message to localStorage
function saveMessage(message) {
    const chatHistory = JSON.parse(localStorage.getItem(chatHistoryKey)) || [];
    chatHistory.push(message);
    localStorage.setItem(chatHistoryKey, JSON.stringify(chatHistory));
}

// Event handling for send button
sendButton.addEventListener('click', () => {
    const message = chatInput.value;
    if (message.trim()) {
        sendMessage(message);
        chatInput.value = '';
    }
});

// Load chat history when the page is loaded
window.onload = loadChatHistory;
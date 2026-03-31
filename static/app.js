'use strict';

const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const chatWindow = document.getElementById('chatWindow');
const clearButton = document.getElementById('clearButton');
const statusDiv = document.getElementById('status');
const sessionList = document.getElementById('sessionList');
const newChatButton = document.getElementById('newChatButton');

let currentSessionId = null;

window.addEventListener('load', () => {
    checkOllamaHealth();
    startNewSession();
    loadSessions();
});

sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

clearButton.addEventListener('click', () => {
    if (confirm('Clear all messages?')) {
        chatWindow.innerHTML = '';
    }
});

newChatButton.addEventListener('click', () => {
    startNewSession();
    loadSessions();
});

async function checkOllamaHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (data.status === 'ok') {
            statusDiv.textContent = '🟢 Ollama Ready';
            statusDiv.style.color = '#28a745';
        } else {
            statusDiv.textContent = '🔴 Ollama Offline';
            statusDiv.style.color = '#dc3545';
        }
    } catch (error) {
        statusDiv.textContent = '🔴 Ollama Not Running';
        statusDiv.style.color = '#dc3545';
    }
}

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    chatInput.value = '';
    chatInput.focus();

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot';
    loadingDiv.id = 'loading-indicator';
    loadingDiv.innerHTML = '<div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
    chatWindow.appendChild(loadingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: currentSessionId })
        });

        const data = await response.json();
        loadingDiv.remove();

        if (!response.ok) {
            appendMessage('❌ Error: ' + (data.error || 'Unknown error'), 'bot');
            return;
        }

        currentSessionId = data.session_id || currentSessionId;
        appendMessage(data.response, 'bot');
        loadSessions();
    } catch (error) {
        loadingDiv.remove();
        appendMessage('❌ Connection error: ' + error.message, 'bot');
    }
}

function appendMessage(msg, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = msg;

    messageDiv.appendChild(bubble);
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function startNewSession() {
    currentSessionId = null;
    chatWindow.innerHTML = '';
    chatInput.focus();
}

async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        renderSessionList(data.sessions || []);
    } catch (error) {
        sessionList.innerHTML = '<p class="empty">Unable to load history</p>';
    }
}

function renderSessionList(sessions) {
    sessionList.innerHTML = '';

    if (!sessions.length) {
        sessionList.innerHTML = '<p class="empty">No history yet</p>';
        return;
    }

    sessions.forEach((session) => {
        const button = document.createElement('button');
        button.className = 'session-item';
        button.setAttribute('type', 'button');
        button.innerHTML = `
            <div class="session-title">${buildSessionTitle(session)}</div>
            <div class="session-meta">${formatMessageCount(session.message_count)}</div>
        `;
        button.addEventListener('click', () => loadSession(session.id));
        sessionList.appendChild(button);
    });
}

function buildSessionTitle(session) {
    const snippet = (session.first_message || 'New chat').trim();
    const shortSnippet = snippet.length > 50 ? `${snippet.slice(0, 50).trim()}...` : snippet;
    const timeLabel = formatTime(session.created_at);
    return `${timeLabel} • ${shortSnippet || 'Conversation'}`;
}

function formatTime(value) {
    if (!value) return 'Now';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Now';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatMessageCount(count) {
    if (!count || count < 2) return '1 message';
    return `${count} messages`;
}

async function loadSession(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        const data = await response.json();

        if (!response.ok) {
            appendMessage('❌ Session not found', 'bot');
            return;
        }

        chatWindow.innerHTML = '';
        (data.messages || []).forEach((msg) => {
            const sender = msg.role === 'user' ? 'user' : 'bot';
            appendMessage(msg.content, sender);
        });

        currentSessionId = sessionId;
    } catch (error) {
        appendMessage('❌ Failed to load session', 'bot');
    }
}

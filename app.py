from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)

# Configuration untuk Ollama API
OLLAMA_API = 'http://localhost:11434/api/generate'
MODEL = 'gemma3:12b'

# Session history storage
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
HISTORY_FILE = os.path.join(DATA_DIR, 'chat_history.json')
MAX_SESSIONS = 50

SNIPPET_LENGTH = 40
active_sessions = {}


def load_history():
    """Load saved sessions from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_history(sessions):
    """Persist sessions to JSON file, keeping at most MAX_SESSIONS."""
    os.makedirs(DATA_DIR, exist_ok=True)
    sessions = sessions[-MAX_SESSIONS:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


@app.route('/')
def index():
    """Render halaman chat utama"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle request chat dan panggil Ollama API"""
    try:
        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id', '')

        if not message:
            return jsonify({'error': 'Pesan tidak boleh kosong'}), 400

        # Initialize a new active session on first message
        if session_id and session_id not in active_sessions:
            now = datetime.now()
            snippet = message[:SNIPPET_LENGTH] + ('...' if len(message) > SNIPPET_LENGTH else '')
            active_sessions[session_id] = {
                'id': session_id,
                'title': now.strftime('%H:%M') + ' - ' + snippet,
                'created_at': now.isoformat(),
                'messages': []
            }

        # Record user message
        if session_id and session_id in active_sessions:
            active_sessions[session_id]['messages'].append({
                'role': 'user',
                'content': message
            })

        # Panggil Ollama API
        response = requests.post(OLLAMA_API, json={
            'model': MODEL,
            'prompt': message,
            'stream': False
        }, timeout=300)

        if response.status_code != 200:
            return jsonify({'error': f'Ollama API error: {response.status_code}'}), 500

        result = response.json()
        response_text = result.get('response', '')

        # Record assistant message
        if session_id and session_id in active_sessions:
            active_sessions[session_id]['messages'].append({
                'role': 'assistant',
                'content': response_text
            })

        return jsonify({
            'response': response_text,
            'model': MODEL
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Tidak bisa terhubung ke Ollama. Pastikan Ollama running di localhost:11434'
        }), 500
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Ollama request timeout'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Return saved session summaries (newest first, no message bodies)."""
    sessions = load_history()
    summaries = []
    for s in reversed(sessions):
        summaries.append({
            'id': s['id'],
            'title': s['title'],
            'created_at': s['created_at'],
            'message_count': len(s.get('messages', []))
        })
    return jsonify(summaries)


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Return full message list for a saved session."""
    sessions = load_history()
    for s in sessions:
        if s['id'] == session_id:
            return jsonify(s)
    return jsonify({'error': 'Session not found'}), 404


@app.route('/api/sessions', methods=['POST'])
def save_session():
    """Save the current active session to history and clear it from memory."""
    data = request.json
    session_id = data.get('session_id', '')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404

    session = active_sessions[session_id]
    if not session.get('messages'):
        del active_sessions[session_id]
        return jsonify({'message': 'Empty session not saved'})

    sessions = load_history()
    # Replace existing entry if the same session_id was saved before
    sessions = [s for s in sessions if s['id'] != session_id]
    sessions.append(session)
    save_history(sessions)
    del active_sessions[session_id]

    return jsonify({
        'message': 'Session saved',
        'session': {
            'id': session['id'],
            'title': session['title'],
            'created_at': session['created_at'],
            'message_count': len(session['messages'])
        }
    })


@app.route('/api/health', methods=['GET'])
def health():
    """Check apakah Ollama API tersedia"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            return jsonify({'status': 'ok', 'message': 'Ollama sedang running'})
        else:
            return jsonify({'status': 'error', 'message': 'Ollama tidak merespons'}), 500
    except:
        return jsonify({'status': 'error', 'message': 'Ollama tidak tersedia'}), 500


if __name__ == '__main__':
    print('='*60)
    print('✅ Chat Ollama dengan Flask')
    print('='*60)
    print('📍 Akses di: http://localhost:5000')
    print('🤖 Model: gemma3:12b')
    print('🔗 Ollama API: http://localhost:11434')
    print('='*60)
    print('⚠️  Pastikan Ollama sudah running: ollama serve')
    print('='*60)
    app.run(debug=True, port=5000, host='0.0.0.0')


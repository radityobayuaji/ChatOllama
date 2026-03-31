from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# Path to chat history file
DATA_DIR = 'data'
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, 'chat_history.json')
MAX_SESSIONS = 50

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def load_sessions():
    """Load sessions from JSON file"""
    if not os.path.exists(CHAT_HISTORY_FILE):
        return []
    try:
        with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_sessions(sessions):
    """Save sessions to JSON file"""
    # Keep only the last MAX_SESSIONS
    if len(sessions) > MAX_SESSIONS:
        sessions = sessions[-MAX_SESSIONS:]

    with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

# Configuration untuk Ollama API
OLLAMA_API = 'http://localhost:11434/api/generate'
MODEL = 'gemma3:12b'

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
        
        if not message:
            return jsonify({'error': 'Pesan tidak boleh kosong'}), 400
        
        # Panggil Ollama API
        response = requests.post(OLLAMA_API, json={
            'model': MODEL,
            'prompt': message,
            'stream': False
        }, timeout=300)
        
        if response.status_code != 200:
            return jsonify({'error': f'Ollama API error: {response.status_code}'}), 500
        
        result = response.json()
        return jsonify({
            'response': result.get('response', ''),
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

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all chat sessions"""
    try:
        sessions = load_sessions()
        return jsonify({'sessions': sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session by ID"""
    try:
        sessions = load_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)

        if session:
            return jsonify(session)
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
def save_session():
    """Save a new chat session"""
    try:
        data = request.json
        messages = data.get('messages', [])

        if not messages:
            return jsonify({'error': 'No messages to save'}), 400

        # Generate session title from first user message
        first_user_msg = next((msg['content'] for msg in messages if msg['role'] == 'user'), '')
        title = first_user_msg[:50] + ('...' if len(first_user_msg) > 50 else '')

        # Create new session
        session = {
            'id': str(uuid.uuid4()),
            'title': title,
            'timestamp': datetime.now().isoformat(),
            'messages': messages
        }

        # Load existing sessions and add new one
        sessions = load_sessions()
        sessions.append(session)

        # Save updated sessions
        save_sessions(sessions)

        return jsonify(session), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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


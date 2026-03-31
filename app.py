from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime
import db

app = Flask(__name__)

# Configuration untuk Ollama API
OLLAMA_BASE = 'http://localhost:11434'
OLLAMA_API = f'{OLLAMA_BASE}/api/generate'
MODEL = 'gemma3:12b'

SNIPPET_LENGTH = 40
active_sessions = {}

# Initialise SQLite DB (creates tables + migrates JSON if present)
db.init_db()


def check_ollama_ready():
    """Check if Ollama is running and the required model is available.

    Returns (is_ready: bool, error_message: str | None).
    Does NOT pull the model automatically.
    """
    try:
        response = requests.get(f'{OLLAMA_BASE}/api/tags', timeout=5)
    except requests.exceptions.ConnectionError:
        return False, (
            f'Ollama is not running on {OLLAMA_BASE}. '
            'Start it with: ollama serve'
        )
    except requests.exceptions.Timeout:
        return False, (
            f'Ollama did not respond in time on {OLLAMA_BASE}. '
            'Check that Ollama is running: ollama serve'
        )
    except Exception:
        return False, (
            f'Cannot reach Ollama on {OLLAMA_BASE}. '
            'Make sure it is running: ollama serve'
        )

    if response.status_code != 200:
        return False, 'Ollama server is not responding correctly'

    try:
        tags_data = response.json()
    except ValueError:
        return False, 'Ollama returned an unexpected response (not valid JSON)'

    available_models = [m.get('name', '') for m in tags_data.get('models', [])]

    if MODEL not in available_models:
        return False, (
            f'Ollama is not ready / model {MODEL} missing. '
            f'Run: ollama pull {MODEL}'
        )

    return True, None


@app.route('/')
def index():
    """Render halaman chat utama"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle request chat dan panggil Ollama API"""
    is_ready, error = check_ollama_ready()
    if not is_ready:
        return jsonify({'error': error}), 503

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
    return jsonify(db.get_sessions())


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Return full message list for a saved session."""
    session = db.get_session(session_id)
    if session is None:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session)


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

    db.save_session(session)
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
    """Check if Ollama is running and the required model is available."""
    is_ready, error = check_ollama_ready()
    if is_ready:
        return jsonify({'status': 'ok', 'message': 'Ollama ready', 'model': MODEL})
    return jsonify({'status': 'error', 'message': error}), 503


if __name__ == '__main__':
    print('='*60)
    print('✅ Chat Ollama dengan Flask')
    print('='*60)
    print('📍 Akses di: http://localhost:5000')
    print(f'🤖 Model: {MODEL}')
    print(f'🔗 Ollama API: {OLLAMA_BASE}')
    print('='*60)

    is_ready, error = check_ollama_ready()
    if is_ready:
        print(f'✅ Ollama ready — model {MODEL} is available')
    else:
        print(f'⚠️  WARNING: {error}')

    print('='*60)
    app.run(debug=True, port=5000, host='0.0.0.0')


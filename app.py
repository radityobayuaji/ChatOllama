from flask import Flask, render_template, request, jsonify
import requests
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)

# Configuration untuk Ollama API
OLLAMA_API = 'http://localhost:11434/api/generate'
MODEL = 'gemma3:12b'

DATA_DIR = Path(__file__).parent / 'data'
HISTORY_FILE = DATA_DIR / 'chat_history.json'
MAX_SESSIONS = 50


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + 'Z'


def _load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {'sessions': []}

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get('sessions'), list):
                return data
    except json.JSONDecodeError:
        pass

    return {'sessions': []}


def _save_history(history: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def _build_title(session: dict) -> str:
    created_at = session.get('created_at')
    first_user = next((m for m in session.get('messages', []) if m.get('role') == 'user'), None)
    snippet = (first_user.get('content', '') if first_user else '').strip()
    if len(snippet) > 60:
        snippet = snippet[:60].rstrip() + '...'

    time_label = ''
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            time_label = dt.strftime('%H:%M')
        except ValueError:
            time_label = created_at

    if time_label and snippet:
        return f'{time_label} • {snippet}'
    return snippet or time_label or 'Chat session'


def _record_session(session_id: str, user_message: str, bot_message: str) -> dict:
    history = _load_history()
    sessions = history.get('sessions', [])
    now = _timestamp()

    session = next((s for s in sessions if s.get('id') == session_id), None)
    if not session:
        session = {
            'id': session_id,
            'created_at': now,
            'messages': []
        }

    session['messages'].append({'role': 'user', 'content': user_message, 'timestamp': now})
    session['messages'].append({'role': 'assistant', 'content': bot_message, 'timestamp': now})
    session['updated_at'] = now
    session['title'] = session.get('title') or _build_title(session)

    sessions = [s for s in sessions if s.get('id') != session_id]
    sessions.insert(0, session)
    sessions = sessions[:MAX_SESSIONS]

    _save_history({'sessions': sessions})
    return session

@app.route('/')
def index():
    """Render halaman chat utama"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle request chat, panggil Ollama API, dan simpan sesi"""
    try:
        data = request.json or {}
        message = (data.get('message') or '').strip()
        session_id = data.get('session_id') or str(uuid4())
        
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
        reply_text = result.get('response', '')

        _record_session(session_id, message, reply_text)

        return jsonify({
            'response': reply_text,
            'model': MODEL,
            'session_id': session_id
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
def list_sessions():
    """Ambil daftar sesi chat yang tersimpan"""
    history = _load_history()
    sessions_meta = []

    for session in history.get('sessions', []):
        first_user = next((m for m in session.get('messages', []) if m.get('role') == 'user'), None)
        sessions_meta.append({
            'id': session.get('id'),
            'title': session.get('title') or _build_title(session),
            'created_at': session.get('created_at'),
            'updated_at': session.get('updated_at'),
            'first_message': (first_user.get('content', '') if first_user else '')[:120],
            'message_count': len(session.get('messages', []))
        })

    return jsonify({'sessions': sessions_meta})


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Ambil detail sebuah sesi beserta pesan-pesannya"""
    history = _load_history()
    session = next((s for s in history.get('sessions', []) if s.get('id') == session_id), None)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    session['title'] = session.get('title') or _build_title(session)
    return jsonify(session)

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

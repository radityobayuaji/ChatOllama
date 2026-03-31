from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

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
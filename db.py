"""SQLite helper module for chat history storage."""
import json
import os
import sqlite3

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_FILE = os.path.join(DATA_DIR, 'chat_history.db')
JSON_FILE = os.path.join(DATA_DIR, 'chat_history.json')
MAX_SESSIONS = 50


def get_connection():
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist, then migrate from JSON if needed."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
    _migrate_from_json()


def _migrate_from_json():
    """Migrate data/chat_history.json into SQLite once, then leave JSON in place."""
    if not os.path.exists(JSON_FILE):
        return

    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            sessions = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    if not sessions:
        return

    with get_connection() as conn:
        # Only migrate sessions that are not already in the DB
        for s in sessions:
            existing = conn.execute(
                'SELECT id FROM sessions WHERE id = ?', (s['id'],)
            ).fetchone()
            if existing:
                continue
            conn.execute(
                'INSERT INTO sessions (id, created_at, title) VALUES (?, ?, ?)',
                (s['id'], s.get('created_at', ''), s.get('title', ''))
            )
            session_created_at = s.get('created_at', '')
            for msg in s.get('messages', []):
                conn.execute(
                    'INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)',
                    (s['id'], msg.get('role', ''), msg.get('content', ''), session_created_at)
                )
        conn.commit()

    _enforce_max_sessions()


def get_sessions():
    """Return session summaries ordered newest-first (no message bodies)."""
    with get_connection() as conn:
        rows = conn.execute('''
            SELECT s.id, s.title, s.created_at,
                   COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        ''').fetchall()
    return [dict(r) for r in rows]


def get_session(session_id):
    """Return a session dict with its messages, or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            'SELECT id, title, created_at FROM sessions WHERE id = ?',
            (session_id,)
        ).fetchone()
        if row is None:
            return None
        session = dict(row)
        msg_rows = conn.execute(
            'SELECT role, content FROM messages WHERE session_id = ? ORDER BY id',
            (session_id,)
        ).fetchall()
        session['messages'] = [dict(m) for m in msg_rows]
    return session


def save_session(session):
    """Upsert a session and its messages, then enforce MAX_SESSIONS."""
    with get_connection() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO sessions (id, created_at, title) VALUES (?, ?, ?)',
            (session['id'], session.get('created_at', ''), session.get('title', ''))
        )
        # Replace all messages for this session
        conn.execute('DELETE FROM messages WHERE session_id = ?', (session['id'],))
        session_created_at = session.get('created_at', '')
        for msg in session.get('messages', []):
            conn.execute(
                'INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)',
                (session['id'], msg.get('role', ''), msg.get('content', ''), session_created_at)
            )
        conn.commit()
    _enforce_max_sessions()


def _enforce_max_sessions():
    """Delete sessions (and their messages) beyond MAX_SESSIONS oldest entries."""
    with get_connection() as conn:
        rows = conn.execute(
            'SELECT id FROM sessions ORDER BY created_at DESC'
        ).fetchall()
        if len(rows) <= MAX_SESSIONS:
            return
        ids_to_delete = [(r['id'],) for r in rows[MAX_SESSIONS:]]
        conn.executemany('DELETE FROM messages WHERE session_id = ?', ids_to_delete)
        conn.executemany('DELETE FROM sessions WHERE id = ?', ids_to_delete)
        conn.commit()

"""
TaskFlow - Flask REST API Backend
SQLite-backed to-do list with full CRUD support.
Run: python app.py  →  open http://127.0.0.1:5000
"""

import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

# ── App setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join('/tmp' if os.environ.get('VERCEL') else BASE_DIR, 'tasks.db')

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)  # allow cross-origin requests during development


@app.errorhandler(RuntimeError)
def handle_runtime_error(error):
    """Return configuration errors in the format expected by the frontend."""
    return jsonify({'ok': False, 'error': str(error)}), 503


# ── Database helpers ─────────────────────────────────────────────────────────
def get_db():
    """Open a DB connection with row-as-dict support."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if psycopg2 is None:
            raise RuntimeError('psycopg2 is required when DATABASE_URL is configured')
        connection = PostgresConnection(database_url)
        init_db(connection)
        return connection
    if os.environ.get('VERCEL'):
        raise RuntimeError('DATABASE_URL must be configured on Vercel for persistent task storage')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


class PostgresConnection:
    def __init__(self, database_url):
        self.connection = psycopg2.connect(database_url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.close()

    def execute(self, query, parameters=()):
        query = query.replace('?', '%s')
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, parameters)
        return cursor

    def commit(self):
        self.connection.commit()


def init_db(connection=None):
    """Create the tasks table if it doesn't already exist."""
    if connection is None:
        with sqlite3.connect(DB_PATH) as conn:
            _init_db_schema(conn)
        return
    _init_db_schema(connection)


def _init_db_schema(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id         TEXT    PRIMARY KEY,
            title      TEXT    NOT NULL,
            note       TEXT    DEFAULT '',
            priority   TEXT    DEFAULT 'medium',
            category   TEXT    DEFAULT 'General',
            due        TEXT,
            completed  INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            reminder   INTEGER
        )
    ''')
    # Add reminder column if upgrading an existing DB
    if isinstance(conn, PostgresConnection):
        conn.execute('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reminder INTEGER')
    else:
        try:
            conn.execute('ALTER TABLE tasks ADD COLUMN reminder INTEGER')
        except Exception:
            pass  # column already exists
    conn.commit()


init_db()


def row_to_dict(row):
    """Convert a SQLite Row to a JSON-friendly dict matching the frontend schema."""
    d = dict(row)
    d['completed'] = bool(d['completed'])   # 0/1  →  False/True
    d['createdAt'] = d.pop('created_at')    # snake_case → camelCase for JS
    # reminder stays as integer ms timestamp (or None)
    return d


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the TaskFlow frontend."""
    return send_from_directory(BASE_DIR, 'index.html')


# ── Task collection endpoints ─────────────────────────────────────────────────

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Return all tasks ordered by creation date (newest first)."""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM tasks ORDER BY created_at DESC'
        ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Create a new task."""
    data = request.get_json(force=True)
    with get_db() as conn:
        conn.execute(
            '''INSERT INTO tasks
               (id, title, note, priority, category, due, completed, created_at, reminder)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                data['id'],
                data['title'],
                data.get('note', ''),
                data.get('priority', 'medium'),
                data.get('category', 'General'),
                data.get('due'),          # None is stored as NULL
                1 if data.get('completed') else 0,
                data['createdAt'],
                data.get('reminder'),
            )
        )
        conn.commit()
    return jsonify({'ok': True}), 201


# ── Bulk-action endpoints  (must come BEFORE /<task_id> to avoid conflicts) ──

@app.route('/api/tasks/completed', methods=['DELETE'])
def clear_completed():
    """Delete all completed tasks."""
    with get_db() as conn:
        conn.execute('DELETE FROM tasks WHERE completed = 1')
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/tasks/complete-all', methods=['PUT'])
def complete_all():
    """Mark every active task as complete."""
    with get_db() as conn:
        conn.execute('UPDATE tasks SET completed = 1 WHERE completed = 0')
        conn.commit()
    return jsonify({'ok': True})


# ── Single-task endpoints ─────────────────────────────────────────────────────

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task's fields (title, note, priority, category, due, completed)."""
    data = request.get_json(force=True)
    with get_db() as conn:
        conn.execute(
            '''UPDATE tasks
               SET title=?, note=?, priority=?, category=?, due=?, completed=?, reminder=?
               WHERE id=?''',
            (
                data['title'],
                data.get('note', ''),
                data.get('priority', 'medium'),
                data.get('category', 'General'),
                data.get('due'),
                1 if data.get('completed') else 0,
                data.get('reminder'),
                task_id,
            )
        )
        conn.commit()
    return jsonify({'ok': True})


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Permanently delete a single task."""
    with get_db() as conn:
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
    return jsonify({'ok': True})


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print()
    print('  [*]  TaskFlow backend started!')
    print('  [>]  Open --> http://127.0.0.1:5000')
    print('  [db] Database --> tasks.db')
    print('  Press  Ctrl+C  to stop.')
    print()
    app.run(debug=True, port=5000)

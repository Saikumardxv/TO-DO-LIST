"""
TaskFlow - Flask REST API Backend
SQLite-backed to-do list with full CRUD support.
Run: python app.py  →  open http://127.0.0.1:5000
"""

import os
import uuid
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

# ── App setup ────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join('/tmp' if os.environ.get('VERCEL') else BASE_DIR, 'tasks.db')
UPLOAD_DIR  = os.path.join(BASE_DIR, 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)  # allow cross-origin requests during development

# Allowed file types for upload
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg',  # images
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', # documents
    'txt', 'csv', 'md', 'rtf',                            # text
    'zip', 'rar', '7z',                                   # archives
    'mp4', 'mp3', 'wav', 'ogg',                           # media
}
MAX_UPLOAD_MB = 20


@app.errorhandler(RuntimeError)
def handle_runtime_error(error):
    """Return configuration errors in the format expected by the frontend."""
    return jsonify({'ok': False, 'error': str(error)}), 503


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS


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
    """Create the tables if they don't already exist."""
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
            created_at BIGINT NOT NULL,
            reminder   BIGINT
        )
    ''')
    # Add reminder column if upgrading an existing DB
    if isinstance(conn, PostgresConnection):
        conn.execute('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reminder INTEGER')
        conn.execute('ALTER TABLE tasks ALTER COLUMN created_at TYPE BIGINT')
        conn.execute('ALTER TABLE tasks ALTER COLUMN reminder TYPE BIGINT')
    else:
        try:
            conn.execute('ALTER TABLE tasks ADD COLUMN reminder INTEGER')
        except Exception:
            pass  # column already exists

    # ── Task Attachments table ─────────────────────────────────────────────
    conn.execute('''
        CREATE TABLE IF NOT EXISTS task_attachments (
            id            TEXT    PRIMARY KEY,
            task_id       TEXT    NOT NULL,
            filename      TEXT    NOT NULL,
            original_name TEXT    NOT NULL,
            mime_type     TEXT    DEFAULT 'application/octet-stream',
            file_size     INTEGER DEFAULT 0,
            created_at    BIGINT  NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    ''')
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
    """Permanently delete a single task and its attachments."""
    with get_db() as conn:
        # Remove physical files first
        rows = conn.execute(
            'SELECT filename FROM task_attachments WHERE task_id = ?', (task_id,)
        ).fetchall()
        for row in rows:
            fpath = os.path.join(UPLOAD_DIR, dict(row)['filename'])
            if os.path.exists(fpath):
                os.remove(fpath)
        conn.execute('DELETE FROM task_attachments WHERE task_id = ?', (task_id,))
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
    return jsonify({'ok': True})


# ── Attachment endpoints ──────────────────────────────────────────────────────

@app.route('/api/tasks/<task_id>/attachments', methods=['GET'])
def get_attachments(task_id):
    """Return all attachments for a task."""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM task_attachments WHERE task_id = ? ORDER BY created_at ASC',
            (task_id,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/tasks/<task_id>/attachments', methods=['POST'])
def upload_attachment(task_id):
    """Upload a file and attach it to a task."""
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file part'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'ok': False, 'error': 'No file selected'}), 400
    if not allowed_file(f.filename):
        return jsonify({'ok': False, 'error': 'File type not allowed'}), 400

    original_name = secure_filename(f.filename)
    ext           = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    stored_name   = str(uuid.uuid4()) + ('.' + ext if ext else '')
    save_path     = os.path.join(UPLOAD_DIR, stored_name)
    f.save(save_path)
    file_size = os.path.getsize(save_path)

    if file_size > MAX_UPLOAD_MB * 1024 * 1024:
        os.remove(save_path)
        return jsonify({'ok': False, 'error': f'File exceeds {MAX_UPLOAD_MB} MB limit'}), 413

    import time
    att_id = str(uuid.uuid4()).replace('-', '')
    mime   = f.mimetype or 'application/octet-stream'

    with get_db() as conn:
        conn.execute(
            '''INSERT INTO task_attachments
               (id, task_id, filename, original_name, mime_type, file_size, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (att_id, task_id, stored_name, original_name, mime, file_size, int(time.time() * 1000))
        )
        conn.commit()

    return jsonify({
        'ok': True,
        'attachment': {
            'id': att_id, 'task_id': task_id,
            'filename': stored_name, 'original_name': original_name,
            'mime_type': mime, 'file_size': file_size,
        }
    }), 201


@app.route('/api/attachments/<att_id>/file', methods=['GET'])
def serve_attachment(att_id):
    """Serve an attachment file for viewing/download."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM task_attachments WHERE id = ?', (att_id,)
        ).fetchone()
    if not row:
        abort(404)
    row = dict(row)
    return send_from_directory(
        UPLOAD_DIR, row['filename'],
        as_attachment=False,
        download_name=row['original_name'],
        mimetype=row['mime_type']
    )


@app.route('/api/attachments/<att_id>', methods=['DELETE'])
def delete_attachment(att_id):
    """Delete a single attachment."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT filename FROM task_attachments WHERE id = ?', (att_id,)
        ).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Not found'}), 404
        fpath = os.path.join(UPLOAD_DIR, dict(row)['filename'])
        if os.path.exists(fpath):
            os.remove(fpath)
        conn.execute('DELETE FROM task_attachments WHERE id = ?', (att_id,))
        conn.commit()
    return jsonify({'ok': True})


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print()
    print('  [*]  TaskFlow backend started!')
    print('  [>]  Open --> http://127.0.0.1:5000')
    print('  [db] Database --> tasks.db')
    print('  [UP] Uploads --> uploads/')
    print('  Press  Ctrl+C  to stop.')
    print()
    app.run(debug=True, port=5000)

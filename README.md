# ✅ TaskFlow — Premium To-Do List

A full-stack To-Do List app with a beautiful black & white UI, Flask REST API backend, SQLite persistence, and browser reminder notifications.

## 🚀 Features

- ➕ Add tasks with title, note, priority, category & due date
- ✅ Mark tasks complete / incomplete
- ✏️ Edit tasks inline via modal
- 🗑️ Delete individual tasks or clear all completed
- 🔔 **Task Reminders** — set a date+time and get a browser notification
- 📊 Stats bar (total, active, done, high priority)
- 🔍 Search, filter by status/priority/category, sort tasks
- 🎨 Black & white theme with light/dark toggle
- 💾 Data persisted in SQLite database (survives refresh)

## 🗂️ Project Structure

```
TO DO list/
├── app.py              # Flask REST API backend
├── index.html          # Frontend (HTML/CSS/JS)
├── To do list.py       # Terminal-based CLI version
├── requirements.txt    # Python dependencies
└── tasks.db            # SQLite database (auto-created)
```

## ⚙️ Setup & Run

### 1. Install dependencies
```bash
pip install flask flask-cors
```

### 2. Start the server
```bash
python app.py
```

### 3. Open in browser
```
http://127.0.0.1:5000
```

## 🔌 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/tasks` | Get all tasks |
| POST | `/api/tasks` | Create a task |
| PUT | `/api/tasks/<id>` | Update a task |
| DELETE | `/api/tasks/<id>` | Delete a task |
| DELETE | `/api/tasks/completed` | Clear completed |
| PUT | `/api/tasks/complete-all` | Mark all complete |

## 🖥️ Terminal Version

Run the standalone CLI version (no server needed):
```bash
python "To do list.py"
```

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3 (Vanilla), JavaScript (ES2020+)
- **Backend:** Python, Flask, Flask-CORS
- **Database:** SQLite (via Python `sqlite3`)
- **Notifications:** Web Notifications API

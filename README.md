# ✅ TaskFlow — Premium To-Do List

A full-stack To-Do List app with a beautiful black & white UI, Flask REST API backend, SQLite persistence, and browser reminder notifications.

On Vercel, configure a persistent PostgreSQL connection in the `DATABASE_URL` environment variable. Vercel's `/tmp` filesystem is temporary, so the app rejects API writes there when this variable is missing instead of silently losing tasks.

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

For Vercel, set `DATABASE_URL` to the connection string from your hosted PostgreSQL provider, then redeploy.

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
- **Database:** SQLite locally; PostgreSQL on Vercel via `DATABASE_URL`
- **Notifications:** Web Notifications API

Reminders are delivered while the HTTPS app is open and browser notifications are permitted. Delivery after closing the site requires a Web Push service and is not provided by the browser timer alone.

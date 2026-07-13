"""
Session management: each conversation is saved as a named session.
Sessions live in <project>/.coder/sessions/*.json
"""
import json
import os
import re
from datetime import datetime


def sessions_dir(project_root="."):
    """Where sessions are stored for a project."""
    folder = os.path.join(os.path.abspath(project_root), ".coder", "sessions")
    os.makedirs(folder, exist_ok=True)
    return folder


def _slugify(text, max_len=40):
    """Convert 'Add login endpoint' → 'add-login-endpoint'."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_len] or "session"


def new_session_name(topic=""):
    """Generate a filename like '2024-01-15_1430_add-login.json'."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    slug = _slugify(topic) if topic else "session"
    return f"{stamp}_{slug}.json"


def list_sessions(project_root="."):
    """Return session filenames, newest first."""
    folder = sessions_dir(project_root)
    files = [f for f in os.listdir(folder) if f.endswith(".json")]
    files.sort(reverse=True)
    return files


def load_session(name, project_root="."):
    """Load a session by filename. Returns the message list or [] if missing."""
    path = os.path.join(sessions_dir(project_root), name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except Exception:
        return []


def save_session(name, messages, project_root="."):
    """Save messages under the given session name."""
    path = os.path.join(sessions_dir(project_root), name)
    data = {
        "name": name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "messages": messages,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def delete_session(name, project_root="."):
    """Delete a session file. Returns True if deleted."""
    path = os.path.join(sessions_dir(project_root), name)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def session_preview(name, project_root="."):
    """Return a short preview: first user message, message count."""
    messages = load_session(name, project_root)
    count = len(messages)
    first_user = next(
        (m["content"] for m in messages if m["role"] == "user"),
        "(no user messages)"
    )
    preview = first_user.replace("\n", " ")[:80]
    return f"{count} msgs — {preview}"

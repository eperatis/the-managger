"""
Session management: each conversation is saved as a named session.
Sessions live in <project>/.coder/sessions/*.json
"""
import json
import os
import re
from datetime import datetime


SESSION_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def sessions_dir(project_root="."):
    """Where sessions are stored for a project."""
    coder_folder = os.path.join(os.path.abspath(project_root), ".coder")
    folder = os.path.join(coder_folder, "sessions")
    os.makedirs(folder, exist_ok=True)
    # Sessions contain project file contents; keep them out of the project's git repository.
    gitignore_path = os.path.join(coder_folder, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w", encoding="utf-8") as gitignore_file:
            gitignore_file.write("*\n")
    return folder


def session_filename(name):
    """Turn 'my-session' or 'my-session.json' into a validated filename that cannot leave the sessions folder."""
    stem = name.removesuffix(".json")
    if not SESSION_NAME_PATTERN.fullmatch(stem):
        raise ValueError(f"Invalid session name {name!r}: use only letters, digits, '-' and '_'")
    return stem + ".json"


def session_path(name, project_root):
    return os.path.join(sessions_dir(project_root), session_filename(name))


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
    """Load a session's message list. Raises if the file is missing or malformed."""
    path = session_path(name, project_root)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Session not found: {name}")
    with open(path, "r", encoding="utf-8") as session_file:
        session_data = json.load(session_file)
    if not isinstance(session_data.get("messages"), list):
        raise ValueError(f"Session file {name} has no 'messages' list")
    return session_data["messages"]


def save_session(name, messages, project_root="."):
    """Save messages under the given session name."""
    path = session_path(name, project_root)
    data = {
        "name": name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "messages": messages,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def delete_session(name, project_root="."):
    path = session_path(name, project_root)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Session not found: {name}")
    os.remove(path)


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

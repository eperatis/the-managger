import os

IGNORED_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", "dist", "build"}
ALLOWED_EXT = {".py", ".js", ".ts", ".html", ".css", ".md",
               ".json", ".txt", ".yml", ".yaml", ".toml", ".sh"}


def list_files(root="."):
    """List all relevant files in the project."""
    found = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in ALLOWED_EXT:
                path = os.path.relpath(os.path.join(dirpath, f), root)
                found.append(path)
    return found


def read_file(path):
    """Read the content of a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading {path}: {e}]"


def write_file(path, content):
    """Write content to a file (creates directories if needed)."""
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def project_summary(root=".", max_chars_per_file=3000):
    """Return a summary of the project files with content."""
    files = list_files(root)
    summary = []
    for f in files:
        content = read_file(os.path.join(root, f))
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n...[truncated]"
        summary.append(f"### File: {f}\n```\n{content}\n```")
    return "\n\n".join(summary)


def search(query, root="."):
    """Search for a string in all project files."""
    results = []
    for f in list_files(root):
        content = read_file(os.path.join(root, f))
        if query.lower() in content.lower():
            results.append(f)
    return results

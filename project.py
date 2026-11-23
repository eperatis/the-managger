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


def resolve_path_inside_project(project_root, path):
    """Return the absolute real path, or raise if it (after symlinks and '..') is outside project_root."""
    real_project_root = os.path.realpath(project_root)
    resolved_path = os.path.realpath(os.path.join(real_project_root, path))
    if os.path.commonpath([real_project_root, resolved_path]) != real_project_root:
        raise ValueError(f"Refusing path outside the project: {path}")
    return resolved_path


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            return file_handle.read()
    except UnicodeDecodeError as decode_error:
        raise ValueError(f"Cannot read {path}: not valid UTF-8 text") from decode_error


def write_file(path, content):
    """Write content to a file (creates directories if needed)."""
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def format_project_file_list(root="."):
    return "\n".join(sorted(list_files(root)))


def read_project_md(root="."):
    """Return PROJECT.md content, or None when the project has no PROJECT.md (it is optional)."""
    project_md_path = os.path.join(root, "PROJECT.md")
    if not os.path.isfile(project_md_path):
        return None
    return read_file(project_md_path)


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
    """Case-insensitive search. Returns (relative_path, line_number, line_text) tuples."""
    lowercase_query = query.lower()
    matches = []
    for relative_path in list_files(root):
        content = read_file(os.path.join(root, relative_path))
        for line_number, line_text in enumerate(content.splitlines(), start=1):
            if lowercase_query in line_text.lower():
                matches.append((relative_path, line_number, line_text.strip()))
    return matches

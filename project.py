import os

IGNORED_DIRECTORY_NAMES = {".git", "__pycache__", "node_modules", "venv", ".venv", "dist", "build"}
ALLOWED_FILE_EXTENSIONS = {".py", ".js", ".ts", ".html", ".css", ".md",
                           ".json", ".txt", ".yml", ".yaml", ".toml", ".sh"}


def list_files(root="."):
    """Relative paths of project files with an allowed extension, skipping ignored directories."""
    found_paths = []
    for directory_path, directory_names, file_names in os.walk(root):
        directory_names[:] = [name for name in directory_names if name not in IGNORED_DIRECTORY_NAMES]
        for file_name in file_names:
            if os.path.splitext(file_name)[1] in ALLOWED_FILE_EXTENSIONS:
                found_paths.append(os.path.relpath(os.path.join(directory_path, file_name), root))
    return found_paths


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
    """Write content to a file, creating parent directories if needed."""
    directory_name = os.path.dirname(path)
    if directory_name:
        os.makedirs(directory_name, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        file_handle.write(content)


def format_project_file_list(root="."):
    return "\n".join(sorted(list_files(root)))


def read_project_md(root="."):
    """Return PROJECT.md content, or None when the project has no PROJECT.md (it is optional)."""
    project_md_path = os.path.join(root, "PROJECT.md")
    if not os.path.isfile(project_md_path):
        return None
    return read_file(project_md_path)


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

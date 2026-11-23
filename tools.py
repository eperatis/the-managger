import os

from project import read_file, resolve_path_inside_project, search

MAX_TOOL_RESULT_CHARACTERS = 20000


def require_string_argument(tool_args, argument_name):
    value = tool_args.get(argument_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing or non-string argument '{argument_name}'")
    return value


def read_file_tool(tool_args, project_root):
    relative_path = require_string_argument(tool_args, "path")
    full_path = resolve_path_inside_project(project_root, relative_path)
    if not os.path.isfile(full_path):
        raise ValueError(f"Not a file: {relative_path}")
    return read_file(full_path)


def search_tool(tool_args, project_root):
    query = require_string_argument(tool_args, "query")
    matches = search(query, project_root)
    if not matches:
        return f"No matches for {query!r}"
    return "\n".join(f"{relative_path}:{line_number}: {line_text}"
                     for relative_path, line_number, line_text in matches)


# Tool name -> (description, argument descriptions, implementation)
TOOLS = {
    "read_file": (
        "Read the full content of one project file.",
        {"path": "file path relative to the project root"},
        read_file_tool,
    ),
    "search": (
        "Case-insensitive text search across all project files. Returns 'path:line: text' lines.",
        {"query": "text to search for"},
        search_tool,
    ),
}


def tools_description():
    lines = []
    for tool_name, (description, argument_descriptions, _) in TOOLS.items():
        arguments_text = ", ".join(f'"{argument}": {meaning}'
                                   for argument, meaning in argument_descriptions.items())
        lines.append(f"- {tool_name}: {description} Args: {{{arguments_text}}}")
    return "\n".join(lines)


def run_tool(tool_name, tool_args, project_root):
    """Run a tool and return its result text. Raises ValueError for unknown tools or bad arguments."""
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool '{tool_name}'. Available: {', '.join(TOOLS)}")
    _, _, implementation = TOOLS[tool_name]
    result = implementation(tool_args, project_root)
    if len(result) > MAX_TOOL_RESULT_CHARACTERS:
        result = result[:MAX_TOOL_RESULT_CHARACTERS] + "\n...[truncated]"
    return result

"""Tools offered to the model through Ollama's native tool calling."""
import os

from project import search

MAX_TOOL_RESULT_CHARACTERS = 20000


def require_string_argument(tool_args, argument_name, allow_empty=False):
    value = tool_args.get(argument_name)
    if not isinstance(value, str) or (not value and not allow_empty):
        raise ValueError(f"Missing or non-string argument '{argument_name}'")
    return value


def read_file_tool(tool_args, staged_edits):
    full_path, display_path = staged_edits.resolve(require_string_argument(tool_args, "path"))
    if os.path.isdir(full_path):
        raise ValueError(f"{display_path} is a directory, not a file")
    content = staged_edits.current_content(full_path)
    if content is None:
        raise ValueError(f"File not found: {display_path}")
    return content


def search_tool(tool_args, staged_edits):
    query = require_string_argument(tool_args, "query")
    matches = search(query, staged_edits.project_root)
    if not matches:
        return f"No matches for {query!r}"
    return "\n".join(f"{relative_path}:{line_number}: {line_text}"
                     for relative_path, line_number, line_text in matches)


def replace_in_file_tool(tool_args, staged_edits):
    staged_edit = staged_edits.stage(require_string_argument(tool_args, "path"),
                                     require_string_argument(tool_args, "old_text"),
                                     require_string_argument(tool_args, "new_text", allow_empty=True))
    return (f"Staged edit {staged_edit.edit_number} for {staged_edit.display_path}. "
            "The user reviews staged edits after your final reply.")


def create_file_tool(tool_args, staged_edits):
    staged_edit = staged_edits.stage(require_string_argument(tool_args, "path"), None,
                                     require_string_argument(tool_args, "content", allow_empty=True))
    return (f"Staged edit {staged_edit.edit_number}: create {staged_edit.display_path}. "
            "The user reviews staged edits after your final reply.")


# Tool name -> (description, {argument name: description}, implementation). Every argument is a required string.
TOOLS = {
    "read_file": (
        "Read a project file. Shows your staged edits.",
        {"path": "file path relative to the project root"},
        read_file_tool,
    ),
    "search": (
        "Case-insensitive text search in all project files on disk. Returns 'path:line: text' lines.",
        {"query": "text to search for"},
        search_tool,
    ),
    "replace_in_file": (
        "Change an existing file by replacing old_text with new_text. old_text must be copied exactly "
        "from read_file output and occur exactly once; include surrounding lines to make it unique. "
        "Use one call per change. Changes are staged for the user to approve.",
        {"path": "file path relative to the project root",
         "old_text": "exact existing text to replace",
         "new_text": "replacement text; empty to delete old_text"},
        replace_in_file_tool,
    ),
    "create_file": (
        "Create a new file. Fails if the file exists. Staged for the user to approve.",
        {"path": "file path relative to the project root",
         "content": "full content of the new file"},
        create_file_tool,
    ),
}


def ollama_tool_schemas():
    return [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {argument_name: {"type": "string", "description": argument_description}
                                   for argument_name, argument_description in argument_descriptions.items()},
                    "required": list(argument_descriptions),
                },
            },
        }
        for tool_name, (description, argument_descriptions, _) in TOOLS.items()
    ]


def run_tool(tool_name, tool_args, staged_edits):
    """Run a tool and return its result text. Raises ValueError for unknown tools or bad arguments."""
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool '{tool_name}'. Available: {', '.join(TOOLS)}")
    if not isinstance(tool_args, dict):
        raise ValueError("Tool arguments must be an object")
    _, _, implementation = TOOLS[tool_name]
    result = implementation(tool_args, staged_edits)
    if len(result) > MAX_TOOL_RESULT_CHARACTERS:
        result = result[:MAX_TOOL_RESULT_CHARACTERS] + "\n...[truncated]"
    return result

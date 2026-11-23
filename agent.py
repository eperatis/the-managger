from rich.console import Console

from file_edits import StagedEdits
from ollama_client import chat
from terminal_text import safe_for_rich_markup
from tools import ollama_tool_schemas, run_tool

console = Console()

MAX_MODEL_CALLS_PER_TURN = 10


def describe_tool_call(tool_name, tool_args):
    """One short line for the user, e.g. 'replace_in_file app.py'; long arguments like old_text are left out."""
    if not isinstance(tool_args, dict):
        return tool_name
    short_argument = tool_args.get("path", tool_args.get("query", ""))
    return f"{tool_name} {short_argument}" if isinstance(short_argument, str) else tool_name


def agent_loop(history, project_root):
    """Run one user turn: the model calls tools until it replies without one. Returns the edits it staged.

    Appends every assistant message and tool result to history. Tool errors are returned to the model
    so it can correct itself, and shown to the user.
    """
    staged_edits = StagedEdits(project_root)
    tool_schemas = ollama_tool_schemas()
    for _ in range(MAX_MODEL_CALLS_PER_TURN):
        assistant_message = chat(history, tool_schemas)
        history.append(assistant_message)
        tool_calls = assistant_message.get("tool_calls", [])
        if not tool_calls:
            return staged_edits

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]
            tool_call_description = safe_for_rich_markup(describe_tool_call(tool_name, tool_args))
            try:
                tool_result = run_tool(tool_name, tool_args, staged_edits)
                console.print(f"[dim]> {tool_call_description}[/dim]")
            except (ValueError, OSError) as tool_error:
                tool_result = f"Error: {tool_error}"
                console.print(f"[red]> {tool_call_description}: {safe_for_rich_markup(str(tool_error))}[/red]")
            history.append({"role": "tool", "tool_name": tool_name, "content": tool_result})

    raise RuntimeError(f"Model did not finish after {MAX_MODEL_CALLS_PER_TURN} calls in one turn")

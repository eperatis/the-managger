import json
import re

from rich.console import Console

from file_edits import EditPlanError, parse_edit_blocks, plan_edits
from ollama_client import chat
from terminal_text import safe_for_rich_markup
from tools import run_tool

console = Console()

TOOL_CALL_PATTERN = re.compile(r"<<<TOOL>>>\s*(.*?)\s*<<<END>>>", re.DOTALL)
MAX_MODEL_CALLS_PER_TURN = 10


def parse_tool_call(tool_call_json):
    """Parse '{"name": ..., "args": {...}}'. Raises ValueError when malformed."""
    tool_call = json.loads(tool_call_json)
    if not isinstance(tool_call, dict):
        raise ValueError("Tool call must be a JSON object")
    if not isinstance(tool_call.get("name"), str):
        raise ValueError("Tool call needs a string 'name'")
    if not isinstance(tool_call.get("args"), dict):
        raise ValueError("Tool call needs an 'args' object")
    return tool_call["name"], tool_call["args"]


def agent_loop(history, project_root):
    """Let the model call tools until it gives a final reply whose edit blocks all apply; return their EditPlan.

    Edit blocks that cannot be applied are sent back to the model to fix. Appends every assistant reply,
    tool result and edit error to history.
    """
    for _ in range(MAX_MODEL_CALLS_PER_TURN):
        reply = chat(history)
        history.append({"role": "assistant", "content": reply})

        tool_call_match = TOOL_CALL_PATTERN.search(reply)
        if not tool_call_match:
            try:
                return plan_edits(parse_edit_blocks(reply), project_root)
            except EditPlanError as plan_error:
                console.print(f"[red]Proposed edits rejected, asking the model to fix them:\n"
                              f"{safe_for_rich_markup(str(plan_error))}[/red]")
                history.append({"role": "user", "content": (
                    f"Your edits could not be applied:\n{plan_error}\n"
                    "Send ALL your edit blocks again, corrected. SEARCH text must be copied exactly "
                    "from the current file and match exactly one place.")})
                continue

        # Tool errors go back to the model so it can correct the call; they are also shown to the user.
        try:
            tool_name, tool_args = parse_tool_call(tool_call_match.group(1))
            tool_result = run_tool(tool_name, tool_args, project_root)
            console.print(f"[dim]Tool {safe_for_rich_markup(tool_name)}: {len(tool_result)} characters returned[/dim]")
        except (ValueError, OSError) as tool_error:
            tool_result = f"Tool error: {tool_error}"
            console.print(f"[red]{safe_for_rich_markup(tool_result)}[/red]")

        history.append({"role": "user", "content": f"Tool result:\n{tool_result}"})

    raise RuntimeError(f"Model did not finish after {MAX_MODEL_CALLS_PER_TURN} calls in one turn")

import os
import re
import sys
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Prompt

from project import (list_files, read_file, write_file,
                     project_tree, read_project_md, search)
from diff_tool import show_diff
from session import (list_sessions, load_session, save_session,
                     delete_session, new_session_name, session_preview)
from tools import tools_description
from agent import agent_loop

console = Console()

SYSTEM_PROMPT_TEMPLATE = """You are a helpful coding assistant running in a terminal.
You have access to the user's project files via TOOLS.

## Available tools

{tools}

## How to call a tool

Output ONE tool call, then STOP. Format:

<<<TOOL>>>
{{"name": "tool_name", "args": {{...}}}}
<<<END>>>

You will receive the tool result in the next message, then you can call
another tool or write your final answer.

## How to modify code

When you want to CREATE or MODIFY files, respond with blocks (not tool calls):

<<<FILE: path/to/file.py>>>
<full new content>
<<<END>>>

Rules:
- Explore with tools BEFORE proposing changes. Don't guess file contents.
- Always output the ENTIRE new file, not just changed lines.
- Be concise. Only read files you actually need.
- For simple questions, answer directly without tools.
"""


FILE_BLOCK_PATTERN = re.compile(
    r"<<<FILE:\s*(.+?)>>>\n(.*?)<<<END>>>", re.DOTALL
)


def parse_file_blocks(text):
    return [(p.strip(), c) for p, c in FILE_BLOCK_PATTERN.findall(text)]


def handle_file_changes(text, project_root):
    blocks = parse_file_blocks(text)
    if not blocks:
        return

    console.print("\n[bold cyan]Proposed changes:[/bold cyan]")
    for path, new_content in blocks:
        full_path = os.path.join(project_root, path)
        old_content = read_file(full_path) if os.path.exists(full_path) else ""
        show_diff(old_content, new_content, path)

    answer = Prompt.ask("\n[bold yellow]Apply changes?[/bold yellow]",
                        choices=["y", "n"], default="n")
    if answer == "y":
        for path, new_content in blocks:
            full_path = os.path.join(project_root, path)
            write_file(full_path, new_content)
            console.print(f"[green]✓ Wrote {path}[/green]")
    else:
        console.print("[red]Changes discarded.[/red]")


def build_system_messages(project_root):
    """System prompt + project overview + PROJECT.md."""
    sys_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools=tools_description())
    msgs = [{"role": "system", "content": sys_prompt}]

    tree = project_tree(project_root)
    overview = f"## Project overview\nRoot: {project_root}\n\nFiles:\n{tree}"
    msgs.append({"role": "system", "content": overview})

    pmd = read_project_md(project_root)
    if pmd:
        msgs.append({"role": "system",
                     "content": f"## PROJECT.md (project rules)\n\n{pmd}"})
    return msgs


def print_help():
    console.print("""
[bold]Chat commands:[/bold]
  /files              List project files
  /search <query>     Search text in project
  /project            Show PROJECT.md
  /reload             Reload project context

[bold]Session commands:[/bold]
  /sessions           List saved sessions
  /save [name]        Save current session
  /load <name>        Load a session (replaces current)
  /new [topic]        Start a fresh session (discards current)
  /delete <name>      Delete a saved session
  /rename <name>      Rename current session

[bold]Other:[/bold]
  /help               Show this help
  /exit               Quit (asks to save)
""")


def prompt_save(current_name, messages, project_root):
    """Ask if the user wants to save the current session."""
    # Only offer to save if there was real conversation
    user_msgs = [m for m in messages if m["role"] == "user"]
    if not user_msgs:
        return
    ans = Prompt.ask("[yellow]Save this session?[/yellow]",
                     choices=["y", "n"], default="y")
    if ans == "y":
        name = current_name
        if not name:
            topic = user_msgs[0]["content"]
            name = new_session_name(topic)
        save_session(name, messages, project_root)
        console.print(f"[green]✓ Saved: {name}[/green]")



@dataclass
class ChatState:
    project_root: str
    history: list
    current_session_name: str | None = None


def handle_help_command(state, argument):
    print_help()


def handle_files_command(state, argument):
    for relative_path in list_files(state.project_root):
        console.print(f" - {relative_path}")


def handle_project_command(state, argument):
    project_md_content = read_project_md(state.project_root)
    console.print(project_md_content if project_md_content else "[dim]No PROJECT.md found[/dim]")


def handle_reload_command(state, argument):
    conversation_messages = [m for m in state.history if m["role"] != "system"]
    state.history = build_system_messages(state.project_root) + conversation_messages
    console.print("[yellow]Project context reloaded.[/yellow]")


def handle_search_command(state, query):
    matches = search(query, state.project_root)
    if not matches:
        console.print("[dim]No matches.[/dim]")
    for relative_path, line_number, line_text in matches:
        console.print(f" {relative_path}:{line_number}: {line_text}")


def handle_sessions_command(state, argument):
    session_names = list_sessions(state.project_root)
    if not session_names:
        console.print("[dim]No saved sessions.[/dim]")
    for session_name in session_names:
        console.print(f" [cyan]{session_name}[/cyan]")
        try:
            console.print(f"   {session_preview(session_name, state.project_root)}")
        except ValueError as preview_error:
            console.print(f"   [red]Unreadable session: {preview_error}[/red]")


def handle_save_command(state, requested_name):
    if requested_name:
        name = requested_name if requested_name.endswith(".json") else requested_name + ".json"
    elif state.current_session_name:
        name = state.current_session_name
    else:
        user_msgs = [m for m in state.history if m["role"] == "user"]
        topic = user_msgs[0]["content"] if user_msgs else ""
        name = new_session_name(topic)
    save_session(name, state.history, state.project_root)
    state.current_session_name = name
    console.print(f"[green]✓ Saved: {name}[/green]")


def handle_load_command(state, requested_name):
    name = requested_name if requested_name.endswith(".json") else requested_name + ".json"
    loaded_history = load_session(name, state.project_root)
    prompt_save(state.current_session_name, state.history, state.project_root)
    state.history = loaded_history
    state.current_session_name = name
    console.print(f"[green]✓ Loaded: {name}[/green]")
    console.print(f"[dim]{len(loaded_history)} messages restored[/dim]")


def handle_new_command(state, topic):
    prompt_save(state.current_session_name, state.history, state.project_root)
    state.history = build_system_messages(state.project_root)
    state.current_session_name = None
    if topic:
        console.print(f"[green]✓ New session on: {topic}[/green]")
    else:
        console.print("[green]✓ New session started[/green]")


def handle_delete_command(state, requested_name):
    name = requested_name if requested_name.endswith(".json") else requested_name + ".json"
    delete_session(name, state.project_root)
    console.print(f"[green]✓ Deleted {name}[/green]")
    if name == state.current_session_name:
        state.current_session_name = None


def handle_rename_command(state, requested_name):
    new_name = requested_name if requested_name.endswith(".json") else requested_name + ".json"
    save_session(new_name, state.history, state.project_root)
    previous_session_was_saved = state.current_session_name in list_sessions(state.project_root)
    if previous_session_was_saved and state.current_session_name != new_name:
        delete_session(state.current_session_name, state.project_root)
    state.current_session_name = new_name
    console.print(f"[green]✓ Renamed to {new_name}[/green]")


# Maps command -> (handler, argument usage or None when the command takes no required argument).
COMMAND_HANDLERS = {
    "/help": (handle_help_command, None),
    "/files": (handle_files_command, None),
    "/project": (handle_project_command, None),
    "/reload": (handle_reload_command, None),
    "/search": (handle_search_command, "<query>"),
    "/sessions": (handle_sessions_command, None),
    "/save": (handle_save_command, None),
    "/load": (handle_load_command, "<name>"),
    "/new": (handle_new_command, None),
    "/delete": (handle_delete_command, "<name>"),
    "/rename": (handle_rename_command, "<name>"),
}


def run_command(state, command_text):
    command_name, _, argument = command_text.partition(" ")
    argument = argument.strip()
    if command_name not in COMMAND_HANDLERS:
        console.print(f"[red]Unknown command: {command_name}. Type /help for commands.[/red]")
        return
    handler, required_argument_usage = COMMAND_HANDLERS[command_name]
    if required_argument_usage and not argument:
        console.print(f"[red]Usage: {command_name} {required_argument_usage}[/red]")
        return
    try:
        handler(state, argument)
    except (OSError, ValueError) as command_error:
        console.print(f"[red]{command_name} failed: {command_error}[/red]")


def run_chat_turn(state, user_input):
    history_length_before_turn = len(state.history)
    state.history.append({"role": "user", "content": user_input})

    try:
        final_reply = agent_loop(state.history, state.project_root)
    except Exception as turn_error:
        console.print(f"[red]Error: {type(turn_error).__name__}: {turn_error}[/red]")
        del state.history[history_length_before_turn:]
        return

    try:
        handle_file_changes(final_reply, state.project_root)
    except (OSError, ValueError) as file_change_error:
        console.print(f"[red]Changes not applied: {file_change_error}[/red]")


def main():
    project_root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not os.path.isdir(project_root):
        console.print(f"[red]Directory not found: {project_root}[/red]")
        sys.exit(1)

    console.print(f"[bold green]Coder Helper[/bold green] — {project_root}")
    file_count = len(list_files(project_root))
    project_md_note = "PROJECT.md ✓" if read_project_md(project_root) else "no PROJECT.md"
    session_count = len(list_sessions(project_root))
    console.print(f"[dim]{file_count} files · {project_md_note} · {session_count} saved sessions[/dim]")
    console.print("Type /help for commands, /new to start fresh.\n")

    state = ChatState(project_root=project_root, history=build_system_messages(project_root))

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print()
            prompt_save(state.current_session_name, state.history, project_root)
            break

        stripped_input = user_input.strip()
        if not stripped_input:
            continue
        if stripped_input == "/exit":
            prompt_save(state.current_session_name, state.history, project_root)
            break
        if stripped_input.startswith("/"):
            run_command(state, stripped_input)
        else:
            run_chat_turn(state, user_input)


if __name__ == "__main__":
    main()

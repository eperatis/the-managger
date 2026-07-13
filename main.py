import os
import re
import sys
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


def start_fresh(project_root, topic=""):
    """Return (system_msgs list, new session name or None)."""
    return build_system_messages(project_root), None


def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    project_root = os.path.abspath(project_root)

    if not os.path.isdir(project_root):
        console.print(f"[red]Directory not found: {project_root}[/red]")
        sys.exit(1)

    console.print(f"[bold green]Coder Helper[/bold green] — {project_root}")
    n_files = len(list_files(project_root))
    pmd_note = "PROJECT.md ✓" if read_project_md(project_root) else "no PROJECT.md"
    n_sessions = len(list_sessions(project_root))
    console.print(f"[dim]{n_files} files · {pmd_note} · {n_sessions} saved sessions[/dim]")
    console.print("Type /help for commands, /new to start fresh.\n")

    # Fresh session by default
    history = build_system_messages(project_root)
    current_session_name = None

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print()
            prompt_save(current_session_name, history, project_root)
            break

        if not user_input.strip():
            continue

        # --- Commands ---
        cmd = user_input.strip()

        if cmd == "/exit":
            prompt_save(current_session_name, history, project_root)
            break

        if cmd == "/help":
            print_help()
            continue

        if cmd == "/files":
            for f in list_files(project_root):
                console.print(f" - {f}")
            continue

        if cmd == "/project":
            pmd = read_project_md(project_root)
            console.print(pmd if pmd else "[dim]No PROJECT.md found[/dim]")
            continue

        if cmd == "/reload":
            sys_msgs = build_system_messages(project_root)
            history = sys_msgs + [h for h in history if h["role"] != "system"]
            console.print("[yellow]Project context reloaded.[/yellow]")
            continue

        if cmd.startswith("/search "):
            q = cmd[len("/search "):]
            hits = search(q, project_root)
            if hits:
                for p, ln, txt in hits:
                    console.print(f" {p}:{ln}: {txt}")
            else:
                console.print("[dim]No matches.[/dim]")
            continue

        # Session commands
        if cmd == "/sessions":
            sessions = list_sessions(project_root)
            if not sessions:
                console.print("[dim]No saved sessions.[/dim]")
            else:
                for s in sessions:
                    console.print(f" [cyan]{s}[/cyan]")
                    console.print(f"   {session_preview(s, project_root)}")
            continue

        if cmd.startswith("/save"):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 2:
                name = parts[1]
                if not name.endswith(".json"):
                    name += ".json"
                current_session_name = name
            elif not current_session_name:
                user_msgs = [m for m in history if m["role"] == "user"]
                topic = user_msgs[0]["content"] if user_msgs else ""
                current_session_name = new_session_name(topic)
            save_session(current_session_name, history, project_root)
            console.print(f"[green]✓ Saved: {current_session_name}[/green]")
            continue

        if cmd.startswith("/load "):
            name = cmd[len("/load "):].strip()
            if not name.endswith(".json"):
                name += ".json"
            loaded = load_session(name, project_root)
            if not loaded:
                console.print(f"[red]Session not found: {name}[/red]")
                continue
            # Offer to save current before switching
            prompt_save(current_session_name, history, project_root)
            history = loaded
            current_session_name = name
            console.print(f"[green]✓ Loaded: {name}[/green]")
            console.print(f"[dim]{len(history)} messages restored[/dim]")
            continue

        if cmd.startswith("/new"):
            prompt_save(current_session_name, history, project_root)
            parts = cmd.split(maxsplit=1)
            topic = parts[1] if len(parts) == 2 else ""
            history = build_system_messages(project_root)
            current_session_name = None
            if topic:
                console.print(f"[green]✓ New session on: {topic}[/green]")
            else:
                console.print("[green]✓ New session started[/green]")
            continue

        if cmd.startswith("/delete "):
            name = cmd[len("/delete "):].strip()
            if not name.endswith(".json"):
                name += ".json"
            if delete_session(name, project_root):
                console.print(f"[green]✓ Deleted {name}[/green]")
                if name == current_session_name:
                    current_session_name = None
            else:
                console.print(f"[red]Not found: {name}[/red]")
            continue

        if cmd.startswith("/rename "):
            new_name = cmd[len("/rename "):].strip()
            if not new_name.endswith(".json"):
                new_name += ".json"
            # If already saved under old name, delete old file
            if current_session_name:
                delete_session(current_session_name, project_root)
            current_session_name = new_name
            save_session(current_session_name, history, project_root)
            console.print(f"[green]✓ Renamed to {new_name}[/green]")
            continue

        # --- Normal chat turn ---
        history.append({"role": "user", "content": user_input})

        try:
            final_reply = agent_loop(history, project_root)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            history.pop()
            continue

        handle_file_changes(final_reply, project_root)


if __name__ == "__main__":
    main()

import os
import re
import sys
from rich.console import Console
from rich.prompt import Prompt

from ollama_client import chat
from project import list_files, read_file, write_file, project_summary, search
from diff_tool import show_diff
from memory import load_history, save_history, clear_history

console = Console()

SYSTEM_PROMPT = """You are a helpful coding assistant running in a terminal.
You have access to the user's project files.

When the user asks you to CREATE or MODIFY code, respond with one or more blocks
in this EXACT format:

<<<FILE: path/to/file.py>>>
<full new content of the file here>
<<<END>>>

Rules:
- Only use this format when creating/modifying files.
- Always output the ENTIRE new file content, not just the changed lines.
- For explanations or questions, answer in plain text (no file blocks).
- Be concise and practical.
"""


def parse_file_blocks(text):
    """Extract file modification blocks from the model's reply."""
    pattern = r"<<<FILE:\s*(.+?)>>>\n(.*?)<<<END>>>"
    matches = re.findall(pattern, text, re.DOTALL)
    return [(path.strip(), content) for path, content in matches]


def handle_file_changes(text, project_root="."):
    """Detect proposed file changes, show diffs, and ask to apply."""
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


def build_context(project_root="."):
    """Build a system message containing the project files."""
    summary = project_summary(project_root)
    if not summary:
        return "The project is currently empty."
    return f"Here is the current project:\n\n{summary}"


def print_help():
    console.print("""
[bold]Commands:[/bold]
  /files            List project files
  /search <query>   Search text in project
  /reload           Reload project context
  /clear            Clear conversation history
  /help             Show this help
  /exit             Quit
""")


def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    project_root = os.path.abspath(project_root)

    if not os.path.isdir(project_root):
        console.print(f"[red]Directory not found: {project_root}[/red]")
        sys.exit(1)

    console.print(f"[bold green]Coder Helper[/bold green] — project: {project_root}")
    console.print("Type your request or /help for commands.\n")

    history = load_history()
    if not history:
        history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": build_context(project_root)},
        ]

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/dim]")
            break

        if not user_input.strip():
            continue

        # Commands
        if user_input == "/exit":
            break
        if user_input == "/help":
            print_help()
            continue
        if user_input == "/files":
            for f in list_files(project_root):
                console.print(f" - {f}")
            continue
        if user_input == "/clear":
            clear_history()
            history = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": build_context(project_root)},
            ]
            console.print("[yellow]History cleared.[/yellow]")
            continue
        if user_input == "/reload":
            history = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": build_context(project_root)},
            ] + [h for h in history if h["role"] != "system"]
            console.print("[yellow]Project context reloaded.[/yellow]")
            continue
        if user_input.startswith("/search "):
            q = user_input[len("/search "):]
            hits = search(q, project_root)
            if hits:
                for h in hits:
                    console.print(f" - {h}")
            else:
                console.print("[dim]No matches.[/dim]")
            continue

        # Send to model
        history.append({"role": "user", "content": user_input})

        console.print("[bold magenta]A:[/bold magenta] ", end="")
        try:
            reply = chat(history)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            history.pop()
            continue

        history.append({"role": "assistant", "content": reply})
        save_history(history)

        # Handle any proposed file changes
        handle_file_changes(reply, project_root)


if __name__ == "__main__":
    main()

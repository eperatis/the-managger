import difflib
from rich.console import Console
from rich.syntax import Syntax

console = Console()


def make_diff(old, new, filename="file"):
    """Generate a unified diff between old and new content."""
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def show_diff(old, new, filename="file"):
    """Print a colorized diff."""
    diff = make_diff(old, new, filename)
    if not diff:
        console.print(f"[yellow]No changes in {filename}[/yellow]")
        return
    syntax = Syntax(diff, "diff", theme="monokai", line_numbers=False)
    console.print(syntax)

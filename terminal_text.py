import re

from rich.markup import escape

# C0 controls except tab and newline, DEL, and C1 controls. ESC (0x1b) is the
# important one: it starts ANSI sequences that can clear, move or recolor output.
TERMINAL_CONTROL_CHARACTERS_PATTERN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def strip_terminal_control_characters(text):
    return TERMINAL_CONTROL_CHARACTERS_PATTERN.sub("", text)


def safe_for_rich_markup(text):
    """Make untrusted text (model output, file content, file names) safe to embed in a Rich markup string."""
    return escape(strip_terminal_control_characters(text))

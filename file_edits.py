"""Parse, validate and apply the file changes a model proposes.

Two block types, applied in the order they appear in the reply:

<<<FILE: path>>>            creates a new file with the given content
<<<EDIT: path>>>            replaces SEARCH text (which must occur exactly once) in an existing file
<<<SEARCH>>> ... <<<REPLACE>>> ... <<<END>>>
"""
import os
import re
from dataclasses import dataclass

from project import read_file, resolve_path_inside_project, write_file

BLOCK_START_PATTERN = re.compile(r"<<<(FILE|EDIT):")
BLOCK_END_MARKER = "<<<END>>>"
BLOCK_HEADER_LINE_PATTERN = re.compile(r"<<<(?:FILE|EDIT):[^<>\n]+>>>")
NEW_FILE_BLOCK_PATTERN = re.compile(
    r"<<<FILE:[ \t]*(?P<path>[^\n]+?)>>>\n(?P<content>.*)<<<END>>>", re.DOTALL)
EDIT_BLOCK_PATTERN = re.compile(
    r"<<<EDIT:[ \t]*(?P<path>[^\n]+?)>>>\n<<<SEARCH>>>\n(?P<search_text>.*?)"
    r"<<<REPLACE>>>\n(?P<replacement_text>.*)<<<END>>>", re.DOTALL)


class EditPlanError(ValueError):
    """The proposed blocks cannot be applied; the message lists every problem."""


@dataclass
class EditBlock:
    block_number: int
    path: str
    search_text: str | None  # None for a new-file block
    replacement_text: str


@dataclass
class PlannedEdit:
    block: EditBlock
    full_path: str
    content_before: str | None  # None when the file does not exist yet
    content_after: str


@dataclass
class EditPlan:
    planned_edits: list[PlannedEdit]
    original_content_by_full_path: dict[str, str | None]


def describe_malformed_block(block_text):
    """Say what is wrong with a block, specifically enough for a small model to fix it."""
    header_line = block_text.split("\n", 1)[0]
    if BLOCK_START_PATTERN.search(block_text, 1):
        return f"'{header_line}' has no {BLOCK_END_MARKER} line before the next block starts"
    if not BLOCK_HEADER_LINE_PATTERN.fullmatch(header_line):
        return f"header '{header_line}' must be alone on its own line, like <<<EDIT: path/to/file.py>>>"
    if block_text.startswith("<<<EDIT:"):
        if "<<<SEARCH>>>\n" not in block_text:
            return f"'{header_line}' is missing the <<<SEARCH>>> line directly after it"
        if "<<<REPLACE>>>\n" not in block_text:
            return f"'{header_line}' is missing the <<<REPLACE>>> line between the old lines and the new lines"
    return f"'{header_line}' does not follow the block format"


def parse_edit_blocks(model_reply):
    """Parse every FILE/EDIT block in the reply. Raises EditPlanError describing each malformed block."""
    blocks = []
    problems = []
    for block_number, start_match in enumerate(BLOCK_START_PATTERN.finditer(model_reply), start=1):
        end_index = model_reply.find(BLOCK_END_MARKER, start_match.start())
        if end_index == -1:
            problems.append(f"Block {block_number}: no {BLOCK_END_MARKER} line closes it")
            continue
        block_text = model_reply[start_match.start():end_index + len(BLOCK_END_MARKER)]
        is_new_file_block = start_match[1] == "FILE"
        block_pattern = NEW_FILE_BLOCK_PATTERN if is_new_file_block else EDIT_BLOCK_PATTERN
        contains_next_block_start = BLOCK_START_PATTERN.search(block_text, 1) is not None
        block_match = None if contains_next_block_start else block_pattern.fullmatch(block_text)
        if not block_match:
            problems.append(f"Block {block_number}: {describe_malformed_block(block_text)}")
        elif is_new_file_block:
            blocks.append(EditBlock(block_number, block_match["path"].strip(), None, block_match["content"]))
        else:
            blocks.append(EditBlock(block_number, block_match["path"].strip(),
                                    block_match["search_text"], block_match["replacement_text"]))
    if problems:
        raise EditPlanError("\n".join(problems))
    return blocks


def apply_block(block, current_content):
    """Return the file content after applying block, or raise ValueError explaining why it cannot apply."""
    if block.search_text is None:
        if current_content is not None:
            raise ValueError("file already exists; use an EDIT block to change it")
        return block.replacement_text
    if current_content is None:
        raise ValueError("file does not exist; use a FILE block to create it")
    if not block.search_text:
        raise ValueError("SEARCH text is empty")
    match_count = current_content.count(block.search_text)
    if match_count == 0:
        raise ValueError("SEARCH text not found; it must match the current file exactly, including indentation")
    if match_count > 1:
        raise ValueError(f"SEARCH text matches {match_count} places; include more surrounding lines")
    return current_content.replace(block.search_text, block.replacement_text, 1)


def read_original_content(full_path):
    return read_file(full_path) if os.path.exists(full_path) else None


def plan_edits(blocks, project_root):
    """Validate every block against the files, applying them in order. Raises EditPlanError listing all problems."""
    problems = []
    planned_edits = []
    original_content_by_full_path = {}
    current_content_by_full_path = {}
    for block in blocks:
        try:
            full_path = resolve_path_inside_project(project_root, block.path)
            if full_path not in original_content_by_full_path:
                original_content_by_full_path[full_path] = read_original_content(full_path)
                current_content_by_full_path[full_path] = original_content_by_full_path[full_path]
            content_before = current_content_by_full_path[full_path]
            content_after = apply_block(block, content_before)
        except (ValueError, OSError) as block_error:
            problems.append(f"Block {block.block_number} ({block.path}): {block_error}")
            continue
        current_content_by_full_path[full_path] = content_after
        planned_edits.append(PlannedEdit(block, full_path, content_before, content_after))
    if problems:
        raise EditPlanError("\n".join(problems))
    return EditPlan(planned_edits, original_content_by_full_path)


def write_accepted_edits(edit_plan, accepted_edits):
    """Apply the accepted edits to the original contents and write the results.

    Nothing is written if an accepted edit no longer applies because it depended on a declined one.
    Returns the written paths as the model wrote them.
    """
    final_content_by_full_path = {}
    display_path_by_full_path = {}
    for planned_edit in accepted_edits:
        full_path = planned_edit.full_path
        current_content = final_content_by_full_path.get(
            full_path, edit_plan.original_content_by_full_path[full_path])
        try:
            final_content_by_full_path[full_path] = apply_block(planned_edit.block, current_content)
            display_path_by_full_path.setdefault(full_path, planned_edit.block.path)
        except ValueError as block_error:
            raise EditPlanError(
                f"Block {planned_edit.block.block_number} ({planned_edit.block.path}) depends on a declined "
                f"block: {block_error}. Nothing was written."
            ) from block_error
    for full_path, final_content in final_content_by_full_path.items():
        write_file(full_path, final_content)
    return [display_path_by_full_path[full_path] for full_path in final_content_by_full_path]

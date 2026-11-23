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

EDIT_BLOCK_PATTERN = re.compile(
    r"<<<FILE:[ \t]*(?P<new_file_path>[^\n]+?)>>>\n(?P<new_file_content>.*?)<<<END>>>"
    r"|<<<EDIT:[ \t]*(?P<edit_path>[^\n]+?)>>>\n<<<SEARCH>>>\n(?P<search_text>.*?)"
    r"<<<REPLACE>>>\n(?P<replacement_text>.*?)<<<END>>>",
    re.DOTALL,
)
BLOCK_START_PATTERN = re.compile(r"<<<(?:FILE|EDIT):")


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


def parse_edit_blocks(model_reply):
    blocks = []
    for block_number, match in enumerate(EDIT_BLOCK_PATTERN.finditer(model_reply), start=1):
        if match["new_file_path"] is not None:
            blocks.append(EditBlock(block_number, match["new_file_path"].strip(), None, match["new_file_content"]))
        else:
            blocks.append(EditBlock(block_number, match["edit_path"].strip(),
                                    match["search_text"], match["replacement_text"]))
    started_block_count = len(BLOCK_START_PATTERN.findall(model_reply))
    if started_block_count != len(blocks):
        raise EditPlanError(f"{started_block_count - len(blocks)} block(s) are malformed and could not be parsed")
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

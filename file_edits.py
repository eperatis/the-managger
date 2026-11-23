"""Edits the model proposes through tools. They are validated and staged when proposed,
and only written to disk after the user approves them."""
import os
from dataclasses import dataclass

from project import read_file, resolve_path_inside_project, write_file


class EditConflictError(ValueError):
    """An accepted edit cannot apply because it depended on a declined one."""


@dataclass
class StagedEdit:
    edit_number: int
    display_path: str
    full_path: str
    old_text: str | None  # None for an edit that creates a new file
    new_text: str
    content_before: str | None  # None when the file does not exist yet
    content_after: str


def apply_edit(old_text, new_text, current_content):
    """Return the file content after the edit, or raise ValueError explaining why it cannot apply."""
    if old_text is None:
        if current_content is not None:
            raise ValueError("file already exists; use replace_in_file to change it")
        return new_text
    if current_content is None:
        raise ValueError("file does not exist; use create_file to create it")
    if not old_text:
        raise ValueError("old_text is empty")
    match_count = current_content.count(old_text)
    if match_count == 0:
        raise ValueError("old_text not found; copy it exactly from read_file output, including indentation")
    if match_count > 1:
        raise ValueError(f"old_text matches {match_count} places; include more surrounding lines")
    return current_content.replace(old_text, new_text, 1)


class StagedEdits:
    """The edits proposed during one turn, applied in order to an in-memory view of the files."""

    def __init__(self, project_root):
        self.project_root = project_root
        self.edits = []
        self._original_content_by_full_path = {}
        self._current_content_by_full_path = {}

    def resolve(self, path):
        """Return (full_path, display_path relative to the project root)."""
        try:
            full_path = resolve_path_inside_project(self.project_root, path)
        except ValueError as path_error:
            raise ValueError(f"{path_error}. Use a path relative to the project root, as in the file list.") from path_error
        return full_path, os.path.relpath(full_path, os.path.realpath(self.project_root))

    def current_content(self, full_path):
        """Content including edits staged so far, or None if the file does not exist."""
        if full_path not in self._current_content_by_full_path:
            original_content = read_file(full_path) if os.path.exists(full_path) else None
            self._original_content_by_full_path[full_path] = original_content
            self._current_content_by_full_path[full_path] = original_content
        return self._current_content_by_full_path[full_path]

    def stage(self, path, old_text, new_text):
        """Validate and stage an edit (old_text None creates a file). Raises ValueError if it cannot apply."""
        full_path, display_path = self.resolve(path)
        content_before = self.current_content(full_path)
        content_after = apply_edit(old_text, new_text, content_before)
        staged_edit = StagedEdit(len(self.edits) + 1, display_path, full_path,
                                 old_text, new_text, content_before, content_after)
        self.edits.append(staged_edit)
        self._current_content_by_full_path[full_path] = content_after
        return staged_edit

    def write_accepted(self, accepted_edits):
        """Apply the accepted edits to the original files and write them. Returns the written display paths.

        Nothing is written if an accepted edit no longer applies because it depended on a declined one.
        """
        final_content_by_full_path = {}
        display_path_by_full_path = {}
        for staged_edit in accepted_edits:
            full_path = staged_edit.full_path
            current_content = final_content_by_full_path.get(
                full_path, self._original_content_by_full_path[full_path])
            try:
                final_content_by_full_path[full_path] = apply_edit(
                    staged_edit.old_text, staged_edit.new_text, current_content)
            except ValueError as edit_error:
                raise EditConflictError(
                    f"Edit {staged_edit.edit_number} ({staged_edit.display_path}) was made on top of an edit "
                    "you declined, so it cannot apply alone. Nothing was written."
                ) from edit_error
            display_path_by_full_path[full_path] = staged_edit.display_path
        for full_path, final_content in final_content_by_full_path.items():
            write_file(full_path, final_content)
        return list(display_path_by_full_path.values())

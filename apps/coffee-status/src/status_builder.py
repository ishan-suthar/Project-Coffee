"""
Build Coffee Status model objects from a local Project Coffee checkout.

The builder preserves the MVP dashboard privacy contract: only approved status
documents get previews, while Ledger and Roastery files are existence-only.
"""

from pathlib import Path
from typing import Union

from .readers import file_exists, read_first_lines
from .status_model import CoffeeStatus, TrackedFileStatus


PREVIEW_LINE_LIMIT = 20

TRACKED_FILE_PATHS = (
    "brew-log/active_context.md",
    "ROADMAP.md",
    "config/house_blend.md",
    "ledger/cost_log.md",
    "roastery/tasting_notes.md",
)

PREVIEWABLE_FILE_PATHS = frozenset(
    (
        "brew-log/active_context.md",
        "ROADMAP.md",
        "config/house_blend.md",
    )
)


def build_coffee_status(project_root: Union[str, Path]) -> CoffeeStatus:
    """Build the current MVP Coffee Status snapshot for project_root."""

    root = Path(project_root)
    tracked_files = tuple(
        _build_tracked_file_status(root, relative_path)
        for relative_path in TRACKED_FILE_PATHS
    )
    return CoffeeStatus(project_root=root, tracked_files=tracked_files)


def _build_tracked_file_status(project_root: Path, relative_path: str) -> TrackedFileStatus:
    exists = file_exists(project_root, relative_path)
    preview_lines = None

    if exists and relative_path in PREVIEWABLE_FILE_PATHS:
        lines = read_first_lines(project_root, relative_path, max_lines=PREVIEW_LINE_LIMIT)
        if lines is not None:
            preview_lines = tuple(lines)

    return TrackedFileStatus(
        relative_path=relative_path,
        exists=exists,
        preview_lines=preview_lines,
    )

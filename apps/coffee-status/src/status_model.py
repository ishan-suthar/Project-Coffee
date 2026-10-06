"""
Internal data contract for Coffee Status.

This module defines the plain-Python status objects only. It does not read
files, render Streamlit UI, or decide which files are safe to preview.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class TrackedFileStatus:
    """
    Status for one Project Coffee file tracked by the dashboard.

    preview_lines is None when no preview is included. Use an empty tuple when
    a preview was allowed but the file had no lines to show.
    """

    relative_path: str
    exists: bool
    preview_lines: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class CoffeeStatus:
    """Top-level Coffee Status snapshot for a Project Coffee checkout."""

    project_root: Path
    tracked_files: Tuple[TrackedFileStatus, ...] = field(default_factory=tuple)

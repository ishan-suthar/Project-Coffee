"""
Coffee Status readers module.

Provides safe, read-only helper functions for reading project status files.
"""

from pathlib import Path
from typing import Optional, List


def resolve_project_root(app_file: str) -> Path:
    """
    Resolve the Project Coffee root directory from the app.py file path.
    
    Args:
        app_file: The __file__ variable from app.py
        
    Returns:
        Path object pointing to the project root (two levels up from app.py)
    """
    app_path = Path(app_file).resolve()
    return app_path.parent.parent


def file_exists(project_root: Path, relative_path: str) -> bool:
    """
    Check if a file exists relative to the project root.
    
    Args:
        project_root: The Project Coffee root directory
        relative_path: Path relative to project root (e.g., "brew-log/active_context.md")
        
    Returns:
        True if file exists, False otherwise
    """
    file_path = project_root / relative_path
    return file_path.is_file()


def read_first_lines(project_root: Path, relative_path: str, max_lines: int = 20) -> Optional[List[str]]:
    """
    Read the first N lines of a text file safely.
    
    Args:
        project_root: The Project Coffee root directory
        relative_path: Path relative to project root
        max_lines: Maximum number of lines to read (default: 20)
        
    Returns:
        List of lines (without newlines) if file exists and can be read,
        None if file doesn't exist or read error occurs
    """
    file_path = project_root / relative_path
    
    if not file_path.is_file():
        return None
        
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        return lines[:max_lines]
    except Exception:
        # Return None on any read error (permissions, encoding, etc.)
        return None
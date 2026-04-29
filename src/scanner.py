"""Scan directories to discover paper/material files."""

import os
from pathlib import Path
from typing import List

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


def scan_directory(directory: str) -> List[str]:
    """Recursively scan a directory and return paths of supported files.

    Args:
        directory: Path to the directory to scan.

    Returns:
        A sorted list of absolute file paths with supported extensions.

    Raises:
        FileNotFoundError: If the directory does not exist.
        NotADirectoryError: If the path is not a directory.
    """
    root = Path(directory).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    found: List[str] = []
    for dirpath, _dirs, filenames in os.walk(root):
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                found.append(str(Path(dirpath) / filename))

    return sorted(found)

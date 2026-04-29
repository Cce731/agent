"""Organize files into a structured directory hierarchy.

Output structure:
    output_dir/
        {category}/
            {year}/
                filename.ext
            unknown_year/
                filename.ext
"""

import shutil
from pathlib import Path
from typing import Any, Dict, Optional


def _sanitize(name: str) -> str:
    """Remove characters that are unsafe in directory/file names."""
    # Replace common unsafe characters with an underscore
    safe = "".join(c if c.isalnum() or c in " ._-()" else "_" for c in name)
    return safe.strip(" _") or "Unknown"


def organize_file(
    source_path: str,
    output_dir: str,
    category: str,
    year: Optional[int],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Copy (or dry-run) a file into the organized directory structure.

    Args:
        source_path: Absolute path to the source file.
        output_dir: Root directory for the organized output.
        category: Topic category name.
        year: Publication year (or None).
        dry_run: If True, compute the destination but do not copy.

    Returns:
        Dictionary with keys: source, destination, status.
    """
    src = Path(source_path)
    year_folder = str(year) if year else "unknown_year"
    dest_dir = Path(output_dir) / _sanitize(category) / year_folder
    dest = dest_dir / src.name

    # Handle duplicate file names
    counter = 1
    while dest.exists() and dest.resolve() != src.resolve():
        stem = src.stem
        dest = dest_dir / f"{stem}_{counter}{src.suffix}"
        counter += 1

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dest))
        status = "copied"
    else:
        status = "dry_run"

    return {
        "source": str(src),
        "destination": str(dest),
        "status": status,
    }

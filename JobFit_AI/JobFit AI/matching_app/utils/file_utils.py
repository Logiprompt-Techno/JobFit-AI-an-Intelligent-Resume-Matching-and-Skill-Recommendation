"""
General-purpose file helper functions.

These are small, reusable utilities for working with uploaded files
(mainly resumes) that don't belong in any single service or view —
things like getting a file's extension or turning a raw byte count
into a human-friendly size like "2.3 MB". Keeping them here means
views.py and templates can reuse the same logic instead of repeating
it in multiple places.
"""

import os


def get_file_extension(filename: str) -> str:
    """
    Return a file's extension, lowercased and without the leading dot.

    Examples:
        get_file_extension("resume.PDF")  -> "pdf"
        get_file_extension("resume.docx") -> "docx"
        get_file_extension("resume")      -> ""
    """
    if not filename:
        return ""
    _, extension = os.path.splitext(filename)
    return extension.lower().lstrip(".")


def human_readable_file_size(num_bytes) -> str:
    """
    Convert a raw byte count into a human-friendly string.

    Examples:
        human_readable_file_size(512)       -> "512 B"
        human_readable_file_size(2048)      -> "2.0 KB"
        human_readable_file_size(3_500_000) -> "3.3 MB"
    """
    try:
        size = float(num_bytes)
    except (TypeError, ValueError):
        return "Unknown size"

    if size < 0:
        return "Unknown size"

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            # Whole bytes are shown without decimals; everything else
            # gets one decimal place for readability.
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0

    return f"{size:.1f} TB"


def is_allowed_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Check whether a filename's extension is in a list of allowed
    extensions (case-insensitive). Used as a lightweight, reusable
    check anywhere file-type validation is needed outside of forms.py
    (which has its own full ValidationError-raising check).
    """
    extension = get_file_extension(filename)
    normalized_allowed = [ext.lower().lstrip(".") for ext in allowed_extensions]
    return extension in normalized_allowed
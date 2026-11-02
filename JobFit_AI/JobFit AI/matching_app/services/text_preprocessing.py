"""
Shared text-preprocessing helpers used across the NLP services.

Keeping this cleaning logic in one place means resume text and job
description text are always cleaned the same way before being fed
into skill extraction, information extraction, or similarity matching
— which keeps results consistent.
"""

import re


def clean_text(raw_text: str) -> str:
    """
    Perform light, safe cleaning of raw extracted text.

    - Removes non-printable/control characters
    - Collapses repeated spaces/tabs WITHIN each line into single spaces
    - Removes blank lines
    - Strips leading/trailing whitespace on each line and on the whole text

    IMPORTANT: this function deliberately PRESERVES line breaks
    (unlike a simple "collapse all whitespace" cleaner). Section-based
    extraction in info_extractor.py (finding "Education", "Experience",
    etc.) depends on resumes still being split into lines. Only
    horizontal whitespace (spaces/tabs) is collapsed — newlines are kept.

    Intentionally does NOT lowercase or remove punctuation here,
    because some downstream steps (e.g. spaCy NER for names/dates)
    work better with original casing and punctuation. Functions that
    need lowercase text do that themselves.
    """
    if not raw_text:
        return ""

    # Remove non-printable/control characters (keep normal punctuation
    # and newlines).
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', raw_text)

    # Normalize different line-ending styles to a single '\n'.
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Collapse repeated spaces/tabs within each line, and drop empty lines.
    cleaned_lines = []
    for line in text.split('\n'):
        collapsed_line = re.sub(r'[ \t]+', ' ', line).strip()
        if collapsed_line:
            cleaned_lines.append(collapsed_line)

    return "\n".join(cleaned_lines).strip()


def normalize_for_matching(text: str) -> str:
    """
    Lowercase and strip extra punctuation/whitespace, for use when
    comparing two pieces of text (e.g. matching a skill name against
    resume text) where case and punctuation shouldn't matter.
    """
    if not text:
        return ""

    text = text.lower()
    # Keep letters, numbers, spaces, and a few symbols common in tech
    # skill names (e.g. "C++", "C#", "Node.js", "CI/CD").
    text = re.sub(r'[^a-z0-9\s\+\#\./\-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_into_lines(text: str) -> list:
    """
    Split raw resume/JD text into non-empty, stripped lines.
    Useful for section-based extraction (e.g. finding the line that
    starts with "Education" or "Experience").
    """
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]
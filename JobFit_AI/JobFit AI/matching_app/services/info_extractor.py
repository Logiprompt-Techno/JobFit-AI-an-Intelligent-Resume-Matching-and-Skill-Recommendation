"""
Candidate information extraction service.

Given raw resume text, this module pulls out:
    - name       (best-guess candidate name)
    - email      (via regex pattern matching)
    - phone      (via regex pattern matching)
    - education  (text found under an "Education" section heading)
    - experience (text found under an "Experience" section heading)

This uses a combination of regular expressions and spaCy's Named
Entity Recognition (NER) — no custom model training is involved.
"""

import re

import spacy
from django.conf import settings

from .text_preprocessing import split_into_lines

_nlp = None

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# Matches common phone number formats, e.g. "+91 9876543210",
# "(123) 456-7890", "123-456-7890", "9876543210".
PHONE_PATTERN = re.compile(
    r'(\+?\d{1,3}[\s.-]?)?(\(?\d{3,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,6}'
)

EDUCATION_HEADERS = ["education", "academic background", "academic qualification", "qualifications"]
EXPERIENCE_HEADERS = ["experience", "work experience", "professional experience", "employment history"]

# Any of these headings signal the END of whatever section we're
# currently reading (so we know where to stop collecting lines).
ALL_SECTION_HEADERS = EDUCATION_HEADERS + EXPERIENCE_HEADERS + [
    "skills", "projects", "certifications", "achievements", "summary",
    "objective", "contact", "references", "languages", "hobbies", "interests",
]


def _get_nlp():
    """Lazily load the spaCy model once and reuse it for every call."""
    global _nlp
    if _nlp is None:
        model_name = getattr(settings, "SPACY_MODEL_NAME", "en_core_web_sm")
        _nlp = spacy.load(model_name)
    return _nlp


def _extract_email(text: str) -> str:
    """Find the first email address in the text, if any."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else ""


def _extract_phone(text: str) -> str:
    """Find the first phone-number-like sequence in the text, if any."""
    for match in PHONE_PATTERN.finditer(text):
        candidate = match.group(0).strip()
        # Require at least 7 digits so we don't accidentally match
        # things like a year range ("2020-2024") as a phone number.
        digit_count = len(re.sub(r'\D', '', candidate))
        if digit_count >= 7:
            return candidate
    return ""


def _extract_name(text: str, lines: list) -> str:
    """
    Best-guess the candidate's name.

    Strategy:
        1. Try spaCy NER on the first few lines of the resume — resumes
           almost always start with the candidate's name, so a PERSON
           entity found near the top is very likely correct.
        2. Fall back to simply using the first non-empty line, if it
           looks like a plausible name (short, no digits/symbols).
    """
    nlp = _get_nlp()

    # Only look at the first ~3 lines to avoid picking up a name of
    # someone else mentioned later (e.g. a reference or manager's name).
    top_text = " ".join(lines[:3]) if lines else text[:200]
    doc = nlp(top_text)

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()

    # Fallback: use the first line if it looks like a name
    # (short, mostly alphabetic, no @ symbol or digits).
    if lines:
        first_line = lines[0].strip()
        if (
            0 < len(first_line) <= 60
            and "@" not in first_line
            and not any(char.isdigit() for char in first_line)
        ):
            return first_line

    return ""


def _extract_section(lines: list, section_headers: list) -> str:
    """
    Find a section (e.g. "Education" or "Experience") by looking for a
    line that matches one of the given headers, then collect every
    line until the next recognised section header (or end of resume).
    """
    collected = []
    inside_section = False

    for line in lines:
        normalized_line = line.lower().strip(" :-")

        is_target_header = any(
            normalized_line == header or normalized_line.startswith(header)
            for header in section_headers
        )
        is_other_header = any(
            normalized_line == header or normalized_line.startswith(header)
            for header in ALL_SECTION_HEADERS
            if header not in section_headers
        )

        if is_target_header:
            inside_section = True
            continue  # don't include the heading line itself

        if inside_section and is_other_header:
            break  # reached the start of a different section — stop collecting

        if inside_section:
            clean_line = line.strip()
            if clean_line:
                collected.append(clean_line)

    return "\n".join(collected).strip()


def extract_candidate_info(text: str) -> dict:
    """
    Extract candidate information from raw resume text.

    Returns:
        A dictionary with keys: 'name', 'email', 'phone', 'education',
        'experience'. Any piece of information that couldn't be found
        is returned as an empty string rather than raising an error —
        a resume missing a phone number, for example, should not stop
        the rest of the pipeline from working.
    """
    if not text:
        return {"name": "", "email": "", "phone": "", "education": "", "experience": ""}

    lines = split_into_lines(text)

    return {
        "name": _extract_name(text, lines),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "education": _extract_section(lines, EDUCATION_HEADERS),
        "experience": _extract_section(lines, EXPERIENCE_HEADERS),
    }
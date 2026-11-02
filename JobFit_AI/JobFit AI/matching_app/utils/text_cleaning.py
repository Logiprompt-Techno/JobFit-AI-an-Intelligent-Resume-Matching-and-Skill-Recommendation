"""
General-purpose text helper functions used by views and templates.

NOTE: this is different from matching_app/services/text_preprocessing.py,
which contains NLP-specific cleaning used internally by the resume
parsing/matching pipeline. The functions here are simple, generic
helpers for DISPLAYING and CONVERTING data in views/templates (e.g.
turning a comma-separated skills string into a list, or shortening a
long description for a list page) — they don't know anything about
spaCy, embeddings, or matching.
"""


def skills_string_to_list(skills_string: str) -> list:
    """
    Convert a comma-separated skills string (as stored in the
    database, e.g. Resume.extracted_skills or Job.required_skills)
    into a clean list of individual skill names.

    Example:
        skills_string_to_list("Python, Django,  SQL ,")
        -> ["Python", "Django", "SQL"]
    """
    if not skills_string:
        return []
    return [skill.strip() for skill in skills_string.split(",") if skill.strip()]


def list_to_skills_string(skills_list: list) -> str:
    """
    Convert a list of skill names back into a single comma-separated
    string, ready to store in a database TextField.

    Example:
        list_to_skills_string(["Python", "Django", "SQL"])
        -> "Python, Django, SQL"
    """
    if not skills_list:
        return ""
    return ", ".join(str(skill).strip() for skill in skills_list if str(skill).strip())


def truncate_text(text: str, max_length: int = 150) -> str:
    """
    Shorten a piece of text for display in a list/preview (e.g. a job
    description preview on the job list page), adding "..." if it was
    cut short. Never cuts a word in half — trims back to the last
    whole word before the limit.

    Example:
        truncate_text("This is a long job description", 10)
        -> "This is a..."
    """
    if not text:
        return ""

    text = text.strip()
    if len(text) <= max_length:
        return text

    shortened = text[:max_length].rsplit(" ", 1)[0]
    return f"{shortened}..."
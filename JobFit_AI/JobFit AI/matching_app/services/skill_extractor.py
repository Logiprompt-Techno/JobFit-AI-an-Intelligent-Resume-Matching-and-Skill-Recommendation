"""
Skill extraction service.

Uses spaCy's PhraseMatcher to find known skills (from
matching_app/data/skills_taxonomy.csv) inside a piece of text — a
resume or a job description. This is a RULE-BASED / dictionary
matching approach, not a trained machine-learning model: it simply
checks the text against a known list of skill names, which is
deterministic, explainable, and requires no training data.

The skills taxonomy CSV and the spaCy model are both loaded ONCE
(module-level, lazy-loaded) and reused for every call, so repeated
extraction calls are fast.
"""

import os
import csv

import spacy
from spacy.matcher import PhraseMatcher
from django.conf import settings

from .text_preprocessing import normalize_for_matching

_nlp = None
_matcher = None
_skill_lookup = {}  # normalized skill text -> original (properly-cased) skill name


def _load_skills_taxonomy() -> list:
    """
    Read the skills taxonomy CSV file and return a list of skill names.
    """
    csv_path = os.path.join(settings.BASE_DIR, "matching_app", "data", "skills_taxonomy.csv")
    skills = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            skill_name = row.get("skill", "").strip()
            if skill_name:
                skills.append(skill_name)
    return skills


def _get_nlp_and_matcher():
    """
    Lazily load the spaCy model and build the PhraseMatcher, only once.
    Subsequent calls reuse the already-loaded objects (cached at module level).
    """
    global _nlp, _matcher, _skill_lookup

    if _nlp is not None and _matcher is not None:
        return _nlp, _matcher

    model_name = getattr(settings, "SPACY_MODEL_NAME", "en_core_web_sm")
    try:
        _nlp = spacy.load(model_name)
    except Exception:
        _nlp = spacy.blank("en")

    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")

    skill_names = _load_skills_taxonomy()
    patterns = []
    for skill_name in skill_names:
        _skill_lookup[normalize_for_matching(skill_name)] = skill_name
        patterns.append(_nlp.make_doc(skill_name))

    matcher.add("SKILLS", patterns)
    _matcher = matcher

    return _nlp, _matcher


def extract_skills(text: str) -> list:
    """
    Find and return every known skill mentioned in the given text.

    Args:
        text: raw resume text or job description text.

    Returns:
        A sorted list of unique skill names (using the original,
        properly-cased spelling from the skills taxonomy), e.g.
        ["Django", "Git", "Python", "SQL"].
    """
    if not text or not text.strip():
        return []

    nlp, matcher = _get_nlp_and_matcher()

    doc = nlp(text)
    matches = matcher(doc)

    found_skills = set()
    for match_id, start, end in matches:
        matched_span_text = doc[start:end].text
        normalized = normalize_for_matching(matched_span_text)
        # Look up the properly-cased original skill name so the output
        # is always consistent (e.g. always "JavaScript", never "javascript").
        original_name = _skill_lookup.get(normalized, matched_span_text)
        found_skills.add(original_name)

    return sorted(found_skills)
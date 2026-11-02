"""
Skill recommendation engine.

Given a list of skills a candidate is MISSING for a particular job,
this module suggests what they could learn or which certification
could help close that gap. It looks each missing skill up in
matching_app/data/certifications_map.csv (a curated reference list,
not a trained model). If a skill isn't in that map, a sensible
generic suggestion is generated instead, so every missing skill gets
a useful recommendation.
"""

import os
import csv

from django.conf import settings

_certifications_map = None  # cached at module level after first load


def _load_certifications_map() -> dict:
    """
    Load matching_app/data/certifications_map.csv into a dictionary of
    {normalized_skill_name: recommended_certification_text}.
    """
    global _certifications_map
    if _certifications_map is not None:
        return _certifications_map

    csv_path = os.path.join(settings.BASE_DIR, "matching_app", "data", "certifications_map.csv")
    mapping = {}

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            skill_name = row.get("skill", "").strip()
            certification = row.get("recommended_certification", "").strip()
            if skill_name and certification:
                mapping[skill_name.lower()] = certification

    _certifications_map = mapping
    return _certifications_map


def recommend_skills_for_gap(missing_skills: list) -> list:
    """
    For each missing skill, return a recommendation string.

    Args:
        missing_skills: list of skill names the candidate is missing
                         for a given job (e.g. from matcher.calculate_match).

    Returns:
        A list of recommendation strings, one per missing skill, e.g.
        ["Python: Python Institute PCEP/PCAP Certification, or ...",
         "Kubernetes: Consider taking an online course or certification in Kubernetes"]
    """
    if not missing_skills:
        return []

    certifications_map = _load_certifications_map()
    recommendations = []

    for skill in missing_skills:
        certification = certifications_map.get(skill.lower())
        if certification:
            recommendations.append(f"{skill}: {certification}")
        else:
            # Generic, still-useful fallback for skills not in our
            # curated certifications map.
            recommendations.append(
                f"{skill}: Consider taking an online course or certification in {skill}"
            )

    return recommendations
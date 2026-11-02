"""
Resume-Job matching engine.

Combines two signals into one final match percentage for a
(resume, job) pair:

    1. Semantic similarity  - how similar the overall MEANING of the
                               resume text is to the job description
                               text (via embedding_engine.py).
    2. Skill overlap        - what fraction of the job's REQUIRED
                               skills are actually present in the
                               resume's extracted skills.

Blending both signals gives a more reliable score than either alone:
semantic similarity alone can be fooled by generic wording, while
skill overlap alone ignores context (e.g. years of experience,
seniority, domain). The two are combined with fixed, explainable
weights (60% skill overlap, 40% semantic similarity) rather than a
trained model, which keeps the scoring transparent and reproducible.
"""

from .embedding_engine import get_text_similarity
from .text_preprocessing import normalize_for_matching

# How much each signal contributes to the final match percentage.
# Skill overlap is weighted higher because it's a more concrete,
# literal signal for "can this candidate actually do this job",
# while semantic similarity adds useful context on top of that.
SKILL_OVERLAP_WEIGHT = 0.6
SEMANTIC_SIMILARITY_WEIGHT = 0.4


def _parse_skill_list(comma_separated_skills: str) -> list:
    """Turn a comma-separated skills string into a clean list of skill names."""
    if not comma_separated_skills:
        return []
    return [s.strip() for s in comma_separated_skills.split(",") if s.strip()]


def _calculate_skill_overlap(resume_skills: list, required_skills: list) -> dict:
    """
    Compare a resume's skills against a job's required skills.

    Returns:
        A dict with:
            'overlap_ratio'   - fraction (0.0-1.0) of required skills the
                                 candidate has.
            'missing_skills'  - list of required skills NOT found in the
                                 resume (using the job's original spelling).
    """
    if not required_skills:
        # Nothing specific was required, so there's nothing to be
        # "missing" and we treat the skill-overlap component as neutral.
        return {"overlap_ratio": 1.0, "missing_skills": []}

    normalized_resume_skills = {normalize_for_matching(s) for s in resume_skills}

    missing_skills = []
    matched_count = 0
    for required_skill in required_skills:
        if normalize_for_matching(required_skill) in normalized_resume_skills:
            matched_count += 1
        else:
            missing_skills.append(required_skill)

    overlap_ratio = matched_count / len(required_skills)
    return {"overlap_ratio": overlap_ratio, "missing_skills": missing_skills}


def calculate_match(resume, job) -> dict:
    """
    Calculate how well a Resume matches a Job.

    Args:
        resume: a matching_app.models.Resume instance (must already
                 have extracted_text and extracted_skills populated).
        job:    a matching_app.models.Job instance.

    Returns:
        A dict with:
            'match_percentage'  - float from 0.0 to 100.0
            'missing_skills'    - list of required job skills not found
                                    in the resume
            'skill_overlap_ratio'    - float 0.0-1.0 (for transparency/debugging)
            'semantic_similarity'    - float 0.0-1.0 (for transparency/debugging)
    """
    resume_skills = _parse_skill_list(resume.extracted_skills)
    required_skills = _parse_skill_list(job.required_skills)

    skill_result = _calculate_skill_overlap(resume_skills, required_skills)

    # Build the text used for semantic comparison: prefer the resume's
    # full extracted text (richer context) compared against the job's
    # full description.
    resume_text_for_comparison = resume.extracted_text or ", ".join(resume_skills)
    job_text_for_comparison = job.job_description or ", ".join(required_skills)

    semantic_similarity = get_text_similarity(resume_text_for_comparison, job_text_for_comparison)

    final_score = (
        (skill_result["overlap_ratio"] * SKILL_OVERLAP_WEIGHT)
        + (semantic_similarity * SEMANTIC_SIMILARITY_WEIGHT)
    ) * 100

    # Round to 2 decimal places for a clean, readable percentage.
    match_percentage = round(final_score, 2)

    return {
        "match_percentage": match_percentage,
        "missing_skills": skill_result["missing_skills"],
        "skill_overlap_ratio": round(skill_result["overlap_ratio"], 3),
        "semantic_similarity": round(semantic_similarity, 3),
    }
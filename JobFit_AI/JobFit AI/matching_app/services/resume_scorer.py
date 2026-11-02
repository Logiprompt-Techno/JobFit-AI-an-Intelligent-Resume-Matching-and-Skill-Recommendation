"""
Resume Quality Scoring Engine.

Calculates an overall Resume Quality & Completeness Score (0–100) based on:
    1. Contact Information completeness (Name, Email, Phone)
    2. Detected Skill Density & Diversity (Max 35 pts)
    3. Extracted Education Section depth (Max 20 pts)
    4. Extracted Work Experience & Project details depth (Max 20 pts)

Returns score integer (0-100), letter grade, and specific improvement suggestions.
"""

from matching_app.utils.text_cleaning import skills_string_to_list


def calculate_resume_score(resume) -> dict:
    """
    Calculate a realistic, comprehensive Resume Quality Score (0 to 100) and generate improvement suggestions.

    Args:
        resume: matching_app.models.Resume instance.

    Returns:
        dict: {
            'score': int (0 to 100),
            'grade': str ('Excellent', 'Good', 'Average', 'Needs Improvement'),
            'suggestions': list of str,
            'breakdown': dict
        }
    """
    score = 0
    suggestions = []
    breakdown = {
        'contact_info': 0,
        'skills': 0,
        'education': 0,
        'experience': 0,
    }

    # 1. Contact Information Evaluation (Max 25 pts)
    if resume.candidate_name and len(resume.candidate_name.strip()) > 3:
        score += 8
        breakdown['contact_info'] += 8
    else:
        suggestions.append("Ensure your full name is clearly positioned at the top of your resume.")

    if resume.email and "@" in resume.email:
        score += 9
        breakdown['contact_info'] += 9
    else:
        suggestions.append("Add a professional email address for recruiters to contact you.")

    if resume.phone and len(resume.phone.strip()) >= 7:
        score += 8
        breakdown['contact_info'] += 8
    else:
        suggestions.append("Add your phone number so hiring managers can reach you directly.")

    # 2. Skill Density & Variety Evaluation (Max 35 pts)
    skills = skills_string_to_list(resume.extracted_skills)
    skill_count = len(skills)

    if skill_count >= 15:
        score += 35
        breakdown['skills'] += 35
    elif skill_count >= 10:
        score += 28
        breakdown['skills'] += 28
        suggestions.append("Add 5 or more relevant technical skills or frameworks to achieve maximum skill density.")
    elif skill_count >= 6:
        score += 20
        breakdown['skills'] += 20
        suggestions.append("Include more technical skills, databases, or cloud platforms to improve matching accuracy.")
    elif skill_count >= 3:
        score += 12
        breakdown['skills'] += 12
        suggestions.append("Expand your skills list with specific programming languages, libraries, and tools.")
    elif skill_count >= 1:
        score += 5
        breakdown['skills'] += 5
        suggestions.append("Add a dedicated 'Skills' section listing your technical competencies.")
    else:
        suggestions.append("No technical skills were detected. Add a clear list of skills to your resume.")

    # 3. Education Section Evaluation (Max 20 pts)
    edu_text = (resume.education or "").strip()
    if len(edu_text) >= 80:
        score += 20
        breakdown['education'] += 20
    elif len(edu_text) >= 20:
        score += 12
        breakdown['education'] += 12
        suggestions.append("Elaborate on your Education section (include university name, degree title, and graduation year).")
    else:
        suggestions.append("Add an 'Education' section detailing your academic qualifications and degree background.")

    # 4. Work Experience & Projects Depth Evaluation (Max 20 pts)
    exp_text = (resume.experience or "").strip()
    if len(exp_text) >= 120:
        score += 20
        breakdown['experience'] += 20
    elif len(exp_text) >= 30:
        score += 10
        breakdown['experience'] += 10
        suggestions.append("Detail your key project achievements, technologies used, and responsibilities under Work Experience.")
    else:
        suggestions.append("Add a 'Work Experience' or 'Key Projects' section to demonstrate practical skills.")

    # Grade Assignment
    if score >= 88:
        grade = "Excellent"
    elif score >= 72:
        grade = "Good"
    elif score >= 55:
        grade = "Average"
    else:
        grade = "Needs Improvement"

    return {
        'score': min(100, score),
        'grade': grade,
        'suggestions': suggestions,
        'breakdown': breakdown,
    }

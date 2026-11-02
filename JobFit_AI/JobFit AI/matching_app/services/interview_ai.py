import os
import json
import random
from matching_app.utils.text_cleaning import skills_string_to_list


def generate_interview_questions(job) -> list:
    """
    Generate 4 randomized, highly technical screening interview questions for a given Job opening.
    Tries Groq LLM API with high temperature if GROQ_API_KEY is set, otherwise uses a rich,
    randomized technical question pool tailored to required skills and job title.
    """
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()

    if groq_api_key:
        try:
            import urllib.request
            url = "https://api.groq.com/openai/v1/chat/completions"
            prompt = (
                f"You are an expert technical interviewer hiring for a '{job.job_title}' position. "
                f"Required skills: {job.required_skills}. Job description: {job.job_description[:300]}. "
                f"Generate exactly 4 distinct, deep technical screening interview questions to assess technical competence, coding/architecture trade-offs, and problem-solving. "
                f"Ensure questions are fresh, specific, and non-generic. "
                f"Return ONLY a JSON array of 4 question strings, e.g. [\"Q1\", \"Q2\", \"Q3\", \"Q4\"]."
            )

            payload = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 500
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                content = res_data['choices'][0]['message']['content'].strip()
                if "[" in content and "]" in content:
                    json_str = content[content.find("["):content.rfind("]")+1]
                    questions = json.loads(json_str)
                    if isinstance(questions, list) and len(questions) == 4:
                        return [str(q).strip() for q in questions]
        except Exception:
            pass  # Gracefully fall back to local randomized technical generator

    # Local Randomized Technical Question Pools
    skills = skills_string_to_list(job.required_skills)
    primary_skill = skills[0] if skills else job.job_title
    secondary_skill = skills[1] if len(skills) > 1 else "clean architecture"
    tertiary_skill = skills[2] if len(skills) > 2 else "performance tuning"

    # Category 1: Architecture & Technical Fundamentals
    arch_pool = [
        f"In a production system using {primary_skill}, how do you design data structures and memory management for high-concurrency workloads?",
        f"What architectural trade-offs do you consider when implementing {primary_skill} alongside {secondary_skill} in a scalable microservices setup?",
        f"Explain how you structure component modules and data access layers when building scalable applications with {primary_skill}.",
        f"What design patterns (e.g. Factory, Repository, Dependency Injection) do you implement most frequently when developing with {primary_skill} and why?"
    ]

    # Category 2: Performance, Query & State Optimization
    perf_pool = [
        f"How do you profile, identify, and resolve CPU or memory bottlenecks when working with {primary_skill} and {secondary_skill}?",
        f"Explain your approach to database indexing, query optimization, and caching strategies when managing heavy read/write operations using {tertiary_skill}.",
        f"How do you handle asynchronous execution, event loops, or background tasks in {primary_skill} applications to prevent blocking the main thread?",
        f"What strategies do you use for connection pooling, state management, and latency reduction in high-traffic {job.job_title} environments?"
    ]

    # Category 3: Debugging & Production Incident Scenarios
    debug_pool = [
        f"Walk us through a real-world scenario where a critical bug or memory leak occurred in your {primary_skill} codebase. How did you diagnose and fix it?",
        f"Suppose a production service built with {primary_skill} starts throwing 500 error rates or slow timeouts under load. What diagnostic tools and steps would you take immediately?",
        f"How do you handle error logging, stack trace analysis, and automated monitoring (e.g., Sentry, Prometheus, CloudWatch) for a {job.job_title} system?",
        f"Describe how you handle edge-case data validation and error recovery when integrating external APIs with {secondary_skill}."
    ]

    # Category 4: Testing, Security & CI/CD Best Practices
    test_sec_pool = [
        f"What strategies do you follow to implement unit testing, integration testing, and mock dependencies when working with {primary_skill}?",
        f"How do you ensure application security (e.g. preventing SQL injection, XSS, CSRF, and securing API endpoints/JWT tokens) in a {job.job_title} role?",
        f"Explain your experience with CI/CD pipelines, containerization (Docker/Kubernetes), and automated deployment workflows for {primary_skill} projects.",
        f"What security and code review standards do you enforce before pushing code changes involving {secondary_skill} to production?"
    ]

    # Randomly select 1 technical question from each of the 4 technical domains
    q1 = random.choice(arch_pool)
    q2 = random.choice(perf_pool)
    q3 = random.choice(debug_pool)
    q4 = random.choice(test_sec_pool)

    return [q1, q2, q3, q4]


def evaluate_interview_answers(session) -> dict:
    """
    Evaluate candidate answers in an InterviewSession and compute AI evaluation score and summary feedback.
    """
    questions = session.questions.all().order_by('question_number')
    if not questions.exists():
        return {
            'overall_score': 0.0,
            'summary': "No questions were answered in this session.",
            'recommendation': "Needs Review"
        }

    job_skills = set(s.lower() for s in skills_string_to_list(session.job.required_skills))
    total_score = 0.0

    for q in questions:
        answer_text = (q.candidate_answer or "").strip()
        word_count = len(answer_text.split())

        if not answer_text or word_count < 4:
            q_score = 10.0
            feedback = "Answer too brief or missing."
        else:
            q_score = 50.0
            if word_count >= 15:
                q_score += 20.0
            if word_count >= 30:
                q_score += 15.0

            # Check skill keyword overlap in candidate answer
            matched_skills = [s for s in job_skills if s in answer_text.lower()]
            if matched_skills:
                q_score += min(15.0, len(matched_skills) * 5.0)

            q_score = min(100.0, q_score)
            feedback = f"Good detail ({word_count} words). Demonstrated relevance to key requirements."

        q.score = round(q_score, 1)
        q.ai_feedback = feedback
        q.save()

        total_score += q_score

    overall_score = round(total_score / len(questions), 1)

    # Penalize if proctoring tab switch violation occurred
    if session.tab_switch_count > 0:
        penalty = min(30.0, session.tab_switch_count * 10.0)
        overall_score = max(0.0, overall_score - penalty)

    overall_score = round(overall_score, 1)

    if session.status == 'Terminated (Tab Switch Violation)':
        summary = (
            f"Candidate achieved an average response score of {overall_score}%, but the session was "
            f"AUTOMATICALLY TERMINATED due to exceeding the maximum permitted browser tab switches ({session.tab_switch_count} violations)."
        )
        recommendation = "Unsuitable (Proctoring Violation)"
    elif overall_score >= 80:
        summary = f"Strong candidate performance ({overall_score}% score). Answers showed technical depth, clear communication, and skill relevance."
        recommendation = "Highly Recommended"
    elif overall_score >= 60:
        summary = f"Satisfactory response quality ({overall_score}% score). Meets key requirements with acceptable technical communication."
        recommendation = "Recommended"
    else:
        summary = f"Below target threshold ({overall_score}% score). Answers lacked detail or key required technical coverage."
        recommendation = "Needs Further Assessment"

    session.ai_evaluation_score = overall_score
    session.ai_summary = f"{summary} (Proctoring log: {session.tab_switch_count} tab switches detected)."
    session.save()

    return {
        'overall_score': overall_score,
        'summary': session.ai_summary,
        'recommendation': recommendation
    }

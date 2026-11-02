import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Template filter to perform dictionary lookup by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def split_skills(value):
    """
    Splits a comma-separated skills or recommendation string by commas,
    NOT whitespace spaces, returning a clean list of skill/recommendation strings.
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    
    return [s.strip() for s in str(value).split(",") if s.strip()]


@register.filter
def format_parsed_summary(text):
    """
    Format unstructured raw extracted experience or education text into a clean,
    point-wise list with sub-headings and bullet points for recruiters.
    """
    if not text:
        return ""

    raw_str = str(text).strip()
    if not raw_str:
        return ""

    # Split by newlines first
    raw_lines = [l.strip() for l in raw_str.split("\n") if l.strip()]

    # If it's a single paragraph blob without newlines, split by sentence endings and title patterns
    if len(raw_lines) <= 1:
        blob = raw_lines[0] if raw_lines else raw_str
        # Insert newline before dates/role patterns or major headings
        # e.g., "Nov 2025-Nov 2026", "Brands 4 Less", "Part-Time Tutor"
        blob = re.sub(
            r'([a-z0-9\.\)])\s+([A-Z][a-zA-Z0-9\s\-\(\),]+(?:Associate|Picker|Tutor|Developer|Engineer|Manager|Specialist|Analyst|Lead|Assistant|Officer|Executive|Store|Centre|Center|University|College|School|Limited|Inc|Pvt|Ltd))',
            r'\1\n\2',
            blob
        )
        blob = re.sub(r'(\.|\b[0-9]{4}\b)\s+([A-Z])', r'\1\n\2', blob)
        raw_lines = [l.strip() for l in blob.split("\n") if l.strip()]

    html_output = []
    current_bullets = []

    def flush_bullets():
        if current_bullets:
            html_output.append('<ul class="list-unstyled ms-2 mb-3">')
            for b in current_bullets:
                html_output.append(
                    f'<li class="d-flex align-items-start mb-2">'
                    f'<i class="bi bi-check2-circle text-emerald me-2 mt-1" style="color: var(--emerald-500); font-size: 1.1rem; flex-shrink: 0;"></i>'
                    f'<span class="text-dark leading-relaxed">{b}</span>'
                    f'</li>'
                )
            html_output.append('</ul>')
            current_bullets.clear()

    heading_keywords = [
        'picker', 'associate', 'tutor', 'developer', 'engineer', 'manager', 'lead',
        'intern', 'analyst', 'specialist', 'assistant', 'officer', 'executive',
        'store', 'centre', 'center', 'university', 'college', 'school', 'instamart',
        'brands 4 less', 'bca', 'b.sc', 'b.tech', 'mca', 'm.tech', 'diploma', 'hsc', 'sslc'
    ]

    date_pattern = re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[0-9]{4})\b', re.IGNORECASE)

    for line in raw_lines:
        line_lower = line.lower()
        is_heading = (
            date_pattern.search(line) or
            any(kw in line_lower for kw in heading_keywords) or
            line.endswith(":") or
            (len(line) < 70 and "," in line and not line.endswith("."))
        )

        # Action verbs that indicate a bullet point sentence, not a job title
        is_action_sentence = line_lower.startswith((
            'managed', 'assisted', 'helped', 'trained', 'developed', 'ensured',
            'improved', 'gained', 'responsible', 'handled', 'created', 'built',
            'designed', 'maintained', 'conducted', 'supported', 'provided'
        ))

        if is_heading and len(line) < 120 and not is_action_sentence:
            flush_bullets()
            clean_title = line.strip(" :-")
            html_output.append(
                f'<div class="fw-bold text-navy fs-6 mt-3 mb-2 pb-1 border-bottom d-flex align-items-center gap-2">'
                f'<i class="bi bi-briefcase-fill text-emerald" style="color: var(--emerald-500);"></i>'
                f'<span>{clean_title}</span>'
                f'</div>'
            )
        else:
            # Bullet point item: split multiple sentences in a line into distinct bullets
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', line) if s.strip()]
            for stmt in sentences:
                stmt_clean = stmt.lstrip("•-–* ").strip()
                if stmt_clean:
                    current_bullets.append(stmt_clean)

    flush_bullets()

    if not html_output:
        return f'<p class="text-muted mb-0">{text}</p>'

    return mark_safe("".join(html_output))

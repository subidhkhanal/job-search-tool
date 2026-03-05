"""
Resume Tailor — Two-pass GPT-4 resume tailoring for ATS optimization.

Pass 1: Deep JD analysis — extract prioritized requirements, keywords, action verbs
Pass 2: Resume rewriting — rewrite bullets using Pass 1 analysis, reorder sections

Includes LaTeX validation and bullet-by-bullet diff extraction.
"""

import json
import re

# Skills categorized by learnability for gap analysis
SKILL_DIFFICULTY = {
    "easy": [
        "docker", "tailwind", "css", "html", "pandas", "numpy",
        "streamlit", "gradio", "git", "github", "selenium",
    ],
    "medium": [
        "react", "typescript", "angular", "vue", "django", "flask",
        "postgresql", "mongodb", "redis", "graphql", "ci/cd",
        "tensorflow", "pytorch", "airflow",
    ],
    "hard": [
        "kubernetes", "aws", "gcp", "azure", "terraform", "kafka",
        "java", "go", "rust", "c++", "scala", "spark",
        "distributed systems", "microservices",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_resume_latex():
    """Fetch the LaTeX resume from the user profile in Supabase."""
    try:
        from profile import get_resume_text
        text = get_resume_text()
        if text and text.strip():
            return text
    except Exception:
        pass
    return None


def _analyze_gaps(jd_text, resume_text):
    """Find skills the JD wants that aren't in the resume."""
    from jd_analyzer import _extract_tech_keywords

    jd_keywords = _extract_tech_keywords(jd_text)
    resume_lower = resume_text.lower()

    gaps = []
    for kw in jd_keywords:
        if kw not in resume_lower:
            difficulty = "medium"
            for level, skills in SKILL_DIFFICULTY.items():
                if kw in skills:
                    difficulty = level
                    break

            if difficulty == "easy":
                note = "Learnable quickly — add if you have any exposure"
            elif difficulty == "medium":
                note = "Worth picking up if multiple JDs ask for it"
            else:
                note = "Significant gap — acknowledge as area of growth"

            gaps.append({
                "skill": kw,
                "difficulty": difficulty,
                "note": note,
            })

    return gaps


def _extract_resume_items(latex_text):
    """Extract all \\resumeItem{...} contents from LaTeX, handling nested braces."""
    items = []
    pattern = r"\\resumeItem\{"
    for match in re.finditer(pattern, latex_text):
        start = match.end()
        depth = 1
        i = start
        while i < len(latex_text) and depth > 0:
            if latex_text[i] == "{":
                depth += 1
            elif latex_text[i] == "}":
                depth -= 1
            i += 1
        if depth == 0:
            items.append(latex_text[start : i - 1].strip())
    return items


def _validate_latex(latex_text):
    """Validate basic LaTeX structure. Returns (is_valid, errors)."""
    errors = []

    if "\\begin{document}" not in latex_text:
        errors.append("Missing \\begin{document}")
    if "\\end{document}" not in latex_text:
        errors.append("Missing \\end{document}")

    # Check balanced braces
    depth = 0
    for ch in latex_text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth < 0:
            errors.append("Unbalanced braces: extra closing brace found")
            break
    if depth > 0:
        errors.append(f"Unbalanced braces: {depth} unclosed opening brace(s)")

    # Check \\begin/\\end pairs
    begins = re.findall(r"\\begin\{(\w+)\}", latex_text)
    ends = re.findall(r"\\end\{(\w+)\}", latex_text)
    begin_counts = {}
    end_counts = {}
    for b in begins:
        begin_counts[b] = begin_counts.get(b, 0) + 1
    for e in ends:
        end_counts[e] = end_counts.get(e, 0) + 1
    for env in set(list(begin_counts.keys()) + list(end_counts.keys())):
        bc = begin_counts.get(env, 0)
        ec = end_counts.get(env, 0)
        if bc != ec:
            errors.append(
                f"Mismatched \\begin/{env} ({bc}) vs \\end/{env} ({ec})"
            )

    return len(errors) == 0, errors


def _build_bullet_diffs(original_latex, tailored_latex):
    """Extract bullet-by-bullet diffs between original and tailored resume."""
    original_items = _extract_resume_items(original_latex)
    tailored_items = _extract_resume_items(tailored_latex)

    diffs = []
    # Match by position (same order assumption)
    for i in range(min(len(original_items), len(tailored_items))):
        orig = original_items[i]
        tail = tailored_items[i]
        if orig.strip() != tail.strip():
            # Find keywords added (words in tailored not in original)
            orig_words = set(re.findall(r"\b\w+\b", orig.lower()))
            tail_words = set(re.findall(r"\b\w+\b", tail.lower()))
            new_words = tail_words - orig_words
            # Filter to meaningful keywords (3+ chars, not common words)
            stop_words = {
                "the", "and", "for", "with", "that", "this", "from",
                "are", "was", "were", "been", "has", "have", "had",
                "not", "but", "its", "our", "can", "will", "into",
                "also", "each", "more", "than", "very", "such",
            }
            keywords_added = sorted(
                w for w in new_words if len(w) >= 3 and w not in stop_words
            )

            diffs.append({
                "section": _guess_section(original_latex, orig),
                "original": orig,
                "rewritten": tail,
                "keywords_added": keywords_added[:10],  # cap at 10
            })

    return diffs


def _guess_section(latex_text, item_text):
    """Try to determine which section a resume item belongs to."""
    item_pos = latex_text.find(item_text)
    if item_pos == -1:
        return "Unknown"

    # Look backwards for the nearest \\section{...}
    before = latex_text[:item_pos]
    section_matches = list(re.finditer(r"\\section\{([^}]+)\}", before))
    if section_matches:
        return section_matches[-1].group(1)
    return "Unknown"


def _parse_json_response(raw):
    """Parse JSON from LLM response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object from the response
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("LLM returned invalid JSON. Please try again.")


# ---------------------------------------------------------------------------
# Pass 1: JD Analysis
# ---------------------------------------------------------------------------

def _analyze_jd(client, job_title, jd_text):
    """Pass 1: Deep analysis of the job description."""
    prompt = f"""Analyze this job description thoroughly. Extract structured information that a resume writer would need.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{jd_text[:4000]}

Return ONLY valid JSON (no markdown fences) in this exact format:
{{
  "must_have_keywords": ["keyword1", "keyword2"],
  "preferred_keywords": ["keyword1", "keyword2"],
  "action_verbs": ["verb1", "verb2"],
  "key_responsibilities": ["resp1", "resp2"],
  "tech_stack": ["tech1", "tech2"],
  "company_values": ["value1", "value2"],
  "seniority_signals": "intern/junior/mid/senior"
}}

RULES:
- must_have_keywords: technologies/skills explicitly listed as required
- preferred_keywords: technologies/skills listed as nice-to-have or preferred
- action_verbs: specific verbs used in the JD (e.g., "develop", "implement", "optimize", "deploy")
- key_responsibilities: the top 5 actual duties described
- tech_stack: all technologies mentioned anywhere in the JD
- company_values: any cultural or value signals (e.g., "fast-paced", "collaborative")
- seniority_signals: what level this role is targeting"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1500,
    )

    return _parse_json_response(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Pass 2: Resume Rewriting
# ---------------------------------------------------------------------------

def _rewrite_resume(client, resume_latex, jd_analysis, job_title, missing_keywords):
    """Pass 2: Rewrite the resume using the JD analysis."""
    analysis_str = json.dumps(jd_analysis, indent=2)

    prompt = f"""You are an expert ATS resume optimizer. Rewrite this LaTeX resume to maximize ATS score for the target role.

You have already analyzed the job description. Use this analysis to guide your rewriting:

JD ANALYSIS:
{analysis_str}

JOB TITLE: {job_title}

MISSING ATS KEYWORDS (not in resume, need to add where truthful): {', '.join(missing_keywords) if missing_keywords else 'None'}

ORIGINAL RESUME (LaTeX):
{resume_latex}

REWRITING RULES — FOLLOW STRICTLY:
1. NEVER fabricate experience, projects, or skills the candidate doesn't have
2. Rewrite each \\resumeItem{{}} bullet to naturally incorporate the JD's action verbs and keywords
3. Mirror the JD's language — if the JD says "implement" use "implement", not "built"
4. Reorder projects: most relevant to this JD first
5. Reorder skills within each category line: JD-relevant skills first
6. If a missing keyword maps to something the candidate clearly does (visible in projects/experience), add it to skills
7. Keep existing metrics and numbers — don't invent new ones
8. Keep LaTeX 100% compilable — preserve ALL preamble, \\usepackage, \\newcommand, formatting macros EXACTLY
9. Do NOT change document structure, fonts, margins, or formatting commands
10. Do NOT add new sections, projects, or experience entries
11. Do NOT remove any projects or experience entries
12. Keep resume to 1 page — do not add content that would overflow
13. Each bullet should start with a strong action verb from the JD analysis

Return ONLY valid JSON (no markdown fences) in this exact format:
{{
  "latex": "<the COMPLETE tailored LaTeX resume from \\\\documentclass to \\\\end{{document}}>",
  "changes": [
    {{"section": "<section name>", "what_changed": "<brief description>", "why": "<which JD requirement this addresses>"}}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=8000,
    )

    return _parse_json_response(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def tailor_resume(client, job_title, jd_text):
    """
    Two-pass resume tailoring with GPT-4.

    Pass 1: Analyze JD → extract requirements, keywords, action verbs
    Pass 2: Rewrite resume using Pass 1 analysis

    Returns dict with: tailored_latex, changes, bullet_diffs, ats_before, ats_after, gaps
    """
    from jd_analyzer import ats_check

    # 1. Fetch resume from settings
    resume_latex = _get_resume_latex()
    if not resume_latex:
        raise ValueError(
            "No resume found. Please paste your LaTeX resume in Settings first."
        )

    # 2. Calculate ATS score BEFORE tailoring
    ats_before_result = ats_check(resume_latex, jd_text)
    ats_before = ats_before_result["ats_score"]
    missing_keywords = ats_before_result["missing"]

    # 3. Analyze skill gaps
    gaps = _analyze_gaps(jd_text, resume_latex)

    # 4. Pass 1: Deep JD analysis
    jd_analysis = _analyze_jd(client, job_title, jd_text)

    # 5. Pass 2: Rewrite resume using analysis
    rewrite_result = _rewrite_resume(
        client, resume_latex, jd_analysis, job_title, missing_keywords
    )

    tailored_latex = rewrite_result.get("latex", "")
    changes = rewrite_result.get("changes", [])

    if not tailored_latex:
        raise ValueError("GPT-4 returned empty resume. Please try again.")

    # 6. Validate LaTeX
    is_valid, validation_errors = _validate_latex(tailored_latex)
    if not is_valid:
        raise ValueError(
            f"Generated LaTeX has structural issues: {'; '.join(validation_errors)}. "
            "Please try again."
        )

    # 7. Calculate ATS score AFTER tailoring
    ats_after_result = ats_check(tailored_latex, jd_text)
    ats_after = ats_after_result["ats_score"]

    # 8. Build bullet-by-bullet diffs
    bullet_diffs = _build_bullet_diffs(resume_latex, tailored_latex)

    return {
        "tailored_latex": tailored_latex,
        "changes": changes,
        "bullet_diffs": bullet_diffs,
        "ats_before": ats_before,
        "ats_after": ats_after,
        "gaps": gaps,
    }

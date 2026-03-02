"""
JD Analyzer — NOC compatibility check, skill match scoring, red flag detection,
ATS resume compatibility check.
Used both in the Streamlit UI (full analysis) and in hourly.py (quick verdict).
"""

import re
from datetime import datetime, timedelta

# --- NOC Codes relevant to tech roles ---
NOC_CODES = {
    "21232": {
        "title": "Software Developers and Programmers",
        "duties": [
            "design, develop, test", "write code", "software applications",
            "maintain software", "programming", "web applications",
            "develop software", "build applications", "implement features",
        ],
    },
    "21211": {
        "title": "Data Scientists",
        "duties": [
            "machine learning", "data analysis", "statistical models",
            "algorithms", "data mining", "predictive models",
            "deep learning", "neural network", "data pipeline",
        ],
    },
    "21231": {
        "title": "Software Engineers",
        "duties": [
            "software architecture", "system design", "software requirements",
            "technical leadership", "software systems", "scalable systems",
            "microservices", "distributed systems",
        ],
    },
    "21222": {
        "title": "Information Systems Specialists",
        "duties": [
            "information systems", "system administration", "IT infrastructure",
            "technical support", "system analysis", "database administration",
        ],
    },
    "21234": {
        "title": "Web Developers and Programmers",
        "duties": [
            "web application", "frontend", "backend", "full stack",
            "website development", "web services", "rest api", "api development",
        ],
    },
    "21230": {
        "title": "Computer Systems Developers and Programmers (General)",
        "duties": [
            "develop software", "programming", "coding", "technical solutions",
            "application development", "software development",
        ],
    },
}

# --- Resume skills tiered by strength ---
MY_SKILLS = {
    "high": [
        "python", "langchain", "rag", "fastapi", "openai", "chromadb",
        "agentic ai", "hybrid search", "ragas", "cohere", "next.js",
        "automation", "web scraping", "rest api", "sql", "git",
    ],
    "medium": [
        "tailwind", "react", "javascript", "typescript", "docker",
        "tensorflow", "pytorch", "pandas", "numpy", "streamlit",
    ],
    "low": [
        "kubernetes", "aws", "gcp", "azure", "java", "go", "rust",
        "c++", "scala", "terraform", "ci/cd", "kafka", "redis",
    ],
}

ALL_MY_SKILLS = MY_SKILLS["high"] + MY_SKILLS["medium"] + MY_SKILLS["low"]


# --- ATS Synonym Groups ---
SYNONYM_GROUPS = [
    {"js", "javascript", "ecmascript"},
    {"ts", "typescript"},
    {"node", "node.js", "nodejs"},
    {"react", "react.js", "reactjs"},
    {"next", "next.js", "nextjs"},
    {"vue", "vue.js", "vuejs"},
    {"express", "express.js", "expressjs"},
    {"fastapi", "fast api"},
    {"scikit-learn", "sklearn", "scikit learn"},
    {"langchain", "lang chain"},
    {"langgraph", "lang graph"},
    {"hugging face", "huggingface", "hf"},
    {"ml", "machine learning"},
    {"dl", "deep learning"},
    {"nlp", "natural language processing"},
    {"cv", "computer vision"},
    {"gen ai", "generative ai", "genai"},
    {"llm", "large language model", "large language models"},
    {"rag", "retrieval augmented generation", "retrieval-augmented generation"},
    {"ai agent", "agentic ai", "agentic"},
    {"k8s", "kubernetes"},
    {"aws", "amazon web services"},
    {"gcp", "google cloud", "google cloud platform"},
    {"azure", "microsoft azure"},
    {"ci/cd", "cicd", "ci cd", "continuous integration"},
    {"terraform", "tf", "infrastructure as code"},
    {"postgres", "postgresql"},
    {"mongo", "mongodb"},
    {"chromadb", "chroma", "chroma db"},
    {"elastic", "elasticsearch", "elastic search"},
    {"rabbitmq", "rabbit mq"},
    {"golang", "go lang"},
    {"c#", "csharp", "c sharp"},
    {"c++", "cpp"},
    {"rest api", "restful api", "rest apis", "restful"},
    {"graphql", "graph ql"},
    {"docker", "containerization", "containers"},
    {"git", "version control"},
    {"sql", "structured query language"},
    {"html", "html5"},
    {"css", "css3"},
    {"tailwind", "tailwind css", "tailwindcss"},
    {"sass", "scss"},
    {"selenium", "web automation"},
    {"etl", "extract transform load"},
    {"airflow", "apache airflow"},
    {"spark", "apache spark", "pyspark"},
    {"kafka", "apache kafka"},
    {"pinecone", "pinecone db"},
    {"weaviate", "weaviate db"},
    {"cohere", "cohere api"},
    {"openai", "openai api"},
]

_SYNONYM_LOOKUP = {}
for _group in SYNONYM_GROUPS:
    _frozen = frozenset(_group)
    for _term in _group:
        _SYNONYM_LOOKUP[_term] = _frozen


def _expand_synonyms(term):
    """Return all known synonyms for a term, including itself."""
    return _SYNONYM_LOOKUP.get(term.lower(), frozenset({term.lower()}))


# --- ATS Requirement Extraction Patterns ---
_EXPERIENCE_PATTERNS = [
    re.compile(
        r"(?:minimum|at\s+least|min\.?)?\s*(\d+)\s*[\+\-]?\s*(?:to\s+\d+\s+)?years?\s+"
        r"(?:of\s+)?(?:experience|exp\.?|work\s+experience)",
        re.IGNORECASE,
    ),
    re.compile(r"(\d+)\s*\+?\s*yrs?\s+(?:of\s+)?(?:experience|exp\.?)", re.IGNORECASE),
]

_DEGREE_PATTERNS = [
    re.compile(
        r"(?:bachelor'?s?|b\.?s\.?|b\.?tech|b\.?e\.?)\s*(?:degree)?\s*(?:in\s+)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:master'?s?|m\.?s\.?|m\.?tech|m\.?e\.?)\s*(?:degree)?\s*(?:in\s+)?",
        re.IGNORECASE,
    ),
    re.compile(r"(?:ph\.?d\.?|doctorate)", re.IGNORECASE),
]

_CERT_PATTERNS = [
    re.compile(
        r"(AWS\s+(?:Solutions?\s+Architect|Developer|SysOps|DevOps)|"
        r"Azure\s+(?:Developer|Administrator|AI\s+Engineer)|"
        r"GCP\s+(?:Professional|Associate)|"
        r"PMP|Scrum\s+Master|CISSP|CKA|CKAD)",
        re.IGNORECASE,
    ),
]


def _extract_experience_requirement(text):
    results = []
    seen = set()
    for pattern in _EXPERIENCE_PATTERNS:
        for match in pattern.finditer(text):
            years = int(match.group(1))
            if years not in seen:
                seen.add(years)
                results.append({"type": "experience", "value": f"{years}+ years", "years": years})
    return results


def _extract_degree_requirements(text):
    results = []
    for pattern in _DEGREE_PATTERNS:
        for match in pattern.finditer(text):
            results.append({"type": "degree", "value": match.group(0).strip()})
    return results


def _extract_cert_requirements(text):
    results = []
    for pattern in _CERT_PATTERNS:
        for match in pattern.finditer(text):
            results.append({"type": "certification", "value": match.group(0).strip()})
    return results


def _resume_has_experience(resume_lower, required_years):
    """Heuristic: check if resume text suggests enough experience."""
    year_range = re.compile(r"(\d{4})\s*[-\u2013]\s*(?:present|\d{4})", re.IGNORECASE)
    for m in year_range.finditer(resume_lower):
        start = int(m.group(1))
        if start >= 2000:
            span = 2026 - start
            if span >= required_years:
                return True
    exp_mention = re.compile(r"(\d+)\s*\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE)
    for m in exp_mention.finditer(resume_lower):
        if int(m.group(1)) >= required_years:
            return True
    return required_years <= 1


_SUGGESTION_HINTS = {
    "docker": "skills section or project descriptions",
    "kubernetes": "skills section (only if you have exposure)",
    "aws": "skills section or cloud experience subsection",
    "gcp": "skills section or cloud experience subsection",
    "azure": "skills section or cloud experience subsection",
    "terraform": "DevOps/infrastructure skills section",
    "ci/cd": "project descriptions (mention deployment workflows)",
    "kafka": "skills section (only if you have exposure)",
    "redis": "skills section (only if you have exposure)",
    "spark": "skills section (only if you have exposure)",
    "airflow": "skills section (only if you have exposure)",
}


# --- Default Resume Text (lazy-loaded to avoid circular import) ---
_DEFAULT_RESUME_TEXT_CACHE = None


def _get_default_resume_text():
    global _DEFAULT_RESUME_TEXT_CACHE
    if _DEFAULT_RESUME_TEXT_CACHE is not None:
        return _DEFAULT_RESUME_TEXT_CACHE

    # Try dynamic profile first
    try:
        from profile import get_resume_text
        dynamic = get_resume_text()
        if dynamic:
            _DEFAULT_RESUME_TEXT_CACHE = dynamic
            return _DEFAULT_RESUME_TEXT_CACHE
    except Exception:
        pass

    # Fall back to hardcoded data
    from resume_tailor import RESUME_SKILLS, PROJECTS
    from message_generator import SUBIDH_PROFILE
    project_lines = []
    for name, info in PROJECTS.items():
        project_lines.append(f"{name}: {info['one_liner']}. Keywords: {', '.join(info['keywords'])}")
    _DEFAULT_RESUME_TEXT_CACHE = (
        f"SKILLS: {', '.join(RESUME_SKILLS)}\n\n"
        f"PROFILE:\n{SUBIDH_PROFILE}\n\n"
        f"PROJECTS:\n" + "\n".join(project_lines) + "\n\n"
        f"EDUCATION:\nM.Tech in Artificial Intelligence, Amity University Noida (graduating March 2026)\n\n"
        f"ADDITIONAL SKILLS: {', '.join(ALL_MY_SKILLS)}"
    )
    return _DEFAULT_RESUME_TEXT_CACHE


def ats_check(resume_text, jd_text):
    """Compare resume against JD for ATS keyword compatibility.

    Returns dict with: ats_score (int 0-100), found (list), missing (list),
    suggestions (list), truncation_warning (bool).
    """
    resume_lower = resume_text.lower()

    truncation_warning = len(jd_text.strip()) < 600

    # Extract tech keywords from JD
    jd_tech_keywords = _extract_tech_keywords(jd_text)

    # Extract non-tech requirements
    experience_reqs = _extract_experience_requirement(jd_text)
    degree_reqs = _extract_degree_requirements(jd_text)
    cert_reqs = _extract_cert_requirements(jd_text)

    # Match tech keywords with synonym expansion
    tech_found = []
    tech_missing = []
    for kw in jd_tech_keywords:
        synonyms = _expand_synonyms(kw)
        if any(syn in resume_lower for syn in synonyms):
            tech_found.append(kw)
        else:
            tech_missing.append(kw)

    # Match non-tech requirements
    non_tech_found = []
    non_tech_missing = []

    for req in experience_reqs:
        if _resume_has_experience(resume_lower, req["years"]):
            non_tech_found.append(req["value"])
        else:
            non_tech_missing.append(req["value"])

    for req in degree_reqs:
        raw_lower = req["value"].lower()
        if any(t in resume_lower for t in [raw_lower, "m.tech", "master", "b.tech", "bachelor"]):
            non_tech_found.append(req["value"])
        else:
            non_tech_missing.append(req["value"])

    for req in cert_reqs:
        if req["value"].lower() in resume_lower:
            non_tech_found.append(req["value"])
        else:
            non_tech_missing.append(req["value"])

    # Calculate score
    total_items = len(jd_tech_keywords) + len(non_tech_found) + len(non_tech_missing)
    found_items = len(tech_found) + len(non_tech_found)
    ats_score = round(found_items / total_items * 100) if total_items > 0 else 100

    # Generate suggestions
    suggestions = []
    for kw in tech_missing:
        section = _SUGGESTION_HINTS.get(kw.lower(), "your skills section")
        suggestions.append(f"Add '{kw}' to {section}")
    for val in non_tech_missing:
        if "year" in val.lower():
            suggestions.append(
                f"JD requires '{val}' \u2014 consider adding experience duration "
                f"to your PathToPR entry or project timeline"
            )
        else:
            suggestions.append(f"JD mentions '{val}' \u2014 verify your resume covers this")

    return {
        "ats_score": ats_score,
        "found": sorted(tech_found + non_tech_found),
        "missing": sorted(tech_missing + non_tech_missing),
        "suggestions": suggestions,
        "experience_reqs": experience_reqs,
        "degree_reqs": degree_reqs,
        "cert_reqs": cert_reqs,
        "truncation_warning": truncation_warning,
    }


def quick_ats(jd_text, resume_text=None):
    """Quick ATS score for hourly.py. Returns int 0-100."""
    if resume_text is None:
        resume_text = _get_default_resume_text()
    return ats_check(resume_text, jd_text)["ats_score"]


# --- Red flags ---
RED_FLAGS = {
    "unpaid": {
        "patterns": ["unpaid", "voluntary", "volunteer", "no stipend", "unpaid internship"],
        "message": "UNPAID — This won't count for IRCC work experience",
    },
    "overqualified": {
        "patterns": [
            "senior", "lead", "principal", "staff", "5+ years",
            "7+ years", "10+ years", "8+ years", "6+ years",
        ],
        "message": "SENIOR LEVEL — You'll likely be filtered out, apply only if JD duties match",
    },
    "region_locked": {
        "patterns": [
            "us only", "usa only", "eu only", "europe only",
            "us citizen", "clearance required", "work authorization required",
            "must be authorized to work in the united states",
        ],
        "message": "REGION LOCKED — Requires specific work authorization you may not have",
    },
    "generic_title": {
        "patterns": [
            "trainee", "management trainee", "graduate trainee",
            "fresher trainee",
        ],
        "message": "GENERIC TITLE — May not map to a skilled NOC code, verify duties carefully",
    },
    "bond_risk": {
        "patterns": [
            "bond", "service agreement", "minimum commitment",
            "2 year bond", "3 year bond",
        ],
        "message": "BOND — Acceptable only if title is NOC-compatible, verify before accepting",
    },
    "contract_risk": {
        "patterns": [
            "contract", "freelance", "gig", "project-based", "temporary",
        ],
        "message": "CONTRACT/TEMP — May not qualify for experience letter, confirm with employer",
    },
    "non_english": {
        "patterns": [
            "deutsch", "fran\u00e7ais", "espa\u00f1ola", "wir suchen",
            "aufgaben", "anforderungen", "stellenangebot", "nous recherchons",
            "requisitos", "offre d'emploi",
        ],
        "message": "NON-ENGLISH — Job posting is not in English, likely region-locked",
    },
}


def _extract_tech_keywords(text):
    """Extract technology keywords from a job description."""
    text_lower = text.lower()
    # Common tech keywords to look for
    tech_terms = [
        "python", "java", "javascript", "typescript", "go", "golang", "rust",
        "c++", "c#", "scala", "ruby", "php", "swift", "kotlin",
        "react", "angular", "vue", "next.js", "nuxt", "svelte",
        "node.js", "express", "django", "flask", "fastapi", "spring",
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure",
        "terraform", "ansible", "jenkins", "ci/cd",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "kafka", "rabbitmq", "graphql", "rest api", "grpc",
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "langchain", "langgraph", "openai", "rag", "llm",
        "chromadb", "pinecone", "weaviate", "vector database",
        "agentic ai", "ai agent", "cohere", "ragas", "hybrid search",
        "streamlit", "gradio", "hugging face",
        "git", "github", "gitlab", "bitbucket",
        "tailwind", "css", "html", "sass",
        "web scraping", "automation", "selenium", "playwright",
        "data pipeline", "etl", "airflow", "spark",
    ]
    found = []
    for term in tech_terms:
        if term in text_lower:
            found.append(term)
    return list(set(found))


def analyze_noc(title, text):
    """Match a JD against NOC codes. Returns best match with confidence."""
    text_lower = text.lower()
    title_lower = title.lower()
    combined = title_lower + " " + text_lower

    best_code = None
    best_score = 0
    best_matched_duties = []

    for code, info in NOC_CODES.items():
        score = 0
        matched = []

        # Check title keywords
        noc_title_words = info["title"].lower().split()
        title_overlap = sum(1 for w in noc_title_words if w in title_lower)
        if title_overlap >= 2:
            score += 3

        # Check duty phrases
        for duty in info["duties"]:
            if duty in combined:
                score += 1
                matched.append(duty)

        if score > best_score:
            best_score = score
            best_code = code
            best_matched_duties = matched

    if not best_code:
        return {
            "code": None,
            "title": None,
            "confidence": "red",
            "emoji": "\U0001f534",
            "matched_duties": [],
            "message": "No clear NOC match found — generic title with no identifiable skilled duties",
        }

    if best_score >= 5:
        confidence = "green"
        emoji = "\U0001f7e2"
    elif best_score >= 2:
        confidence = "yellow"
        emoji = "\U0001f7e1"
    else:
        confidence = "red"
        emoji = "\U0001f534"

    return {
        "code": best_code,
        "title": NOC_CODES[best_code]["title"],
        "confidence": confidence,
        "emoji": emoji,
        "matched_duties": best_matched_duties,
        "message": f"Best NOC match: **{best_code} — {NOC_CODES[best_code]['title']}** {emoji}",
    }


def analyze_skills(text):
    """Compare JD tech requirements against resume skills."""
    jd_keywords = _extract_tech_keywords(text)

    matched = []
    gaps = []

    for kw in jd_keywords:
        if kw in ALL_MY_SKILLS:
            matched.append(kw)
        else:
            gaps.append(kw)

    total = len(jd_keywords)
    match_pct = (len(matched) / total * 100) if total > 0 else 0

    return {
        "matched": sorted(matched),
        "gaps": sorted(gaps),
        "total_required": total,
        "match_percentage": round(match_pct),
    }


def detect_red_flags(title, text):
    """Scan for red flag patterns in the JD."""
    combined = (title + " " + text).lower()
    flags = []

    for flag_type, info in RED_FLAGS.items():
        for pattern in info["patterns"]:
            if pattern in combined:
                flags.append({
                    "type": flag_type,
                    "trigger": pattern,
                    "message": info["message"],
                })
                break  # one flag per category

    return flags


def get_verdict(noc_result, skill_result, flags):
    """Generate final verdict based on all analyses."""
    critical_flags = {"unpaid", "region_locked", "non_english"}
    has_critical = any(f["type"] in critical_flags for f in flags)

    noc_ok = noc_result["confidence"] in ("green", "yellow")
    skill_ok = skill_result["match_percentage"] >= 60

    if has_critical:
        return "skip", "\u274c SKIP", "Critical red flags detected"
    elif noc_ok and skill_ok and len(flags) == 0:
        return "apply", "\u2705 APPLY", "NOC compatible + strong skill match + no red flags"
    elif noc_ok and skill_ok:
        return "caution", "\u26a0\ufe0f APPLY WITH CAUTION", "Good match but some flags to watch"
    elif noc_ok and not skill_ok:
        return "caution", "\u26a0\ufe0f APPLY WITH CAUTION", f"NOC compatible but only {skill_result['match_percentage']}% skill match"
    elif not noc_ok and skill_ok:
        return "caution", "\u26a0\ufe0f APPLY WITH CAUTION", "Good skill match but weak NOC alignment"
    else:
        return "skip", "\u274c SKIP", "Low skill match and weak NOC alignment"


def full_analyze(title, description):
    """Run all analyses and return complete results dict."""
    noc = analyze_noc(title, description)
    skills = analyze_skills(description)
    flags = detect_red_flags(title, description)
    verdict_key, verdict_label, verdict_reason = get_verdict(noc, skills, flags)

    return {
        "noc": noc,
        "skills": skills,
        "red_flags": flags,
        "verdict": verdict_key,
        "verdict_label": verdict_label,
        "verdict_reason": verdict_reason,
    }



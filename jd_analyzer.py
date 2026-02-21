"""
JD Analyzer — NOC compatibility check, skill match scoring, red flag detection.
Used both in the Streamlit UI (full analysis) and in nightly.py (quick verdict).
"""

import re

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
    critical_flags = {"unpaid", "region_locked"}
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


def quick_analyze(title, description):
    """Quick one-line verdict for use in nightly.py battle plan."""
    result = full_analyze(title, description)
    noc = result["noc"]
    skills = result["skills"]

    noc_str = f"NOC {noc['code']}" if noc["code"] else "NOC ?"
    match_str = f"{skills['match_percentage']}% match"

    return f"{result['verdict_label']} | {noc_str} | {match_str}"

"""
Hourly Job Search Automation
Runs all scrapers, scores/ranks jobs, sends email, and saves to Supabase.
Designed to run both locally and in GitHub Actions.
"""

import os
import re
from datetime import datetime
from rapidfuzz import fuzz
from tracker import (
    init_db, save_scraped_job, save_email_log, get_existing_job_urls,
    save_notification, init_notifications_table,
    send_push_notifications,
)
from scraper import run_all_scrapers
from send_email import build_email_content, send_email, get_alert_number

# Default fallback blocked list
_DEFAULT_BLOCKED = {"turing"}


def _get_blocked_companies():
    """Try to load blocked companies from DB, fall back to hardcoded default."""
    try:
        from profile import get_blocked_companies
        blocked = get_blocked_companies()
        if blocked is not None:
            return blocked
    except Exception:
        pass
    return _DEFAULT_BLOCKED


# Backward-compatible reference
BLOCKED_COMPANIES = _DEFAULT_BLOCKED

# Curated list of desired AI/ML job titles for fuzzy matching
DESIRED_TITLES = [
    "AI Engineer",
    "Generative AI Engineer",
    "Machine Learning Engineer",
    "AI/ML Developer",
    "Machine Learning Research Engineer",
    "Agentic AI Engineer",
    "Data and AI Engineer",
    "AI Agent Developer",
    "AI/ML Engineer",
    "Generative AI Developer",
    "AI Research Engineer",
    "Agentic AI Developer",
    "Deep Tech AI Engineer",
    "ML Engineer",
    "AI-ML Systems Engineer",
    "Machine Learning Scientist",
    "Artificial Intelligence Engineer",
    "LLM Engineer",
    "RAG Developer",
    "NLP Engineer",
    "LangChain Developer",
    "FastAPI Developer",
    "AI Pipeline Engineer",
    "Prompt Engineer",
    "Conversational AI Engineer",
    "AI Solutions Engineer",
    "Applied AI Engineer",
    "AI Product Engineer",
    "GenAI Engineer",
    "GenAI Researcher",
    "Generative AI Developer",
    "Deep Learning Engineer",
    "NLP Developer",
    "Document AI Engineer",
    "OCR Engineer",
    "AI Chatbot Developer",
    "MLOps Engineer",
    "AI/ML Researcher",
    "Applied Machine Learning Engineer",
    "LLM Application Developer",
    "AI Agent Engineer",
    "Predictive Modeling Engineer",
    "Multimodal AI Engineer",
    "LLM Fine-Tuning Engineer",
    "Machine Learning Developer",
    "AI ML Engineer",
    "Machine Learning Researcher",
    "ML Researcher",
    "Generative AI Developer",
    "Machine Learning Engineer",
    "AI ML Developer",
    "Speech Recognition Engineer",
    "LLM & RAG Engineer",
    "Junior Artificial Intelligence Engineer",
    "Junior ML Engineer",
    "Junior AI Engineer",
    "Entry Level AI Engineer",
    "Graduate AI Engineer",
    "Graduate ML Engineer",
    "GenAI Document AI Engineer",
    "Research Scientist",
    "Graduate Technical Engineer",
    "AI Research Scientist",
    "Python Engineer",
    "Large Language Model Engineer",
    "NLP Researcher",
    "Research Assistant AI/ML",
    "AI/ML Research and Development Engineer",
    "AI Engineer",
    "Artificial Intelligence (AI) Engineer",
]

# Pre-compute normalized titles for faster matching
_DESIRED_TITLES_LOWER = [t.lower().strip() for t in DESIRED_TITLES]

# Domain keywords — a job title must contain at least one to be considered relevant
_DOMAIN_KEYWORDS = {
    "ai", "ml", "artificial intelligence", "machine learning", "deep learning",
    "data science", "data scientist", "data analyst", "analytics",
    "nlp", "natural language", "computer vision", "llm", "large language model",
    "genai", "generative ai", "agentic", "rag", "langchain",
    "python", "fastapi", "backend engineer", "software engineer",
    "mlops", "prompt engineer", "chatbot", "conversational ai",
    "iot", "robotics", "uav", "digital twin", "edge computing", "simulation",
    "ocr", "document ai", "speech recognition", "predictive modeling",
    "optimization algorithm", "multimodal",
}


# Internship markers — any title containing these is rejected (jobs-only mode)
_INTERN_REJECT_KEYWORDS = ("intern", "internship", "trainee", "apprentice")

# Titles matching any of these (case-insensitive, word-boundary) are rejected:
# senior/staff/principal/lead levels, Java roles, generic Software Engineer /
# Data Scientist roles, and mid-level postings.
_TITLE_REJECT_RE = re.compile(
    r"\b("
    r"senior|sr|staff|principal|lead|phd|distinguished|"
    r"java|"
    r"software engineer|data scientist|data science|backend engineer|specialist|"
    r"python developer|python automation engineer|manager|computer vision|"
    r"mid[\s-]?level"
    r")\b",
    re.IGNORECASE,
)


def _matches_desired_title(job_title, threshold=65):
    """Check if a job title matches any desired title.

    Filter pipeline (jobs-only, junior/entry only):
    1. Reject titles containing an internship marker.
    2. Reject senior/staff/principal/lead/PhD, Java, Software Engineer,
       Data Scientist, Backend Engineer, Specialist, and mid-level titles
       (see _TITLE_REJECT_RE).
    3. Reject generic one-word titles.
    4. Exact match against the curated list (normalized).
    5. Domain keyword check + fuzzy match — the title must contain a relevant
       domain keyword AND score >= threshold via token_sort_ratio against at
       least one desired title. This prevents false positives like
       'Market Research Engineer' matching 'Research Engineer'.
    """
    normalized = job_title.lower().strip()
    if not normalized:
        return False

    # Step 1: reject internships
    if any(kw in normalized for kw in _INTERN_REJECT_KEYWORDS):
        return False

    # Step 2: reject senior/staff/principal/lead, Java, generic SWE/DS, mid-level
    if _TITLE_REJECT_RE.search(normalized):
        return False

    # Step 3: reject generic one-word titles
    if normalized in ("engineer", "developer", "scientist", "analyst"):
        return False

    # Step 3: exact match
    if normalized in _DESIRED_TITLES_LOWER:
        return True

    # Step 4: must contain at least one domain keyword
    has_domain_keyword = any(kw in normalized for kw in _DOMAIN_KEYWORDS)
    if not has_domain_keyword:
        return False

    # Step 5: fuzzy match using token_sort_ratio (penalizes extra/missing words)
    best = max(
        fuzz.token_sort_ratio(normalized, desired)
        for desired in _DESIRED_TITLES_LOWER
    )
    return best >= threshold


def main():
    print("=== Hourly Job Search Automation ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize database
    init_db()
    init_notifications_table()

    # Run all automated scrapers
    print("Running scrapers...")
    jobs, sources_status, sources_errors = run_all_scrapers()
    print(f"\nTotal jobs found: {len(jobs)}")
    for source, count in sources_status.items():
        print(f"  {source}: {count}")
    if sources_errors:
        print(f"\nFailed scrapers: {', '.join(sources_errors.keys())}")

    # Filter out already-seen jobs (deduplication across hourly runs)
    print("\nChecking for duplicates...")
    existing_urls = get_existing_job_urls()
    new_jobs = [j for j in jobs if j.get("url", "") not in existing_urls]
    print(f"New jobs: {len(new_jobs)} (filtered out {len(jobs) - len(new_jobs)} duplicates)")

    # Filter blocked companies
    new_jobs = [j for j in new_jobs if j.get("company", "").strip().lower() not in _get_blocked_companies()]

    # Only keep jobs whose title matches or is similar to the desired titles list
    new_jobs = [j for j in new_jobs if _matches_desired_title(j.get("title", ""))]
    print(f"After title filter (desired titles match): {len(new_jobs)}")

    # Health check: if LinkedIn scraper returned 0 results, flag it
    linkedin_count = sources_status.get("LinkedIn AI/ML", 0)
    if linkedin_count == 0 and "LinkedIn AI/ML" not in sources_errors:
        print("\n[HEALTH CHECK FAILED] LinkedIn scraper returned 0 results — possible scraper failure.")
        try:
            save_notification(
                title="Scraper Health Check Failed",
                body="LinkedIn AI/ML scraper returned 0 results. Possible scraper failure — check logs.",
                notification_type="health_check",
                metadata={"source": "LinkedIn AI/ML", "timestamp": datetime.now().isoformat()},
            )
        except Exception:
            pass

    # Auto-analyze top jobs for verdict/ATS
    if new_jobs:
        print("\nRunning auto-analysis on top jobs...")
        try:
            from jd_analyzer import full_analyze, quick_ats
            for job in new_jobs[:15]:
                try:
                    result = full_analyze(job.get("title", ""), job.get("description", ""))
                    job["verdict"] = result.get("verdict_label", "")
                    job["ats_score"] = quick_ats(job.get("description", ""))
                    job["skill_match"] = result.get("skills", {}).get("match_percentage", 0)
                    job["noc_verdict"] = result.get("noc", {}).get("confidence", "")
                except Exception:
                    pass
            print(f"Auto-analysis complete for top {min(15, len(new_jobs))} jobs.")
        except ImportError:
            print("jd_analyzer not available — skipping auto-analysis.")

    # Save new jobs to database
    print("\nSaving new jobs to database...")
    for job in new_jobs:
        try:
            save_scraped_job(
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                source=job.get("source", ""),
                url=job.get("url", ""),
                description=job.get("description", ""),
                score=job.get("score", 0),
                verdict=job.get("verdict", ""),
                ats_score=job.get("ats_score", 0),
            )
        except Exception:
            pass

    # Only send email if there are any new jobs
    if not new_jobs:
        print("\nNo new jobs found this run. Skipping email.")
        print("Done!")
        return

    print("\nBuilding email content...")
    alert_number = get_alert_number()

    for job in new_jobs:
        job["filtered"] = True

    md_content = build_email_content(new_jobs, sources_status, sources_errors)

    # Send email
    print(f"Sending Job Alert #{alert_number}...")
    email_sent = send_email(md_content, alert_number=alert_number)

    # Save to Supabase so frontend can display it
    print("Saving email log to database...")
    try:
        save_email_log(
            subject=f"Job Alert #{alert_number}",
            markdown_content=md_content,
            html_content="",
            jobs_count=len(new_jobs),
            sources_summary=sources_status,
            email_sent=email_sent,
        )
    except Exception as e:
        print(f"  WARNING: Could not save email log to database: {e}")

    # Save in-app notification
    print("Saving in-app notification...")
    try:
        save_notification(
            title=f"Job Alert #{alert_number}",
            body=f"{len(new_jobs)} new jobs found",
            notification_type="job_alert",
            metadata={
                "jobs_count": len(new_jobs),
                "alert_number": alert_number,
                "sources": sources_status,
            },
        )
    except Exception as e:
        print(f"  WARNING: Could not save notification: {e}")

    # Send push notification to subscribed devices
    print("Sending push notification...")
    try:
        send_push_notifications(
            title=f"Job Alert #{alert_number}",
            body=f"{len(new_jobs)} new jobs found",
            url="/tonight",
        )
    except Exception as e:
        print(f"  WARNING: Could not send push notification: {e}")

    print(f"\nDone! Job Alert #{alert_number} sent: {email_sent}. {len(new_jobs)} jobs saved.")


if __name__ == "__main__":
    main()

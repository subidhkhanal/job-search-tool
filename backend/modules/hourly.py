"""
Hourly Job Search Automation
Runs all scrapers, scores/ranks jobs, sends email, and saves to Supabase.
Designed to run both locally and in GitHub Actions.
"""

import os
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

# Curated list of desired internship titles for fuzzy matching
DESIRED_TITLES = [
    "Software Engineer Intern",
    "AI Engineer Intern",
    "AI Internship",
    "Generative AI Intern",
    "Machine Learning Intern",
    "AI/ML Developer Intern",
    "Machine Learning Research Intern",
    "Agentic AI Intern",
    "Internship - Computer Vision",
    "Data and AI Engineer Intern",
    "AI Agent Development Internship",
    "Machine Learning Internship",
    "AI/ML Intern",
    "Research Intern – Generative AI Agents",
    "AI Research Intern",
    "Generative AI, Agentic AI & AI Agent",
    "AI/ML Internship Opportunities (Deep Tech AI)",
    "ML/AI Intern",
    "AI/ML Engineer",
    "Machine Learning Engineer Internship",
    "Computer Vision Engineer - Intern",
    "AI Intern",
    "AI Agent Development",
    "AI/ML Product Development Internship (Remote)",
    "Python Developer Internship",
    "AI Engineering Internship",
    "Generative AI Fresher",
    "AI-ML Systems Engineering Internship",
    "Internship: Machine Learning / AI",
    "Artificial Intelligence Internship",
    "LLM Engineer Intern",
    "RAG Developer Intern",
    "NLP Engineer Intern",
    "LangChain Developer Intern",
    "Python Backend Intern",
    "FastAPI Developer Intern",
    "AI Pipeline Engineer Intern",
    "Prompt Engineer Intern",
    "Conversational AI Intern",
    "AI Solutions Engineer Intern",
    "Applied AI Intern",
    "AI Product Intern",
    "GenAI Intern",
    "GenAI Researcher",
    "Generative AI Developer Intern",
    "ML Engineer Intern",
    "Deep Learning Intern",
    "NLP Intern",
    "Document AI Intern",
    "OCR & Document AI Intern",
    "AI Chatbot Developer Intern",
    "Conversational AI Engineer Intern",
    "MLOps Intern",
    "AI/ML Research Intern",
    "Technical Intern - AI/ML",
    "Intern - Machine Learning (Gen AI)",
    "AI Research Internship",
    "AI Intern",
    "Applied Machine Learning Intern",
    "AI Backend Intern",
    "LLM Application Developer Intern",
    "AI Agent Engineer Intern",
    "AI Strategy Intern",
    "AI Trainee",
    "AI/ML Trainee Engineer",
    "Predictive Modeling Intern",
    "Multimodal AI Intern",
    "AI Evaluation Intern",
    "LLM Fine-Tuning Intern",
    "Machine Learning",
    "Python Development",
    "AI Intern",
    "AI ML Intern",
    "Machine Learning Researcher Intern",
    "ML Research Intern",
    "Intern - Generative AI",
    "Intern, Machine Learning",
    "Intern - AI ML",
    "Speech Recognition Intern",
    "Computer Vision Intern",
    "Research Intern",
    "Data Science - Intern",
    "AI/ML Engineering Intern",
    "AI Intern – LLM & RAG",
    "Intern, AI/ML Specialist",
    "Jr. Artificial Intelligence Engineer",
    "ML Intern",
    "Internship - Data Science",
    "GenAI / Document AI Intern",
    "Engineering Intern – Gen AI",
    "Research Sciences Intern",
    "Graduate Intern Technical",
    "Intern - AI Research",
    "Python Intern",
    "Large Language Model Engineering Internship",
    "Backend Engineer Intern",
    "NLP Research Intern",
    "AI Intern",
    "Research Assistant – AI/ML",
    "AI/ML Research and Development Intern",
    "AI Engineer"
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


def _matches_desired_title(job_title, threshold=65):
    """Check if a job title matches any desired title.

    Two-step filter:
    1. Exact match against the curated list (normalized).
    2. Domain keyword check + fuzzy match — the title must contain a relevant
       domain keyword AND score >= threshold via token_sort_ratio against at
       least one desired title. This prevents false positives like
       'Market Research Intern' matching 'Research Intern'.
    """
    normalized = job_title.lower().strip()
    if not normalized:
        return False

    # Reject generic one-word titles
    if normalized in ("intern", "internship", "trainee"):
        return False

    # Step 1: exact match
    if normalized in _DESIRED_TITLES_LOWER:
        return True

    # Step 2: must contain at least one domain keyword
    has_domain_keyword = any(kw in normalized for kw in _DOMAIN_KEYWORDS)
    if not has_domain_keyword:
        return False

    # Step 3: fuzzy match using token_sort_ratio (penalizes extra/missing words)
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

"""
Hourly Job Search Automation
Runs all scrapers, scores/ranks jobs, sends email, and saves to Supabase.
Designed to run both locally and in GitHub Actions.
"""

import os
import json
from datetime import datetime
from tracker import (
    init_db, save_scraped_job, save_email_log, get_existing_job_urls,
)
from scraper import run_all_scrapers
from send_email import build_email_content, send_email, get_alert_number

# Companies to exclude from battle plan (scams, bad reputation, etc.)
BLOCKED_COMPANIES = {"turing"}


def score_job(job):
    """Score a job listing based on profile match. Higher = better fit."""
    text = (
        job.get("title", "") + " " + job.get("description", "")
    ).lower()
    score = 0

    # Instant disqualify: non-English
    non_english = [
        "deutsch", "fran\u00e7ais", "espa\u00f1ola", "wir suchen",
        "aufgaben", "anforderungen", "stellenangebot",
        "nous recherchons", "requisitos",
    ]
    if any(kw in text for kw in non_english):
        return -100

    # Exact stack match (FROM RESUME — highest signal)
    stack_match = [
        "langchain", "chromadb", "fastapi", "rag",
        "openai api", "agentic", "cohere", "ragas",
        "hybrid search", "next.js", "automation pipeline",
        "gemini", "gemini api",
    ]
    score += sum(12 for kw in stack_match if kw in text)

    # High-value keywords (general relevance)
    high_value = [
        "gen ai", "generative ai", "llm", "large language model",
        "rag", "retrieval augmented", "ai agent", "agentic",
        "langchain", "vector database", "nlp",
    ]
    score += sum(5 for kw in high_value if kw in text)

    # Role title match
    role_titles = [
        "software developer", "software engineer", "ai developer",
        "ml engineer", "data scientist", "ai engineer",
        "machine learning developer", "gen ai developer",
        "backend developer", "full stack developer",
        "python developer", "automation engineer",
        "nlp engineer", "ai intern", "ml intern",
    ]
    title_lower = job.get("title", "").lower()
    score += sum(8 for t in role_titles if t in title_lower)

    # Delhi-NCR location bonus (highest priority — you're in Noida)
    location = job.get("location", "").lower()
    full_text = location + " " + text
    ncr_keywords = [
        "noida", "delhi", "gurgaon", "gurugram", "ncr",
        "delhi-ncr", "delhi ncr", "greater noida",
        "faridabad", "ghaziabad",
    ]
    if any(kw in full_text for kw in ncr_keywords):
        score += 20
    elif any(kw in full_text for kw in [
        "india", "bangalore", "bengaluru", "hyderabad", "mumbai", "pune",
    ]):
        score += 5

    # Onsite/hybrid bonus (preferred over remote)
    work_mode_keywords = [
        "onsite", "on-site", "on site", "hybrid",
        "office", "in-office", "in office",
        "work from office", "wfo",
    ]
    if any(kw in full_text for kw in work_mode_keywords):
        score += 10

    # Remote is acceptable but not preferred
    if "remote" in full_text and not any(kw in full_text for kw in ncr_keywords):
        score += 2

    # Fresher/intern friendly bonus
    if any(kw in text for kw in [
        "intern", "fresher", "entry level", "0-1 year", "junior",
    ]):
        score += 5

    # Negative signals
    negative = ["senior", "5+ years", "lead", "principal", "unpaid",
                "us only", "eu only", "clearance required"]
    score -= sum(10 for kw in negative if kw in text)

    # === Startup signals (small teams = higher response rates) ===
    startup_signals = ["seed", "series a", "series b", "early stage", "founding",
                       "small team", "10-50 employees", "startup", "funded",
                       "yc", "y combinator"]
    if any(kw in text for kw in startup_signals):
        score += 8

    # === Urgency signals (faster hiring process) ===
    urgency_signals = ["immediate joining", "urgently hiring", "asap",
                       "start immediately", "urgent requirement", "walk-in",
                       "notice period: immediate"]
    if any(kw in text for kw in urgency_signals):
        score += 6

    # === Direct contact available (skip HR) ===
    direct_contact = ["email us at", "dm me", "reach out to", "contact:",
                      "founders@", "hiring@", "apply directly",
                      "send resume to", "whatsapp"]
    if any(kw in text for kw in direct_contact):
        score += 6

    # === High competition penalty ===
    high_competition = ["500+ applicants", "1000+ applicants", "200+ applicants",
                        "500+ applications", "1000+ applications"]
    if any(kw in text for kw in high_competition):
        score -= 8

    return score


def _get_relevance_label(score):
    """Return a relevance label emoji + text for a given score."""
    if score >= 35:
        return "\U0001f525 PERFECT FIT"
    elif score >= 25:
        return "\u2b50 STRONG MATCH"
    elif score >= 15:
        return "\U0001f4cc WORTH APPLYING"
    else:
        return "\U0001f4cb STRETCH"


def llm_rerank_jobs(jobs, top_n=20):
    """
    Use Groq LLM to re-rank the top N keyword-scored jobs.
    Returns the same list with 'score' and 'llm_reason' fields updated.
    Falls back gracefully if GROQ_API_KEY is missing or API fails.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        print("GROQ_API_KEY not set — skipping LLM re-ranking.")
        return jobs

    try:
        from groq import Groq
    except ImportError:
        print("groq package not available — skipping LLM re-ranking.")
        return jobs

    candidates = jobs[:top_n]
    rest = jobs[top_n:]

    # Build a compact job list for the prompt
    job_list_text = ""
    for i, j in enumerate(candidates, 1):
        job_list_text += (
            f"\n[{i}] Title: {j.get('title', '')[:80]}\n"
            f"    Company: {j.get('company', '')[:40]}\n"
            f"    Location: {j.get('location', '')[:40]}\n"
            f"    Description: {j.get('description', '')[:300]}\n"
        )

    prompt = f"""You are a strict job relevance scorer. Rate each job for this candidate:
- M.Tech AI student, graduating March 2026, based in Noida (Delhi NCR)
- Skills: Python, LangChain, RAG pipelines, FastAPI, ChromaDB, agentic AI, web scraping, automation
- Preference: AI/ML roles, onsite or hybrid in Delhi NCR; open to remote
- Acceptable: intern, fresher, junior, entry-level, 0-2 years experience

SCORING RULES — follow strictly:
- Score 0: Role title has nothing to do with tech/engineering/AI/ML/data/software (e.g., "Marketing Student", "Sales Rep", "Account Manager", "HR Coordinator")
- Score 0: Requires 5+ years experience, senior/lead/principal level, or clearance/visa restrictions
- Score 0: Non-English job postings
- Score 1-25: Tech role but wrong specialization or poor location match
- Score 26-50: Relevant tech role, some skill overlap, acceptable location
- Score 51-75: Strong match — AI/ML/Python role, good skill overlap
- Score 76-100: Near-perfect — AI/ML role in Delhi NCR, exact stack match, entry-level friendly

For each job, provide:
1. A relevance score from 0-100
2. A one-line reason (max 10 words)

Jobs to score:
{job_list_text}

Respond ONLY in this JSON format:
{{"rankings": [{{"id": 1, "score": 85, "reason": "RAG + LangChain match, NCR location"}}, ...]}}"""

    try:
        client = Groq(api_key=groq_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        ranking_map = {r["id"]: r for r in data.get("rankings", [])}
        for i, job in enumerate(candidates, 1):
            if i in ranking_map:
                r = ranking_map[i]
                job["score"] = r["score"]
                job["llm_reason"] = r.get("reason", "")

        candidates.sort(key=lambda j: j.get("score", 0), reverse=True)
        print(f"LLM re-ranking complete for {len(candidates)} jobs.")

    except Exception as e:
        print(f"LLM re-ranking failed: {e} — using keyword scores.")

    return candidates + rest


def main():
    print("=== Hourly Job Search Automation ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize database
    init_db()

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

    # Score and filter new jobs
    for job in new_jobs:
        job["score"] = score_job(job)
    new_jobs = [j for j in new_jobs if j["score"] > -100]
    new_jobs = [j for j in new_jobs if j.get("score", 0) >= 20]
    new_jobs = [j for j in new_jobs if j.get("company", "").strip().lower() not in BLOCKED_COMPANIES]
    new_jobs.sort(key=lambda j: j["score"], reverse=True)

    # LLM re-ranking for top candidates
    if new_jobs:
        print("\nRunning LLM re-ranking on top candidates...")
        new_jobs = llm_rerank_jobs(new_jobs, top_n=20)

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
            )
        except Exception:
            pass

    # Only send email if there are new jobs
    if not new_jobs:
        print("\nNo new jobs found this run. Skipping email.")
        print("Done!")
        return

    # Build email content with only new jobs
    print("\nBuilding email content...")
    alert_number = get_alert_number()
    md_content = build_email_content(new_jobs, sources_status, sources_errors)

    # Send email
    print(f"Sending Job Alert #{alert_number}...")
    email_sent = send_email(md_content, alert_number=alert_number)

    # Save to Supabase so frontend can display it
    print("Saving email log to database...")
    save_email_log(
        subject=f"Job Alert #{alert_number}",
        markdown_content=md_content,
        html_content="",
        jobs_count=len(new_jobs),
        sources_summary=sources_status,
        email_sent=email_sent,
    )

    print(f"\nDone! Job Alert #{alert_number} sent: {email_sent}. {len(new_jobs)} new jobs.")


if __name__ == "__main__":
    main()

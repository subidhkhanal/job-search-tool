"""
Nightly Job Search Automation
Runs all scrapers, builds TONIGHT.md battle plan, and sends email.
Designed to run both locally and in GitHub Actions.
"""

import os
from datetime import datetime
from tracker import init_db, get_follow_ups_due, get_stats, get_scraped_jobs
from scraper import (
    run_all_scrapers,
    scrape_wellfound_search_hint,
    scrape_linkedin_search_urls,
)
from jd_analyzer import quick_analyze


def score_job(job):
    """Score a job listing based on profile match. Higher = better fit."""
    text = (
        job.get("title", "") + " " + job.get("description", "")
    ).lower()
    score = 0

    # High-value keywords (general relevance)
    high_value = [
        "gen ai", "generative ai", "llm", "large language model",
        "rag", "retrieval augmented", "ai agent", "agentic",
        "langchain", "vector database", "nlp",
    ]
    score += sum(5 for kw in high_value if kw in text)

    # Exact stack match (these are on the resume — highest signal)
    stack_match = [
        "langchain", "chromadb", "fastapi", "rag",
        "openai api", "agentic", "cohere", "ragas",
        "hybrid search", "next.js", "automation pipeline",
    ]
    score += sum(12 for kw in stack_match if kw in text)

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

    # India-friendly bonus
    location = job.get("location", "").lower()
    if any(
        kw in location
        for kw in ["india", "remote", "noida", "delhi", "bangalore", "bengaluru"]
    ):
        score += 5

    # Fresher/intern friendly bonus
    if any(kw in text for kw in ["intern", "fresher", "entry level", "0-1 year", "junior"]):
        score += 5

    return score


def build_battle_plan(jobs, sources_status):
    """Build the TONIGHT.md battle plan markdown."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    total_found = len(jobs)

    # Score and sort all jobs
    for job in jobs:
        job["score"] = score_job(job)
    jobs.sort(key=lambda j: j["score"], reverse=True)

    lines = []
    lines.append(f"# Tonight's Battle Plan — {today}")
    lines.append("")
    lines.append(f"**{total_found} new jobs found tonight.**")
    lines.append("")

    # Source breakdown
    lines.append("## Scrape Summary")
    lines.append("")
    lines.append("| Source | Jobs Found |")
    lines.append("|--------|-----------|")
    for source, count in sources_status.items():
        lines.append(f"| {source} | {count} |")
    lines.append("")

    # Jobs sorted by score with tier indicators
    if jobs:
        lines.append("## New Jobs (sorted by match score)")
        lines.append("")

        for idx, j in enumerate(jobs, 1):
            title = j.get("title", "Untitled")
            company = j.get("company", "Unknown")
            location = j.get("location", "")
            url = j.get("url", "")
            desc = j.get("description", "")
            source = j.get("source", "")
            score = j.get("score", 0)

            # Tier emoji based on score
            if score >= 40:
                tier = "\U0001f525"
            elif score >= 20:
                tier = "\U0001f4cc"
            else:
                tier = "\U0001f4cb"

            # JD Analyzer verdict
            verdict = quick_analyze(title, desc)

            lines.append(f"### {tier} {idx}. {company} — {title} [{verdict}]")
            lines.append(f"- Score: {score}")
            if location:
                lines.append(f"- Location: {location}")
            lines.append(f"- Source: {source}")
            if url:
                lines.append(f"- [Apply here]({url})")
            if desc:
                lines.append(f"- {desc[:150]}...")
            lines.append("")
    else:
        lines.append("## No New Jobs Tonight")
        lines.append("")
        lines.append("Scrapers came back empty. Check manual links below.")
        lines.append("")

    # Manual search links
    lines.append("## Manual Search Links")
    lines.append("")
    lines.append("### Wellfound")
    for url in scrape_wellfound_search_hint():
        lines.append(f"- [{url}]({url})")
    lines.append("")

    lines.append("### LinkedIn")
    for item in scrape_linkedin_search_urls():
        lines.append(f"- [{item['query']}]({item['url']})")
    lines.append("")

    # Follow-up reminders (only meaningful locally where tracker DB exists)
    try:
        follow_ups = get_follow_ups_due()
        if not follow_ups.empty:
            lines.append("## Follow-Ups Due")
            lines.append("")
            for _, row in follow_ups.iterrows():
                lines.append(
                    f"- [ ] **{row['company']}** — {row['role']} "
                    f"(applied {row['date_applied']})"
                )
            lines.append("")
    except Exception:
        pass

    # Stats (only meaningful locally)
    try:
        stats = get_stats()
        if stats.get("total", 0) > 0:
            lines.append("## Your Stats")
            lines.append("")
            lines.append(f"- Total applications: {stats['total']}")
            lines.append(f"- Awaiting response: {stats['applied']}")
            lines.append(f"- Interviews: {stats['interviews']}")
            lines.append(f"- Offers: {stats['offers']}")
            lines.append(f"- Rejected: {stats['rejected']}")
            lines.append("")
    except Exception:
        pass

    # Action checklist
    lines.append("## Tonight's Checklist")
    lines.append("")
    lines.append("- [ ] Review new jobs above")
    lines.append("- [ ] Apply to top 3-5 matches")
    lines.append("- [ ] Send follow-ups to overdue applications")
    lines.append("- [ ] Log applications in tracker")
    lines.append("- [ ] Check Wellfound & LinkedIn manually")
    lines.append("")
    lines.append("---")
    lines.append("*Generated automatically by Job Search Tool*")

    return "\n".join(lines)


def main():
    print("=== Nightly Job Search Automation ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize database (creates tables if they don't exist)
    init_db()

    # Run all automated scrapers
    print("Running scrapers...")
    jobs, sources_status = run_all_scrapers()
    print(f"\nTotal jobs found: {len(jobs)}")
    for source, count in sources_status.items():
        print(f"  {source}: {count}")

    # Build battle plan
    print("\nBuilding TONIGHT.md...")
    battle_plan = build_battle_plan(jobs, sources_status)

    with open("TONIGHT.md", "w", encoding="utf-8") as f:
        f.write(battle_plan)
    print("TONIGHT.md written.")

    # Send email
    print("\nSending email...")
    try:
        from send_email import send_battle_plan_email

        send_battle_plan_email()
    except Exception as e:
        print(f"Email sending skipped: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()

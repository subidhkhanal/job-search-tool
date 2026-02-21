"""
Nightly Job Search Automation
Runs all scrapers, checks watchlist, builds TONIGHT.md battle plan, and sends email.
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
from watchlist import check_all_watchlist


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

    return score


def build_battle_plan(jobs, sources_status, watchlist_results=None):
    """Build the TONIGHT.md battle plan markdown with phased structure."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    now = datetime.now().strftime("%I:%M %p")
    total_found = len(jobs)

    # Score and sort all jobs, filter out non-English
    for job in jobs:
        job["score"] = score_job(job)
    jobs = [j for j in jobs if j["score"] > -100]
    jobs.sort(key=lambda j: j["score"], reverse=True)

    # Get stats and follow-ups
    stats = {}
    try:
        stats = get_stats()
    except Exception:
        pass

    follow_ups = []
    try:
        fu = get_follow_ups_due()
        if not fu.empty:
            follow_ups = fu.to_dict("records")
    except Exception:
        pass

    lines = []
    lines.append(f"# \U0001f3af Tonight's Battle Plan \u2014 {today}")
    lines.append(f"*Generated at {now}. You start at 10 PM. Go.*")
    lines.append("")

    # === Stats ===
    if stats.get("total", 0) > 0:
        lines.append("## \U0001f4ca Your Numbers")
        lines.append(f"- Total applications: {stats.get('total', 0)}")
        lines.append(f"- Awaiting response: {stats.get('applied', 0)}")
        lines.append(f"- Interviews: {stats.get('interviews', 0)} | Offers: {stats.get('offers', 0)}")
        lines.append("")

    # === Scrape Summary ===
    lines.append("## \U0001f4e1 Scrape Summary")
    lines.append("")
    lines.append("| Source | Jobs Found |")
    lines.append("|--------|-----------|")
    for source, count in sources_status.items():
        lines.append(f"| {source} | {count} |")
    if watchlist_results:
        wl_total = sum(len(v) for v in watchlist_results.values())
        lines.append(f"| Watchlist | {wl_total} new |")
    high_relevance = sum(1 for j in jobs if j.get("score", 0) >= 40)
    lines.append(f"\n**Total: {total_found}** | **High relevance: {high_relevance}**")
    lines.append("")

    # === Phase 1: Follow-ups ===
    lines.append("## \u23f0 Phase 1: Follow-ups (10:00 \u2013 10:15 PM)")
    lines.append("")
    if follow_ups:
        for fu in follow_ups:
            lines.append(
                f"- [ ] Follow up: **{fu['company']}** \u2014 {fu['role']} "
                f"({fu.get('platform', '')})"
            )
    else:
        lines.append("No follow-ups due tonight. \u2705")
    lines.append("")

    # === Phase 1.5: Watchlist Alerts ===
    if watchlist_results:
        lines.append("## \U0001f3e2 Phase 1.5: Watchlist Alerts (New Listings at Target Companies)")
        lines.append("")
        for company, new_jobs in watchlist_results.items():
            for wj in new_jobs:
                lines.append(f"### \U0001f195 {company} posted: \"{wj['title']}\"")
                lines.append(f"- [Apply here]({wj['url']})")
                lines.append("- [ ] Apply (priority \u2014 target company)")
                lines.append("")

    # === Phase 2: Top Scraped Jobs ===
    lines.append("## \U0001f50d Phase 2: Apply to Top Scraped Jobs (10:15 \u2013 10:50 PM)")
    lines.append("")

    if jobs:
        for idx, j in enumerate(jobs[:15], 1):
            title = j.get("title", "Untitled")
            company = j.get("company", "Unknown")
            location = j.get("location", "")
            url = j.get("url", "")
            desc = j.get("description", "")
            source = j.get("source", "")
            score = j.get("score", 0)

            if score >= 40:
                tier = "\U0001f525"
            elif score >= 20:
                tier = "\U0001f4cc"
            else:
                tier = "\U0001f4cb"

            verdict = quick_analyze(title, desc)

            lines.append(f"### {tier} {idx}. {company} \u2014 {title} [{verdict}]")
            lines.append(f"- Source: {source} | Score: {score}")
            if location:
                lines.append(f"- Location: {location}")
            if url:
                lines.append(f"- [Apply here]({url})")
            if desc:
                lines.append(f"- {desc[:150]}...")
            lines.append("- [ ] Apply")
            lines.append("- [ ] Log in tracker")
            lines.append("")
    else:
        lines.append("Scrapers came back empty. Check manual links below.")
        lines.append("")

    # === Phase 3: Manual Platform Applications ===
    lines.append("## \U0001f4bc Phase 3: Manual Platform Applications (10:50 \u2013 11:20 PM)")
    lines.append("")
    lines.append("### Wellfound (5-8 apps)")
    for url in scrape_wellfound_search_hint():
        lines.append(f"- [ ] [{url}]({url})")
    lines.append("")
    lines.append("### LinkedIn Easy Apply (10-15 apps)")
    for item in scrape_linkedin_search_urls():
        lines.append(f"- [ ] [{item['query']}]({item['url']})")
    lines.append("")

    # === Phase 4: Cold DMs ===
    lines.append("## \U0001f3af Phase 4: Cold DMs (11:20 \u2013 11:45 PM)")
    lines.append("")
    if jobs:
        top3 = [j for j in jobs[:5] if j.get("score", 0) >= 30][:3]
        if top3:
            for j in top3:
                lines.append(f"### Target: {j['company']} \u2014 {j['title']}")
                lines.append(f"- Find the hiring manager on LinkedIn")
                lines.append(f"- Use Message Generator to draft a cold DM")
                lines.append("- [ ] Personalize and send")
                lines.append("")
        else:
            lines.append("No strong-match targets for DMs tonight. Focus on volume.")
            lines.append("")
    else:
        lines.append("No targets for DMs tonight.")
        lines.append("")

    # === Phase 5: Log & Review ===
    lines.append("## \U0001f4cb Phase 5: Log & Review (11:45 PM \u2013 12:00 AM)")
    lines.append("")
    lines.append("- [ ] Log tonight's applications in tracker")
    lines.append("- [ ] Total applications tonight: ___ ")
    lines.append("- [ ] Review tomorrow's follow-up schedule")
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

    # Check watchlist companies
    print("\nChecking watchlist companies...")
    watchlist_results = {}
    try:
        watchlist_results = check_all_watchlist()
        wl_total = sum(len(v) for v in watchlist_results.values())
        print(f"Watchlist: {wl_total} new listings from {len(watchlist_results)} companies")
    except Exception as e:
        print(f"Watchlist check skipped: {e}")

    # Build battle plan
    print("\nBuilding TONIGHT.md...")
    battle_plan = build_battle_plan(jobs, sources_status, watchlist_results)

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

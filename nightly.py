"""
Nightly Job Search Automation
Runs all scrapers, checks watchlist, builds TONIGHT.md battle plan, and sends email.
Designed to run both locally and in GitHub Actions.
"""

import os
import json
from datetime import datetime
from tracker import init_db, get_follow_ups_due, get_stats, get_scraped_jobs
from scraper import (
    run_all_scrapers,
    scrape_wellfound_search_hint,
    scrape_linkedin_search_urls,
)
from jd_analyzer import quick_analyze
from watchlist import check_all_watchlist
from url_store import load_seen, save_seen, is_new, mark_seen


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


def llm_rerank_jobs(jobs, top_n=20):
    """
    Use Groq LLM to re-rank the top N keyword-scored jobs.
    Returns the same list with 'score' and 'llm_reason' fields updated.
    Falls back gracefully if GROQ_API_KEY is missing or API fails.
    """
    groq_key = os.environ.get("GROQ_API_KEY")
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

    prompt = f"""You are a job relevance scorer. Rate each job listing for a candidate with this profile:
- M.Tech AI student, graduating March 2026, based in Noida (Delhi NCR)
- Skills: Python, LangChain, RAG pipelines, FastAPI, ChromaDB, agentic AI, web scraping, automation
- Preference: AI/ML roles, onsite or hybrid in Delhi NCR; open to remote
- Acceptable: intern, fresher, junior, entry-level, 0-2 years experience
- Should be filtered out: non-English postings, unpaid, "5+ years", "senior", US/EU-only

For each job, provide:
1. A relevance score from 1-100 (100 = perfect fit)
2. A one-line reason (max 10 words)

IMPORTANT: Understand context. "No Python experience required" should score LOW for Python.

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


def _render_job_table(jobs_list, max_rows, include_verdict=True):
    """Render a markdown table of jobs. Returns list of lines."""
    lines = []
    if include_verdict:
        lines.append("| # | Job Title | Score | Verdict | LLM Take | Location | Link |")
        lines.append("|---|-----------|-------|---------|----------|----------|------|")
    else:
        lines.append("| # | Job Title | Score | Location | Link |")
        lines.append("|---|-----------|-------|----------|------|")

    for idx, j in enumerate(jobs_list[:max_rows], 1):
        title = j.get("title", "Untitled").replace("|", "/").strip()[:50]
        company = j.get("company", "Unknown").replace("|", "/").strip()[:20]
        location = j.get("location", "").replace("|", "/").strip()[:20]
        url = j.get("url", "")
        score = j.get("score", 0)

        if score >= 40:
            tier = "\U0001f525"
        elif score >= 20:
            tier = "\U0001f4cc"
        else:
            tier = "\U0001f4cb"

        job_title = f"{company} \u2014 {title}"
        link = f"[Apply]({url})" if url else "\u2014"

        if include_verdict:
            # JD verdict
            try:
                verdict = quick_analyze(j.get("title", ""), j.get("description", ""))
                parts = verdict.split("|")
                verdict_short = f"{parts[0].strip()} \u00b7 {parts[2].strip()}" if len(parts) >= 3 else verdict
            except Exception:
                verdict_short = "\u2014"
            verdict_short = verdict_short.replace("|", "\u00b7")

            # LLM reason
            llm_reason = j.get("llm_reason", "").replace("|", "\u00b7")[:40] or "\u2014"

            lines.append(
                f"| {tier} {idx} | {job_title} | {score} | {verdict_short} | {llm_reason} | {location} | {link} |"
            )
        else:
            lines.append(f"| {tier} {idx} | {job_title} | {score} | {location} | {link} |")

    return lines


def build_battle_plan(jobs, sources_status, watchlist_results=None,
                      sources_errors=None, seen=None):
    """Build the TONIGHT.md battle plan markdown with phased structure."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    now = datetime.now().strftime("%I:%M %p")
    total_found = len(jobs)
    sources_errors = sources_errors or {}

    # Score and sort all jobs, filter out non-English
    for job in jobs:
        job["score"] = score_job(job)
    jobs = [j for j in jobs if j["score"] > -100]
    jobs.sort(key=lambda j: j["score"], reverse=True)

    # Split into new and seen
    new_jobs = [j for j in jobs if j.get("is_new", True)]
    seen_jobs = [j for j in jobs if not j.get("is_new", True)]

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

    # === Scrape Summary with health status ===
    lines.append("## \U0001f4e1 Scrape Summary")
    lines.append("")
    lines.append("| Source | Jobs Found | Status |")
    lines.append("|--------|-----------|--------|")
    for source, count in sources_status.items():
        if source in sources_errors:
            status = "\u274c FAILED"
        elif count == 0:
            status = "\u26a0\ufe0f EMPTY"
        else:
            status = "\u2705 OK"
        lines.append(f"| {source} | {count} | {status} |")
    if watchlist_results:
        wl_total = sum(len(v) for v in watchlist_results.values())
        lines.append(f"| Watchlist | {wl_total} new | \u2705 OK |")

    high_relevance = sum(1 for j in jobs if j.get("score", 0) >= 40)
    lines.append(f"\n**Total: {total_found}** | **New tonight: {len(new_jobs)}** | **High relevance: {high_relevance}**")

    if sources_errors:
        lines.append("")
        lines.append("**Scraper failures:**")
        for source, err in sources_errors.items():
            lines.append(f"- {source}: `{err[:80]}`")
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
        for company, wl_jobs in watchlist_results.items():
            for wj in wl_jobs:
                lines.append(f"### \U0001f195 {company} posted: \"{wj['title']}\"")
                lines.append(f"- [Apply here]({wj['url']})")
                lines.append("- [ ] Apply (priority \u2014 target company)")
                lines.append("")

    # === Phase 2: Top NEW Scraped Jobs ===
    lines.append("## \U0001f50d Phase 2: Apply to Top NEW Jobs (10:15 \u2013 10:50 PM)")
    lines.append("")

    if new_jobs:
        lines.extend(_render_job_table(new_jobs, max_rows=15, include_verdict=True))
        lines.append("")
    else:
        lines.append("No new jobs found tonight. Check 'Still Open' below or manual links.")
        lines.append("")

    # === Still Open (previously seen, high score) ===
    still_open = [j for j in seen_jobs if j.get("score", 0) >= 30]
    if still_open:
        lines.append("### Still Open (Seen Before, Score \u2265 30)")
        lines.append("")
        lines.extend(_render_job_table(still_open, max_rows=10, include_verdict=False))
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
    all_jobs = new_jobs + seen_jobs
    if all_jobs:
        top3 = [j for j in all_jobs[:5] if j.get("score", 0) >= 30][:3]
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
    jobs, sources_status, sources_errors = run_all_scrapers()
    print(f"\nTotal jobs found: {len(jobs)}")
    for source, count in sources_status.items():
        print(f"  {source}: {count}")
    if sources_errors:
        print(f"\nFailed scrapers: {', '.join(sources_errors.keys())}")

    # Check watchlist companies
    print("\nChecking watchlist companies...")
    watchlist_results = {}
    try:
        watchlist_results = check_all_watchlist()
        wl_total = sum(len(v) for v in watchlist_results.values())
        print(f"Watchlist: {wl_total} new listings from {len(watchlist_results)} companies")
    except Exception as e:
        print(f"Watchlist check skipped: {e}")

    # Load seen URLs for freshness filtering
    print("\nLoading seen URL history...")
    seen = load_seen()
    print(f"  {len(seen)} previously seen URLs loaded")

    # Tag each job as new or seen
    for job in jobs:
        url = job.get("url", "")
        job["is_new"] = is_new(url, seen)
        mark_seen(url, seen)

    new_count = sum(1 for j in jobs if j.get("is_new"))
    print(f"  {new_count} new jobs, {len(jobs) - new_count} previously seen")

    # LLM re-ranking for top candidates
    print("\nRunning LLM re-ranking on top candidates...")
    jobs = llm_rerank_jobs(jobs, top_n=20)

    # Build battle plan
    print("\nBuilding TONIGHT.md...")
    battle_plan = build_battle_plan(
        jobs, sources_status, watchlist_results,
        sources_errors=sources_errors, seen=seen,
    )

    with open("TONIGHT.md", "w", encoding="utf-8") as f:
        f.write(battle_plan)
    print("TONIGHT.md written.")

    # Persist seen URLs for next run
    save_seen(seen)
    print(f"Saved {len(seen)} seen URLs.")

    print("\nDone! View the plan on the Streamlit page or check TONIGHT.md.")


if __name__ == "__main__":
    main()

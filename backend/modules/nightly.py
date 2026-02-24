"""
Nightly Job Search Automation
Runs all scrapers, builds TONIGHT.md battle plan, and sends email.
Designed to run both locally and in GitHub Actions.
"""

import os
import json
import random
from datetime import datetime
from tracker import (
    init_db, get_follow_ups_due, get_stats, get_scraped_jobs,
    get_referral_follow_ups_due, get_referrals_by_company, get_referral_stats,
    get_active_demos,
)
from scraper import (
    run_all_scrapers,
    scrape_wellfound_search_hint,
    scrape_linkedin_search_urls,
    generate_career_url,
)
from jd_analyzer import quick_ats

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


def _render_job_table(jobs_list, max_rows):
    """Render a markdown table of jobs. Returns list of lines."""
    lines = []
    lines.append("| Relevance | Mode | Job Title | Score | ATS | LLM Take | Link | Career Page |")
    lines.append("|-----------|------|-----------|-------|-----|----------|------|-------------|")

    for idx, j in enumerate(jobs_list[:max_rows], 1):
        title = j.get("title", "Untitled").replace("|", "/").strip()[:60]
        url = j.get("url", "")
        score = j.get("score", 0)
        relevance = _get_relevance_label(score)

        # Detect work mode
        text = (j.get("location", "") + " " + j.get("description", "") + " " + j.get("title", "")).lower()
        if any(kw in text for kw in ["onsite", "on-site", "on site", "in-office", "in office", "work from office", "wfo"]):
            work_mode = "\U0001f3e2 Onsite"
        elif "hybrid" in text:
            work_mode = "\U0001f500 Hybrid"
        elif "remote" in text:
            work_mode = "\U0001f3e0 Remote"
        else:
            work_mode = "\u2014"

        # ATS score
        desc = j.get("description", "")
        ats_score = quick_ats(desc) if desc else 0
        ats_display = f"{ats_score}%"
        if len(desc.strip()) < 600:
            ats_display += "~"

        link = f"[Apply]({url})" if url else "\u2014"
        llm_reason = j.get("llm_reason", "").replace("|", "\u00b7")[:40] or "\u2014"
        career_url = generate_career_url(j.get("company", ""), j.get("title", ""))
        career_link = f"[Career]({career_url})"

        lines.append(
            f"| {relevance} | {work_mode} | {title} | {score} | {ats_display} | {llm_reason} | {link} | {career_link} |"
        )

    return lines


def build_battle_plan(jobs, sources_status, sources_errors=None):
    """Build the TONIGHT.md battle plan markdown with phased structure."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    now = datetime.now().strftime("%I:%M %p")
    total_found = len(jobs)
    sources_errors = sources_errors or {}

    # Score and sort all jobs, filter out non-English and low-relevance
    for job in jobs:
        job["score"] = score_job(job)
    jobs = [j for j in jobs if j["score"] > -100]
    jobs = [j for j in jobs if j.get("score", 0) >= 20]
    jobs = [j for j in jobs if j.get("company", "").strip().lower() not in BLOCKED_COMPANIES]
    jobs.sort(key=lambda j: j["score"], reverse=True)

    # Get stats, follow-ups, referrals, demos
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

    referral_follow_ups = []
    try:
        rfu = get_referral_follow_ups_due()
        if not rfu.empty:
            referral_follow_ups = rfu.to_dict("records")
    except Exception:
        pass

    ref_stats = {}
    try:
        ref_stats = get_referral_stats()
    except Exception:
        pass

    active_demos = []
    try:
        demos_df = get_active_demos()
        if not demos_df.empty:
            active_demos = demos_df.to_dict("records")
    except Exception:
        pass

    lines = []
    lines.append(f"# \U0001f3af Tonight's Battle Plan \u2014 {today}")
    lines.append(f"*Generated at {now}. You start at 10 PM. Go.*")
    lines.append("")

    # === Stats ===
    lines.append("## \U0001f4ca Your Numbers")
    lines.append(f"- Total applications: {stats.get('total', 0)} | Referrals in pipeline: {ref_stats.get('total', 0)}")
    lines.append(f"- Awaiting response: {stats.get('applied', 0)}")
    lines.append(f"- Interviews: {stats.get('interviews', 0)} | Offers: {stats.get('offers', 0)}")
    if active_demos:
        lines.append(f"- Demos in progress: {len([d for d in active_demos if d.get('status') in ('Idea', 'Building')])}")
    lines.append("")

    # === Phase 0: Referral Outreach ===
    lines.append("## \U0001f91d Phase 0: Referral Outreach (9:55 \u2013 10:10 PM)")
    lines.append("*One referral = 20 cold applications. Do this first.*")
    lines.append("")
    if referral_follow_ups:
        for rfu in referral_follow_ups:
            lines.append(
                f"- [ ] Follow up: **{rfu['contact_name']}** ({rfu.get('contact_role', '')}) at "
                f"{rfu['company']} \u2014 Status: {rfu['status']} \u2014 "
                f"Last contacted: {rfu.get('last_contacted', 'N/A')}"
            )
    else:
        lines.append("No referral follow-ups due tonight. \u2705")

    # Cross-reference top jobs with referrals
    if jobs:
        lines.append("")
        lines.append("**\U0001f4a1 Contact cross-reference:**")
        for j in jobs[:10]:
            company = j.get("company", "")
            if company:
                try:
                    refs = get_referrals_by_company(company)
                    if not refs.empty:
                        for _, ref in refs.iterrows():
                            lines.append(
                                f"- \U0001f525 **{company}** has a job AND you know "
                                f"**{ref['contact_name']}** ({ref.get('contact_role', '')}) \u2014 "
                                f"Send referral request!"
                            )
                except Exception:
                    pass
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

    high_relevance = sum(1 for j in jobs if j.get("score", 0) >= 40)
    lines.append(f"\n**Total: {total_found}** | **High relevance: {high_relevance}**")

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

    # === Phase 2: Top Jobs ===
    lines.append("## \U0001f50d Phase 2: Apply to Top Jobs (10:15 \u2013 10:50 PM)")
    lines.append("")

    if jobs:
        lines.extend(_render_job_table(jobs, max_rows=20))
        lines.append("")
    else:
        lines.append("No relevant jobs found tonight. Try manual links below.")
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

    # === Phase 4: Direct Outreach ===
    lines.append("## \U0001f3af Phase 4: Direct Outreach (11:20 \u2013 11:45 PM)")
    lines.append("")

    # Deployed demos ready to send
    deployed_demos = [d for d in active_demos if d.get("status") == "Deployed" and not d.get("result")]
    if deployed_demos:
        lines.append("### \U0001f6e0\ufe0f Demo Ready to Send:")
        for d in deployed_demos:
            lines.append(f"**{d['company']}** \u2014 Built: {d['demo_idea']}")
            if d.get("demo_url"):
                lines.append(f"Demo: {d['demo_url']}")
            lines.append("- [ ] Personalize outreach and send to decision maker")
            lines.append("")

    # Cold DMs
    if jobs:
        lines.append("### Cold DMs:")
        top3 = [j for j in jobs[:5] if j.get("score", 0) >= 30][:3]
        if top3:
            for j in top3:
                lines.append(f"**{j['company']}** \u2014 {j['title']}")
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
    lines.append("- [ ] Update referral statuses")
    lines.append("- [ ] Total applications tonight: ___ ")
    lines.append("- [ ] Review tomorrow's follow-up schedule")
    lines.append("")

    # === LinkedIn Reminder (Mon/Wed/Fri only) ===
    if datetime.now().weekday() in [0, 2, 4]:  # Mon, Wed, Fri
        lines.append("## \U0001f4e3 LinkedIn Post Reminder (tomorrow morning \u2014 15 min)")
        lines.append("")
        post_ideas = [
            "Share a build update on your Agentic RAG project",
            "Explain how hybrid search (dense + BM25) works with a simple diagram",
            "Write about a bug you fixed this week and what you learned",
            "Compare LangChain vs LlamaIndex for RAG \u2014 share your test results",
            "Share how your PathToPR automation reduced manual work from hours to minutes",
            "Explain reciprocal rank fusion in simple terms",
            "Share your job search tool \u2014 'I built this to automate my job search'",
            "Write about how you chose ChromaDB over Pinecone and why",
            "Explain RAGAS evaluation framework to someone who's never heard of it",
            "Share 3 things you learned about the Gen AI job market this week",
            "Write about a mistake you made while building a RAG pipeline",
            "Compare different embedding models \u2014 which works best for your use case",
            "Share how you built a query routing system with LangChain",
            "Write about the difference between semantic search and keyword search",
            "Post about why you chose FastAPI over Flask for your backend",
            "Share a 'day in my life' as an M.Tech AI student building projects",
            "Explain how you use the OpenAI API in your PathToPR automation",
            "Write about why production AI is different from tutorial AI",
            "Post about a paper you read this week and your key takeaway",
            "Share how you evaluate RAG pipeline quality with metrics",
        ]
        selected = random.sample(post_ideas, min(5, len(post_ideas)))
        lines.append("Pick ONE:")
        for idea in selected:
            lines.append(f"- \U0001f4dd {idea}")
        lines.append("")
        lines.append("**Format:** Hook first line \u2192 line breaks every 2-3 sentences \u2192 end with a question")
        lines.append("**Tags:** #GenAI #LangChain #RAG #AIJobs #MTechAI #BuildInPublic")
        lines.append("**Best time:** 8-9 AM IST (day after reminder)")
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

    # LLM re-ranking for top candidates
    print("\nRunning LLM re-ranking on top candidates...")
    jobs = llm_rerank_jobs(jobs, top_n=20)

    # Build battle plan
    print("\nBuilding TONIGHT.md...")
    battle_plan = build_battle_plan(
        jobs, sources_status,
        sources_errors=sources_errors,
    )

    with open("TONIGHT.md", "w", encoding="utf-8") as f:
        f.write(battle_plan)
    print("TONIGHT.md written.")

    print("\nDone! View the plan on the Streamlit page or check TONIGHT.md.")


if __name__ == "__main__":
    main()

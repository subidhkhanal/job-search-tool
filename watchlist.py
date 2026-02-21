"""
Watchlist — monitor company career pages for new AI/ML listings.
Supports Lever, Greenhouse, Ashby, and Workable JSON APIs.
Falls back to HTML scraping for custom career pages.
"""

import requests
from bs4 import BeautifulSoup
from tracker import (
    get_watchlist, save_watchlist_job, update_watchlist_checked,
    add_to_watchlist,
)

# ATS platform API URL templates
PLATFORMS = {
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "workable": "https://apply.workable.com/api/v3/accounts/{slug}/jobs",
    "custom": None,
}

# AI/ML keywords to filter relevant listings
RELEVANT_KEYWORDS = [
    "ai", "ml", "machine learning", "deep learning", "data scien",
    "nlp", "natural language", "llm", "gen ai", "generative",
    "rag", "langchain", "python", "backend", "software engineer",
    "software developer", "full stack", "automation",
]

STARTER_COMPANIES = [
    {"name": "Postman", "platform": "greenhouse", "slug": "postman"},
    {"name": "Razorpay", "platform": "lever", "slug": "razorpay"},
    {"name": "Freshworks", "platform": "greenhouse", "slug": "freshworks"},
    {"name": "Hasura", "platform": "greenhouse", "slug": "hasura"},
    {"name": "Meesho", "platform": "lever", "slug": "meesho"},
    {"name": "Zerodha", "platform": "lever", "slug": "zerodha"},
    {"name": "Cred", "platform": "lever", "slug": "cred"},
    {"name": "PhonePe", "platform": "greenhouse", "slug": "phonepe"},
    {"name": "Groww", "platform": "lever", "slug": "groww"},
    {"name": "Ola", "platform": "lever", "slug": "olacabs"},
]


def _is_relevant(title):
    """Check if a job title contains AI/ML relevant keywords."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in RELEVANT_KEYWORDS)


def _fetch_lever(slug):
    """Fetch jobs from Lever API."""
    url = PLATFORMS["lever"].format(slug=slug)
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return []

    jobs = []
    for posting in resp.json():
        title = posting.get("text", "")
        link = posting.get("hostedUrl", "")
        if _is_relevant(title) and link:
            jobs.append({"title": title, "url": link})
    return jobs


def _fetch_greenhouse(slug):
    """Fetch jobs from Greenhouse API."""
    url = PLATFORMS["greenhouse"].format(slug=slug)
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return []

    jobs = []
    for job in resp.json().get("jobs", []):
        title = job.get("title", "")
        link = job.get("absolute_url", "")
        if _is_relevant(title) and link:
            jobs.append({"title": title, "url": link})
    return jobs


def _fetch_ashby(slug):
    """Fetch jobs from Ashby API."""
    url = PLATFORMS["ashby"].format(slug=slug)
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return []

    jobs = []
    for job in resp.json().get("jobs", []):
        title = job.get("title", "")
        job_id = job.get("id", "")
        link = f"https://jobs.ashbyhq.com/{slug}/{job_id}" if job_id else ""
        if _is_relevant(title) and link:
            jobs.append({"title": title, "url": link})
    return jobs


def _fetch_workable(slug):
    """Fetch jobs from Workable API."""
    url = PLATFORMS["workable"].format(slug=slug)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return []

        jobs = []
        for job in resp.json().get("results", []):
            title = job.get("title", "")
            shortcode = job.get("shortcode", "")
            link = f"https://apply.workable.com/{slug}/j/{shortcode}/" if shortcode else ""
            if _is_relevant(title) and link:
                jobs.append({"title": title, "url": link})
        return jobs
    except Exception:
        return []


def _fetch_custom(career_url):
    """Scrape a custom career page for AI/ML keywords in links."""
    try:
        resp = requests.get(career_url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"
        })
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]
            if _is_relevant(text) and len(text) > 5:
                # Make relative URLs absolute
                if href.startswith("/"):
                    from urllib.parse import urljoin
                    href = urljoin(career_url, href)
                if href.startswith("http"):
                    jobs.append({"title": text[:150], "url": href})

        return jobs
    except Exception:
        return []


FETCHERS = {
    "lever": _fetch_lever,
    "greenhouse": _fetch_greenhouse,
    "ashby": _fetch_ashby,
    "workable": _fetch_workable,
}


def check_company(company_row):
    """Check a single watchlist company for new AI/ML job listings.
    Returns list of new jobs found."""
    platform = company_row["platform_type"]
    slug = company_row.get("company_slug", "")
    career_url = company_row["career_url"]
    watchlist_id = company_row["id"]

    if platform in FETCHERS and slug:
        listings = FETCHERS[platform](slug)
    else:
        listings = _fetch_custom(career_url)

    new_jobs = []
    for job in listings:
        save_watchlist_job(watchlist_id, job["title"], job["url"])
        new_jobs.append(job)

    update_watchlist_checked(watchlist_id)
    return new_jobs


def check_all_watchlist():
    """Check all active watchlist companies. Returns dict of company → new jobs."""
    watchlist = get_watchlist()
    results = {}

    for _, company in watchlist.iterrows():
        name = company["company_name"]
        try:
            new_jobs = check_company(company)
            if new_jobs:
                results[name] = new_jobs
        except Exception as e:
            print(f"Watchlist error for {name}: {e}")

    return results


def load_starter_list():
    """Add the starter companies to the watchlist."""
    for company in STARTER_COMPANIES:
        platform = company["platform"]
        slug = company["slug"]

        if platform in PLATFORMS and PLATFORMS[platform]:
            url = PLATFORMS[platform].format(slug=slug)
        else:
            url = company.get("url", "")

        add_to_watchlist(
            company_name=company["name"],
            career_url=url,
            platform_type=platform,
            company_slug=slug,
        )

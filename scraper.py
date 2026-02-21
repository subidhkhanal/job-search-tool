import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import quote_plus
from tracker import save_scraped_job


def generate_career_url(company, title=""):
    """Google search URL targeting the company's career page for this role."""
    query = f'{company} careers "{title}"' if title else f'{company} careers jobs'
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _get_with_retry(url, max_attempts=3, timeout=15, **kwargs):
    """GET request with exponential backoff retry."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                wait = 2 ** attempt
                print(f"  Retry {attempt + 1} for {url[:60]}... (waiting {wait}s)")
                time.sleep(wait)
    raise last_exc


KEYWORDS = [
    # Core AI/LLM
    "gen ai", "generative ai", "llm", "large language model",
    "rag", "retrieval augmented", "agentic ai", "ai agent",
    "langchain", "langgraph", "openai", "cohere",

    # Role titles
    "ai developer", "ai engineer", "ml engineer", "ai intern",
    "ml intern", "python developer", "backend developer",
    "nlp engineer", "automation engineer",

    # Tech stack
    "machine learning", "deep learning", "nlp",
    "natural language processing", "vector database",
    "chromadb", "pinecone", "fastapi", "python ai",

    # Broader catches
    "ai/ml", "artificial intelligence", "data scientist",
    "prompt engineer", "llm ops", "mlops",
]

INDIA_KEYWORDS = ["india", "noida", "delhi", "bangalore", "bengaluru",
                  "hyderabad", "mumbai", "pune", "chennai", "gurgaon",
                  "gurugram", "remote"]

# Priority: Delhi-NCR region (Noida-based, onsite/hybrid preferred)
NCR_KEYWORDS = ["noida", "delhi", "gurgaon", "gurugram", "ncr",
                "delhi-ncr", "delhi ncr", "greater noida", "faridabad",
                "ghaziabad"]
WORK_MODE_KEYWORDS = ["onsite", "on-site", "on site", "hybrid",
                      "office", "in-office", "in office", "work from office",
                      "wfo"]

def matches_keywords(text):
    """Check if text matches any of our target keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)

def scrape_remotive():
    """Scrape Remotive API - free, no key needed, remote jobs."""
    jobs = []
    try:
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=50"
        resp = _get_with_retry(url)
        data = resp.json()

        for job in data.get("jobs", []):
            title = job.get("title", "")
            desc = job.get("description", "")

            if matches_keywords(title) or matches_keywords(desc[:500]):
                job_data = {
                    "title": title,
                    "company": job.get("company_name", "Unknown"),
                    "location": job.get("candidate_required_location", "Remote"),
                    "source": "Remotive",
                    "url": job.get("url", ""),
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500]
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
    except Exception as e:
        print(f"Remotive error: {e}")

    return jobs

HN_THREAD_ID = "46857488"


def scrape_hn_who_is_hiring():
    """Scrape HackerNews 'Who is hiring?' thread - free HN API."""
    jobs = []
    try:
        # Use the known thread ID directly
        story_id = HN_THREAD_ID
        comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=200"
        resp = _get_with_retry(comments_url)
        comments = resp.json().get("hits", [])

        for comment in comments:
            text = comment.get("comment_text", "")
            if not text:
                continue

            text_clean = BeautifulSoup(text, "html.parser").get_text()

            # Check if it matches AI/ML keywords
            if matches_keywords(text_clean):
                # Check if India-friendly (remote or India mentioned)
                is_india_friendly = any(kw in text_clean.lower() for kw in INDIA_KEYWORDS)

                # Extract company and role from first line
                # HN format is usually: "Company | Role | Location | Type"
                first_line = text_clean.split("\n")[0].strip()
                parts = [p.strip() for p in first_line.split("|")]

                if len(parts) >= 3:
                    company = parts[0][:50]
                    title = parts[1][:80]
                    hn_location = parts[2][:50] if len(parts) > 2 else ""
                elif len(parts) == 2:
                    company = parts[0][:50]
                    title = parts[1][:80]
                    hn_location = ""
                else:
                    company = first_line[:50]
                    title = first_line[:80]
                    hn_location = ""

                location = hn_location if hn_location else "Remote/Various"
                if is_india_friendly and "india" not in location.lower():
                    location += " (India mentioned)"

                job_data = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "source": "HN Who's Hiring",
                    "url": f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}",
                    "description": text_clean[:500]
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
    except Exception as e:
        print(f"HN error: {e}")

    return jobs

def scrape_arbeitnow():
    """Scrape Arbeitnow API - free, no key needed."""
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        resp = _get_with_retry(url)
        data = resp.json()

        for job in data.get("data", []):
            title = job.get("title", "")
            desc = job.get("description", "")
            location = job.get("location", "")

            is_relevant = matches_keywords(title) or matches_keywords(desc[:500])
            is_india = any(kw in location.lower() for kw in INDIA_KEYWORDS) or job.get("remote", False)

            if is_relevant and is_india:
                job_data = {
                    "title": title,
                    "company": job.get("company_name", "Unknown"),
                    "location": location or ("Remote" if job.get("remote") else "Unknown"),
                    "source": "Arbeitnow",
                    "url": job.get("url", ""),
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500]
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
    except Exception as e:
        print(f"Arbeitnow error: {e}")

    return jobs


def scrape_jobspy():
    """Scrape multiple job boards via JobSpy (Indeed, Google, Glassdoor)."""
    jobs = []
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("python-jobspy not installed — skipping JobSpy scraper. Run: pip install python-jobspy")
        return jobs

    search_queries = [
        "AI developer India",
        "machine learning intern India",
        "gen ai developer Delhi NCR",
        "LLM engineer India",
        "python developer AI Noida",
        "AI intern India",
        "agentic AI developer India",
    ]

    seen_urls = set()

    for query in search_queries:
        try:
            results = scrape_jobs(
                site_name=["indeed", "google", "glassdoor"],
                search_term=query,
                location="India",
                results_wanted=10,
                hours_old=72,
                country_indeed="India",
            )

            for _, row in results.iterrows():
                title = str(row.get("title", ""))
                url = str(row.get("job_url", ""))

                # Deduplicate across queries
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                desc = str(row.get("description", "") or "")
                if not matches_keywords(title) and not matches_keywords(desc[:500]):
                    continue

                job_data = {
                    "title": title[:150],
                    "company": str(row.get("company_name", "Unknown"))[:80],
                    "location": str(row.get("location", "India"))[:80],
                    "source": f"JobSpy/{row.get('site', 'unknown')}",
                    "url": url,
                    "description": desc[:500],
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)

            time.sleep(3)  # Pause between queries
        except Exception as e:
            print(f"  JobSpy query '{query}' error: {e}")

    return jobs


def scrape_wellfound_search_hint():
    """
    Wellfound doesn't have a public API and scraping it violates TOS.
    Instead, this generates optimized search URLs for manual browsing.
    """
    base = "https://wellfound.com/jobs"
    searches = [
        f"{base}?q=gen+ai&location=Delhi+NCR",
        f"{base}?q=machine+learning&location=Delhi+NCR",
        f"{base}?q=llm+developer&location=Delhi+NCR",
        f"{base}?q=ai+engineer&location=Noida",
        f"{base}?q=ai+intern&location=Delhi+NCR",
        f"{base}?q=python+developer&location=Noida",
        f"{base}?q=ai+intern&location=Gurgaon",
    ]
    return searches

def scrape_linkedin_search_urls():
    """
    LinkedIn automation gets accounts banned.
    Instead, generate optimized search URLs for manual browsing.
    """
    base = "https://www.linkedin.com/jobs/search/?"
    searches = []
    queries_ncr = [
        ("gen ai developer Delhi NCR", "Delhi%2C%20India"),
        ("llm engineer Noida", "Noida%2C%20Uttar%20Pradesh%2C%20India"),
        ("ai ml intern Delhi NCR", "Delhi%2C%20India"),
        ("ai engineer Gurgaon", "Gurgaon%2C%20Haryana%2C%20India"),
        ("python developer Noida", "Noida%2C%20Uttar%20Pradesh%2C%20India"),
        ("machine learning engineer Delhi", "Delhi%2C%20India"),
        ("ai developer intern", "Delhi%2C%20India"),
        ("generative ai", "India"),
    ]
    for q, loc in queries_ncr:
        url = f"{base}keywords={q.replace(' ', '%20')}&location={loc}"
        searches.append({"query": q, "url": url})
    return searches

def scrape_hasjob():
    """Scrape HasJob by HasGeek for AI/ML jobs in India."""
    jobs = []
    try:
        url = "https://hasjob.co/search?q=ai+ml"
        resp = _get_with_retry(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        listings = soup.select(".listing")[:30]
        for listing in listings:
            title_el = listing.select_one(".listing-title a, h2 a")
            company_el = listing.select_one(".listing-company, .company")
            location_el = listing.select_one(".listing-location, .location")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            location = location_el.get_text(strip=True) if location_el else "India"
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://hasjob.co{link}"

            if matches_keywords(title):
                job_data = {
                    "title": title[:150],
                    "company": company[:80],
                    "location": location[:80],
                    "source": "HasJob",
                    "url": link,
                    "description": title,
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
    except Exception as e:
        print(f"HasJob error: {e}")
    return jobs


def scrape_developersindia():
    """Scrape developersindia.in job board for AI/ML jobs."""
    jobs = []
    try:
        url = "https://developersindia.in/job-board"
        resp = _get_with_retry(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try common listing patterns
        for link_el in soup.select("a[href*='job'], a[href*='position'], .job-listing a, .job-card a")[:30]:
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if not href.startswith("http"):
                href = f"https://developersindia.in{href}"

            if title and matches_keywords(title):
                job_data = {
                    "title": title[:150],
                    "company": "via developersIndia",
                    "location": "India",
                    "source": "developersIndia",
                    "url": href,
                    "description": title,
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
    except Exception as e:
        print(f"developersIndia error: {e}")
    return jobs


def scrape_internshala():
    """Scrape Internshala for AI/ML internships."""
    jobs = []
    urls = [
        "https://internshala.com/internships/artificial-intelligence-internship",
        "https://internshala.com/internships/machine-learning-internship",
    ]
    try:
        for page_url in urls:
            resp = _get_with_retry(page_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")

            for card in soup.select(".individual_internship, .internship_meta, .internship-heading-container")[:20]:
                title_el = card.select_one("h3, .heading_4_5, .profile a, a.view_detail_button")
                company_el = card.select_one(".company_name, h4, .heading_6")
                location_el = card.select_one(".location_link, #location_names span")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                location = location_el.get_text(strip=True) if location_el else "India"
                link = title_el.get("href", "")
                if link and not link.startswith("http"):
                    link = f"https://internshala.com{link}"

                job_data = {
                    "title": title[:150],
                    "company": company[:80],
                    "location": location[:80],
                    "source": "Internshala",
                    "url": link,
                    "description": f"Internship: {title}",
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
            time.sleep(2)
    except Exception as e:
        print(f"Internshala error: {e}")
    return jobs


def run_all_scrapers():
    """Run all automated scrapers and return combined results with error tracking."""
    all_jobs = []
    sources_status = {}
    sources_errors = {}

    scrapers = [
        ("Remotive", scrape_remotive),
        ("HN Who's Hiring", scrape_hn_who_is_hiring),
        ("Arbeitnow", scrape_arbeitnow),
        ("JobSpy (Indeed/Google/Glassdoor)", scrape_jobspy),
        ("HasJob", scrape_hasjob),
        ("developersIndia", scrape_developersindia),
        ("Internshala", scrape_internshala),
    ]

    for name, scraper_fn in scrapers:
        print(f"Scraping {name}...")
        try:
            results = scraper_fn()
            all_jobs.extend(results)
            sources_status[name] = len(results)
            if len(results) == 0:
                print(f"  WARNING: {name} returned 0 jobs")
        except Exception as e:
            sources_status[name] = 0
            sources_errors[name] = str(e)
            print(f"  ERROR: {name} failed: {e}")

    return all_jobs, sources_status, sources_errors

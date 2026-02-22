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

    # Role titles — intern-focused
    "ai intern", "ml intern", "ai internship", "ml internship",
    "python intern", "data science intern", "nlp intern",
    "ai developer", "ai engineer", "ml engineer",
    "python developer", "backend developer",
    "nlp engineer", "automation engineer",

    # Tech stack
    "machine learning", "deep learning", "nlp",
    "natural language processing", "vector database",
    "chromadb", "pinecone", "fastapi", "python ai",

    # Broader catches
    "ai/ml", "artificial intelligence", "data scientist",
    "prompt engineer", "llm ops", "mlops",
]

# Internship keywords — a job must match at least one to be included
INTERN_KEYWORDS = ["intern", "internship", "trainee", "apprentice",
                   "fresher", "entry level", "entry-level", "graduate",
                   "junior"]

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "anywhere",
                   "distributed", "fully remote"]

INDIA_KEYWORDS = ["india", "noida", "delhi", "bangalore", "bengaluru",
                  "hyderabad", "mumbai", "pune", "chennai", "gurgaon",
                  "gurugram", "remote"]

# Allowed locations: remote/worldwide, India, or Nepal
ALLOWED_LOCATION_KEYWORDS = [
    "remote", "worldwide", "anywhere", "global", "distributed",
    "work from home", "wfh", "fully remote",
    # India
    "india", "noida", "delhi", "bangalore", "bengaluru", "hyderabad",
    "mumbai", "pune", "chennai", "gurgaon", "gurugram", "kolkata",
    "jaipur", "ahmedabad", "lucknow",
    # Nepal
    "nepal", "kathmandu", "pokhara", "lalitpur", "biratnagar",
]


def is_allowed_location(text):
    """Check if job is remote/worldwide or located in India/Nepal."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALLOWED_LOCATION_KEYWORDS)

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


def is_remote(text):
    """Check if job text indicates remote work."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in REMOTE_KEYWORDS)


def is_internship(text):
    """Check if job text indicates an internship/entry-level role."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in INTERN_KEYWORDS)

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
            combined = title + " " + desc[:500]

            if not (matches_keywords(title) or matches_keywords(desc[:500])):
                continue
            # Remotive is already remote-only; filter for internships
            if not is_internship(combined):
                continue
            # Must allow India/Nepal/worldwide
            location_text = combined + " " + job.get("candidate_required_location", "")
            if not is_allowed_location(location_text):
                continue

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

            # Check if it matches AI/ML keywords + remote + internship + allowed location
            if not (matches_keywords(text_clean) and is_remote(text_clean) and is_internship(text_clean)):
                continue
            if not is_allowed_location(text_clean):
                continue

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

            combined = title + " " + desc[:500] + " " + location
            is_relevant = matches_keywords(title) or matches_keywords(desc[:500])
            is_remote_job = job.get("remote", False) or is_remote(combined)
            is_intern = is_internship(combined)

            if is_relevant and is_remote_job and is_intern and is_allowed_location(combined):
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
        "AI intern remote",
        "machine learning intern remote",
        "gen ai intern remote India",
        "LLM intern remote",
        "python intern AI remote",
        "data science intern remote India",
        "AI ML internship remote",
    ]

    seen_urls = set()

    for query in search_queries:
        try:
            results = scrape_jobs(
                site_name=["indeed", "google", "glassdoor", "linkedin", "naukri"],
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
                location = str(row.get("location", ""))
                combined = title + " " + desc[:500] + " " + location

                if not matches_keywords(title) and not matches_keywords(desc[:500]):
                    continue
                if not is_internship(combined) or not is_remote(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                job_data = {
                    "title": title[:150],
                    "company": str(row.get("company_name", "Unknown"))[:80],
                    "location": location[:80] or "Remote",
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
        f"{base}?q=ai+intern&remote=true",
        f"{base}?q=machine+learning+intern&remote=true",
        f"{base}?q=llm+intern&remote=true",
        f"{base}?q=gen+ai+intern&remote=true",
        f"{base}?q=python+intern&remote=true",
        f"{base}?q=data+science+intern&remote=true",
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
        ("ai intern remote", "India"),
        ("machine learning intern remote", "India"),
        ("llm intern remote", "India"),
        ("gen ai intern remote", "India"),
        ("data science intern remote", "India"),
        ("python intern remote", "India"),
        ("ai ml internship remote", "India"),
    ]
    for q, loc in queries_ncr:
        url = f"{base}keywords={q.replace(' ', '%20')}&location={loc}"
        searches.append({"query": q, "url": url})
    return searches

def scrape_hasjob():
    """Scrape HasJob by HasGeek for AI/ML jobs in India."""
    jobs = []
    try:
        url = "https://hasjob.co/search?q=ai+ml+intern"
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

            combined = title + " " + location
            if matches_keywords(title) and is_internship(combined) and is_allowed_location(combined):
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

            if title and matches_keywords(title) and is_internship(title):
                job_data = {
                    "title": title[:150],
                    "company": "via developersIndia",
                    "location": "India (Remote)",
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
        "https://internshala.com/internships/work-from-home-artificial-intelligence-internship",
        "https://internshala.com/internships/work-from-home-machine-learning-internship",
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


def scrape_remoteok():
    """Scrape RemoteOK API - free, no auth, remote jobs."""
    jobs = []
    try:
        resp = _get_with_retry("https://remoteok.com/api",
                               headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        # First element is a legal notice, actual jobs start at index 1
        for job in data[1:]:
            title = job.get("position", "")
            desc = job.get("description", "")
            location = job.get("location", "Remote")
            combined = title + " " + desc[:500] + " " + location

            if not (matches_keywords(title) or matches_keywords(desc[:500])):
                continue
            if not is_internship(combined):
                continue
            # RemoteOK is inherently remote, but verify for location
            if not is_allowed_location(combined):
                continue
            if not is_remote(combined):
                continue

            job_data = {
                "title": title[:150],
                "company": job.get("company", "Unknown")[:80],
                "location": location[:80] or "Remote",
                "source": "RemoteOK",
                "url": job.get("url", ""),
                "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500],
            }
            jobs.append(job_data)
            save_scraped_job(**job_data)
    except Exception as e:
        print(f"RemoteOK error: {e}")
    return jobs


def scrape_himalayas():
    """Scrape Himalayas API - free, no auth, remote jobs with intern filter."""
    jobs = []
    try:
        for offset in range(0, 100, 50):
            resp = _get_with_retry(
                f"https://himalayas.app/jobs/api?limit=50&offset={offset}",
                headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()

            for job in data.get("jobs", []):
                title = job.get("title", "")
                desc = job.get("description", "")
                company = job.get("companyName", "Unknown")
                emp_type = (job.get("employmentType", "") or "").lower()
                locations = job.get("locationRestrictions", [])
                location = ", ".join(locations[:3]) if locations else "Remote"
                combined = title + " " + desc[:500] + " " + location + " " + emp_type

                # Accept if employment type is intern, or if it matches keywords + intern check
                is_intern_type = "intern" in emp_type
                if not is_intern_type:
                    if not is_internship(combined):
                        continue
                if not (matches_keywords(title) or matches_keywords(desc[:500])):
                    continue
                if not is_remote(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                app_link = job.get("applicationLink", "") or job.get("guid", "")

                job_data = {
                    "title": title[:150],
                    "company": company[:80],
                    "location": location[:80] or "Remote",
                    "source": "Himalayas",
                    "url": app_link,
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500],
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)

            time.sleep(2)
    except Exception as e:
        print(f"Himalayas error: {e}")
    return jobs


def scrape_jobicy():
    """Scrape Jobicy API - free, no auth, remote jobs with internship filter."""
    jobs = []
    tags = ["ai", "machine-learning", "python", "data-science", "nlp"]
    try:
        for tag in tags:
            resp = _get_with_retry(
                f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={tag}",
                headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()

            for job in data.get("jobs", []):
                title = job.get("jobTitle", "")
                desc = job.get("jobDescription", "") or job.get("jobExcerpt", "")
                location = job.get("jobGeo", "Remote")
                job_types = job.get("jobType", [])
                job_level = (job.get("jobLevel", "") or "").lower()
                combined = title + " " + desc[:500] + " " + location + " " + job_level

                # Check for internship via jobType list or keywords
                is_intern_type = any("intern" in str(jt).lower() for jt in job_types)
                if not is_intern_type:
                    if not is_internship(combined):
                        continue
                if not (matches_keywords(title) or matches_keywords(desc[:500])):
                    continue
                if not is_remote(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                job_data = {
                    "title": title[:150],
                    "company": job.get("companyName", "Unknown")[:80],
                    "location": location[:80] or "Remote",
                    "source": "Jobicy",
                    "url": job.get("url", ""),
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500],
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)

            time.sleep(2)
    except Exception as e:
        print(f"Jobicy error: {e}")
    return jobs


def scrape_themuse():
    """Scrape The Muse API - free, no auth, has native Internship level filter."""
    jobs = []
    try:
        for page in range(0, 3):
            resp = _get_with_retry(
                f"https://www.themuse.com/api/public/jobs?level=Internship&page={page}",
                headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()

            for job in data.get("results", []):
                title = job.get("name", "")
                desc = job.get("contents", "")
                company_obj = job.get("company", {}) or {}
                company = company_obj.get("name", "Unknown")
                locations = [loc.get("name", "") for loc in job.get("locations", [])]
                location = ", ".join(locations[:3]) if locations else "Remote"
                combined = title + " " + desc[:500] + " " + location

                if not (matches_keywords(title) or matches_keywords(desc[:500])):
                    continue
                if not is_remote(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                refs = job.get("refs", {}) or {}
                url = refs.get("landing_page", "")

                job_data = {
                    "title": title[:150],
                    "company": company[:80],
                    "location": location[:80] or "Remote",
                    "source": "The Muse",
                    "url": url,
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500],
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)

            time.sleep(2)
    except Exception as e:
        print(f"The Muse error: {e}")
    return jobs


def scrape_jooble():
    """Scrape Jooble API - free with API key, aggregates many sources."""
    import os
    api_key = os.environ.get("JOOBLE_API_KEY", "")
    if not api_key:
        print("Jooble: No JOOBLE_API_KEY set — skipping.")
        return []

    jobs = []
    queries = [
        ("ai intern remote", ""),
        ("machine learning internship", "India"),
        ("llm intern", ""),
        ("gen ai internship", "India"),
        ("python intern ai", ""),
    ]
    try:
        for keywords, location in queries:
            payload = {"keywords": keywords, "location": location}
            resp = requests.post(
                f"https://jooble.org/api/{api_key}",
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for job in data.get("jobs", []):
                title = job.get("title", "")
                desc = job.get("snippet", "")
                loc = job.get("location", "Remote")
                combined = title + " " + desc[:500] + " " + loc

                if not (matches_keywords(title) or matches_keywords(desc[:500])):
                    continue
                if not is_internship(combined):
                    continue
                if not is_remote(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                job_data = {
                    "title": BeautifulSoup(title, "html.parser").get_text()[:150],
                    "company": job.get("company", "Unknown")[:80],
                    "location": loc[:80] or "Remote",
                    "source": "Jooble",
                    "url": job.get("link", ""),
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500],
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)

            time.sleep(2)
    except Exception as e:
        print(f"Jooble error: {e}")
    return jobs


def scrape_simplify_internships():
    """Parse SimplifyJobs Summer2026-Internships GitHub repo for curated listings."""
    import re
    jobs = []
    try:
        url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
        resp = _get_with_retry(url, headers={"User-Agent": "Mozilla/5.0"})
        text = resp.text

        # Parse markdown table rows: | Company | Role | Location | Link | Date |
        table_pattern = re.compile(
            r'^\|\s*(?:\*\*)?(.+?)(?:\*\*)?\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|',
            re.MULTILINE
        )

        for match in table_pattern.finditer(text):
            company = BeautifulSoup(match.group(1).strip(), "html.parser").get_text()
            title = BeautifulSoup(match.group(2).strip(), "html.parser").get_text()
            location = BeautifulSoup(match.group(3).strip(), "html.parser").get_text()

            # Skip table headers
            if company.lower() in ("company", "---", ""):
                continue
            if "---" in title:
                continue

            # Extract URL from markdown link [text](url)
            link_match = re.search(r'\[.*?\]\((https?://[^)]+)\)', match.group(4))
            url = link_match.group(1) if link_match else ""

            combined = title + " " + company + " " + location
            if not (matches_keywords(combined)):
                continue
            if not is_remote(combined):
                continue
            if not is_allowed_location(combined):
                continue

            job_data = {
                "title": title[:150],
                "company": company[:80],
                "location": location[:80] or "Remote",
                "source": "SimplifyJobs",
                "url": url,
                "description": f"Summer 2026 Internship: {title} at {company}",
            }
            jobs.append(job_data)
            save_scraped_job(**job_data)
    except Exception as e:
        print(f"SimplifyJobs error: {e}")
    return jobs


def scrape_wellfound_graphql():
    """Scrape Wellfound via internal GraphQL API. Requires browser cookies."""
    import os
    import json

    session_cookie = os.environ.get("WELLFOUND_SESSION", "")
    cf_cookie = os.environ.get("WELLFOUND_CF", "")
    dd_cookie = os.environ.get("WELLFOUND_DATADOME", "")

    if not session_cookie or not cf_cookie:
        print("Wellfound: Missing cookies (WELLFOUND_SESSION, WELLFOUND_CF) — skipping.")
        return []

    jobs = []
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Apollographql-Client-Name": "talent-web",
        "Content-Type": "application/json",
        "Origin": "https://wellfound.com",
        "Referer": "https://wellfound.com/jobs",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-Apollo-Operation-Name": "JobSearchResultsX",
        "X-Requested-With": "XMLHttpRequest",
    }
    cookies = {
        "logged_in": "true",
        "_wellfound": session_cookie,
        "cf_clearance": cf_cookie,
        "datadome": dd_cookie,
    }

    search_keywords = [
        ["AI intern", "ML intern", "LLM"],
        ["machine learning intern", "gen ai intern"],
    ]

    try:
        for kw_batch in search_keywords:
            for page in range(1, 4):
                payload = {
                    "operationName": "JobSearchResultsX",
                    "variables": {
                        "filterConfigurationInput": {
                            "page": page,
                            "customJobTitles": kw_batch,
                            "remotePreference": "REMOTE_OPEN",
                            "jobTypes": ["internship"],
                            "equity": {"min": None, "max": None},
                            "salary": {"min": None, "max": None},
                            "yearsExperience": {"min": None, "max": 2},
                        }
                    },
                    "extensions": {
                        "operationId": "tfe/2aeb9d7cc572a94adfe2b888b32e64eb8b7fb77215b168ba4256b08f9a94f37b"
                    }
                }

                resp = requests.post(
                    "https://wellfound.com/graphql",
                    json=payload,
                    headers=headers,
                    cookies=cookies,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                edges = data.get("data", {}).get("talent", {}).get(
                    "jobSearchResults", {}).get("startups", {}).get("edges", [])

                for edge in edges:
                    node = edge.get("node", {})
                    typename = node.get("__typename", "")

                    # Normalize company node based on type
                    if typename == "StartupSearchResult":
                        company_node = node
                    elif typename == "PromotedResult":
                        company_node = node.get("promotedStartup", node)
                    else:
                        continue

                    company_name = company_node.get("name", "Unknown")
                    company_slug = company_node.get("slug", "")
                    locations = [loc.get("displayName", "")
                                 for loc in company_node.get("locationTaggings", [])]

                    for jl in company_node.get("highlightedJobListings", []):
                        jl_title = jl.get("title", "")
                        jl_id = jl.get("id", "")
                        jl_slug = jl.get("slug", "")
                        jl_locations = jl.get("locationNames", [])
                        jl_desc = (jl.get("description", "") or "")[:500]

                        if jl.get("remote"):
                            location = "Remote"
                            if jl_locations:
                                location += f" ({', '.join(jl_locations[:3])})"
                        elif jl_locations:
                            location = ", ".join(jl_locations[:3])
                        elif locations:
                            location = ", ".join(locations[:3])
                        else:
                            location = "Unknown"

                        combined = jl_title + " " + jl_desc[:300] + " " + location
                        if not (matches_keywords(jl_title) or matches_keywords(jl_desc[:300])):
                            continue
                        if not is_remote(combined):
                            continue
                        if not is_allowed_location(combined):
                            continue

                        url = f"https://wellfound.com/company/{company_slug}/jobs/{jl_id}-{jl_slug}" if company_slug and jl_slug else "https://wellfound.com/jobs"

                        job_data = {
                            "title": jl_title[:150],
                            "company": company_name[:80],
                            "location": location[:80],
                            "source": "Wellfound",
                            "url": url,
                            "description": BeautifulSoup(jl_desc, "html.parser").get_text()[:500],
                        }
                        jobs.append(job_data)
                        save_scraped_job(**job_data)

                has_next = data.get("data", {}).get("talent", {}).get(
                    "jobSearchResults", {}).get("hasNextPage", False)
                if not has_next:
                    break
                time.sleep(3)

            time.sleep(2)
    except Exception as e:
        print(f"Wellfound GraphQL error: {e}")
    return jobs


def scrape_unstop():
    """Scrape Unstop (D2C) internships page via their internal API."""
    jobs = []
    try:
        # Unstop has an internal API that returns JSON for opportunities
        api_url = "https://unstop.com/api/public/opportunity/search-new"
        payload = {
            "opportunity": ["internships"],
            "oppstatus": "open",
            "sort": "recency",
            "page": 1,
            "per_page": 30,
            "filters": {
                "keyword": "ai ml",
            }
        }
        resp = requests.post(
            api_url,
            json=payload,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://unstop.com",
                "Referer": "https://unstop.com/internships",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        opportunities = data.get("data", {}).get("data", [])
        for opp in opportunities:
            title = opp.get("title", "")
            org = opp.get("organisation", {}) or {}
            company = org.get("name", "Unknown")
            location = opp.get("city", "") or "India"
            if isinstance(location, list):
                location = ", ".join(location[:3])
            slug = opp.get("public_url", "") or opp.get("slug", "")
            url = f"https://unstop.com/internships/{slug}" if slug and not slug.startswith("http") else slug

            combined = title + " " + company + " " + str(location)
            if not (matches_keywords(title) or matches_keywords(combined)):
                continue
            if not is_remote(combined):
                continue
            if not is_allowed_location(combined):
                continue

            job_data = {
                "title": title[:150],
                "company": company[:80],
                "location": str(location)[:80] or "Remote",
                "source": "Unstop",
                "url": url,
                "description": f"Internship: {title} at {company}",
            }
            jobs.append(job_data)
            save_scraped_job(**job_data)
    except Exception as e:
        print(f"Unstop error: {e}")
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
        ("JobSpy (Indeed/Google/Glassdoor/LinkedIn/Naukri)", scrape_jobspy),
        ("HasJob", scrape_hasjob),
        ("developersIndia", scrape_developersindia),
        ("Internshala", scrape_internshala),
        ("RemoteOK", scrape_remoteok),
        ("Himalayas", scrape_himalayas),
        ("Jobicy", scrape_jobicy),
        ("The Muse", scrape_themuse),
        ("Jooble", scrape_jooble),
        ("SimplifyJobs", scrape_simplify_internships),
        ("Wellfound", scrape_wellfound_graphql),
        ("Unstop", scrape_unstop),
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

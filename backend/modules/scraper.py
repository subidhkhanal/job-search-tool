import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import quote_plus
from tracker import save_scraped_job


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
                  "gurugram"]

# Allowed locations: India only
ALLOWED_LOCATION_KEYWORDS = [
    "india", "noida", "delhi", "bangalore", "bengaluru", "hyderabad",
    "mumbai", "pune", "chennai", "gurgaon", "gurugram", "kolkata",
    "jaipur", "ahmedabad", "lucknow",
]


def is_allowed_location(text):
    """Check if job explicitly mentions India or an Indian city."""
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


def is_global_or_india(location_text):
    """Check if location explicitly mentions India or an Indian city.
    Empty location is rejected (can't confirm it's India)."""
    if not location_text or not location_text.strip():
        return False
    text_lower = location_text.lower()
    return any(kw in text_lower for kw in ALLOWED_LOCATION_KEYWORDS)


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

            if not is_internship(combined):
                continue
            # Must allow India/worldwide
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

            # Check if it matches remote + internship + allowed location
            if not (is_remote(text_clean) and is_internship(text_clean)):
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
            is_remote_job = job.get("remote", False) or is_remote(combined)
            is_intern = is_internship(combined)

            if is_remote_job and is_intern and is_allowed_location(combined):
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
                hours_old=24,
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
            if is_internship(combined) and is_allowed_location(combined):
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

            if title and is_internship(title):
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
    """Scrape RemoteOK API - free, no auth, remote jobs.
    RemoteOK is inherently remote; location field = geo-restriction."""
    jobs = []
    try:
        resp = _get_with_retry("https://remoteok.com/api",
                               headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        # First element is a legal notice, actual jobs start at index 1
        for job in data[1:]:
            title = job.get("position", "")
            desc = job.get("description", "")
            tags = " ".join(job.get("tags", []))
            location = job.get("location", "")
            combined = title + " " + desc[:500] + " " + tags

            if not is_internship(combined):
                continue
            # RemoteOK is all-remote; location = geo-restriction
            if not is_global_or_india(location):
                continue

            job_data = {
                "title": title[:150],
                "company": job.get("company", "Unknown")[:80],
                "location": (location or "Remote (Worldwide)")[:80],
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
    """Scrape Himalayas API - free, no auth, remote-first board.
    locationRestrictions = geo-restriction, seniority = level."""
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
                seniority = [s.lower() for s in job.get("seniority", [])]
                categories = " ".join(job.get("categories", []))
                locations = job.get("locationRestrictions", [])
                location = ", ".join(locations[:3]) if locations else ""
                combined = title + " " + desc[:500] + " " + categories

                # Check intern/entry-level via seniority field or text
                is_entry = any("entry" in s or "intern" in s or "junior" in s for s in seniority)
                if not is_entry:
                    if not is_internship(combined):
                        continue
                # Himalayas is remote-first; locationRestrictions = geo-restriction
                if not is_global_or_india(location):
                    continue

                app_link = job.get("applicationLink", "") or job.get("guid", "")

                job_data = {
                    "title": title[:150],
                    "company": company[:80],
                    "location": (location or "Remote (Worldwide)")[:80],
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
    """Scrape Jobicy API - free, no auth, remote job board.
    jobGeo = geo-restriction for remote workers, not remote status."""
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
                location = job.get("jobGeo", "")
                job_types = job.get("jobType", [])
                job_level = (job.get("jobLevel", "") or "").lower()
                combined = title + " " + desc[:500] + " " + job_level

                # Check for internship via jobType list, jobLevel, or text
                is_intern_type = any("intern" in str(jt).lower() for jt in job_types)
                is_entry_level = any(kw in job_level for kw in ["entry", "junior", "intern"])
                if not is_intern_type and not is_entry_level:
                    if not is_internship(combined):
                        continue
                # Jobicy is all-remote; jobGeo = geo-restriction
                if not is_global_or_india(location):
                    continue

                job_data = {
                    "title": title[:150],
                    "company": job.get("companyName", "Unknown")[:80],
                    "location": (location or "Remote (Worldwide)")[:80],
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
    """Scrape The Muse API - free, no auth, has native Internship level filter.
    Fetches remote/flexible + India-based internships."""
    jobs = []
    # Query both remote/flexible and India-based internships
    api_urls = [
        "https://www.themuse.com/api/public/jobs?level=Internship&location=Flexible%20%2F%20Remote&page=0",
        "https://www.themuse.com/api/public/jobs?level=Internship&location=Flexible%20%2F%20Remote&page=1",
        "https://www.themuse.com/api/public/jobs?level=Internship&location=India&page=0",
    ]
    seen_ids = set()
    try:
        for api_url in api_urls:
            resp = _get_with_retry(api_url, headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()

            for job in data.get("results", []):
                job_id = job.get("id")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = job.get("name", "")
                desc = job.get("contents", "")
                company_obj = job.get("company", {}) or {}
                company = company_obj.get("name", "Unknown")
                locations = [loc.get("name", "") for loc in job.get("locations", [])]
                location = ", ".join(locations[:3]) if locations else "Flexible / Remote"
                combined = title + " " + desc[:500] + " " + location

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
    """Parse SimplifyJobs Summer2026-Internships GitHub repo for curated listings.
    The README uses HTML <table> tags, not pipe-delimited markdown."""
    import re
    jobs = []
    try:
        url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
        resp = _get_with_retry(url, headers={"User-Agent": "Mozilla/5.0"})
        text = resp.text

        # Parse HTML table rows: <tr><td>Company</td><td>Role</td><td>Location</td><td>Link</td><td>Date</td></tr>
        tr_pattern = re.compile(r'<tr>\s*(.*?)\s*</tr>', re.DOTALL)
        td_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)

        for tr_match in tr_pattern.finditer(text):
            tds = td_pattern.findall(tr_match.group(1))
            if len(tds) < 4:
                continue

            company = BeautifulSoup(tds[0], "html.parser").get_text(strip=True)
            title = BeautifulSoup(tds[1], "html.parser").get_text(strip=True)
            location = BeautifulSoup(tds[2], "html.parser").get_text(strip=True)

            # Skip headers
            if company.lower() in ("company", "---", "") or not title:
                continue

            # Extract apply URL from the link column
            link_match = re.search(r'href="(https?://[^"]+)"', tds[3])
            apply_url = link_match.group(1) if link_match else ""

            combined = title + " " + company + " " + location
            # All entries are internships — filter by remote or India location
            location_lower = location.lower()
            is_remote_job = any(kw in location_lower for kw in ["remote", "anywhere", "worldwide", "flexible"])
            is_india_job = any(kw in location_lower for kw in ["india", "bangalore", "bengaluru", "hyderabad",
                                                                "mumbai", "pune", "delhi", "noida", "chennai"])
            if not is_remote_job and not is_india_job:
                continue

            job_data = {
                "title": title[:150],
                "company": company[:80],
                "location": location[:80] or "Remote",
                "source": "SimplifyJobs",
                "url": apply_url,
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
    """Scrape Unstop (D2C) internships via their search API."""
    jobs = []
    search_queries = ["ai ml internship", "machine learning intern", "data science intern",
                      "python intern", "gen ai internship"]
    try:
        for query in search_queries:
            # Unstop search API (public, no auth)
            api_url = f"https://unstop.com/api/public/opportunity/search-result?opportunity=internships&searchTerm={quote_plus(query)}&oppstatus=open&sort=recency&per_page=20"
            resp = requests.get(
                api_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://unstop.com/internships",
                },
                timeout=15,
            )
            if resp.status_code == 403:
                # Fallback: try scraping HTML search page
                break
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
                url = f"https://unstop.com/internships/{slug}" if slug and not slug.startswith("http") else (slug or "")

                combined = title + " " + company + " " + str(location)
                if not is_internship(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                job_data = {
                    "title": title[:150],
                    "company": company[:80],
                    "location": str(location)[:80] or "India",
                    "source": "Unstop",
                    "url": url,
                    "description": f"Internship: {title} at {company}",
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
            time.sleep(2)
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

import requests
from bs4 import BeautifulSoup
import time
import random
import re
import os
from datetime import datetime
from urllib.parse import quote_plus


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
    except Exception as e:
        print(f"Remotive error: {e}")

    return jobs

HN_THREAD_ID_FALLBACK = "46857488"


def _get_latest_hn_thread_id():
    """Auto-discover the latest 'Who is hiring?' thread from the whoishiring bot."""
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={
                "query": '"Who is hiring"',
                "tags": "ask_hn,author_whoishiring",
                "hitsPerPage": 1,
            },
            timeout=10,
        )
        hits = resp.json().get("hits", [])
        if hits:
            return hits[0]["objectID"]
    except Exception as e:
        print(f"  HN thread auto-discovery failed: {e}")
    return HN_THREAD_ID_FALLBACK


def scrape_hn_who_is_hiring():
    """Scrape HackerNews 'Who is hiring?' thread - free HN API."""
    jobs = []
    try:
        story_id = _get_latest_hn_thread_id()
        print(f"  HN thread ID: {story_id}")
        comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=200"
        resp = _get_with_retry(comments_url)
        comments = resp.json().get("hits", [])

        for comment in comments:
            text = comment.get("comment_text", "")
            if not text:
                continue

            text_clean = BeautifulSoup(text, "html.parser").get_text()

            # Check if it matches internship keywords (no location filter for HN — global board)
            if not is_internship(text_clean):
                continue

            # Extract company and role from first line
            # HN format is usually: "Company | Role | Location | Type"
            first_line = text_clean.split("\n")[0].strip()

            # Skip non-job comments (replies, job seekers) — real posts use pipe format
            if "|" not in first_line:
                continue

            parts = [p.strip() for p in first_line.split("|")]

            if len(parts) >= 3:
                company = parts[0][:50]
                title = parts[1][:80]
                hn_location = parts[2][:50]
            else:
                company = parts[0][:50]
                title = parts[1][:80]
                hn_location = ""

            location = hn_location if hn_location else "Remote/Various"

            job_data = {
                "title": title,
                "company": company,
                "location": location,
                "source": "HN Who's Hiring",
                "url": f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}",
                "description": text_clean[:500]
            }
            jobs.append(job_data)
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

            if is_internship(combined) and is_allowed_location(combined):
                job_data = {
                    "title": title,
                    "company": job.get("company_name", "Unknown"),
                    "location": location or ("Remote" if job.get("remote") else "Unknown"),
                    "source": "Arbeitnow",
                    "url": job.get("url", ""),
                    "description": BeautifulSoup(desc[:1000], "html.parser").get_text()[:500]
                }
                jobs.append(job_data)
    except Exception as e:
        print(f"Arbeitnow error: {e}")

    return jobs


_LINKEDIN_SEARCH_QUERIES = [
    "gen ai intern",
    "generative ai intern",
    "genai intern",
    "llm engineer intern",
    "ai engineer intern",
    "ai developer intern",
    "machine learning intern",
    "ml intern",
    "nlp intern",
    "prompt engineer intern",
    "ai automation intern",
    "deep learning intern",
    "computer vision intern",
    "data science intern",
    "ai research intern",
    "research intern ai",
    "ai trainee",
]

_LINKEDIN_LOCATIONS = ["India", "Remote"]

_TITLE_INCLUDE = [
    "gen ai", "genai", "generative ai", "llm", "ai engineer", "ai developer",
    "nlp engineer", "machine learning engineer", "ml intern", "ai/ml",
    "ai automation", "prompt engineer", "ai research", "research intern",
    "large language model", "langchain", "rag", "agentic ai",
    "ai trainee", "deep learning", "computer vision", "data science",
]

_TITLE_REJECT = [
    "frontend", "react", "angular", "ui/ux", "devops", "cloud", "data analyst",
    "content", "marketing", "sales", "hr", "finance", "blockchain",
]

# Exact phrases score higher than partial keyword matches
_TITLE_EXACT_PHRASES = [
    "ai engineer intern", "ml engineer intern", "ai developer intern",
    "gen ai intern", "generative ai intern", "machine learning intern",
    "data science intern", "deep learning intern", "nlp intern",
    "computer vision intern", "ai research intern", "prompt engineer intern",
    "ai automation intern", "ai trainee", "llm engineer intern",
]


def _is_india_or_remote(location_str):
    """Keep job if location contains 'india' or indicates remote."""
    if not location_str or not location_str.strip():
        return False
    loc = location_str.lower()
    return "india" in loc or "remote" in loc


def _load_blacklist():
    """Load company blacklist from blacklist.txt. Returns a set of lowercase names."""
    blacklist_path = os.path.join(os.path.dirname(__file__), "..", "..", "blacklist.txt")
    try:
        with open(blacklist_path, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def _normalize_for_dedup(text):
    """Lowercase, strip punctuation, strip 'intern'/'internship' for dedup key."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\b(internship|intern)\b", "", text)
    return " ".join(text.split())


def _title_passes_filter(title):
    """Return True if title passes REJECT/INCLUDE filter. REJECT checked first."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in _TITLE_REJECT):
        return False
    if any(kw in title_lower for kw in _TITLE_INCLUDE):
        return True
    return False


def _llm_filter_jobs(jobs):
    """Use LLM to filter jobs for relevance to the user's profile.
    Returns filtered list on success, or None to signal fallback to keyword filter."""
    import json
    try:
        from groq import Groq
        from message_generator import _get_profile_text
    except Exception:
        return None

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    profile_text = _get_profile_text()
    job_list = "\n".join(
        f"{i}. {j['title']} — {j['company']}" for i, j in enumerate(jobs)
    )

    prompt = f"""You are filtering job listings for an AI/ML job seeker.

CANDIDATE PROFILE:
{profile_text}

JOB LISTINGS:
{job_list}

Return ONLY a JSON array of the 0-based index numbers of jobs relevant for this candidate.
Include: AI, ML, data science, NLP, LLM, GenAI, computer vision, research, automation engineering roles.
Exclude: pure frontend, DevOps, cloud ops, marketing, sales, HR, finance, blockchain, content.
Example: [0, 2, 5]
Respond with ONLY the JSON array, nothing else."""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        indices = json.loads(response.choices[0].message.content.strip())
        return [jobs[i] for i in indices if 0 <= i < len(jobs)]
    except Exception as e:
        print(f"  LLM title filter failed: {e} — falling back to keyword filter")
        return None


def _is_blacklisted(company, blacklist):
    """Check if company name matches any blacklisted name (substring match)."""
    if not blacklist:
        return False
    company_lower = company.lower()
    return any(bl in company_lower for bl in blacklist)


def _score_linkedin_job(job):
    """Simple deterministic scoring for a LinkedIn job. Returns 0-100."""
    score = 0
    title_lower = job.get("title", "").lower()

    # Exact title phrase match: +40
    if any(phrase in title_lower for phrase in _TITLE_EXACT_PHRASES):
        score += 40
    # Partial keyword match: +20 (only if no exact match)
    elif any(kw in title_lower for kw in _TITLE_INCLUDE):
        score += 20

    # Match count bonus: (match_count - 1) * 10, capped at +30
    match_count = job.get("match_count", 1)
    score += min((match_count - 1) * 10, 30)

    # Company name present: +5
    company = job.get("company", "").strip()
    if company and company != "Unknown":
        score += 5

    # Location is Remote: +5
    location = job.get("location", "").lower()
    if "remote" in location:
        score += 5

    # Posted date available: +5
    if job.get("posted_date"):
        score += 5

    return min(score, 100)


def scrape_linkedin():
    """Scrape LinkedIn via JobSpy for targeted AI/ML internships."""
    start_time = time.time()

    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("python-jobspy not installed — skipping LinkedIn scraper. Run: pip install python-jobspy")
        return []

    # Build and randomize 34 query+location combos
    combos = [(q, loc) for q in _LINKEDIN_SEARCH_QUERIES for loc in _LINKEDIN_LOCATIONS]
    random.shuffle(combos)

    blacklist = _load_blacklist()

    # Stats
    total_raw = 0
    after_location_filter = 0
    after_title_filter = 0
    after_blacklist = 0
    combos_run = 0

    # In-memory dedup: key -> job_data (with match_count)
    dedup_map = {}

    for query, location in combos:
        combos_run += 1
        try:
            results = scrape_jobs(
                site_name=["linkedin"],
                search_term=query,
                location=location,
                job_type="internship",
                hours_old=24,
                results_wanted=50,
            )

            for _, row in results.iterrows():
                total_raw += 1

                title = str(row.get("title", "")).strip()
                if not title:
                    continue

                # Location filter — must contain "india"
                if not _is_india_or_remote(str(row.get("location", ""))):
                    continue
                after_location_filter += 1

                company = str(row.get("company", "Unknown")).strip() or "Unknown"
                url = str(row.get("job_url", "")).strip()

                # Blacklist check
                if _is_blacklisted(company, blacklist):
                    continue
                after_blacklist += 1

                job_location = str(row.get("location", "")).strip() or location
                desc = str(row.get("description", "") or "")[:500]
                posted_date = str(row.get("date_posted", "") or "") or None

                # In-memory dedup by normalized title + company
                dedup_key = _normalize_for_dedup(title) + "||" + _normalize_for_dedup(company)

                if dedup_key in dedup_map:
                    dedup_map[dedup_key]["match_count"] += 1
                    # Keep the URL with more info (prefer non-empty)
                    if url and not dedup_map[dedup_key]["url"]:
                        dedup_map[dedup_key]["url"] = url
                else:
                    dedup_map[dedup_key] = {
                        "title": title[:150],
                        "company": company[:80],
                        "location": job_location[:80],
                        "source": "LinkedIn",
                        "url": url,
                        "description": desc,
                        "posted_date": posted_date,
                        "source_query": query,
                        "match_count": 1,
                        "score": 0,
                        "scraped_at": datetime.now().isoformat(),
                    }

            time.sleep(3)
        except Exception as e:
            print(f"  LinkedIn query '{query}' ({location}) error: {e}")

    # Convert dedup map to list
    jobs = list(dedup_map.values())
    after_title_filter = len(jobs)

    for job in jobs:
        job["score"] = _score_linkedin_job(job)
    jobs.sort(key=lambda j: j["score"], reverse=True)

    # Print summary
    elapsed = time.time() - start_time
    avg_match = sum(j["match_count"] for j in jobs) / len(jobs) if jobs else 0
    top_score = jobs[0]["score"] if jobs else 0
    health = "OK" if total_raw > 0 else "FAILED"

    print(f"\n--- LinkedIn Scraper Run Summary ---")
    print(f"Combinations run: {combos_run}")
    print(f"Query order: randomized")
    print(f"Time filter: last 24 hours")
    print(f"Results per query: up to 50")
    print(f"Total raw results: {total_raw}")
    print(f"After location filter: {after_location_filter} (dropped {total_raw - after_location_filter} non-India)")
    print(f"After title filter: {after_title_filter}")
    print(f"After blacklist: {after_blacklist}")
    print(f"After in-memory dedup: {len(jobs)}")
    print(f"Avg match count: {avg_match:.1f}")
    print(f"Top score: {top_score}")
    print(f"Time taken: {elapsed:.0f}s")
    print(f"Health: {health}")

    if health == "FAILED":
        print("[HEALTH CHECK FAILED] Zero raw results across all combinations — possible scraper failure.")

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
    except Exception as e:
        print(f"developersIndia error: {e}")
    return jobs


_INTERNSHALA_CATEGORIES = [
    "work-from-home-artificial-intelligence-internship",
    "work-from-home-machine-learning-internship",
    "work-from-home-data-science-internship",
    "work-from-home-python-internship",
]

_INTERNSHALA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://internshala.com/internships/",
}


def _parse_internshala_cards(html, seen_urls):
    """Parse Internshala internship cards from HTML. Returns list of job dicts."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    for card in soup.select(".individual_internship"):
        title_el = card.select_one("h3.job-internship-name a, h3.job-internship-name")
        company_el = card.select_one(".company-name")
        location_el = card.select_one(".locations")

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        company = company_el.get_text(strip=True) if company_el else "Unknown"
        location = location_el.get_text(strip=True) if location_el else "India"

        link = ""
        link_el = title_el if title_el.name == "a" else card.select_one("a.job-title-href, .company a[href]")
        if link_el:
            link = link_el.get("href", "")
        if link and not link.startswith("http"):
            link = f"https://internshala.com{link}"

        if link in seen_urls:
            continue
        if link:
            seen_urls.add(link)

        # Extract stipend and duration from row-1 items
        row_items = card.select(".row-1-item")
        stipend = ""
        duration = ""
        for item in row_items:
            text = item.get_text(strip=True)
            if "/month" in text or "/week" in text:
                stipend = text
            elif "Month" in text or "Week" in text or "Day" in text:
                duration = text

        skills = ", ".join(
            s.get_text(strip=True) for s in card.select(".skill_container")
        )

        desc_parts = [f"Internship: {title}"]
        if stipend:
            desc_parts.append(f"Stipend: {stipend}")
        if duration:
            desc_parts.append(f"Duration: {duration}")
        if skills:
            desc_parts.append(f"Skills: {skills}")

        job_data = {
            "title": title[:150],
            "company": company[:80],
            "location": location[:80],
            "source": "Internshala",
            "url": link,
            "description": " | ".join(desc_parts)[:500],
        }
        jobs.append(job_data)

    return jobs


def scrape_internshala():
    """Scrape Internshala for AI/ML internships via their AJAX endpoint."""
    seen_urls = set()
    dedup_map = {}
    blacklist = _load_blacklist()

    for category in _INTERNSHALA_CATEGORIES:
        try:
            ajax_url = f"https://internshala.com/internships_ajax/{category}"
            resp = _get_with_retry(ajax_url, headers=_INTERNSHALA_HEADERS)
            data = resp.json()

            html = data.get("internship_list_html", "")
            if not html:
                continue

            parsed = _parse_internshala_cards(html, seen_urls)
            for job in parsed:
                # Blacklist check
                if _is_blacklisted(job["company"], blacklist):
                    continue

                # In-memory dedup by normalized title + company
                dedup_key = _normalize_for_dedup(job["title"]) + "||" + _normalize_for_dedup(job["company"])
                if dedup_key in dedup_map:
                    dedup_map[dedup_key]["match_count"] += 1
                else:
                    job["match_count"] = 1
                    job["scraped_at"] = datetime.now().isoformat()
                    dedup_map[dedup_key] = job

            time.sleep(2)
        except Exception as e:
            print(f"  Internshala error for {category}: {e}")

    return list(dedup_map.values())


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
            # All entries are internships — filter by India location
            if not is_allowed_location(combined):
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
    except Exception as e:
        print(f"SimplifyJobs error: {e}")
    return jobs


def scrape_unstop():
    """Scrape Unstop (D2C) internships via their search API."""
    search_queries = ["ai ml internship", "machine learning intern", "data science intern",
                      "python intern", "gen ai internship"]
    dedup_map = {}
    blacklist = _load_blacklist()

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
                url = f"https://unstop.com/{slug}" if slug and not slug.startswith("http") else (slug or "")

                combined = title + " " + company + " " + str(location)
                if not is_internship(combined):
                    continue
                if not is_allowed_location(combined):
                    continue

                # Blacklist check
                if _is_blacklisted(company, blacklist):
                    continue

                # In-memory dedup by normalized title + company
                dedup_key = _normalize_for_dedup(title) + "||" + _normalize_for_dedup(company)
                if dedup_key in dedup_map:
                    dedup_map[dedup_key]["match_count"] += 1
                else:
                    dedup_map[dedup_key] = {
                        "title": title[:150],
                        "company": company[:80],
                        "location": str(location)[:80] or "India",
                        "source": "Unstop",
                        "url": url,
                        "description": f"Internship: {title} at {company}",
                        "match_count": 1,
                        "scraped_at": datetime.now().isoformat(),
                    }
            time.sleep(2)
    except Exception as e:
        print(f"Unstop error: {e}")

    return list(dedup_map.values())


def run_all_scrapers():
    """Run all automated scrapers and return combined results with error tracking."""
    all_jobs = []
    sources_status = {}
    sources_errors = {}

    scrapers = [
        ("Remotive", scrape_remotive),
        ("HN Who's Hiring", scrape_hn_who_is_hiring),
        ("Arbeitnow", scrape_arbeitnow),
        ("LinkedIn AI/ML", scrape_linkedin),
        ("Internshala", scrape_internshala),
        ("RemoteOK", scrape_remoteok),
        ("Himalayas", scrape_himalayas),
        ("Jobicy", scrape_jobicy),
        ("The Muse", scrape_themuse),
        ("Jooble", scrape_jooble),
        ("SimplifyJobs", scrape_simplify_internships),
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

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from tracker import save_scraped_job

try:
    from googlesearch import search as google_search
except ImportError:
    google_search = None

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
        resp = requests.get(url, timeout=15)
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

def scrape_hn_who_is_hiring():
    """Scrape HackerNews 'Who is hiring?' thread - free HN API."""
    jobs = []
    try:
        # Find the latest "Who is hiring" thread
        search_url = "https://hn.algolia.com/api/v1/search?query=who%20is%20hiring&tags=story&hitsPerPage=5"
        resp = requests.get(search_url, timeout=15)
        stories = resp.json().get("hits", [])
        
        hiring_story = None
        for story in stories:
            if "who is hiring" in story.get("title", "").lower():
                hiring_story = story
                break
        
        if not hiring_story:
            return jobs
        
        # Get comments from the thread
        story_id = hiring_story["objectID"]
        comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=200"
        resp = requests.get(comments_url, timeout=15)
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
                
                # Extract company name (usually first line)
                first_line = text_clean.split("\n")[0].strip()
                company = first_line[:100] if first_line else "See posting"
                
                job_data = {
                    "title": first_line[:150],
                    "company": company.split("|")[0].strip() if "|" in company else company,
                    "location": "Remote/Various" + (" (India mentioned)" if is_india_friendly else ""),
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
        resp = requests.get(url, timeout=15)
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

def scrape_github_jobs_search():
    """Search GitHub repositories for job postings in AI/ML."""
    jobs = []
    try:
        # Search for recent AI job posting repos
        url = "https://api.github.com/search/repositories?q=ai+ml+jobs+india+2025+2026&sort=updated&per_page=10"
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            for repo in resp.json().get("items", []):
                job_data = {
                    "title": repo.get("name", ""),
                    "company": repo.get("owner", {}).get("login", "Unknown"),
                    "location": "Various",
                    "source": "GitHub Repos",
                    "url": repo.get("html_url", ""),
                    "description": (repo.get("description", "") or "")[:500]
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
    except Exception as e:
        print(f"GitHub error: {e}")
    
    return jobs

GOOGLE_QUERIES = [
    # Location-specific
    '"ai developer" OR "ai engineer" OR "ai intern" site:careers.* OR site:jobs.* Delhi NCR',
    '"gen ai" OR "llm" OR "langchain" hiring Noida OR Gurgaon OR Delhi',
    '"machine learning" intern OR developer Bangalore OR Hyderabad OR Pune 2026',
    '"rag" OR "vector database" OR "langchain" developer India',

    # ATS platform-specific (catches jobs not on LinkedIn)
    'site:lever.co "ai" OR "machine learning" India',
    'site:boards.greenhouse.io "ai" OR "llm" India',
    'site:ashbyhq.com "ai" OR "machine learning" India',

    # Direct career pages
    '"careers" OR "jobs" "ai developer" OR "gen ai" Noida OR Gurgaon OR Delhi 2026',
    '"we are hiring" "ai" OR "ml" OR "llm" Delhi NCR',

    # Startup-specific
    'ai startup hiring India internship 2026',
    '"founding engineer" OR "early engineer" ai India',
]

NAUKRI_FEEDS = [
    "https://www.naukri.com/jobs-in-delhi-ncr?rss=1&keyword=ai+developer",
    "https://www.naukri.com/jobs-in-delhi-ncr?rss=1&keyword=machine+learning",
    "https://www.naukri.com/jobs-in-delhi-ncr?rss=1&keyword=gen+ai",
    "https://www.naukri.com/jobs-in-india?rss=1&keyword=langchain",
    "https://www.naukri.com/jobs-in-india?rss=1&keyword=ai+intern",
]

INDEED_FEEDS = [
    "https://www.indeed.co.in/rss?q=ai+developer&l=Delhi+NCR",
    "https://www.indeed.co.in/rss?q=machine+learning+intern&l=India",
    "https://www.indeed.co.in/rss?q=gen+ai+developer&l=India",
    "https://www.indeed.co.in/rss?q=langchain&l=India",
]


def scrape_google_jobs():
    """Search Google for AI/ML job listings on career pages and ATS platforms.
    Rotates through queries — runs 3-4 per night to avoid rate limits."""
    jobs = []
    if google_search is None:
        print("googlesearch-python not installed — skipping Google scraper.")
        return jobs

    # Pick 3-4 queries based on day of week (rotate across the full list)
    day_index = datetime.now().timetuple().tm_yday  # 1-366
    batch_size = 4
    start = (day_index * batch_size) % len(GOOGLE_QUERIES)
    tonight_queries = []
    for i in range(batch_size):
        tonight_queries.append(GOOGLE_QUERIES[(start + i) % len(GOOGLE_QUERIES)])

    seen_urls = set()

    for query in tonight_queries:
        try:
            import time
            results = list(google_search(query, num_results=10, lang="en"))
            for url in results:
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Extract a meaningful title from the URL
                title = url.split("/")[-1].replace("-", " ").replace("_", " ").title()
                if len(title) < 5:
                    title = url.split("/")[-2].replace("-", " ").title() if len(url.split("/")) > 2 else "Job Listing"

                # Try to extract company from domain
                domain = url.split("//")[-1].split("/")[0]
                company_parts = domain.replace("www.", "").replace("careers.", "").replace("jobs.", "")
                company = company_parts.split(".")[0].title()

                job_data = {
                    "title": title[:150],
                    "company": company,
                    "location": "See listing",
                    "source": "Google Career Search",
                    "url": url,
                    "description": f"Found via: {query[:100]}"
                }

                # Only save if it looks like a job page
                if matches_keywords(title) or matches_keywords(query):
                    jobs.append(job_data)
                    save_scraped_job(**job_data)

            time.sleep(2)  # Be polite between queries
        except Exception as e:
            print(f"Google search error for '{query[:50]}...': {e}")

    return jobs


def scrape_naukri_rss():
    """Parse Naukri RSS feeds for AI/ML jobs in Delhi NCR."""
    jobs = []
    for feed_url in NAUKRI_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"
            })
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")

            for item in items[:15]:  # Cap per feed
                title = item.find("title")
                link = item.find("link")
                desc = item.find("description")

                title_text = title.get_text(strip=True) if title else "Untitled"
                link_text = link.get_text(strip=True) if link else ""
                desc_text = desc.get_text(strip=True) if desc else ""

                if not matches_keywords(title_text) and not matches_keywords(desc_text[:300]):
                    continue

                # Extract company from description if possible
                company = "See Naukri listing"
                company_match = re.search(r"(?:at|by|company:?)\s+([^,\n<]+)", desc_text, re.IGNORECASE)
                if company_match:
                    company = company_match.group(1).strip()[:80]

                job_data = {
                    "title": title_text[:150],
                    "company": company,
                    "location": "Delhi NCR / India",
                    "source": "Naukri RSS",
                    "url": link_text,
                    "description": BeautifulSoup(desc_text[:1000], "html.parser").get_text()[:500]
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
        except Exception as e:
            print(f"Naukri RSS error: {e}")

    return jobs


def scrape_indeed_rss():
    """Parse Indeed India RSS feeds for AI/ML jobs."""
    jobs = []
    for feed_url in INDEED_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"
            })
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")

            for item in items[:15]:
                title = item.find("title")
                link = item.find("link")
                desc = item.find("description")

                title_text = title.get_text(strip=True) if title else "Untitled"
                link_text = link.get_text(strip=True) if link else ""
                desc_text = desc.get_text(strip=True) if desc else ""

                if not matches_keywords(title_text) and not matches_keywords(desc_text[:300]):
                    continue

                # Indeed titles often include company: "Role - Company"
                company = "See Indeed listing"
                if " - " in title_text:
                    parts = title_text.rsplit(" - ", 1)
                    if len(parts) == 2:
                        company = parts[1].strip()[:80]
                        title_text = parts[0].strip()

                job_data = {
                    "title": title_text[:150],
                    "company": company,
                    "location": "India",
                    "source": "Indeed RSS",
                    "url": link_text,
                    "description": BeautifulSoup(desc_text[:1000], "html.parser").get_text()[:500]
                }
                jobs.append(job_data)
                save_scraped_job(**job_data)
        except Exception as e:
            print(f"Indeed RSS error: {e}")

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

def run_all_scrapers():
    """Run all automated scrapers and return combined results."""
    all_jobs = []
    sources_status = {}
    
    print("Scraping Remotive...")
    remotive = scrape_remotive()
    all_jobs.extend(remotive)
    sources_status["Remotive"] = len(remotive)
    
    print("Scraping HN Who's Hiring...")
    hn = scrape_hn_who_is_hiring()
    all_jobs.extend(hn)
    sources_status["HN Who's Hiring"] = len(hn)
    
    print("Scraping Arbeitnow...")
    arbeitnow = scrape_arbeitnow()
    all_jobs.extend(arbeitnow)
    sources_status["Arbeitnow"] = len(arbeitnow)

    print("Searching Google career pages...")
    google = scrape_google_jobs()
    all_jobs.extend(google)
    sources_status["Google Career Search"] = len(google)

    print("Scraping Naukri RSS...")
    naukri = scrape_naukri_rss()
    all_jobs.extend(naukri)
    sources_status["Naukri RSS"] = len(naukri)

    print("Scraping Indeed RSS...")
    indeed = scrape_indeed_rss()
    all_jobs.extend(indeed)
    sources_status["Indeed RSS"] = len(indeed)

    return all_jobs, sources_status

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from tracker import save_scraped_job

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

def scrape_wellfound_search_hint():
    """
    Wellfound doesn't have a public API and scraping it violates TOS.
    Instead, this generates optimized search URLs for manual browsing.
    """
    base = "https://wellfound.com/jobs"
    searches = [
        f"{base}?q=gen+ai&location=India",
        f"{base}?q=machine+learning&location=India",
        f"{base}?q=llm+developer&location=India",
        f"{base}?q=ai+engineer&location=India",
        f"{base}?q=ai+intern&location=India",
    ]
    return searches

def scrape_linkedin_search_urls():
    """
    LinkedIn automation gets accounts banned.
    Instead, generate optimized search URLs for manual browsing.
    """
    base = "https://www.linkedin.com/jobs/search/?"
    searches = []
    queries = [
        "gen ai developer", "llm engineer", "ai ml intern",
        "generative ai", "machine learning engineer india",
        "ai developer intern", "rag developer"
    ]
    for q in queries:
        url = f"{base}keywords={q.replace(' ', '%20')}&location=India&f_AL=true"
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
    
    return all_jobs, sources_status

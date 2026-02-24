"""
Company Research — gather intel on a company using Google search.
Uses googlesearch-python for web search, with Supabase caching.
"""

import time
import re

try:
    from googlesearch import search as gsearch
except ImportError:
    gsearch = None

TECH_KEYWORDS = [
    "python", "langchain", "rag", "llm", "openai", "fastapi", "react",
    "next.js", "kubernetes", "docker", "aws", "gcp", "azure", "terraform",
    "chromadb", "pinecone", "vector database", "pytorch", "tensorflow",
    "kafka", "redis", "postgresql", "mongodb", "graphql", "rest api",
    "machine learning", "deep learning", "nlp", "computer vision",
    "agentic", "generative ai", "automation", "data pipeline",
]


def research_company(company_name, company_domain=None):
    """Gather intel on a company using Google search.

    Returns dict with: company_name, description, recent_news,
    tech_signals, hiring_contact, product_url.
    """
    if gsearch is None:
        return _empty_result(company_name, "googlesearch-python not installed")

    result = {
        "company_name": company_name,
        "description": "",
        "recent_news": "No recent funding news found",
        "tech_signals": [],
        "hiring_contact": {"name": "", "title": "", "linkedin_url": ""},
        "product_url": "",
    }

    try:
        # Search 1: Company description
        desc_results = list(gsearch(
            f'"{company_name}" what does company do product',
            num_results=3, lang="en"
        ))
        if desc_results:
            result["product_url"] = desc_results[0]
            if company_domain is None:
                # Extract domain from first result
                match = re.match(r"https?://(?:www\.)?([^/]+)", desc_results[0])
                if match:
                    company_domain = match.group(1)
            result["description"] = f"See: {desc_results[0]}"
        time.sleep(2)

        # Search 2: Recent funding/news
        news_results = list(gsearch(
            f'"{company_name}" funding OR raised OR series 2025 2026',
            num_results=3, lang="en"
        ))
        if news_results:
            result["recent_news"] = f"See: {news_results[0]}"
        time.sleep(2)

        # Search 3: Tech stack signals
        tech_results = list(gsearch(
            f'"{company_name}" engineering blog OR tech stack OR "we use"',
            num_results=3, lang="en"
        ))
        if tech_results:
            # Scan URLs for tech keywords
            combined = " ".join(tech_results).lower()
            found_tech = [kw for kw in TECH_KEYWORDS if kw in combined]
            result["tech_signals"] = found_tech
        time.sleep(2)

        # Search 4: Hiring decision-maker
        contact_results = list(gsearch(
            f'"{company_name}" CTO OR "engineering manager" OR "head of ai" site:linkedin.com',
            num_results=3, lang="en"
        ))
        if contact_results:
            for url in contact_results:
                if "linkedin.com/in/" in url:
                    # Extract name from URL path
                    path = url.split("linkedin.com/in/")[-1].strip("/")
                    name_guess = path.replace("-", " ").title()
                    result["hiring_contact"] = {
                        "name": name_guess,
                        "title": "Decision Maker",
                        "linkedin_url": url,
                    }
                    break

    except Exception as e:
        print(f"Company research error for {company_name}: {e}")

    return result


def _empty_result(company_name, reason=""):
    return {
        "company_name": company_name,
        "description": reason or "Research unavailable",
        "recent_news": "",
        "tech_signals": [],
        "hiring_contact": {"name": "", "title": "", "linkedin_url": ""},
        "product_url": "",
    }

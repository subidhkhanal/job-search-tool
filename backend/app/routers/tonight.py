from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from scraper import scrape_wellfound_search_hint, scrape_linkedin_search_urls

router = APIRouter()


@router.get("/links")
def manual_links(_user: str = Depends(get_current_user)):
    return {
        "wellfound_urls": scrape_wellfound_search_hint(),
        "linkedin_urls": scrape_linkedin_search_urls(),
    }

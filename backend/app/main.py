import os
import sys

# Add modules directory to path so existing module imports work unchanged
_modules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules")
if _modules_dir not in sys.path:
    sys.path.insert(0, _modules_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import (
    applications,
    auth_router,
    company_research,
    jd_analyzer,
    messages,
    mini_demos,
    profile,
    referrals,
    resume_tailor,
    scraper,
    stats,
    tonight,
)

# Inject env vars from settings so modules read them via os.environ
settings = get_settings()
for key in ("SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY", "JOOBLE_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"):
    val = getattr(settings, key, "")
    if val:
        os.environ[key] = val

app = FastAPI(title="Job Search HQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(scraper.router, prefix="/api/scraped-jobs", tags=["Scraped Jobs"])
app.include_router(tonight.router, prefix="/api/tonight", tags=["Tonight"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(jd_analyzer.router, prefix="/api/analyze", tags=["JD Analyzer"])
app.include_router(resume_tailor.router, prefix="/api/resume-tailor", tags=["Resume Tailor"])
app.include_router(company_research.router, prefix="/api/company-research", tags=["Company Research"])
app.include_router(referrals.router, prefix="/api/referrals", tags=["Referrals"])
app.include_router(mini_demos.router, prefix="/api/demos", tags=["Mini Demos"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])


@app.get("/api/health")
def health():
    return {"status": "ok"}

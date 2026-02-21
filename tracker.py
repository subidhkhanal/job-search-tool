"""
Database layer — Supabase (PostgreSQL) backend.
All other modules import from here. Function signatures and return types
are unchanged from the original SQLite version.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# --- Supabase client (singleton) ---
# Streamlit Cloud → st.secrets | GitHub Actions → os.environ
try:
    import streamlit as st
    _url = st.secrets["SUPABASE_URL"]
    _key = st.secrets["SUPABASE_KEY"]
except Exception:
    _url = os.environ.get("SUPABASE_URL", "")
    _key = os.environ.get("SUPABASE_KEY", "")

supabase = create_client(_url, _key) if _url and _key else None


def _get_client():
    """Return the Supabase client, raising a clear error if not configured."""
    if supabase is None:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "in .streamlit/secrets.toml or environment variables."
        )
    return supabase


def init_db():
    """No-op. Tables are created via Supabase dashboard SQL editor."""
    pass


# ===================== APPLICATION FUNCTIONS =====================

def add_application(company, role, job_type, platform, url="",
                    noc_compatible="Unknown", conversion="N/A",
                    salary="", notes=""):
    db = _get_client()
    today = datetime.now().strftime("%Y-%m-%d")
    follow_up = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    db.table("applications").insert({
        "company": company,
        "role": role,
        "type": job_type,
        "platform": platform,
        "url": url,
        "date_applied": today,
        "follow_up_date": follow_up,
        "noc_compatible": noc_compatible,
        "conversion_potential": conversion,
        "salary_range": salary,
        "notes": notes,
    }).execute()


def update_status(app_id, new_status):
    db = _get_client()
    db.table("applications").update({"status": new_status}).eq("id", app_id).execute()


def get_all_applications():
    db = _get_client()
    resp = db.table("applications").select("*").order("date_applied", desc=True).execute()
    return pd.DataFrame(resp.data)


def get_follow_ups_due():
    db = _get_client()
    today = datetime.now().strftime("%Y-%m-%d")
    resp = (db.table("applications")
            .select("*")
            .lte("follow_up_date", today)
            .eq("status", "Applied")
            .execute())
    return pd.DataFrame(resp.data)


def get_stats():
    db = _get_client()
    resp = db.table("applications").select("status, type, platform").execute()
    df = pd.DataFrame(resp.data)

    stats = {}
    if df.empty:
        stats['total'] = 0
        stats['applied'] = 0
        stats['interviews'] = 0
        stats['offers'] = 0
        stats['rejected'] = 0
        stats['jobs'] = 0
        stats['internships'] = 0
        stats['by_platform'] = []
        stats['response_rates'] = []
        return stats

    stats['total'] = len(df)
    stats['applied'] = len(df[df['status'] == 'Applied'])
    stats['interviews'] = len(df[df['status'] == 'Interview Scheduled'])
    stats['offers'] = len(df[df['status'] == 'Offer'])
    stats['rejected'] = len(df[df['status'] == 'Rejected'])
    stats['jobs'] = len(df[df['type'] == 'Job'])
    stats['internships'] = len(df[df['type'] == 'Internship'])

    # by_platform: list of (platform, count) tuples
    stats['by_platform'] = list(
        df.groupby('platform').size().sort_values(ascending=False).items()
    )

    # response_rates: list of (platform, total, responses) tuples
    response_rates = []
    for platform, group in df.groupby('platform'):
        total = len(group)
        responses = len(group[group['status'].isin(
            ['Interview Scheduled', 'Interviewed', 'Offer']
        )])
        response_rates.append((platform, total, responses))
    stats['response_rates'] = response_rates

    return stats


def delete_application(app_id):
    db = _get_client()
    db.table("applications").delete().eq("id", app_id).execute()


# ===================== SCRAPED JOBS FUNCTIONS =====================

def save_scraped_job(title, company, location, source, url, description="",
                     score=0, noc_verdict="", skill_match=0):
    db = _get_client()
    try:
        db.table("scraped_jobs").upsert({
            "title": title,
            "company": company,
            "location": location,
            "source": source,
            "url": url,
            "description": description,
            "score": score,
            "noc_verdict": noc_verdict or "",
            "skill_match": skill_match,
        }, on_conflict="url", ignore_duplicates=True).execute()
    except Exception:
        pass


def update_scraped_job_analysis(job_id, score, noc_verdict, skill_match):
    """Update a scraped job with analysis results."""
    db = _get_client()
    db.table("scraped_jobs").update({
        "score": score,
        "noc_verdict": noc_verdict,
        "skill_match": skill_match,
    }).eq("id", job_id).execute()


def get_scraped_jobs(source=None):
    db = _get_client()
    query = db.table("scraped_jobs").select("*").eq("dismissed", 0).eq("applied", 0)
    if source:
        query = query.eq("source", source)
    resp = query.order("scraped_at", desc=True).execute()
    return pd.DataFrame(resp.data)


def mark_scraped_job(job_id, action):
    db = _get_client()
    if action == 'applied':
        db.table("scraped_jobs").update({"applied": 1}).eq("id", job_id).execute()
    elif action == 'dismissed':
        db.table("scraped_jobs").update({"dismissed": 1}).eq("id", job_id).execute()


# ===================== ANALYTICS FUNCTIONS =====================

def get_weekly_trend():
    """Get application counts grouped by week, split by type."""
    db = _get_client()
    resp = db.table("applications").select("date_applied, type").order("date_applied").execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return pd.DataFrame()

    df["date_applied"] = pd.to_datetime(df["date_applied"])
    df["week"] = df["date_applied"].dt.isocalendar().week.astype(int)
    df["year"] = df["date_applied"].dt.year

    pivot = df.groupby(["year", "week", "type"]).size().reset_index(name="count")
    pivot["label"] = "W" + pivot["week"].astype(str)
    return pivot


def get_platform_effectiveness():
    """Get total applications and positive responses per platform."""
    db = _get_client()
    resp = db.table("applications").select("platform, status").execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return df

    grouped = df.groupby("platform").apply(
        lambda g: pd.Series({
            "total": len(g),
            "responses": len(g[g["status"].isin(
                ["Interview Scheduled", "Interviewed", "Offer"]
            )]),
        })
    ).reset_index().sort_values("total", ascending=False)
    grouped["rate"] = (grouped["responses"] / grouped["total"] * 100).round(1)
    return grouped


def get_status_funnel():
    """Get counts at each status stage for a funnel view."""
    db = _get_client()
    resp = db.table("applications").select("status").execute()
    df = pd.DataFrame(resp.data)
    stages = [
        "Applied", "Follow-up Sent", "Interview Scheduled",
        "Interviewed", "Offer",
    ]
    counts = {}
    for stage in stages:
        counts[stage] = len(df[df["status"] == stage]) if not df.empty else 0
    return counts


def get_role_analysis():
    """Group applications by role keywords and show conversion rates."""
    db = _get_client()
    resp = db.table("applications").select("role, status").execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        return pd.DataFrame()

    role_keywords = [
        "AI Developer", "AI Engineer", "ML Engineer", "AI Intern",
        "ML Intern", "Python Developer", "Backend Developer",
        "Data Scientist", "NLP", "Automation", "Full Stack",
    ]

    rows = []
    for kw in role_keywords:
        mask = df["role"].str.contains(kw, case=False, na=False)
        subset = df[mask]
        if len(subset) == 0:
            continue
        total = len(subset)
        responses = len(
            subset[subset["status"].isin(
                ["Interview Scheduled", "Interviewed", "Offer"]
            )]
        )
        rate = round(responses / total * 100, 1) if total > 0 else 0
        rows.append({
            "Role Keyword": kw,
            "Applied": total,
            "Responses": responses,
            "Response Rate": f"{rate}%",
        })

    return pd.DataFrame(rows)


# ===================== WATCHLIST FUNCTIONS =====================

def add_to_watchlist(company_name, career_url, platform_type="custom", company_slug=""):
    db = _get_client()
    try:
        db.table("watchlist").insert({
            "company_name": company_name,
            "career_url": career_url,
            "platform_type": platform_type,
            "company_slug": company_slug,
        }).execute()
    except Exception:
        pass


def remove_from_watchlist(company_id):
    db = _get_client()
    db.table("watchlist_jobs").delete().eq("watchlist_id", company_id).execute()
    db.table("watchlist").delete().eq("id", company_id).execute()


def get_watchlist():
    db = _get_client()
    resp = (db.table("watchlist")
            .select("*")
            .eq("active", 1)
            .order("company_name")
            .execute())
    return pd.DataFrame(resp.data)


def save_watchlist_job(watchlist_id, job_title, job_url):
    db = _get_client()
    try:
        db.table("watchlist_jobs").upsert({
            "watchlist_id": watchlist_id,
            "job_title": job_title,
            "job_url": job_url,
        }, on_conflict="job_url", ignore_duplicates=True).execute()
    except Exception:
        pass


def get_new_watchlist_jobs():
    db = _get_client()
    resp = (db.table("watchlist_jobs")
            .select("*, watchlist(company_name, career_url)")
            .eq("is_new", 1)
            .order("first_seen", desc=True)
            .execute())
    data = resp.data
    for row in data:
        wl = row.pop("watchlist", {}) or {}
        row["company_name"] = wl.get("company_name", "")
        row["career_url"] = wl.get("career_url", "")
    return pd.DataFrame(data)


def mark_watchlist_job_seen(job_id):
    db = _get_client()
    db.table("watchlist_jobs").update({"is_new": 0}).eq("id", job_id).execute()


def update_watchlist_checked(watchlist_id):
    db = _get_client()
    db.table("watchlist").update({
        "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }).eq("id", watchlist_id).execute()

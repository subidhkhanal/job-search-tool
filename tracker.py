"""
Database layer — Supabase (PostgreSQL) backend.
All other modules import from here. Function signatures and return types
are unchanged from the original SQLite version.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

# --- Supabase client (lazy singleton) ---
_supabase_client = None


def _get_client():
    """Return the Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    # Streamlit Cloud → st.secrets | GitHub Actions → os.environ
    _url = ""
    _key = ""
    try:
        import streamlit as st
        _url = st.secrets["SUPABASE_URL"]
        _key = st.secrets["SUPABASE_KEY"]
    except Exception:
        _url = os.environ.get("SUPABASE_URL", "")
        _key = os.environ.get("SUPABASE_KEY", "")

    if not _url or not _key:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "in .streamlit/secrets.toml or environment variables."
        )

    _supabase_client = create_client(_url, _key)
    return _supabase_client


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

def get_existing_job_urls():
    """Get all URLs already in scraped_jobs table for deduplication."""
    try:
        db = _get_client()
        resp = db.table("scraped_jobs").select("url").execute()
        return {row["url"] for row in resp.data} if resp.data else set()
    except Exception:
        return set()


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


# ===================== REFERRAL FUNCTIONS =====================

def add_referral(contact_name, company, contact_role="", relationship="",
                 linkedin_url="", email="", notes=""):
    db = _get_client()
    today = datetime.now().strftime("%Y-%m-%d")
    follow_up = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    try:
        db.table("referrals").insert({
            "contact_name": contact_name,
            "company": company,
            "contact_role": contact_role,
            "relationship": relationship,
            "linkedin_url": linkedin_url,
            "email": email,
            "status": "Identified",
            "last_contacted": today,
            "follow_up_date": follow_up,
            "notes": notes,
        }).execute()
    except Exception:
        raise RuntimeError("referrals table not found. Create it in Supabase first.")


def update_referral_status(referral_id, new_status):
    db = _get_client()
    update_data = {"status": new_status}
    if new_status == "Contacted":
        today = datetime.now().strftime("%Y-%m-%d")
        follow_up = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        update_data["last_contacted"] = today
        update_data["follow_up_date"] = follow_up
    try:
        db.table("referrals").update(update_data).eq("id", referral_id).execute()
    except Exception:
        raise RuntimeError("referrals table not found. Create it in Supabase first.")


def get_referral_follow_ups_due():
    try:
        db = _get_client()
        today = datetime.now().strftime("%Y-%m-%d")
        terminal = ["Referral Given", "Applied via Referral", "Interview", "Offer"]
        resp = (db.table("referrals")
                .select("*")
                .lte("follow_up_date", today)
                .execute())
        df = pd.DataFrame(resp.data)
        if df.empty:
            return df
        return df[~df["status"].isin(terminal)]
    except Exception:
        return pd.DataFrame()


def get_referral_stats():
    stats = {
        "total": 0,
        "by_status": {},
        "referral_interview_rate": 0,
    }
    try:
        db = _get_client()
        resp = db.table("referrals").select("status").execute()
        df = pd.DataFrame(resp.data)
        if df.empty:
            return stats
        stats["total"] = len(df)
        stats["by_status"] = dict(df["status"].value_counts())
        referred = len(df[df["status"].isin(["Referral Given", "Applied via Referral", "Interview", "Offer"])])
        interviews = len(df[df["status"].isin(["Interview", "Offer"])])
        stats["referral_interview_rate"] = round(interviews / referred * 100, 1) if referred > 0 else 0
    except Exception:
        pass
    return stats


def get_referrals_by_company(company):
    try:
        db = _get_client()
        resp = (db.table("referrals")
                .select("*")
                .ilike("company", f"%{company}%")
                .execute())
        return pd.DataFrame(resp.data)
    except Exception:
        return pd.DataFrame()


# ===================== COMPANY RESEARCH CACHE =====================

def get_cached_research(company_name):
    db = _get_client()
    resp = (db.table("company_research_cache")
            .select("*")
            .ilike("company_name", company_name)
            .execute())
    if not resp.data:
        return None
    row = resp.data[0]
    # Check staleness (14 days)
    researched = row.get("researched_at", "")
    if researched:
        try:
            from dateutil.parser import parse as parse_dt
            dt = parse_dt(researched)
            if (datetime.now(dt.tzinfo) - dt).days > 14:
                return None  # stale
        except Exception:
            pass
    return row


def save_research_cache(company_name, research_data):
    db = _get_client()
    import json
    db.table("company_research_cache").upsert({
        "company_name": company_name,
        "description": research_data.get("description", ""),
        "recent_news": research_data.get("recent_news", ""),
        "tech_signals": json.dumps(research_data.get("tech_signals", [])),
        "hiring_contact_name": research_data.get("hiring_contact", {}).get("name", ""),
        "hiring_contact_title": research_data.get("hiring_contact", {}).get("title", ""),
        "hiring_contact_linkedin": research_data.get("hiring_contact", {}).get("linkedin_url", ""),
        "product_url": research_data.get("product_url", ""),
    }, on_conflict="company_name").execute()


# ===================== MINI DEMO FUNCTIONS =====================

def add_mini_demo(company, role, demo_idea):
    db = _get_client()
    try:
        db.table("mini_demos").insert({
            "company": company,
            "role": role,
            "demo_idea": demo_idea,
            "status": "Idea",
            "hours_spent": 0,
        }).execute()
    except Exception:
        raise RuntimeError("mini_demos table not found. Create it in Supabase first.")


def update_mini_demo(demo_id, **kwargs):
    """Update mini demo fields. Pass any of: status, github_url, demo_url, hours_spent, result."""
    db = _get_client()
    allowed = {"status", "github_url", "demo_url", "hours_spent", "result"}
    update_data = {k: v for k, v in kwargs.items() if k in allowed}
    if update_data:
        try:
            db.table("mini_demos").update(update_data).eq("id", demo_id).execute()
        except Exception:
            raise RuntimeError("mini_demos table not found. Create it in Supabase first.")


def get_active_demos():
    try:
        db = _get_client()
        resp = (db.table("mini_demos")
                .select("*")
                .in_("status", ["Idea", "Building", "Deployed"])
                .order("created_at", desc=True)
                .execute())
        return pd.DataFrame(resp.data)
    except Exception:
        return pd.DataFrame()


def get_demo_results():
    try:
        db = _get_client()
        resp = db.table("mini_demos").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(resp.data)
    except Exception:
        return pd.DataFrame()


# ===================== EMAIL LOG FUNCTIONS =====================

def save_email_log(subject, markdown_content, html_content, jobs_count=0,
                   sources_summary=None, email_sent=False):
    """Save a sent email log to Supabase so the frontend can display it."""
    db = _get_client()
    import json
    try:
        db.table("email_logs").insert({
            "subject": subject,
            "markdown_content": markdown_content,
            "html_content": html_content,
            "jobs_count": jobs_count,
            "sources_summary": json.dumps(sources_summary or {}),
            "email_sent": email_sent,
        }).execute()
    except Exception as e:
        print(f"Failed to save email log: {e}")


def get_email_logs(limit=20):
    """Get recent email logs, newest first."""
    try:
        db = _get_client()
        resp = (db.table("email_logs")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute())
        return resp.data or []
    except Exception:
        return []


def get_email_log(log_id):
    """Get a single email log by ID."""
    try:
        db = _get_client()
        resp = (db.table("email_logs")
                .select("*")
                .eq("id", log_id)
                .single()
                .execute())
        return resp.data
    except Exception:
        return None

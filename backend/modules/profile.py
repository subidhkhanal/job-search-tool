"""
Profile data layer — stores and retrieves user profile data from Supabase.
Other modules import from here to get dynamic profile/skills/projects instead
of using hardcoded values.
"""

import os
from datetime import datetime

# --- Supabase client (reuse from tracker) ---
_supabase_client = None


def _get_client():
    """Return the Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    from supabase import create_client

    _url = os.environ.get("SUPABASE_URL", "")
    _key = os.environ.get("SUPABASE_KEY", "")

    if not _url or not _key:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )

    _supabase_client = create_client(_url, _key)
    return _supabase_client


# ===================== PROFILE CRUD =====================

def get_profile(username="subidh"):
    """Get full profile dict from Supabase. Returns None if not found."""
    try:
        db = _get_client()
        result = db.table("user_profile").select("*").eq("username", username).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        print(f"[profile] get_profile failed: {e}")
    return None


def upsert_profile(username="subidh", data=None):
    """Create or update a user profile. Returns the saved row."""
    if data is None:
        data = {}
    db = _get_client()
    payload = {**data, "username": username, "updated_at": datetime.now().isoformat()}
    # Remove id if present to avoid conflicts
    payload.pop("id", None)

    result = db.table("user_profile").upsert(
        payload, on_conflict="username"
    ).execute()
    return result.data[0] if result.data else None


# ===================== HELPER ACCESSORS =====================

def get_profile_text(username="subidh"):
    """Build an LLM-ready profile summary from DB data.
    Falls back to None if profile not found (caller should use hardcoded default).
    """
    profile = get_profile(username)
    if not profile:
        return None

    lines = []

    # Experience
    experience = profile.get("experience") or []
    for exp in experience:
        role = exp.get("role", "")
        company = exp.get("company", "")
        period = exp.get("period", "")
        desc = exp.get("description", "")
        lines.append(f"- {role} at {company} ({period}): {desc}")

    # Education
    education = profile.get("education", "")
    if education:
        lines.append(f"- {education}")

    # Projects
    projects = profile.get("projects") or []
    for proj in projects:
        name = proj.get("name", "")
        desc = proj.get("description", "")
        lines.append(f"- Built {name}: {desc}")

    # Skills
    skills = profile.get("skills") or []
    if skills:
        lines.append(f"- Tech stack: {', '.join(skills)}")

    # Location & target
    location = profile.get("location_preference", "")
    if location:
        lines.append(f"- Location preference: {location}")

    target_roles = profile.get("target_roles") or []
    if target_roles:
        lines.append(f"- Looking for: {', '.join(target_roles)}")

    return "\n".join(lines) if lines else None


def get_resume_text(username="subidh"):
    """Get the full resume text for ATS checks. Falls back to None."""
    profile = get_profile(username)
    if not profile:
        return None

    resume_text = profile.get("resume_text", "")
    if resume_text and resume_text.strip():
        return resume_text

    # Build from structured data if no raw resume text
    parts = []

    skills = profile.get("skills") or []
    if skills:
        parts.append(f"SKILLS: {', '.join(skills)}")

    profile_text = get_profile_text(username)
    if profile_text:
        parts.append(f"PROFILE:\n{profile_text}")

    projects = profile.get("projects") or []
    if projects:
        project_lines = []
        for p in projects:
            name = p.get("name", "")
            desc = p.get("description", "")
            kws = p.get("keywords") or []
            project_lines.append(f"{name}: {desc}. Keywords: {', '.join(kws)}")
        parts.append("PROJECTS:\n" + "\n".join(project_lines))

    education = profile.get("education", "")
    if education:
        parts.append(f"EDUCATION:\n{education}")

    return "\n\n".join(parts) if parts else None


def get_projects(username="subidh"):
    """Get projects dict in the same shape as resume_tailor.PROJECTS.
    Returns None if not found (caller should use hardcoded default).
    """
    profile = get_profile(username)
    if not profile:
        return None

    projects = profile.get("projects") or []
    if not projects:
        return None

    result = {}
    for p in projects:
        name = p.get("name", "")
        if name:
            result[name] = {
                "keywords": p.get("keywords", []),
                "one_liner": p.get("description", ""),
            }
    return result if result else None


def get_skills(username="subidh"):
    """Get skills list in the same shape as resume_tailor.RESUME_SKILLS.
    Returns None if not found.
    """
    profile = get_profile(username)
    if not profile:
        return None

    skills = profile.get("skills") or []
    return skills if skills else None


def get_blocked_companies(username="subidh"):
    """Get set of blocked company names (lowercased). Returns None if not found."""
    profile = get_profile(username)
    if not profile:
        return None

    blocked = profile.get("blocked_companies") or []
    return {c.strip().lower() for c in blocked} if blocked else None


def get_scoring_weights(username="subidh"):
    """Get custom scoring weights. Returns None if not found."""
    profile = get_profile(username)
    if not profile:
        return None

    weights = profile.get("scoring_weights") or {}
    return weights if weights else None

from pydantic import BaseModel
from typing import Optional


# ---- Profile ----

class ProjectEntry(BaseModel):
    name: str = ""
    description: str = ""
    keywords: list[str] = []


class ExperienceEntry(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


class UserProfileRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[list[str]] = None
    projects: Optional[list[ProjectEntry]] = None
    experience: Optional[list[ExperienceEntry]] = None
    education: Optional[str] = None
    location_preference: Optional[str] = None
    target_roles: Optional[list[str]] = None
    resume_text: Optional[str] = None
    blocked_companies: Optional[list[str]] = None
    scoring_weights: Optional[dict] = None


class UserProfileResponse(BaseModel):
    id: Optional[int] = None
    username: str = "subidh"
    full_name: str = ""
    bio: str = ""
    skills: list[str] = []
    projects: list[ProjectEntry] = []
    experience: list[ExperienceEntry] = []
    education: str = ""
    location_preference: str = ""
    target_roles: list[str] = []
    resume_text: str = ""
    blocked_companies: list[str] = []
    scoring_weights: dict = {}
    updated_at: Optional[str] = None


# ---- Applications ----

class AddApplicationRequest(BaseModel):
    company: str
    role: str
    job_type: str = "Job"
    platform: str = ""
    url: str = ""
    noc_compatible: str = "Unknown"
    conversion: str = "N/A"
    salary: str = ""
    notes: str = ""


class UpdateStatusRequest(BaseModel):
    status: str


class UpdateNotesRequest(BaseModel):
    notes: str


class SnoozeRequest(BaseModel):
    new_date: str


# ---- Scraped Jobs ----

class MarkScrapedJobRequest(BaseModel):
    action: str  # "applied" or "dismissed"


# ---- Messages ----

class ColdDMRequest(BaseModel):
    company: str
    role: str
    company_desc: str = ""
    platform: str = "LinkedIn"
    project_link: str = ""


class FollowUpRequest(BaseModel):
    company: str
    role: str
    days: int = 7
    platform: str = "LinkedIn"
    follow_up_number: int = 1
    previous_messages: list[str] = []


class CoverLetterRequest(BaseModel):
    company: str
    role: str
    jd: str
    company_info: str = ""


class ThankYouRequest(BaseModel):
    company: str
    interviewer: str
    discussion: str = ""


class ReferralRequestBody(BaseModel):
    contact_name: str
    contact_role: str = ""
    company: str
    role_applying_for: str
    relationship: str = ""


class DemoOutreachRequest(BaseModel):
    company: str
    role: str
    demo_url: str
    demo_description: str
    company_desc: str = ""


# ---- JD Analyzer ----

class FullAnalyzeRequest(BaseModel):
    title: str
    description: str
    company: Optional[str] = None
    custom_resume: Optional[str] = None


class ATSCheckRequest(BaseModel):
    jd_text: str
    custom_resume: Optional[str] = None


# ---- Resume Tailor ----

class ResumeTailorRequest(BaseModel):
    title: str
    jd_text: str


# ---- Company Research ----

class CompanyResearchRequest(BaseModel):
    company_name: str


# ---- Referrals ----

class AddReferralRequest(BaseModel):
    contact_name: str
    company: str
    contact_role: str = ""
    relationship: str = ""
    linkedin_url: str = ""
    email: str = ""
    notes: str = ""


class UpdateReferralStatusRequest(BaseModel):
    status: str


# ---- Follow-up History ----

class LogFollowUpRequest(BaseModel):
    entity_type: str   # "application" or "referral"
    entity_id: int
    message_content: str = ""
    channel: str = ""


class UpdateFollowUpOutcomeRequest(BaseModel):
    outcome: str       # "pending", "responded", "no_response"


# ---- Mini Demos ----

class AddDemoRequest(BaseModel):
    company: str
    role: str
    demo_idea: str


class UpdateDemoRequest(BaseModel):
    status: Optional[str] = None
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    hours_spent: Optional[float] = None
    result: Optional[str] = None


# ---- Push Subscriptions ----

class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict

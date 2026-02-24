// ---- Auth ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ---- Applications ----
export interface Application {
  id: number;
  company: string;
  role: string;
  type: string;
  platform: string;
  url: string;
  noc_compatible: string;
  conversion: string;
  salary: string;
  notes: string;
  status: string;
  date_applied?: string;
  follow_up_date?: string;
}

export interface AddApplicationRequest {
  company: string;
  role: string;
  job_type?: string;
  platform?: string;
  url?: string;
  noc_compatible?: string;
  conversion?: string;
  salary?: string;
  notes?: string;
}

// ---- Dashboard / Stats ----
export interface DashboardStats {
  total: number;
  applied: number;
  interview: number;
  offer: number;
  rejected: number;
  this_week: number;
  [key: string]: number;
}

export interface FollowUp {
  id: number;
  company: string;
  role: string;
  follow_up_date: string;
  status: string;
  platform?: string;
}

export interface WeeklyTrend {
  week: string;
  Job?: number;
  Internship?: number;
  total: number;
  [key: string]: string | number | undefined;
}

export interface PlatformEffectiveness {
  platform: string;
  applications: number;
  responses: number;
  response_rate: number;
}

export interface StatusFunnel {
  [status: string]: number;
}

export interface RoleAnalysis {
  role_keyword: string;
  applied: number;
  responses: number;
  response_rate: number;
}

// ---- Scraped Jobs ----
export interface ScrapedJob {
  id?: number;
  title: string;
  company: string;
  location: string;
  source: string;
  url: string;
  description: string;
  score: number;
  work_mode?: string;
  llm_reason?: string;
  verdict?: string;
  ats_score?: number;
  skill_match?: number;
  noc_verdict?: string;
}

// ---- Messages ----
export interface ColdDMRequest {
  company: string;
  role: string;
  company_desc?: string;
  platform?: string;
  project_link?: string;
}

export interface FollowUpRequest {
  company: string;
  role: string;
  days?: number;
  platform?: string;
}

export interface CoverLetterRequest {
  company: string;
  role: string;
  jd: string;
  company_info?: string;
}

export interface ThankYouRequest {
  company: string;
  interviewer: string;
  discussion?: string;
}

export interface ReferralRequestBody {
  contact_name: string;
  contact_role?: string;
  company: string;
  role_applying_for: string;
  relationship?: string;
}

export interface DemoOutreachRequest {
  company: string;
  role: string;
  demo_url: string;
  demo_description: string;
  company_desc?: string;
}

export interface MessageResponse {
  content: string;
}

// ---- JD Analyzer ----
export interface FullAnalyzeRequest {
  title: string;
  description: string;
  company?: string;
  custom_resume?: string;
}

export interface ATSCheckRequest {
  jd_text: string;
  custom_resume?: string;
}

export interface ATSResult {
  ats_score: number;
  found_keywords: string[];
  missing_keywords: string[];
  suggestions: string[];
  experience_req?: string;
  degree_req?: string;
}

export interface AnalysisResult {
  verdict_label?: string;
  verdict_reason?: string;
  noc?: {
    code: string;
    title: string;
    confidence: string;
    matched_duties: string[];
    message: string;
  };
  skills?: {
    matched: string[];
    gaps: string[];
    match_pct: number;
  };
  red_flags?: Array<{
    type: string;
    message: string;
  }>;
  ats?: ATSResult;
  company_intel?: CompanyIntel;
}

// ---- Resume Tailor ----
export interface ResumeTailorRequest {
  title: string;
  jd_text: string;
}

export interface ResumeTailorResult {
  projects: Array<{
    name: string;
    matches: number;
    keywords: string[];
    one_liner: string;
  }> | string[];
  skills: string[];
  gaps: Array<{
    skill: string;
    difficulty: string;
    emoji: string;
    note: string;
  }> | string[];
  summaries: string[];
}

// ---- Company Research ----
export interface CompanyIntel {
  description?: string;
  recent_news?: string;
  tech_signals?: string[];
  hiring_contact?: {
    name?: string;
    title?: string;
    linkedin?: string;
  };
  product_url?: string;
  [key: string]: unknown;
}

// ---- Referrals ----
export interface Referral {
  id: number;
  contact_name: string;
  company: string;
  contact_role: string;
  relationship: string;
  linkedin_url: string;
  email: string;
  notes: string;
  status: string;
  last_contacted?: string;
  follow_up_date?: string;
}

export interface AddReferralRequest {
  contact_name: string;
  company: string;
  contact_role?: string;
  relationship?: string;
  linkedin_url?: string;
  email?: string;
  notes?: string;
}

export interface ReferralStats {
  total: number;
  requested: number;
  received: number;
  interview_rate: number;
  follow_ups_due: number;
  [key: string]: number;
}

// ---- Mini Demos ----
export interface MiniDemo {
  id: number;
  company: string;
  role: string;
  demo_idea: string;
  status: string;
  github_url?: string;
  demo_url?: string;
  hours_spent?: number;
  result?: string;
}

export interface AddDemoRequest {
  company: string;
  role: string;
  demo_idea: string;
}

export interface UpdateDemoRequest {
  status?: string;
  github_url?: string;
  demo_url?: string;
  hours_spent?: number;
  result?: string;
}

// ---- Profile ----
export interface ProjectEntry {
  name: string;
  description: string;
  keywords: string[];
}

export interface ExperienceEntry {
  role: string;
  company: string;
  period: string;
  description: string;
}

export interface UserProfile {
  id?: number;
  username: string;
  full_name: string;
  bio: string;
  skills: string[];
  projects: ProjectEntry[];
  experience: ExperienceEntry[];
  education: string;
  location_preference: string;
  target_roles: string[];
  resume_text: string;
  blocked_companies: string[];
  scoring_weights: Record<string, unknown>;
  updated_at?: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  bio?: string;
  skills?: string[];
  projects?: ProjectEntry[];
  experience?: ExperienceEntry[];
  education?: string;
  location_preference?: string;
  target_roles?: string[];
  resume_text?: string;
  blocked_companies?: string[];
  scoring_weights?: Record<string, unknown>;
}

import type {
  AddApplicationRequest,
  AddDemoRequest,
  AddReferralRequest,
  AnalysisResult,
  Application,
  ATSCheckRequest,
  ATSResult,
  ColdDMRequest,
  CompanyIntel,
  CoverLetterRequest,
  DashboardStats,
  DemoOutreachRequest,
  FollowUp,
  FollowUpRequest,
  FullAnalyzeRequest,
  MessageResponse,
  MiniDemo,
  PlatformEffectiveness,
  Referral,
  ReferralRequestBody,
  ReferralStats,
  ResumeTailorRequest,
  ResumeTailorResult,
  RoleAnalysis,
  ScrapedJob,
  StatusFunnel,
  ThankYouRequest,
  TokenResponse,
  UpdateDemoRequest,
  UserProfile,
  UserProfileUpdate,
  WeeklyTrend,
  AppNotification,
  UnreadCountResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed: ${res.status}`);
  }

  return res.json();
}

// ---- Auth ----
export async function login(username: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

// ---- Applications ----
export async function getApplications(filters?: {
  status?: string;
  type?: string;
  platform?: string;
}): Promise<Application[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.type) params.set("type", filters.type);
  if (filters?.platform) params.set("platform", filters.platform);
  const qs = params.toString();
  return apiFetch<Application[]>(`/api/applications${qs ? `?${qs}` : ""}`);
}

export async function createApplication(data: AddApplicationRequest) {
  return apiFetch<{ success: boolean }>("/api/applications", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateApplicationStatus(id: number, status: string) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function updateApplicationNotes(id: number, notes: string) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}/notes`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

export async function deleteApplication(id: number) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}`, {
    method: "DELETE",
  });
}

// ---- Stats ----
export async function getDashboard(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/api/stats/dashboard");
}

export async function getFollowUps(): Promise<FollowUp[]> {
  return apiFetch<FollowUp[]>("/api/stats/follow-ups");
}

export async function getWeeklyTrend(): Promise<WeeklyTrend[]> {
  return apiFetch<WeeklyTrend[]>("/api/stats/weekly-trend");
}

export async function getPlatformEffectiveness(): Promise<PlatformEffectiveness[]> {
  return apiFetch<PlatformEffectiveness[]>("/api/stats/platform-effectiveness");
}

export async function getStatusFunnel(): Promise<StatusFunnel> {
  return apiFetch<StatusFunnel>("/api/stats/status-funnel");
}

export async function getRoleAnalysis(): Promise<RoleAnalysis[]> {
  return apiFetch<RoleAnalysis[]>("/api/stats/role-analysis");
}

// ---- Scraper ----
export async function getScrapedJobs(source?: string): Promise<ScrapedJob[]> {
  const qs = source ? `?source=${encodeURIComponent(source)}` : "";
  return apiFetch<ScrapedJob[]>(`/api/scraped-jobs${qs}`);
}

export async function markScrapedJob(id: number, action: string) {
  return apiFetch<{ success: boolean }>(`/api/scraped-jobs/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ action }),
  });
}

// ---- Messages ----
export async function generateColdDM(data: ColdDMRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/cold-dm", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateFollowUp(data: FollowUpRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/follow-up", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateCoverLetter(data: CoverLetterRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/cover-letter", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateThankYou(data: ThankYouRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/thank-you", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateReferralRequest(data: ReferralRequestBody): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/referral-request", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateDemoOutreach(data: DemoOutreachRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/demo-outreach", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---- JD Analyzer ----
export async function analyzeFullJD(data: FullAnalyzeRequest): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>("/api/analyze/full", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function checkATS(data: ATSCheckRequest): Promise<ATSResult> {
  return apiFetch<ATSResult>("/api/analyze/ats", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---- Resume Tailor ----
export async function tailorResume(data: ResumeTailorRequest): Promise<ResumeTailorResult> {
  return apiFetch<ResumeTailorResult>("/api/resume-tailor/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---- Company Research ----
export async function researchCompany(companyName: string): Promise<CompanyIntel> {
  return apiFetch<CompanyIntel>("/api/company-research/", {
    method: "POST",
    body: JSON.stringify({ company_name: companyName }),
  });
}

// ---- Referrals ----
export async function getReferrals(company?: string): Promise<Referral[]> {
  const qs = company ? `?company=${encodeURIComponent(company)}` : "";
  return apiFetch<Referral[]>(`/api/referrals${qs}`);
}

export async function createReferral(data: AddReferralRequest) {
  return apiFetch<{ success: boolean }>("/api/referrals", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateReferralStatus(id: number, status: string) {
  return apiFetch<{ success: boolean }>(`/api/referrals/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function getReferralStats(): Promise<ReferralStats> {
  return apiFetch<ReferralStats>("/api/referrals/stats");
}

export async function getReferralFollowUps(): Promise<Referral[]> {
  return apiFetch<Referral[]>("/api/referrals/follow-ups");
}

// ---- Mini Demos ----
export async function getDemos(activeOnly = true): Promise<MiniDemo[]> {
  return apiFetch<MiniDemo[]>(`/api/demos?active_only=${activeOnly}`);
}

export async function createDemo(data: AddDemoRequest) {
  return apiFetch<{ success: boolean }>("/api/demos", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateDemo(id: number, data: UpdateDemoRequest) {
  return apiFetch<{ success: boolean }>(`/api/demos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ---- Profile ----
export async function getProfile(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/profile/");
}

export async function updateProfile(data: UserProfileUpdate): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/profile/", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ---- Notifications ----
export async function getNotifications(unreadOnly = false): Promise<AppNotification[]> {
  const qs = unreadOnly ? "?unread_only=true" : "";
  return apiFetch<AppNotification[]>(`/api/notifications${qs}`);
}

export async function getUnreadCount(): Promise<UnreadCountResponse> {
  return apiFetch<UnreadCountResponse>("/api/notifications/unread-count");
}

export async function markNotificationRead(id: number) {
  return apiFetch<{ success: boolean }>(`/api/notifications/${id}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead() {
  return apiFetch<{ success: boolean }>("/api/notifications/mark-all-read", {
    method: "POST",
  });
}

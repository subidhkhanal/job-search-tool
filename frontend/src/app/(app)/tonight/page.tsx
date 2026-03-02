"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getScrapedJobs, getFollowUps, createApplication, markScrapedJob } from "@/lib/api";
import type { ScrapedJob, FollowUp } from "@/lib/types";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Loader2,
  ExternalLink,
  ClipboardPlus,
  Building2,
  MapPin,
  AlertTriangle,
  Check,
  FileSearch,
  MessageSquare,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function scoreBadgeColor(score: number) {
  if (score >= 60) return "bg-emerald-600 text-white";
  if (score >= 30) return "bg-yellow-500 text-black";
  return "bg-red-600 text-white";
}

function workModeBadgeColor(mode: string | undefined) {
  const m = (mode ?? "").toLowerCase();
  if (m === "remote") return "bg-emerald-600/15 text-emerald-400 border-emerald-600/30";
  if (m === "hybrid") return "bg-blue-600/15 text-blue-400 border-blue-600/30";
  return "bg-orange-600/15 text-orange-400 border-orange-600/30";
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------
export default function TonightPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<ScrapedJob[]>([]);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loggedJobs, setLoggedJobs] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<"score" | "source" | "company">("score");
  const [filterMode, setFilterMode] = useState<"all" | "remote" | "hybrid" | "onsite">("all");

  const filteredJobs = useMemo(() => {
    let filtered = [...jobs];
    if (filterMode !== "all") {
      filtered = filtered.filter(
        (j) => (j.work_mode || "").toLowerCase() === filterMode
      );
    }
    filtered.sort((a, b) => {
      if (sortBy === "score") return (b.score || 0) - (a.score || 0);
      if (sortBy === "company") return (a.company || "").localeCompare(b.company || "");
      if (sortBy === "source") return (a.source || "").localeCompare(b.source || "");
      return 0;
    });
    return filtered;
  }, [jobs, sortBy, filterMode]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [jobsData, followUpsData] = await Promise.all([
        getScrapedJobs(),
        getFollowUps(),
      ]);
      setJobs(jobsData);
      setFollowUps(followUpsData);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ------- Log to tracker handler -------
  const handleLog = useCallback(async (job: ScrapedJob) => {
    const key = `${job.company}::${job.title}`;
    try {
      await createApplication({
        company: job.company,
        role: job.title,
        platform: job.source,
        url: job.url,
      });
      if (job.id) await markScrapedJob(job.id, "applied");
      setLoggedJobs((prev) => new Set(prev).add(key));
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      toast.success(`Logged ${job.company} - ${job.title} to tracker`);
    } catch {
      toast.error("Failed to log application");
    }
  }, []);

  // ------- Dismiss handler -------
  const handleDismiss = useCallback(async (job: ScrapedJob) => {
    try {
      if (job.id) await markScrapedJob(job.id, "dismissed");
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      toast.success(`Dismissed ${job.company} - ${job.title}`);
    } catch {
      toast.error("Failed to dismiss job");
    }
  }, []);

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Today Todo
          </h1>
          <p className="text-muted-foreground mt-1">
            Latest scraped jobs and follow-ups for your application list.
          </p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      {/* ---- Loading State ---- */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && (
        <>
          {/* ---- Section 1: Follow-ups Due ---- */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                Follow-ups Due
              </CardTitle>
              <CardDescription>
                Applications that need a follow-up soon.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {followUps.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No follow-ups due. You&apos;re all caught up!
                </p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {followUps.map((fu) => (
                    <div
                      key={fu.id}
                      className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 space-y-2"
                    >
                      <p className="font-semibold">{fu.company}</p>
                      <p className="text-muted-foreground text-sm">
                        {fu.role}
                      </p>
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-xs text-amber-400">
                          {fu.follow_up_date}
                        </span>
                        <span className="text-muted-foreground text-xs capitalize">
                          {fu.status}
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full mt-1"
                        onClick={() => {
                          const params = new URLSearchParams({
                            company: fu.company,
                            role: fu.role,
                            type: "follow-up",
                          });
                          router.push(`/messages?${params.toString()}`);
                        }}
                      >
                        <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
                        Write Follow-up
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Separator />

          {/* ---- Section 2: Scraped Jobs ---- */}
          <div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
              <h2 className="text-2xl font-semibold tracking-tight">
                Latest Scraped Jobs
                {jobs.length > 0 && (
                  <span className="text-muted-foreground text-base font-normal ml-2">
                    ({filteredJobs.length}{filterMode !== "all" ? ` of ${jobs.length}` : ""})
                  </span>
                )}
              </h2>
              {jobs.length > 0 && (
                <div className="flex gap-2">
                  <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
                    <SelectTrigger className="w-[130px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="score">Sort: Score</SelectItem>
                      <SelectItem value="company">Sort: Company</SelectItem>
                      <SelectItem value="source">Sort: Source</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={filterMode} onValueChange={(v) => setFilterMode(v as typeof filterMode)}>
                    <SelectTrigger className="w-[130px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Modes</SelectItem>
                      <SelectItem value="remote">Remote</SelectItem>
                      <SelectItem value="hybrid">Hybrid</SelectItem>
                      <SelectItem value="onsite">Onsite</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            {jobs.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No scraped jobs yet. Jobs are fetched automatically every hour
                via GitHub Actions.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {filteredJobs.map((job, idx) => {
                  const key = `${job.company}::${job.title}`;
                  const isLogged = loggedJobs.has(key);

                  return (
                    <Card key={job.id ?? idx} className="flex flex-col">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <CardTitle className="text-base leading-snug">
                              {job.title}
                            </CardTitle>
                            <div className="mt-1 flex items-center gap-1.5 text-sm font-semibold">
                              <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                              {job.company}
                            </div>
                          </div>
                          {job.score > 0 && (
                            <Badge
                              className={cn(
                                "shrink-0 tabular-nums",
                                scoreBadgeColor(job.score)
                              )}
                            >
                              {job.score}
                            </Badge>
                          )}
                        </div>
                      </CardHeader>

                      <CardContent className="flex flex-1 flex-col gap-3 pt-0">
                        {/* Location */}
                        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                          <MapPin className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">
                            {job.location || "Not specified"}
                          </span>
                        </div>

                        {/* Badges row */}
                        <div className="flex flex-wrap gap-1.5">
                          {job.verdict && (
                            <Badge
                              className={cn(
                                "text-xs",
                                job.verdict.toUpperCase().includes("APPLY") && !job.verdict.toUpperCase().includes("CAUTION")
                                  ? "bg-emerald-600/15 text-emerald-400 border-emerald-600/30"
                                  : job.verdict.toUpperCase().includes("CAUTION")
                                    ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                                    : "bg-red-500/15 text-red-400 border-red-500/30"
                              )}
                            >
                              {job.verdict}
                            </Badge>
                          )}
                          {typeof job.ats_score === "number" && job.ats_score > 0 && (
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                job.ats_score >= 75
                                  ? "text-emerald-400 border-emerald-600/30"
                                  : job.ats_score >= 50
                                    ? "text-yellow-400 border-yellow-500/30"
                                    : "text-red-400 border-red-500/30"
                              )}
                            >
                              ATS {job.ats_score}%
                            </Badge>
                          )}
                          {job.work_mode && (
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                workModeBadgeColor(job.work_mode)
                              )}
                            >
                              {job.work_mode}
                            </Badge>
                          )}
                          <Badge variant="secondary" className="text-xs">
                            {job.source}
                          </Badge>
                        </div>

                        {/* LLM Reason */}
                        {job.llm_reason && (
                          <p className="text-muted-foreground text-xs italic leading-relaxed">
                            {job.llm_reason}
                          </p>
                        )}

                        {/* Spacer */}
                        <div className="flex-1" />

                        {/* Action buttons */}
                        <div className="flex flex-wrap items-center gap-2 pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            asChild
                          >
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                              Apply
                            </a>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const params = new URLSearchParams({
                                title: job.title,
                                company: job.company,
                                description: (job.description || "").slice(0, 2000),
                              });
                              router.push(`/analyzer?${params.toString()}`);
                            }}
                          >
                            <FileSearch className="mr-1.5 h-3.5 w-3.5" />
                            Analyze
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const params = new URLSearchParams({
                                company: job.company,
                                role: job.title,
                                type: "cold-dm",
                              });
                              router.push(`/messages?${params.toString()}`);
                            }}
                          >
                            <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
                            Message
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={isLogged}
                            onClick={() => handleLog(job)}
                          >
                            {isLogged ? (
                              <Check className="mr-1.5 h-3.5 w-3.5" />
                            ) : (
                              <ClipboardPlus className="mr-1.5 h-3.5 w-3.5" />
                            )}
                            {isLogged ? "Logged" : "Log"}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-red-400"
                            onClick={() => handleDismiss(job)}
                          >
                            <XCircle className="mr-1.5 h-3.5 w-3.5" />
                            Dismiss
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

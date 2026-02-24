"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { runScraper, getFollowUps, createApplication } from "@/lib/api";
import type { SSEEvent, ScrapedJob, FollowUp } from "@/lib/types";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Loader2,
  ExternalLink,
  ClipboardPlus,
  Building2,
  MapPin,
  AlertTriangle,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Pipeline phases in display order
// ---------------------------------------------------------------------------
const PHASES = [
  "started",
  "scrape_complete",
  "scoring",
  "scoring_complete",
  "reranking",
  "complete",
] as const;

type Phase = (typeof PHASES)[number];

const PHASE_LABELS: Record<Phase, string> = {
  started: "Starting",
  scrape_complete: "Scraping",
  scoring: "Scoring Jobs",
  scoring_complete: "Scoring Complete",
  reranking: "Re-ranking",
  complete: "Complete",
};

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
  const [running, setRunning] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<Phase | null>(null);
  const [completedPhases, setCompletedPhases] = useState<Set<Phase>>(new Set());
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [jobs, setJobs] = useState<ScrapedJob[]>([]);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loggedJobs, setLoggedJobs] = useState<Set<string>>(new Set());
  const [sourcesStatus, setSourcesStatus] = useState<Record<string, number>>({});
  const [sourcesErrors, setSourcesErrors] = useState<Record<string, string>>({});

  const abortRef = useRef<AbortController | null>(null);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ------- SSE event handler -------
  const handleEvent = useCallback((evt: SSEEvent) => {
    setEvents((prev) => [...prev, evt]);

    const phase = evt.event as Phase;

    switch (phase) {
      case "started":
        setCurrentPhase("started");
        setCompletedPhases((prev) => new Set(prev).add("started"));
        break;

      case "scrape_complete":
        setCurrentPhase("scrape_complete");
        setCompletedPhases((prev) => {
          const next = new Set(prev);
          next.add("started");
          next.add("scrape_complete");
          return next;
        });
        if (evt.sources_status) setSourcesStatus(evt.sources_status);
        if (evt.sources_errors) setSourcesErrors(evt.sources_errors);
        break;

      case "scoring":
        setCurrentPhase("scoring");
        setCompletedPhases((prev) => {
          const next = new Set(prev);
          next.add("started");
          next.add("scrape_complete");
          return next;
        });
        break;

      case "scoring_complete":
        setCurrentPhase("scoring_complete");
        setCompletedPhases((prev) => {
          const next = new Set(prev);
          next.add("started");
          next.add("scrape_complete");
          next.add("scoring");
          next.add("scoring_complete");
          return next;
        });
        break;

      case "reranking":
        setCurrentPhase("reranking");
        setCompletedPhases((prev) => {
          const next = new Set(prev);
          next.add("started");
          next.add("scrape_complete");
          next.add("scoring");
          next.add("scoring_complete");
          return next;
        });
        break;

      case "complete":
        setCurrentPhase("complete");
        setCompletedPhases(new Set(PHASES));
        if (evt.jobs) setJobs(evt.jobs);
        setRunning(false);
        break;
    }
  }, []);

  // ------- Generate handler -------
  const handleGenerate = useCallback(async () => {
    setRunning(true);
    setEvents([]);
    setJobs([]);
    setCurrentPhase(null);
    setCompletedPhases(new Set());
    setSourcesStatus({});
    setSourcesErrors({});
    setLoggedJobs(new Set());

    // Fetch follow-ups in parallel
    getFollowUps()
      .then(setFollowUps)
      .catch(() => setFollowUps([]));

    const controller = runScraper(handleEvent);
    abortRef.current = controller;
  }, [handleEvent]);

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
      setLoggedJobs((prev) => new Set(prev).add(key));
      toast.success(`Logged ${job.company} - ${job.title} to tracker`);
    } catch {
      toast.error("Failed to log application");
    }
  }, []);

  // ------- Phase badge rendering -------
  const renderPhaseBadge = (phase: Phase) => {
    const isCompleted = completedPhases.has(phase);
    const isCurrent = currentPhase === phase && !isCompleted;

    if (isCompleted) {
      return (
        <Badge className="bg-emerald-600 text-white">
          <Check className="mr-1 h-3 w-3" />
          {PHASE_LABELS[phase]}
        </Badge>
      );
    }

    if (isCurrent) {
      return (
        <Badge className="animate-pulse bg-yellow-500 text-black">
          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          {PHASE_LABELS[phase]}
        </Badge>
      );
    }

    return (
      <Badge variant="outline" className="text-muted-foreground">
        {PHASE_LABELS[phase]}
      </Badge>
    );
  };

  const isComplete = currentPhase === "complete";

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Tonight&apos;s Plan
          </h1>
          <p className="text-muted-foreground mt-1">
            Run scrapers, score jobs, and build your application list for
            tonight.
          </p>
        </div>
        <Button onClick={handleGenerate} disabled={running}>
          {running ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Play className="mr-2 h-4 w-4" />
          )}
          Generate Tonight&apos;s Plan
        </Button>
      </div>

      {/* ---- Progress Section ---- */}
      {(running || isComplete) && (
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Progress</CardTitle>
            <CardDescription>
              {running
                ? "Scraping and scoring jobs..."
                : `Done -- ${jobs.length} jobs found.`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {PHASES.map((phase) => (
                <span key={phase}>{renderPhaseBadge(phase)}</span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---- Results (shown after complete) ---- */}
      {isComplete && (
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
                      className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 space-y-1"
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
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Separator />

          {/* ---- Section 2: Top Jobs ---- */}
          <div>
            <h2 className="text-2xl font-semibold tracking-tight mb-4">
              Top Jobs
            </h2>
            {jobs.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No jobs were returned by the scrapers.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {jobs.map((job, idx) => {
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
                          <Badge
                            className={cn(
                              "shrink-0 tabular-nums",
                              scoreBadgeColor(job.score)
                            )}
                          >
                            {job.score}
                          </Badge>
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
                        <div className="flex items-center gap-2 pt-2">
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
                            disabled={isLogged}
                            onClick={() => handleLog(job)}
                          >
                            {isLogged ? (
                              <Check className="mr-1.5 h-3.5 w-3.5" />
                            ) : (
                              <ClipboardPlus className="mr-1.5 h-3.5 w-3.5" />
                            )}
                            {isLogged ? "Logged" : "Log to Tracker"}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          <Separator />

          {/* ---- Section 3: Scrape Summary ---- */}
          <Card>
            <CardHeader>
              <CardTitle>Scrape Summary</CardTitle>
              <CardDescription>
                Source breakdown from the latest scrape run.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Sources status */}
              {Object.keys(sourcesStatus).length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Jobs per source</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(sourcesStatus).map(([source, count]) => (
                      <Badge key={source} variant="secondary">
                        {source}: {count}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Errors */}
              {Object.keys(sourcesErrors).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-red-400 mb-2">
                    Errors
                  </p>
                  <div className="space-y-1">
                    {Object.entries(sourcesErrors).map(([source, error]) => (
                      <div
                        key={source}
                        className="rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm"
                      >
                        <span className="font-medium">{source}:</span>{" "}
                        <span className="text-muted-foreground">{error}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(sourcesStatus).length === 0 &&
                Object.keys(sourcesErrors).length === 0 && (
                  <p className="text-muted-foreground text-sm">
                    No scrape summary data available.
                  </p>
                )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

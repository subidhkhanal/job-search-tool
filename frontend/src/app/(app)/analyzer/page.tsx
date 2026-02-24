"use client";

import { useState } from "react";
import { analyzeFullJD, checkATS } from "@/lib/api";
import type { AnalysisResult, ATSResult } from "@/lib/types";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  FileSearch,
  Loader2,
  ChevronDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Building2,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 75) return "text-emerald-500";
  if (score >= 50) return "text-yellow-500";
  return "text-red-500";
}

function progressColor(score: number) {
  if (score >= 75) return "[&_[data-slot=progress-indicator]]:bg-emerald-500";
  if (score >= 50) return "[&_[data-slot=progress-indicator]]:bg-yellow-500";
  return "[&_[data-slot=progress-indicator]]:bg-red-500";
}

function verdictStyle(label: string) {
  const l = label.toUpperCase();
  if (l.includes("APPLY"))
    return "border-emerald-500/50 bg-emerald-500/10 text-emerald-400";
  if (l.includes("CAUTION"))
    return "border-amber-500/50 bg-amber-500/10 text-amber-400";
  if (l.includes("SKIP"))
    return "border-red-500/50 bg-red-500/10 text-red-400";
  return "border-border";
}

function verdictIcon(label: string) {
  const l = label.toUpperCase();
  if (l.includes("APPLY"))
    return <CheckCircle className="h-6 w-6 text-emerald-500" />;
  if (l.includes("CAUTION"))
    return <AlertTriangle className="h-6 w-6 text-amber-500" />;
  if (l.includes("SKIP"))
    return <XCircle className="h-6 w-6 text-red-500" />;
  return null;
}

// ---------------------------------------------------------------------------
// Sub-components shared between tabs
// ---------------------------------------------------------------------------

function ATSResultsDisplay({ ats }: { ats: ATSResult }) {
  return (
    <div className="space-y-6">
      {/* Score */}
      <Card>
        <CardContent className="pt-6 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">ATS Score</p>
            <span className={cn("text-2xl font-bold", scoreColor(ats.ats_score))}>
              {ats.ats_score}%
            </span>
          </div>
          <Progress
            value={ats.ats_score}
            className={cn("h-3", progressColor(ats.ats_score))}
          />
          {(ats.experience_req || ats.degree_req) && (
            <div className="flex flex-wrap gap-4 pt-2 text-sm text-muted-foreground">
              {ats.experience_req && (
                <span>Experience: {ats.experience_req}</span>
              )}
              {ats.degree_req && <span>Degree: {ats.degree_req}</span>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Found keywords */}
      {ats.found_keywords.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500" />
            Found Keywords ({ats.found_keywords.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {ats.found_keywords.map((kw) => (
              <Badge
                key={kw}
                className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
              >
                {kw}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Missing keywords */}
      {ats.missing_keywords.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-500" />
            Missing Keywords ({ats.missing_keywords.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {ats.missing_keywords.map((kw) => (
              <Badge
                key={kw}
                variant="outline"
                className="border-red-500/30 text-red-400"
              >
                {kw}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Suggestions */}
      {ats.suggestions.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Suggestions</p>
          <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
            {ats.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AnalyzerPage() {
  // ---- Full Analysis state ----
  const [fullForm, setFullForm] = useState({
    title: "",
    description: "",
    company: "",
    custom_resume: "",
  });
  const [fullLoading, setFullLoading] = useState(false);
  const [fullResult, setFullResult] = useState<AnalysisResult | null>(null);
  const [fullError, setFullError] = useState<string | null>(null);
  const [resumeOpen, setResumeOpen] = useState(false);

  // ---- Quick ATS state ----
  const [atsForm, setAtsForm] = useState({
    jd_text: "",
    custom_resume: "",
  });
  const [atsLoading, setAtsLoading] = useState(false);
  const [atsResult, setAtsResult] = useState<ATSResult | null>(null);
  const [atsError, setAtsError] = useState<string | null>(null);

  // ---- Handlers ----
  async function handleFullAnalyze() {
    if (!fullForm.title.trim() || !fullForm.description.trim()) return;
    setFullLoading(true);
    setFullError(null);
    setFullResult(null);
    try {
      const result = await analyzeFullJD({
        title: fullForm.title.trim(),
        description: fullForm.description.trim(),
        company: fullForm.company.trim() || undefined,
        custom_resume: fullForm.custom_resume.trim() || undefined,
      });
      setFullResult(result);
    } catch (err) {
      setFullError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setFullLoading(false);
    }
  }

  async function handleATSCheck() {
    if (!atsForm.jd_text.trim()) return;
    setAtsLoading(true);
    setAtsError(null);
    setAtsResult(null);
    try {
      const result = await checkATS({
        jd_text: atsForm.jd_text.trim(),
        custom_resume: atsForm.custom_resume.trim() || undefined,
      });
      setAtsResult(result);
    } catch (err) {
      setAtsError(err instanceof Error ? err.message : "ATS check failed");
    } finally {
      setAtsLoading(false);
    }
  }

  // ---- Render ----
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">JD Analyzer</h1>
        <p className="text-muted-foreground mt-1">
          Analyze job descriptions for ATS compatibility, NOC codes, skills
          match, and red flags.
        </p>
      </div>

      <Tabs defaultValue="full">
        <TabsList>
          <TabsTrigger value="full">Full Analysis</TabsTrigger>
          <TabsTrigger value="ats">Quick ATS Check</TabsTrigger>
        </TabsList>

        {/* ================================================================ */}
        {/* TAB 1 — Full Analysis                                            */}
        {/* ================================================================ */}
        <TabsContent value="full" className="space-y-6">
          {/* Form */}
          <Card>
            <CardHeader>
              <CardTitle>Job Description</CardTitle>
              <CardDescription>
                Paste the full job description for a comprehensive analysis.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Job Title */}
              <div className="space-y-2">
                <Label htmlFor="full-title">Job Title</Label>
                <Input
                  id="full-title"
                  placeholder="e.g. Full-Stack Developer"
                  value={fullForm.title}
                  onChange={(e) =>
                    setFullForm((p) => ({ ...p, title: e.target.value }))
                  }
                />
              </div>

              {/* Job Description */}
              <div className="space-y-2">
                <Label htmlFor="full-description">Job Description</Label>
                <Textarea
                  id="full-description"
                  placeholder="Paste the full job description here..."
                  className="h-64"
                  value={fullForm.description}
                  onChange={(e) =>
                    setFullForm((p) => ({ ...p, description: e.target.value }))
                  }
                />
              </div>

              {/* Company Name (optional) */}
              <div className="space-y-2">
                <Label htmlFor="full-company">Company Name (optional)</Label>
                <Input
                  id="full-company"
                  placeholder="e.g. Shopify"
                  value={fullForm.company}
                  onChange={(e) =>
                    setFullForm((p) => ({ ...p, company: e.target.value }))
                  }
                />
              </div>

              {/* Custom Resume (collapsible) */}
              <Collapsible open={resumeOpen} onOpenChange={setResumeOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2 px-0">
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 transition-transform",
                        resumeOpen && "rotate-180"
                      )}
                    />
                    Custom Resume (optional)
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="pt-2">
                  <Textarea
                    placeholder="Paste your resume text here for a personalized analysis..."
                    className="h-48"
                    value={fullForm.custom_resume}
                    onChange={(e) =>
                      setFullForm((p) => ({
                        ...p,
                        custom_resume: e.target.value,
                      }))
                    }
                  />
                </CollapsibleContent>
              </Collapsible>

              {/* Submit */}
              <Button
                onClick={handleFullAnalyze}
                disabled={
                  fullLoading ||
                  !fullForm.title.trim() ||
                  !fullForm.description.trim()
                }
                className="w-full sm:w-auto"
              >
                {fullLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FileSearch className="mr-2 h-4 w-4" />
                )}
                {fullLoading ? "Analyzing..." : "Analyze"}
              </Button>
            </CardContent>
          </Card>

          {/* Error */}
          {fullError && (
            <Card className="border-red-500/50 bg-red-500/10">
              <CardContent className="pt-6">
                <p className="text-sm text-red-400">{fullError}</p>
              </CardContent>
            </Card>
          )}

          {/* Results */}
          {fullResult && (
            <div className="space-y-6">
              {/* 1. Verdict Banner */}
              {fullResult.verdict_label && (
                <Card
                  className={cn(
                    "border-2",
                    verdictStyle(fullResult.verdict_label)
                  )}
                >
                  <CardContent className="flex items-start gap-4 pt-6">
                    {verdictIcon(fullResult.verdict_label)}
                    <div className="space-y-1">
                      <p className="text-lg font-bold">
                        {fullResult.verdict_label}
                      </p>
                      {fullResult.verdict_reason && (
                        <p className="text-sm opacity-80">
                          {fullResult.verdict_reason}
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* 2. Three Metric Cards */}
              <div className="grid gap-4 md:grid-cols-3">
                {/* ATS Score */}
                {fullResult.ats && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        ATS Score
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <p
                        className={cn(
                          "text-3xl font-bold",
                          scoreColor(fullResult.ats.ats_score)
                        )}
                      >
                        {fullResult.ats.ats_score}%
                      </p>
                      <Progress
                        value={fullResult.ats.ats_score}
                        className={cn(
                          "h-2",
                          progressColor(fullResult.ats.ats_score)
                        )}
                      />
                    </CardContent>
                  </Card>
                )}

                {/* NOC Code */}
                {fullResult.noc && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        NOC Code
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <p className="text-3xl font-bold">
                        {fullResult.noc.code}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {fullResult.noc.title}
                      </p>
                      <Badge variant="secondary">
                        {fullResult.noc.confidence} confidence
                      </Badge>
                    </CardContent>
                  </Card>
                )}

                {/* Skill Match */}
                {fullResult.skills && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Skill Match
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <p
                        className={cn(
                          "text-3xl font-bold",
                          scoreColor(fullResult.skills.match_pct)
                        )}
                      >
                        {fullResult.skills.match_pct}%
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {fullResult.skills.matched.length} skills matched
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* 3. Company Intel */}
              {fullResult.company_intel && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building2 className="h-5 w-5" />
                      Company Intel
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {fullResult.company_intel.description && (
                      <div className="space-y-1">
                        <p className="text-sm font-medium">About</p>
                        <p className="text-sm text-muted-foreground">
                          {fullResult.company_intel.description}
                        </p>
                      </div>
                    )}

                    {fullResult.company_intel.recent_news && (
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Recent News</p>
                        <p className="text-sm text-muted-foreground">
                          {fullResult.company_intel.recent_news}
                        </p>
                      </div>
                    )}

                    {fullResult.company_intel.tech_signals &&
                      fullResult.company_intel.tech_signals.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-sm font-medium">Tech Signals</p>
                          <div className="flex flex-wrap gap-2">
                            {fullResult.company_intel.tech_signals.map((t) => (
                              <Badge key={t} variant="secondary">
                                {t}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                    {fullResult.company_intel.hiring_contact && (
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Hiring Contact</p>
                        <div className="text-sm text-muted-foreground space-y-0.5">
                          {fullResult.company_intel.hiring_contact.name && (
                            <p>{fullResult.company_intel.hiring_contact.name}</p>
                          )}
                          {fullResult.company_intel.hiring_contact.title && (
                            <p className="text-xs">
                              {fullResult.company_intel.hiring_contact.title}
                            </p>
                          )}
                          {fullResult.company_intel.hiring_contact.linkedin && (
                            <a
                              href={
                                fullResult.company_intel.hiring_contact.linkedin
                              }
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-blue-400 hover:underline"
                            >
                              LinkedIn
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    )}

                    {fullResult.company_intel.product_url && (
                      <div className="space-y-1">
                        <p className="text-sm font-medium">Product</p>
                        <a
                          href={fullResult.company_intel.product_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm text-blue-400 hover:underline"
                        >
                          {fullResult.company_intel.product_url}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* 4. Skills Section */}
              {fullResult.skills && (
                <>
                  <Separator />
                  <div className="grid gap-6 md:grid-cols-2">
                    {/* Matched */}
                    <div className="space-y-3">
                      <p className="text-sm font-medium flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-emerald-500" />
                        Matched Skills ({fullResult.skills.matched.length})
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {fullResult.skills.matched.map((s) => (
                          <Badge
                            key={s}
                            className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          >
                            {s}
                          </Badge>
                        ))}
                        {fullResult.skills.matched.length === 0 && (
                          <p className="text-sm text-muted-foreground">
                            No matched skills found.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Gaps */}
                    <div className="space-y-3">
                      <p className="text-sm font-medium flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-red-500" />
                        Skill Gaps ({fullResult.skills.gaps.length})
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {fullResult.skills.gaps.map((s) => (
                          <Badge
                            key={s}
                            className="bg-red-500/15 text-red-400 border-red-500/30"
                          >
                            {s}
                          </Badge>
                        ))}
                        {fullResult.skills.gaps.length === 0 && (
                          <p className="text-sm text-muted-foreground">
                            No skill gaps detected.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* 5. Red Flags */}
              {fullResult.red_flags && fullResult.red_flags.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <p className="text-sm font-medium flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      Red Flags ({fullResult.red_flags.length})
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {fullResult.red_flags.map((flag, i) => (
                        <Card
                          key={i}
                          className="border-amber-500/30 bg-amber-500/5"
                        >
                          <CardContent className="flex items-start gap-3 pt-4 pb-4">
                            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-amber-500" />
                            <div className="space-y-0.5">
                              <p className="text-sm font-medium text-amber-400">
                                {flag.type}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {flag.message}
                              </p>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* 6. ATS Details */}
              {fullResult.ats && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    <p className="text-lg font-semibold">ATS Details</p>
                    <ATSResultsDisplay ats={fullResult.ats} />
                  </div>
                </>
              )}
            </div>
          )}
        </TabsContent>

        {/* ================================================================ */}
        {/* TAB 2 — Quick ATS Check                                          */}
        {/* ================================================================ */}
        <TabsContent value="ats" className="space-y-6">
          {/* Form */}
          <Card>
            <CardHeader>
              <CardTitle>Quick ATS Check</CardTitle>
              <CardDescription>
                Paste a job description to quickly check your ATS keyword match.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* JD Text */}
              <div className="space-y-2">
                <Label htmlFor="ats-jd">Job Description</Label>
                <Textarea
                  id="ats-jd"
                  placeholder="Paste the job description here..."
                  className="h-64"
                  value={atsForm.jd_text}
                  onChange={(e) =>
                    setAtsForm((p) => ({ ...p, jd_text: e.target.value }))
                  }
                />
              </div>

              {/* Custom Resume */}
              <div className="space-y-2">
                <Label htmlFor="ats-resume">Custom Resume (optional)</Label>
                <Textarea
                  id="ats-resume"
                  placeholder="Paste your resume text here for a personalized check..."
                  className="h-48"
                  value={atsForm.custom_resume}
                  onChange={(e) =>
                    setAtsForm((p) => ({
                      ...p,
                      custom_resume: e.target.value,
                    }))
                  }
                />
              </div>

              {/* Submit */}
              <Button
                onClick={handleATSCheck}
                disabled={atsLoading || !atsForm.jd_text.trim()}
                className="w-full sm:w-auto"
              >
                {atsLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FileSearch className="mr-2 h-4 w-4" />
                )}
                {atsLoading ? "Checking..." : "Check ATS"}
              </Button>
            </CardContent>
          </Card>

          {/* Error */}
          {atsError && (
            <Card className="border-red-500/50 bg-red-500/10">
              <CardContent className="pt-6">
                <p className="text-sm text-red-400">{atsError}</p>
              </CardContent>
            </Card>
          )}

          {/* Results */}
          {atsResult && <ATSResultsDisplay ats={atsResult} />}
        </TabsContent>
      </Tabs>
    </div>
  );
}

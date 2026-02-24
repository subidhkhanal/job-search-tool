"use client";

import { useState } from "react";
import { tailorResume } from "@/lib/api";
import type { ResumeTailorResult } from "@/lib/types";

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
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { FileText, Loader2, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function difficultyColor(difficulty: string) {
  const d = difficulty.toLowerCase();
  if (d === "easy") return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  if (d === "medium") return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
  if (d === "hard") return "bg-red-500/15 text-red-400 border-red-500/30";
  return "bg-muted text-muted-foreground";
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ResumeTailorPage() {
  const [title, setTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [result, setResult] = useState<ResumeTailorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skillsCopied, setSkillsCopied] = useState(false);

  // ---- Handlers ----

  async function handleTailor() {
    if (!title.trim() || !jdText.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await tailorResume({
        title: title.trim(),
        jd_text: jdText.trim(),
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume tailoring failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopySkills() {
    if (!result) return;
    const skillsLine = result.skills.join(" \u00b7 ");
    try {
      await navigator.clipboard.writeText(skillsLine);
      setSkillsCopied(true);
      toast.success("Skills copied to clipboard!");
      setTimeout(() => setSkillsCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard.");
    }
  }

  // ---- Render ----

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <FileText className="h-8 w-8" />
          Resume Tailor
        </h1>
        <p className="text-muted-foreground mt-1">
          Tailor your resume to a specific job description. Get project ordering,
          skill suggestions, gap analysis, and summary lines.
        </p>
      </div>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <CardTitle>Job Details</CardTitle>
          <CardDescription>
            Enter the job title and paste the full job description to tailor your
            resume.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Job Title */}
          <div className="space-y-2">
            <Label htmlFor="tailor-title">Job Title</Label>
            <Input
              id="tailor-title"
              placeholder="e.g. Full-Stack Developer"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Job Description */}
          <div className="space-y-2">
            <Label htmlFor="tailor-jd">Job Description</Label>
            <Textarea
              id="tailor-jd"
              placeholder="Paste the full job description here..."
              className="h-64"
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />
          </div>

          {/* Submit */}
          <Button
            onClick={handleTailor}
            disabled={loading || !title.trim() || !jdText.trim()}
            className="w-full sm:w-auto"
          >
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileText className="mr-2 h-4 w-4" />
            )}
            {loading ? "Tailoring..." : "Tailor My Resume"}
          </Button>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Card className="border-red-500/50 bg-red-500/10">
          <CardContent className="pt-6">
            <p className="text-sm text-red-400">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* ---- Section 1: Project Order ---- */}
          <Card>
            <CardHeader>
              <CardTitle>Project Order</CardTitle>
              <CardDescription>
                Recommended ordering of your projects based on relevance to this
                role.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {result.projects.map((project, i) => (
                <div key={i}>
                  {i > 0 && <Separator className="mb-4" />}
                  {typeof project === "string" ? (
                    <p className="text-sm">
                      <span className="font-mono text-muted-foreground mr-2">
                        {i + 1}.
                      </span>
                      {project}
                    </p>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-mono text-muted-foreground">
                          {i + 1}.
                        </span>
                        <span className="font-bold">{project.name}</span>
                        <Badge variant="secondary">
                          {project.matches}{" "}
                          {project.matches === 1 ? "match" : "matches"}
                        </Badge>
                      </div>
                      {project.keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 ml-6">
                          {project.keywords.map((kw) => (
                            <Badge
                              key={kw}
                              variant="outline"
                              className="text-xs"
                            >
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {project.one_liner && (
                        <p className="text-sm text-muted-foreground ml-6">
                          {project.one_liner}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* ---- Section 2: Suggested Skills Line ---- */}
          {result.skills.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle>Suggested Skills Line</CardTitle>
                  <CardDescription>
                    Copy this skills line directly into your resume.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopySkills}
                  className="flex items-center gap-2"
                >
                  {skillsCopied ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  {skillsCopied ? "Copied" : "Copy"}
                </Button>
              </CardHeader>
              <CardContent>
                <div className="bg-muted font-mono p-4 rounded text-sm">
                  {result.skills.join(" \u00b7 ")}
                </div>
              </CardContent>
            </Card>
          )}

          {/* ---- Section 3: Gap Analysis ---- */}
          {result.gaps.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Gap Analysis</CardTitle>
                <CardDescription>
                  Skills you may want to address or learn before applying.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.gaps.map((gap, i) => (
                  <div key={i}>
                    {i > 0 && <Separator className="mb-3" />}
                    {typeof gap === "string" ? (
                      <p className="text-sm">{gap}</p>
                    ) : (
                      <div className="flex items-start gap-3">
                        <span className="text-lg leading-none mt-0.5">
                          {gap.emoji}
                        </span>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm">
                              {gap.skill}
                            </span>
                            <Badge
                              className={cn(
                                "text-xs",
                                difficultyColor(gap.difficulty)
                              )}
                            >
                              {gap.difficulty}
                            </Badge>
                          </div>
                          {gap.note && (
                            <p className="text-sm text-muted-foreground">
                              {gap.note}
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* ---- Section 4: Tailored Summary Lines ---- */}
          {result.summaries.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Tailored Summary Lines</CardTitle>
                <CardDescription>
                  Use these as your resume summary or objective lines.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.summaries.map((summary, i) => (
                  <div
                    key={i}
                    className="border-l-4 border-muted-foreground/30 pl-4 py-2"
                  >
                    <p className="text-sm">
                      <span className="font-mono text-muted-foreground mr-2">
                        {i + 1}.
                      </span>
                      {summary}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

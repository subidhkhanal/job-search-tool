"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
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
import {
  FileText,
  Loader2,
  Copy,
  Check,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  GitCompareArrows,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

function scoreColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-yellow-400";
  return "text-red-400";
}

function scoreBg(score: number) {
  if (score >= 80) return "bg-emerald-500/15 border-emerald-500/30";
  if (score >= 60) return "bg-yellow-500/15 border-yellow-500/30";
  return "bg-red-500/15 border-red-500/30";
}

function difficultyColor(difficulty: string) {
  const d = difficulty.toLowerCase();
  if (d === "easy")
    return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  if (d === "medium")
    return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
  if (d === "hard")
    return "bg-red-500/15 text-red-400 border-red-500/30";
  return "bg-muted text-muted-foreground";
}

function ResumeTailorContent() {
  const searchParams = useSearchParams();
  const [title, setTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [result, setResult] = useState<ResumeTailorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Pre-fill from query params (e.g. from Tonight page)
  useEffect(() => {
    const t = searchParams.get("title");
    const jd = searchParams.get("jd_text");
    if (t) setTitle(t);
    if (jd) setJdText(jd);
  }, [searchParams]);

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
      setError(
        err instanceof Error ? err.message : "Resume tailoring failed"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleCopyLatex() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.tailored_latex);
      setCopied(true);
      toast.success("LaTeX copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard.");
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <FileText className="h-8 w-8" />
          Resume Tailor
        </h1>
        <p className="text-muted-foreground mt-1">
          Two-pass GPT-4 tailoring: analyzes the JD first, then rewrites your
          resume for maximum ATS score. Your LaTeX resume from Settings is used
          automatically.
        </p>
      </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Job Details</CardTitle>
          <CardDescription>
            Enter the job title and paste the full job description.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="tailor-title">Job Title</Label>
            <Input
              id="tailor-title"
              placeholder="e.g. AI Engineer Intern"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
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
          {/* ATS Score Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                ATS Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center gap-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-1">Before</p>
                  <div
                    className={cn(
                      "text-4xl font-bold rounded-lg border px-6 py-3",
                      scoreBg(result.ats_before)
                    )}
                  >
                    <span className={scoreColor(result.ats_before)}>
                      {result.ats_before}%
                    </span>
                  </div>
                </div>
                <ArrowRight className="h-8 w-8 text-muted-foreground" />
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-1">After</p>
                  <div
                    className={cn(
                      "text-4xl font-bold rounded-lg border px-6 py-3",
                      scoreBg(result.ats_after)
                    )}
                  >
                    <span className={scoreColor(result.ats_after)}>
                      {result.ats_after}%
                    </span>
                  </div>
                </div>
                {result.ats_after > result.ats_before && (
                  <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-lg px-3 py-1">
                    +{result.ats_after - result.ats_before}%
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Bullet-by-Bullet Diff */}
          {result.bullet_diffs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitCompareArrows className="h-5 w-5" />
                  Bullet-by-Bullet Diff
                </CardTitle>
                <CardDescription>
                  Original vs rewritten for each bullet point. Review each
                  change to verify accuracy.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {result.bullet_diffs.map((diff, i) => (
                  <div key={i}>
                    {i > 0 && <Separator className="mb-6" />}
                    <div className="space-y-3">
                      <Badge variant="outline">{diff.section}</Badge>
                      <div className="grid gap-2">
                        <div className="rounded-md border border-red-500/20 bg-red-500/5 p-3">
                          <p className="text-xs font-medium text-red-400 mb-1">
                            Original
                          </p>
                          <p className="text-sm">{diff.original}</p>
                        </div>
                        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3">
                          <p className="text-xs font-medium text-emerald-400 mb-1">
                            Rewritten
                          </p>
                          <p className="text-sm">{diff.rewritten}</p>
                        </div>
                      </div>
                      {diff.keywords_added.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-muted-foreground">
                            Keywords added:
                          </span>
                          {diff.keywords_added.map((kw) => (
                            <Badge
                              key={kw}
                              className="text-xs bg-blue-500/15 text-blue-400 border-blue-500/30"
                            >
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Tailored LaTeX */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Tailored Resume</CardTitle>
                <CardDescription>
                  Copy this LaTeX and compile in Overleaf or your editor.
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyLatex}
                className="flex items-center gap-2"
              >
                {copied ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                {copied ? "Copied" : "Copy LaTeX"}
              </Button>
            </CardHeader>
            <CardContent>
              <div className="bg-muted rounded-lg p-4 max-h-[500px] overflow-auto">
                <pre className="text-sm font-mono whitespace-pre-wrap break-words">
                  {result.tailored_latex}
                </pre>
              </div>
            </CardContent>
          </Card>

          {/* What Changed */}
          {result.changes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>What Changed</CardTitle>
                <CardDescription>
                  High-level summary of modifications and why.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {result.changes.map((change, i) => (
                  <div key={i}>
                    {i > 0 && <Separator className="mb-4" />}
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{change.section}</Badge>
                      </div>
                      <p className="text-sm font-medium">
                        {change.what_changed}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {change.why}
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Skill Gaps */}
          {result.gaps.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Skill Gaps
                </CardTitle>
                <CardDescription>
                  Skills the JD requires that aren&apos;t in your resume. These
                  can&apos;t be rephrased in — you&apos;d need to actually learn
                  them.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.gaps.map((gap, i) => (
                  <div key={i}>
                    {i > 0 && <Separator className="mb-3" />}
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sm">{gap.skill}</span>
                      <Badge
                        className={cn(
                          "text-xs",
                          difficultyColor(gap.difficulty)
                        )}
                      >
                        {gap.difficulty}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {gap.note}
                      </span>
                    </div>
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

export default function ResumeTailorPage() {
  return (
    <Suspense>
      <ResumeTailorContent />
    </Suspense>
  );
}

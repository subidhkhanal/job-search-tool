"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  generateColdDM,
  generateFollowUp,
  generateCoverLetter,
  generateThankYou,
  generateReferralRequest,
  generateDemoOutreach,
  getApplications,
  getFollowUpHistory,
  logFollowUp,
} from "@/lib/api";
import type { Application } from "@/lib/types";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { MessageSquare, Loader2, Copy, Check } from "lucide-react";
import { toast } from "sonner";

type MessageType =
  | "cold-dm"
  | "follow-up"
  | "cover-letter"
  | "thank-you"
  | "referral-request"
  | "demo-outreach";

const MESSAGE_TYPE_OPTIONS: { value: MessageType; label: string }[] = [
  { value: "cold-dm", label: "Cold DM" },
  { value: "follow-up", label: "Follow-up" },
  { value: "cover-letter", label: "Cover Letter" },
  { value: "thank-you", label: "Thank You" },
  { value: "referral-request", label: "Referral Request" },
  { value: "demo-outreach", label: "Demo Outreach" },
];

function MessagesPageInner() {
  const searchParams = useSearchParams();
  const [messageType, setMessageType] = useState<MessageType | "">("");
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showLogDialog, setShowLogDialog] = useState(false);
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [loggingFollowUp, setLoggingFollowUp] = useState(false);
  const [logged, setLogged] = useState(false);

  // Pre-fill from query params (e.g. from Tonight's Plan)
  useEffect(() => {
    const type = searchParams.get("type") as MessageType | null;
    const company = searchParams.get("company");
    const role = searchParams.get("role");
    const days = searchParams.get("days");
    const followUpNumber = searchParams.get("follow_up_number");
    if (type) setMessageType(type);
    const prefill: Record<string, string> = {};
    if (company) prefill.company = company;
    if (role) prefill.role = role;
    if (days) prefill.days = days;
    if (followUpNumber) prefill.follow_up_number = followUpNumber;
    if (Object.keys(prefill).length > 0) setFormData(prefill);
  }, [searchParams]);

  function handleTypeChange(value: string) {
    setMessageType(value as MessageType);
    setFormData({});
    setResult("");
  }

  function updateField(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleGenerate() {
    if (!messageType) return;
    setLoading(true);
    setResult("");
    setCopied(false);
    setLogged(false);

    try {
      let response: { content: string };

      switch (messageType) {
        case "cold-dm":
          response = await generateColdDM({
            company: formData.company || "",
            role: formData.role || "",
            platform: formData.platform || undefined,
            company_desc: formData.company_desc || undefined,
            project_link: formData.project_link || undefined,
          });
          break;
        case "follow-up": {
          const followUpNum = formData.follow_up_number
            ? parseInt(formData.follow_up_number, 10)
            : 1;
          let previousMessages: string[] | undefined;
          if (followUpNum > 1) {
            try {
              const apps = await getApplications();
              const match = apps.find(
                (a) =>
                  a.company.toLowerCase() ===
                  (formData.company || "").toLowerCase()
              );
              if (match) {
                const history = await getFollowUpHistory(
                  "application",
                  match.id
                );
                previousMessages = history
                  .filter((h) => h.follow_up_number < followUpNum)
                  .sort((a, b) => a.follow_up_number - b.follow_up_number)
                  .map((h) => h.message_content)
                  .filter(Boolean);
              }
            } catch {
              // History fetch failed — generate without it
            }
          }
          response = await generateFollowUp({
            company: formData.company || "",
            role: formData.role || "",
            days: formData.days ? parseInt(formData.days, 10) : 7,
            platform: formData.platform || undefined,
            follow_up_number: followUpNum,
            previous_messages: previousMessages,
          });
          break;
        }
        case "cover-letter":
          response = await generateCoverLetter({
            company: formData.company || "",
            role: formData.role || "",
            jd: formData.jd || "",
            company_info: formData.company_info || undefined,
          });
          break;
        case "thank-you":
          response = await generateThankYou({
            company: formData.company || "",
            interviewer: formData.interviewer || "",
            discussion: formData.discussion || undefined,
          });
          break;
        case "referral-request":
          response = await generateReferralRequest({
            contact_name: formData.contact_name || "",
            contact_role: formData.contact_role || undefined,
            company: formData.company || "",
            role_applying_for: formData.role_applying_for || "",
            relationship: formData.relationship || undefined,
          });
          break;
        case "demo-outreach":
          response = await generateDemoOutreach({
            company: formData.company || "",
            role: formData.role || "",
            demo_url: formData.demo_url || "",
            demo_description: formData.demo_description || "",
            company_desc: formData.company_desc || undefined,
          });
          break;
      }

      setResult(response.content);
    } catch (err) {
      console.error("Failed to generate message", err);
      toast.error("Failed to generate message. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogAsSent() {
    setLoggingFollowUp(true);
    try {
      const apps = await getApplications();
      setApplications(apps);
      const match = apps.find(
        (a) => a.company.toLowerCase() === (formData.company || "").toLowerCase()
      );
      setSelectedAppId(match ? match.id : apps[0]?.id ?? null);
      setShowLogDialog(true);
    } catch {
      toast.error("Failed to load applications.");
    } finally {
      setLoggingFollowUp(false);
    }
  }

  async function handleConfirmLog() {
    if (!selectedAppId) return;
    setLoggingFollowUp(true);
    try {
      const resp = await logFollowUp({
        entity_type: "application",
        entity_id: selectedAppId,
        message_content: result,
        channel: formData.platform || "LinkedIn",
      });
      toast.success(`Follow-up #${resp.follow_up_number} logged`);
      setLogged(true);
      setShowLogDialog(false);
    } catch {
      toast.error("Failed to log follow-up.");
    } finally {
      setLoggingFollowUp(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      toast.success("Copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard.");
    }
  }

  function renderFormFields() {
    switch (messageType) {
      case "cold-dm":
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                value={formData.company || ""}
                onChange={(e) => updateField("company", e.target.value)}
                placeholder="e.g. Stripe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={formData.role || ""}
                onChange={(e) => updateField("role", e.target.value)}
                placeholder="e.g. Frontend Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="platform">Platform</Label>
              <Select
                value={formData.platform || ""}
                onValueChange={(v) => updateField("platform", v)}
              >
                <SelectTrigger id="platform">
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LinkedIn">LinkedIn</SelectItem>
                  <SelectItem value="Twitter">Twitter</SelectItem>
                  <SelectItem value="Email">Email</SelectItem>
                  <SelectItem value="Wellfound">Wellfound</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company_desc">Company Description</Label>
              <Textarea
                id="company_desc"
                value={formData.company_desc || ""}
                onChange={(e) => updateField("company_desc", e.target.value)}
                placeholder="Brief description of what the company does..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="project_link">Project Link</Label>
              <Input
                id="project_link"
                value={formData.project_link || ""}
                onChange={(e) => updateField("project_link", e.target.value)}
                placeholder="https://github.com/you/project"
              />
            </div>
          </>
        );

      case "follow-up":
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                value={formData.company || ""}
                onChange={(e) => updateField("company", e.target.value)}
                placeholder="e.g. Stripe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={formData.role || ""}
                onChange={(e) => updateField("role", e.target.value)}
                placeholder="e.g. Frontend Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="days">Days Since Applied</Label>
              <Input
                id="days"
                type="number"
                value={formData.days || "7"}
                onChange={(e) => updateField("days", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="follow_up_number">Follow-up # (1 = gentle, 2 = value-add, 3 = final)</Label>
              <Select
                value={formData.follow_up_number || "1"}
                onValueChange={(v) => updateField("follow_up_number", v)}
              >
                <SelectTrigger id="follow_up_number">
                  <SelectValue placeholder="Select attempt" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">#1 — Polite check-in</SelectItem>
                  <SelectItem value="2">#2 — With value-add</SelectItem>
                  <SelectItem value="3">#3 — Final follow-up</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="platform">Platform</Label>
              <Select
                value={formData.platform || ""}
                onValueChange={(v) => updateField("platform", v)}
              >
                <SelectTrigger id="platform">
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LinkedIn">LinkedIn</SelectItem>
                  <SelectItem value="Twitter">Twitter</SelectItem>
                  <SelectItem value="Email">Email</SelectItem>
                  <SelectItem value="Wellfound">Wellfound</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        );

      case "cover-letter":
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                value={formData.company || ""}
                onChange={(e) => updateField("company", e.target.value)}
                placeholder="e.g. Stripe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={formData.role || ""}
                onChange={(e) => updateField("role", e.target.value)}
                placeholder="e.g. Frontend Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd">Job Description</Label>
              <Textarea
                id="jd"
                className="h-48"
                value={formData.jd || ""}
                onChange={(e) => updateField("jd", e.target.value)}
                placeholder="Paste the full job description here..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="company_info">Company Info</Label>
              <Textarea
                id="company_info"
                value={formData.company_info || ""}
                onChange={(e) => updateField("company_info", e.target.value)}
                placeholder="Any additional info about the company..."
              />
            </div>
          </>
        );

      case "thank-you":
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                value={formData.company || ""}
                onChange={(e) => updateField("company", e.target.value)}
                placeholder="e.g. Stripe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="interviewer">Interviewer Name</Label>
              <Input
                id="interviewer"
                value={formData.interviewer || ""}
                onChange={(e) => updateField("interviewer", e.target.value)}
                placeholder="e.g. Sarah Chen"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="discussion">Key Discussion Point</Label>
              <Textarea
                id="discussion"
                value={formData.discussion || ""}
                onChange={(e) => updateField("discussion", e.target.value)}
                placeholder="What stood out from the interview..."
              />
            </div>
          </>
        );

      case "referral-request":
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input
                id="contact_name"
                value={formData.contact_name || ""}
                onChange={(e) => updateField("contact_name", e.target.value)}
                placeholder="e.g. John Doe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_role">Their Role</Label>
              <Input
                id="contact_role"
                value={formData.contact_role || ""}
                onChange={(e) => updateField("contact_role", e.target.value)}
                placeholder="e.g. Senior Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                value={formData.company || ""}
                onChange={(e) => updateField("company", e.target.value)}
                placeholder="e.g. Stripe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role_applying_for">Role Applying For</Label>
              <Input
                id="role_applying_for"
                value={formData.role_applying_for || ""}
                onChange={(e) =>
                  updateField("role_applying_for", e.target.value)
                }
                placeholder="e.g. Frontend Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="relationship">Relationship</Label>
              <Select
                value={formData.relationship || ""}
                onValueChange={(v) => updateField("relationship", v)}
              >
                <SelectTrigger id="relationship">
                  <SelectValue placeholder="Select relationship" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Colleague">Colleague</SelectItem>
                  <SelectItem value="Alumni">Alumni</SelectItem>
                  <SelectItem value="LinkedIn Connection">
                    LinkedIn Connection
                  </SelectItem>
                  <SelectItem value="Friend">Friend</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        );

      case "demo-outreach":
        return (
          <>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                value={formData.company || ""}
                onChange={(e) => updateField("company", e.target.value)}
                placeholder="e.g. Stripe"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={formData.role || ""}
                onChange={(e) => updateField("role", e.target.value)}
                placeholder="e.g. Frontend Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="demo_url">Demo URL</Label>
              <Input
                id="demo_url"
                value={formData.demo_url || ""}
                onChange={(e) => updateField("demo_url", e.target.value)}
                placeholder="https://your-demo.vercel.app"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="demo_description">Demo Description</Label>
              <Textarea
                id="demo_description"
                value={formData.demo_description || ""}
                onChange={(e) =>
                  updateField("demo_description", e.target.value)
                }
                placeholder="Describe what you built and why..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="company_desc">Company Description</Label>
              <Textarea
                id="company_desc"
                value={formData.company_desc || ""}
                onChange={(e) => updateField("company_desc", e.target.value)}
                placeholder="Brief description of what the company does..."
              />
            </div>
          </>
        );

      default:
        return null;
    }
  }

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <MessageSquare className="h-8 w-8" />
          Message Generator
        </h1>
        <p className="text-muted-foreground mt-1">
          Generate AI-powered messages for your job search outreach.
        </p>
      </div>

      {/* ---- Form Card ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Compose Message</CardTitle>
          <CardDescription>
            Select a message type and fill in the details to generate a
            tailored message.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Message Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="message-type">Message Type</Label>
            <Select value={messageType} onValueChange={handleTypeChange}>
              <SelectTrigger id="message-type">
                <SelectValue placeholder="Select message type" />
              </SelectTrigger>
              <SelectContent>
                {MESSAGE_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Dynamic Form Fields */}
          {messageType && (
            <>
              <Separator />
              <div className="space-y-4">{renderFormFields()}</div>
              <Button
                onClick={handleGenerate}
                disabled={loading || !messageType}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  "Generate"
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* ---- Result Card ---- */}
      {result && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Generated Message</CardTitle>
            <div className="flex items-center gap-2">
              {messageType === "follow-up" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleLogAsSent}
                  disabled={loggingFollowUp || logged}
                  className="flex items-center gap-2"
                >
                  {loggingFollowUp ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : logged ? (
                    <Check className="h-4 w-4" />
                  ) : null}
                  {logged ? "Logged" : "Log as Sent"}
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="flex items-center gap-2"
              >
                {copied ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="whitespace-pre-wrap rounded-lg border bg-muted/50 p-4 text-sm">
              {result}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---- Log as Sent Dialog ---- */}
      <Dialog open={showLogDialog} onOpenChange={setShowLogDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Log Follow-up as Sent</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-muted-foreground">
              Select the application to mark as <span className="font-medium text-yellow-400">Follow-up Sent</span>:
            </p>
            <Select
              value={selectedAppId?.toString() ?? ""}
              onValueChange={(v) => setSelectedAppId(Number(v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select application..." />
              </SelectTrigger>
              <SelectContent>
                {applications.map((app) => (
                  <SelectItem key={app.id} value={app.id.toString()}>
                    {app.company} — {app.role}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLogDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirmLog} disabled={!selectedAppId || loggingFollowUp}>
              {loggingFollowUp ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <Suspense>
      <MessagesPageInner />
    </Suspense>
  );
}

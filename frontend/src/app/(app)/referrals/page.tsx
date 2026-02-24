"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getReferrals,
  createReferral,
  updateReferralStatus,
  getReferralStats,
  getReferralFollowUps,
  generateReferralRequest,
} from "@/lib/api";
import type { Referral, ReferralStats } from "@/lib/types";

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
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import {
  Users,
  UserPlus,
  ChevronDown,
  Loader2,
  AlertTriangle,
  ExternalLink,
  Mail,
  Copy,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUSES = [
  "Identified",
  "Contacted",
  "Responded",
  "Referral Requested",
  "Referral Received",
  "Interview",
] as const;

const RELATIONSHIPS = [
  "Colleague",
  "Alumni",
  "LinkedIn Connection",
  "Friend",
  "Meetup/Conference",
  "Online Community",
  "Other",
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusBadgeClass(status: string): string {
  switch (status) {
    case "Identified":
      return "bg-gray-500/15 text-gray-400 border-gray-500/30";
    case "Contacted":
      return "bg-blue-500/15 text-blue-400 border-blue-500/30";
    case "Responded":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    case "Referral Requested":
      return "bg-purple-500/15 text-purple-400 border-purple-500/30";
    case "Referral Received":
      return "bg-green-500/15 text-green-400 border-green-500/30";
    case "Interview":
      return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    default:
      return "bg-gray-500/15 text-gray-400 border-gray-500/30";
  }
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ReferralsPage() {
  // ---- Data state ----
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [followUps, setFollowUps] = useState<Referral[]>([]);

  // ---- Add Contact form state ----
  const [formData, setFormData] = useState({
    contact_name: "",
    company: "",
    contact_role: "",
    relationship: "",
    linkedin_url: "",
    email: "",
    notes: "",
  });
  const [creating, setCreating] = useState(false);

  // ---- Network filters ----
  const [statusFilter, setStatusFilter] = useState("All");
  const [companyFilter, setCompanyFilter] = useState("");

  // ---- Per-referral status update state ----
  const [statusUpdates, setStatusUpdates] = useState<Record<number, string>>(
    {}
  );
  const [updatingStatus, setUpdatingStatus] = useState<Record<number, boolean>>(
    {}
  );

  // ---- Per-referral generate request state ----
  const [roleApplyingFor, setRoleApplyingFor] = useState<
    Record<number, string>
  >({});
  const [generatingRequest, setGeneratingRequest] = useState<
    Record<number, boolean>
  >({});
  const [generatedMessages, setGeneratedMessages] = useState<
    Record<number, string>
  >({});
  const [copiedMessage, setCopiedMessage] = useState<Record<number, boolean>>(
    {}
  );

  // ---- Collapsible open state ----
  const [openCards, setOpenCards] = useState<Record<number, boolean>>({});

  // ---- Fetch all data ----
  const fetchData = useCallback(async () => {
    try {
      const [statsRes, referralsRes, followUpsRes] = await Promise.all([
        getReferralStats(),
        getReferrals(),
        getReferralFollowUps(),
      ]);
      setStats(statsRes);
      setReferrals(referralsRes);
      setFollowUps(followUpsRes);
    } catch (err) {
      console.error("Failed to load referral data", err);
      toast.error("Failed to load referral data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ---- Handlers ----

  async function handleAddContact() {
    if (!formData.contact_name.trim() || !formData.company.trim()) {
      toast.error("Contact name and company are required.");
      return;
    }

    setCreating(true);
    try {
      await createReferral({
        contact_name: formData.contact_name.trim(),
        company: formData.company.trim(),
        contact_role: formData.contact_role.trim() || undefined,
        relationship: formData.relationship || undefined,
        linkedin_url: formData.linkedin_url.trim() || undefined,
        email: formData.email.trim() || undefined,
        notes: formData.notes.trim() || undefined,
      });
      toast.success("Contact added successfully!");
      setFormData({
        contact_name: "",
        company: "",
        contact_role: "",
        relationship: "",
        linkedin_url: "",
        email: "",
        notes: "",
      });
      await fetchData();
    } catch (err) {
      console.error("Failed to add contact", err);
      toast.error("Failed to add contact. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateStatus(id: number) {
    const newStatus = statusUpdates[id];
    if (!newStatus) {
      toast.error("Please select a status.");
      return;
    }

    setUpdatingStatus((prev) => ({ ...prev, [id]: true }));
    try {
      await updateReferralStatus(id, newStatus);
      toast.success("Status updated successfully!");
      setStatusUpdates((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      await fetchData();
    } catch (err) {
      console.error("Failed to update status", err);
      toast.error("Failed to update status. Please try again.");
    } finally {
      setUpdatingStatus((prev) => ({ ...prev, [id]: false }));
    }
  }

  async function handleGenerateRequest(referral: Referral) {
    const role = roleApplyingFor[referral.id];
    if (!role?.trim()) {
      toast.error("Please enter the role you are applying for.");
      return;
    }

    setGeneratingRequest((prev) => ({ ...prev, [referral.id]: true }));
    try {
      const response = await generateReferralRequest({
        contact_name: referral.contact_name,
        contact_role: referral.contact_role || undefined,
        company: referral.company,
        role_applying_for: role.trim(),
        relationship: referral.relationship || undefined,
      });
      setGeneratedMessages((prev) => ({
        ...prev,
        [referral.id]: response.content,
      }));
    } catch (err) {
      console.error("Failed to generate referral request", err);
      toast.error("Failed to generate referral request. Please try again.");
    } finally {
      setGeneratingRequest((prev) => ({ ...prev, [referral.id]: false }));
    }
  }

  async function handleCopyMessage(id: number) {
    const message = generatedMessages[id];
    if (!message) return;
    try {
      await navigator.clipboard.writeText(message);
      setCopiedMessage((prev) => ({ ...prev, [id]: true }));
      toast.success("Copied to clipboard!");
      setTimeout(() => {
        setCopiedMessage((prev) => ({ ...prev, [id]: false }));
      }, 2000);
    } catch {
      toast.error("Failed to copy to clipboard.");
    }
  }

  // ---- Filtered referrals ----
  const filteredReferrals = referrals.filter((r) => {
    if (statusFilter !== "All" && r.status !== statusFilter) return false;
    if (
      companyFilter.trim() &&
      !r.company.toLowerCase().includes(companyFilter.toLowerCase())
    )
      return false;
    return true;
  });

  // ---- Loading state ----
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ---- Stat cards config ----
  const statCards = [
    {
      label: "Total Contacts",
      value: stats?.total ?? 0,
    },
    {
      label: "Referrals Requested",
      value: stats?.requested ?? 0,
    },
    {
      label: "Referrals Received",
      value: stats?.received ?? 0,
    },
    {
      label: "Interview Rate",
      value: `${stats?.interview_rate ?? 0}%`,
    },
    {
      label: "Follow-ups Due",
      value: stats?.follow_ups_due ?? 0,
    },
  ];

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Users className="h-8 w-8" />
          Referrals
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your referral contacts and track your referral pipeline.
        </p>
      </div>

      {/* ---- Stat Cards ---- */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {statCards.map((s) => (
          <Card key={s.label}>
            <CardContent className="flex flex-col items-center gap-2 pt-6 text-center">
              <p className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
                {s.label}
              </p>
              <p className="text-3xl font-bold">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ---- Tabs ---- */}
      <Tabs defaultValue="add">
        <TabsList>
          <TabsTrigger value="add">Add Contact</TabsTrigger>
          <TabsTrigger value="network">My Network</TabsTrigger>
          <TabsTrigger value="followups">Follow-ups Due</TabsTrigger>
        </TabsList>

        {/* ============================================================== */}
        {/* TAB 1 -- Add Contact                                           */}
        {/* ============================================================== */}
        <TabsContent value="add" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                Add Referral Contact
              </CardTitle>
              <CardDescription>
                Add a new contact to your referral network.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Contact Name */}
              <div className="space-y-2">
                <Label htmlFor="contact_name">Contact Name *</Label>
                <Input
                  id="contact_name"
                  placeholder="e.g. Jane Smith"
                  value={formData.contact_name}
                  onChange={(e) =>
                    setFormData((p) => ({
                      ...p,
                      contact_name: e.target.value,
                    }))
                  }
                />
              </div>

              {/* Company */}
              <div className="space-y-2">
                <Label htmlFor="company">Company *</Label>
                <Input
                  id="company"
                  placeholder="e.g. Google"
                  value={formData.company}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, company: e.target.value }))
                  }
                />
              </div>

              {/* Their Role */}
              <div className="space-y-2">
                <Label htmlFor="contact_role">Their Role</Label>
                <Input
                  id="contact_role"
                  placeholder="e.g. Senior Software Engineer"
                  value={formData.contact_role}
                  onChange={(e) =>
                    setFormData((p) => ({
                      ...p,
                      contact_role: e.target.value,
                    }))
                  }
                />
              </div>

              {/* Relationship */}
              <div className="space-y-2">
                <Label htmlFor="relationship">Relationship</Label>
                <Select
                  value={formData.relationship}
                  onValueChange={(v) =>
                    setFormData((p) => ({ ...p, relationship: v }))
                  }
                >
                  <SelectTrigger id="relationship">
                    <SelectValue placeholder="Select relationship" />
                  </SelectTrigger>
                  <SelectContent>
                    {RELATIONSHIPS.map((rel) => (
                      <SelectItem key={rel} value={rel}>
                        {rel}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* LinkedIn URL */}
              <div className="space-y-2">
                <Label htmlFor="linkedin_url">LinkedIn URL</Label>
                <Input
                  id="linkedin_url"
                  placeholder="https://linkedin.com/in/janesmith"
                  value={formData.linkedin_url}
                  onChange={(e) =>
                    setFormData((p) => ({
                      ...p,
                      linkedin_url: e.target.value,
                    }))
                  }
                />
              </div>

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="jane@company.com"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, email: e.target.value }))
                  }
                />
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="How you know them, context for the referral..."
                  value={formData.notes}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, notes: e.target.value }))
                  }
                />
              </div>

              {/* Submit */}
              <Button
                onClick={handleAddContact}
                disabled={
                  creating ||
                  !formData.contact_name.trim() ||
                  !formData.company.trim()
                }
                className="w-full sm:w-auto"
              >
                {creating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Add Contact
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============================================================== */}
        {/* TAB 2 -- My Network                                            */}
        {/* ============================================================== */}
        <TabsContent value="network" className="space-y-6">
          {/* Filter Row */}
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="w-full sm:w-48">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All</SelectItem>
                  {STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full sm:w-64">
              <Input
                placeholder="Filter by company..."
                value={companyFilter}
                onChange={(e) => setCompanyFilter(e.target.value)}
              />
            </div>
          </div>

          {/* Referral Cards */}
          {filteredReferrals.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-muted-foreground text-sm text-center">
                  No contacts found. Add some contacts to get started!
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredReferrals.map((referral) => (
                <Collapsible
                  key={referral.id}
                  open={openCards[referral.id] ?? false}
                  onOpenChange={(open) =>
                    setOpenCards((prev) => ({ ...prev, [referral.id]: open }))
                  }
                >
                  <Card>
                    <CollapsibleTrigger asChild>
                      <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 flex-wrap">
                            <Badge className={statusBadgeClass(referral.status)}>
                              {referral.status}
                            </Badge>
                            <span className="font-bold">
                              {referral.contact_name}
                            </span>
                            <span className="text-muted-foreground">
                              {referral.company}
                            </span>
                            {referral.contact_role && (
                              <span className="text-muted-foreground text-sm">
                                &middot; {referral.contact_role}
                              </span>
                            )}
                          </div>
                          <ChevronDown
                            className={cn(
                              "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                              openCards[referral.id] && "rotate-180"
                            )}
                          />
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <CardContent className="space-y-4 pt-0">
                        <Separator />

                        {/* Contact Details */}
                        <div className="grid gap-3 sm:grid-cols-2">
                          {referral.relationship && (
                            <div className="space-y-1">
                              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                Relationship
                              </p>
                              <p className="text-sm">{referral.relationship}</p>
                            </div>
                          )}

                          {referral.linkedin_url && (
                            <div className="space-y-1">
                              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                LinkedIn
                              </p>
                              <a
                                href={referral.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-sm text-blue-400 hover:underline"
                              >
                                Profile
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            </div>
                          )}

                          {referral.email && (
                            <div className="space-y-1">
                              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                Email
                              </p>
                              <a
                                href={`mailto:${referral.email}`}
                                className="inline-flex items-center gap-1 text-sm text-blue-400 hover:underline"
                              >
                                {referral.email}
                                <Mail className="h-3 w-3" />
                              </a>
                            </div>
                          )}

                          {referral.last_contacted && (
                            <div className="space-y-1">
                              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                Last Contacted
                              </p>
                              <p className="text-sm">
                                {referral.last_contacted}
                              </p>
                            </div>
                          )}

                          {referral.follow_up_date && (
                            <div className="space-y-1">
                              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                Follow-up Date
                              </p>
                              <p className="text-sm">
                                {referral.follow_up_date}
                              </p>
                            </div>
                          )}
                        </div>

                        {referral.notes && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                              Notes
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {referral.notes}
                            </p>
                          </div>
                        )}

                        <Separator />

                        {/* Status Update */}
                        <div className="space-y-2">
                          <p className="text-sm font-medium">Update Status</p>
                          <div className="flex flex-col gap-2 sm:flex-row">
                            <Select
                              value={statusUpdates[referral.id] ?? ""}
                              onValueChange={(v) =>
                                setStatusUpdates((prev) => ({
                                  ...prev,
                                  [referral.id]: v,
                                }))
                              }
                            >
                              <SelectTrigger className="w-full sm:w-48">
                                <SelectValue placeholder="Select status" />
                              </SelectTrigger>
                              <SelectContent>
                                {STATUSES.map((s) => (
                                  <SelectItem key={s} value={s}>
                                    {s}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Button
                              onClick={() => handleUpdateStatus(referral.id)}
                              disabled={
                                !statusUpdates[referral.id] ||
                                updatingStatus[referral.id]
                              }
                              size="sm"
                            >
                              {updatingStatus[referral.id] ? (
                                <>
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                  Updating...
                                </>
                              ) : (
                                "Update Status"
                              )}
                            </Button>
                          </div>
                        </div>

                        {/* Generate Referral Request (only for Responded / Referral Requested) */}
                        {(referral.status === "Responded" ||
                          referral.status === "Referral Requested") && (
                          <>
                            <Separator />
                            <div className="space-y-3">
                              <p className="text-sm font-medium">
                                Generate Referral Request Message
                              </p>
                              <div className="flex flex-col gap-2 sm:flex-row">
                                <Input
                                  placeholder="Role you are applying for..."
                                  value={roleApplyingFor[referral.id] ?? ""}
                                  onChange={(e) =>
                                    setRoleApplyingFor((prev) => ({
                                      ...prev,
                                      [referral.id]: e.target.value,
                                    }))
                                  }
                                  className="flex-1"
                                />
                                <Button
                                  onClick={() =>
                                    handleGenerateRequest(referral)
                                  }
                                  disabled={
                                    generatingRequest[referral.id] ||
                                    !roleApplyingFor[referral.id]?.trim()
                                  }
                                  size="sm"
                                >
                                  {generatingRequest[referral.id] ? (
                                    <>
                                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                      Generating...
                                    </>
                                  ) : (
                                    "Generate Referral Request"
                                  )}
                                </Button>
                              </div>

                              {generatedMessages[referral.id] && (
                                <Card>
                                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm">
                                      Generated Message
                                    </CardTitle>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() =>
                                        handleCopyMessage(referral.id)
                                      }
                                      className="flex items-center gap-2"
                                    >
                                      {copiedMessage[referral.id] ? (
                                        <Check className="h-4 w-4" />
                                      ) : (
                                        <Copy className="h-4 w-4" />
                                      )}
                                      {copiedMessage[referral.id]
                                        ? "Copied"
                                        : "Copy"}
                                    </Button>
                                  </CardHeader>
                                  <CardContent>
                                    <div className="whitespace-pre-wrap rounded-lg border bg-muted/50 p-4 text-sm">
                                      {generatedMessages[referral.id]}
                                    </div>
                                  </CardContent>
                                </Card>
                              )}
                            </div>
                          </>
                        )}
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ============================================================== */}
        {/* TAB 3 -- Follow-ups Due                                        */}
        {/* ============================================================== */}
        <TabsContent value="followups" className="space-y-6">
          {followUps.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-muted-foreground text-sm text-center">
                  No follow-ups due. You&apos;re all caught up!
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {followUps.map((referral) => (
                <Card
                  key={referral.id}
                  className="border-amber-500/40 bg-amber-500/5"
                >
                  <CardContent className="pt-6 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold">{referral.contact_name}</p>
                      <Badge className={statusBadgeClass(referral.status)}>
                        {referral.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {referral.company}
                    </p>
                    <Separator />
                    <div className="flex items-center justify-between text-xs">
                      {referral.last_contacted && (
                        <span className="text-muted-foreground">
                          Last contacted: {referral.last_contacted}
                        </span>
                      )}
                      {referral.follow_up_date && (
                        <span className="text-amber-400 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {referral.follow_up_date}
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

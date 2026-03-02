"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  getApplications,
  createApplication,
  updateApplicationStatus,
  updateApplicationNotes,
  deleteApplication,
  getDemos,
  createDemo,
  updateDemo,
} from "@/lib/api";
import type { Application, MiniDemo } from "@/lib/types";

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
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  ClipboardList,
  Plus,
  ChevronDown,
  Trash2,
  Loader2,
  ExternalLink,
  Pencil,
  MessageSquare,
  Mail,
  StickyNote,
  Check,
  X as XIcon,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PLATFORMS = [
  "LinkedIn",
  "Wellfound",
  "YC WaaS",
  "Internshala",
  "Instahyre",
  "Naukri",
  "Indeed",
  "HasJob",
  "Direct",
  "Referral",
  "Other",
] as const;

const STATUSES = [
  "Applied",
  "Assignment Submitted",
  "Interview",
  "Offer",
  "Rejected",
  "Ghosted",
] as const;

const STATUS_COLORS: Record<string, string> = {
  Applied: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  "Assignment Submitted": "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  Interview: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  Offer: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  Rejected: "bg-red-500/15 text-red-400 border-red-500/30",
  Ghosted: "bg-gray-500/15 text-gray-400 border-gray-500/30",
};

const DEMO_STATUSES = ["Idea", "Building", "Deployed", "Shipped"] as const;

// ---------------------------------------------------------------------------
// Helper: status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(STATUS_COLORS[status] || "border-border")}
    >
      {status}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function TrackerPage() {
  const router = useRouter();

  // ---- Applications state ----
  const [applications, setApplications] = useState<Application[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);

  // ---- Add application form ----
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({
    company: "",
    role: "",
    job_type: "Job",
    platform: "LinkedIn",
    url: "",
    noc_compatible: "Unknown",
    conversion: "N/A",
    salary: "",
    notes: "",
  });
  const [addLoading, setAddLoading] = useState(false);

  // ---- Filters ----
  const [filterStatus, setFilterStatus] = useState("All");
  const [filterType, setFilterType] = useState("All");
  const [filterPlatform, setFilterPlatform] = useState("All");

  // ---- Application status update ----
  const [statusUpdates, setStatusUpdates] = useState<Record<number, string>>(
    {}
  );
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  // ---- Delete dialog ----
  const [deleteTarget, setDeleteTarget] = useState<Application | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ---- Notes editing ----
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  // ---- Mini Demos state ----
  const [demos, setDemos] = useState<MiniDemo[]>([]);
  const [allDemos, setAllDemos] = useState<MiniDemo[]>([]);
  const [demosLoading, setDemosLoading] = useState(true);

  // ---- Add demo form ----
  const [demoForm, setDemoForm] = useState({
    company: "",
    role: "",
    demo_idea: "",
  });
  const [demoAddLoading, setDemoAddLoading] = useState(false);

  // ---- Demo update forms (keyed by id) ----
  const [demoUpdates, setDemoUpdates] = useState<
    Record<
      number,
      {
        status: string;
        github_url: string;
        demo_url: string;
        hours_spent: string;
        result: string;
      }
    >
  >({});
  const [demoUpdatingId, setDemoUpdatingId] = useState<number | null>(null);

  // ---- Fetch helpers ----
  const fetchApplications = useCallback(async () => {
    setAppsLoading(true);
    try {
      const filters: { status?: string; type?: string; platform?: string } = {};
      if (filterStatus !== "All") filters.status = filterStatus;
      if (filterType !== "All") filters.type = filterType;
      if (filterPlatform !== "All") filters.platform = filterPlatform;
      const data = await getApplications(filters);
      setApplications(data);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load applications"
      );
    } finally {
      setAppsLoading(false);
    }
  }, [filterStatus, filterType, filterPlatform]);

  const fetchDemos = useCallback(async () => {
    setDemosLoading(true);
    try {
      const [active, all] = await Promise.all([
        getDemos(true),
        getDemos(false),
      ]);
      setDemos(active);
      setAllDemos(all);

      // Initialise update forms for active demos
      const updates: typeof demoUpdates = {};
      for (const d of active) {
        updates[d.id] = {
          status: d.status || "Idea",
          github_url: d.github_url || "",
          demo_url: d.demo_url || "",
          hours_spent: d.hours_spent != null ? String(d.hours_spent) : "",
          result: d.result || "",
        };
      }
      setDemoUpdates(updates);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load demos"
      );
    } finally {
      setDemosLoading(false);
    }
  }, []);

  // ---- Load on mount + filter change ----
  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  useEffect(() => {
    fetchDemos();
  }, [fetchDemos]);

  // ---- Handlers: Applications ----
  async function handleAddApplication() {
    if (!addForm.company.trim() || !addForm.role.trim()) return;
    setAddLoading(true);
    try {
      await createApplication({
        company: addForm.company.trim(),
        role: addForm.role.trim(),
        job_type: addForm.job_type,
        platform: addForm.platform,
        url: addForm.url.trim() || undefined,
        noc_compatible: addForm.noc_compatible,
        conversion: addForm.conversion,
        salary: addForm.salary.trim() || undefined,
        notes: addForm.notes.trim() || undefined,
      });
      toast.success("Application logged successfully");
      setAddForm({
        company: "",
        role: "",
        job_type: "Job",
        platform: "LinkedIn",
        url: "",
        noc_compatible: "Unknown",
        conversion: "N/A",
        salary: "",
        notes: "",
      });
      setAddOpen(false);
      await fetchApplications();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to add application"
      );
    } finally {
      setAddLoading(false);
    }
  }

  async function handleUpdateStatus(id: number) {
    const newStatus = statusUpdates[id];
    if (!newStatus) return;
    setUpdatingId(id);
    try {
      await updateApplicationStatus(id, newStatus);
      toast.success("Status updated");
      await fetchApplications();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update status"
      );
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteApplication(deleteTarget.id);
      toast.success("Application deleted");
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await fetchApplications();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to delete application"
      );
    } finally {
      setDeleting(false);
    }
  }

  // ---- Handlers: Demos ----
  async function handleAddDemo() {
    if (
      !demoForm.company.trim() ||
      !demoForm.role.trim() ||
      !demoForm.demo_idea.trim()
    )
      return;
    setDemoAddLoading(true);
    try {
      await createDemo({
        company: demoForm.company.trim(),
        role: demoForm.role.trim(),
        demo_idea: demoForm.demo_idea.trim(),
      });
      toast.success("Demo added");
      setDemoForm({ company: "", role: "", demo_idea: "" });
      await fetchDemos();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to add demo"
      );
    } finally {
      setDemoAddLoading(false);
    }
  }

  async function handleUpdateDemo(id: number) {
    const form = demoUpdates[id];
    if (!form) return;
    setDemoUpdatingId(id);
    try {
      await updateDemo(id, {
        status: form.status,
        github_url: form.github_url.trim() || undefined,
        demo_url: form.demo_url.trim() || undefined,
        hours_spent: form.hours_spent ? Number(form.hours_spent) : undefined,
        result: form.result.trim() || undefined,
      });
      toast.success("Demo updated");
      await fetchDemos();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update demo"
      );
    } finally {
      setDemoUpdatingId(null);
    }
  }

  // ---- Render ----
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <ClipboardList className="h-8 w-8" />
          Application Tracker
        </h1>
        <p className="text-muted-foreground mt-1">
          Track your job applications and mini demos in one place.
        </p>
      </div>

      {/* ================================================================== */}
      {/* Section 1: Add New Application (Collapsible)                       */}
      {/* ================================================================== */}
      <Card>
        <Collapsible open={addOpen} onOpenChange={setAddOpen}>
          <CardHeader className="pb-3">
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                className="flex w-full items-center justify-between px-0 hover:bg-transparent"
              >
                <span className="flex items-center gap-2 text-lg font-semibold">
                  <Plus className="h-5 w-5" />
                  Add New Application
                </span>
                <ChevronDown
                  className={cn(
                    "h-5 w-5 transition-transform",
                    addOpen && "rotate-180"
                  )}
                />
              </Button>
            </CollapsibleTrigger>
          </CardHeader>

          <CollapsibleContent>
            <CardContent className="pt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Company */}
                <div className="space-y-2">
                  <Label htmlFor="app-company">Company *</Label>
                  <Input
                    id="app-company"
                    placeholder="e.g. Shopify"
                    value={addForm.company}
                    onChange={(e) =>
                      setAddForm((p) => ({ ...p, company: e.target.value }))
                    }
                  />
                </div>

                {/* Role */}
                <div className="space-y-2">
                  <Label htmlFor="app-role">Role *</Label>
                  <Input
                    id="app-role"
                    placeholder="e.g. Full-Stack Developer"
                    value={addForm.role}
                    onChange={(e) =>
                      setAddForm((p) => ({ ...p, role: e.target.value }))
                    }
                  />
                </div>

                {/* Type */}
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select
                    value={addForm.job_type}
                    onValueChange={(v) =>
                      setAddForm((p) => ({ ...p, job_type: v }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Job">Job</SelectItem>
                      <SelectItem value="Internship">Internship</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Platform */}
                <div className="space-y-2">
                  <Label>Platform</Label>
                  <Select
                    value={addForm.platform}
                    onValueChange={(v) =>
                      setAddForm((p) => ({ ...p, platform: v }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLATFORMS.map((p) => (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* URL */}
                <div className="space-y-2">
                  <Label htmlFor="app-url">URL</Label>
                  <Input
                    id="app-url"
                    placeholder="https://..."
                    value={addForm.url}
                    onChange={(e) =>
                      setAddForm((p) => ({ ...p, url: e.target.value }))
                    }
                  />
                </div>

                {/* NOC Compatible */}
                <div className="space-y-2">
                  <Label>NOC Compatible</Label>
                  <Select
                    value={addForm.noc_compatible}
                    onValueChange={(v) =>
                      setAddForm((p) => ({ ...p, noc_compatible: v }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Yes">Yes</SelectItem>
                      <SelectItem value="No">No</SelectItem>
                      <SelectItem value="Unknown">Unknown</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Conversion Potential */}
                <div className="space-y-2">
                  <Label>Conversion Potential</Label>
                  <Select
                    value={addForm.conversion}
                    onValueChange={(v) =>
                      setAddForm((p) => ({ ...p, conversion: v }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="N/A">N/A</SelectItem>
                      <SelectItem value="Likely">Likely</SelectItem>
                      <SelectItem value="Unlikely">Unlikely</SelectItem>
                      <SelectItem value="Unknown">Unknown</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Salary */}
                <div className="space-y-2">
                  <Label htmlFor="app-salary">Salary</Label>
                  <Input
                    id="app-salary"
                    placeholder="e.g. $80,000"
                    value={addForm.salary}
                    onChange={(e) =>
                      setAddForm((p) => ({ ...p, salary: e.target.value }))
                    }
                  />
                </div>

                {/* Notes */}
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="app-notes">Notes</Label>
                  <Textarea
                    id="app-notes"
                    placeholder="Any additional notes..."
                    value={addForm.notes}
                    onChange={(e) =>
                      setAddForm((p) => ({ ...p, notes: e.target.value }))
                    }
                  />
                </div>

                {/* Submit */}
                <div className="md:col-span-2">
                  <Button
                    onClick={handleAddApplication}
                    disabled={
                      addLoading ||
                      !addForm.company.trim() ||
                      !addForm.role.trim()
                    }
                    className="w-full"
                  >
                    {addLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="mr-2 h-4 w-4" />
                    )}
                    {addLoading ? "Logging..." : "Log Application"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      {/* ================================================================== */}
      {/* Section 2: Filters                                                 */}
      {/* ================================================================== */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Filter by Status */}
        <div className="space-y-2">
          <Label>Filter by Status</Label>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-full">
              <SelectValue />
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

        {/* Filter by Type */}
        <div className="space-y-2">
          <Label>Filter by Type</Label>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All</SelectItem>
              <SelectItem value="Job">Job</SelectItem>
              <SelectItem value="Internship">Internship</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Filter by Platform */}
        <div className="space-y-2">
          <Label>Filter by Platform</Label>
          <Select value={filterPlatform} onValueChange={setFilterPlatform}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All</SelectItem>
              {PLATFORMS.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* ================================================================== */}
      {/* Section 3: Applications List                                       */}
      {/* ================================================================== */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">
          Applications{" "}
          <span className="text-muted-foreground font-normal text-base">
            ({applications.length})
          </span>
        </h2>

        {appsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : applications.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No applications found. Add one above to get started.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {applications.map((app) => (
              <Card key={app.id}>
                <Collapsible>
                  <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors pb-3 pt-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      {/* Inline status dropdown */}
                      <div onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
                        <Select
                          value={app.status}
                          onValueChange={async (v) => {
                            setUpdatingId(app.id);
                            try {
                              await updateApplicationStatus(app.id, v);
                              toast.success(`Status → ${v}`);
                              await fetchApplications();
                            } catch {
                              toast.error("Failed to update status");
                            } finally {
                              setUpdatingId(null);
                            }
                          }}
                        >
                          <SelectTrigger
                            className={cn(
                              "w-[130px] h-7 text-xs font-medium",
                              STATUS_COLORS[app.status] || "border-border"
                            )}
                          >
                            {updatingId === app.id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <SelectValue />
                            )}
                          </SelectTrigger>
                          <SelectContent>
                            {STATUSES.map((s) => (
                              <SelectItem key={s} value={s}>
                                {s}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <CollapsibleTrigger asChild>
                        <div className="flex items-center gap-3 flex-1 min-w-0 cursor-pointer">
                          <span className="font-bold truncate">{app.company}</span>
                          <span className="text-muted-foreground truncate">
                            {app.role}
                          </span>
                          <Badge variant="secondary">{app.platform}</Badge>
                        </div>
                      </CollapsibleTrigger>

                      {/* Quick action buttons */}
                      <TooltipProvider delayDuration={300}>
                        <div className="ml-auto flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => {
                                  const params = new URLSearchParams({
                                    company: app.company,
                                    role: app.role,
                                    type: "follow-up",
                                  });
                                  router.push(`/messages?${params.toString()}`);
                                }}
                              >
                                <MessageSquare className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Follow-up</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => {
                                  const params = new URLSearchParams({
                                    company: app.company,
                                    role: app.role,
                                    type: "cold-dm",
                                  });
                                  router.push(`/messages?${params.toString()}`);
                                }}
                              >
                                <Mail className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Cold DM</TooltipContent>
                          </Tooltip>
                          <CollapsibleTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-7 w-7">
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </CollapsibleTrigger>
                        </div>
                      </TooltipProvider>
                    </div>
                  </CardHeader>

                  <CollapsibleContent>
                    <CardContent className="pt-0 space-y-4">
                      <Separator />

                      {/* Details grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        {app.date_applied && (
                          <div>
                            <p className="text-muted-foreground">
                              Date Applied
                            </p>
                            <p className="font-medium">{app.date_applied}</p>
                          </div>
                        )}
                        {app.follow_up_date && (
                          <div>
                            <p className="text-muted-foreground">
                              Follow-up Date
                            </p>
                            <p className="font-medium">{app.follow_up_date}</p>
                          </div>
                        )}
                        {app.url && (
                          <div>
                            <p className="text-muted-foreground">URL</p>
                            <a
                              href={app.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-blue-400 hover:underline"
                            >
                              View Listing
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        )}
                        <div>
                          <p className="text-muted-foreground">NOC</p>
                          <p className="font-medium">{app.noc_compatible}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Conversion</p>
                          <p className="font-medium">{app.conversion}</p>
                        </div>
                        {app.salary && (
                          <div>
                            <p className="text-muted-foreground">Salary</p>
                            <p className="font-medium">{app.salary}</p>
                          </div>
                        )}
                      </div>

                      {/* Notes section */}
                      <div className="text-sm">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-muted-foreground">Notes</p>
                          {editingNoteId !== app.id && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => {
                                setEditingNoteId(app.id);
                                setNoteText(app.notes || "");
                              }}
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                        {editingNoteId === app.id ? (
                          <div className="space-y-2">
                            <Textarea
                              value={noteText}
                              onChange={(e) => setNoteText(e.target.value)}
                              placeholder="Add a note..."
                              className="min-h-[80px]"
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                disabled={savingNote}
                                onClick={async () => {
                                  setSavingNote(true);
                                  try {
                                    await updateApplicationNotes(app.id, noteText.trim());
                                    toast.success("Note saved");
                                    setEditingNoteId(null);
                                    await fetchApplications();
                                  } catch {
                                    toast.error("Failed to save note");
                                  } finally {
                                    setSavingNote(false);
                                  }
                                }}
                              >
                                {savingNote ? (
                                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                ) : (
                                  <Check className="mr-1 h-3 w-3" />
                                )}
                                Save
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setEditingNoteId(null)}
                              >
                                <XIcon className="mr-1 h-3 w-3" />
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : app.notes ? (
                          <p className="font-medium whitespace-pre-wrap">
                            {app.notes}
                          </p>
                        ) : (
                          <p className="text-muted-foreground/50 italic">No notes yet</p>
                        )}
                      </div>

                      <Separator />

                      {/* Actions row */}
                      <div className="flex items-center gap-3 flex-wrap">
                        <Dialog
                          open={
                            deleteDialogOpen &&
                            deleteTarget?.id === app.id
                          }
                          onOpenChange={(open) => {
                            setDeleteDialogOpen(open);
                            if (!open) setDeleteTarget(null);
                          }}
                        >
                          <DialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="destructive"
                              className="ml-auto"
                              onClick={() => setDeleteTarget(app)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Confirm Deletion</DialogTitle>
                              <DialogDescription>
                                Are you sure you want to delete the application
                                for{" "}
                                <span className="font-semibold">
                                  {app.role}
                                </span>{" "}
                                at{" "}
                                <span className="font-semibold">
                                  {app.company}
                                </span>
                                ? This action cannot be undone.
                              </DialogDescription>
                            </DialogHeader>
                            <DialogFooter>
                              <Button
                                variant="outline"
                                onClick={() => {
                                  setDeleteDialogOpen(false);
                                  setDeleteTarget(null);
                                }}
                              >
                                Cancel
                              </Button>
                              <Button
                                variant="destructive"
                                onClick={handleDelete}
                                disabled={deleting}
                              >
                                {deleting ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="mr-2 h-4 w-4" />
                                )}
                                {deleting ? "Deleting..." : "Delete"}
                              </Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardContent>
                  </CollapsibleContent>
                </Collapsible>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================== */}
      {/* Section 4: Mini Demos                                              */}
      {/* ================================================================== */}
      <Separator />

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Mini Demos</h2>

        <Tabs defaultValue="active">
          <TabsList>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="add">Add New</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
          </TabsList>

          {/* -------------------------------------------------------------- */}
          {/* Active Demos                                                    */}
          {/* -------------------------------------------------------------- */}
          <TabsContent value="active" className="space-y-4">
            {demosLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : demos.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No active demos. Switch to the &quot;Add New&quot; tab to
                  create one.
                </CardContent>
              </Card>
            ) : (
              demos.map((demo) => {
                const form = demoUpdates[demo.id];
                if (!form) return null;
                return (
                  <Card key={demo.id}>
                    <CardHeader>
                      <CardTitle className="text-base">
                        {demo.company} &mdash; {demo.role}
                      </CardTitle>
                      <CardDescription>{demo.demo_idea}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {/* Status */}
                        <div className="space-y-2">
                          <Label>Status</Label>
                          <Select
                            value={form.status}
                            onValueChange={(v) =>
                              setDemoUpdates((prev) => ({
                                ...prev,
                                [demo.id]: { ...prev[demo.id], status: v },
                              }))
                            }
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {DEMO_STATUSES.map((s) => (
                                <SelectItem key={s} value={s}>
                                  {s}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Hours Spent */}
                        <div className="space-y-2">
                          <Label htmlFor={`demo-hours-${demo.id}`}>
                            Hours Spent
                          </Label>
                          <Input
                            id={`demo-hours-${demo.id}`}
                            type="number"
                            min="0"
                            step="0.5"
                            placeholder="0"
                            value={form.hours_spent}
                            onChange={(e) =>
                              setDemoUpdates((prev) => ({
                                ...prev,
                                [demo.id]: {
                                  ...prev[demo.id],
                                  hours_spent: e.target.value,
                                },
                              }))
                            }
                          />
                        </div>

                        {/* GitHub URL */}
                        <div className="space-y-2">
                          <Label htmlFor={`demo-github-${demo.id}`}>
                            GitHub URL
                          </Label>
                          <Input
                            id={`demo-github-${demo.id}`}
                            placeholder="https://github.com/..."
                            value={form.github_url}
                            onChange={(e) =>
                              setDemoUpdates((prev) => ({
                                ...prev,
                                [demo.id]: {
                                  ...prev[demo.id],
                                  github_url: e.target.value,
                                },
                              }))
                            }
                          />
                        </div>

                        {/* Demo URL */}
                        <div className="space-y-2">
                          <Label htmlFor={`demo-url-${demo.id}`}>
                            Demo URL
                          </Label>
                          <Input
                            id={`demo-url-${demo.id}`}
                            placeholder="https://..."
                            value={form.demo_url}
                            onChange={(e) =>
                              setDemoUpdates((prev) => ({
                                ...prev,
                                [demo.id]: {
                                  ...prev[demo.id],
                                  demo_url: e.target.value,
                                },
                              }))
                            }
                          />
                        </div>

                        {/* Result */}
                        <div className="space-y-2 sm:col-span-2">
                          <Label htmlFor={`demo-result-${demo.id}`}>
                            Result
                          </Label>
                          <Textarea
                            id={`demo-result-${demo.id}`}
                            placeholder="Outcome / feedback..."
                            value={form.result}
                            onChange={(e) =>
                              setDemoUpdates((prev) => ({
                                ...prev,
                                [demo.id]: {
                                  ...prev[demo.id],
                                  result: e.target.value,
                                },
                              }))
                            }
                          />
                        </div>
                      </div>

                      <Button
                        onClick={() => handleUpdateDemo(demo.id)}
                        disabled={demoUpdatingId === demo.id}
                      >
                        {demoUpdatingId === demo.id ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Pencil className="mr-2 h-4 w-4" />
                        )}
                        {demoUpdatingId === demo.id
                          ? "Updating..."
                          : "Update"}
                      </Button>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </TabsContent>

          {/* -------------------------------------------------------------- */}
          {/* Add New Demo                                                    */}
          {/* -------------------------------------------------------------- */}
          <TabsContent value="add" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Add Mini Demo</CardTitle>
                <CardDescription>
                  Track a mini demo you&apos;re building for a company.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="demo-company">Company *</Label>
                    <Input
                      id="demo-company"
                      placeholder="e.g. Stripe"
                      value={demoForm.company}
                      onChange={(e) =>
                        setDemoForm((p) => ({
                          ...p,
                          company: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="demo-role">Role *</Label>
                    <Input
                      id="demo-role"
                      placeholder="e.g. Frontend Engineer"
                      value={demoForm.role}
                      onChange={(e) =>
                        setDemoForm((p) => ({ ...p, role: e.target.value }))
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="demo-idea">Demo Idea *</Label>
                  <Textarea
                    id="demo-idea"
                    placeholder="Describe the mini demo you plan to build..."
                    value={demoForm.demo_idea}
                    onChange={(e) =>
                      setDemoForm((p) => ({
                        ...p,
                        demo_idea: e.target.value,
                      }))
                    }
                  />
                </div>
                <Button
                  onClick={handleAddDemo}
                  disabled={
                    demoAddLoading ||
                    !demoForm.company.trim() ||
                    !demoForm.role.trim() ||
                    !demoForm.demo_idea.trim()
                  }
                  className="w-full"
                >
                  {demoAddLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="mr-2 h-4 w-4" />
                  )}
                  {demoAddLoading ? "Adding..." : "Add Demo"}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* -------------------------------------------------------------- */}
          {/* Results                                                         */}
          {/* -------------------------------------------------------------- */}
          <TabsContent value="results" className="space-y-4">
            {demosLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : allDemos.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No demos yet.
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Company</TableHead>
                        <TableHead>Demo Idea</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Hours</TableHead>
                        <TableHead>Result</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {allDemos.map((demo) => (
                        <TableRow key={demo.id}>
                          <TableCell className="font-medium">
                            {demo.company}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate">
                            {demo.demo_idea}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{demo.status}</Badge>
                          </TableCell>
                          <TableCell>
                            {demo.hours_spent != null
                              ? demo.hours_spent
                              : "-"}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate">
                            {demo.result || "-"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { X, Save, Loader2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Tag Input – reusable for blocked companies
// ---------------------------------------------------------------------------
function TagInput({
  tags,
  onAdd,
  onRemove,
  placeholder,
}: {
  tags: string[];
  onAdd: (tag: string) => void;
  onRemove: (index: number) => void;
  placeholder?: string;
}) {
  const [value, setValue] = useState("");

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = value.trim();
      if (trimmed && !tags.includes(trimmed)) {
        onAdd(trimmed);
      }
      setValue("");
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <Badge key={i} variant="secondary" className="gap-1 pr-1">
            {tag}
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? "Type and press Enter to add"}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settings Page
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [resumeText, setResumeText] = useState("");
  const [blockedCompanies, setBlockedCompanies] = useState<string[]>([]);

  // ------ Load profile on mount ------
  useEffect(() => {
    async function load() {
      try {
        const profile: UserProfile = await getProfile();
        setResumeText(profile.resume_text ?? "");
        setBlockedCompanies(profile.blocked_companies ?? []);
      } catch {
        toast.error("Failed to load profile");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // ------ Save profile ------
  async function handleSave() {
    setSaving(true);
    try {
      const data: UserProfileUpdate = {
        resume_text: resumeText,
        blocked_companies: blockedCompanies,
      };
      await updateProfile(data);
      toast.success("Profile saved successfully");
    } catch {
      toast.error("Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  // ------ Loading state ------
  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ------ Render ------
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>

      {/* ---- Resume ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Resume</CardTitle>
          <p className="text-sm text-muted-foreground">
            Paste your LaTeX resume here. This is used by the JD Analyzer and Resume Tailor.
          </p>
        </CardHeader>
        <CardContent>
          <Textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste your LaTeX resume here..."
            rows={20}
            className="font-mono text-sm"
          />
        </CardContent>
      </Card>

      {/* ---- Blocked Companies ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Blocked Companies</CardTitle>
        </CardHeader>
        <CardContent>
          <TagInput
            tags={blockedCompanies}
            onAdd={(tag) => setBlockedCompanies((prev) => [...prev, tag])}
            onRemove={(i) =>
              setBlockedCompanies((prev) => prev.filter((_, idx) => idx !== i))
            }
            placeholder="Add a company to block and press Enter"
          />
        </CardContent>
      </Card>

      {/* ---- Bottom Save ---- */}
      <div className="flex justify-end pb-8">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>
    </div>
  );
}

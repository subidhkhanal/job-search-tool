"use client";

import { useState, useEffect } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type {
  UserProfile,
  ProjectEntry,
  ExperienceEntry,
  UserProfileUpdate,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, X, Save, Loader2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Tag Input – reusable for skills, target roles, blocked companies, keywords
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

  // Basic info
  const [fullName, setFullName] = useState("");
  const [bio, setBio] = useState("");
  const [education, setEducation] = useState("");
  const [locationPreference, setLocationPreference] = useState("");

  // Tags
  const [skills, setSkills] = useState<string[]>([]);
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [blockedCompanies, setBlockedCompanies] = useState<string[]>([]);

  // Complex lists
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [experience, setExperience] = useState<ExperienceEntry[]>([]);

  // Resume
  const [resumeText, setResumeText] = useState("");

  // ------ Load profile on mount ------
  useEffect(() => {
    async function load() {
      try {
        const profile: UserProfile = await getProfile();
        setFullName(profile.full_name ?? "");
        setBio(profile.bio ?? "");
        setEducation(profile.education ?? "");
        setLocationPreference(profile.location_preference ?? "");
        setSkills(profile.skills ?? []);
        setTargetRoles(profile.target_roles ?? []);
        setBlockedCompanies(profile.blocked_companies ?? []);
        setProjects(profile.projects ?? []);
        setExperience(profile.experience ?? []);
        setResumeText(profile.resume_text ?? "");
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
        full_name: fullName,
        bio,
        education,
        location_preference: locationPreference,
        skills,
        target_roles: targetRoles,
        blocked_companies: blockedCompanies,
        projects,
        experience,
        resume_text: resumeText,
      };
      await updateProfile(data);
      toast.success("Profile saved successfully");
    } catch {
      toast.error("Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  // ------ Project helpers ------
  function addProject() {
    setProjects((prev) => [
      ...prev,
      { name: "", description: "", keywords: [] },
    ]);
  }

  function removeProject(index: number) {
    setProjects((prev) => prev.filter((_, i) => i !== index));
  }

  function updateProject(index: number, field: keyof ProjectEntry, value: string | string[]) {
    setProjects((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p))
    );
  }

  // ------ Experience helpers ------
  function addExperience() {
    setExperience((prev) => [
      ...prev,
      { role: "", company: "", period: "", description: "" },
    ]);
  }

  function removeExperience(index: number) {
    setExperience((prev) => prev.filter((_, i) => i !== index));
  }

  function updateExperience(index: number, field: keyof ExperienceEntry, value: string) {
    setExperience((prev) =>
      prev.map((e, i) => (i === index ? { ...e, [field]: value } : e))
    );
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
          Save Profile
        </Button>
      </div>

      {/* ---- Basic Info ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Basic Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Full Name</label>
            <Input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your full name"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Bio</label>
            <Input
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Short bio"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Education</label>
            <Input
              value={education}
              onChange={(e) => setEducation(e.target.value)}
              placeholder="e.g. B.Sc. Computer Science, University X"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Location Preference</label>
            <Input
              value={locationPreference}
              onChange={(e) => setLocationPreference(e.target.value)}
              placeholder="e.g. Remote, Toronto, Hybrid"
            />
          </div>
        </CardContent>
      </Card>

      {/* ---- Skills ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Skills</CardTitle>
        </CardHeader>
        <CardContent>
          <TagInput
            tags={skills}
            onAdd={(tag) => setSkills((prev) => [...prev, tag])}
            onRemove={(i) => setSkills((prev) => prev.filter((_, idx) => idx !== i))}
            placeholder="Add a skill and press Enter"
          />
        </CardContent>
      </Card>

      {/* ---- Target Roles ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Target Roles</CardTitle>
        </CardHeader>
        <CardContent>
          <TagInput
            tags={targetRoles}
            onAdd={(tag) => setTargetRoles((prev) => [...prev, tag])}
            onRemove={(i) => setTargetRoles((prev) => prev.filter((_, idx) => idx !== i))}
            placeholder="Add a target role and press Enter"
          />
        </CardContent>
      </Card>

      {/* ---- Projects ---- */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Projects</CardTitle>
            <Button variant="outline" size="sm" onClick={addProject}>
              <Plus className="mr-1 h-4 w-4" />
              Add Project
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {projects.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No projects yet. Click &quot;Add Project&quot; to get started.
            </p>
          )}
          {projects.map((project, index) => (
            <Card key={index} className="relative">
              <CardContent className="space-y-3 pt-6">
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-2"
                  onClick={() => removeProject(index)}
                >
                  <X className="h-4 w-4" />
                </Button>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Project Name</label>
                  <Input
                    value={project.name}
                    onChange={(e) => updateProject(index, "name", e.target.value)}
                    placeholder="Project name"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Description</label>
                  <Input
                    value={project.description}
                    onChange={(e) => updateProject(index, "description", e.target.value)}
                    placeholder="Brief description"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Keywords</label>
                  <TagInput
                    tags={project.keywords}
                    onAdd={(tag) =>
                      updateProject(index, "keywords", [...project.keywords, tag])
                    }
                    onRemove={(i) =>
                      updateProject(
                        index,
                        "keywords",
                        project.keywords.filter((_, idx) => idx !== i)
                      )
                    }
                    placeholder="Add keyword and press Enter"
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>

      {/* ---- Experience ---- */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Experience</CardTitle>
            <Button variant="outline" size="sm" onClick={addExperience}>
              <Plus className="mr-1 h-4 w-4" />
              Add Experience
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {experience.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No experience entries yet. Click &quot;Add Experience&quot; to get started.
            </p>
          )}
          {experience.map((exp, index) => (
            <Card key={index} className="relative">
              <CardContent className="space-y-3 pt-6">
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-2"
                  onClick={() => removeExperience(index)}
                >
                  <X className="h-4 w-4" />
                </Button>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Role</label>
                    <Input
                      value={exp.role}
                      onChange={(e) => updateExperience(index, "role", e.target.value)}
                      placeholder="Job title"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Company</label>
                    <Input
                      value={exp.company}
                      onChange={(e) => updateExperience(index, "company", e.target.value)}
                      placeholder="Company name"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Period</label>
                  <Input
                    value={exp.period}
                    onChange={(e) => updateExperience(index, "period", e.target.value)}
                    placeholder="e.g. Jan 2023 - Present"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Description</label>
                  <Textarea
                    value={exp.description}
                    onChange={(e) => updateExperience(index, "description", e.target.value)}
                    placeholder="What did you do in this role?"
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
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

      {/* ---- Resume Text ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Resume Text</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste your raw resume text here..."
            rows={12}
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
          Save Profile
        </Button>
      </div>
    </div>
  );
}

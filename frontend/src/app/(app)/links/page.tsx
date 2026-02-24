import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ExternalLink,
  Star,
  Users,
  Zap,
  Building2,
  BookOpen,
  CheckCircle,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface LinkItem {
  name: string;
  url: string;
  description: string;
}

interface ChecklistItem {
  label: string;
}

interface LinkSection {
  title: string;
  badge: string;
  badgeColor: string;
  icon: React.ElementType;
  links: LinkItem[];
}

const LINK_SECTIONS: LinkSection[] = [
  {
    title: "Tier 0 — Low Competition, High Quality",
    badge: "Best ROI",
    badgeColor: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    icon: Star,
    links: [
      {
        name: "HasJob",
        url: "https://hasjob.co",
        description: "India startup jobs, low noise",
      },
      {
        name: "YC Work at a Startup",
        url: "https://workatastartup.com",
        description: "Direct to YC companies",
      },
      {
        name: "r/developersIndia",
        url: "https://reddit.com/r/developersindia",
        description: "Weekly hiring threads",
      },
      {
        name: "HackerNews Who's Hiring",
        url: "https://news.ycombinator.com/item?id=39562986",
        description: "Monthly thread, global remote",
      },
      {
        name: "Remotive",
        url: "https://remotive.com",
        description: "Curated remote tech jobs",
      },
      {
        name: "Arbeitnow",
        url: "https://arbeitnow.com",
        description: "Remote-friendly European startups",
      },
    ],
  },
  {
    title: "Communities",
    badge: "Network",
    badgeColor: "bg-blue-500/15 text-blue-400 border-blue-500/25",
    icon: Users,
    links: [
      {
        name: "DataTalks.Club Slack",
        url: "https://datatalks.club/slack",
        description: "ML/Data community",
      },
      {
        name: "MLOps Community Slack",
        url: "https://mlops.community",
        description: "MLOps practitioners",
      },
      {
        name: "HasGeek Events",
        url: "https://hasgeek.com",
        description: "Bangalore tech meetups",
      },
      {
        name: "LinkedIn AI Groups",
        url: "https://linkedin.com/groups",
        description: "AI/ML professional groups",
      },
    ],
  },
  {
    title: "Tier 1 — Apply Here First",
    badge: "High Priority",
    badgeColor: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    icon: Zap,
    links: [
      {
        name: "Wellfound / AngelList",
        url: "https://wellfound.com",
        description: "Startup jobs, easy apply",
      },
      {
        name: "YC Work at a Startup",
        url: "https://workatastartup.com",
        description: "YC portfolio companies",
      },
      {
        name: "Reddit hiring threads",
        url: "https://reddit.com/r/forhire",
        description: "Multiple subreddits",
      },
    ],
  },
  {
    title: "Tier 2 — Volume Play",
    badge: "Volume",
    badgeColor: "bg-purple-500/15 text-purple-400 border-purple-500/25",
    icon: Building2,
    links: [
      {
        name: "LinkedIn Jobs",
        url: "https://linkedin.com/jobs",
        description: "Largest job board",
      },
      {
        name: "Internshala",
        url: "https://internshala.com",
        description: "India internships",
      },
      {
        name: "Instahyre",
        url: "https://instahyre.com",
        description: "AI-matched jobs",
      },
      {
        name: "Cutshort",
        url: "https://cutshort.io",
        description: "Tech-focused hiring",
      },
    ],
  },
  {
    title: "Tier 3 — Passive",
    badge: "Passive",
    badgeColor: "bg-gray-500/15 text-gray-400 border-gray-500/25",
    icon: BookOpen,
    links: [
      {
        name: "Naukri",
        url: "https://naukri.com",
        description: "India's largest job portal",
      },
      {
        name: "Indeed",
        url: "https://indeed.com",
        description: "Global aggregator",
      },
    ],
  },
  {
    title: "Startup Research",
    badge: "Research",
    badgeColor: "bg-cyan-500/15 text-cyan-400 border-cyan-500/25",
    icon: BookOpen,
    links: [
      {
        name: "Inc42",
        url: "https://inc42.com",
        description: "Indian startup news",
      },
      {
        name: "YourStory",
        url: "https://yourstory.com",
        description: "Startup stories & funding",
      },
      {
        name: "Tracxn",
        url: "https://tracxn.com",
        description: "Startup data & analytics",
      },
    ],
  },
];

const CHECKLIST_ITEMS: ChecklistItem[] = [
  { label: "Updated Resume (ATS-optimized)" },
  { label: "Portfolio Website" },
  { label: "GitHub Profile (pinned projects)" },
  { label: "LinkedIn (headline + about optimized)" },
  { label: "Cover Letter Template" },
];

/* ------------------------------------------------------------------ */
/*  Components                                                         */
/* ------------------------------------------------------------------ */

function LinkRow({ item }: { item: LinkItem }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-center justify-between gap-4 rounded-lg border border-transparent px-4 py-3 transition-colors hover:border-border hover:bg-muted/50"
    >
      <div className="flex flex-col gap-0.5">
        <span className="flex items-center gap-2 text-sm font-medium text-foreground group-hover:text-primary">
          {item.name}
          <ExternalLink className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </span>
        <span className="text-xs text-muted-foreground">
          {item.description}
        </span>
      </div>
      <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground/50" />
    </a>
  );
}

function LinkSectionCard({ section }: { section: LinkSection }) {
  const Icon = section.icon;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg">{section.title}</CardTitle>
        </div>
        <CardDescription>
          <Badge
            variant="outline"
            className={section.badgeColor}
          >
            {section.badge}
          </Badge>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-1">
        {section.links.map((link) => (
          <LinkRow key={link.name + link.url} item={link} />
        ))}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function QuickLinksPage() {
  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Quick Links</h1>
        <p className="text-muted-foreground mt-1">
          Curated job boards, communities, and resources — organized by
          priority.
        </p>
      </div>

      {/* ---- Link Sections ---- */}
      <div className="grid gap-6 lg:grid-cols-2">
        {LINK_SECTIONS.map((section) => (
          <LinkSectionCard key={section.title} section={section} />
        ))}
      </div>

      <Separator />

      {/* ---- Your Assets Checklist ---- */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            <CardTitle className="text-lg">Your Assets</CardTitle>
          </div>
          <CardDescription>
            <Badge
              variant="outline"
              className="bg-emerald-500/15 text-emerald-400 border-emerald-500/25"
            >
              Checklist
            </Badge>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-3 sm:grid-cols-2">
            {CHECKLIST_ITEMS.map((item) => (
              <li key={item.label} className="flex items-center gap-3">
                <CheckCircle className="h-4 w-4 shrink-0 text-emerald-400" />
                <span className="text-sm text-foreground">{item.label}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

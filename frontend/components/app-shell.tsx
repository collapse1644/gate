"use client";

import clsx from "clsx";
import {
  BarChart3,
  BookOpen,
  CalendarClock,
  Database,
  GraduationCap,
  LayoutDashboard,
  Library,
  ListChecks,
  Menu,
  Settings,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { useApi } from "@/lib/hooks";

interface Health {
  status: string;
  database: string;
  startup?: { seeded?: boolean; error?: string | null } | null;
}

const GROUPS = [
  {
    label: "Study",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/subjects", label: "Subjects", icon: BookOpen },
      { href: "/library", label: "PYQ Library", icon: Library },
      { href: "/practice", label: "Practice", icon: Target },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/tutor", label: "AI Tutor", icon: Sparkles },
      { href: "/formulas", label: "Formula Bank", icon: GraduationCap },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/revision", label: "Revision", icon: CalendarClock },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/data", label: "Data Management", icon: Database },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { data: health } = useApi<Health>("/health");
  const online = health?.status === "ok";

  return (
    <div className="flex h-full flex-col">
      <Link href="/" onClick={onNavigate} className="flex items-center gap-3 px-5 py-5">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-brand to-brand-2 text-lg font-black text-white shadow-lg shadow-brand/25">
          G
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-accent" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-tight text-ink">GATE CS 2027</div>
          <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted">
            Local-first tutor
          </div>
        </div>
      </Link>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
        {GROUPS.map((group) => (
          <div key={group.label}>
            <div className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-[0.18em] text-muted/70">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    className={clsx(
                      "group flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-[13px] font-medium transition-colors",
                      active
                        ? "bg-brand-soft text-brand"
                        : "text-muted hover:bg-surface-2 hover:text-ink",
                    )}
                  >
                    <Icon
                      className={clsx(
                        "h-4 w-4 shrink-0 transition-colors",
                        active ? "text-brand" : "text-muted group-hover:text-ink",
                      )}
                    />
                    <span>{item.label}</span>
                    {item.href === "/library" ? (
                      <span className="ml-auto rounded-md bg-surface-2 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-muted">
                        PYQ
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="space-y-2 border-t border-line p-3">
        <div className="rounded-xl border border-line bg-surface-2/60 px-3 py-2.5">
          <div className="flex items-center gap-2 text-[11px] font-semibold text-ink">
            <span
              className={clsx(
                "h-2 w-2 rounded-full",
                online ? "bg-accent shadow-[0_0_8px_var(--accent)]" : "bg-danger",
              )}
            />
            {online ? "Backend online" : health === null ? "Connecting…" : "Backend offline"}
          </div>
          <p className="mt-1 text-[10px] leading-relaxed text-muted">
            {health?.startup?.error
              ? "Startup warning — open Settings"
              : "Your PDFs and keys stay on this machine."}
          </p>
        </div>
        <ThemeToggle />
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[260px] border-r border-line bg-surface/80 backdrop-blur-xl lg:block">
        <SidebarContent />
      </aside>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <aside className="animate-rise absolute inset-y-0 left-0 w-[272px] border-r border-line bg-surface shadow-2xl">
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-[260px]">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-line bg-canvas/80 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn-secondary h-9 w-9 p-0 lg:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="hidden items-center gap-2 text-[11px] font-medium text-muted sm:flex">
              <ListChecks className="h-3.5 w-3.5 text-accent" />
              Official GATE 2027 CS syllabus
              <span className="text-line">/</span>
              <span className="text-ink">IIT Madras</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/data" className="btn-secondary btn-sm hidden sm:inline-flex">
              <Database className="h-3.5 w-3.5" />
              Upload PYQs
            </Link>
            <Link href="/tutor" className="btn-primary btn-sm">
              <Sparkles className="h-3.5 w-3.5" />
              Ask tutor
            </Link>
            <div className="lg:hidden">
              <ThemeToggle compact />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}

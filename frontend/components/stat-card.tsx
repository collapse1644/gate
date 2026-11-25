import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { ProgressBar } from "@/components/ui";

export function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = "brand",
  progress,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "brand" | "accent" | "warn" | "danger";
  progress?: number;
}) {
  const toneClass =
    tone === "accent"
      ? "bg-accent-soft text-accent"
      : tone === "warn"
        ? "bg-warn-soft text-warn"
        : tone === "danger"
          ? "bg-danger-soft text-danger"
          : "bg-brand-soft text-brand";

  return (
    <div className="card card-hover p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</div>
          <div className="mt-1.5 text-2xl font-bold tracking-tight text-ink">{value}</div>
        </div>
        <div className={clsx("flex h-9 w-9 items-center justify-center rounded-xl", toneClass)}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {progress !== undefined ? (
        <ProgressBar
          value={progress}
          tone={tone === "danger" ? "danger" : tone === "warn" ? "warn" : tone === "accent" ? "accent" : "brand"}
          className="mt-3"
        />
      ) : null}
      {hint ? <div className="mt-2 text-[11px] leading-relaxed text-muted">{hint}</div> : null}
    </div>
  );
}

export function RingStat({
  value,
  label,
  sublabel,
}: {
  value: number;
  label: string;
  sublabel?: string;
}) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="flex items-center gap-4">
      <div
        className="relative flex h-20 w-20 items-center justify-center rounded-full"
        style={{
          background: `conic-gradient(var(--brand) ${pct * 3.6}deg, var(--surface-2) 0deg)`,
        }}
      >
        <div className="flex h-[62px] w-[62px] flex-col items-center justify-center rounded-full bg-surface">
          <span className="text-base font-bold text-ink">{Math.round(pct)}%</span>
        </div>
      </div>
      <div>
        <div className="text-sm font-semibold text-ink">{label}</div>
        {sublabel ? <div className="mt-0.5 text-[11px] text-muted">{sublabel}</div> : null}
      </div>
    </div>
  );
}

"use client";

import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Inbox, Loader2, X } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? (
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-brand">
            {eyebrow}
          </div>
        ) : null}
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-[28px]">{title}</h1>
        {description ? (
          <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wider text-ink">{title}</h2>
        {subtitle ? <p className="mt-0.5 text-xs text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function Card({
  children,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return <Tag className={clsx("card p-5", className)}>{children}</Tag>;
}

type Tone = "brand" | "accent" | "warn" | "danger" | "neutral";

const TONES: Record<Tone, string> = {
  brand: "border-brand/25 bg-brand-soft text-brand",
  accent: "border-accent/25 bg-accent-soft text-accent",
  warn: "border-warn/25 bg-warn-soft text-warn",
  danger: "border-danger/25 bg-danger-soft text-danger",
  neutral: "border-line bg-surface-2 text-muted",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return <span className={clsx("badge", TONES[tone], className)}>{children}</span>;
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const normalized = status.toUpperCase();
  const tone: Tone =
    normalized === "VERIFIED" || normalized === "APPROVED"
      ? "accent"
      : normalized === "PARTIALLY VERIFIED"
        ? "brand"
        : normalized === "DISPUTED" || normalized === "REJECTED"
          ? "danger"
          : normalized === "NEEDS REVIEW" || normalized === "STAGED"
            ? "warn"
            : "neutral";
  return (
    <Badge tone={tone} className={className}>
      {status.replaceAll("_", " ")}
    </Badge>
  );
}

export function ProgressBar({
  value,
  tone = "brand",
  className,
}: {
  value: number;
  tone?: "brand" | "accent" | "warn" | "danger";
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const bar =
    tone === "accent"
      ? "bg-accent"
      : tone === "warn"
        ? "bg-warn"
        : tone === "danger"
          ? "bg-danger"
          : "bg-gradient-to-r from-brand to-brand-2";
  return (
    <div className={clsx("h-1.5 w-full overflow-hidden rounded-full bg-surface-2", className)}>
      <div className={clsx("h-full rounded-full transition-all duration-500", bar)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "flex flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-surface/60 px-6 py-12 text-center",
        className,
      )}
    >
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-soft text-brand">
        {icon ?? <Inbox className="h-5 w-5" />}
      </div>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {description ? <p className="mt-1.5 max-w-md text-xs leading-relaxed text-muted">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function Loading({ label = "Loading…", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="space-y-3" aria-label={label}>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="card p-5">
          <div className="skeleton mb-3 h-4 w-1/3" />
          <div className="skeleton mb-2 h-3 w-full" />
          <div className="skeleton h-3 w-2/3" />
        </div>
      ))}
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("h-4 w-4 animate-spin", className)} />;
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        <p className="font-semibold">Something went wrong</p>
        <p className="mt-0.5 text-xs leading-relaxed opacity-90">{message}</p>
      </div>
      {onRetry ? (
        <button type="button" className="btn-sm btn-secondary shrink-0" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Notice({
  tone = "brand",
  title,
  children,
  className,
}: {
  tone?: "brand" | "accent" | "warn" | "danger" | "neutral";
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("rounded-xl border px-4 py-3 text-xs leading-relaxed", TONES[tone], className)}>
      {title ? <p className="mb-0.5 flex items-center gap-1.5 font-semibold">{title}</p> : null}
      <div className="opacity-90">{children}</div>
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm sm:p-8">
      <div
        className={clsx(
          "card animate-rise my-auto w-full p-0 shadow-2xl",
          wide ? "max-w-3xl" : "max-w-xl",
        )}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="text-sm font-bold text-ink">{title}</h2>
          <button type="button" className="btn-ghost h-8 w-8 p-0" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={clsx("block", className)}>
      <span className="label">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] leading-relaxed text-muted">{hint}</span> : null}
    </label>
  );
}

export function KeyValue({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-2 last:border-0">
      <span className="text-xs text-muted">{label}</span>
      <span className="text-right text-xs font-medium text-ink">{children}</span>
    </div>
  );
}

export function LinkButton({
  href,
  children,
  variant = "secondary",
  className,
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  className?: string;
}) {
  const style =
    variant === "primary" ? "btn-primary" : variant === "ghost" ? "btn-ghost" : "btn-secondary";
  return (
    <Link href={href} className={clsx(style, className)}>
      {children}
    </Link>
  );
}

export function SuccessTick({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 text-accent">
      <CheckCircle2 className="h-3.5 w-3.5" />
      {children}
    </span>
  );
}

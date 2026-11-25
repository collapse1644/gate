"use client";

import clsx from "clsx";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Badge, Card, EmptyState, ErrorNotice, Loading, PageHeader, ProgressBar } from "@/components/ui";
import { formatPercent, masteryLabel } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Subject } from "@/lib/types";

export default function SubjectsPage() {
  const { data, loading, error, refresh } = useApi<{ subjects: Subject[] }>("/subjects");
  const [query, setQuery] = useState("");

  const subjects = useMemo(() => {
    const rows = data?.subjects ?? [];
    const text = query.trim().toLowerCase();
    if (!text) return rows;
    return rows.filter(
      (subject) =>
        subject.name.toLowerCase().includes(text) ||
        subject.code.toLowerCase().includes(text) ||
        subject.description.toLowerCase().includes(text),
    );
  }, [data, query]);

  if (loading) return <Loading rows={3} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;

  const total = data?.subjects.reduce((sum, subject) => sum + subject.questions_available, 0) ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Official taxonomy"
        title="Subjects"
        description={`Eleven subjects from the official GATE 2027 CS syllabus. ${total} approved PYQs are distributed across them.`}
        actions={
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search subjects…"
              className="input w-64 pl-8"
            />
          </div>
        }
      />

      {subjects.length === 0 ? (
        <EmptyState
          icon={<BookOpen className="h-5 w-5" />}
          title="No subject matches that search"
          description="Try the subject code (ALGO, OS, DB) or a topic such as 'deadlock'."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {subjects.map((subject) => {
            const available = subject.questions_available;
            const attempted = subject.progress?.distinct_questions ?? 0;
            const accuracy = subject.progress?.accuracy ?? null;
            const completion = available > 0 ? attempted / available : 0;
            const isGA = subject.code === "GA";
            return (
              <Link key={subject.id} href={`/subjects/${subject.id}`} className="card card-hover group flex flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={clsx(
                        "flex h-11 w-11 items-center justify-center rounded-2xl text-xs font-black",
                        isGA ? "bg-accent-soft text-accent" : "bg-brand-soft text-brand",
                      )}
                    >
                      {subject.code}
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-ink group-hover:text-brand">{subject.name}</h2>
                      <div className="mt-0.5 text-[10px] uppercase tracking-wider text-muted">
                        Section {subject.section_code}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
                </div>

                <p className="mt-3 line-clamp-3 flex-1 text-[11px] leading-relaxed text-muted">
                  {subject.description || "Official syllabus area."}
                </p>

                <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-surface-2/60 px-1 py-2">
                    <div className="text-sm font-bold text-ink">{available}</div>
                    <div className="text-[9px] uppercase tracking-wider text-muted">PYQs</div>
                  </div>
                  <div className="rounded-lg bg-surface-2/60 px-1 py-2">
                    <div className="text-sm font-bold text-ink">{formatPercent(accuracy)}</div>
                    <div className="text-[9px] uppercase tracking-wider text-muted">Accuracy</div>
                  </div>
                  <div className="rounded-lg bg-surface-2/60 px-1 py-2">
                    <div className="text-sm font-bold text-ink">{attempted}</div>
                    <div className="text-[9px] uppercase tracking-wider text-muted">Attempted</div>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="mb-1 flex items-center justify-between text-[10px] text-muted">
                    <span>{masteryLabel(subject.progress?.mastery)}</span>
                    <span>{Math.round(completion * 100)}% covered</span>
                  </div>
                  <ProgressBar
                    value={completion * 100}
                    tone={completion >= 0.7 ? "accent" : completion > 0 ? "brand" : "warn"}
                  />
                </div>

                {available === 0 ? (
                  <div className="mt-3">
                    <Badge tone="warn">No approved PYQs yet</Badge>
                  </div>
                ) : null}
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}

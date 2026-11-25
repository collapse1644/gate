"use client";

import clsx from "clsx";
import { ArrowLeft, ArrowRight, BookOpen, ExternalLink, Target } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { MathText } from "@/components/math-text";
import {
  Badge,
  Card,
  EmptyState,
  ErrorNotice,
  LinkButton,
  Loading,
  PageHeader,
  ProgressBar,
  SectionTitle,
} from "@/components/ui";
import { formatPercent, masteryLabel } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SubjectDetail, SyllabusResponse } from "@/lib/types";

export default function SubjectDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data, loading, error, refresh } = useApi<SubjectDetail>(id ? `/subjects/${id}` : null);
  const { data: syllabus } = useApi<SyllabusResponse>("/syllabus");

  if (loading) return <Loading rows={3} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;
  if (!data) return null;

  const { subject, topics } = data;
  const available = topics.reduce((sum, topic) => sum + topic.questions_available, 0);
  const attempted = topics.reduce((sum, topic) => sum + (topic.progress?.distinct_questions ?? 0), 0);
  const completion = available > 0 ? attempted / available : 0;
  const codes = subject.code === "GA" ? ["GA"] : [];
  const sections = syllabus?.sections.filter((section) => codes.includes(section.code)) ?? [];

  return (
    <>
      <Link href="/subjects" className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink">
        <ArrowLeft className="h-3.5 w-3.5" /> All subjects
      </Link>

      <PageHeader
        eyebrow={`Subject · ${subject.code}`}
        title={subject.name}
        description={subject.description}
        actions={
          <>
            <LinkButton href={`/library?subject_id=${subject.id}`} variant="secondary">
              <BookOpen className="h-4 w-4" /> PYQ library
            </LinkButton>
            <LinkButton href={`/practice?subject_id=${subject.id}`} variant="primary">
              <Target className="h-4 w-4" /> Practise subject
            </LinkButton>
          </>
        }
      />

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Approved PYQs</div>
          <div className="mt-1 text-2xl font-bold text-ink">{available}</div>
        </div>
        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Coverage</div>
          <div className="mt-1 text-2xl font-bold text-ink">{Math.round(completion * 100)}%</div>
          <ProgressBar value={completion * 100} className="mt-2" />
        </div>
        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wider text-muted">Topics</div>
          <div className="mt-1 text-2xl font-bold text-ink">{topics.length}</div>
        </div>
      </div>

      {sections.length ? (
        <Card className="mb-5">
          <SectionTitle title="Official syllabus wording" subtitle="Preserved verbatim from the GATE 2027 PDF." />
          <div className="space-y-3">
            {sections.map((section) => (
              <details key={section.id} className="group rounded-xl border border-line bg-surface-2/40 p-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                  <span className="text-xs font-semibold text-ink">
                    {section.code} · {section.title}
                  </span>
                  <span className="text-[10px] text-muted group-open:hidden">Expand</span>
                </summary>
                <p className="mt-2 whitespace-pre-wrap text-[11px] leading-relaxed text-muted">
                  {section.official_text}
                </p>
              </details>
            ))}
          </div>
        </Card>
      ) : null}

      <Card>
        <SectionTitle
          title="Topics and progress"
          subtitle="Topic completion uses distinct approved questions you have attempted."
        />
        {topics.length ? (
          <div className="space-y-2">
            {topics.map((topic) => {
              const topicAvailable = topic.questions_available;
              const topicAttempted = topic.progress?.distinct_questions ?? 0;
              const topicCompletion = topicAvailable > 0 ? topicAttempted / topicAvailable : 0;
              const accuracy = topic.progress?.accuracy ?? null;
              return (
                <div key={topic.id} className="rounded-xl border border-line bg-surface-2/30 p-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="text-xs font-semibold text-ink">{topic.name}</span>
                      <Badge tone="neutral">{topicAvailable} PYQs</Badge>
                      {accuracy !== null ? (
                        <Badge tone={accuracy >= 0.7 ? "accent" : accuracy >= 0.45 ? "warn" : "danger"}>
                          {formatPercent(accuracy)} accuracy
                        </Badge>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted">{masteryLabel(topic.progress?.mastery)}</span>
                      <Link
                        href={`/library?topic_id=${topic.id}`}
                        className="btn-secondary btn-sm"
                        aria-label={`Open ${topic.name} questions`}
                      >
                        Questions <ArrowRight className="h-3 w-3" />
                      </Link>
                    </div>
                  </div>
                  {topic.description ? (
                    <div className="mt-1.5 text-[11px] leading-relaxed text-muted">
                      <MathText text={topic.description} inline />
                    </div>
                  ) : null}
                  <div className="mt-2 flex items-center gap-2">
                    <ProgressBar
                      value={topicCompletion * 100}
                      tone={topicCompletion >= 0.7 ? "accent" : topicCompletion > 0 ? "brand" : "warn"}
                      className="flex-1"
                    />
                    <span className="w-10 text-right text-[10px] text-muted">
                      {Math.round(topicCompletion * 100)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState title="No topics found" description="The syllabus taxonomy may not have been seeded." />
        )}
      </Card>

      <div className="mt-5 flex items-center gap-2 text-[10px] text-muted">
        <ExternalLink className="h-3 w-3" />
        Official source:{" "}
        <a
          href={syllabus?.version.source_url ?? "https://gate2027.iitm.ac.in"}
          target="_blank"
          rel="noreferrer"
          className="link"
        >
          gate2027.iitm.ac.in
        </a>
        {syllabus?.version.source_sha256 ? (
          <span className={clsx("mono truncate", "max-w-[280px]")}>sha256 {syllabus.version.source_sha256.slice(0, 16)}…</span>
        ) : null}
      </div>
    </>
  );
}

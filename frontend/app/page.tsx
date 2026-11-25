"use client";

import clsx from "clsx";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  Flame,
  Sparkles,
  Target,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";

import { MathText } from "@/components/math-text";
import { RingStat, StatCard } from "@/components/stat-card";
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
  StatusBadge,
} from "@/components/ui";
import { useApi } from "@/lib/hooks";
import {
  formatDuration,
  formatPercent,
  masteryLabel,
  relativeTime,
  truncate,
} from "@/lib/format";
import type { DashboardResponse } from "@/lib/types";

export default function DashboardPage() {
  const { data, loading, error, refresh } = useApi<DashboardResponse>("/dashboard");

  if (loading) return <Loading rows={4} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;
  if (!data) return null;

  const { stats } = data;
  const hasQuestions = stats.questions_available > 0;

  return (
    <>
      <PageHeader
        eyebrow={`Official syllabus · ${new Date().getFullYear()}`}
        title="Your GATE CS 2027 command centre"
        description="Everything here is computed from the papers you upload. No synthetic questions, no invented statistics."
        actions={
          <>
            <LinkButton href="/data" variant="secondary">
              <UploadCloud className="h-4 w-4" /> Upload PYQs
            </LinkButton>
            <LinkButton href="/practice" variant="primary">
              <Target className="h-4 w-4" /> Start practice
            </LinkButton>
          </>
        }
      />

      {!hasQuestions ? (
        <Card className="mb-6 overflow-hidden border-brand/20 bg-gradient-to-br from-brand-soft via-surface to-surface p-0">
          <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-[1.35fr_0.65fr]">
            <div>
              <Badge tone="brand">Local-first workspace</Badge>
              <h2 className="mt-3 text-2xl font-bold tracking-tight text-ink sm:text-3xl">
                Start with a real GATE paper.
              </h2>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
                Upload a ZIP containing official question papers and answer keys. The app extracts the text
                layer (never OCR), preserves figures, pairs official answers, and asks you to review every
                uncertain classification before anything enters practice.
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <LinkButton href="/data" variant="primary">
                  <UploadCloud className="h-4 w-4" /> Import a ZIP
                </LinkButton>
                <LinkButton href="/subjects" variant="secondary">
                  Browse syllabus <ArrowRight className="h-3.5 w-3.5" />
                </LinkButton>
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                {[
                  ["1", "Upload", "Question paper + answer key PDFs in one ZIP."],
                  ["2", "Review", "Approve staged questions and fix classifications."],
                  ["3", "Practise", "Only approved PYQs appear in practice modes."],
                ].map(([step, title, body]) => (
                  <div key={step} className="rounded-xl border border-line bg-surface/80 p-3">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-brand">Step {step}</div>
                    <div className="mt-1 text-xs font-semibold text-ink">{title}</div>
                    <div className="mt-0.5 text-[10px] leading-relaxed text-muted">{body}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-col justify-center rounded-2xl border border-line bg-surface/80 p-5">
              <RingStat value={0} label="Syllabus coverage" sublabel="No approved PYQs yet" />
              <div className="mt-5 space-y-3">
                <div>
                  <div className="mb-1 flex justify-between text-[10px] text-muted">
                    <span>Official taxonomy</span>
                    <span>11 subjects</span>
                  </div>
                  <ProgressBar value={100} tone="accent" />
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-[10px] text-muted">
                    <span>PYQ library</span>
                    <span>0 questions</span>
                  </div>
                  <ProgressBar value={0} />
                </div>
              </div>
              <p className="mt-4 text-[10px] leading-relaxed text-muted">
                The syllabus tree is pre-loaded from the official IIT Madras GATE 2027 PDFs. Question
                content is never generated.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={BookOpen}
          label="Approved PYQs"
          value={stats.questions_available}
          hint={`${stats.questions_remaining} not attempted yet`}
        />
        <StatCard
          icon={Target}
          label="Questions attempted"
          value={stats.questions_attempted}
          hint={`${formatPercent(stats.completion)} of the approved library`}
          progress={stats.completion * 100}
          tone="brand"
        />
        <StatCard
          icon={CheckCircle2}
          label="Accuracy"
          value={formatPercent(stats.accuracy)}
          hint={`${stats.correct_attempts} correct of ${stats.graded_attempts} graded attempts`}
          tone="accent"
        />
        <StatCard
          icon={CalendarClock}
          label="Due revisions"
          value={stats.due_revisions}
          hint={`${formatDuration(stats.time_spent_seconds)} total practice time`}
          tone={stats.due_revisions > 0 ? "warn" : "accent"}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card>
            <SectionTitle
              title="Subject coverage"
              subtitle="Completion is based on distinct approved questions attempted."
              action={
                <Link href="/subjects" className="text-xs font-semibold text-brand hover:underline">
                  All subjects
                </Link>
              }
            />
            <div className="space-y-3">
              {data.subjects.slice(0, 7).map((subject) => {
                const completion =
                  subject.questions_available > 0
                    ? subject.distinct_questions / subject.questions_available
                    : 0;
                return (
                  <Link
                    key={subject.id}
                    href={`/subjects/${subject.id}`}
                    className="group block rounded-xl border border-transparent px-1 py-1.5 transition hover:border-line hover:bg-surface-2/50"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ backgroundColor: subject.code === "GA" ? "var(--accent)" : "var(--brand)" }}
                        />
                        <span className="truncate text-xs font-semibold text-ink group-hover:text-brand">
                          {subject.name}
                        </span>
                        <Badge tone="neutral">{subject.questions_available} PYQs</Badge>
                      </div>
                      <div className="flex shrink-0 items-center gap-2 text-[10px] text-muted">
                        <span>{masteryLabel(subject.mastery)}</span>
                        <span className="font-semibold text-ink">{Math.round(completion * 100)}%</span>
                      </div>
                    </div>
                    <ProgressBar
                      value={completion * 100}
                      tone={completion >= 0.7 ? "accent" : completion > 0 ? "brand" : "warn"}
                      className="mt-1.5"
                    />
                  </Link>
                );
              })}
            </div>
          </Card>

          <Card>
            <SectionTitle
              title="Recommended next"
              subtitle="Ordered by weakest accuracy and question availability — not a prediction."
            />
            {data.recommended_topics.length ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {data.recommended_topics.map((topic) => (
                  <Link
                    key={topic.topic_id}
                    href={`/library?topic_id=${topic.topic_id}`}
                    className="rounded-xl border border-line bg-surface-2/40 p-3 transition hover:border-brand/40 hover:bg-surface-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold text-ink">{topic.topic}</span>
                      <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted" />
                    </div>
                    <p className="mt-1 text-[10px] leading-relaxed text-muted">{topic.reason}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge tone="neutral">{topic.questions_available} available</Badge>
                      {topic.accuracy !== null ? (
                        <Badge tone={topic.accuracy >= 0.7 ? "accent" : topic.accuracy >= 0.45 ? "warn" : "danger"}>
                          {formatPercent(topic.accuracy)} accuracy
                        </Badge>
                      ) : null}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No topic-level evidence yet"
                description="Attempt a few approved PYQs and topic recommendations will appear here."
                action={<LinkButton href="/practice">Start practice</LinkButton>}
              />
            )}
          </Card>

          <Card>
            <SectionTitle title="Recent activity" subtitle="Your last graded attempts." />
            {data.recent_activity.length ? (
              <div className="divide-y divide-line">
                {data.recent_activity.map((item) => (
                  <Link
                    key={item.attempt_id}
                    href={`/library/${item.question_id}`}
                    className="flex items-center gap-3 py-2.5 transition hover:opacity-80"
                  >
                    <span
                      className={clsx(
                        "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                        item.is_correct ? "bg-accent-soft text-accent" : "bg-danger-soft text-danger",
                      )}
                    >
                      {item.is_correct ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                    </span>
                    <span className="min-w-0 flex-1 text-xs text-ink">
                      {item.year} · Q{item.question_no}
                      <span className="ml-2 text-[10px] text-muted">{item.mode}</span>
                    </span>
                    <span className="text-[10px] text-muted">{relativeTime(item.completed_at)}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="py-4 text-xs text-muted">No attempts recorded yet.</p>
            )}
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <SectionTitle title="Overall completion" />
            <RingStat
              value={stats.completion}
              label={`${stats.questions_attempted} of ${stats.questions_available} PYQs`}
              sublabel={`${formatDuration(stats.time_spent_seconds)} of practice recorded`}
            />
            <div className="mt-5 grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-line bg-surface-2/50 p-3">
                <div className="text-lg font-bold text-ink">{stats.due_revisions}</div>
                <div className="text-[10px] text-muted">revisions due</div>
              </div>
              <div className="rounded-xl border border-line bg-surface-2/50 p-3">
                <div className="text-lg font-bold text-ink">{data.weak_topics.length}</div>
                <div className="text-[10px] text-muted">weak topics tracked</div>
              </div>
            </div>
          </Card>

          <Card>
            <SectionTitle
              title="Exam priority"
              subtitle="A study-ordering heuristic, not a forecast."
              action={
                <Link href="/analytics" className="text-xs font-semibold text-brand hover:underline">
                  Detail
                </Link>
              }
            />
            {data.priority_subjects.length ? (
              <div className="space-y-2.5">
                {data.priority_subjects.map((item) => (
                  <div key={item.subject_id}>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-medium text-ink">{item.subject}</span>
                      <Badge tone={item.priority_band === "High" ? "brand" : item.priority_band === "Medium" ? "warn" : "accent"}>
                        {item.priority_band}
                      </Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <ProgressBar value={item.priority_score} />
                      <span className="w-10 text-right text-[10px] text-muted">{item.priority_score}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-3 text-xs text-muted">Upload papers to compute weightage.</p>
            )}
          </Card>

          <Card>
            <SectionTitle
              title="Revision queue"
              action={
                <Link href="/revision" className="text-xs font-semibold text-brand hover:underline">
                  Open
                </Link>
              }
            />
            {data.revision_due.length ? (
              <div className="space-y-2">
                {data.revision_due.slice(0, 4).map((item) => (
                  <Link
                    key={item.question_id}
                    href={`/library/${item.question_id}`}
                    className="block rounded-lg border border-line bg-surface-2/40 p-2.5 transition hover:border-brand/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <Badge tone="warn">
                        {item.year} · Q{item.question_no}
                      </Badge>
                      <span className="text-[10px] text-muted">{relativeTime(item.due_at)}</span>
                    </div>
                    <div className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-muted">
                      <MathText text={truncate(item.question_text, 130)} inline />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="py-3 text-xs text-muted">Nothing due. Attempt questions to build the schedule.</p>
            )}
          </Card>

          <Card className="border-brand/20 bg-brand-soft/40">
            <div className="flex items-start gap-2.5">
              <Flame className="mt-0.5 h-4 w-4 text-brand" />
              <div>
                <div className="text-xs font-semibold text-ink">Study rule</div>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  Only verified or clearly-labelled unverified material is shown. Never treat an AI
                  explanation as an official answer key.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

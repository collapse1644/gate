"use client";

import { ArrowLeft, CheckCircle2, Clock3, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { MathText } from "@/components/math-text";
import { Badge, Card, EmptyState, ErrorNotice, Loading, PageHeader, SectionTitle, StatusBadge } from "@/components/ui";
import { api, assetUrl, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { PracticeAnswerResult, PracticeSession, QuestionSummary } from "@/lib/types";

export default function PracticeRunnerPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <PracticeRunner />
    </Suspense>
  );
}

function PracticeRunner() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data: session, loading, error, refresh, setData } = useApi<PracticeSession>(id ? `/practice/sessions/${id}` : null);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [msqSelected, setMsqSelected] = useState<string[]>([]);
  const [natValue, setNatValue] = useState("");
  const [feedback, setFeedback] = useState<PracticeAnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [questionStart, setQuestionStart] = useState(Date.now());
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    if (session) {
      setIndex(Math.min(session.current_index, Math.max(0, session.total_questions - 1)));
      setFinished(Boolean(session.completed_at) && session.answered_count >= session.total_questions);
    }
  }, [session]);

  useEffect(() => {
    setSelected(null);
    setMsqSelected([]);
    setNatValue("");
    setFeedback(null);
    setQuestionStart(Date.now());
  }, [index]);

  if (loading) return <Loading rows={3} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;
  if (!session) return null;

  const questions = session.questions ?? [];
  const q = questions[index];
  if (!q) return <EmptyState title="No questions in this session" />;

  const isMsq = q.question_type === "MSQ";
  const isNat = q.question_type === "NAT";

  function selectedAnswer(): string | null {
    if (isMsq) return msqSelected.length ? msqSelected.sort().join(",") : null;
    if (isNat) return natValue.trim() || null;
    return selected;
  }

  async function submit() {
    const answer = selectedAnswer();
    if (answer === null && !window.confirm("Submit without an answer?")) return;
    setSubmitting(true);
    try {
      const result = await api.post<PracticeAnswerResult>(`/practice/sessions/${session!.id}/answer`, {
        question_id: q.id,
        selected_answer: answer,
        time_spent_seconds: Math.max(0, Math.round((Date.now() - questionStart) / 1000)),
      });
      setFeedback(result);
      refresh();
    } catch (err) {
      alert(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    if (index + 1 >= questions.length) {
      setFinished(true);
    } else {
      setIndex(index + 1);
    }
  }

  if (finished) {
    const correct = session.correct_count;
    const total = session.total_questions;
    const pct = total ? Math.round((correct / total) * 100) : 0;
    return (
      <>
        <PageHeader eyebrow="Practice complete" title={`Session #${session.id}`} description={session.paper ? `${session.paper.year} · ${session.paper.label}` : session.mode} />
        <Card className="max-w-xl">
          <div className="text-center">
            <div className="text-5xl font-black text-brand">{pct}%</div>
            <p className="mt-2 text-sm text-muted">{correct} correct out of {total}</p>
            <p className="mt-1 text-xs text-muted">Mode: {session.mode}</p>
          </div>
          <div className="mt-6 flex justify-center gap-2">
            <Link href="/practice" className="btn-primary">New session</Link>
            <Link href="/library" className="btn-secondary">Review mistakes</Link>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <Link href="/practice" className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" /> Practice
        </Link>
        <div className="flex items-center gap-2 text-xs text-muted">
          <Clock3 className="h-3.5 w-3.5" />
          {session.mode}
          <Badge tone="neutral">{index + 1} / {questions.length}</Badge>
        </div>
      </div>

      <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div className="h-full bg-gradient-to-r from-brand to-brand-2 transition-all" style={{ width: `${((index + (feedback ? 1 : 0)) / questions.length) * 100}%` }} />
      </div>

      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] text-muted">
          <Badge tone="brand">{q.year} · Q{q.question_no}</Badge>
          <Badge tone="neutral">{q.question_type}</Badge>
          {q.marks ? <Badge tone="neutral">{q.marks} marks</Badge> : null}
          {q.subject ? <span>{q.subject}{q.topic ? ` / ${q.topic}` : ""}</span> : null}
        </div>
        <MathText text={q.question_text} className="text-[15px] leading-8 text-ink" />

        {q.assets?.length ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {q.assets.map((a) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={a.id} src={assetUrl(a.id)} alt="figure" className="max-h-56 w-full rounded-xl border border-line object-contain bg-surface-2/40 p-2" />
            ))}
          </div>
        ) : null}

        <div className="mt-5 space-y-2">
          {isNat ? (
            <input className="input max-w-xs" type="text" inputMode="decimal" value={natValue} onChange={(e) => setNatValue(e.target.value)} placeholder="Enter numeric answer" disabled={!!feedback} />
          ) : isMsq ? (
            q.options.map((opt) => (
              <label key={opt.key} className={`flex items-start gap-3 rounded-xl border px-3.5 py-2.5 cursor-pointer ${msqSelected.includes(opt.key) ? "border-brand bg-brand-soft/60" : "border-line bg-surface-2/40"}`}>
                <input type="checkbox" checked={msqSelected.includes(opt.key)} disabled={!!feedback} onChange={(e) => {
                  setMsqSelected((prev) => e.target.checked ? [...prev, opt.key] : prev.filter((k) => k !== opt.key));
                }} className="mt-1" />
                <span className="font-bold text-brand">{opt.key}</span>
                <MathText text={opt.text} className="text-[13px] text-ink" inline />
              </label>
            ))
          ) : (
            q.options.map((opt) => (
              <button
                key={opt.key}
                type="button"
                disabled={!!feedback}
                onClick={() => setSelected(opt.key)}
                className={`flex w-full items-start gap-3 rounded-xl border px-3.5 py-2.5 text-left transition ${selected === opt.key ? "border-brand bg-brand-soft/60" : "border-line bg-surface-2/40 hover:bg-surface-2"}`}
              >
                <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold ${selected === opt.key ? "bg-brand text-white" : "bg-surface text-muted"}`}>{opt.key}</span>
                <MathText text={opt.text} className="pt-0.5 text-[13px] text-ink" inline />
              </button>
            ))
          )}
        </div>

        {!feedback ? (
          <div className="mt-5 flex justify-end">
            <button className="btn-primary" onClick={submit} disabled={submitting}>
              {submitting ? "Submitting…" : "Submit answer"}
            </button>
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold ${feedback.is_correct ? "border-accent/40 bg-accent-soft text-accent" : "border-danger/40 bg-danger-soft text-danger"}`}>
              {feedback.is_correct ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
              {feedback.is_correct ? "Correct" : "Incorrect"}
              {feedback.official_answer ? <span className="ml-2 font-normal text-ink">Official answer: {feedback.official_answer}</span> : null}
            </div>
            {feedback.explanation ? (
              <Card className="bg-surface-2/40">
                <SectionTitle title="Explanation (unverified unless marked)" />
                <MathText text={feedback.explanation} className="text-[13px] text-ink" />
              </Card>
            ) : null}
            <div className="flex justify-end">
              <button className="btn-primary" onClick={next}>
                {index + 1 >= questions.length ? "Finish" : "Next question"}
              </button>
            </div>
          </div>
        )}
      </Card>
    </>
  );
}
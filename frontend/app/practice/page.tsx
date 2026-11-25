"use client";

import { Play, Settings2, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Card, EmptyState, ErrorNotice, Loading, PageHeader, SectionTitle } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Subject, TaxonomySubject } from "@/lib/types";

const MODES: Array<{ value: string; label: string; description: string }> = [
  { value: "random", label: "Random practice", description: "Shuffle approved PYQs with optional filters." },
  { value: "subtopic", label: "By subtopic", description: "Focus on a single subtopic." },
  { value: "topic", label: "By topic", description: "All questions under a topic." },
  { value: "subject", label: "By subject", description: "Whole subject revision." },
  { value: "year", label: "By year", description: "A specific GATE year." },
  { value: "incorrect", label: "Incorrect only", description: "Questions you last got wrong." },
  { value: "unattempted", label: "Unattempted", description: "Questions you have never tried." },
  { value: "revision", label: "Due revisions", description: "Spaced-repetition due items." },
  { value: "full_paper", label: "Full paper", description: "Simulate an original paper in original order." },
];

export default function PracticePage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <PracticeIndex />
    </Suspense>
  );
}

function PracticeIndex() {
  const router = useRouter();
  const params = useSearchParams();
  const [mode, setMode] = useState(params.get("mode") ?? "random");
  const [subjectId, setSubjectId] = useState(params.get("subject_id") ?? "");
  const [topicId, setTopicId] = useState(params.get("topic_id") ?? "");
  const [subtopicId, setSubtopicId] = useState(params.get("subtopic_id") ?? "");
  const [year, setYear] = useState(params.get("year") ?? "");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [paperId, setPaperId] = useState(params.get("paper_id") ?? "");
  const [limit, setLimit] = useState(20);
  const [shuffle, setShuffle] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: taxonomy } = useApi<{ subjects: TaxonomySubject[] }>("/taxonomy");
  const { data: papersData } = useApi<{ items: any[] }>("/papers");
  const { data: subjectsData } = useApi<{ subjects: Subject[] }>("/subjects");

  const subjects = taxonomy?.subjects ?? [];
  const selectedSubject = subjects.find((s) => s.id === Number(subjectId));
  const topics = selectedSubject?.topics ?? [];
  const selectedTopic = topics.find((t) => t.id === Number(topicId));
  const subtopics = selectedTopic?.subtopics ?? [];

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = { mode, limit, shuffle };
      if (subjectId) payload.subject_id = Number(subjectId);
      if (topicId) payload.topic_id = Number(topicId);
      if (subtopicId) payload.subtopic_id = Number(subtopicId);
      if (year) payload.year = Number(year);
      if (yearFrom) payload.year_from = Number(yearFrom);
      if (yearTo) payload.year_to = Number(yearTo);
      if (questionType) payload.question_type = questionType;
      if (mode === "full_paper" && paperId) payload.paper_id = Number(paperId);
      const session = await api.post<{ id: number }>("/practice/sessions", payload);
      router.push(`/practice/${session.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Practice engine"
        title="Practice"
        description="Only approved PYQs from your uploaded papers. Answers stay hidden until you submit."
        actions={
          <Link href="/library" className="btn-secondary btn-sm">
            Browse library
          </Link>
        }
      />

      {error ? <div className="mb-4"><ErrorNotice message={error} /></div> : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.9fr)]">
        <Card>
          <SectionTitle title="Configure a session" />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="label">Mode</span>
              <select className="input" value={mode} onChange={(e) => setMode(e.target.value)}>
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
              <span className="mt-1 block text-[11px] text-muted">{MODES.find((m) => m.value === mode)?.description}</span>
            </label>

            {mode === "full_paper" ? (
              <label className="block sm:col-span-2">
                <span className="label">Paper</span>
                <select className="input" value={paperId} onChange={(e) => setPaperId(e.target.value)}>
                  <option value="">Choose a paper</option>
                  {papersData?.items?.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.year} {p.session ?? ""} · {p.label} ({p.question_count} Q)</option>
                  ))}
                </select>
              </label>
            ) : null}

            <label className="block">
              <span className="label">Subject</span>
              <select className="input" value={subjectId} onChange={(e) => { setSubjectId(e.target.value); setTopicId(""); setSubtopicId(""); }}>
                <option value="">All subjects</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Topic</span>
              <select className="input" value={topicId} onChange={(e) => { setTopicId(e.target.value); setSubtopicId(""); }} disabled={!subjectId}>
                <option value="">All topics</option>
                {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Subtopic</span>
              <select className="input" value={subtopicId} onChange={(e) => setSubtopicId(e.target.value)} disabled={!topicId}>
                <option value="">All subtopics</option>
                {subtopics.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Question type</span>
              <select className="input" value={questionType} onChange={(e) => setQuestionType(e.target.value)}>
                <option value="">Any</option>
                <option value="MCQ">MCQ</option>
                <option value="MSQ">MSQ</option>
                <option value="NAT">NAT</option>
              </select>
            </label>
            <label className="block">
              <span className="label">Year</span>
              <input className="input" type="number" value={year} onChange={(e) => setYear(e.target.value)} placeholder="Any" />
            </label>
            <label className="block">
              <span className="label">Year from</span>
              <input className="input" type="number" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} placeholder="Any" />
            </label>
            <label className="block">
              <span className="label">Year to</span>
              <input className="input" type="number" value={yearTo} onChange={(e) => setYearTo(e.target.value)} placeholder="Any" />
            </label>
            <label className="block">
              <span className="label">Limit</span>
              <input className="input" type="number" min={1} max={65} value={limit} onChange={(e) => setLimit(Number(e.target.value) || 20)} />
            </label>
            <label className="inline-flex items-center gap-2 text-xs">
              <input type="checkbox" checked={shuffle} onChange={(e) => setShuffle(e.target.checked)} className="h-3.5 w-3.5 accent-[var(--brand)]" />
              Shuffle order (off by default; full paper preserves original order)
            </label>
          </div>
          <div className="mt-4 flex justify-end">
            <button className="btn-primary" onClick={start} disabled={busy}>
              <Play className="h-4 w-4" /> {busy ? "Starting…" : "Start session"}
            </button>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <SectionTitle title="Recent sessions" />
            <RecentSessions />
          </Card>
          <Card>
            <SectionTitle title="Tips" />
            <p className="text-xs leading-relaxed text-muted">
              Full-paper simulation preserves the original question order and shows a timer. Answers are revealed only
              after submission. Use “Incorrect only” to drill weak areas.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}

function RecentSessions() {
  const { data, loading, error } = useApi<{ items: any[] }>("/practice/sessions");
  if (loading) return <p className="text-xs text-muted">Loading…</p>;
  if (error) return <p className="text-xs text-danger">{error}</p>;
  if (!data?.items?.length) return <p className="text-xs text-muted">No sessions yet.</p>;
  return (
    <div className="space-y-2">
      {data.items.slice(0, 8).map((s) => (
        <Link key={s.id} href={`/practice/${s.id}`} className="flex items-center justify-between rounded-xl border border-line bg-surface-2/40 px-3 py-2 text-xs hover:bg-surface-2">
          <span className="font-semibold text-ink">#{s.id} · {s.mode}</span>
          <span className="text-muted">{s.answered_count}/{s.total_questions} · {s.correct_count} correct</span>
        </Link>
      ))}
    </div>
  );
}
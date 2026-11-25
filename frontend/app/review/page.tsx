"use client";

import { Filter, RotateCcw, Search, ShieldCheck, SlidersHorizontal, Wand2 } from "lucide-react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { QuestionCard } from "@/components/question-card";
import {
  Badge,
  Card,
  EmptyState,
  ErrorNotice,
  Loading,
  Modal,
  Notice,
  PageHeader,
  SectionTitle,
  StatusBadge,
} from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi, useDebounced } from "@/lib/hooks";
import type { QuestionSummary, ReviewQueue, TaxonomySubject } from "@/lib/types";

const VIEWS = [
  { value: "all", label: "All flagged" },
  { value: "classification", label: "Classification" },
  { value: "extraction", label: "Extraction" },
  { value: "answers", label: "Missing answers" },
  { value: "staged", label: "Staged" },
];

export default function ReviewPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <ReviewInner />
    </Suspense>
  );
}

function ReviewInner() {
  const searchParams = useSearchParams();
  const initialView = searchParams.get("view") ?? "all";
  const initialQuestion = searchParams.get("question");

  const [view, setView] = useState(initialView);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(initialQuestion ? Number(initialQuestion) : null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const [subjectId, setSubjectId] = useState("");
  const [topicId, setTopicId] = useState("");
  const [subtopicId, setSubtopicId] = useState("");
  const [conceptIds, setConceptIds] = useState<number[]>([]);
  const [reviewer, setReviewer] = useState("local-user");
  const [reviewNotes, setReviewNotes] = useState("");
  const [useLlm, setUseLlm] = useState(false);

  const { data: taxonomy } = useApi<{ subjects: TaxonomySubject[] }>("/taxonomy");
  const path = useMemo(() => `/review/queue${api.query({ view, page, page_size: 25 })}`, [view, page]);
  const { data, loading, error, refresh } = useApi<ReviewQueue>(path);
  const { data: benchmarkData, refresh: refreshBenchmark } = useApi<{ items: any[]; report: any }>("/review/benchmark");

  const subjects = taxonomy?.subjects ?? [];
  const selectedSubject = subjects.find((s) => s.id === Number(subjectId));
  const topics = selectedSubject?.topics ?? [];
  const selectedTopic = topics.find((t) => t.id === Number(topicId));
  const subtopics = selectedTopic?.subtopics ?? [];
  const concepts = subtopics.find((s) => s.id === Number(subtopicId))?.concepts ?? [];

  useEffect(() => {
    setPage(1);
  }, [view]);

  async function run(label: string, action: () => Promise<void>, notice?: string) {
    setBusy(label);
    setActionError(null);
    setActionNotice(null);
    try {
      await action();
      refresh();
      refreshBenchmark();
      if (notice) setActionNotice(notice);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  function openClassify(questionId: number) {
    setSelectedId(questionId);
    setSubjectId("");
    setTopicId("");
    setSubtopicId("");
    setConceptIds([]);
    setReviewNotes("");
  }

  async function applyClassification(accept: boolean) {
    if (!selectedId) return;
    await run("classify", async () => {
      if (useLlm) {
        await api.post(`/questions/${selectedId}/classify`, { use_llm: true });
      }
      await api.post(`/questions/${selectedId}/classification`, {
        subject_id: subjectId ? Number(subjectId) : null,
        topic_id: topicId ? Number(topicId) : null,
        subtopic_id: subtopicId ? Number(subtopicId) : null,
        concept_ids: conceptIds,
        reason: reviewNotes || (useLlm ? "LLM-assisted reclassification reviewed by user." : "Manual classification."),
        accept,
      });
      setSelectedId(null);
    }, accept ? "Classification accepted." : "Classification saved as pending.");
  }

  async function reclassifyDeterministic(questionId: number) {
    await run("reclassify", async () => {
      await api.post(`/questions/${questionId}/classify`, { use_llm: false });
    }, "Deterministic classifier re-run. AI suggestions are never auto-accepted.");
  }

  async function reclassifyLlm(questionId: number) {
    await run("reclassify-llm", async () => {
      await api.post(`/questions/${questionId}/classify`, { use_llm: true });
    }, "LLM recommendation applied as a suggestion; review before approving.");
  }

  async function approve(questionId: number) {
    await run("approve", async () => {
      await api.post(`/questions/${questionId}/approve`, { reviewer });
    }, "Question approved for practice.");
  }

  async function reject(questionId: number) {
    if (!window.confirm("Reject this question? It leaves the practice pool.")) return;
    await run("reject", async () => {
      await api.post(`/questions/${questionId}/reject`, {
        reviewer,
        reason: reviewNotes || "Rejected from review queue.",
      });
    }, "Question rejected.");
  }

  async function saveBenchmark(questionId: number) {
    await run("benchmark", async () => {
      await api.post(`/questions/${questionId}/benchmark`, {
        expected_subject_id: subjectId ? Number(subjectId) : null,
        expected_topic_id: topicId ? Number(topicId) : null,
        expected_subtopic_id: subtopicId ? Number(subtopicId) : null,
        expected_concepts: [],
        notes: reviewNotes,
      });
    }, "Benchmark expectation saved.");
  }

  return (
    <>
      <PageHeader
        eyebrow="Human-in-the-loop"
        title="Review queue"
        description="Staged and flagged questions stay out of practice until you approve them. AI suggestions are never auto-accepted."
        actions={
          <div className="flex flex-wrap gap-2">
            <select className="input w-40" value={view} onChange={(e) => setView(e.target.value)}>
              {VIEWS.map((v) => (
                <option key={v.value} value={v.value}>{v.label}</option>
              ))}
            </select>
          </div>
        }
      />

      {actionError ? <div className="mb-4"><ErrorNotice message={actionError} onRetry={refresh} /></div> : null}
      {actionNotice ? <div className="mb-4"><Notice tone="accent">{actionNotice}</Notice></div> : null}

      {data?.counts ? (
        <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {Object.entries(data.counts).map(([key, value]) => (
            <Card key={key} className="p-4">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">{key.replace(/_/g, " ")}</div>
              <div className="mt-1 text-2xl font-bold text-ink">{value}</div>
            </Card>
          ))}
        </div>
      ) : null}

      {loading ? <Loading /> : null}
      {error ? <ErrorNotice message={error} onRetry={refresh} /> : null}

      {data && (data.items?.length ?? 0) > 0 ? (
        <div className="space-y-4">
          {data.items.map((question) => (
            <Card key={question.id} className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <QuestionCard question={question} />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 border-t border-line pt-3">
                <button className="btn-primary btn-sm" onClick={() => approve(question.id)} disabled={busy !== null}>
                  <ShieldCheck className="h-3.5 w-3.5" /> Approve
                </button>
                <button className="btn-danger btn-sm" onClick={() => reject(question.id)} disabled={busy !== null}>
                  Reject
                </button>
                <button className="btn-secondary btn-sm" onClick={() => reclassifyDeterministic(question.id)} disabled={busy !== null}>
                  <Wand2 className="h-3.5 w-3.5" /> Re-run rules
                </button>
                <button className="btn-secondary btn-sm" onClick={() => reclassifyLlm(question.id)} disabled={busy !== null}>
                  LLM suggest
                </button>
                <button className="btn-ghost btn-sm" onClick={() => openClassify(question.id)}>
                  Fix classification
                </button>
                <button className="btn-ghost btn-sm" onClick={() => saveBenchmark(question.id)}>
                  Save benchmark
                </button>
              </div>
            </Card>
          ))}
          {data.pages && data.pages > 1 ? (
            <div className="flex items-center justify-between">
              <button className="btn-secondary btn-sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                Previous
              </button>
              <span className="text-xs text-muted">Page {page}</span>
              <button className="btn-secondary btn-sm" onClick={() => setPage((p) => p + 1)} disabled={(data.items?.length ?? 0) < 25}>
                Next
              </button>
            </div>
          ) : null}
        </div>
      ) : !loading ? (
        <EmptyState
          title="Nothing to review"
          description="Staged or flagged questions appear here after ingestion. Approve them to make them available in practice."
        />
      ) : null}

      <Card className="mt-6">
        <SectionTitle title="Classification benchmark" subtitle="Expected labels saved by you; used to measure rule + LLM agreement." />
        {benchmarkData?.report ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-line bg-surface-2/40 p-3">
              <div className="text-[10px] text-muted">Samples</div>
              <div className="text-xl font-bold">{benchmarkData.report.samples ?? 0}</div>
            </div>
            <div className="rounded-xl border border-line bg-surface-2/40 p-3">
              <div className="text-[10px] text-muted">Subject accuracy</div>
              <div className="text-xl font-bold">{formatMaybe(benchmarkData.report.subject_accuracy)}</div>
            </div>
            <div className="rounded-xl border border-line bg-surface-2/40 p-3">
              <div className="text-[10px] text-muted">Topic accuracy</div>
              <div className="text-xl font-bold">{formatMaybe(benchmarkData.report.topic_accuracy)}</div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted">No benchmark samples yet. Use “Save benchmark” on reviewed questions.</p>
        )}
      </Card>

      <Modal open={selectedId !== null} onClose={() => setSelectedId(null)} title="Fix classification" wide>
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="label">Subject</span>
              <select className="input" value={subjectId} onChange={(e) => { setSubjectId(e.target.value); setTopicId(""); setSubtopicId(""); setConceptIds([]); }}>
                <option value="">Keep / choose</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Topic</span>
              <select className="input" value={topicId} onChange={(e) => { setTopicId(e.target.value); setSubtopicId(""); setConceptIds([]); }} disabled={!subjectId}>
                <option value="">Choose topic</option>
                {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Subtopic</span>
              <select className="input" value={subtopicId} onChange={(e) => { setSubtopicId(e.target.value); setConceptIds([]); }} disabled={!topicId}>
                <option value="">Choose subtopic</option>
                {subtopics.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="label">Concepts</span>
              <select
                multiple
                className="input h-28"
                value={conceptIds.map(String)}
                onChange={(e) => setConceptIds(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
                disabled={!subtopicId}
              >
                {concepts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="label">Reviewer</span>
            <input className="input" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
          </label>
          <label className="block">
            <span className="label">Notes</span>
            <textarea className="input" rows={3} value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} />
          </label>
          <label className="inline-flex items-center gap-2 text-xs">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="h-3.5 w-3.5 accent-[var(--brand)]" />
            Run LLM suggestion first (still requires your accept)
          </label>
          <div className="flex flex-wrap gap-2 pt-2">
            <button className="btn-primary" onClick={() => applyClassification(true)} disabled={busy !== null}>
              Accept classification
            </button>
            <button className="btn-secondary" onClick={() => applyClassification(false)} disabled={busy !== null}>
              Save as pending
            </button>
            <button className="btn-ghost" onClick={() => setSelectedId(null)}>
              Cancel
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function formatMaybe(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return `${(value * 100).toFixed(1)}%`;
  return String(value);
}
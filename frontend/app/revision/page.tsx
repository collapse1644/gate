"use client";

import { Play } from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";

import { Card, EmptyState, ErrorNotice, Loading, PageHeader, SectionTitle } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { RevisionOverview } from "@/lib/types";

export default function RevisionPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <RevisionInner />
    </Suspense>
  );
}

function RevisionInner() {
  const { data, loading, error, refresh } = useApi<RevisionOverview>("/revision");
  const [busy, setBusy] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function review(questionId: number, outcome: "good" | "again") {
    setBusy(questionId);
    try {
      await api.post(`/revision/${questionId}/review`, { outcome });
      refresh();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function startRevisionPractice() {
    try {
      const session = await api.post<{ id: number }>("/practice/sessions", { mode: "revision", limit: 20 });
      window.location.href = `/practice/${session.id}`;
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  if (loading) return <Loading rows={3} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;

  const due = data?.due ?? [];
  const upcoming = data?.upcoming ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Spaced repetition"
        title="Revision"
        description="Due reviews are generated from your attempts. Review outcomes update the schedule; they do not create graded attempts."
        actions={
          <button className="btn-primary btn-sm" onClick={startRevisionPractice}>
            <Play className="h-3.5 w-3.5" /> Start revision practice
          </button>
        }
      />

      {actionError ? <div className="mb-4"><ErrorNotice message={actionError} onRetry={() => setActionError(null)} /></div> : null}

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Card className="p-4">
          <div className="text-[10px] text-muted">Tracked</div>
          <div className="text-2xl font-bold">{data?.tracked ?? 0}</div>
        </Card>
        <Card className="p-4">
          <div className="text-[10px] text-muted">Due now</div>
          <div className="text-2xl font-bold">{due.length}</div>
        </Card>
        <Card className="p-4">
          <div className="text-[10px] text-muted">Upcoming</div>
          <div className="text-2xl font-bold">{upcoming.length}</div>
        </Card>
      </div>

      <Card className="mb-5">
        <SectionTitle title="Due now" />
        {due.length ? (
          <div className="space-y-3">
            {due.map((d) => (
              <div key={d.question_id} className="rounded-xl border border-line bg-surface-2/40 p-3">
                <div className="flex flex-wrap items-center gap-2 text-[11px]">
                  <span className="font-semibold text-ink">{d.year} Q{d.question_no}</span>
                  <span className="text-muted">{d.question_type}</span>
                  <span className="text-muted">lapses {d.lapses}</span>
                </div>
                <p className="mt-1 text-xs text-muted line-clamp-2">{d.question_text}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link href={`/library/${d.question_id}`} className="btn-ghost btn-sm">Open</Link>
                  <button className="btn-primary btn-sm" onClick={() => review(d.question_id, "good")} disabled={busy === d.question_id}>Good</button>
                  <button className="btn-danger btn-sm" onClick={() => review(d.question_id, "again")} disabled={busy === d.question_id}>Again</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="Nothing due" description="Great — no revisions are due right now." />
        )}
      </Card>

      <Card>
        <SectionTitle title="Upcoming" />
        {upcoming.length ? (
          <div className="space-y-2">
            {upcoming.map((u) => (
              <div key={u.question_id} className="flex items-center justify-between rounded-xl border border-line bg-surface-2/40 px-3 py-2 text-xs">
                <span className="font-semibold text-ink">{u.year} Q{u.question_no}</span>
                <span className="text-muted">due {new Date(u.due_at).toLocaleDateString()} · rep {u.repetitions} · {u.interval_days}d</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted">No upcoming revisions tracked.</p>
        )}
      </Card>
    </>
  );
}
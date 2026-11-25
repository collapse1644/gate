"use client";

import { Bot, Play, Send, Square, Sparkles } from "lucide-react";
import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { MathText } from "@/components/math-text";
import { Badge, Card, EmptyState, ErrorNotice, Loading, Notice, PageHeader, SectionTitle, StatusBadge } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { AIStatus, QuestionDetail, TutorMessage, TutorSession, TutorSessionSummary } from "@/lib/types";

export default function TutorPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <TutorInner />
    </Suspense>
  );
}

function TutorInner() {
  const params = useSearchParams();
  const questionId = params.get("question_id");
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [mode, setMode] = useState("doubt");
  const [subjectId, setSubjectId] = useState("");
  const [topicId, setTopicId] = useState("");
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [includeFigures, setIncludeFigures] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [localVision, setLocalVision] = useState(false);

  const { data: status, refresh: refreshStatus } = useApi<AIStatus>("/ai/status");
  const { data: sessionsData, refresh: refreshSessions } = useApi<{ items: TutorSessionSummary[] }>("/ai/tutor/sessions");
  const { data: session, refresh: refreshSession } = useApi<TutorSession>(selectedSessionId ? `/ai/tutor/sessions/${selectedSessionId}` : null);
  const { data: question } = useApi<QuestionDetail>(questionId ? `/questions/${questionId}` : null);

  const sessions = sessionsData?.items ?? [];

  useEffect(() => {
    if (questionId && !selectedSessionId) {
      // auto-create session for the question on first visit
      (async () => {
        try {
          const created = await api.post<TutorSession>("/ai/tutor/sessions", {
            mode: "doubt",
            question_id: Number(questionId),
            title: question ? `${question.year} Q${question.question_no} — doubt` : undefined,
          });
          setSelectedSessionId(created.id);
          refreshSessions();
        } catch (err) {
          setError(errorMessage(err));
        }
      })();
    }
  }, [questionId, question, selectedSessionId, refreshSessions]);

  async function createSession() {
    setBusy("create");
    setError(null);
    try {
      const payload: Record<string, unknown> = { mode, title: title || undefined };
      if (questionId) payload.question_id = Number(questionId);
      if (subjectId) payload.subject_id = Number(subjectId);
      if (topicId) payload.topic_id = Number(topicId);
      const created = await api.post<TutorSession>("/ai/tutor/sessions", payload);
      setSelectedSessionId(created.id);
      setTitle("");
      refreshSessions();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function conceptLesson() {
    if (!topicId && !subjectId) {
      setError("Select a topic or subtopic first.");
      return;
    }
    setBusy("concept");
    setError(null);
    try {
      const res = await api.post<{ session: TutorSession }>("/ai/concept-lesson", {
        subject_id: subjectId ? Number(subjectId) : undefined,
        topic_id: topicId ? Number(topicId) : undefined,
      });
      setSelectedSessionId(res.session.id);
      refreshSessions();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function send() {
    if (!selectedSessionId || !message.trim()) return;
    setBusy("send");
    setError(null);
    try {
      await api.post(`/ai/tutor/sessions/${selectedSessionId}/messages`, {
        message: message.trim(),
        include_figures: includeFigures,
      });
      setMessage("");
      refreshSession();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function startLocal(vision: boolean) {
    setBusy("local");
    setError(null);
    try {
      await api.post(`/ai/local/start${vision ? "?vision=true" : ""}`);
      refreshStatus();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function stopLocal() {
    setBusy("local");
    setError(null);
    try {
      await api.post("/ai/local/stop");
      refreshStatus();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  const messages = session?.messages ?? [];

  return (
    <>
      <PageHeader
        eyebrow="AI tutor"
        title="Tutor"
        description="Explanations are labelled EXPLANATION — NOT VERIFIED. Local-only mode never contacts the cloud."
        actions={
          <Link href="/settings" className="btn-secondary btn-sm">AI settings</Link>
        }
      />

      {error ? <div className="mb-4"><ErrorNotice message={error} onRetry={() => setError(null)} /></div> : null}

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">Mode</div>
          <div className="mt-1 text-sm font-bold text-ink">{status?.mode ?? "—"}</div>
          <div className="text-[11px] text-muted">Cloud consent: {status?.cloud_consent ? "yes" : "no"}</div>
        </Card>
        <Card className="p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">Gemini</div>
          <div className="mt-1 text-sm font-bold text-ink">{status?.gemini?.ready ? "Ready" : status?.gemini?.configured ? "Configured" : "Not configured"}</div>
          <div className="text-[11px] text-muted">{status?.gemini?.model}</div>
        </Card>
        <Card className="p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">Local</div>
          <div className="mt-1 text-sm font-bold text-ink">{status?.local?.ready ? "Ready" : "Stopped"}</div>
          <div className="text-[11px] text-muted">{status?.local?.model}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">Local server</div>
              <div className="mt-1 text-sm font-bold text-ink">{status?.local?.server?.running ? "Running" : "Stopped"}</div>
            </div>
            <div className="flex gap-1">
              <button className="btn-secondary btn-sm" onClick={() => startLocal(false)} disabled={busy === "local"}>
                <Play className="h-3.5 w-3.5" />
              </button>
              <button className="btn-secondary btn-sm" onClick={() => startLocal(true)} disabled={busy === "local"} title="Start with vision model">
                Vision
              </button>
              <button className="btn-danger btn-sm" onClick={stopLocal} disabled={busy === "local"}>
                <Square className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(260px,0.7fr)_minmax(0,1.6fr)]">
        <div className="space-y-4">
          <Card>
            <SectionTitle title="Sessions" />
            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {sessions.length ? sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSessionId(s.id)}
                  className={`block w-full rounded-xl border px-3 py-2 text-left text-xs transition ${selectedSessionId === s.id ? "border-brand bg-brand-soft/60" : "border-line bg-surface-2/40 hover:bg-surface-2"}`}
                >
                  <div className="font-semibold text-ink">{s.title}</div>
                  <div className="text-muted">{s.mode} · {s.message_count} messages · {s.updated_at ? new Date(s.updated_at).toLocaleDateString() : ""}</div>
                </button>
              )) : <p className="text-xs text-muted">No sessions yet.</p>}
            </div>
          </Card>

          <Card>
            <SectionTitle title="New session" />
            <div className="space-y-2">
              <select className="input" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="doubt">Doubt (question)</option>
                <option value="knows">Knows concept</option>
                <option value="wrong">Got it wrong</option>
                <option value="unknown">Unknown</option>
                <option value="concept">Concept lesson</option>
              </select>
              <input className="input" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
              <input className="input" placeholder="Subject id (optional)" value={subjectId} onChange={(e) => setSubjectId(e.target.value)} />
              <input className="input" placeholder="Topic id (optional)" value={topicId} onChange={(e) => setTopicId(e.target.value)} />
              <div className="flex gap-2">
                <button className="btn-primary btn-sm" onClick={createSession} disabled={busy === "create"}>Create</button>
                <button className="btn-secondary btn-sm" onClick={conceptLesson} disabled={busy === "concept"}>Concept lesson</button>
              </div>
            </div>
          </Card>
        </div>

        <Card className="min-h-[520px]">
          {session ? (
            <div className="flex h-full flex-col">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-ink">{session.title}</h2>
                  <p className="text-[11px] text-muted">{session.mode}{session.question ? ` · ${session.question.year} Q${session.question.question_no}` : ""}</p>
                </div>
                <StatusBadge status="EXPLANATION — NOT VERIFIED" />
              </div>
              {session.question ? (
                <div className="mb-3 rounded-xl border border-line bg-surface-2/40 p-3">
                  <MathText text={session.question.question_text.slice(0, 280)} className="text-[12px] text-ink" />
                </div>
              ) : null}
              <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                {messages.map((m) => (
                  <div key={m.id} className={`rounded-xl border px-3.5 py-2.5 text-[13px] ${m.role === "user" ? "border-brand/30 bg-brand-soft/40" : "border-line bg-surface-2/40"}`}>
                    <div className="mb-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-muted">
                      {m.role}
                      {m.provider ? <Badge tone="neutral">{m.provider}:{m.model}</Badge> : null}
                      {m.role === "assistant" ? <Badge tone="warn">not verified</Badge> : null}
                    </div>
                    <MathText text={m.content} className="text-ink" />
                  </div>
                ))}
                {messages.length === 0 ? <EmptyState title="Start the conversation" description="Ask a doubt about the selected question or concept." /> : null}
              </div>
              <div className="mt-3 border-t border-line pt-3">
                <label className="mb-2 inline-flex items-center gap-2 text-xs text-muted">
                  <input type="checkbox" checked={includeFigures} onChange={(e) => setIncludeFigures(e.target.checked)} className="h-3.5 w-3.5 accent-[var(--brand)]" />
                  Include figures (vision model)
                </label>
                <div className="flex gap-2">
                  <textarea
                    className="input min-h-[44px] flex-1 resize-y"
                    rows={2}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Ask a question…"
                    onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send(); }}
                  />
                  <button className="btn-primary self-end" onClick={send} disabled={busy === "send" || !message.trim()}>
                    <Send className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-1 text-[10px] text-muted">Ctrl/Cmd+Enter to send. AI output is never treated as verified.</p>
              </div>
            </div>
          ) : (
            <EmptyState title="Select or create a session" description="Pick a session from the list, or create a new one." icon={<Bot className="h-5 w-5" />} />
          )}
        </Card>
      </div>
    </>
  );
}
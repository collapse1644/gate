"use client";

import clsx from "clsx";
import {
  ArrowLeft,
  Bookmark,
  Bot,
  CheckCircle2,
  ChevronDown,
  Eye,
  FileText,
  ImageIcon,
  Maximize,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Wand2,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { MathText } from "@/components/math-text";
import { PdfViewer } from "@/components/pdf-viewer";
import {
  Badge,
  Card,
  EmptyState,
  ErrorNotice,
  Field,
  KeyValue,
  Loading,
  Notice,
  PageHeader,
  SectionTitle,
  StatusBadge,
  Spinner,
} from "@/components/ui";
import { api, assetUrl, errorMessage } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Attempt, QuestionDetail, Solution } from "@/lib/types";

const MODES = [
  { value: "unknown", label: "Explain from scratch" },
  { value: "knows", label: "I know the concept" },
  { value: "wrong", label: "I got it wrong" },
];

export default function QuestionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data, loading, error, refresh, setData } = useApi<QuestionDetail>(id ? `/questions/${id}` : null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [mode, setMode] = useState("unknown");
  const [working, setWorking] = useState("");
  const [reviewer, setReviewer] = useState("local-user");
  const [reviewNotes, setReviewNotes] = useState("");

  // Answer interaction state
  const [selected, setSelected] = useState<string | null>(null);
  const [msqSelected, setMsqSelected] = useState<string[]>([]);
  const [natValue, setNatValue] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<Attempt | null>(null);
  const [questionStart, setQuestionStart] = useState(Date.now());
  const [aiExplanationLoading, setAiExplanationLoading] = useState(false);
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);

  if (loading) return <Loading rows={4} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;
  if (!data) return null;

  const current = data.current_solution;
  const isPreview = data.import_status !== "approved";
  const isMsq = data.question_type === "MSQ";
  const isNat = data.question_type === "NAT";
  const hasOfficialAnswer = Boolean(data.official_answer);

  function currentAnswer(): string | null {
    if (isMsq) return msqSelected.length ? msqSelected.sort().join(",") : null;
    if (isNat) return natValue.trim() || null;
    return selected;
  }

  async function run(label: string, action: () => Promise<QuestionDetail | void>, notice?: string) {
    setBusy(label);
    setActionError(null);
    setActionNotice(null);
    try {
      const result = await action();
      if (result) setData(result);
      else refresh();
      if (notice) setActionNotice(notice);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function toggleBookmark() {
    const response = await api.post<{ id: number; is_bookmarked: boolean }>(`/questions/${data!.id}/bookmark`, {
      is_bookmarked: !data!.is_bookmarked,
    });
    setData({ ...data!, is_bookmarked: response.is_bookmarked });
  }

  async function generateSolution() {
    await run(
      "solution",
      async () => {
        const response = await api.post<{ question: QuestionDetail; notice: string }>(`/ai/solution/${data!.id}`, {
          mode,
          working_text: working,
        });
        setActionNotice(response.notice);
        return response.question;
      },
      undefined,
    );
  }

  async function requestAiExplanation() {
    setAiExplanationLoading(true);
    setActionNotice(null);
    try {
      const response = await api.post<{ question: QuestionDetail; notice: string }>(`/ai/solution/${data!.id}`, {
        mode: "unknown",
        working_text: working,
      });
      setActionNotice(response.notice + " (AI explanation is UNVERIFIED)");
      setFeedback((prev) => (prev ? { ...prev, is_correct: null } : null));
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setAiExplanationLoading(false);
    }
  }

  async function submitAnswer() {
    const answer = currentAnswer();
    if (answer === null && !window.confirm("Submit without an answer?")) return;
    setSubmitting(true);
    setActionError(null);
    try {
      const response = await api.post<Attempt>(`/questions/${data!.id}/attempts`, {
        question_id: data!.id,
        selected_answer: answer,
        time_spent_seconds: Math.max(0, Math.round((Date.now() - questionStart) / 1000)),
        working_text: working,
        mode: isPreview ? "preview" : "practice",
      });
      setFeedback(response);
      setSubmitted(true);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function verifySolution() {
    if (!current) return;
    await run("verify", async () => {
      const response = await api.post<{ solution: Solution; notice: string }>(
        `/solutions/${current.id}/verify`,
        { generate_plan: true },
      );
      setActionNotice(response.notice);
      refresh();
    });
  }

  async function manualCheck(passed: boolean) {
    if (!current) return;
    await run("manual", async () => {
      const response = await api.post<{ solution: Solution; notice: string }>(
        `/solutions/${current.id}/manual-check`,
        {
          passed,
          reviewer: reviewer || "local-user",
          notes: reviewNotes || (passed ? "Reviewed by local user." : "Review did not pass."),
          check_type: "expert_review",
        },
      );
      setActionNotice(response.notice);
      refresh();
    });
  }

  async function rerunClassifier() {
    await run("classify", async () => {
      const response = await api.post<{ question: QuestionDetail }>(`/questions/${data!.id}/classify`, {
        use_llm: false,
      });
      return response.question;
    }, "Deterministic classifier re-run. LLM suggestions are not auto-accepted.");
  }

  async function interpretAsset(assetId: number) {
    await run("vision", async () => {
      const response = await api.post<{ notice: string }>(`/ai/vision/${data!.id}`, { asset_id: assetId });
      setActionNotice(response.notice);
      refresh();
    });
  }

  async function moderate(approve: boolean) {
    if (!approve && !window.confirm("Reject this question? It will leave the practice pool.")) return;
    await run(approve ? "approve" : "reject", async () => {
      if (approve) {
        return api.post<QuestionDetail>(`/questions/${data!.id}/approve`, { reviewer: reviewer || "local-user" });
      }
      await api.post(`/questions/${data!.id}/reject`, {
        reviewer: reviewer || "local-user",
        reason: reviewNotes || "Rejected from local review.",
      });
      refresh();
    }, approve ? "Question approved for practice." : "Question rejected.");
  }

  const isCorrect = feedback?.is_correct;
  const answerShown = submitted && feedback;

  return (
    <>
      <Link href="/library" className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink">
        <ArrowLeft className="h-3.5 w-3.5" /> PYQ library
      </Link>

      <PageHeader
        eyebrow={`${data.year} · Question ${data.question_no}${data.subtopic ? ` · ${data.subtopic}` : ""}${
          isPreview ? " · STAGED (preview)" : ""
        }`}
        title={data.paper_label || `GATE ${data.year} CS`}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={data.verification_status} />
            <Badge tone="neutral">{data.question_type}</Badge>
            {data.marks ? <Badge tone="neutral">{data.marks} marks</Badge> : null}
            {data.negative_marks ? <Badge tone="warn">negative {data.negative_marks.toFixed(2)}</Badge> : null}
            <Badge tone={data.import_status === "approved" ? "accent" : "warn"}>{data.import_status}</Badge>
            <Badge tone="neutral">extraction {formatPercent(data.extraction_confidence)}</Badge>
            <Badge tone="neutral">classification {formatPercent(data.classification_confidence)}</Badge>
          </span>
        }
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => run("bookmark", toggleBookmark)}>
              <Bookmark className={clsx("h-4 w-4", data!.is_bookmarked && "fill-brand text-brand")} />
              {data!.is_bookmarked ? "Bookmarked" : "Bookmark"}
            </button>
            <Link href={`/tutor?question_id=${data!.id}`} className="btn-primary">
              <Sparkles className="h-4 w-4" /> Ask tutor
            </Link>
          </>
        }
      />

      {isPreview ? (
        <Notice tone="warn" title="Preview mode — staged question">
          This question is staged and not yet approved for practice. Your attempt will be recorded as a preview and
          will not affect official practice statistics. Approve the question to include it in regular practice.
        </Notice>
      ) : null}

      {actionError ? <div className="mb-4"><ErrorNotice message={actionError} /></div> : null}
      {actionNotice ? (
        <div className="mb-4">
          <Notice tone="brand" title="Action completed">{actionNotice}</Notice>
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.85fr)]">
        <div className="space-y-5">
          <Card>
            <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] text-muted">
              <FileText className="h-3.5 w-3.5" />
              {data.source_pdf ? <span className="mono truncate">{data.source_pdf}</span> : "Source PDF"}
              {data.source_page ? <Badge tone="neutral">page {data.source_page}</Badge> : null}
              {data.source_pdf && data.source_page ? (
                <button
                  type="button"
                  onClick={() => {
                    setPdfViewerOpen(true);
                  }}
                  className="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline"
                >
                  <Maximize className="h-3 w-3" /> View original PDF page
                </button>
              ) : null}
            </div>
            <MathText text={data.question_text} className="text-[15px] leading-8 text-ink" />

            {data.options.length ? (
              <div className="mt-5 space-y-2">
                {data.options.map((option) => {
                  const isSelected =
                    (isMsq && msqSelected.includes(option.key)) ||
                    (!isMsq && !isNat && selected === option.key);
                  const official = hasOfficialAnswer
                    ? data.official_answer!
                        .toUpperCase()
                        .split(/[,\s]+/)
                        .includes(option.key.toUpperCase())
                    : false;
                  return (
                    <div
                      key={option.key}
                      onClick={() => {
                        if (submitted) return;
                        if (isMsq) {
                          setMsqSelected((prev) =>
                            prev.includes(option.key) ? prev.filter((k) => k !== option.key) : [...prev, option.key]
                          );
                        } else if (isNat) {
                          // NAT uses text input, not option click
                        } else {
                          setSelected(option.key);
                        }
                      }}
                      className={clsx(
                        "flex items-start gap-3 rounded-xl border px-3.5 py-2.5 cursor-pointer transition",
                        submitted
                          ? official
                            ? "border-accent/40 bg-accent-soft/60"
                            : isSelected
                              ? "border-danger/40 bg-danger-soft/60"
                              : "border-line bg-surface-2/40"
                          : isSelected
                            ? "border-brand bg-brand-soft/60"
                            : "border-line bg-surface-2/40 hover:bg-surface-2",
                      )}
                    >
                      <span
                        className={clsx(
                          "flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold",
                          isSelected
                            ? "bg-brand text-white"
                            : "bg-surface text-muted",
                        )}
                      >
                        {isMsq ? (
                          <input
                            type="checkbox"
                            checked={isSelected}
                            readOnly
                            className="h-4 w-4"
                          />
                        ) : (
                          option.key
                        )}
                      </span>
                      <MathText text={option.text} className="pt-0.5 text-[13px] text-ink" inline />
                      {submitted && official ? (
                        <CheckCircle2 className="ml-auto mt-1 h-4 w-4 shrink-0 text-accent" />
                      ) : submitted && isSelected && !official ? (
                        <XCircle className="ml-auto mt-1 h-4 w-4 shrink-0 text-danger" />
                      ) : null}
                    </div>
                  );
                })}
                {isNat && (
                  <div className="mt-3">
                    <label className="block text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
                      Numerical answer
                    </label>
                    <input
                      type="text"
                      inputMode="decimal"
                      value={natValue}
                      onChange={(e) => setNatValue(e.target.value)}
                      placeholder="e.g. 42 or 0.75 to 0.85"
                      className="input max-w-xs"
                      disabled={submitted}
                    />
                  </div>
                )}
              </div>
            ) : null}

            {submitted && feedback ? (
              <div className="mt-4 rounded-xl border px-4 py-3">
                <div className="flex items-center gap-2 text-sm font-semibold mb-2">
                  {isCorrect === true ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-accent" />
                      <span className="text-accent">Correct</span>
                    </>
                  ) : isCorrect === false ? (
                    <>
                      <XCircle className="h-4 w-4 text-danger" />
                      <span className="text-danger">Incorrect</span>
                    </>
                  ) : (
                    <>
                      <Eye className="h-4 w-4 text-warn" />
                      <span className="text-warn">Not graded — no official answer</span>
                    </>
                  )}
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted">Your answer:</span>
                    <span className="text-ink">{currentAnswer() ?? "—"}</span>
                  </div>
                  {hasOfficialAnswer && (
                    <div className="flex justify-between">
                      <span className="text-muted">Official answer:</span>
                      <span className="text-ink font-medium">{data.official_answer}</span>
                    </div>
                  )}
                  {!hasOfficialAnswer && (
                    <div className="flex justify-between">
                      <span className="text-muted">Official answer:</span>
                      <span className="text-warn">Unavailable — grading not possible</span>
                    </div>
                  )}
                </div>
                {feedback?.explanation && (
                  <div className="mt-2 rounded-lg border border-line bg-surface-2/40 p-2">
                    <p className="text-[10px] font-semibold text-muted mb-1">Official explanation:</p>
                    <MathText text={feedback.explanation} className="text-[12px] text-ink" />
                  </div>
                )}
                {!hasOfficialAnswer && !aiExplanationLoading && !data.current_solution ? (
                  <button
                    type="button"
                    onClick={requestAiExplanation}
                    className="mt-2 btn-secondary btn-sm"
                    disabled={aiExplanationLoading}
                  >
                    {aiExplanationLoading ? <Spinner className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}
                    Request AI explanation (UNVERIFIED)
                  </button>
                ) : null}
              </div>
            ) : null}

            {!submitted && data.options.length && !isNat ? (
              <div className="mt-4">
                <button
                  type="button"
                  onClick={submitAnswer}
                  disabled={submitting || currentAnswer() === null}
                  className="btn-primary"
                >
                  {submitting ? <Spinner className="h-4 w-4" /> : "Submit answer"}
                </button>
                {currentAnswer() === null && !submitting ? (
                  <p className="mt-1 text-[10px] text-muted">Please select an answer before submitting.</p>
                ) : null}
              </div>
            ) : null}

            {!submitted && isNat && !submitting ? (
              <div className="mt-4">
                <button
                  type="button"
                  onClick={submitAnswer}
                  disabled={currentAnswer() === null}
                  className="btn-primary"
                >
                  Submit answer
                </button>
              </div>
            ) : null}
          </Card>

          <Card>
            <SectionTitle
              title="Solutions"
              subtitle="AI explanations are versioned and start UNVERIFIED. Official answers are never overwritten."
              action={
                <button type="button" onClick={refresh} className="btn-ghost btn-sm">
                  <RefreshCw className="h-3.5 w-3.5" /> Refresh
                </button>
              }
            />
            {current ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={current.verification_status} />
                  <Badge tone="neutral">v{current.version}</Badge>
                  <Badge tone="neutral">{current.provider}:{current.model}</Badge>
                  {current.final_answer ? <Badge tone="brand">final answer {current.final_answer}</Badge> : null}
                </div>
                {current.verification_status !== "VERIFIED" ? (
                  <Notice tone="warn" title="Not verified">
                    This is an AI-generated explanation. It has not been independently verified. Check the
                    verification evidence below before relying on the final answer.
                  </Notice>
                ) : null}
                <div className="rounded-xl border border-line bg-surface-2/40 p-4">
                  <MathText text={current.content} className="text-[13px] text-ink" />
                </div>

                {current.checks?.length ? (
                  <div className="overflow-x-auto rounded-xl border border-line">
                    <table className="w-full text-left text-[11px]">
                      <thead className="bg-surface-2 text-muted">
                        <tr>
                          <th className="px-3 py-2 font-semibold">Check</th>
                          <th className="px-3 py-2 font-semibold">Independent</th>
                          <th className="px-3 py-2 font-semibold">Result</th>
                          <th className="px-3 py-2 font-semibold">Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {current.checks.map((check) => (
                          <tr key={check.id} className="border-t border-line">
                            <td className="px-3 py-2">{check.description || check.check_type}</td>
                            <td className="px-3 py-2">{check.independent ? "Yes" : "No"}</td>
                            <td className="px-3 py-2">
                              {check.passed === true ? (
                                <span className="text-accent">Passed</span>
                              ) : check.passed === false ? (
                                <span className="text-danger">Failed</span>
                              ) : (
                                <span className="text-warn">Inconclusive</span>
                              )}
                            </td>
                            <td className="max-w-[280px] px-3 py-2 text-muted">{check.notes || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-[11px] text-muted">No verification checks recorded yet.</p>
                )}

                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary btn-sm" onClick={verifySolution} disabled={busy === "verify"}>
                    {busy === "verify" ? <Spinner className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                    Run verification
                  </button>
                  <details className="w-full rounded-xl border border-line bg-surface-2/30 p-3">
                    <summary className="cursor-pointer text-[11px] font-semibold text-ink">
                      Record a manual expert check
                    </summary>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <Field label="Reviewer">
                        <input className="input" value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
                      </Field>
                      <Field label="Notes">
                        <input
                          className="input"
                          value={reviewNotes}
                          onChange={(event) => setReviewNotes(event.target.value)}
                          placeholder="What did you check?"
                        />
                      </Field>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button type="button" className="btn-primary btn-sm" onClick={() => manualCheck(true)} disabled={busy === "manual"}>
                        <ThumbsUp className="h-3.5 w-3.5" /> Passed
                      </button>
                      <button type="button" className="btn-danger btn-sm" onClick={() => manualCheck(false)} disabled={busy === "manual"}>
                        <ThumbsDown className="h-3.5 w-3.5" /> Failed
                      </button>
                    </div>
                    <p className="mt-2 text-[10px] leading-relaxed text-muted">
                      Manual checks are appended to the audit trail with your reviewer name. They do not erase
                      earlier checks or versions.
                    </p>
                  </details>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-line bg-surface-2/30 p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-ink">
                  <Bot className="h-4 w-4 text-brand" /> No AI solution generated
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  Generate an explanation with your configured provider. It will be stored as UNVERIFIED until
                  checks pass.
                </p>
                <div className="mt-3 grid gap-2 sm:grid-cols-[180px_1fr_auto]">
                  <select className="input" value={mode} onChange={(event) => setMode(event.target.value)}>
                    {MODES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                  <input
                    className="input"
                    value={working}
                    onChange={(event) => setWorking(event.target.value)}
                    placeholder="Optional: your working / where you got stuck"
                  />
                  <button type="button" className="btn-primary" onClick={generateSolution} disabled={busy === "solution"}>
                    {busy === "solution" ? <Spinner className="h-4 w-4" /> : <Wand2 className="h-4 w-4" />}
                    Generate
                  </button>
                </div>
                <p className="mt-2 text-[10px] text-muted">
                  Provider routing is controlled in Settings. Local-only mode never contacts the cloud.
                </p>
              </div>
            )}

            {data.solutions.length > 1 ? (
              <details className="mt-4 rounded-xl border border-line p-3">
                <summary className="cursor-pointer text-[11px] font-semibold text-ink">
                  Earlier versions ({data.solutions.length - 1})
                </summary>
                <div className="mt-2 space-y-2">
                  {data.solutions.slice(1).map((solution) => (
                    <div key={solution.id} className="rounded-lg bg-surface-2/50 p-2.5 text-[11px] text-muted">
                      v{solution.version} · {solution.provider}:{solution.model} · {formatDate(solution.created_at)} ·{" "}
                      {solution.verification_status}
                    </div>
                  ))}
                </div>
              </details>
            ) : null}
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <SectionTitle title="Official answer" />
            <KeyValue label="Answer key">{data.official_answer ?? "Not matched"}</KeyValue>
            <KeyValue label="Question type">{data.question_type}</KeyValue>
            <KeyValue label="Marks">{data.marks ?? "Unknown"}</KeyValue>
            <KeyValue label="Negative">{data.negative_marks ?? "—"}</KeyValue>
            {!data.official_answer ? (
              <Notice tone="warn" className="mt-3">
                Official answer unavailable — grading is not currently possible. You can still save your attempt
                and request an AI explanation (clearly labelled UNVERIFIED).
              </Notice>
            ) : null}
          </Card>

          <Card>
            <SectionTitle title="Classification" />
            <div className="space-y-0">
              <KeyValue label="Subject">{data.subject ?? "Unclassified"}</KeyValue>
              <KeyValue label="Topic">{data.topic ?? "—"}</KeyValue>
              <KeyValue label="Subtopic">{data.subtopic ?? "—"}</KeyValue>
              <KeyValue label="Method">{data.classification_method}</KeyValue>
              <KeyValue label="Confidence">{formatPercent(data.classification_confidence, 1)}</KeyValue>
              <KeyValue label="Review status">{data.review_status}</KeyValue>
            </div>
            {data.concepts.length ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {data.concepts.map((concept) => (
                  <Badge key={concept} tone="brand">
                    {concept}
                  </Badge>
                ))}
              </div>
            ) : null}
            {data.review_notes ? (
              <details className="mt-3 rounded-lg border border-line bg-surface-2/40 p-2.5">
                <summary className="cursor-pointer text-[11px] font-semibold text-ink">
                  Classifier evidence
                </summary>
                <pre className="mono mt-1 max-h-48 overflow-auto whitespace-pre-wrap text-[10px] text-muted">
                  {data.review_notes}
                </pre>
              </details>
            ) : null}
            <button type="button" onClick={rerunClassifier} className="btn-secondary btn-sm mt-3" disabled={busy === "classify"}>
              {busy === "classify" ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
              Re-run deterministic classifier
            </button>
            <Link href={`/review?question=${data!.id}`} className="mt-2 block text-[11px] font-semibold text-brand hover:underline">
              Fix classification in review queue →
            </Link>
          </Card>

          <Card>
            <SectionTitle title="Review" />
            {data.needs_review ? <Badge tone="warn" className="mb-2">Flagged for review</Badge> : null}
            <p className="text-[11px] leading-relaxed text-muted">
              {data.import_status === "approved"
                ? "Approved for practice. You can reject it if the extraction is wrong."
                : "This question is staged and must be approved before it enters practice."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.import_status !== "approved" ? (
                <button type="button" className="btn-primary btn-sm" onClick={() => moderate(true)} disabled={busy === "approve"}>
                  <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                </button>
              ) : null}
              {data.import_status !== "rejected" ? (
                <button type="button" className="btn-danger btn-sm" onClick={() => moderate(false)} disabled={busy === "reject"}>
                  <ThumbsDown className="h-3.5 w-3.5" /> Reject
                </button>
              ) : null}
            </div>
            {data.extraction_notes.length ? (
              <details className="mt-3">
                <summary className="cursor-pointer text-[11px] font-semibold text-muted">
                  Extraction notes ({data.extraction_notes.length})
                </summary>
                <ul className="mt-1 list-disc space-y-1 pl-4 text-[10px] text-muted">
                  {data.extraction_notes.map((note, index) => (
                    <li key={index}>{note}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </Card>

          <Card>
            <SectionTitle title="Provenance" />
            <KeyValue label="Source">{data.source_pdf || "—"}</KeyValue>
            <KeyValue label="Page">{data.source_page ?? "—"}</KeyValue>
            <KeyValue label="Session">{data.session ?? "—"}</KeyValue>
            <KeyValue label="Public ID">
              <span className="mono text-[10px]">{data.public_id}</span>
            </KeyValue>
            <KeyValue label="Imported">{formatDate(data.created_at)}</KeyValue>
          </Card>

          {data.assets.some((asset) => asset.interpretation) ? (
            <Notice tone="warn" title="AI figure interpretation is not the figure">
              Interpretations are stored separately and never replace the clipped original. Treat them as
              hypotheses.
            </Notice>
          ) : null}
        </div>
      </div>

      {data.source_pdf && data.source_page ? (
        <PdfViewer
          open={pdfViewerOpen}
          onClose={() => setPdfViewerOpen(false)}
          imageUrl={`/api/questions/${data!.id}/pdf-page?dpi=200`}
          pdfName={data.source_pdf.split("/").pop() || "source.pdf"}
          pageNumber={data.source_page}
          totalPages={1}
        />
      ) : null}

    </>
  );
}
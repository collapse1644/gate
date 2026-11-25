"use client";

import { Database, Download, RefreshCw, ShieldCheck, UploadCloud } from "lucide-react";
import { Suspense, useEffect, useRef, useState } from "react";

import { Badge, Card, EmptyState, ErrorNotice, Loading, PageHeader, SectionTitle } from "@/components/ui";
import { api, downloadUrl, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { formatBytes } from "@/lib/format";
import type { DataOverview, IngestionJobDetail, IntegrityReport } from "@/lib/types";

export default function DataPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <DataInner />
    </Suspense>
  );
}

function DataInner() {
  const { data: overview, loading, error, refresh } = useApi<DataOverview>("/data/overview");
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<number | null>(null);
  const [job, setJob] = useState<IngestionJobDetail | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [integrity, setIntegrity] = useState<IntegrityReport | null>(null);
  const [integrityBusy, setIntegrityBusy] = useState(false);
  const [backupLabel, setBackupLabel] = useState("manual");
  const [backupBusy, setBackupBusy] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    const poll = async () => {
      try {
        const detail = await api.get<IngestionJobDetail>(`/ingestion/${jobId}`);
        setJob(detail);
        if (detail.job.status === "completed" || detail.job.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          refresh();
        }
      } catch (err) {
        setUploadError(errorMessage(err));
      }
    };
    poll();
    pollRef.current = setInterval(poll, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, refresh]);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setJob(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post<{ job_id: number }>("/ingestion/upload", form);
      setJobId(res.job_id);
    } catch (err) {
      setUploadError(errorMessage(err));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function resume() {
    if (!jobId) return;
    try {
      await api.post(`/ingestion/${jobId}/resume`);
      // restart polling
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
      setJobId(jobId);
    } catch (err) {
      setUploadError(errorMessage(err));
    }
  }

  async function runIntegrity() {
    setIntegrityBusy(true);
    try {
      setIntegrity(await api.get<IntegrityReport>("/data/integrity"));
    } catch (err) {
      setUploadError(errorMessage(err));
    } finally {
      setIntegrityBusy(false);
    }
  }

  async function createBackup() {
    setBackupBusy(true);
    try {
      await api.post("/data/backups", { label: backupLabel || "manual" });
      refresh();
    } catch (err) {
      setUploadError(errorMessage(err));
    } finally {
      setBackupBusy(false);
    }
  }

  async function restore(filename: string) {
    if (!window.confirm(`Restore database from ${filename}? This replaces current data.`)) return;
    try {
      await api.post("/data/restore", { filename });
      refresh();
      alert("Restored. Restart backend to fully reload.");
    } catch (err) {
      setUploadError(errorMessage(err));
    }
  }

  if (loading) return <Loading rows={3} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;

  return (
    <>
      <PageHeader
        eyebrow="Local-first data"
        title="Data management"
        description="Upload official ZIPs, inspect storage, run integrity checks, create backups, and export data. Nothing leaves this machine unless you export it."
      />

      {uploadError ? <div className="mb-4"><ErrorNotice message={uploadError} onRetry={() => setUploadError(null)} /></div> : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.9fr)]">
        <div className="space-y-5">
          <Card>
            <SectionTitle title="Upload PYQ ZIP" />
            <div className="flex flex-wrap items-center gap-3">
              <input ref={fileRef} type="file" accept=".zip" className="input max-w-md" />
              <button className="btn-primary" onClick={upload} disabled={uploading}>
                <UploadCloud className="h-4 w-4" /> {uploading ? "Uploading…" : "Upload"}
              </button>
            </div>
            <p className="mt-2 text-[11px] text-muted">
              ZIP must contain question-paper PDFs and matching answer-key PDFs. Text-layer PDFs only; scans are flagged for manual review.
            </p>

            {job ? (
              <div className="mt-4 rounded-xl border border-line bg-surface-2/40 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-ink">{job.job.filename}</div>
                    <div className="text-[11px] text-muted">{job.job.status} · {job.job.stage}</div>
                  </div>
                  <Badge tone={job.job.status === "completed" ? "accent" : job.job.status === "failed" ? "danger" : "warn"}>{job.job.status}</Badge>
                </div>
                {job.job.error ? <p className="mt-2 text-xs text-danger">{job.job.error}</p> : null}
                <div className="mt-3 space-y-1 text-[11px]">
                  {job.files.map((f) => (
                    <div key={f.id} className="flex items-center justify-between rounded-lg border border-line bg-surface px-2.5 py-1.5">
                      <span className="truncate">{f.relative_path}</span>
                      <span className="text-muted">{f.kind} · {f.status} · {f.questions_found}Q/{f.answers_found}A</span>
                    </div>
                  ))}
                </div>
                {job.job.status === "failed" || job.files.some((f) => f.status === "failed" || f.status === "needs_review") ? (
                  <button className="btn-secondary btn-sm mt-3" onClick={resume}>Resume failed files</button>
                ) : null}
              </div>
            ) : null}
          </Card>

          <Card>
            <SectionTitle title="Ingestion history" />
            {overview?.ingestion_history?.length ? (
              <div className="space-y-2">
                {overview.ingestion_history.map((j) => (
                  <div key={j.id} className="flex items-center justify-between rounded-xl border border-line bg-surface-2/40 px-3 py-2 text-xs">
                    <span className="font-semibold text-ink">{j.filename}</span>
                    <span className="text-muted">{j.status} · {j.created_at ? new Date(j.created_at).toLocaleString() : ""}</span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No uploads yet" description="Upload a ZIP to begin." />
            )}
          </Card>

          <Card>
            <SectionTitle title="Integrity check" />
            <button className="btn-secondary btn-sm" onClick={runIntegrity} disabled={integrityBusy}>
              <ShieldCheck className="h-3.5 w-3.5" /> {integrityBusy ? "Checking…" : "Run integrity check"}
            </button>
            {integrity ? (
              <div className="mt-3 rounded-xl border border-line bg-surface-2/40 p-3 text-xs">
                <div className="font-semibold text-ink">SQLite: {integrity.sqlite_integrity}</div>
                <div className="text-muted">OK: {String(integrity.ok)} · checked {new Date(integrity.checked_at).toLocaleString()}</div>
                {integrity.issues?.length ? (
                  <ul className="mt-2 list-disc pl-4 text-danger">
                    {integrity.issues.map((i, idx) => <li key={idx}>{i.type}: {JSON.stringify(i.detail)}</li>)}
                  </ul>
                ) : (
                  <p className="mt-2 text-accent">No issues found.</p>
                )}
              </div>
            ) : null}
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <SectionTitle title="Storage" />
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-muted">Database</span><span>{formatBytes(overview?.database?.size_bytes)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Originals</span><span>{formatBytes(overview?.storage?.originals_bytes)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Assets</span><span>{formatBytes(overview?.storage?.assets_bytes)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Uploads</span><span>{formatBytes(overview?.storage?.uploads_bytes)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Backups</span><span>{formatBytes(overview?.storage?.backups_bytes)}</span></div>
              <div className="flex justify-between font-semibold"><span>Total</span><span>{formatBytes(overview?.storage?.total_bytes)}</span></div>
            </div>
            <p className="mt-2 text-[10px] text-muted mono break-all">{overview?.database?.path}</p>
          </Card>

          <Card>
            <SectionTitle title="Backups" />
            <div className="flex items-center gap-2">
              <input className="input" value={backupLabel} onChange={(e) => setBackupLabel(e.target.value)} placeholder="label" />
              <button className="btn-secondary btn-sm" onClick={createBackup} disabled={backupBusy}>
                {backupBusy ? "…" : "Create"}
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {overview?.backups?.length ? overview.backups.map((b) => (
                <div key={b.file} className="flex items-center justify-between rounded-xl border border-line bg-surface-2/40 px-3 py-2 text-xs">
                  <div>
                    <div className="font-semibold text-ink">{b.file}</div>
                    <div className="text-muted">{formatBytes(b.size_bytes)} · {new Date(b.modified_at).toLocaleString()}</div>
                  </div>
                  <button className="btn-ghost btn-sm" onClick={() => restore(b.file)}>Restore</button>
                </div>
              )) : <p className="text-xs text-muted">No backups.</p>}
            </div>
          </Card>

          <Card>
            <SectionTitle title="Export" />
            <a href={downloadUrl("/data/export/file")} className="btn-secondary btn-sm inline-flex" download>
              <Download className="h-3.5 w-3.5" /> Download JSON export
            </a>
            <p className="mt-2 text-[10px] text-muted">Exports questions, taxonomy progress, formulas, and settings metadata.</p>
          </Card>

          <Card>
            <SectionTitle title="Refresh" />
            <button className="btn-ghost btn-sm" onClick={refresh}>
              <RefreshCw className="h-3.5 w-3.5" /> Refresh overview
            </button>
          </Card>
        </div>
      </div>
    </>
  );
}
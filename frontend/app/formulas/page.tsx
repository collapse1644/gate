"use client";

import { Bookmark, Plus } from "lucide-react";
import { Suspense, useEffect, useMemo, useState } from "react";

import { Badge, Card, EmptyState, ErrorNotice, Loading, Modal, Notice, PageHeader, SectionTitle } from "@/components/ui";
import { Latex } from "@/components/math-text";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Formula, Subject } from "@/lib/types";

export default function FormulasPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <FormulasInner />
    </Suspense>
  );
}

function FormulasInner() {
  const [subjectId, setSubjectId] = useState("");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [bookmarked, setBookmarked] = useState("");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Formula | null>(null);
  const [sheetSubject, setSheetSubject] = useState("");
  const [flashSubject, setFlashSubject] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: subjectsData } = useApi<{ subjects: Subject[] }>("/subjects");
  const path = useMemo(() => `/formulas${api.query({ subject_id: subjectId, status, q, bookmarked: bookmarked === "true" ? true : bookmarked === "false" ? false : undefined, page, page_size: 30 })}`, [subjectId, status, q, bookmarked, page]);
  const { data, loading, error: listError, refresh } = useApi<{ items: Formula[]; total: number; page: number }>(path);
  const { data: sheet } = useApi<any>(sheetSubject ? `/formulas/sheet?subject_id=${sheetSubject}` : null);
  const { data: flash } = useApi<{ cards: any[] }>(flashSubject ? `/formulas/flashcards?subject_id=${flashSubject}&limit=20` : null);

  const subjects = subjectsData?.subjects ?? [];

  async function toggleBookmark(id: number) {
    setBusy("bm");
    try {
      await api.post(`/formulas/${id}/bookmark`);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function saveFormula(payload: any, id?: number) {
    setBusy("save");
    setError(null);
    try {
      if (id) await api.patch(`/formulas/${id}`, payload);
      else await api.post("/formulas", payload);
      setCreateOpen(false);
      setEditing(null);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Formula bank"
        title="Formulas"
        description="Verified formulas only enter the bank. AI-extracted formulas start as proposed and require manual validation."
        actions={
          <button className="btn-primary btn-sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" /> New formula
          </button>
        }
      />

      {error || listError ? <div className="mb-4"><ErrorNotice message={error || listError || ""} onRetry={refresh} /></div> : null}

      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[180px] flex-1">
            <label className="label">Search</label>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="name, latex, concept…" />
          </div>
          <div className="w-44">
            <label className="label">Subject</label>
            <select className="input" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
              <option value="">All</option>
              {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
            </select>
          </div>
          <div className="w-36">
            <label className="label">Status</label>
            <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Any</option>
              <option value="verified">Verified</option>
              <option value="proposed">Proposed</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
          <div className="w-32">
            <label className="label">Bookmarked</label>
            <select className="input" value={bookmarked} onChange={(e) => setBookmarked(e.target.value)}>
              <option value="">Any</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>
      </Card>

      {loading ? <Loading /> : null}

      {data?.items?.length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.items.map((f) => (
            <Card key={f.id} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-bold text-ink">{f.name}</div>
                  <div className="text-[10px] text-muted">{f.subject ?? ""}{f.topic ? ` / ${f.topic}` : ""}</div>
                </div>
                <div className="flex gap-1">
                  <button className="btn-ghost h-7 w-7 p-0" onClick={() => toggleBookmark(f.id)} disabled={busy === "bm"}>
                    <Bookmark className={`h-3.5 w-3.5 ${f.is_bookmarked ? "fill-brand text-brand" : ""}`} />
                  </button>
                  <button className="btn-ghost btn-sm" onClick={() => setEditing(f)}>Edit</button>
                </div>
              </div>
              <div className="mt-2 overflow-x-auto rounded-lg border border-line bg-surface-2/40 p-2">
                <Latex latex={f.latex} display />
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge tone={f.verification_status === "verified" ? "accent" : f.verification_status === "rejected" ? "danger" : "warn"}>{f.verification_status}</Badge>
                {f.units ? <Badge tone="neutral">{f.units}</Badge> : null}
              </div>
              {f.applicability ? <p className="mt-2 text-[11px] text-muted">{f.applicability}</p> : null}
              {f.common_mistakes ? <p className="mt-1 text-[10px] text-danger">Mistakes: {f.common_mistakes}</p> : null}
            </Card>
          ))}
        </div>
      ) : !loading ? (
        <EmptyState title="No formulas yet" description="Create one manually or extract proposed formulas from a solution in the library." />
      ) : null}

      <div className="mt-8 grid gap-5 xl:grid-cols-2">
        <Card>
          <SectionTitle title="Subject revision sheet" />
          <select className="input mb-3" value={sheetSubject} onChange={(e) => setSheetSubject(e.target.value)}>
            <option value="">Choose subject</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
          </select>
          {sheet?.groups?.length ? (
            <div className="space-y-3 max-h-[420px] overflow-y-auto">
              {sheet.groups.map((g: any) => (
                <div key={g.topic}>
                  <div className="text-xs font-bold text-ink">{g.topic}</div>
                  <div className="mt-1 space-y-1">
                    {g.formulas.map((f: any) => (
                      <div key={f.id} className="rounded-lg border border-line bg-surface-2/40 p-2">
                        <div className="text-[11px] font-semibold text-ink">{f.name}</div>
                        <Latex latex={f.latex} />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : sheetSubject ? <p className="text-xs text-muted">No verified formulas for this subject.</p> : null}
        </Card>

        <Card>
          <SectionTitle title="Flashcards" />
          <select className="input mb-3" value={flashSubject} onChange={(e) => setFlashSubject(e.target.value)}>
            <option value="">All subjects</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
          </select>
          {flash?.cards?.length ? (
            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {flash.cards.map((c: any) => (
                <div key={c.id} className="rounded-xl border border-line bg-surface-2/40 p-3">
                  <div className="text-[11px] font-semibold text-ink">{c.name}</div>
                  <Latex latex={c.latex} />
                  {c.common_mistakes ? <p className="mt-1 text-[10px] text-danger">{c.common_mistakes}</p> : null}
                </div>
              ))}
            </div>
          ) : flashSubject ? <p className="text-xs text-muted">No flashcards.</p> : null}
        </Card>
      </div>

      <FormulaModal
        open={createOpen || !!editing}
        onClose={() => { setCreateOpen(false); setEditing(null); }}
        initial={editing}
        subjects={subjects}
        onSave={saveFormula}
        busy={busy === "save"}
      />
    </>
  );
}

function FormulaModal({ open, onClose, initial, subjects, onSave, busy }: any) {
  const [name, setName] = useState(initial?.name ?? "");
  const [latex, setLatex] = useState(initial?.latex ?? "");
  const [subjectId, setSubjectId] = useState(initial?.subject_id ? String(initial.subject_id) : "");
  const [units, setUnits] = useState(initial?.units ?? "");
  const [applicability, setApplicability] = useState(initial?.applicability ?? "");
  const [derivation, setDerivation] = useState(initial?.derivation ?? "");
  const [commonMistakes, setCommonMistakes] = useState(initial?.common_mistakes ?? "");
  const [related, setRelated] = useState(initial?.related_concepts ?? "");
  const [status, setStatus] = useState(initial?.verification_status ?? "proposed");

  useEffect(() => {
    setName(initial?.name ?? "");
    setLatex(initial?.latex ?? "");
    setSubjectId(initial?.subject_id ? String(initial.subject_id) : "");
    setUnits(initial?.units ?? "");
    setApplicability(initial?.applicability ?? "");
    setDerivation(initial?.derivation ?? "");
    setCommonMistakes(initial?.common_mistakes ?? "");
    setRelated(initial?.related_concepts ?? "");
    setStatus(initial?.verification_status ?? "proposed");
  }, [initial]);

  if (!open) return null;

  function submit() {
    const payload: any = {
      name, latex, units, applicability, derivation, common_mistakes: commonMistakes,
      related_concepts: related, verification_status: status,
      subject_id: subjectId ? Number(subjectId) : null,
    };
    onSave(payload, initial?.id);
  }

  return (
    <Modal open={open} onClose={onClose} title={initial ? "Edit formula" : "New formula"} wide>
      <div className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label">Name</span>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="block">
            <span className="label">Subject</span>
            <select className="input" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
              <option value="">Unmapped</option>
              {subjects.map((s: any) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
            </select>
          </label>
        </div>
        <label className="block">
          <span className="label">LaTeX</span>
          <textarea className="input mono" rows={3} value={latex} onChange={(e) => setLatex(e.target.value)} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label">Units</span>
            <input className="input" value={units} onChange={(e) => setUnits(e.target.value)} />
          </label>
          <label className="block">
            <span className="label">Verification status</span>
            <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="proposed">Proposed</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
        </div>
        <label className="block">
          <span className="label">Applicability</span>
          <textarea className="input" rows={2} value={applicability} onChange={(e) => setApplicability(e.target.value)} />
        </label>
        <label className="block">
          <span className="label">Derivation</span>
          <textarea className="input" rows={2} value={derivation} onChange={(e) => setDerivation(e.target.value)} />
        </label>
        <label className="block">
          <span className="label">Common mistakes</span>
          <textarea className="input" rows={2} value={commonMistakes} onChange={(e) => setCommonMistakes(e.target.value)} />
        </label>
        <label className="block">
          <span className="label">Related concepts</span>
          <input className="input" value={related} onChange={(e) => setRelated(e.target.value)} />
        </label>
        {latex ? (
          <div className="rounded-xl border border-line bg-surface-2/40 p-3">
            <Latex latex={latex} display />
          </div>
        ) : null}
        <div className="flex justify-end gap-2 pt-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={submit} disabled={busy || !name || !latex}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
    </Modal>
  );
}
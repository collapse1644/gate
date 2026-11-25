"use client";

import { Suspense, useMemo, useState } from "react";

import { AccuracyChart, WeightageChart, YearTrendChart } from "@/components/charts";
import { Card, EmptyState, ErrorNotice, Loading, PageHeader, SectionTitle } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { bandTone } from "@/lib/format";
import type { AnalyticsReport } from "@/lib/types";

export default function AnalyticsPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <AnalyticsInner />
    </Suspense>
  );
}

function AnalyticsInner() {
  const [fromYear, setFromYear] = useState("");
  const [toYear, setToYear] = useState("");
  const [session, setSession] = useState("");

  const path = useMemo(() => `/analytics${api.query({ from_year: fromYear, to_year: toYear, session })}`, [fromYear, toYear, session]);
  const { data, loading, error, refresh } = useApi<AnalyticsReport>(path);

  return (
    <>
      <PageHeader
        eyebrow="Data-driven"
        title="Analytics"
        description="Weightage and trends are computed only from approved questions in papers you uploaded. No fabricated statistics."
      />

      {error ? <div className="mb-4"><ErrorNotice message={error} onRetry={refresh} /></div> : null}

      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-28">
            <label className="label">From year</label>
            <input className="input" type="number" value={fromYear} onChange={(e) => setFromYear(e.target.value)} placeholder="Any" />
          </div>
          <div className="w-28">
            <label className="label">To year</label>
            <input className="input" type="number" value={toYear} onChange={(e) => setToYear(e.target.value)} placeholder="Any" />
          </div>
          <div className="w-32">
            <label className="label">Session</label>
            <select className="input" value={session} onChange={(e) => setSession(e.target.value)}>
              <option value="">All</option>
              <option value="Morning">Morning</option>
              <option value="Afternoon">Afternoon</option>
            </select>
          </div>
        </div>
        {data ? (
          <p className="mt-3 text-[11px] text-muted">
            {data.papers_analyzed} papers analyzed · {data.questions_analyzed} questions · {data.questions_missing_marks} missing marks.
            Attribution: {data.attribution_policy}
          </p>
        ) : null}
      </Card>

      {loading ? <Loading /> : null}

      {data && data.papers_analyzed === 0 ? (
        <EmptyState
          title="No uploaded papers yet"
          description="Upload a ZIP with GATE papers and answer keys. Analytics appear only after approved questions exist."
          action={<a href="/data" className="btn-primary">Upload PYQs</a>}
        />
      ) : null}

      {data && data.papers_analyzed > 0 ? (
        <>
          <div className="grid gap-5 xl:grid-cols-2">
            <Card>
              <SectionTitle title="Subject weightage" subtitle="Average marks per paper" />
              <WeightageChart report={data} />
            </Card>
            <Card>
              <SectionTitle title="Year trend" subtitle="Questions and average marks per paper" />
              <YearTrendChart report={data} />
            </Card>
          </div>

          <Card className="mt-5">
            <SectionTitle title="Subject priority" />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-2 text-muted">
                  <tr>
                    <th className="px-3 py-2">Subject</th>
                    <th className="px-3 py-2">Avg marks</th>
                    <th className="px-3 py-2">Avg %</th>
                    <th className="px-3 py-2">Papers</th>
                    <th className="px-3 py-2">Trend</th>
                    <th className="px-3 py-2">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {data.subjects.map((s) => (
                    <tr key={s.subject_id} className="border-t border-line">
                      <td className="px-3 py-2 font-semibold text-ink">{s.code} — {s.subject}</td>
                      <td className="px-3 py-2">{s.average_marks.toFixed(2)}</td>
                      <td className="px-3 py-2">{s.average_percentage.toFixed(1)}%</td>
                      <td className="px-3 py-2">{s.papers_present}</td>
                      <td className="px-3 py-2">{s.trend.direction} ({s.trend.change.toFixed(2)})</td>
                      <td className="px-3 py-2">
                        <span className={`badge ${bandTone(s.priority_band) === "brand" ? "bg-brand-soft text-brand" : bandTone(s.priority_band) === "warn" ? "bg-warn-soft text-warn" : "bg-accent-soft text-accent"}`}>{s.priority_band}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="mt-5">
            <SectionTitle title="Topic weightage" />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-2 text-muted">
                  <tr>
                    <th className="px-3 py-2">Topic</th>
                    <th className="px-3 py-2">Subject</th>
                    <th className="px-3 py-2">Avg marks</th>
                    <th className="px-3 py-2">Avg %</th>
                    <th className="px-3 py-2">Papers</th>
                    <th className="px-3 py-2">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {data.topics.slice(0, 40).map((t, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="px-3 py-2 font-semibold text-ink">{t.topic}</td>
                      <td className="px-3 py-2 text-muted">{t.subject}</td>
                      <td className="px-3 py-2">{t.average_marks.toFixed(2)}</td>
                      <td className="px-3 py-2">{t.average_percentage.toFixed(1)}%</td>
                      <td className="px-3 py-2">{t.papers_present}</td>
                      <td className="px-3 py-2">{t.priority_band ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-[10px] text-muted">{data.priority_formula}</p>
          </Card>

          {data.yearly?.length ? (
            <Card className="mt-5">
              <SectionTitle title="Yearly summary" />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-2 text-muted">
                    <tr>
                      <th className="px-3 py-2">Year</th>
                      <th className="px-3 py-2">Papers</th>
                      <th className="px-3 py-2">Questions</th>
                      <th className="px-3 py-2">Avg marks/paper</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.yearly.map((y) => (
                      <tr key={y.year} className="border-t border-line">
                        <td className="px-3 py-2 font-semibold">{y.year}</td>
                        <td className="px-3 py-2">{y.papers}</td>
                        <td className="px-3 py-2">{y.questions}</td>
                        <td className="px-3 py-2">{y.average_marks_per_paper.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : null}
        </>
      ) : null}
    </>
  );
}
"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { AnalyticsReport } from "@/lib/types";

const COLORS = ["#6366f1", "#8b5cf6", "#14b8a6", "#f59e0b", "#ef4444", "#0ea5e9", "#ec4899", "#84cc16"];

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: 12,
  color: "var(--ink)",
  fontSize: 12,
  boxShadow: "0 10px 30px rgba(16,24,40,0.12)",
};

export function WeightageChart({ report }: { report: AnalyticsReport }) {
  const data = report.subjects.slice(0, 10).map((subject) => ({
    name: subject.code,
    full: subject.subject,
    marks: subject.average_marks,
    percent: subject.average_percentage,
  }));

  if (!data.length) {
    return <div className="flex h-64 items-center justify-center text-xs text-muted">No uploaded papers yet.</div>;
  }

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value: any, name: any) => [
              name === "marks" ? `${Number(value).toFixed(2)} avg marks` : `${Number(value).toFixed(1)}%`,
              name === "marks" ? "Average marks" : "Share of paper",
            ]}
            labelFormatter={(label: any, payload: any) => {
              const first = Array.isArray(payload) && payload[0] ? (payload[0] as { payload?: { full?: string } }).payload : null;
              return first?.full ?? label;
            }}
          />
          <Bar dataKey="marks" radius={[6, 6, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function YearTrendChart({ report }: { report: AnalyticsReport }) {
  const data = report.yearly.map((row) => ({
    year: String(row.year),
    questions: row.questions,
    marks: row.average_marks_per_paper,
  }));

  if (!data.length) {
    return <div className="flex h-64 items-center justify-center text-xs text-muted">No year trend yet.</div>;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11, color: "var(--muted)" }} />
          <Line type="monotone" dataKey="questions" name="Questions" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="marks" name="Avg marks / paper" stroke="#14b8a6" strokeWidth={2.5} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AccuracyChart({
  data,
}: {
  data: Array<{ name: string; accuracy: number | null; attempted: number }>;
}) {
  const rows = data
    .filter((row) => row.accuracy !== null)
    .map((row) => ({ ...row, percent: Math.round((row.accuracy ?? 0) * 100) }));

  if (!rows.length) {
    return <div className="flex h-56 items-center justify-center text-xs text-muted">Attempt some questions to see accuracy.</div>;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 18, left: 8, bottom: 0 }}>
          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" width={110} tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} formatter={(value: any) => [`${value}%`, "Accuracy"]} />
          <Bar dataKey="percent" radius={[0, 6, 6, 0]}>
            {rows.map((row, index) => (
              <Cell key={index} fill={row.percent >= 70 ? "#14b8a6" : row.percent >= 45 ? "#f59e0b" : "#ef4444"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

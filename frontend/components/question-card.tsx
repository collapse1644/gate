"use client";

import { Bookmark, ChevronRight, Clock3, GitBranch } from "lucide-react";
import Link from "next/link";

import { MathText } from "@/components/math-text";
import { Badge, StatusBadge } from "@/components/ui";
import { truncate } from "@/lib/format";
import type { QuestionSummary } from "@/lib/types";

export function QuestionCard({
  question,
  showStatus = true,
  compact = false,
}: {
  question: QuestionSummary;
  showStatus?: boolean;
  compact?: boolean;
}) {
  return (
    <Link
      href={`/library/${question.id}`}
      className="card card-hover group block p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <Badge tone="brand">
          {question.year} · Q{question.question_no}
        </Badge>
        <Badge tone="neutral">{question.question_type}</Badge>
        {question.marks ? <Badge tone="neutral">{question.marks} mark{question.marks === 1 ? "" : "s"}</Badge> : null}
        {question.session ? <span className="text-muted">{question.session}</span> : null}
        <span className="ml-auto flex items-center gap-2">
          {question.is_bookmarked ? <Bookmark className="h-3.5 w-3.5 fill-brand text-brand" /> : null}
          {showStatus ? <StatusBadge status={question.verification_status} /> : null}
          <ChevronRight className="h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
        </span>
      </div>

      <div className="mt-2.5 text-[13px] leading-relaxed text-ink">
        <MathText text={truncate(question.question_text, compact ? 180 : 320)} inline />
      </div>

      {!compact && question.options.length > 0 ? (
        <div className="mt-3 grid gap-1.5 sm:grid-cols-2">
          {question.options.slice(0, 4).map((option) => (
            <div
              key={option.key}
              className="flex items-start gap-2 rounded-lg border border-line/70 bg-surface-2/50 px-2.5 py-1.5 text-[11px] text-muted"
            >
              <span className="font-bold text-brand">{option.key}</span>
              <MathText text={truncate(option.text, 90)} inline />
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted">
        {question.subject ? (
          <span className="inline-flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            {question.subject}
            {question.topic ? ` / ${question.topic}` : ""}
          </span>
        ) : (
          <Badge tone="warn">Unclassified</Badge>
        )}
        {question.source_page ? (
          <span className="inline-flex items-center gap-1">
            <Clock3 className="h-3 w-3" /> source p.{question.source_page}
          </span>
        ) : null}
        {question.import_status !== "approved" ? (
          <Badge tone="warn">{question.import_status}</Badge>
        ) : null}
        {question.needs_review ? <Badge tone="warn">needs review</Badge> : null}
      </div>
    </Link>
  );
}

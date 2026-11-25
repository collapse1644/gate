"use client";

import { Filter, RotateCcw, Search, SlidersHorizontal, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { QuestionCard } from "@/components/question-card";
import {
  Badge,
  Card,
  EmptyState,
  ErrorNotice,
  LinkButton,
  Loading,
  PageHeader,
  SectionTitle,
} from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi, useDebounced } from "@/lib/hooks";
import type { QuestionList, Subject } from "@/lib/types";

function LibraryInner() {
  const searchParams = useSearchParams();
  const initialSubject = searchParams.get("subject_id") ?? "";
  const initialTopic = searchParams.get("topic_id") ?? "";
  const initialReview = searchParams.get("review") ?? "";

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const debouncedQuery = useDebounced(query);
  const [subjectId, setSubjectId] = useState(initialSubject);
  const [topicId, setTopicId] = useState(initialTopic);
  const [year, setYear] = useState("");
  const [reviewStatus, setReviewStatus] = useState(initialReview);
  const [includeStaged, setIncludeStaged] = useState(false);
  const [sort, setSort] = useState("recent");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [debouncedQuery, subjectId, topicId, year, reviewStatus, includeStaged, sort]);

  const { data: subjectsData } = useApi<{ subjects: Subject[] }>("/subjects");

  const path = useMemo(() => {
    return `/questions${api.query({
      q: debouncedQuery,
      subject_id: subjectId,
      topic_id: topicId,
      year,
      review_status: reviewStatus,
      include_staged: includeStaged || undefined,
      sort,
      page,
      page_size: 20,
    })}`;
  }, [debouncedQuery, subjectId, topicId, year, reviewStatus, includeStaged, sort, page]);

  const { data, loading, error, refresh } = useApi<QuestionList>(path);

  function reset() {
    setQuery("");
    setSubjectId("");
    setTopicId("");
    setYear("");
    setReviewStatus("");
    setIncludeStaged(false);
    setSort("recent");
    setPage(1);
  }

  const activeFilters = [debouncedQuery, subjectId, topicId, year, reviewStatus, includeStaged].filter(Boolean).length;

  return (
    <>
      <PageHeader
        eyebrow="Previous year questions"
        title="PYQ Library"
        description="Every question here came from a PDF you uploaded. Answers stay hidden in practice sessions until you submit."
        actions={
          <>
            <LinkButton href="/review" variant="secondary">
              Review queue
            </LinkButton>
            <LinkButton href="/data" variant="primary">
              <UploadCloud className="h-4 w-4" /> Upload ZIP
            </LinkButton>
          </>
        }
      />

      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <label className="label" htmlFor="library-search">
              Search question text
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <input
                id="library-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="e.g. deadlock, recurrence, TCP…"
                className="input pl-8"
              />
            </div>
          </div>
          <div className="w-44">
            <label className="label" htmlFor="library-subject">
              Subject
            </label>
            <select
              id="library-subject"
              value={subjectId}
              onChange={(event) => {
                setSubjectId(event.target.value);
                setTopicId("");
              }}
              className="input"
            >
              <option value="">All subjects</option>
              {subjectsData?.subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.code} — {subject.name}
                </option>
              ))}
            </select>
          </div>
          <div className="w-28">
            <label className="label" htmlFor="library-year">
              Year
            </label>
            <input
              id="library-year"
              type="number"
              min={2010}
              max={2030}
              value={year}
              onChange={(event) => setYear(event.target.value)}
              placeholder="Any"
              className="input"
            />
          </div>
          <div className="w-44">
            <label className="label" htmlFor="library-review">
              Classification
            </label>
            <select
              id="library-review"
              value={reviewStatus}
              onChange={(event) => setReviewStatus(event.target.value)}
              className="input"
            >
              <option value="">Any status</option>
              <option value="auto_accepted">Auto accepted</option>
              <option value="manually_accepted">Manually accepted</option>
              <option value="pending">Pending review</option>
              <option value="out_of_syllabus">Out of syllabus</option>
            </select>
          </div>
          <div className="w-36">
            <label className="label" htmlFor="library-sort">
              Sort
            </label>
            <select id="library-sort" value={sort} onChange={(event) => setSort(event.target.value)} className="input">
              <option value="recent">Newest first</option>
              <option value="question_no">Paper order</option>
              <option value="year_asc">Oldest first</option>
              <option value="marks">Highest marks</option>
            </select>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted">
            <label className="inline-flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={includeStaged}
                onChange={(event) => setIncludeStaged(event.target.checked)}
                className="h-3.5 w-3.5 accent-[var(--brand)]"
              />
              Include staged / unreviewed
            </label>
            {activeFilters > 0 ? (
              <button type="button" onClick={reset} className="inline-flex items-center gap-1 font-semibold text-brand hover:underline">
                <RotateCcw className="h-3 w-3" /> Clear {activeFilters} filter{activeFilters === 1 ? "" : "s"}
              </button>
            ) : null}
            {initialTopic ? <Badge tone="brand">Topic filter active</Badge> : null}
          </div>
          <div className="inline-flex items-center gap-1.5 text-[11px] text-muted">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            {data ? `${data.total} questions` : "…"}
          </div>
        </div>
      </Card>

      {error ? <ErrorNotice message={error} onRetry={refresh} /> : null}

      {loading ? (
        <Loading />
      ) : data && data.items.length ? (
        <>
          <div className="grid gap-3">
            {data.items.map((question) => (
              <QuestionCard key={question.id} question={question} />
            ))}
          </div>
          {data.pages > 1 ? (
            <div className="mt-5 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={data.page <= 1}
                className="btn-secondary btn-sm"
              >
                Previous
              </button>
              <span className="text-xs text-muted">
                Page {data.page} of {data.pages}
              </span>
              <button
                type="button"
                onClick={() => setPage((value) => Math.min(data.pages, value + 1))}
                disabled={data.page >= data.pages}
                className="btn-secondary btn-sm"
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      ) : (
        <EmptyState
          icon={<Filter className="h-5 w-5" />}
          title={activeFilters ? "No questions match these filters" : "Your PYQ library is empty"}
          description={
            activeFilters
              ? "Try clearing filters, or include staged questions to see imported material awaiting review."
              : "Upload a ZIP with official GATE question papers and answer keys. Staged questions appear here after ingestion and must be approved before practice."
          }
          action={
            activeFilters ? (
              <button type="button" onClick={reset} className="btn-secondary">
                Clear filters
              </button>
            ) : (
              <LinkButton href="/data" variant="primary">
                <UploadCloud className="h-4 w-4" /> Upload PYQ ZIP
              </LinkButton>
            )
          }
        />
      )}

      <Card className="mt-5 border-brand/20 bg-brand-soft/30">
        <SectionTitle title="How answers are handled" />
        <p className="text-[11px] leading-relaxed text-muted">
          Official answers are stored from the answer-key PDF and compared exactly (with numeric tolerance for
          NAT). They are never overwritten by AI output. The library shows the answer for review; practice
          sessions hide it until submission.
        </p>
        <Link href="/review" className="mt-2 inline-flex text-[11px] font-semibold text-brand hover:underline">
          Open the review queue to approve or fix classifications →
        </Link>
      </Card>
    </>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <LibraryInner />
    </Suspense>
  );
}

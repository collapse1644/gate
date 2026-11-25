export type VerificationStatus =
  | "UNVERIFIED"
  | "PARTIALLY VERIFIED"
  | "VERIFIED"
  | "NEEDS REVIEW"
  | "DISPUTED";

export interface Stats {
  questions_available: number;
  questions_attempted: number;
  questions_remaining: number;
  graded_attempts: number;
  correct_attempts: number;
  accuracy: number | null;
  time_spent_seconds: number;
  due_revisions: number;
  completion: number;
}

export interface ProgressRef {
  id: number;
  name: string;
  code?: string;
  level: string;
  questions_available: number;
  attempted: number;
  distinct_questions: number;
  correct: number;
  incorrect: number;
  accuracy: number | null;
  time_spent_seconds: number;
  last_attempted_at: string | null;
  mastery: string;
  manual_status: string | null;
}

export interface SubjectProgress extends ProgressRef {
  code: string;
}

export interface TopicProgress extends ProgressRef {
  subject_id: number;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  description: string;
  color: string;
  section_code: string;
  questions_available: number;
  progress: SubjectProgress | null;
}

export interface Topic {
  id: number;
  name: string;
  section_id: number | null;
  description: string;
  questions_available: number;
  progress: TopicProgress | null;
}

export interface Concept {
  id: number;
  name: string;
  description: string;
}

export interface Subtopic {
  id: number;
  name: string;
  description: string;
  questions_available: number;
  progress: ProgressRef | null;
  concepts: Concept[];
}

export interface SubjectDetail {
  subject: Pick<Subject, "id" | "code" | "name" | "description" | "color">;
  topics: Topic[];
}

export interface TopicDetail {
  topic: { id: number; name: string; subject_id: number; description: string };
  subtopics: Subtopic[];
}

export interface SyllabusSection {
  id: number;
  code: string;
  title: string;
  category: string;
  official_text: string;
}

export interface SyllabusResponse {
  version: {
    id: number;
    exam: string;
    year: number;
    paper_code: string;
    title: string;
    source_url: string;
    source_sha256: string;
    retrieved_at: string | null;
    is_active: boolean;
  };
  sections: SyllabusSection[];
  subjects: TaxonomySubject[];
  note: string;
}

export interface TaxonomySubject {
  id: number;
  code: string;
  name: string;
  section_code: string;
  topics: Array<{
    id: number;
    name: string;
    subtopics: Array<{ id: number; name: string; concepts: Array<{ id: number; name: string }> }>;
  }>;
}

export interface QuestionAsset {
  id: number;
  url: string;
  kind: string;
  page: number;
  width: number | null;
  height: number | null;
  sha256: string;
  interpretation: string | null;
  interpretation_status: string;
  interpretation_model: string | null;
}

export interface QuestionSummary {
  id: number;
  public_id: string;
  year: number;
  session: string | null;
  paper_label: string;
  question_no: number;
  question_type: "MCQ" | "MSQ" | "NAT" | string;
  marks: number | null;
  negative_marks: number | null;
  question_text: string;
  raw_text: string | null;
  options: Array<{ key: string; text: string }>;
  official_answer: string | null;
  subject_id: number | null;
  subject: string | null;
  topic_id: number | null;
  topic: string | null;
  subtopic_id: number | null;
  subtopic: string | null;
  concepts: string[];
  difficulty: number | null;
  extraction_confidence: number;
  classification_confidence: number;
  classification_method: string;
  review_status: string;
  verification_status: VerificationStatus | string;
  import_status: string;
  needs_review: boolean;
  is_bookmarked: boolean;
  source_pdf: string;
  source_page: number | null;
  assets: QuestionAsset[];
  solution_available: boolean;
  created_at: string | null;
}

export interface VerificationCheck {
  id: number;
  check_type: string;
  tool: string;
  description: string;
  passed: boolean | null;
  expected: string | null;
  actual: string | null;
  independent: boolean;
  notes: string;
}

export interface Solution {
  id: number;
  version: number;
  provider: string;
  model: string;
  learning_mode: string;
  content: string;
  final_answer: string | null;
  verification_status: VerificationStatus;
  is_current: boolean;
  checks?: VerificationCheck[];
  created_at: string | null;
}

export interface Attempt {
  id: number;
  selected_answer: string | null;
  is_correct: boolean | null;
  mode: string;
  time_spent_seconds: number;
  working_text: string;
  started_at: string | null;
  completed_at: string | null;
  preview?: boolean;
  explanation: string | null;
}

export interface QuestionDetail extends QuestionSummary {
  extraction_notes: string[];
  review_notes: string;
  reviewed_by: string | null;
  source_bbox: number[] | null;
  secondary_topics: Array<{ id: number; name: string }>;
  solutions: Solution[];
  current_solution: Solution | null;
  attempts?: Attempt[];
}

export interface QuestionList {
  items: QuestionSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DashboardResponse {
  stats: Stats;
  subjects: SubjectProgress[];
  weak_topics: TopicProgress[];
  strong_topics: TopicProgress[];
  recent_activity: Array<{
    attempt_id: number;
    question_id: number;
    year: number;
    question_no: number;
    is_correct: boolean | null;
    mode: string;
    completed_at: string | null;
  }>;
  revision_due: RevisionDue[];
  priority_subjects: Array<{
    subject_id: number;
    subject: string;
    average_marks: number;
    priority_score: number;
    priority_band: string;
  }>;
  recommended_topics: Array<{
    topic_id: number;
    topic: string;
    questions_available: number;
    accuracy: number | null;
    reason: string;
  }>;
  empty_state: boolean;
}

export interface RevisionDue {
  question_id: number;
  year: number;
  question_no: number;
  session: string | null;
  question_type: string;
  question_text: string;
  due_at: string;
  interval_days: number;
  lapses: number;
}

export interface RevisionOverview {
  stats: Stats;
  due: RevisionDue[];
  upcoming: Array<RevisionDue & { repetitions: number }>;
  tracked: number;
  subjects: SubjectProgress[];
}

export interface AnalyticsSubject {
  subject_id: number;
  subject: string;
  code: string;
  color: string;
  average_marks: number;
  average_percentage: number;
  average_question_count: number;
  min_marks: number;
  max_marks: number;
  papers_present: number;
  frequency: number;
  priority_score: number;
  priority_band: string;
  trend: { change: number; direction: string; recent_average: number; earlier_average: number };
  year_wise: Array<{ year: number; average_marks: number; papers: number }>;
}

export interface AnalyticsReport {
  filters: { from_year: number | null; to_year: number | null; session: string | null };
  papers_analyzed: number;
  papers: Array<{
    id: number;
    year: number;
    session: string | null;
    label: string;
    question_count: number;
    total_marks: number | null;
  }>;
  questions_analyzed: number;
  questions_missing_marks: number;
  attribution_policy: string;
  attribution_note: string;
  subjects: AnalyticsSubject[];
  topics: Array<{
    topic_id: number;
    topic: string;
    subject: string;
    average_marks: number;
    average_percentage: number;
    papers_present: number;
    priority_band?: string;
  }>;
  yearly: Array<{
    year: number;
    papers: number;
    questions: number;
    average_marks_per_paper: number;
    [key: string]: number | string;
  }>;
  priority_formula: string;
}

export interface PracticeSession {
  id: number;
  mode: string;
  paper: { id: number; year: number; session: string | null; label: string } | null;
  current_index: number;
  answered_count: number;
  correct_count: number;
  total_questions: number;
  questions: QuestionSummary[];
  started_at: string | null;
  completed_at: string | null;
}

export interface PracticeAnswerResult {
  attempt_id: number;
  is_correct: boolean | null;
  official_answer: string | null;
  question_type: string;
  explanation: string | null;
  session: {
    id: number;
    answered_count: number;
    correct_count: number;
    current_index: number;
    completed: boolean;
  };
}

export interface Formula {
  id: number;
  name: string;
  latex: string;
  subject_id: number | null;
  topic_id: number | null;
  subtopic_id: number | null;
  variable_definitions: Array<{ symbol?: string; name?: string; meaning?: string }>;
  units: string;
  applicability: string;
  derivation: string;
  common_mistakes: string;
  related_concepts: string;
  pyq_references: number[];
  verification_status: "proposed" | "verified" | "rejected" | string;
  is_bookmarked: boolean;
  reviewed_by: string | null;
  created_at: string | null;
  subject?: string | null;
  topic?: string | null;
}

export interface AIStatus {
  mode: "auto" | "gemini" | "local" | "local_only";
  preferred_provider: "gemini" | "local";
  allow_auto_fallback: boolean;
  cloud_consent: boolean;
  gemini: { configured: boolean; ready: boolean; model: string; note: string };
  local: {
    ready: boolean;
    endpoint: string;
    model: string;
    vision_model: string;
    health: Record<string, unknown>;
    server: Record<string, unknown>;
  };
  privacy: { cloud_optional: boolean; local_only_mode: boolean; note: string };
}

export interface TutorSessionSummary {
  id: number;
  title: string;
  mode: string;
  question_id: number | null;
  message_count: number;
  updated_at: string | null;
}

export interface TutorMessage {
  id: number;
  role: "user" | "assistant" | string;
  content: string;
  provider?: string | null;
  model?: string | null;
  verification_status?: string | null;
  fallback_from?: string | null;
  latency_ms?: number | null;
  created_at?: string | null;
}

export interface TutorSession {
  id: number;
  title: string;
  mode: string;
  question_id: number | null;
  question: QuestionDetail | null;
  subject_id: number | null;
  topic_id: number | null;
  created_at: string | null;
  messages: TutorMessage[];
}

export interface AppSettings {
  [key: string]: string | number | boolean | null | undefined;
  ai_mode: string;
  preferred_provider: string;
  allow_auto_fallback: boolean;
  cloud_consent: boolean;
  gemini_model: string;
  gemini_api_key?: string;
  gemini_api_key_set: boolean;
  local_base_url: string;
  local_model_path: string;
  local_mmproj_path: string;
  local_model_label: string;
  local_vision_model_label: string;
  local_context: number;
  local_gpu_layers: number;
  local_auto_start: boolean;
  classification_review_threshold: number;
  classification_accept_threshold: number;
  attribution_policy: string;
  backup_retention: number;
}

export interface ReviewQueue {
  items: QuestionSummary[];
  total: number;
  counts: {
    staged: number;
    needs_review: number;
    missing_answers: number;
    low_extraction: number;
    low_classification: number;
  };
  page: number;
  page_size: number;
  pages: number;
}

export interface IngestionJob {
  id: number;
  filename: string;
  status: string;
  stage: string;
  stats: Record<string, number>;
  error: string | null;
  created_at: string | null;
  started_at?: string | null;
  completed_at: string | null;
}

export interface IngestionJobDetail {
  job: IngestionJob;
  files: Array<{
    id: number;
    relative_path: string;
    kind: string;
    status: string;
    year: number | null;
    session: string | null;
    page_count: number | null;
    questions_found: number;
    answers_found: number;
    duplicates: number;
    warnings: string[];
    error: string | null;
    paper_id: number | null;
  }>;
}

export interface DataOverview {
  database: { path: string; size_bytes: number };
  storage: {
    originals_bytes: number;
    assets_bytes: number;
    uploads_bytes: number;
    backups_bytes: number;
    total_bytes: number;
  };
  backups: Array<{
    file: string;
    size_bytes: number;
    modified_at: string;
    manifest: Record<string, unknown>;
  }>;
  ingestion_history: IngestionJob[];
  notes: string[];
}

export interface IntegrityReport {
  ok: boolean;
  sqlite_integrity: string;
  issues: Array<{ type: string; detail: unknown }>;
  checked_at: string;
}

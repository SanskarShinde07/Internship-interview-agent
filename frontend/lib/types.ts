// Shared DTOs mirroring the backend API contract (docs/BLUEPRINT.md §6).

export type InterviewState =
  | "CREATED"
  | "INTRODUCTION"
  | "PYTHON"
  | "MACHINE_LEARNING"
  | "NLP"
  | "PROJECT_DISCUSSION"
  | "SCENARIO"
  | "HR"
  | "COMPLETED"
  | "TERMINATED";

export type ReadinessLevel = "NOT_READY" | "DEVELOPING" | "READY" | "STRONG";

export interface SessionSummary {
  session_id: string;
  state: InterviewState;
}

export interface Question {
  question_id: string;
  question_text: string;
  round: string;
  difficulty: number;
}

export interface StartSessionResult {
  state: InterviewState;
  current_question: Question;
}

export interface SessionProgress {
  state: InterviewState;
  round: string;
  difficulty: number;
  progress: {
    asked: number;
    total_estimate: number;
  };
}

export interface NextStepResult {
  state: InterviewState;
  next_question: Question | null;
}

export interface LearningRoadmapItem {
  topic: string;
  action: string;
  priority: string;
}

export interface InterviewReport {
  overall_score: number;
  category_scores: Record<string, number | null>;
  strengths: string[];
  improvements: string[];
  recruiter_summary: string;
  learning_roadmap: LearningRoadmapItem[];
  readiness_level: ReadinessLevel;
}

export interface DifficultyChange {
  sequence_number: number;
  previous_difficulty: number;
  new_difficulty: number;
  reason: string;
}

export interface TimelineEntry {
  sequence_number: number;
  round: string;
  topic: string;
  difficulty: number;
  question_type: string;
}

export interface InterviewAnalytics {
  interview_duration_seconds: number | null;
  total_questions: number;
  questions_per_round: Record<string, number>;
  follow_up_questions: number;
  difficulty_progression: DifficultyChange[];
  highest_difficulty_reached: number | null;
  topic_wise_scores: Record<string, number>;
  average_technical_score: number | null;
  average_communication_score: number | null;
  average_answer_length: number | null;
  strongest_topic: string | null;
  weakest_topic: string | null;
  round_completion_times_seconds: Record<string, number>;
  interview_completion_rate: number;
  adaptive_difficulty_changes: number;
  interview_timeline: TimelineEntry[];
}

export type CoachMessageRole = "USER" | "ASSISTANT";

export interface CoachMessageItem {
  role: CoachMessageRole;
  content: string;
  referenced_question_id: string | null;
}

export interface CoachMessageResult {
  reply: string;
  conversation_id: string;
}

export interface ApiErrorBody {
  error_code: string;
  message: string;
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
}

export interface AuthResult {
  access_token: string;
  user: AuthUser;
}

export interface SessionHistoryItem {
  session_id: string;
  state: InterviewState;
  started_at: string | null;
  completed_at: string | null;
  overall_score: number | null;
  readiness_level: ReadinessLevel | null;
}

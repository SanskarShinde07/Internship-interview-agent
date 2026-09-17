// Shared DTOs mirroring the backend API contract (docs/BLUEPRINT.md §6).
// Kept minimal in Phase 0; expanded as each endpoint is implemented.

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

export interface SessionSummary {
  session_id: string;
  state: InterviewState;
}

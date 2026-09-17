import type {
  ApiErrorBody,
  AuthResult,
  CoachMessageItem,
  CoachMessageResult,
  InterviewAnalytics,
  InterviewReport,
  NextStepResult,
  Question,
  SessionHistoryItem,
  SessionProgress,
  SessionSummary,
  StartSessionResult,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  errorCode: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.errorCode = body.error_code;
  }
}

// Kept as a plain in-memory value (not read from localStorage per-request)
// so this module has no framework dependency - AuthContext is the single
// place that reads/writes localStorage and calls setAuthToken to keep this
// in sync with it.
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = await response.json();
    } catch {
      body = { error_code: "unknown_error", message: response.statusText };
    }
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function checkBackendHealth(): Promise<{ status: string }> {
  return request("/health");
}

export function createSession(input: {
  display_name?: string;
  email?: string;
}): Promise<SessionSummary> {
  return request("/sessions", { method: "POST", body: JSON.stringify(input) });
}

export function startSession(sessionId: string): Promise<StartSessionResult> {
  return request(`/sessions/${sessionId}/start`, { method: "POST" });
}

export function getSession(sessionId: string): Promise<SessionProgress> {
  return request(`/sessions/${sessionId}`);
}

export function getCurrentQuestion(sessionId: string): Promise<Question> {
  return request(`/sessions/${sessionId}/current-question`);
}

export function submitAnswer(
  sessionId: string,
  input: { question_id: string; transcript_text: string; duration_seconds?: number },
): Promise<NextStepResult> {
  return request(`/sessions/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function repeatQuestion(sessionId: string): Promise<{ question_text: string }> {
  return request(`/sessions/${sessionId}/repeat-question`, { method: "POST" });
}

export function endSession(sessionId: string, reason?: string): Promise<{ state: string }> {
  return request(`/sessions/${sessionId}/end`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

/** Permanently deletes a session and all data derived from it (docs/BLUEPRINT.md §17).
 * Irreversible - callers should confirm with the candidate before calling this. */
export function deleteSession(sessionId: string): Promise<void> {
  return request(`/sessions/${sessionId}`, { method: "DELETE" });
}

export function getReport(sessionId: string): Promise<InterviewReport> {
  return request(`/sessions/${sessionId}/report`);
}

export function getAnalytics(sessionId: string): Promise<InterviewAnalytics> {
  return request(`/sessions/${sessionId}/analytics`);
}

export function postCoachMessage(
  sessionId: string,
  message: string,
  referencedQuestionId?: string,
): Promise<CoachMessageResult> {
  return request(`/sessions/${sessionId}/coach/messages`, {
    method: "POST",
    body: JSON.stringify({ message, referenced_question_id: referencedQuestionId }),
  });
}

export function getCoachMessages(
  sessionId: string,
): Promise<{ messages: CoachMessageItem[] }> {
  return request(`/sessions/${sessionId}/coach/messages`);
}

export function registerUser(input: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<AuthResult> {
  return request("/auth/register", { method: "POST", body: JSON.stringify(input) });
}

export function loginUser(input: { email: string; password: string }): Promise<AuthResult> {
  return request("/auth/login", { method: "POST", body: JSON.stringify(input) });
}

export function getMe(): Promise<{ id: string; email: string; display_name: string | null }> {
  return request("/auth/me");
}

export function forgotPassword(email: string): Promise<{ message: string }> {
  return request("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
}

export function resetPassword(
  token: string,
  newPassword: string,
): Promise<{ message: string }> {
  return request("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function getMyInterviews(): Promise<{ sessions: SessionHistoryItem[] }> {
  return request("/auth/me/interviews");
}

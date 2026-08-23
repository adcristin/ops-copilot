// Shared types - mirror the shapes returned by the FastAPI backend
// (db/models.py). Keep these in sync manually for now; a future upgrade
// could generate these from the OpenAPI schema at /openapi.json.

export interface User {
  username: string;
  role: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface BackgroundTask {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
  result?: any;
  error?: string;
  created_at: string;
}

export type Priority = "high" | "medium" | "low";
export type TaskStatus = "open" | "in_progress" | "blocked" | "done";
export type MailboxCategory =
  | "escalation"
  | "complaint"
  | "status_check"
  | "info_request"
  | "other";
export type MailboxStatus = "open" | "drafted" | "replied" | "escalated" | "closed";
export type Sentiment = "positive" | "neutral" | "negative";
export type TaskSourceType = "qa_flag" | "mailbox_escalation" | "manual";

export interface Agent {
  id: number;
  name: string;
  email: string;
  team?: string | null;
}

export interface AgentPerformance {
  name: string;
  calls: number;
  avgScore: number;
  flagged: number;
}

export interface Violation {
  category: string;
  quote: string;
  note: string;
}

export interface QAScore {
  id: number;
  call_id: number;
  overall_score: number;
  greeting_score: number;
  compliance_score: number;
  resolution_score: number;
  tone_score: number;
  sentiment: Sentiment;
  flagged: boolean;
  violations: Violation[];
  coaching_notes: string;
}

export interface Call {
  id: number;
  agent_id: number;
  customer_ref?: string | null;
  transcript: string;
  duration_seconds?: number | null;
  call_date: string;
  qa_score?: QAScore | null;
}

export interface MailboxItem {
  id: number;
  sender: string;
  subject: string;
  body: string;
  received_at: string;
  category: MailboxCategory;
  priority: Priority;
  status: MailboxStatus;
  sla_hours: number;
  suggested_reply?: string;
  reasoning?: string;
  final_reply?: string;
  routed_to?: string;
}
}

export interface Task {
  id: number;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: Priority;
  due_date?: string | null;
  source_type: TaskSourceType;
  agent?: string;
}

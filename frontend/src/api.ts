import type { Agent, Call, MailboxItem, Task } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export const api = {
  listAgents: () => request<Agent[]>("/agents"),
  createAgent: (payload: { name: string; email: string; team?: string }) =>
    request<Agent>("/agents", { method: "POST", body: JSON.stringify(payload) }),

  listCalls: () => request<Call[]>("/calls"),
  scoreCall: (payload: { agent_id: number; customer_ref?: string; transcript: string }) =>
    request<{ call_id: number; qa_score: any }>("/calls/score", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listMailbox: () => request<MailboxItem[]>("/mailbox"),
  ingestEmail: (payload: { sender: string; subject: string; body: string }) =>
    request<MailboxItem>("/mailbox", { method: "POST", body: JSON.stringify(payload) }),

  listTasks: () => request<Task[]>("/tasks"),
  closeTask: (taskId: number) =>
    request<Task>(`/tasks/${taskId}/close`, { method: "POST" }),

  reportUrls: {
    excel: () => `${API_BASE}/reports/excel`,
    pptx: () => `${API_BASE}/reports/pptx`,
  },
};

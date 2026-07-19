import type { Agent, Call, MailboxItem, Task, User, Token, BackgroundTask } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Helper to get token from local storage
function getToken(): string | null {
  return localStorage.getItem("ops_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  });

  if (res.status === 401) {
    // Token expired or invalid - clear it and throw error to be caught by UI
    localStorage.removeItem("ops_token");
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${detail}`);
  }

  return res.json();
}

export const api = {
  // Auth
  login: (data: { username: string; password: string }) =>
    request<Token>("/auth/token", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  me: () => request<User>("/auth/me"),

  setToken: (token: string) => localStorage.setItem("ops_token", token),
  logout: () => localStorage.removeItem("ops_token"),

  // Agents
  listAgents: () => request<Agent[]>("/agents"),
  createAgent: (payload: { name: string; email: string; team?: string }) =>
    request<Agent>("/agents", { method: "POST", body: JSON.stringify(payload) }),

  // Call QA (Now Async)
  listCalls: () => request<Call[]>("/calls"),
  scoreCall: (payload: { agent_id: number; customer_ref?: string; transcript: string }) =>
    request<{ task_id: string; status: string }>("/calls/score", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Mailbox (Now Async)
  listMailbox: () => request<MailboxItem[]>("/mailbox"),
  ingestEmail: (payload: { sender: string; subject: string; body: string }) =>
    request<{ task_id: string; status: string }>("/mailbox", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  // Tasks
  listTasks: () => request<Task[]>("/tasks"),
  closeTask: (taskId: number) =>
    request<Task>(`/tasks/${taskId}/close`, { method: "POST" }),

  // Background Task Polling
  getBackgroundTask: (taskId: string) => request<BackgroundTask>(`/tasks/background/${taskId}`),

  reportUrls: {
    excel: () => `${API_BASE}/reports/excel`,
    pptx: () => `${API_BASE}/reports/pptx`,
  },
};

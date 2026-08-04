import type { Agent, Call, MailboxItem, Task, User, Token, BackgroundTask } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

let authToken: string | null = null;

export const isAuthenticated = () => authToken !== null;

// Helper to get token from memory
function getToken(): string | null {
  return authToken;
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
    authToken = null;
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
  login: (data: { username: string; password: string }) => {
    const params = new URLSearchParams();
    params.append("username", data.username); // This is now email or username
    params.append("password", data.password);

    return request<Token>("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params
    });
  },

  me: () => request<User>("/auth/me"),
  signup: (data: { username: string; email: string; password: string }) =>
    request<User>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  setToken: (token: string) => { authToken = token; },
  logout: () => { authToken = null; },

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

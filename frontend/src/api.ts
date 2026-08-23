import type { Agent, Call, MailboxItem, Task, User, Token, BackgroundTask } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// We no longer store the token in localStorage as we've moved to httpOnly cookies.
let userCache: User | null = null;

export const isAuthenticated = () => userCache !== null;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
    credentials: 'include', // Crucial for sending/receiving cookies
  });

  if (res.status === 401) {
    userCache = null;
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${detail}`);
  }

  return res.json();
}

export const api = {
  login: (data: { username: string; password: string }) => {
    const params = new URLSearchParams();
    params.append("username", data.username);
    params.append("password", data.password);

    return request<Token>("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params
    });
  },

  me: async () => {
    try {
      const user = await request<User>("/auth/me");
      userCache = user;
      return user;
    } catch (e) {
      userCache = null;
      throw e;
    }
  },

  updateProfile: (data: Partial<User>) =>
    request<User>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  changePassword: (data: { current_password: string; new_password: string }) =>
    request<{ detail: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  signup: (data: { username: string; email: string; password: string }) =>
    request<User>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  logout: async () => {
    // Note: To truly logout with httpOnly cookies, the backend needs a /auth/logout
    // endpoint that clears the cookie. For now, we clear the local cache.
    userCache = null;
  },

  listAgents: () => request<Agent[]>("/agents"),
  createAgent: (payload: { name: string; email: string; team?: string }) =>
    request<Agent>("/agents", { method: "POST", body: JSON.stringify(payload) }),

  listCalls: () => request<Call[]>("/calls"),
  uploadCall: (formData: FormData) =>
    request<{ call_id: string; status: string }>("/api/calls/upload", {
      method: "POST",
      body: formData,
    }),
  scoreCall: (payload: { agent_id: number; customer_ref?: string; transcript: string }) =>
    request<{ task_id: string; status: string }>("/calls/score", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listMailbox: () => request<MailboxItem[]>("/mailbox"),
  sendMailboxReply: (itemId: number | string, payload: { reply: string }) =>
    request<{ detail: string }>(`/mailbox/${itemId}/reply`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  ingestEmail: (payload: { sender: string; subject: string; body: string }) =>
    request<{ task_id: string; status: string }>("/mailbox", {
      method: "POST",
      body: JSON.stringify(payload)
    }),

  listTasks: () => request<Task[]>("/tasks"),
  closeTask: (taskId: number) =>
    request<Task>(`/tasks/${taskId}/close`, { method: "POST" }),

  getBackgroundTask: (taskId: string) => request<BackgroundTask>(`/tasks/background/${taskId}`),

  reportUrls: {
    excel: () => `${API_BASE}/reports/excel`,
    pptx: () => `${API_BASE}/reports/pptx`,
  },
};

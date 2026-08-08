import type { Agent, Call, MailboxItem, Task, User, Token, BackgroundTask } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const TOKEN_KEY = "auth_token";
let authToken: string | null = null;

// Init token from storage
try {
  authToken = localStorage.getItem(TOKEN_KEY);
} catch (e) {
  // Storage unavailable
}

/**
 * Decodes a JWT payload.
 * Format: header.payload.signature
 */
function decodeJwtPayload(token: string) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c =>
      '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    ).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload || !payload.exp) return true;

  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
}

function saveToken(token: string | null) {
  authToken = token;
  try {
    // NOTE: Token is readable by any script (XSS risk).
    // httpOnly cookies would be more secure.
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (e) {
    // Storage unavailable
  }
}

export const isAuthenticated = () => getToken() !== null;

function getToken(): string | null {
  if (authToken && isTokenExpired(authToken)) {
    saveToken(null);
    return null;
  }
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
    saveToken(null);
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

  me: () => request<User>("/auth/me"),
  signup: (data: { username: string; email: string; password: string }) =>
    request<User>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  setToken: (token: string) => { saveToken(token); },
  logout: () => { saveToken(null); },

  listAgents: () => request<Agent[]>("/agents"),
  createAgent: (payload: { name: string; email: string; team?: string }) =>
    request<Agent>("/agents", { method: "POST", body: JSON.stringify(payload) }),

  listCalls: () => request<Call[]>("/calls"),
  scoreCall: (payload: { agent_id: number; customer_ref?: string; transcript: string }) =>
    request<{ task_id: string; status: string }>("/calls/score", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listMailbox: () => request<MailboxItem[]>("/mailbox"),
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

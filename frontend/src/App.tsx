import React, { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell,
} from "recharts";
import {
  Phone, ListChecks, AlertTriangle, CheckCircle2, Clock,
  FileSpreadsheet, Presentation, ChevronRight, Inbox as InboxIcon, Lock
} from "lucide-react";
import { api } from "./api";
import type {
  AgentPerformance, MailboxItem, Task, TaskStatus, Priority, MailboxCategory, User
} from "./types";

type TabId = "dashboard" | "inbox" | "tasks";
const ACCENT = "#D4A24C";
const OK = "#4C9A8D";
const BG = "#14171C";
const PANEL = "#1B1F26";
const BORDER = "#2A2F38";
const TEXT_MUTED = "#8891A0";

const priorityColor: Record<Priority, string> = { high: "#C4573F", medium: ACCENT, low: OK };
const statusColor: Record<TaskStatus, string> = { open: ACCENT, in_progress: "#5B8FD9", blocked: "#C4573F", done: OK };

const MOCK_AGENTS: AgentPerformance[] = [
  { name: "Priya Sharma", calls: 24, avgScore: 88, flagged: 1 },
  { name: "Rohan Mehta", calls: 19, avgScore: 61, flagged: 5 },
  { name: "Ananya Iyer", calls: 31, avgScore: 92, flagged: 0 },
  { name: "Karan Verma", calls: 15, avgScore: 74, flagged: 2 },
];
const MOCK_MAILBOX: MailboxItem[] = [
  { id: 1, sender: "customer_884@mail.com", subject: "Package not delivered", body: "", received_at: "", category: "escalation", priority: "high", status: "open", sla_hours: 4 },
  { id: 2, sender: "customer_112@mail.com", subject: "Where is my order #58213", body: "", received_at: "", category: "status_check", priority: "medium", status: "drafted", sla_hours: 24 },
];
const MOCK_TASKS: Task[] = [
  { id: 1, title: "QA review needed - Call #204 (score 55)", status: "open", priority: "high", source_type: "qa_flag", agent: "Rohan Mehta" },
];

const CATEGORY_LABELS: Record<MailboxCategory, string> = {
  escalation: "Escalation", complaint: "Complaint", status_check: "Status check", info_request: "Info request", other: "Other",
};

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokenData = await api.login(form);
      api.setToken(tokenData.access_token);
      const user = await api.me();
      onLogin(user);
    } catch (e: any) {
      setError(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: BG, color: "#F2F3F5", fontFamily: "'Inter', sans-serif" }}>
      <div style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 16, padding: 32, width: 320, textAlign: "center" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}><div style={{ background: "#242A la 33", padding: 12, borderRadius: 12, color: ACCENT }}><Lock size={24} /></div></div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Welcome Back</h2>
        <p style={{ color: TEXT_MUTED, fontSize: 13, marginBottom: 24 }}>Enter your credentials to access Ops Copilot</p>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input type="text" placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }} />
          <input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }} />
          {error && <div style={{ color: "#C4573F", fontSize: 12, textAlign: "left" }}>{error}</div>}
          <button disabled={loading} style={{ background: ACCENT, color: BG, border: "none", padding: "12px", borderRadius: 8, fontWeight: 600, cursor: "pointer", fontSize: 14 }}>{loading ? "Authenticating..." : "Login"}</button>
        </form>
      </div>
    </div>
  );
}

function LiveBadge({ isLive }: { isLive: boolean }) {
  return <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, fontWeight: 600, color: isLive ? OK : TEXT_MUTED, border: `1px solid ${isLive ? OK : BORDER}` }}>{isLive ? "● live data" : "○ demo data"}</span>;
}

function Sidebar({ tab, setTab, user, onLogout }: { tab: TabId; setTab: (t: TabId) => void; user: User; onLogout: () => void }) {
  const items: { id: TabId; label: string; icon: any }[] = [
    { id: "dashboard", label: "QA Dashboard", icon: Phone },
    { id: "inbox", label: "Mailbox", icon: InboxIcon },
    { id: "tasks", label: "Tasks", icon: ListChecks },
  ];
  return (
    <div style={{ width: 220, background: PANEL, borderRight: `1px solid ${BORDER}`, padding: "24px 16px", display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ padding: "0 8px 24px 8px" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: TEXT_MUTED, letterSpacing: 1 }}>OPS://</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: "#F2F3F5", letterSpacing: -0.3 }}>Copilot</div>
      </div>
      {items.map(({ id, label, icon: Icon }) => (
        <button key={id} onClick={() => setTab(id)} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 8, border: "none", cursor: "pointer", textAlign: "left", background: tab === id ? "#242A33" : "transparent", color: tab === id ? "#F2F3F5" : TEXT_MUTED, fontSize: 14, fontWeight: tab === id ? 600 : 500 }}>
          <Icon size={16} /> {label}
        </button>
      ))}
      <div style={{ marginTop: "auto", padding: "16px 8px", borderTop: `1px solid ${BORDER}` }}>
        <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 8 }}>Signed in as:</div>
        <div style={{ fontSize: 13, color: "#F2F3F5", fontWeight: 600, marginBottom: 12 }}>{user.username} ({user.role})</div>
        <button onClick={onLogout} style={{ width: "100%", background: "transparent", border: `1px solid ${BORDER}`, color: TEXT_MUTED, padding: "8px", borderRadius: 8, cursor: "pointer", fontSize: 12 }}>Logout</button>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return <div style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 12, padding: "16px 18px", flex: 1, minWidth: 140 }}><div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div><div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 28, fontWeight: 700, color: color || "#F2F3F5" }}>{value}</div>{sub && <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 4 }}>{sub}</div>}</div>;
}

function Dashboard() {
  const [agents, isLive] = useState<AgentPerformance[]>(MOCK_AGENTS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchAgents() {
      setLoading(true);
      try {
        const [agentList, calls] = await Promise.all([api.listAgents(), api.listCalls()]);
        const performance = agentList.map((a) => {
          const agentCalls = calls.filter((c) => c.agent_id === a.id && c.qa_score);
          const avg = agentCalls.length ? Math.round(agentCalls.reduce((s, c) => s + (c.qa_score?.overall_score || 0), 0) / agentCalls.length) : 0;
          return { name: a.name, calls: agentCalls.length, avgScore: avg, flagged: agentCalls.filter((c) => c.qa_score?.flagged).length };
        });
        setAgents(performance);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }
    fetchAgents();
  }, []);

  const totalCalls = agents.reduce((s, a) => s + a.calls, 0);
  const totalFlagged = agents.reduce((s, a) => s + a.flagged, 0);
  const avgScore = agents.length ? Math.round(agents.reduce((s, a) => s + a.avgScore, 0) / agents.length) : 0;
  const scoreDistribution = [
    { name: "90-100", value: agents.filter((a) => a.avgScore >= 90).length, color: OK },
    { name: "70-89", value: agents.filter((a) => a.avgScore >= 70 && a.avgScore < 90).length, color: "#5B8FD9" },
    { name: "<70", value: agents.filter((a) => a.avgScore < 70).length, color: ACCENT },
  ];

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "#F2F3F5", margin: 0 }}>Call Quality Overview</h1>
            <LiveBadge isLive={true} />
          </div>
          <p style={{ color: TEXT_MUTED, fontSize: 13, marginTop: 4 }}>Auto-scored via LLM rubric across greeting, compliance, resolution, and tone.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <a href={api.reportUrls.excel()} style={{ textDecoration: "none" }}><button style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 500, padding: "8px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, background: PANEL, color: TEXT_MUTED, cursor: "pointer" }}><FileSpreadsheet size={14} /> Export Excel</button></a>
          <a href={api.reportUrls.pptx()} style={{ textDecoration: "none" }}><button style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 500, padding: "8px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, background: PANEL, color: TEXT_MUTED, cursor: "pointer" }}><Presentation size={14} /> Export Slides</button></a>
        </div>
      </div>
      <div style={{ display: "flex", gap: 14, marginBottom: 24 }}>
        <StatCard label="Calls Scored" value={totalCalls} sub="last 7 days" />
        <StatCard label="Avg QA Score" value={avgScore} color={avgScore >= 75 ? OK : ACCENT} sub="across all agents" />
        <StatCard label="Flagged Calls" value={totalFlagged} color={ACCENT} sub="below 70 threshold" />
      </div>
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 2, background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#F2F3F5", marginBottom: 16 }}>Agent Performance</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={agents} margin={{ left: -10 }}><CartesianGrid strokeDasharray="3 3" stroke={BORDER} vertical={false} /><XAxis dataKey="name" tick={{ fill: TEXT_MUTED, fontSize: 11 }} axisLine={{ stroke: BORDER }} tickLine={false} /><YAxis tick={{ fill: TEXT_MUTED, fontSize: 11 }} axisLine={{ stroke: BORDER }} tickLine={false} /><Tooltip contentStyle={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12 }} /><Bar dataKey="avgScore" radius={[4, 4, 0, 0]}>{agents.map((a, i) => <Cell key={i} fill={a.avgScore >= 75 ? OK : ACCENT} />)}</Bar></BarChart>
          </ResponsiveContainer>
        </div>
        <div style={{ flex: 1, background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#F2F3F5", marginBottom: 16 }}>Score Distribution</div>
          <ResponsiveContainer width="100%" height={200}><PieChart><Pie data={scoreDistribution} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={3}>{scoreDistribution.map((d, i) => <Cell key={i} fill={d.color} />)}</Pie><Tooltip contentStyle={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12 }} /></PieChart></ResponsiveContainer>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
            {scoreDistribution.map((d, i) => <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: TEXT_MUTED }}><span style={{ width: 8, height: 8, borderRadius: 2, background: d.color, display: "inline-block" }} />{d.name} <span style={{ marginLeft: "auto", color: "#F2F3F5" }}>{d.value} agents</span></div>)}
          </div>
        </div>
      </div>
    </div>
  );
}

function InboxTab() {
  const [items, setItems] = useState<MailboxItem[]>(MOCK_MAILBOX);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    api.listMailbox().then(setItems).catch(console.error);
  }, []);

  async function handleIngest() {
    setProcessing(true);
    try {
      const { task_id } = await api.ingestEmail({ sender: "test@mail.com", subject: "Test Subject", body: "Test body" });
      let poll = setInterval(async () => {
        const res = await api.getBackgroundTask(task_id);
        if (res.status === "completed") {
          clearInterval(poll);
          setProcessing(false);
          const updated = await api.listMailbox();
          setItems(updated);
        } else if (res.status === "failed") {
          clearInterval(poll);
          setProcessing(false);
        }
      }, 2000);
    } catch (e) { setProcessing(false); }
  }

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#F2F3F5", margin: 0 }}>Delivery Mailbox</h1>
          <LiveBadge isLive={true} />
        </div>
        <button onClick={handleIngest} disabled={processing} style={{ background: ACCENT, color: BG, border: "none", padding: "8px 16px", borderRadius: 8, fontWeight: 600, cursor: "pointer", fontSize: 13 }}>
          {processing ? "Processing AI..." : "Simulate Ingestion"}
        </button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((m) => (
          <div key={m.id} style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 10, padding: "14px 18px", display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: priorityColor[m.priority], flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, color: "#F2F3F5", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{m.subject}</div>
              <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>{m.sender}</div>
            </div>
            <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, fontWeight: 600, color: BG, background: "#3A4150", flexShrink: 0 }}>{CATEGORY_LABELS[m.category]}</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: TEXT_MUTED, flexShrink: 0 }}><Clock size={12} /> SLA {m.sla_hours}h</span>
            <ChevronRight size={16} color={TEXT_MUTED} />
          </div>
        ))}
      </div>
    </div>
  );
}

function TasksTab() {
  const [tasks, setTasks] = useState<Task[]>(MOCK_TASKS);

  useEffect(() => {
    api.listTasks().then(setTasks).catch(console.error);
  }, []);

  const columns: TaskStatus[] = ["open", "in_progress", "done"];
  const labels: Record<TaskStatus, string> = { open: "Open", in_progress: "In Progress", blocked: "Blocked", done: "Done" };

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#F2F3F5", margin: 0 }}>Task Tracker</h1>
        <LiveBadge isLive={true} />
      </div>
      <div style={{ display: "flex", gap: 16 }}>
        {columns.map((col) => (
          <div key={col} style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor[col] }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#F2F3F5" }}>{labels[col]}</span>
              <span style={{ fontSize: 12, color: TEXT_MUTED }}>{tasks.filter((t) => t.status === col).length}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {tasks.filter((t) => t.status === col).map((t) => (
                <div key={t.id} style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 14 }}>
                  <div style={{ fontSize: 13, color: "#F2F3F5", lineHeight: 1.4, marginBottom: 8 }}>{t.title}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 5, fontWeight: 700, color: priorityColor[t.priority], border: `1px solid ${priorityColor[t.priority]}` }}>{t.priority.toUpperCase()}</span>
                    {t.status === "done" ? <CheckCircle2 size={13} color={OK} /> : t.source_type === "qa_flag" ? <span style={{ fontSize: 11, color: TEXT_MUTED }}>{t.agent}</span> : t.source_type === "mailbox_escalation" ? <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: TEXT_MUTED }}><AlertTriangle size={11} /> mailbox</span> : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<TabId>("dashboard");
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("ops_token");
    if (token) {
      api.me().then(setUser).catch(() => {
        localStorage.removeItem("ops_token");
        setUser(null);
      });
    }
  }, []);

  const handleLogin = (u: User) => setUser(u);
  const handleLogout = () => {
    api.logout();
    setUser(null);
  };

  if (!user) return <Login onLogin={handleLogin} />;

  return (
    <div style={{ display: "flex", height: "100vh", background: BG, fontFamily: "'Inter', -apple-system, sans-serif" }}>
      <Sidebar tab={tab} setTab={setTab} user={user} onLogout={handleLogout} />
      {tab === "dashboard" && <Dashboard />}
      {tab === "inbox" && <InboxTab />}
      {tab === "tasks" && <TasksTab />}
    </div>
  );
}

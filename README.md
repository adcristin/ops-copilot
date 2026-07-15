# Ops Copilot

An automated delivery-operations toolkit: call quality auto-scoring, mailbox
triage, task tracking, and scheduled reporting — the software equivalent of
an "Operations Executive - Delivery Operations" role.

## What's built

| Module | What it does | Status |
|---|---|---|
| `backend/call_qa/` | Whisper transcription + LLM rubric scoring of call transcripts | Working |
| `backend/mailbox_ops/` | Classifies incoming emails, drafts replies, sets SLA/priority | Working |
| `backend/tasks/` | Auto-creates tasks from QA flags and mailbox escalations | Working |
| `backend/reporting/` | Generates Excel + PPT summary reports from live DB data | Working, tested end-to-end |
| `backend/core/llm_client.py` | Provider-agnostic LLM client — Anthropic direct or OpenRouter | Working |
| `backend/main.py` | FastAPI app wiring all of the above (18 routes) | Working, verified |
| `frontend/` | React + TypeScript dashboard (QA overview, mailbox inbox, task kanban) | Working, typechecked, builds clean |

The frontend attempts to fetch live data from the backend on load; if the
backend isn't running, it falls back to demo data automatically (look for
the "● live data" / "○ demo data" badge on each page).

## Tech stack

- **Backend**: Python, FastAPI, SQLAlchemy (SQLite by default, swap to
  Postgres via `DATABASE_URL`), Whisper (local, free), Anthropic SDK or
  OpenAI SDK (for OpenRouter)
- **Frontend**: React 18, TypeScript, Vite, Recharts, lucide-react

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill in your key(s)
uvicorn main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for interactive API docs (Swagger).

**Choosing an LLM provider** — set in `.env`:
```bash
# Option A: Anthropic direct (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option B: OpenRouter (one key, many models)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-fable-5
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. Set `VITE_API_BASE` in a `.env` file if your
backend isn't on `localhost:8000`.

## Try it end-to-end (backend running)

1. Create an agent: `POST /agents` with `{name, email, team}`
2. Score a call: `POST /calls/score` with `{agent_id, transcript}` — or
   `POST /calls/transcribe-and-score` with an audio file upload
3. Ingest an email: `POST /mailbox` with `{sender, subject, body}`
4. Check auto-created tasks: `GET /tasks`
5. Pull a report: `GET /reports/excel` or `GET /reports/pptx`
6. Refresh the frontend — the badges should flip to "● live data"

## What's next (not yet built)
- Auth (currently no login — fine for a portfolio demo, not for real use)
- Scheduled report generation (cron/APScheduler calling the reporting
  endpoints daily/weekly)
- Public dataset seeding scripts (Kaggle call-transcript / support-ticket
  datasets) so the demo looks populated out of the box without manual entry
- Deploy: backend to Render/Railway, frontend to Vercel, Postgres instead
  of SQLite for anything beyond local dev
- CI (GitHub Actions running `tsc --noEmit` + a basic pytest suite) — good
  next step now that this is a real repo

## Architecture notes
- The mailbox module directory is named `mailbox_ops` (not `mailbox`) to
  avoid a name collision with Python's stdlib `mailbox` module.
- LLM scoring/classification uses structured JSON output prompts, routed
  through `core/llm_client.py` so the provider (Anthropic vs OpenRouter) is
  a one-line env var swap, not a code change.
- Whisper runs locally (`base` model by default) — no external STT API
  needed, but slower without a GPU. Swap the model size in
  `call_qa/transcriber.py` if you need better accuracy or more speed.

## License
MIT — see [LICENSE](LICENSE).

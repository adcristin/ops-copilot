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
| `backend/scripts/` | Seed scripts pulling real public datasets (HF) for calls + mailbox | Working, logic tested with mocked data |
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

## Seed with real public datasets

Instead of manually creating agents/calls/emails to populate the demo, two
scripts pull real (non-PII) public datasets from Hugging Face:

```bash
cd backend

# Call transcripts (talkmap/telecom-conversation-corpus, MIT, synthetic)
python -m scripts.seed_call_qa --limit 20                # ingest only
python -m scripts.seed_call_qa --limit 20 --score         # + LLM QA scoring (uses your API key)

# Mailbox tickets (Tobi-Bueck/customer-support-tickets, CC-BY-NC-4.0)
python -m scripts.seed_mailbox --limit 20                 # ingest only
python -m scripts.seed_mailbox --limit 20 --classify       # + LLM classification (uses your API key)
```

Both scripts stream the dataset (no full download) and work without an API
key if you skip `--score`/`--classify` — they'll just store the raw
transcript/ticket with the dataset's own priority field instead of an
LLM-derived one. With the flag, each item goes through the real scoring/
classification pipeline, including auto-task-creation on flags/escalations
— exactly like a live call or email would.

**Note on datasets library**: `pip install datasets` was not tested against
the live Hugging Face endpoint in the environment that built this repo (no
network access to huggingface.co there) — the grouping/parsing logic was
verified against the dataset's actual documented schema and with mocked
data, but do a first run with a small `--limit` (e.g. 5) to confirm the
live download behaves as expected on your machine before seeding more.

## What's next (not yet built)
- Auth (currently no login — fine for a portfolio demo, not for real use)
- Scheduled report generation (cron/APScheduler calling the reporting
  endpoints daily/weekly)
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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python/FastAPI)
- **Install dependencies**: `cd backend && pip install -r requirements.txt`
- **Run server**: `cd backend && uvicorn main:app --reload --port 8000`
- **Run tests**: `cd backend && pytest tests/`
- **Run specific test**: `cd backend && pytest tests/test_filename.py`

### Frontend (React/TypeScript)
- **Install dependencies**: `cd frontend && npm install`
- **Run dev server**: `cd frontend && npm run dev`
- **Build for production**: `cd frontend && npm run build`

### Infrastructure
- **Launch full stack**: `docker-compose up --build`

## Architecture Overview

Ops Copilot is an automated delivery-operations toolkit consisting of a FastAPI backend and a React frontend.

### Backend Structure
- `backend/main.py`: Entry point and API route definitions.
- `backend/core/`:
  - `llm_client.py`: Interface for Anthropic/OpenAI SDKs.
  - `security.py`: JWT-based authentication and Role-Based Access Control (RBAC).
- `backend/db/`: SQLAlchemy models and session management (SQLite).
- `backend/call_qa/`: Logic for Whisper transcription and LLM-based rubric scoring of call transcripts.
- `backend/mailbox_ops/`: Email classification and response drafting.
- `backend/tasks/`: Automation for creating tasks from QA flags and email escalations.
- `backend/reporting/`: Generation of Excel and PowerPoint reports.
- `backend/tests/`: Integration and unit tests using `pytest` and `httpx`.

### Frontend Structure
- `frontend/src/`: React components and business logic.
- Built with Vite and TypeScript, using Recharts for data visualization.

### Key Patterns
- **Submit-Poll Pattern**: High-latency AI tasks (transcription, scoring) use an asynchronous pattern: `POST` request returns a `task_id` $\rightarrow$ client polls `GET /tasks/background/{task_id}` until completion.
- **Authentication**: Secured via JWT tokens (`Authorization: Bearer <token>`).
- **RBAC**: Access control is implemented based on user roles for sensitive operations like reporting and agent management.

"""
Ops Copilot - main FastAPI app.
Run with: uvicorn main:app --reload --port 8000
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()  # reads backend/.env into os.environ before any other import touches it

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import tempfile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from db.session import get_db, init_db
from db.models import Agent, Call, QAScore, MailboxItem, Task
from call_qa.scorer import score_and_explain
from mailbox_ops.classifier import classify_email
from tasks.service import (
    create_task_from_qa_flag,
    create_task_from_mailbox_escalation,
    get_overdue_tasks,
    close_task,
)
from reporting.generator import generate_excel_report, generate_pptx_report

app = FastAPI(title="Ops Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Schemas ----------

class TranscriptIn(BaseModel):
    agent_id: int
    customer_ref: Optional[str] = None
    transcript: str
    duration_seconds: Optional[int] = None


class EmailIn(BaseModel):
    sender: str
    subject: str
    body: str


class AgentIn(BaseModel):
    name: str
    email: str
    team: Optional[str] = None


# ---------- Agents ----------

@app.post("/agents")
def create_agent(payload: AgentIn, db: Session = Depends(get_db)):
    agent = Agent(name=payload.name, email=payload.email, team=payload.team)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@app.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


# ---------- Call QA ----------

@app.post("/calls/score")
def score_call(payload: TranscriptIn, db: Session = Depends(get_db)):
    """Ingest a transcript, run it through the LLM rubric scorer, store results,
    and auto-create a task if it's flagged."""
    call = Call(
        agent_id=payload.agent_id,
        customer_ref=payload.customer_ref,
        transcript=payload.transcript,
        duration_seconds=payload.duration_seconds,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    try:
        result = score_and_explain(payload.transcript)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scoring failed: {e}")

    qa_score = QAScore(
        call_id=call.id,
        overall_score=result["overall_score"],
        greeting_score=result["greeting_score"],
        compliance_score=result["compliance_score"],
        resolution_score=result["resolution_score"],
        tone_score=result["tone_score"],
        sentiment=result["sentiment"],
        flagged=result["flagged"],
        violations=result.get("violations", []),
        coaching_notes=result.get("coaching_notes", ""),
        raw_llm_response=result.get("raw_llm_response", {}),
    )
    db.add(qa_score)
    db.commit()
    db.refresh(qa_score)

    if qa_score.flagged:
        create_task_from_qa_flag(db, qa_score)

    return {"call_id": call.id, "qa_score": result}


@app.post("/calls/transcribe-and-score")
async def transcribe_and_score(
    agent_id: int = Form(...),
    customer_ref: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Full pipeline: upload audio -> Whisper transcription -> LLM rubric scoring -> store."""
    from call_qa.transcriber import transcribe_audio

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    try:
        transcript_result = transcribe_audio(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")
    finally:
        os.remove(tmp_path)

    transcript_text = transcript_result["text"]

    call = Call(
        agent_id=agent_id,
        customer_ref=customer_ref,
        audio_path=audio.filename,
        transcript=transcript_text,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    try:
        result = score_and_explain(transcript_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scoring failed: {e}")

    qa_score = QAScore(
        call_id=call.id,
        overall_score=result["overall_score"],
        greeting_score=result["greeting_score"],
        compliance_score=result["compliance_score"],
        resolution_score=result["resolution_score"],
        tone_score=result["tone_score"],
        sentiment=result["sentiment"],
        flagged=result["flagged"],
        violations=result.get("violations", []),
        coaching_notes=result.get("coaching_notes", ""),
        raw_llm_response=result.get("raw_llm_response", {}),
    )
    db.add(qa_score)
    db.commit()
    db.refresh(qa_score)

    if qa_score.flagged:
        create_task_from_qa_flag(db, qa_score)

    return {"call_id": call.id, "transcript": transcript_text, "qa_score": result}


@app.get("/calls/{call_id}")
def get_call(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).get(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return call


@app.get("/calls")
def list_calls(db: Session = Depends(get_db)):
    return db.query(Call).order_by(Call.call_date.desc()).all()


# ---------- Mailbox ----------

@app.post("/mailbox")
def ingest_email(payload: EmailIn, db: Session = Depends(get_db)):
    """Classify an incoming email, store it, auto-draft a reply, and escalate if needed."""
    try:
        result = classify_email(payload.subject, payload.body)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Classification failed: {e}")

    item = MailboxItem(
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
        category=result["category"],
        priority=result["priority"],
        sla_hours=result["sla_hours"],
        routed_to=result["routed_to"],
        suggested_reply=result["suggested_reply"],
        status="drafted",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    if result["category"] == "escalation":
        create_task_from_mailbox_escalation(db, item)

    return item


@app.get("/mailbox")
def list_mailbox(db: Session = Depends(get_db)):
    return db.query(MailboxItem).order_by(MailboxItem.received_at.desc()).all()


# ---------- Tasks ----------

@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.due_date.asc()).all()


@app.get("/tasks/overdue")
def overdue_tasks(db: Session = Depends(get_db)):
    return get_overdue_tasks(db)


@app.post("/tasks/{task_id}/close")
def close_task_endpoint(task_id: int, db: Session = Depends(get_db)):
    task = close_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


# ---------- Reporting ----------

@app.get("/reports/excel")
def download_excel(db: Session = Depends(get_db)):
    path = generate_excel_report(db, output_path="/tmp/ops_report.xlsx")
    return {"path": path}


@app.get("/reports/pptx")
def download_pptx(db: Session = Depends(get_db)):
    path = generate_pptx_report(db, output_path="/tmp/ops_report.pptx")
    return {"path": path}


@app.get("/")
def root():
    return {"status": "ok", "service": "ops-copilot", "time": datetime.utcnow().isoformat()}

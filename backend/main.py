"""
Ops Copilot - main FastAPI app.
Run with: uvicorn main:app --reload --port 8000
"""
from secrets import token_urlsafe
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()  # reads backend/.env into os.environ before any other import touches it

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import shutil
import tempfile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from db.session import get_db, init_db
from db.models import Agent, Call, QAScore, MailboxItem, Task, User
from core.security import (
    verify_password, get_password_hash, create_access_token, decode_access_token
)
from call_qa.scorer import score_and_explain
from mailbox_ops.classifier import classify_email
from tasks.service import (
    create_task_from_qa_flag,
    create_task_from_mailbox_escalation,
    get_overdue_tasks,
    close_task,
    create_background_task,
    update_background_task,
    get_background_task
)
from reporting.generator import generate_excel_report, generate_pptx_report

app = FastAPI(title="Ops Copilot API")

# CORS configuration
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",") if os.getenv("CORS_ALLOWED_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class UserIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """JWT token verification and user retrieval."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------- Background Workers ----------

def run_bg_score_call(task_id: str, payload: TranscriptIn):
    """Background worker for /calls/score"""
    db = next(get_db())
    try:
        update_background_task(db, task_id, "processing")

        call = Call(
            agent_id=payload.agent_id,
            customer_ref=payload.customer_ref,
            transcript=payload.transcript,
            duration_seconds=payload.duration_seconds,
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        result = score_and_explain(payload.transcript)

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

        update_background_task(db, task_id, "completed", result=result)
    except Exception as e:
        update_background_task(db, task_id, "failed", error=str(e))
    finally:
        db.close()


def run_bg_transcribe_and_score(task_id: str, agent_id: int, customer_ref: Optional[str], audio_path: str):
    """Background worker for /calls/transcribe-and-score"""
    db = next(get_db())
    try:
        update_background_task(db, task_id, "processing")
        from call_qa.transcriber import transcribe_audio

        transcript_result = transcribe_audio(audio_path)
        transcript_text = transcript_result["text"]

        call = Call(
            agent_id=agent_id,
            customer_ref=customer_ref,
            audio_path=audio_path,
            transcript=transcript_text,
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        result = score_and_explain(transcript_text)

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

        update_background_task(db, task_id, "completed", result={"transcript": transcript_text, "qa_score": result})
    except Exception as e:
        update_background_task(db, task_id, "failed", error=str(e))
    finally:
        db.close()


def run_bg_ingest_email(task_id: str, payload: EmailIn):
    """Background worker for /mailbox"""
    db = next(get_db())
    try:
        update_background_task(db, task_id, "processing")
        result = classify_email(payload.subject, payload.body)

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

        update_background_task(db, task_id, "completed", result=result)
    except Exception as e:
        update_background_task(db, task_id, "failed", error=str(e))
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Auth ----------

@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------- Agents ----------

@app.post("/agents")
def create_agent(payload: AgentIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    agent = Agent(name=payload.name, email=payload.email, team=payload.team)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@app.get("/agents")
def list_agents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Agent).all()


# ---------- Call QA ----------

@app.post("/calls/score", status_code=202)
def score_call(payload: TranscriptIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Ingest a transcript and schedule it for LLM rubric scoring."""
    task_id = create_background_task(db)
    background_tasks.add_task(run_bg_score_call, task_id, payload)
    return {"task_id": task_id, "status": "accepted"}


@app.post("/calls/transcribe-and-score", status_code=202)
def transcribe_and_score(
    background_tasks: BackgroundTasks,
    agent_id: int = Form(...),
    customer_ref: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Full pipeline: upload audio -> Whisper transcription -> LLM rubric scoring -> store."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    task_id = create_background_task(db)
    background_tasks.add_task(run_bg_transcribe_and_score, task_id, agent_id, customer_ref, tmp_path)

    return {"task_id": task_id, "status": "accepted"}


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

@app.post("/mailbox", status_code=202)
def ingest_email(payload: EmailIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Classify an incoming email and schedule it for processing."""
    task_id = create_background_task(db)
    background_tasks.add_task(run_bg_ingest_email, task_id, payload)
    return {"task_id": task_id, "status": "accepted"}


@app.get("/mailbox")
def list_mailbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(MailboxItem).order_by(MailboxItem.received_at.desc()).all()


# ---------- Tasks ----------

@app.get("/tasks/background/{task_id}")
def get_background_task_status(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Check the status of a background AI operation."""
    task = get_background_task(db, task_id)
    if not task:
        raise HTTPException(404, "Background task not found")
    return {
        "id": task.id,
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at
    }


@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Task).order_by(Task.due_date.asc()).all()


@app.get("/tasks/overdue")
def overdue_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_overdue_tasks(db)


@app.post("/tasks/{task_id}/close")
def close_task_endpoint(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = close_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


# ---------- Reporting ----------

@app.get("/reports/excel")
def download_excel(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    path = generate_excel_report(db, output_path="/tmp/ops_report.xlsx")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="ops_report.xlsx")


@app.get("/reports/pptx")
def download_pptx(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    path = generate_pptx_report(db, output_path="/tmp/ops_report.pptx")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="ops_report.pptx")


@app.get("/")
def root():
    return {"status": "ok", "service": "ops-copilot", "time": datetime.utcnow().isoformat()}

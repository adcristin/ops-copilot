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
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import shutil
import httpx
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
    email: str
    password: str



class UserOut(BaseModel):
    username: str
    email: Optional[str]
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

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
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
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/auth/signup", response_model=UserOut)
def signup(payload: UserIn, db: Session = Depends(get_db)):
    """Register a new user."""
    existing_user = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if existing_user:
        if existing_user.username == payload.username:
            raise HTTPException(status_code=400, detail="Username already registered")
        if existing_user.email == payload.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(payload.password)
    new_user = User(username=payload.username, email=payload.email, hashed_password=hashed_pw, role="user")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# ---------- OAuth ----------

async def handle_oauth_callback(provider: str, code: str, db: Session):
    """Common logic to handle OAuth callbacks."""
    if provider == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        token_url = "https://oauth2.googleapis.com/token"
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    elif provider == "github":
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        token_url = "https://github.com/login/oauth/access_token"
        user_info_url = "https://api.github.com/user"
    else:
        raise HTTPException(400, "Unsupported provider")

    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        if provider == "google":
            payload["redirect_uri"] = os.getenv("GOOGLE_REDIRECT_URI")
        elif provider == "github":
            payload["redirect_uri"] = os.getenv("GITHUB_REDIRECT_URI")

        token_resp = await client.post(token_url, data=payload, headers={"Accept": "application/json"})

        if token_resp.is_error:
            print(f"DEBUG: {provider} token exchange failed: {token_resp.status_code} - {token_resp.text}")
            raise HTTPException(401, "Failed to exchange code for token")

        access_token = token_resp.json().get("access_token")

        # 2. Get user info
        headers = {"Authorization": f"Bearer {access_token}"}
        if provider == "github":
            headers["User-Agent"] = "OpsCopilot-App"

        user_resp = await client.get(user_info_url, headers=headers)
        if user_resp.is_error:
            print(f"DEBUG: {provider} user_info error: {user_resp.text}")
            raise HTTPException(401, "Failed to fetch user info")

        user_data = user_resp.json()
        email = user_data.get("email")

        # GitHub specific: emails might be private and require a separate call
        if not email and provider == "github":
            email_resp = await client.get("https://api.github.com/user/emails", headers=headers)
            if not email_resp.is_error:
                emails = email_resp.json()
                # Find the primary verified email
                primary_email = next((e["email"] for e in emails if e["primary"]), None)
                if primary_email:
                    email = primary_email
        provider_id = user_data.get("id") or user_data.get("sub")

        if not email:
            raise HTTPException(400, "Email not provided by OAuth provider")

        # 3. Account Linking / Creation
        if provider == "google":
            user = db.query(User).filter(User.google_id == provider_id).first()
        elif provider == "github":
            user = db.query(User).filter(User.github_id == provider_id).first()
        else:
            raise HTTPException(400, "Unsupported provider")

        if not user:
            user = db.query(User).filter(User.email == email).first()
            if user:
                # Link provider ID to existing account
                if provider == "google": user.google_id = provider_id
                else: user.github_id = provider_id
            else:
                # Create new user
                import uuid
                username = f"user_{uuid.uuid4().hex[:8]}"
                user = User(username=username, email=email, role="user")
                if provider == "google": user.google_id = provider_id
                else: user.github_id = provider_id
                db.add(user)

            db.commit()
            db.refresh(user)

        # 4. Generate JWT and redirect
        jwt_token = create_access_token(data={"sub": str(user.id)})
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth-callback?token={jwt_token}")

@app.get("/auth/login/{provider}")
async def oauth_login(provider: str):
    """Redirect user to OAuth provider."""
    if provider == "google":
        url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        }
    elif provider == "github":
        url = "https://github.com/login/oauth/authorize"
        params = {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "redirect_uri": os.getenv("GITHUB_REDIRECT_URI"),
            "scope": "user:email",
        }
    else:
        raise HTTPException(400, "Unsupported provider")

    import urllib.parse
    query = urllib.parse.urlencode(params)
    return RedirectResponse(url=f"{url}?{query}")

@app.get("/auth/callback/{provider}")
async def oauth_callback(provider: str, code: str, db: Session = Depends(get_db)):
    """Handle OAuth callback."""
    return await handle_oauth_callback(provider, code, db)



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

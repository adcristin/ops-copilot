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

from datetime import datetime, time, timezone
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import shutil
import httpx
import tempfile
import logging
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from db.session import get_db, init_db
from db.models import Organization, Agent, Call, QAScore, MailboxItem, Task, User
from core.security import (
    verify_password, get_password_hash, create_access_token, decode_access_token,
    get_current_user, require_admin
)
from core.dependencies import get_scoped_db
from schemas import CallOut, CallListOut, CallDetailOut, CallCreate
from call_qa.scorer import score_and_explain
from call_qa.transcriber import transcribe_audio
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Ops Copilot API", lifespan=lifespan)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log")
    ]
)
logger = logging.getLogger("ops-copilot")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Error", "detail": exc.detail, "code": str(exc.status_code)},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception occurred: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "code": "500"},
    )

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


class EmailReplyIn(BaseModel):
    reply: str


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


    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str



class Token(BaseModel):
    access_token: str
    token_type: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ---------- Background Workers ----------

def process_call_ingestion(call_id: str, org_id: str, audio_path: Optional[str], transcript: Optional[str]):
    """Async pipeline: transcription -> scoring -> QA task creation."""
    from uuid import UUID
    db = next(get_db())
    try:
        call_uuid = UUID(call_id)
        org_uuid = UUID(org_id)
        call = db.query(Call).filter(Call.id == call_uuid).first()
        if not call:
            return

        # 1. Transcription Phase
        if audio_path:
            call.status = "transcribing"
            db.commit()

            transcription_result = transcribe_audio(audio_path)
            call.transcript = transcription_result["text"]
            db.commit()

        # 2. Scoring Phase
        if not call.transcript:
            raise ValueError("No transcript available for scoring")

        call.status = "scoring"
        db.commit()

        score_result = score_and_explain(call.transcript)

        qa_score = QAScore(
            call_id=call.id,
            overall_score=score_result["overall_score"],
            greeting_score=score_result["greeting_score"],
            compliance_score=score_result["compliance_score"],
            resolution_score=score_result["resolution_score"],
            tone_score=score_result["tone_score"],
            sentiment=score_result["sentiment"],
            flagged=score_result["flagged"],
            violations=score_result.get("violations", []),
            coaching_notes=score_result.get("coaching_notes", ""),
            raw_llm_response=score_result.get("raw_llm_response", {}),
        )
        db.add(qa_score)
        db.commit()

        # 3. QA Task Integration
        if qa_score.flagged:
            create_task_from_qa_flag(db, qa_score)

        call.status = "completed"
        db.commit()

    except Exception as e:
        # Ensure we use UUID for the update filter as well
        from uuid import UUID as UUIDType
        try:
            cid = UUIDType(call_id)
        except:
            cid = call_id
        db.query(Call).filter(Call.id == cid).update({"status": "failed", "error_reason": str(e)})
        db.commit()
    finally:
        db.close()

def run_bg_score_call(task_id: str, payload: TranscriptIn, org_id: str):
    """Background worker for /calls/score"""
    db = next(get_db())
    try:
        update_background_task(db, task_id, "processing")

        call = Call(
            org_id=org_id,
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


def run_bg_transcribe_and_score(task_id: str, agent_id: int, customer_ref: Optional[str], audio_path: str, org_id: str):
    """Background worker for /calls/transcribe-and-score"""
    db = next(get_db())
    try:
        update_background_task(db, task_id, "processing")
        from call_qa.transcriber import transcribe_audio

        transcript_result = transcribe_audio(audio_path)
        transcript_text = transcript_result["text"]

        call = Call(
            org_id=org_id,
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


def run_bg_ingest_email(task_id: str, payload: EmailIn, org_id: str):
    """Background worker for /mailbox"""
    db = next(get_db())
    try:
        update_background_task(db, task_id, "processing")
        result = classify_email(payload.subject, payload.body)

        item = MailboxItem(
            org_id=org_id,
            sender=payload.sender,
            subject=payload.subject,
            body=payload.body,
            category=result["category"],
            priority=result["priority"],
            sla_hours=result["sla_hours"],
            routed_to=result["routed_to"],
            suggested_reply=result["suggested_reply"],
            reasoning=result["reasoning"],
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




# ---------- Auth ----------

@app.post("/auth/token")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == form_data.username) | (User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")

    access_token = create_access_token(data={"sub": str(user.id)})

    # Set JWT in an httpOnly secure cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Should be True in production (HTTPS)
        samesite="lax",
        max_age=60 * 60 * 24 * 30 # Match ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.patch("/auth/me", response_model=UserOut)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update current user profile."""
    if payload.username:
        existing = db.query(User).filter(User.username == payload.username, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = payload.username

    if payload.email:
        existing = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = payload.email

    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/auth/change-password")
def change_password(payload: PasswordChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Change current user password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}


@app.post("/auth/logout")
def logout(response: Response):
    """Clear the authentication cookie."""
    response.delete_cookie("access_token")
    return {"detail": "Logged out successfully"}



@app.post("/auth/signup", response_model=UserOut)
def signup(payload: UserIn, db: Session = Depends(get_db)):
    """Register a new user."""
    existing_user = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if existing_user:
        if existing_user.username == payload.username:
            raise HTTPException(status_code=400, detail="Username already registered")
        if existing_user.email == payload.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Every user must belong to an organization.
    # For signup, we create a personal organization for them.
    personal_org = Organization(name=f"{payload.username}'s Organization")
    db.add(personal_org)
    db.commit()
    db.refresh(personal_org)

    hashed_pw = get_password_hash(payload.password)
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pw,
        role="user",
        org_id=personal_org.id
    )
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
            logger.error(f"{provider} token exchange failed: {token_resp.status_code} - {token_resp.text}")
            raise HTTPException(401, "Failed to exchange code for token")

        access_token = token_resp.json().get("access_token")

        # 2. Get user info
        headers = {"Authorization": f"Bearer {access_token}"}
        if provider == "github":
            headers["User-Agent"] = "OpsCopilot-App"

        user_resp = await client.get(user_info_url, headers=headers)
        if user_resp.is_error:
            logger.error(f"{provider} user_info error: {user_resp.text}")
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

                # Every user must belong to an organization.
                personal_org = Organization(name=f"{username}'s Organization")
                db.add(personal_org)
                db.commit()
                db.refresh(personal_org)

                user = User(username=username, email=email, role="user", org_id=personal_org.id)
                if provider == "google": user.google_id = provider_id
                else: user.github_id = provider_id
                db.add(user)

            db.commit()
            db.refresh(user)

        # 4. Generate JWT and redirect
        jwt_token = create_access_token(data={"sub": str(user.id)})
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        response = RedirectResponse(url=f"{frontend_url}/auth-callback")
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30
        )
        return response

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
def create_agent(payload: AgentIn, db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    agent = Agent(name=payload.name, email=payload.email, team=payload.team, org_id=current_user.org_id)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@app.get("/agents")
def list_agents(db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    return db.query(Agent).all()


# ---------- Call QA ----------

@app.post("/api/calls/upload", status_code=202)
def upload_call(
    background_tasks: BackgroundTasks,
    agent_id: UUID = Form(...),
    customer_ref: Optional[str] = Form(None),
    audio: UploadFile = File(None),
    transcript: Optional[str] = Form(None),
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
):
    """Unified ingestion: upload audio or transcript -> Async processing -> Scoring."""
    if not audio and not transcript:
        raise HTTPException(status_code=400, detail="Either audio file or transcript must be provided")

    audio_path = None
    if audio:
        # Use a temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            audio_path = tmp.name

    call = Call(
        org_id=current_user.org_id,
        agent_id=agent_id,
        customer_ref=customer_ref,
        audio_path=audio_path,
        transcript=transcript,
        status="pending"
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    background_tasks.add_task(process_call_ingestion, str(call.id), str(current_user.org_id), audio_path, transcript)

    return {"call_id": call.id, "status": call.status}

@app.get("/api/calls/{call_id}", response_model=CallDetailOut)
def get_call(call_id: UUID, db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(404, "Call not found")

    # Join with QAScore for the detail view
    qa_score = db.query(QAScore).filter(QAScore.call_id == call.id).first()

    return {**call.__dict__, "qa_score": qa_score}


@app.get("/api/calls", response_model=List[CallListOut])
def list_calls(
    db: Session = Depends(get_scoped_db),
    current_user: User = Depends(get_current_user),
    agent_id: Optional[UUID] = None,
    status: Optional[str] = None,
    flagged: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Paginated and filterable list of calls for the user's organization."""
    query = db.query(Call)

    # --- FILTERING LOGIC ---
    if agent_id is not None:
        query = query.filter(Call.agent_id == agent_id)

    if status is not None:
        query = query.filter(Call.status == status)

    if flagged is not None:
        # Only join when flagged is actually requested — an unconditional join
        # would silently drop every call that has no QAScore row yet (i.e. any
        # call still 'pending'/'transcribing'/'scoring'), even when nobody
        # asked to filter by flag status at all.
        query = query.join(QAScore).filter(QAScore.flagged == flagged)

    if start_date is not None:
        query = query.filter(Call.call_date >= start_date)

    if end_date is not None:
        # If end_date arrives as a bare date (midnight, no time component),
        # a plain <= comparison excludes everything later that same day.
        # Push the boundary to the start of the next day and use < instead,
        # so the entire end_date calendar day is included regardless of
        # whether the caller passed a date or a full timestamp.
        end_of_day = datetime.combine(end_date.date(), time.max)
        query = query.filter(Call.call_date <= end_of_day)
    # -----------------------

    return query.order_by(Call.call_date.desc()).offset(offset).limit(limit).all()


# ---------- Mailbox ----------

@app.post("/mailbox", status_code=202)
def ingest_email(payload: EmailIn, background_tasks: BackgroundTasks, db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    """Classify an incoming email and schedule it for processing."""
    task_id = create_background_task(db, current_user.org_id)
    background_tasks.add_task(run_bg_ingest_email, task_id, payload, current_user.org_id)
    return {"task_id": task_id, "status": "accepted"}


@app.get("/mailbox")
def list_mailbox(db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    return db.query(MailboxItem).order_by(MailboxItem.received_at.desc()).all()


@app.post("/mailbox/{item_id}/reply")
def send_mailbox_reply(item_id: UUID, payload: EmailReplyIn, db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    """Marks an email as replied and stores the final response."""
    item = db.query(MailboxItem).filter(MailboxItem.id == item_id, MailboxItem.org_id == current_user.org_id).first()
    if not item:
        raise HTTPException(404, "Mailbox item not found")

    item.final_reply = payload.reply
    item.status = "replied"
    item.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return {"detail": "Reply sent successfully", "item_id": item.id}


# ---------- Tasks ----------

@app.get("/tasks/background/{task_id}")
def get_background_task_status(task_id: str, db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
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
def list_tasks(db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    return db.query(Task).order_by(Task.due_date.asc()).all()


@app.get("/tasks/overdue")
def overdue_tasks(db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    return get_overdue_tasks(db)


@app.post("/tasks/{task_id}/close")
def close_task_endpoint(task_id: int, db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    task = close_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


# ---------- Reporting ----------

@app.get("/reports/excel")
def download_excel(db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    path = generate_excel_report(db, output_path="/tmp/ops_report.xlsx")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="ops_report.xlsx")


@app.get("/reports/pptx")
def download_pptx(db: Session = Depends(get_scoped_db), current_user: User = Depends(get_current_user)):
    path = generate_pptx_report(db, output_path="/tmp/ops_report.pptx")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="ops_report.pptx")


@app.get("/")
def root():
    return {"status": "ok", "service": "ops-copilot", "time": datetime.now(timezone.utc).isoformat()}

"""
SQLAlchemy models for Ops Copilot.
Using SQLite for local dev (swap DATABASE_URL for Postgres in production).
"""
from datetime import datetime
import uuid
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON, UUID, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("Agent", back_populates="organization")
    users = relationship("User", back_populates="organization")
    calls = relationship("Call", back_populates="organization")
    mailbox_items = relationship("MailboxItem", back_populates="organization")
    tasks = relationship("Task", back_populates="organization")
    background_tasks = relationship("BackgroundTask", back_populates="organization")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(200), unique=True)
    team = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="agents")
    calls = relationship("Call", back_populates="agent")
    tasks = relationship("Task", back_populates="assigned_agent")


class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    agent_id = Column(UUID, ForeignKey("agents.id"))
    customer_ref = Column(String(120))          # anonymized customer id
    audio_path = Column(String(500))            # path/URL to source audio (nullable if transcript-only)
    transcript = Column(Text)
    duration_seconds = Column(Integer)
    call_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending") # pending/transcribing/scoring/completed/failed
    error_reason = Column(Text, nullable=True)

    organization = relationship("Organization", back_populates="calls")
    agent = relationship("Agent", back_populates="calls")
    qa_score = relationship("QAScore", back_populates="call", uselist=False)


class QAScore(Base):
    """Structured output of the LLM rubric scorer for one call."""
    __tablename__ = "qa_scores"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID, ForeignKey("calls.id"), unique=True)

    overall_score = Column(Float)                # 0-100
    greeting_score = Column(Float)
    compliance_score = Column(Float)
    resolution_score = Column(Float)
    tone_score = Column(Float)

    sentiment = Column(String(20))               # positive/neutral/negative
    flagged = Column(Boolean, default=False)      # below threshold -> needs review
    violations = Column(JSON)                     # list of {category, quote, note}
    coaching_notes = Column(Text)
    raw_llm_response = Column(JSON)               # full structured response, for audit

    scored_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('overall_score >= 0 AND overall_score <= 100', name='check_overall_score'),
        CheckConstraint('greeting_score >= 0 AND greeting_score <= 100', name='check_greeting_score'),
        CheckConstraint('compliance_score >= 0 AND compliance_score <= 100', name='check_compliance_score'),
        CheckConstraint('resolution_score >= 0 AND resolution_score <= 100', name='check_resolution_score'),
        CheckConstraint('tone_score >= 0 AND tone_score <= 100', name='check_tone_score'),
    )

    call = relationship("Call", back_populates="qa_score")


class MailboxItem(Base):
    """A single email that came into the shared delivery mailbox."""
    __tablename__ = "mailbox_items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    sender = Column(String(200))
    subject = Column(String(500))
    body = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)

    category = Column(String(50))                # complaint/status_check/escalation/info_request/other
    priority = Column(String(20))                 # low/medium/high
    status = Column(String(30), default="open")   # open/drafted/replied/escalated/closed
    sla_hours = Column(Integer, default=24)
    responded_at = Column(DateTime, nullable=True)

    suggested_reply = Column(Text)
    routed_to = Column(String(120))                # stakeholder/team name

    organization = relationship("Organization", back_populates="mailbox_items")
    task = relationship("Task", back_populates="mailbox_item", uselist=False)


class Task(Base):
    """Unified task tracker - links back to QA flags or mailbox escalations."""
    __tablename__ = "tasks"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    status = Column(String(30), default="open")    # open/in_progress/blocked/done
    priority = Column(String(20), default="medium")
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    assigned_agent_id = Column(UUID, ForeignKey("agents.id"), nullable=True)
    source_type = Column(String(30))                # "qa_flag" / "mailbox_escalation" / "manual"
    source_qa_score_id = Column(UUID, ForeignKey("qa_scores.id"), nullable=True)
    mailbox_item_id = Column(UUID, ForeignKey("mailbox_items.id"), nullable=True)

    organization = relationship("Organization", back_populates="tasks")
    assigned_agent = relationship("Agent", back_populates="tasks")
    mailbox_item = relationship("MailboxItem", back_populates="task")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(20), default="user") # admin/user
    google_id = Column(String(100), unique=True, nullable=True)
    github_id = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")


class BackgroundTask(Base):
    """Tracks the status of heavy async operations (transcription, scoring)."""
    __tablename__ = "background_tasks"

    id = Column(String(50), primary_key=True) # UUID
    org_id = Column(UUID, ForeignKey("organizations.id"), nullable=False)
    status = Column(String(20), default="pending") # pending/processing/completed/failed
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="background_tasks")

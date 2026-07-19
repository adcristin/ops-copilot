"""
SQLAlchemy models for Ops Copilot.
Using SQLite for local dev (swap DATABASE_URL for Postgres in production).
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), unique=True)
    team = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow)

    calls = relationship("Call", back_populates="agent")
    tasks = relationship("Task", back_populates="assigned_agent")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    customer_ref = Column(String(120))          # anonymized customer id
    audio_path = Column(String(500))            # path/URL to source audio (nullable if transcript-only)
    transcript = Column(Text)
    duration_seconds = Column(Integer)
    call_date = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="calls")
    qa_score = relationship("QAScore", back_populates="call", uselist=False)


class QAScore(Base):
    """Structured output of the LLM rubric scorer for one call."""
    __tablename__ = "qa_scores"

    id = Column(Integer, primary_key=True)
    call_id = Column(Integer, ForeignKey("calls.id"), unique=True)

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

    call = relationship("Call", back_populates="qa_score")


class MailboxItem(Base):
    """A single email that came into the shared delivery mailbox."""
    __tablename__ = "mailbox_items"

    id = Column(Integer, primary_key=True)
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

    task = relationship("Task", back_populates="mailbox_item", uselist=False)


class Task(Base):
    """Unified task tracker - links back to QA flags or mailbox escalations."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    status = Column(String(30), default="open")    # open/in_progress/blocked/done
    priority = Column(String(20), default="medium")
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    assigned_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    source_type = Column(String(30))                # "qa_flag" / "mailbox_escalation" / "manual"
    source_qa_score_id = Column(Integer, ForeignKey("qa_scores.id"), nullable=True)
    mailbox_item_id = Column(Integer, ForeignKey("mailbox_items.id"), nullable=True)

    assigned_agent = relationship("Agent", back_populates="tasks")
    mailbox_item = relationship("MailboxItem", back_populates="task")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user") # admin/user
    created_at = Column(DateTime, default=datetime.utcnow)


class BackgroundTask(Base):
    """Tracks the status of heavy async operations (transcription, scoring)."""
    __tablename__ = "background_tasks"

    id = Column(String(50), primary_key=True) # UUID
    status = Column(String(20), default="pending") # pending/processing/completed/failed
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


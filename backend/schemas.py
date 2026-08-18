from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class CallBase(BaseModel):
    agent_id: UUID
    customer_ref: Optional[str] = None
    duration_seconds: Optional[int] = None

class CallCreate(CallBase):
    transcript: Optional[str] = None

class CallOut(CallBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    org_id: UUID
    audio_path: Optional[str] = None
    transcript: Optional[str] = None
    call_date: datetime
    status: str
    error_reason: Optional[str] = None

class CallListOut(CallBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    call_date: datetime
    status: str
    flagged: bool = False

class QAScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    overall_score: float
    greeting_score: float
    compliance_score: float
    resolution_score: float
    tone_score: float
    sentiment: str
    flagged: bool
    violations: List[dict]
    coaching_notes: Optional[str]
    scored_at: datetime

class CallDetailOut(CallOut):
    qa_score: Optional[QAScoreOut] = None

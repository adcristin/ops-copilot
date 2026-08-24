"""
Task Service
------------
Creates and manages tasks. Auto-generates tasks from:
  - QA scores that fall below the flag threshold
  - Mailbox items classified as escalation/complaint
This is what turns "gaps identified" into "tasks tracked to closure" from the JD.
"""
import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import Task, QAScore, MailboxItem, Call, BackgroundTask


def create_task_from_qa_flag(db: Session, qa_score: QAScore) -> Task:
    call: Call = qa_score.call
    task = Task(
        title=f"QA review needed - Call #{call.id} (score {qa_score.overall_score})",
        description=(
            f"Overall score {qa_score.overall_score} fell below threshold.\n"
            f"Violations: {qa_score.violations}\n"
            f"Coaching notes: {qa_score.coaching_notes}"
        ),
        org_id=call.org_id,
        status="open",
        priority="high" if qa_score.overall_score < 50 else "medium",
        due_date=datetime.utcnow() + timedelta(days=2),
        assigned_agent_id=call.agent_id,
        source_type="qa_flag",
        source_qa_score_id=qa_score.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def create_task_from_mailbox_escalation(db: Session, item: MailboxItem) -> Task:
    task = Task(
        title=f"Escalation: {item.subject}",
        description=item.body,
        status="open",
        priority=item.priority,
        due_date=datetime.utcnow() + timedelta(hours=item.sla_hours),
        source_type="mailbox_escalation",
        mailbox_item_id=item.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_overdue_tasks(db: Session):
    now = datetime.utcnow()
    return (
        db.query(Task)
        .filter(Task.status != "done", Task.due_date < now)
        .all()
    )


def close_task(db: Session, task_id: int) -> Task:
    task = db.query(Task).get(task_id)
    if task:
        task.status = "done"
        task.closed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
    return task


def create_background_task(db: Session, org_id: uuid.UUID) -> str:
    """Initialize a background task record and return its ID."""
    task_id = str(uuid.uuid4())
    bg_task = BackgroundTask(id=task_id, org_id=org_id, status="pending")
    db.add(bg_task)
    db.commit()
    return task_id


def update_background_task(db: Session, task_id: str, status: str, result: dict = None, error: str = None):
    """Update the status and result of a background task."""
    task = db.query(BackgroundTask).get(task_id)
    if task:
        task.status = status
        if result:
            task.result = result
        if error:
            task.error = error
        db.commit()


def get_background_task(db: Session, task_id: str) -> BackgroundTask:
    """Retrieve a background task by ID."""
    return db.query(BackgroundTask).get(task_id)

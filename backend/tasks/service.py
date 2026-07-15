"""
Task Service
------------
Creates and manages tasks. Auto-generates tasks from:
  - QA scores that fall below the flag threshold
  - Mailbox items classified as escalation/complaint
This is what turns "gaps identified" into "tasks tracked to closure" from the JD.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import Task, QAScore, MailboxItem, Call


def create_task_from_qa_flag(db: Session, qa_score: QAScore) -> Task:
    call: Call = qa_score.call
    task = Task(
        title=f"QA review needed - Call #{call.id} (score {qa_score.overall_score})",
        description=(
            f"Overall score {qa_score.overall_score} fell below threshold.\n"
            f"Violations: {qa_score.violations}\n"
            f"Coaching notes: {qa_score.coaching_notes}"
        ),
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

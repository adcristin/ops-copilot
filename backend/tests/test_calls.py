import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from main import app, process_call_ingestion
from db.models import Call, QAScore, Task
from fastapi.testclient import TestClient
from core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def auth_header(db_session):
    """Provide a valid auth header for a test user."""
    from db.models import User, Organization
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.commit()

    user = User(
        username="testuser",
        email="test@example.com",
        role="admin",
        org_id=org.id
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}

def test_upload_transcript_success(db_session, auth_header):
    """Test uploading a transcript directly."""
    # DEBUG: Check columns
    from sqlalchemy import inspect
    inspector = inspect(db_session.get_bind())
    cols = [c['name'] for c in inspector.get_columns('calls')]
    print(f"\nDEBUG: Columns in 'calls' table: {cols}")

    agent_id = uuid4()
    # Need an agent in the DB
    from db.models import Agent, Organization
    org = db_session.query(Organization).first()
    agent = Agent(name="Test Agent", email=f"agent_{uuid4().hex[:8]}@example.com", org_id=org.id)
    db_session.add(agent)
    db_session.commit()

    with patch("main.process_call_ingestion") as mock_process:
        response = client.post(
            "/api/calls/upload",
            data={
                "agent_id": str(agent.id),
                "transcript": "Hello, this is a test call.",
            },
            headers=auth_header
        )

    assert response.status_code == 202
    data = response.json()
    assert "call_id" in data
    assert data["status"] == "pending"

    # Verify call record exists
    from uuid import UUID
    call = db_session.query(Call).filter(Call.id == UUID(data["call_id"])).first()
    assert call is not None
    assert call.transcript == "Hello, this is a test call."
    assert mock_process.called

def test_process_call_ingestion_full_pipeline(db_session):
    """Test the background worker from start to finish."""
    from db.models import Call, Organization, Agent
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.commit()

    agent = Agent(name="Test Agent", email=f"agent_{uuid4().hex[:8]}@example.com", org_id=org.id)
    db_session.add(agent)
    db_session.commit()

    call = Call(
        org_id=org.id,
        agent_id=agent.id,
        transcript=None,
        audio_path="/tmp/test.wav",
        status="pending"
    )
    db_session.add(call)
    db_session.commit()

    # Mock transcription and scoring
    with patch("main.transcribe_audio") as mock_transcribe, \
         patch("main.score_and_explain") as mock_score:

        mock_transcribe.return_value = {"text": "Transcribed text"}
        mock_score.return_value = {
            "overall_score": 85.0,
            "greeting_score": 90.0,
            "compliance_score": 80.0,
            "resolution_score": 80.0,
            "tone_score": 90.0,
            "sentiment": "positive",
            "flagged": False,
            "violations": [],
            "coaching_notes": "Good job",
            "raw_llm_response": {}
        }

        process_call_ingestion(str(call.id), str(org.id), "/tmp/test.wav", None)

    # Verify state transitions and final result
    db_session.refresh(call)
    assert call.status == "completed"
    assert call.transcript == "Transcribed text"

    score = db_session.query(QAScore).filter(QAScore.call_id == call.id).first()
    assert score is not None
    assert score.overall_score == 85.0

def test_process_call_ingestion_flagged_creates_task(db_session):
    """Verify that a flagged call results in a coaching task."""
    from db.models import Call, Organization, Agent
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.commit()

    agent = Agent(name="Test Agent", email=f"agent_{uuid4().hex[:8]}@example.com", org_id=org.id)
    db_session.add(agent)
    db_session.commit()

    call = Call(
        org_id=org.id,
        agent_id=agent.id,
        transcript="Poor quality call",
        status="pending"
    )
    db_session.add(call)
    db_session.commit()

    with patch("main.score_and_explain") as mock_score:
        mock_score.return_value = {
            "overall_score": 40.0,
            "greeting_score": 50.0,
            "compliance_score": 30.0,
            "resolution_score": 40.0,
            "tone_score": 60.0,
            "sentiment": "negative",
            "flagged": True,
            "violations": [{"category": "Compliance", "quote": "Forgot to verify ID", "note": "Critical fail"}],
            "coaching_notes": "Needs urgent training on ID verification",
            "raw_llm_response": {}
        }

        process_call_ingestion(str(call.id), str(org.id), None, "Poor quality call")

    # Verify task creation
    task = db_session.query(Task).filter(Task.source_type == "qa_flag").first()
    assert task is not None
    assert "Needs urgent training" in task.description

def test_process_call_ingestion_failure(db_session):
    """Verify that failures are captured in error_reason."""
    from db.models import Call, Organization
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.commit()

    call = Call(org_id=org.id, status="pending", transcript="Some text")
    db_session.add(call)
    db_session.commit()

    with patch("main.score_and_explain", side_effect=Exception("API Timeout")):
        process_call_ingestion(str(call.id), str(org.id), None, "Some text")

    db_session.refresh(call)
    assert call.status == "failed"
    assert "API Timeout" in call.error_reason

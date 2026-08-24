import pytest
from fastapi.testclient import TestClient
from main import app
from db.models import MailboxItem, Organization, User
from core.security import create_access_token
from uuid import uuid4

client = TestClient(app)

@pytest.fixture
def auth_header(db_session):
    """Provide a valid auth header for a test user."""
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

def test_ingest_email_success(db_session, auth_header):
    """Test successful email ingestion."""
    payload = {
        "sender": "customer@example.com",
        "subject": "Where is my package?",
        "body": "I ordered a package 5 days ago and it's not here."
    }

    # Mock the classifier to avoid LLM calls
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("main.classify_email", lambda s, b: {
            "category": "status_check",
            "priority": "medium",
            "sla_hours": 24,
            "routed_to": "Delivery Coordination",
            "suggested_reply": "We are checking on your package.",
            "reasoning": "Customer asking for status.",
            "confidence": 0.9
        })

        response = client.post("/mailbox", json=payload, headers=auth_header)

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "accepted"

def test_ingest_email_unauthorized(db_session):
    """Verify 401 if no auth header is provided."""
    payload = {
        "sender": "customer@example.com",
        "subject": "Test",
        "body": "Test"
    }
    response = client.post("/mailbox", json=payload)
    assert response.status_code == 401

def test_list_mailbox_success(db_session, auth_header):
    """Test listing mailbox items."""
    org = db_session.query(Organization).first()
    item = MailboxItem(
        org_id=org.id,
        sender="test@example.com",
        subject="Test Subject",
        body="Test Body",
        category="info_request",
        priority="low",
        sla_hours=24,
        routed_to="General",
        suggested_reply="Hi",
        reasoning="Reason",
        status="drafted"
    )
    db_session.add(item)
    db_session.commit()

    response = client.get("/mailbox", headers=auth_header)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_send_reply_success(db_session, auth_header):
    """Test replying to a mailbox item."""
    org = db_session.query(Organization).first()
    item = MailboxItem(
        org_id=org.id,
        sender="test@example.com",
        subject="Test Subject",
        body="Test Body",
        category="info_request",
        priority="low",
        sla_hours=24,
        routed_to="General",
        suggested_reply="Hi",
        reasoning="Reason",
        status="drafted"
    )
    db_session.add(item)
    db_session.commit()

    response = client.post(
        f"/mailbox/{item.id}/reply",
        json={"reply": "This is the final reply"},
        headers=auth_header
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Reply sent successfully"

def test_send_reply_not_found(db_session, auth_header):
    """Verify 404 for non-existent item."""
    import uuid
    response = client.post(
        f"/mailbox/{uuid.uuid4()}/reply",
        json={"reply": "Test"},
        headers=auth_header
    )
    assert response.status_code == 404

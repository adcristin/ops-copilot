import pytest
from fastapi.testclient import TestClient
from main import app, get_db
from sqlalchemy.orm import Session
from db.models import User, Organization
from core.security import get_password_hash

client = TestClient(app)

def test_auth_unprotected_route(db_session):
    # The root endpoint should be public
    response = client.get("/")
    assert response.status_code == 200

def test_auth_protected_route_no_token(db_session):
    # Attempt to access a protected route without a token
    response = client.get("/agents")
    assert response.status_code == 401

def test_auth_invalid_password(db_session):
    # Create user
    org = Organization(name="Test Org 2")
    db_session.add(org)
    db_session.commit()
    user = User(username="failuser", hashed_password=get_password_hash("correct"), role="user", org_id=org.id)
    db_session.add(user)
    db_session.commit()

    # Attempt login with wrong password
    response = client.post("/auth/token", data={"username": "failuser", "password": "wrongpassword"})
    assert response.status_code == 401
    assert "Incorrect username/email or password" in response.json()["detail"]

def test_auth_invalid_token(db_session):
    # Access protected route with malformed token
    response = client.get("/agents", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]

def test_auth_flow(db_session):
    # Create a test organization
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.commit()

    # Create a test user
    username = "testuser"
    password = "testpassword"
    hashed_password = get_password_hash(password)

    db = db_session
    user = User(username=username, hashed_password=hashed_password, role="admin", org_id=org.id)
    db.add(user)
    db.commit()

    # Login to get token
    response = client.post("/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Access protected route with token (Header)
    response = client.get("/agents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # Access protected route with token (Cookie)
    client.cookies.set("access_token", token)
    response = client.get("/agents")
    assert response.status_code == 200

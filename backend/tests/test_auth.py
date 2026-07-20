import pytest
from fastapi.testclient import TestClient
from main import app, get_db
from sqlalchemy.orm import Session
from db.models import User
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

def test_auth_flow(db_session):
    # Create a test user
    username = "testuser"
    password = "testpassword"
    hashed_password = get_password_hash(password)

    db = db_session
    user = User(username=username, hashed_password=hashed_password, role="admin")
    db.add(user)
    db.commit()

    # Login to get token
    response = client.post("/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Access protected route with token
    response = client.get("/agents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

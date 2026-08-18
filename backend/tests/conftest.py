import os
import tempfile

# Set the test database URL BEFORE importing any application modules
# so that the global engine in db.session is initialized with the test DB.
TEST_DB_FILE = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base
from db.session import get_db
from main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialize the test database schema once per session."""
    from db.session import engine
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except PermissionError:
            pass

@pytest.fixture
def db_session(monkeypatch):
    """
    Provides a transactional database session for a single test.
    Each test runs in its own transaction which is rolled back at the end.
    """
    from db.session import SessionLocal

    # Use the global engine which is now bound to the temp file
    from db.session import engine
    connection = engine.connect()
    transaction = connection.begin()

    # Create a session bound to this specific connection to ensure it stays in the transaction
    session = SessionLocal(bind=connection)

    # Wrap the session to prevent the application from closing it prematurely
    class NoCloseSession:
        def __init__(self, s):
            self._s = s
        def __getattr__(self, name):
            return getattr(self._s, name)
        def close(self):
            pass  # Do nothing on close

    wrapped_session = NoCloseSession(session)

    # Override FastAPI dependency to return this specific session
    app.dependency_overrides[get_db] = lambda: wrapped_session

    # Mock get_db for direct calls in the app (e.g. in background tasks)
    def mock_get_db():
        yield wrapped_session

    monkeypatch.setattr("main.get_db", mock_get_db)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

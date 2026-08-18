import pytest
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker
from db.session import get_db
from db.models import Base, Organization, Agent, Call, QAScore, MailboxItem, Task, User
from main import app

# Use an in-memory SQLite database for lightning-fast, fresh tests
TEST_DATABASE_URL = "sqlite://"

@pytest.fixture(scope="session")
def engine():
    # For in-memory SQLite, the connection must stay open to keep the DB alive
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=pool.StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, monkeypatch):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=engine)()

    # Override get_db dependency to return this session
    app.dependency_overrides[get_db] = lambda: session

    def mock_get_db():
        yield session

    monkeypatch.setattr("main.get_db", mock_get_db)

    yield session


    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

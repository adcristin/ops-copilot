import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.session import get_db
from db.models import Base

# Use a separate SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test_ops_copilot.db"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=engine)()

    # Override get_db dependency to return this session
    from main import app
    app.dependency_overrides[get_db] = lambda: session

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

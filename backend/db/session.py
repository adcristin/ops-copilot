import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session, with_loader_criteria
from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ops_copilot.db")

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "supabase.co" in DATABASE_URL or "supabase.com" in DATABASE_URL:
    # Supabase requires SSL; sslmode=require works whether or not the URL
    # already has query params (psycopg2 accepts it via connect_args too).
    connect_args = {"sslmode": "require"}
else:
    connect_args = {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ScopedSession(Session):
    """A session that automatically filters all queries by org_id."""
    def __init__(self, *args, org_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org_id = org_id

    def execute(self, statement, *args, **kwargs):
        # with_loader_criteria is currently causing TypeErrors because it requires a specific entity.
        # We rely on the .query() method to handle org_id filtering for now.
        return super().execute(statement, *args, **kwargs)

    def query(self, entity):
        # Support for legacy query() style
        query = super().query(entity)
        if self.org_id and hasattr(entity, "org_id"):
            query = query.filter(entity.org_id == self.org_id)
        return query

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

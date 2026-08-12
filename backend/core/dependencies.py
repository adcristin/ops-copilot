from fastapi import Depends
from sqlalchemy.orm import Session
from db.session import get_db, ScopedSession
from core.security import get_current_user
from db.models import User

def get_scoped_db(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns a session scoped to the current user's organization.
    This session automatically filters all queries for models with an 'org_id'
    attribute, making it structurally difficult to leak cross-org data.
    """
    scoped_db = ScopedSession(bind=db.bind, org_id=current_user.org_id)
    try:
        yield scoped_db
    finally:
        scoped_db.close()

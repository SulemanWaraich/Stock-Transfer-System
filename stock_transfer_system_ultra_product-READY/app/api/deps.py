from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def current_user(request: Request, db: Session):
    email = request.session.get("user_email")
    if not email: return None
    return db.query(User).filter(User.email==email).first()

def require_login(user):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")

def require_role(user, roles: list[str]):
    require_login(user)
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

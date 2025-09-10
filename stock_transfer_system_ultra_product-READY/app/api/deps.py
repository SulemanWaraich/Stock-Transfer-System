from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User

# DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get current user from session
def current_user(request: Request, db: Session = Depends(get_db)):
    email = request.session.get("user_email")
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()

# Require login
def require_login(user: User = Depends(current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user  # important: return user so it can be reused

# Require role(s)
def require_role(roles: list[str]):
    def role_checker(user: User = Depends(require_login)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

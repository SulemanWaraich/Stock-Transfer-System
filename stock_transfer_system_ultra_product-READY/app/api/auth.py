from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from app.api.deps import get_db
from app.core.security import verify_password, hash_password
from app.models.user import User, Organization
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
async def login(request: Request, 
email: str = Form(...), 
password: str = Form(...),
db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email==email).first()
    if user and verify_password(password, user.hashed_password):
        request.session["user_email"] = user.email
        request.session["org_id"] = user.org_id
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)

def seed_admin(db: Session):
    org = db.query(Organization).filter_by(name="Default Org").first()
    if not org:
        org = Organization(name="Default Org")
        db.add(org); db.commit(); db.refresh(org)
    user = db.query(User).filter_by(email=settings.ADMIN_EMAIL).first()
    if not user:
        user = User(email=settings.ADMIN_EMAIL, name=settings.ADMIN_NAME,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role="Admin", org_id=org.id)
        db.add(user); db.commit()

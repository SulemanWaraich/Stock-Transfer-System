from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.api.deps import get_db, require_role
from app.models.user import User, Organization
from app.core.security import hash_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["Admin"]))
):
    users = db.query(User).filter(User.org_id == user.org_id).all()
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users})


@router.post("/admin/users/create")
def user_create(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["Admin"]))
):
    u = User(
        email=email,
        name=name,
        role=role,
        hashed_password=hash_password(password),
        org_id=user.org_id
    )
    db.add(u)
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.get("/admin/org", response_class=HTMLResponse)
def org_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["Admin"]))
):
    org = db.query(Organization).filter_by(id=user.org_id).first()
    return templates.TemplateResponse("admin_org.html", {"request": request, "org": org})

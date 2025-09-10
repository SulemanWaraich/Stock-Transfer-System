from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from app.api.deps import get_db, current_user, require_role
from app.models.inventory import Rules

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/rules", response_class=HTMLResponse)
def rules_page(request: Request, db: Session = get_db().__next__()):
    user = current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=302)
    rules = db.query(Rules).filter(Rules.org_id==user.org_id).first()
    if not rules:
        rules = Rules(org_id=user.org_id, target_days_cover=7, min_display=1, pack_size=1)
        db.add(rules); db.commit(); db.refresh(rules)
    return templates.TemplateResponse("rules.html", {"request": request, "rules": rules})

@router.post("/rules")
def save_rules(request: Request, target_days_cover: int = Form(...), min_display: int = Form(...), pack_size: int = Form(...), db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Planner"])
    rules = db.query(Rules).filter(Rules.org_id==user.org_id).first()
    if not rules:
        rules = Rules(org_id=user.org_id)
        db.add(rules)
    rules.target_days_cover = target_days_cover
    rules.min_display = min_display
    rules.pack_size = pack_size
    db.commit()
    return RedirectResponse("/rules", status_code=302)

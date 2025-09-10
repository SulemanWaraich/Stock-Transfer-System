from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from app.api.deps import get_db, current_user
from app.models.plan import TransferPlan

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/approvals", response_class=HTMLResponse)
def approvals_page(request: Request, db: Session = get_db().__next__()):
    user = current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=302)
    plans = db.query(TransferPlan).filter(TransferPlan.org_id==user.org_id).order_by(TransferPlan.id.desc()).all()
    return templates.TemplateResponse("approvals.html", {"request": request, "plans": plans})

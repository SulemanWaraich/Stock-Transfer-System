from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os, pandas as pd, csv, io

from app.api.deps import get_db, current_user, require_role
from app.models.inventory import Sale, Stock, Store, Rules, Item
from app.models.plan import TransferPlan, TransferItem, PlanComment
from app.services.planner import compute_velocity, plan_transfers

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
EXPORTS_DIR = "exports"

@router.get("/plan", response_class=HTMLResponse)
def plan_page(request: Request, lookback: int = 7, db: Session = get_db().__next__()):
    user = current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=302)
    require_role(user, ["Admin","Planner","Approver","StoreManager","Viewer"])

    sales = pd.read_sql(db.query(Sale).filter(Sale.org_id==user.org_id).statement, db.bind)
    stock = pd.read_sql(db.query(Stock).filter(Stock.org_id==user.org_id).statement, db.bind)
    stores = pd.read_sql(db.query(Store).filter(Store.org_id==user.org_id).statement, db.bind)
    items  = pd.read_sql(db.query(Item).filter(Item.org_id==user.org_id).statement, db.bind)

    rules_obj = db.query(Rules).filter(Rules.org_id==user.org_id).first()
    rules = {"target_days_cover": rules_obj.target_days_cover if rules_obj else 7,
             "min_display": rules_obj.min_display if rules_obj else 1,
             "pack_size": rules_obj.pack_size if rules_obj else 1}

    vel = compute_velocity(sales, lookback_days=lookback)
    plan_df, pick, recv, kpi = plan_transfers(stock, vel, stores, rules)

    # save plan
    plan = TransferPlan(org_id=user.org_id, created_by=user.id, status="Draft", lookback_days=lookback)
    db.add(plan); db.commit(); db.refresh(plan)
    for _, r in plan_df.iterrows():
        db.add(TransferItem(plan_id=plan.id, **r.to_dict()))
    db.commit()

    # export excel
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_name = f"Plan_{plan.id}_{ts}.xlsx"
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    with pd.ExcelWriter(os.path.join(EXPORTS_DIR, export_name)) as writer:
        sales.to_excel(writer, index=False, sheet_name="Sales")
        stock.to_excel(writer, index=False, sheet_name="Stock")
        items.to_excel(writer, index=False, sheet_name="Items")
        stores.to_excel(writer, index=False, sheet_name="Stores")
        pd.DataFrame([rules]).to_excel(writer, index=False, sheet_name="Rules")
        plan_df.to_excel(writer, index=False, sheet_name="Transfer Plan")
        pick.to_excel(writer, index=False, sheet_name="Pick List")
        recv.to_excel(writer, index=False, sheet_name="Receive List")
        kpi.to_excel(writer, index=False, sheet_name="KPIs")

    # charts data
    k_head = kpi.head(20).to_dict(orient="records")
    return templates.TemplateResponse("plan.html", {"request": request, "plan": plan_df.to_dict(orient="records"),
                                                    "kpis": k_head, "lookback": lookback,
                                                    "export_path": f"/exports/{export_name}",
                                                    "csv_pick": f"/plan/{plan.id}/pick.csv",
                                                    "csv_recv": f"/plan/{plan.id}/receive.csv"})

@router.get("/plan/{plan_id}")
def plan_detail(request: Request, plan_id: int, db: Session = get_db().__next__()):
    user = current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=302)
    plan = db.query(TransferPlan).filter_by(id=plan_id, org_id=user.org_id).first()
    items = db.query(TransferItem).filter_by(plan_id=plan_id).all()
    comments = db.query(PlanComment).filter(PlanComment.plan_id==plan_id).all()
    return templates.TemplateResponse("transfer_detail.html", {"request": request, "plan": plan, "items": items, "comments": comments})

@router.post("/plan/{plan_id}/comment")
def add_comment(request: Request, plan_id: int, db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Planner","Approver"])
    form = request.scope.get("_body");  # fallback for Starlette; we'll fetch via request.form in sync
    from starlette.requests import Request as SR
    import anyio
    async def read_form():
        form = await request.form()
        return form.get("comment","")
    import asyncio
    try:
        comment_text = asyncio.get_event_loop().run_until_complete(read_form())
    except RuntimeError:
        import nest_asyncio; nest_asyncio.apply()
        comment_text = asyncio.get_event_loop().run_until_complete(read_form())
    db.add(PlanComment(plan_id=plan_id, user_email=user.email, comment=comment_text))
    db.commit()
    return RedirectResponse(f"/plan/{plan_id}", status_code=302)

@router.post("/plan/{plan_id}/submit")
def submit_plan(request: Request, plan_id: int, db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Planner"])
    plan = db.query(TransferPlan).filter_by(id=plan_id, org_id=user.org_id).first()
    plan.status = "Submitted"; db.commit()
    return RedirectResponse(f"/plan/{plan_id}", status_code=302)

@router.post("/plan/{plan_id}/approve")
def approve_plan(request: Request, plan_id: int, db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Approver"])
    plan = db.query(TransferPlan).filter_by(id=plan_id, org_id=user.org_id).first()
    plan.status = "Approved"; db.commit()
    return RedirectResponse(f"/plan/{plan_id}", status_code=302)

@router.post("/plan/{plan_id}/reject")
def reject_plan(request: Request, plan_id: int, db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Approver"])
    plan = db.query(TransferPlan).filter_by(id=plan_id, org_id=user.org_id).first()
    plan.status = "Rejected"; db.commit()
    return RedirectResponse(f"/plan/{plan_id}", status_code=302)

@router.get("/plan/{plan_id}/pick.csv")
def csv_pick(plan_id: int, db: Session = get_db().__next__()):
    items = pd.read_sql(db.query(TransferItem).filter(TransferItem.plan_id==plan_id).statement, db.bind)
    if items.empty:
        content = "from_store_id,from_store,sku,style,size,qty\n"
    else:
        pick = items.groupby(["from_store_id","from_store","sku","style","size"], as_index=False)["qty"].sum()
        content = pick.to_csv(index=False)
    return FileResponse(io.BytesIO(content.encode("utf-8")), media_type="text/csv", filename=f"pick_{plan_id}.csv")

@router.get("/plan/{plan_id}/receive.csv")
def csv_recv(plan_id: int, db: Session = get_db().__next__()):
    items = pd.read_sql(db.query(TransferItem).filter(TransferItem.plan_id==plan_id).statement, db.bind)
    if items.empty:
        content = "to_store_id,to_store,sku,style,size,qty\n"
    else:
        recv = items.groupby(["to_store_id","to_store","sku","style","size"], as_index=False)["qty"].sum()
        content = recv.to_csv(index=False)
    return FileResponse(io.BytesIO(content.encode("utf-8")), media_type="text/csv", filename=f"receive_{plan_id}.csv")

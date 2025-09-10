from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
import io, pandas as pd

from app.api.deps import get_db, current_user, require_role
from app.models.inventory import Sale, Stock, Item, Store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db: Session = get_db().__next__()):
    user = current_user(request, db)
    if not user: return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("upload.html", {"request": request, "year": 2025})

@router.post("/upload/csv")
async def upload_csv(request: Request, sales: UploadFile = None, stock: UploadFile = None, items: UploadFile = None, stores: UploadFile = None, db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Planner"])
    if sales:
        df = pd.read_csv(io.BytesIO(await sales.read()))
        for _, r in df.iterrows():
            db.add(Sale(org_id=user.org_id, date=pd.to_datetime(r["date"]).date(), store_id=str(r["store_id"]), store_name=str(r["store_name"]),
                        sku=str(r["sku"]), style=str(r["style"]), size=str(r["size"]), units_sold=int(r["units_sold"])))
    if stock:
        df = pd.read_csv(io.BytesIO(await stock.read()))
        for _, r in df.iterrows():
            db.add(Stock(org_id=user.org_id, store_id=str(r["store_id"]), store_name=str(r["store_name"]), sku=str(r["sku"]),
                         style=str(r["style"]), size=str(r["size"]), on_hand=int(r["on_hand"])))
    if items:
        df = pd.read_csv(io.BytesIO(await items.read()))
        for _, r in df.iterrows():
            db.add(Item(org_id=user.org_id, sku=str(r["sku"]), style=str(r["style"]), size=str(r["size"]), category=str(r.get("category",""))))
    if stores:
        df = pd.read_csv(io.BytesIO(await stores.read()))
        for _, r in df.iterrows():
            db.add(Store(org_id=user.org_id, store_id=str(r["store_id"]), store_name=str(r["store_name"]), priority=int(r.get("priority",1))))
    db.commit()
    return RedirectResponse("/upload", status_code=302)

@router.post("/upload/demo")
def upload_demo(request: Request, db: Session = get_db().__next__()):
    user = current_user(request, db); require_role(user, ["Admin","Planner"])
    # Load embedded sample CSVs
    import csv, os
    base = "sample_data"
    for name, model in [("Sales.csv","sales"),("Stock.csv","stock"),("Items.csv","items"),("Stores.csv","stores")]:
        path = os.path.join(base, name)
        df = pd.read_csv(path)
        if model=="sales":
            for _, r in df.iterrows():
                db.add(Sale(org_id=user.org_id, date=pd.to_datetime(r["date"]).date(), store_id=r["store_id"], store_name=r["store_name"],
                            sku=r["sku"], style=r["style"], size=r["size"], units_sold=int(r["units_sold"])))
        elif model=="stock":
            for _, r in df.iterrows():
                db.add(Stock(org_id=user.org_id, store_id=r["store_id"], store_name=r["store_name"], sku=r["sku"],
                             style=r["style"], size=r["size"], on_hand=int(r["on_hand"])))
        elif model=="items":
            for _, r in df.iterrows():
                db.add(Item(org_id=user.org_id, sku=r["sku"], style=r["style"], size=r["size"], category=r["category"]))
        else:
            for _, r in df.iterrows():
                db.add(Store(org_id=user.org_id, store_id=r["store_id"], store_name=r["store_name"], priority=int(r["priority"])))
    db.commit()
    return RedirectResponse("/upload", status_code=302)
